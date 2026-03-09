import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from datetime import datetime, date
import os

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="Gestão ETUS - Pro", layout="wide", page_icon="logo.png")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    html, body, [class*="css"], [data-testid="stSidebar"] { font-family: 'Space Grotesk', sans-serif !important; }
    .header-rh { font-size: 42px; font-weight: 700; color: #8DF768; margin-bottom: 30px; border-left: 10px solid #8DF768; padding-left: 15px; }
    .vaga-header { background-color: rgba(141, 247, 104, 0.2); color: inherit; padding: 10px; border-radius: 5px; margin-top: 20px; margin-bottom: 10px; font-weight: bold; border-left: 5px solid #8DF768; }
    .status-vencido { color: #FF4B4B; font-weight: bold; }
    .status-alerta { color: #FFA500; font-weight: bold; }
    .status-ok { color: #28A745; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE BANCO DE DADOS ---
@st.cache_resource
def get_engine():
    try:
        DB_URL = st.secrets["postgres"]["url"]
        return create_engine(DB_URL, pool_size=5, max_overflow=10, connect_args={"sslmode": "require"})
    except KeyError:
        st.error("Erro: 'postgres.url' não encontrado nos Secrets.")
        st.stop()

engine = get_engine()

# --- 3. FUNÇÕES DE DADOS ---
def executar_sql(query, params=None):
    try:
        with engine.begin() as conn:
            conn.execute(text(query), params or {})
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro na operação: {e}")
        return False

@st.cache_data(ttl=60)
def carregar_dados(tabela):
    return pd.read_sql(f"SELECT * FROM {tabela}", engine)

# --- 4. INICIALIZAÇÃO DO BANCO (COM NOVA TABELA DE CONTRATOS) ---
def inicializar_banco():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vagas (
                id SERIAL PRIMARY KEY, nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE, data_fechamento DATE
            );
            CREATE TABLE IF NOT EXISTS candidatos (
                id SERIAL PRIMARY KEY, candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, historico TEXT, motivo_perda TEXT,
                envio_proposta BOOLEAN DEFAULT FALSE, solic_documentos BOOLEAN DEFAULT FALSE, solic_contrato BOOLEAN DEFAULT FALSE, solic_acessos BOOLEAN DEFAULT FALSE
            );
            CREATE TABLE IF NOT EXISTS contratos_estagio (
                id SERIAL PRIMARY KEY, estagiario TEXT, instituicao TEXT, data_inicio DATE, data_fim DATE, status_contrato TEXT
            );
        """))
inicializar_banco()

# --- 5. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING", "🎓 ESTAGIÁRIOS"])

st.markdown(f'<div class="header-rh">{"GESTÃO DE ESTÁGIOS" if menu == "🎓 ESTAGIÁRIOS" else "RH ETUS"}</div>', unsafe_allow_html=True)

# --- ABA: ESTAGIÁRIOS (NOVO MÓDULO) ---
if menu == "🎓 ESTAGIÁRIOS":
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📝 Novo Contrato")
        with st.form("form_estagio", clear_on_submit=True):
            nome = st.text_input("Nome do Estagiário")
            inst = st.text_input("Instituição de Ensino")
            d_ini = st.date_input("Início do Contrato", value=date.today())
            d_fim = st.date_input("Término do Contrato")
            if st.form_submit_button("CADASTRAR CONTRATO"):
                executar_sql("INSERT INTO contratos_estagio (estagiario, instituicao, data_inicio, data_fim, status_contrato) VALUES (:n, :i, :di, :df, 'Ativo')",
                             {"n": nome, "i": inst, "di": d_ini, "df": d_fim})
                st.rerun()

    with col2:
        st.subheader("📅 Gestão de Vencimentos")
        df_est = carregar_dados("contratos_estagio")
        
        if not df_est.empty:
            df_est['data_fim'] = pd.to_datetime(df_est['data_fim']).dt.date
            hoje = date.today()
            
            for _, row in df_est.iterrows():
                dias_para_vencer = (row['data_fim'] - hoje).days
                
                # Lógica de Alerta
                if dias_para_vencer < 0:
                    status_txt = "🔴 VENCIDO"
                    css_class = "status-vencido"
                elif dias_para_vencer <= 30:
                    status_txt = f"🟡 VENCE EM {dias_para_vencer} DIAS"
                    css_class = "status-alerta"
                else:
                    status_txt = "🟢 EM DIA"
                    css_class = "status-ok"
                
                with st.expander(f"{row['estagiario']} - {row['instituicao']}"):
                    c_a, c_b = st.columns(2)
                    c_a.write(f"**Término:** {row['data_fim'].strftime('%d/%m/%Y')}")
                    c_a.markdown(f"**Status:** <span class='{css_class}'>{status_txt}</span>", unsafe_allow_html=True)
                    
                    if c_b.button("Remover Registro", key=f"del_est_{row['id']}"):
                        executar_sql("DELETE FROM contratos_estagio WHERE id=:id", {"id": row['id']})
                        st.rerun()
        else:
            st.info("Nenhum contrato de estágio registrado.")

# --- (RESTAURANTE DO CÓDIGO RH MANTIDO ABAIXO) ---
elif menu == "📊 INDICADORES":
    df_v = carregar_dados("vagas")
    df_c = carregar_dados("candidatos")
    if not df_v.empty:
        df_v['data_abertura'] = pd.to_datetime(df_v['data_abertura'], errors='coerce')
        df_v['data_fechamento'] = pd.to_datetime(df_v['data_fechamento'], errors='coerce')
        df_fechadas = df_v[df_v['status_vaga'] == 'Finalizada'].copy().dropna(subset=['data_abertura', 'data_fechamento'])
        avg_tth = int((df_fechadas['data_fechamento'] - df_fechadas['data_abertura']).dt.days.mean()) if not df_fechadas.empty else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 VAGAS ATIVAS", len(df_v[df_v['status_vaga'] == 'Aberta']))
        c2.metric("⏱️ TIME-TO-HIRE MÉDIO", f"{avg_tth} dias")
        c3.metric("👥 CANDIDATOS ATIVOS", len(df_c[~df_c['status_geral'].isin(['Finalizada', 'Perda'])]) if not df_c.empty else 0)

elif menu == "🏢 VAGAS":
    with st.expander("➕ CADASTRAR NOVA VAGA"):
        with st.form("n_vaga", clear_on_submit=True):
            nv = st.text_input("Nome da Vaga"); gv = st.text_input("Gestor")
            av = st.selectbox("Área", ["Comercial", "Operações", "RH", "Tecnologia", "Marketing", "Financeiro"])
            if st.form_submit_button("CRIAR"):
                executar_sql("INSERT INTO vagas (nome_vaga, area, status_vaga, gestor, data_abertura) VALUES (:n, :a, 'Aberta', :g, :d)", {"n": nv, "a": av, "g": gv, "d": date.today()}); st.rerun()
    df_v = carregar_dados("vagas")
    for _, row in df_v.iterrows():
        with st.expander(f"🏢 {row['nome_vaga'].upper()}"):
            with st.form(f"ed_{row['id']}"):
                es = st.selectbox("Status", ["Aberta", "Pausada", "Finalizada"], index=["Aberta", "Pausada", "Finalizada"].index(row['status_vaga']))
                if st.form_submit_button("SALVAR"):
                    df = date.today() if es == "Finalizada" else None
                    executar_sql("UPDATE vagas SET status_vaga=:s, data_fechamento=:df WHERE id=:id", {"s": es, "df": df, "id": row['id']}); st.rerun()

elif menu == "⚙️ CANDIDATOS":
    df_vagas = carregar_dados("vagas")
    df_c = carregar_dados("candidatos")
    with st.expander("➕ ADICIONAR CANDIDATO"):
        if not df_vagas.empty:
            with st.form("add_c"):
                cn = st.text_input("Nome"); cv = st.selectbox("Vaga", df_vagas["nome_vaga"].tolist())
                if st.form_submit_button("CADASTRAR"):
                    executar_sql("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral) VALUES (:n, :v, 'Triagem')", {"n": cn, "v": cv}); st.rerun()
    if not df_vagas.empty:
        for _, v_row in df_vagas.iterrows():
            cands = df_c[df_c['vaga_vinculada'] == v_row['nome_vaga']]
            if not cands.empty:
                st.markdown(f'<div class="vaga-header">🏢 VAGA: {v_row["nome_vaga"].upper()}</div>', unsafe_allow_html=True)
                for _, cand in cands.iterrows():
                    with st.expander(f"👤 {cand['candidato']} ({cand['status_geral']})"):
                        novo_st = st.selectbox("Status", ["Triagem", "Entrevista", "Teste", "Finalizada"], key=f"s_{cand['id']}")
                        if st.button("ATUALIZAR", key=f"u_{cand['id']}"):
                            executar_sql("UPDATE candidatos SET status_geral=:s WHERE id=:id", {"s": novo_st, "id": cand['id']}); st.rerun()

elif menu == "🚀 ONBOARDING":
    df_on = pd.read_sql("SELECT * FROM candidatos WHERE status_geral = 'Finalizada'", engine)
    if not df_on.empty:
        sel_c = st.selectbox("Colaborador:", df_on["candidato"].tolist())
        st.info(f"Gerencie os documentos de entrada para {sel_c}")
