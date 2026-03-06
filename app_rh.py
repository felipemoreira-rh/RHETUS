import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="RH ETUS - Ultra Speed", layout="wide", page_icon="🟢")

# --- 2. POOL DE CONEXÃO OTIMIZADO ---
@st.cache_resource
def get_engine():
    """Mantém a conexão aberta para evitar o atraso de 'handshake' do banco."""
    url = st.secrets["postgres"]["url"]
    # pool_size e max_overflow mantêm conexões prontas para uso
    return create_engine(
        url, 
        pool_size=10, 
        max_overflow=20, 
        pool_pre_ping=True,
        connect_args={"sslmode": "require"}
    )

engine = get_engine()

# --- 3. FUNÇÃO DE SALVAMENTO ULTRA RÁPIDA ---
def fast_update(id_cand, campo, valor, nome_cand):
    """Executa a atualização com o mínimo de processamento possível."""
    try:
        with engine.begin() as conn:  # .begin() faz o commit automático e é mais rápido
            query = text(f"UPDATE candidatos SET {campo} = :v WHERE id = :id")
            conn.execute(query, {"v": valor, "id": id_cand})
        st.toast(f"⚡ {nome_cand} salvo!")
    except Exception as e:
        st.error(f"Erro: {e}")

# --- 4. FRAGMENTO DE UI (O segredo da velocidade) ---
@st.fragment
def card_candidato(cand, opcoes_status):
    """Atualiza apenas este card, sem recarregar a página toda."""
    with st.container():
        st.markdown(f'''
            <div style="background-color: #1E1E1E; padding: 12px; border-radius: 10px; border-left: 4px solid #8DF768; margin-bottom: 5px;">
                <strong style="color: white; font-size: 16px;">{cand["candidato"]}</strong>
            </div>
        ''', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 0.5])
        
        # O salvamento acontece no on_change sem dar refresh na página inteira
        col1.selectbox(
            "Status", opcoes_status, 
            index=opcoes_status.index(cand['status_geral']), 
            key=f"st_{cand['id']}",
            on_change=fast_update,
            args=(cand['id'], "status_geral", None, cand['candidato']),
            kwargs={"valor": None} # O valor será pego via session_state automaticamente se ajustado, 
                                   # mas para simplificar o fragment usamos a lógica direta:
        )
        # Nota: Para on_change com fragment, usamos st.session_state[key] dentro da função
        
        col2.date_input("RH", value=cand['entrevista_rh'], key=f"rh_{cand['id']}", 
                        on_change=lambda: fast_update(cand['id'], "entrevista_rh", st.session_state[f"rh_{cand['id']}"], cand['candidato']))
        
        col3.date_input("Gestor", value=cand['entrevista_gestor'], key=f"gs_{cand['id']}",
                        on_change=lambda: fast_update(cand['id'], "entrevista_gestor", st.session_state[f"gs_{cand['id']}"], cand['candidato']))

        if col4.button("🗑️", key=f"del_{cand['id']}"):
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM candidatos WHERE id = :id"), {"id": cand['id']})
            st.rerun()

# --- 5. INTERFACE PRINCIPAL ---
st.markdown('<h1 style="color: #8DF768;">RH ETUS</h1>', unsafe_allow_html=True)

menu = st.sidebar.radio("Menu", ["📊 DASHBOARD", "🏢 VAGAS", "⚙️ FLUXO"])

if menu == "⚙️ FLUXO":
    vagas = pd.read_sql("SELECT nome_vaga FROM vagas", engine)["nome_vaga"].tolist()
    if vagas:
        v_sel = st.selectbox("Selecione a Vaga", vagas)
        df_c = pd.read_sql(text("SELECT * FROM candidatos WHERE vaga_vinculada = :v ORDER BY id DESC"), engine, params={"v": v_sel})
        
        opcoes_status = ["Vaga aberta", "Triagem", "Entrevista RH", "Entrevista gestor", "Solicitação de documentos", "Solicitação de contratos", "Finalizada"]
        
        st.divider()
        for _, cand in df_c.iterrows():
            card_candidato(cand, opcoes_status)
    else:
        st.warning("Cadastre uma vaga.")
