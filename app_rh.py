import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os
import time

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="RH ETUS - AutoSave Pro", layout="wide", page_icon="🟢")

# --- 2. CONEXÃO ---
try:
    DB_URL = st.secrets["postgres"]["url"]
    engine = create_engine(DB_URL, connect_args={"sslmode": "require"})
except KeyError:
    st.error("Erro: URL do banco não configurada nos Secrets.")
    st.stop()

# --- 3. CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif !important; }
    .header-rh { font-size: 42px; font-weight: 700; color: #8DF768; margin-bottom: 25px; border-left: 10px solid #151514; padding-left: 15px; }
    .candidate-card {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #333;
        margin-bottom: 5px;
    }
    .candidate-name { font-size: 18px; font-weight: 700; color: #FFFFFF; }
    /* Estilo para o Toast de sucesso */
    [data-testid="stToast"] {
        background-color: #151514 !important;
        border: 1px solid #8DF768 !important;
        color: #8DF768 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNÇÕES DE BANCO (COM FEEDBACK) ---
def update_candidato(id_cand, campo, valor, nome_cand):
    """Atualiza o banco e fornece feedback visual imediato."""
    try:
        with engine.connect() as conn:
            query = text(f"UPDATE candidatos SET {campo} = :v WHERE id = :id")
            conn.execute(query, {"v": valor, "id": id_cand})
            conn.commit()
        # Feedback visual no canto da tela
        st.toast(f"✅ {nome_cand} atualizado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

def carregar_vagas():
    return pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)

def carregar_candidatos_vaga(v_nome):
    query = text("SELECT * FROM candidatos WHERE vaga_vinculada = :v ORDER BY id DESC")
    return pd.read_sql(query, engine, params={"v": v_nome})

# --- 5. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    menu = st.radio("NAVEGAÇÃO", ["📊 DASHBOARD", "🏢 VAGAS", "⚙️ FLUXO"])

st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- 6. FLUXO (AUTO-SAVE COM FEEDBACK) ---
if menu == "⚙️ FLUXO":
    df_vagas = carregar_vagas()
    if df_vagas.empty:
        st.warning("Cadastre uma vaga primeiro.")
    else:
        v_sel = st.selectbox("Vaga sendo gerenciada:", df_vagas["nome_vaga"].tolist())
        
        with st.popover("➕ Adicionar Candidato"):
            nome_c = st.text_input("Nome")
            if st.button("Confirmar"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral) VALUES (:c, :v, 'Vaga aberta')"), {"c": nome_c, "v": v_sel})
                    conn.commit()
                st.rerun()

        st.divider()
        df_c = carregar_candidatos_vaga(v_sel)
        
        opcoes_status = ["Vaga aberta", "Triagem", "Entrevista RH", "Entrevista gestor", "Solicitação de documentos", "Solicitação de contratos", "Finalizada"]
        
        for idx, cand in df_c.iterrows():
            with st.container():
                st.markdown(f'<div class="candidate-card"><div class="candidate-name">{cand["candidato"]}</div></div>', unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 0.5])
                
                # AUTO-SAVE STATUS
                col1.selectbox(
                    "Status", opcoes_status, 
                    index=opcoes_status.index(cand['status_geral']), 
                    key=f"st_{cand['id']}",
                    on_change=lambda id=cand['id'], n=cand['candidato'], k=f"st_{cand['id']}": 
                              update_candidato(id, "status_geral", st.session_state[k], n)
                )

                # AUTO-SAVE DATA RH
                col2.date_input(
                    "RH", value=cand['entrevista_rh'], 
                    key=f"rh_{cand['id']}",
                    on_change=lambda id=cand['id'], n=cand['candidato'], k=f"rh_{cand['id']}": 
                              update_candidato(id, "entrevista_rh", st.session_state[k], n)
                )

                # AUTO-SAVE DATA GESTOR
                col3.date_input(
                    "Gestor", value=cand['entrevista_gestor'], 
                    key=f"gs_{cand['id']}",
                    on_change=lambda id=cand['id'], n=cand['candidato'], k=f"gs_{cand['id']}": 
                              update_candidato(id, "entrevista_gestor", st.session_state[k], n)
                )

                # EXCLUIR
                if col4.button("🗑️", key=f"del_{cand['id']}"):
                    with engine.connect() as conn:
                        conn.execute(text("DELETE FROM candidatos WHERE id = :id"), {"id": cand['id']})
                        conn.commit()
                    st.rerun()
                
                st.markdown("<br>", unsafe_allow_html=True)

# Mantive os outros menus (Dashboard e Vagas) simplificados para focar na sua dúvida.
