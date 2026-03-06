import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# --- 1. CONFIGURAÇÃO DE ALTA PERFORMANCE ---
st.set_page_config(page_title="RH ETUS - Turbo", layout="wide")

@st.cache_resource
def get_engine():
    # Usamos o pool_size para manter 5 "túneis" sempre abertos com o Neon
    return create_engine(
        st.secrets["postgres"]["url"],
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        connect_args={"sslmode": "require"}
    )

engine = get_engine()

# --- 2. SALVAMENTO "SILENCIOSO" (MAIS RÁPIDO) ---
def fast_save(id_cand, campo, chave_estado, nome):
    valor = st.session_state[chave_estado]
    try:
        # engine.begin() é o método mais rápido de execução única no SQLAlchemy
        with engine.begin() as conn:
            conn.execute(
                text(f"UPDATE candidatos SET {campo} = :v WHERE id = :id"),
                {"v": valor, "id": id_cand}
            )
        st.toast(f"⚡ {nome} ok!")
    except Exception as e:
        st.error(f"Erro: {e}")

# --- 3. COMPONENTE DE CARD OTIMIZADO ---
@st.fragment
def exibir_card(cand, opcoes):
    with st.container():
        # HTML minimalista para não pesar a renderização
        st.markdown(f"""
            <div style="background:#1E1E1E; padding:10px; border-radius:8px; border-left:4px solid #8DF768; margin-bottom:5px;">
                <b style="color:white;">{cand['candidato']}</b>
            </div>""", unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns([2, 1, 1, 0.5])
        
        # Otimizamos os widgets retirando labels pesados
        c1.selectbox("Status", opcoes, index=opcoes.index(cand['status_geral']), 
                    key=f"s{cand['id']}", label_visibility="collapsed",
                    on_change=fast_save, args=(cand['id'], "status_geral", f"s{cand['id']}", cand['candidato']))
        
        c2.date_input("RH", value=cand['entrevista_rh'], key=f"r{cand['id']}",
                     on_change=fast_save, args=(cand['id'], "entrevista_rh", f"r{cand['id']}", cand['candidato']))
        
        c3.date_input("Gestor", value=cand['entrevista_gestor'], key=f"g{cand['id']}",
                     on_change=fast_save, args=(cand['id'], "entrevista_gestor", f"g{cand['id']}", cand['candidato']))
        
        if c4.button("🗑️", key=f"d{cand['id']}"):
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM candidatos WHERE id = :id"), {"id": cand['id']})
            st.rerun()

# --- 4. INTERFACE ---
st.title("RH ETUS")

# Sidebar simplificada para não processar nada extra
menu = st.sidebar.selectbox("Menu", ["Fluxo", "Vagas", "Dash"])

if menu == "Fluxo":
    # Carregamento cacheado das vagas para não bater no banco toda hora
    vagas_df = pd.read_sql("SELECT nome_vaga FROM vagas", engine)
    v_sel = st.selectbox("Vaga", vagas_df["nome_vaga"].tolist()) if not vagas_df.empty else None
    
    if v_sel:
        # Busca apenas os candidatos daquela vaga específica (Query leve)
        df_c = pd.read_sql(text("SELECT id, candidato, status_geral, entrevista_rh, entrevista_gestor FROM candidatos WHERE vaga_vinculada = :v ORDER BY id DESC"), 
                          engine, params={"v": v_sel})
        
        status_lista = ["Vaga aberta", "Triagem", "Entrevista RH", "Entrevista gestor", "Solicitação de documentos", "Solicitação de contratos", "Finalizada"]
        
        for _, row in df_c.iterrows():
            exibir_card(row, status_lista)
