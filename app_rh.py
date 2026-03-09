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
    except:
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
        st.error(f"Erro: {e}")
        return False

@st.cache_data(ttl=60)
def carregar_dados(tabela):
    return pd.read_sql(f"SELECT * FROM {tabela}", engine)

# --- 4. INICIALIZAÇÃO DO BANCO ---
def inicializar_banco():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vagas (id SERIAL PRIMARY KEY, nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE, data_fechamento DATE);
            CREATE TABLE IF NOT EXISTS candidatos (id SERIAL PRIMARY KEY, candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, historico TEXT, motivo_perda TEXT, envio_proposta BOOLEAN DEFAULT FALSE, solic_documentos BOOLEAN DEFAULT FALSE, solic_contrato BOOLEAN DEFAULT FALSE, solic_acessos BOOLEAN DEFAULT FALSE);
            CREATE TABLE IF NOT EXISTS contratos_estagio (id SERIAL PRIMARY KEY, estagiario TEXT, instituicao TEXT, data_inicio DATE, data_fim DATE, status_contrato TEXT);
        """))
inicializar_banco()

# --- 5. SIDEBAR COM MENUS SEPARADOS (RH E DP) ---
with st.sidebar:
    # Mostra o logo ou título
    caminho_logo = "logo.png"
    if os.path.exists(caminho_logo):
        st.image(caminho_logo, use_container_width=True)
    else:
        st.markdown("## 🏢 RH ETUS")
    
    st.divider()
    
    # 1º Nível: Seleção de Área
    area_selecionada = st.selectbox("GERENCIAMENTO", ["RH - Recrutamento", "DP - Departamento Pessoal"])
    
    st.divider()

    # 2º Nível: Menu Dinâmico
    if area_selecionada == "RH - Recrutamento":
        st.subheader("MENU RH")
        menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])
    else:
        st.subheader("MENU DP")
        menu = st.radio("NAVEGAÇÃO", ["🎓 ESTAGIÁRIOS", "📄 OUTROS DOCUMENTOS"]) # Adicionei um placeholder para crescermos depois

# Título dinâmico no corpo do app
st.markdown(f'<div class="header-rh">{menu}</div>', unsafe_allow_html=True)

# --- 6. LÓGICA DAS ABAS ---

# --- MÓDULO DP ---
if menu == "🎓 ESTAGIÁRIOS":
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("📝 Novo Contrato")
        with st.form("form_estagio", clear_on_submit=True):
            nome = st.text_input("Nome do Estagiário")
            inst = st.text_input("Instituição de Ensino")
            d_ini = st.date_input("Início", value=date.today())
            d_fim = st.date_input("Término")
            if st.form_submit_button("CADASTRAR"):
                executar_sql("INSERT INTO contratos_estagio (estagiario, instituicao, data_inicio, data_fim, status_contrato) VALUES (:n, :i, :di, :df, 'Ativo')",
                             {"n": nome, "i": inst, "di": d_ini, "df": d_fim})
                st.rerun()
    with col2:
        st.subheader("📅 Gestão de Vencimentos")
        df_est = carregar_dados("contratos_estagio")
        if not df_est.empty:
            for _, row in df_est.iterrows():
                d_fim_val = pd.to_datetime(row['data_fim']).date()
                dias = (d_fim_val - date.today()).days
                status_txt, css = ("🔴 VENCIDO", "status-vencido") if dias < 0 else (f"🟡 VENCE EM {dias} DIAS", "status-alerta") if dias <= 30 else ("🟢 EM DIA", "status-ok")
                with st.expander(f"{row['estagiario']} - {row['instituicao']}"):
                    st.markdown(f"**Status:** <span class='{css}'>{status_txt}</span>", unsafe_allow_html=True)
                    if st.button("Remover", key=f"del_{row['id']}"):
                        executar_sql("DELETE FROM contratos_estagio WHERE id=:id", {"id": row['id']})
                        st.rerun()

elif menu == "📄 OUTROS DOCUMENTOS":
    st.info("Espaço reservado para futuras funcionalidades do DP (ex: Férias, Folha de Pagamento).")

# --- MÓDULO RH ---
elif menu == "📊 INDICADORES":
    df_v = carregar_dados("vagas")
    df_c = carregar_dados("candidatos")
    if not df_v.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 VAGAS ATIVAS", len(df_v[df_v['status_vaga'] == 'Aberta']))
        c3.metric("👥 CANDIDATOS ATIVOS", len(df_c[~df_c['status_geral'].isin(['Finalizada', 'Perda'])]) if not df_c.empty else 0)

elif menu == "🏢 VAGAS":
    with st.expander("➕ NOVA VAGA"):
        with st.form("n_vaga"):
            nv = st.text_input("Nome da Vaga"); gv = st.text_input("Gestor")
            if st.form_submit_button("CRIAR"):
                executar_sql("INSERT INTO vagas (nome_vaga, status_vaga, gestor, data_abertura) VALUES (:n, 'Aberta', :g, :d)", {"n": nv, "g": gv, "d": date.today()}); st.rerun()

elif menu == "⚙️ CANDIDATOS":
    df_vagas = carregar_dados("vagas")
    df_c = carregar_dados("candidatos")
    if not df_vagas.empty:
        for _, v_row in df_vagas.iterrows():
            cands = df_c[df_c['vaga_vinculada'] == v_row['nome_vaga']]
            if not cands.empty:
                st.markdown(f'<div class="vaga-header">🏢 VAGA: {v_row["nome_vaga"].upper()}</div>', unsafe_allow_html=True)
                for _, cand in cands.iterrows():
                    st.write(f"👤 {cand['candidato']} - {cand['status_geral']}")

elif menu == "🚀 ONBOARDING":
    st.write("Módulo de Onboarding para candidatos aprovados.")
