import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
import os
from datetime import datetime

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="RH ETUS - Gestão Pro", layout="wide", page_icon="🟢")

# --- 2. CONEXÃO ---
try:
    DB_URL = st.secrets["postgres"]["url"]
    engine = create_engine(DB_URL, connect_args={"sslmode": "require"})
except KeyError:
    st.error("Erro nos Secrets.")
    st.stop()

# --- 3. INICIALIZAÇÃO DE BANCO ---
def inicializar_banco():
    with engine.connect() as conn:
        # Colunas novas para VAGAS
        vagas_cols = {"gestor": "TEXT", "data_abertura": "DATE", "data_fechamento": "DATE"}
        for col, tipo in vagas_cols.items():
            try:
                conn.execute(text(f"ALTER TABLE vagas ADD COLUMN IF NOT EXISTS {col} {tipo}"))
                conn.commit()
            except: pass
        
        # Colunas para ONBOARDING e CULTURA
        try:
            conn.execute(text("ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS entrevista_cultura DATE"))
            conn.commit()
        except: pass

        onboarding_cols = ["envio_proposta", "solic_documentos", "solic_fotos", "solic_contrato", "solic_acessos", "cad_rh_gestor", "cad_starbem", "cad_dasa", "cad_avus", "agend_onboarding", "envio_gestor"]
        for col in onboarding_cols:
            try:
                conn.execute(text(f"ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS {col} BOOLEAN DEFAULT FALSE"))
                conn.commit()
            except: pass

inicializar_banco()

# --- 4. CSS (DESIGN MINIMALISTA APENAS TEXTO) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    html, body, [class*="css"], [data-testid="stSidebar"] { font-family: 'Space Grotesk', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #0E1117 !important; }
    [data-testid="stSidebar"] [data-test="stWidgetSelectionColumn"] { display: none !important; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] { background-color: transparent !important; border: none !important; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label { background-color: transparent !important; border: none !important; box-shadow: none !important; padding: 8px 0px !important; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] p { color: #777777 !important; font-size: 18px !important; transition: color 0.3s; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] input:checked + div p { color: #8DF768 !important; font-weight: 700 !important; font-size: 20px !important; }
    .header-rh { font-size: 42px; font-weight: 700; color: #8DF768; margin-bottom: 30px; border-left: 10px solid #151514; padding-left: 15px; }
    .candidate-card { background-color: #1E1E1E; padding: 20px; border-radius: 12px; border: 1px solid #333; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. FUNÇÕES DE CARGA ---
def carregar_vagas():
    df = pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)
    return df

def carregar_candidatos_vaga(v_nome):
    query = text("SELECT * FROM candidatos WHERE vaga_vinculada = :v ORDER BY id DESC")
    return pd.read_sql(query, engine, params={"v": v_nome})

def carregar_aprovados():
    return pd.read_sql("SELECT * FROM candidatos WHERE status_geral = 'Finalizada' OR aprovacao_final = 'Sim' ORDER BY candidato", engine)

# --- 6. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    menu = st.radio("NAVEGAÇÃO", ["📊 DASHBOARD", "🏢 GESTÃO DE VAGAS", "⚙️ FLUXO DE CANDIDATOS", "🚀 ONBOARDING"])

st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- 7. DASHBOARD ---
if menu == "📊 DASHBOARD":
    df_c = pd.read_sql("SELECT * FROM candidatos", engine)
    if not df_c.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 CANDIDATOS ATIVOS", len(df_c))
        c2.metric("✅ CONTRATAÇÕES", len(df_c[df_c["status_geral"] == "Finalizada"]))
        c3.metric("🏢 VAGAS NO SISTEMA", len(pd.read_sql("SELECT * FROM vagas", engine)))
        st.divider()
        fig = px.pie(df_c, names="status_geral", hole=.4, color_discrete_sequence=['#8DF768', '#4A4A4A', '#222222'])
        st.plotly_chart(fig, use_container_width=True)

# --- 8. GESTÃO DE VAGAS ---
elif menu == "🏢 GESTÃO DE VAGAS":
    st.subheader("Painel de Vagas")
    with st.expander("➕ CRIAR NOVA VAGA"):
        with st.form("f_vaga"):
            n_v = st.text_input("Nome da Vaga")
            a_v = st.selectbox("Departamento", ["Comercial", "Operações", "Tecnologia", "RH", "Marketing"])
            g_v = st.text_input("Gestor Responsável")
            d_ab = st.date_input("Data Abertura", value=datetime.now())
            if st.form_submit_button("CONFIRMAR"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO vagas (nome_vaga, area, status_vaga, gestor, data_abertura) VALUES (:n, :a, 'Aberta', :g, :d)"), 
                                 {"n": n_v, "a": a_v, "g": g_v, "d": d_ab})
                    conn.commit()
                st.rerun()

    st.divider()
    df_v = carregar_vagas()
    for _, row in df_v.iterrows():
        # Lógica de Identificador Seguro para evitar KeyError
        v_id = row['id'] if 'id' in df_v.columns else None
        v_nome_original = row['nome_vaga']
        v_key = v_id if v_id is not None else v_nome_original
        
        d_ini = pd.to_datetime(row['data_abertura'])
        d_fim = pd.to_datetime(row['data_fechamento']) if pd.notnull(row['data_fechamento']) else datetime.now()
        dias = (d_fim - d_ini).days if pd.notnull(d_ini) else 0
        
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 2, 1])
            c1.markdown(f"**{row['nome_vaga']}** ({row['area']})\n\n👤 Gestor: {row.get('gestor', 'N/A')}")
            c2.write(f"⏱️ Aberta há: {dias} dias\n\n📅 Início: {row['data_abertura']}")
            
            if c3.button("📝 EDITAR", key=f"edbtn_{v_key}"):
                st.session_state[f"edit_vaga_{v_key}"] = True
            
            if st.session_state.get(f"edit_vaga_{v_key}"):
                with st.form(f"form_ed_{v_key}"):
                    novo_n = st.text_input("Nome", value=row['nome_vaga'])
                    novo_g = st.text_input("Gestor", value=row.get('gestor', ''))
                    novo_s = st.selectbox("Status", ["Aberta", "Fechada", "Pausada"], index=0)
                    df_ab = st.date_input("Abertura", value=row['data_abertura'] if pd.notnull(row['data_abertura']) else datetime.now())
                    df_fc = st.date_input("Fechamento", value=row['data_fechamento'] if pd.notnull(row['data_fechamento']) else None)
                    
                    if st.form_submit_button("SALVAR"):
                        with engine.connect() as conn:
                            # Se tivermos ID, usamos ID. Se não, usamos o Nome original para localizar o registro.
                            if v_id is not None:
                                conn.execute(text("UPDATE vagas SET nome_vaga=:n, gestor=:g, status_vaga=:s, data_abertura=:da, data_fechamento=:df WHERE id=:id"),
                                             {"n": novo_n, "g": novo_g, "s": novo_s, "da": df_ab, "df": df_fc, "id": v_id})
                            else:
                                conn.execute(text("UPDATE vagas SET nome_vaga=:n, gestor=:g, status_vaga=:s, data_abertura=:da, data_fechamento=:df WHERE nome_vaga=:nome_orig"),
                                             {"n": novo_n
