import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from datetime import datetime

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="RH ETUS - Cloud Database", layout="wide", page_icon="🟢")

# --- 2. CONEXÃO COM POSTGRESQL ---
# No Streamlit Cloud, você cadastrará a URL em: Settings -> Secrets
# Formato da URL: postgresql://usuario:senha@host:porta/nome_do_banco
DB_URL = st.secrets["postgres"]["url"]
engine = create_engine(DB_URL)

def inicializar_banco():
    with engine.connect() as conn:
        # Criar Tabela de Vagas
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vagas (
                nome_vaga TEXT PRIMARY KEY,
                area TEXT,
                status_vaga TEXT
            )
        """))
        # Criar Tabela de Candidatos
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS candidatos (
                id SERIAL PRIMARY KEY,
                candidato TEXT,
                vaga_vinculada TEXT,
                status_geral TEXT,
                entrevista_rh DATE,
                entrevista_gestor DATE,
                teste_tecnico TEXT,
                solicitar_doc BOOLEAN DEFAULT FALSE,
                foto_curiosidade BOOLEAN DEFAULT FALSE,
                contrato BOOLEAN DEFAULT FALSE,
                equipamentos BOOLEAN DEFAULT FALSE,
                cadastro_rh_gestor BOOLEAN DEFAULT FALSE,
                data_inicio DATE,
                aprovacao_final TEXT
            )
        """))
        conn.commit()

def carregar_vagas():
    return pd.read_sql("SELECT * FROM vagas", engine)

def carregar_candidatos():
    df = pd.read_sql("SELECT * FROM candidatos", engine)
    # Converter datas de volta para objeto date do python
    for col in ["entrevista_rh", "entrevista_gestor", "data_inicio"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col]).dt.date
    return df

# Inicializar Tabelas
inicializar_banco()

# --- 3. CSS IDENTIDADE ETUS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #3A3A3A !important; }
    .header-rh { font-size: 48px; font-weight: 700; color: #8DF768; border-left: 15px solid #151514; padding-left: 20px; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. SIDEBAR E NAVEGAÇÃO ---
with st.sidebar:
    menu = st.radio("", ["📊 DASHBOARD", "🏢 VAGAS", "⚙️ FLUXO"], label_visibility="collapsed")

st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- 5. LÓGICA DE INTERFACE ---

if menu == "📊 DASHBOARD":
    df_c = carregar_candidatos()
    df_v = carregar_vagas()
    
    if not df_c.empty:
        st.markdown("<style>[data-testid='stMetricValue'] { color: #8DF768 !important; }</style>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 NO FUNIL", len(df_c))
        c2.metric("✅ CONTRATADOS", len(df_c[df_c["aprovacao_final"] == "Sim"]))
        c3.metric("🏢 VAGAS ATIVAS", len(df_v[df_v["status_vaga"] == "Aberta"]))
        
        st.divider()
        fig = px.bar(df_c["status_geral"].value_counts().reset_index(), x="status_geral", y="count", color_discrete_sequence=['#8DF768'])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum dado no banco de dados ainda.")

elif menu == "🏢 VAGAS":
    st.subheader("Gerenciar Vagas")
    with st.form("add_vaga"):
        nome = st.text_input("Nome da Vaga")
        if st.form_submit_button("CADASTRAR"):
            if nome:
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO vagas (nome_vaga, area, status_vaga) VALUES (:n, :a, :s) ON CONFLICT DO NOTHING"), 
                                 {"n": nome, "a": "Geral", "s": "Aberta"})
                    conn.commit()
                st.rerun()

    df_vagas = carregar_vagas()
    v_ed = st.data_editor(df_vagas, num_rows="dynamic", use_container_width=True, key="v_edit")
    
    if st.button("SALVAR ALTERAÇÕES/EXCLUSÕES VAGAS"):
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM vagas")) # Limpa para resalvar o estado do editor
            v_ed.to_sql("vagas", engine, if_exists="append", index=False)
            conn.commit()
        st.success("Banco de dados atualizado!")

elif menu == "⚙️ FLUXO":
    df_vagas = carregar_vagas()
    if df_vagas.empty:
        st.warning("Cadastre uma vaga primeiro.")
    else:
        v_list = df_vagas["nome_vaga"].unique().tolist()
        tabs = st.tabs(v_list)
        df_all = carregar_candidatos()

        for i, v_nome in enumerate(v_list):
            with tabs[i]:
                df_v = df_all[df_all["vaga_vinculada"] == v_nome].copy()
                
                if st.button(f"➕ NOVO CANDIDATO", key=f"n_{v_nome}"):
                    with engine.connect() as conn:
                        conn.execute(text("""
                            INSERT INTO candidatos (candidato, vaga_vinculada, status_geral, aprovacao_final) 
                            VALUES ('Nome', :v, 'Vaga aberta', 'Não')
                        """), {"v": v_nome})
                        conn.commit()
                    st.rerun()

                df_ed = st.data_editor(
                    df_v, key=f"ed_{v_nome}", use_container_width=True,
                    column_config={
                        "status_geral": st.column_config.SelectboxColumn("Status", options=["Vaga aberta", "Triagem", "Entrevista RH", "Entrevista gestor", "Solicitação de documentos", "Solicitação de contratos", "Finalizada"]),
                        "entrevista_rh": st.column_config.DateColumn("📅 RH"),
                        "entrevista_gestor": st.column_config.DateColumn("📅 Gestor"),
                        "data_inicio": st.column_config.DateColumn("🚀 Início"),
                        "aprovacao_final": st.column_config.SelectboxColumn("Aprovado?", options=["Sim", "Não"])
                    }
                )
                
                if st.button("💾 SALVAR FLUXO", key=f"sv_{v_nome}"):
                    with engine.connect() as conn:
                        # Deleta os registros antigos dessa vaga e insere os novos editados
                        conn.execute(text("DELETE FROM candidatos WHERE vaga_vinculada = :v"), {"v": v_nome})
                        df_ed.to_sql("candidatos", engine, if_exists="append", index=False)
                        conn.commit()
                    st.success("Salvo no Postgres!")
                    st.rerun()
