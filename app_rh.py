import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
import os

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="RH ETUS - Gestão Pro", layout="wide", page_icon="🟢")

# --- 2. CONEXÃO ---
try:
    DB_URL = st.secrets["postgres"]["url"]
    engine = create_engine(DB_URL, connect_args={"sslmode": "require"})
except KeyError:
    st.error("Erro nos Secrets.")
    st.stop()

# --- 3. CSS MODERNIZAÇÃO (Cards e UI) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif !important; }
    
    .header-rh { font-size: 42px; font-weight: 700; color: #8DF768; margin-bottom: 30px; border-left: 10px solid #151514; padding-left: 15px; }
    
    /* Card do Candidato */
    .candidate-card {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #333;
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .candidate-card:hover { border-color: #8DF768; transform: translateY(-2px); }
    .candidate-name { font-size: 20px; font-weight: 700; color: #FFFFFF; margin-bottom: 5px; }
    .candidate-status { font-size: 14px; color: #8DF768; text-transform: uppercase; letter-spacing: 1px; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNÇÕES DE BANCO ---
def carregar_vagas():
    return pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)

def carregar_candidatos_vaga(v_nome):
    query = text("SELECT * FROM candidatos WHERE vaga_vinculada = :v ORDER BY id DESC")
    return pd.read_sql(query, engine, params={"v": v_nome})

# --- 5. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    menu = st.radio("NAVEGAÇÃO", ["📊 DASHBOARD", "🏢 GESTÃO DE VAGAS", "⚙️ FLUXO DE CANDIDATOS"])

st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- 6. DASHBOARD ---
if menu == "📊 DASHBOARD":
    df_c = pd.read_sql("SELECT * FROM candidatos", engine)
    if not df_c.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 CANDIDATOS ATIVOS", len(df_c))
        c2.metric("✅ CONTRATAÇÕES", len(df_c[df_c["aprovacao_final"] == "Sim"]))
        c3.metric("🏢 VAGAS NO SISTEMA", len(pd.read_sql("SELECT * FROM vagas", engine)))
        st.divider()
        fig = px.pie(df_c, names="status_geral", hole=.4, color_discrete_sequence=['#8DF768', '#4A4A4A', '#222222'])
        st.plotly_chart(fig, use_container_width=True)

# --- 7. VAGAS ---
elif menu == "🏢 GESTÃO DE VAGAS":
    st.subheader("Painel de Vagas")
    with st.expander("➕ CRIAR NOVA VAGA", expanded=False):
        with st.form("f_vaga"):
            n_v = st.text_input("Nome da Vaga")
            a_v = st.selectbox("Departamento", ["Comercial", "Operações", "Tecnologia", "RH", "Marketing"])
            if st.form_submit_button("CONFIRMAR CRIAÇÃO"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO vagas (nome_vaga, area, status_vaga) VALUES (:n, :a, 'Aberta')"), {"n": n_v, "a": a_v})
                    conn.commit()
                st.rerun()

    st.divider()
    df_v = carregar_vagas()
    for _, row in df_v.iterrows():
        col1, col2 = st.columns([4, 1])
        col1.info(f"**{row['nome_vaga']}** | {row['area']}")
        if col2.button("🗑️ APAGAR", key=f"del_{row['nome_vaga']}"):
            with engine.connect() as conn:
                conn.execute(text("DELETE FROM candidatos WHERE vaga_vinculada = :v"), {"v": row['nome_vaga']})
                conn.execute(text("DELETE FROM vagas WHERE nome_vaga = :v"), {"v": row['nome_vaga']})
                conn.commit()
            st.rerun()

# --- 8. FLUXO (SEM PLANILHA) ---
elif menu == "⚙️ FLUXO DE CANDIDATOS":
    df_vagas = carregar_vagas()
    if df_vagas.empty:
        st.warning("Cadastre uma vaga primeiro.")
    else:
        v_sel = st.selectbox("Selecione a Vaga:", df_vagas["nome_vaga"].tolist())
        
        # Adicionar Candidato rápido
        with st.popover("➕ Adicionar Candidato nesta Vaga"):
            nome_novo = st.text_input("Nome completo")
            if st.button("Salvar Candidato"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral) VALUES (:c, :v, 'Vaga aberta')"), {"c": nome_novo, "v": v_sel})
                    conn.commit()
                st.rerun()

        st.divider()
        
        # ACOMPANHAMENTO EM CARDS
        df_c = carregar_candidatos_vaga(v_sel)
        if df_c.empty:
            st.info("Nenhum candidato nesta vaga.")
        else:
            # Lista de status para o seletor
            opcoes_status = ["Vaga aberta", "Triagem", "Entrevista RH", "Entrevista gestor", "Solicitação de documentos", "Solicitação de contratos", "Finalizada"]
            
            for idx, cand in df_c.iterrows():
                # Criando um Card visual
                with st.container():
                    st.markdown(f"""
                    <div class="candidate-card">
                        <div class="candidate-name">{cand['candidato']}</div>
                        <div class="candidate-status">{cand['status_geral']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Controles dentro do card (usando colunas para economizar espaço)
                    c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 1])
                    
                    novo_status = c1.selectbox("Mudar Status", opcoes_status, index=opcoes_status.index(cand['status_geral']), key=f"st_{cand['id']}")
                    data_rh = c2.date_input("📅 Entrev. RH", value=cand['entrevista_rh'], key=f"rh_{cand['id']}")
                    data_gestor = c3.date_input("📅 Entrev. Gestor", value=cand['entrevista_gestor'], key=f"gs_{cand['id']}")
                    
                    # Botões de salvar/excluir pequenos
                    if c4.button("💾", key=f"sv_{cand['id']}", help="Salvar Alterações"):
                        with engine.connect() as conn:
                            conn.execute(text("""
                                UPDATE candidatos SET status_geral = :s, entrevista_rh = :rh, entrevista_gestor = :gs 
                                WHERE id = :id
                            """), {"s": novo_status, "rh": data_rh, "gs": data_gestor, "id": cand['id']})
                            conn.commit()
                        st.toast(f"Dados de {cand['candidato']} atualizados!")
                    
                    if c4.button("🗑️", key=f"del_{cand['id']}", help="Excluir Candidato"):
                        with engine.connect() as conn:
                            conn.execute(text("DELETE FROM candidatos WHERE id = :id"), {"id": cand['id']})
                            conn.commit()
                        st.rerun()
                    
                    st.markdown("<br>", unsafe_allow_html=True)
