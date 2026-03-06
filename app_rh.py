import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="RH ETUS - AutoSave", layout="wide", page_icon="🟢")

# --- 2. CONEXÃO ---
try:
    DB_URL = st.secrets["postgres"]["url"]
    engine = create_engine(DB_URL, connect_args={"sslmode": "require"})
except KeyError:
    st.error("Erro: URL do banco não configurada nos Secrets.")
    st.stop()

# --- 3. CSS (UI DE SISTEMA MODERNO) ---
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
        margin-bottom: 15px;
    }
    .candidate-name { font-size: 18px; font-weight: 700; color: #FFFFFF; margin-bottom: 2px; }
    .stSelectbox label, .stDateInput label { color: #888 !important; font-size: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNÇÕES DE BANCO (LÓGICA DE AUTO-SAVE) ---
def update_candidato(id_cand, campo, valor):
    """Atualiza um campo específico do candidato no Postgres de forma automática."""
    with engine.connect() as conn:
        query = text(f"UPDATE candidatos SET {campo} = :v WHERE id = :id")
        conn.execute(query, {"v": valor, "id": id_cand})
        conn.commit()
    st.toast(f"✅ Registro atualizado!")

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

# --- 6. DASHBOARD ---
if menu == "📊 DASHBOARD":
    df_c = pd.read_sql("SELECT * FROM candidatos", engine)
    if not df_c.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("CANDIDATOS", len(df_c))
        c2.metric("CONTRATADOS", len(df_c[df_c["aprovacao_final"] == "Sim"]))
        c3.metric("VAGAS", len(pd.read_sql("SELECT * FROM vagas", engine)))
        st.divider()
        st.subheader("Funil de Recrutamento")
        st.bar_chart(df_c["status_geral"].value_counts(), color="#8DF768")
    else:
        st.info("Sem dados para exibir.")

# --- 7. VAGAS ---
elif menu == "🏢 VAGAS":
    st.subheader("Controle de Vagas")
    with st.expander("➕ NOVA VAGA"):
        with st.form("f_v"):
            n = st.text_input("Nome")
            a = st.selectbox("Área", ["Marketing", "Vendas", "Operações", "TI", "RH"])
            if st.form_submit_button("CRIAR"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO vagas (nome_vaga, area, status_vaga) VALUES (:n, :a, 'Aberta')"), {"n": n, "a": a})
                    conn.commit()
                st.rerun()

    st.divider()
    df_v = carregar_vagas()
    for _, row in df_v.iterrows():
        c_v1, c_v2 = st.columns([5, 1])
        c_v1.write(f"💼 **{row['nome_vaga']}** ({row['area']})")
        if c_v2.button("🗑️", key=f"del_v_{row['nome_vaga']}"):
            with engine.connect() as conn:
                conn.execute(text("DELETE FROM candidatos WHERE vaga_vinculada = :v"), {"v": row['nome_vaga']})
                conn.execute(text("DELETE FROM vagas WHERE nome_vaga = :v"), {"v": row['nome_vaga']})
                conn.commit()
            st.rerun()

# --- 8. FLUXO (AUTO-SAVE EM CARDS) ---
elif menu == "⚙️ FLUXO":
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
                # Estética do Card
                st.markdown(f'<div class="candidate-card"><div class="candidate-name">{cand["candidato"]}</div></div>', unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 0.5])
                
                # --- AUTO-SAVE STATUS ---
                novo_st = col1.selectbox(
                    "Status", opcoes_status, 
                    index=opcoes_status.index(cand['status_geral']), 
                    key=f"st_{cand['id']}",
                    on_change=lambda id=cand['id'], key=f"st_{cand['id']}": update_candidato(id, "status_geral", st.session_state[key])
                )

                # --- AUTO-SAVE DATA RH ---
                col2.date_input(
                    "RH", value=cand['entrevista_rh'], 
                    key=f"rh_{cand['id']}",
                    on_change=lambda id=cand['id'], key=f"rh_{cand['id']}": update_candidato(id, "entrevista_rh", st.session_state[key])
                )

                # --- AUTO-SAVE DATA GESTOR ---
                col3.date_input(
                    "Gestor", value=cand['entrevista_gestor'], 
                    key=f"gs_{cand['id']}",
                    on_change=lambda id=cand['id'], key=f"gs_{cand['id']}": update_candidato(id, "entrevista_gestor", st.session_state[key])
                )

                # --- EXCLUIR ---
                if col4.button("🗑️", key=f"del_{cand['id']}"):
                    with engine.connect() as conn:
                        conn.execute(text("DELETE FROM candidatos WHERE id = :id"), {"id": cand['id']})
                        conn.commit()
                    st.rerun()
                
                st.markdown("<br>", unsafe_allow_html=True)
