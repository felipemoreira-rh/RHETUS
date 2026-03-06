import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="RH ETUS - Ultra Speed", layout="wide", page_icon="🟢")

# --- 2. POOL DE CONEXÃO (CACHEADO) ---
@st.cache_resource
def get_engine():
    url = st.secrets["postgres"]["url"]
    return create_engine(url, pool_pre_ping=True, connect_args={"sslmode": "require"})

engine = get_engine()

# --- 3. FUNÇÃO DE SALVAMENTO DIRETA ---
def fast_update(id_cand, campo, chave_estado, nome_cand):
    """Lê o valor novo diretamente do widget e salva no banco."""
    novo_valor = st.session_state[chave_estado]
    try:
        with engine.begin() as conn:
            query = text(f"UPDATE candidatos SET {campo} = :v WHERE id = :id")
            conn.execute(query, {"v": novo_valor, "id": id_cand})
        st.toast(f"⚡ {nome_cand} salvo!")
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

# --- 4. FRAGMENTO DO CARD (VELOCIDADE ISOLADA) ---
@st.fragment
def card_candidato(cand, opcoes_status):
    """Gerencia as mudanças de um candidato sem recarregar a página toda."""
    with st.container():
        # Visual do Card
        st.markdown(f'''
            <div style="background-color: #1E1E1E; padding: 15px; border-radius: 12px; border-left: 5px solid #8DF768; margin-bottom: 10px;">
                <span style="color: white; font-size: 18px; font-weight: bold;">{cand["candidato"]}</span>
            </div>
        ''', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 0.5])
        
        # CHAVES ÚNICAS PARA O ESTADO
        k_st = f"st_{cand['id']}"
        k_rh = f"rh_{cand['id']}"
        k_gs = f"gs_{cand['id']}"

        # STATUS com Auto-save
        col1.selectbox(
            "Status", opcoes_status, 
            index=opcoes_status.index(cand['status_geral']) if cand['status_geral'] in opcoes_status else 0,
            key=k_st,
            on_change=fast_update,
            args=(cand['id'], "status_geral", k_st, cand['candidato'])
        )
        
        # DATA RH com Auto-save
        col2.date_input(
            "Entrevista RH", value=cand['entrevista_rh'], 
            key=k_rh,
            on_change=fast_update,
            args=(cand['id'], "entrevista_rh", k_rh, cand['candidato'])
        )
        
        # DATA GESTOR com Auto-save
        col3.date_input(
            "Entrevista Gestor", value=cand['entrevista_gestor'], 
            key=k_gs,
            on_change=fast_update,
            args=(cand['id'], "entrevista_gestor", k_gs, cand['candidato'])
        )

        # BOTÃO EXCLUIR
        if col4.button("🗑️", key=f"del_{cand['id']}", help="Excluir Candidato"):
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM candidatos WHERE id = :id"), {"id": cand['id']})
            st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)

# --- 5. INTERFACE PRINCIPAL ---
st.markdown('<h1 style="color: #8DF768; font-family: sans-serif;">RH ETUS</h1>', unsafe_allow_html=True)

menu = st.sidebar.radio("Navegação", ["📊 DASHBOARD", "🏢 VAGAS", "⚙️ FLUXO"])

if menu == "⚙️ FLUXO":
    # Carregar vagas para o seletor
    df_vagas = pd.read_sql("SELECT nome_vaga FROM vagas ORDER BY nome_vaga", engine)
    
    if not df_vagas.empty:
        v_list = df_vagas["nome_vaga"].tolist()
        v_sel = st.selectbox("Escolha a Vaga", v_list)
        
        # Botão Adicionar (Fora do fragmento para poder dar rerun na lista)
        with st.popover("➕ Adicionar Candidato"):
            nome_novo = st.text_input("Nome do Candidato")
            if st.button("Salvar Novo"):
                with engine.begin() as conn:
                    conn.execute(text("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral) VALUES (:c, :v, 'Vaga aberta')"), 
                                 {"c": nome_novo, "v": v_sel})
                st.rerun()

        st.divider()

        # Carregar candidatos da vaga selecionada
        query = text("SELECT * FROM candidatos WHERE vaga_vinculada = :v ORDER BY id DESC")
        df_c = pd.read_sql(query, engine, params={"v": v_sel})
        
        opcoes_status = ["Vaga aberta", "Triagem", "Entrevista RH", "Entrevista gestor", "Solicitação de documentos", "Solicitação de contratos", "Finalizada"]
        
        # Renderizar cada candidato dentro de seu próprio fragmento
        for _, cand in df_c.iterrows():
            card_candidato(cand, opcoes_status)
    else:
        st.warning("Cadastre uma vaga no menu VAGAS primeiro.")

# Outros menus mantidos de forma simples para performance
elif menu == "🏢 VAGAS":
    st.subheader("Gestão de Vagas")
    # ... (lógica de vagas que você já possui)
