import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from datetime import datetime

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RH ETUS - Gestão Pro", layout="wide", page_icon="🏈")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    html, body, [class*="css"], [data-testid="stSidebar"] { font-family: 'Space Grotesk', sans-serif !important; }
    .header-rh { font-size: 42px; font-weight: 700; color: #8DF768; margin-bottom: 30px; border-left: 10px solid #151514; padding-left: 15px; display: flex; align-items: center; }
    .logo-img { margin-right: 20px; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE BANCO DE DADOS (SINGLETON) ---
@st.cache_resource
def get_engine():
    try:
        DB_URL = st.secrets["postgres"]["url"]
        return create_engine(DB_URL, pool_size=5, max_overflow=10, connect_args={"sslmode": "require"})
    except KeyError:
        st.error("Erro: 'postgres.url' não encontrado nos Secrets.")
        st.stop()

engine = get_engine()

# --- 3. FUNÇÕES DE DADOS (COM CACHE) ---
@st.cache_data(ttl=300)
def carregar_vagas():
    return pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)

@st.cache_data(ttl=300)
def carregar_candidatos():
    return pd.read_sql("SELECT * FROM candidatos", engine)

def executar_sql(query, params=None):
    try:
        with engine.begin() as conn:
            conn.execute(text(query), params or {})
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro na operação: {e}")
        return False

# --- 4. INICIALIZAÇÃO DO BANCO ---
def inicializar_banco():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vagas (
                id SERIAL PRIMARY KEY, 
                nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE
            );
            CREATE TABLE IF NOT EXISTS candidatos (
                id SERIAL PRIMARY KEY, 
                candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, historico TEXT,
                envio_proposta BOOLEAN DEFAULT FALSE, solic_documentos BOOLEAN DEFAULT FALSE,
                solic_contrato BOOLEAN DEFAULT FALSE, solic_acessos BOOLEAN DEFAULT FALSE
            );
        """))
        try: conn.execute(text("ALTER TABLE vagas ADD COLUMN IF NOT EXISTS id SERIAL;"))
        except: pass
        try: conn.execute(text("ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS id SERIAL;"))
        except: pass

inicializar_banco()

# --- 5. SIDEBAR E NAVEGAÇÃO ---
with st.sidebar:
    # --- INSIRA O CAMINHO DA SUA LOGO AQUI ---
    # st.image("caminho/para/sua/logo.png", width=150) 
    st.title("🏈 RH ETUS")
    st.divider()
    menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])

# --- HEADER COM LOGO ---
col_logo, col_titulo = st.columns([1, 5])
with col_titulo:
    st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)
# with col_logo:
#     st.image("caminho/para/sua/logo.png", width=80)

# --- 6. ABA: INDICADORES ---
if menu == "📊 INDICADORES":
    df_v = carregar_vagas()
    df_c = carregar_candidatos()
    
    if not df_v.empty:
        hoje = pd.Timestamp(datetime.now().date())
        df_v['data_abertura'] = pd.to_datetime(df_v['data_abertura'])
        v_ativas = df_v[df_v['status_vaga'] == 'Aberta'].copy()
        v_ativas['aging'] = v_ativas['data_abertura'].apply(lambda x: (hoje - x).days if pd.notnull(x) else 0)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 VAGAS ABERTAS", len(v_ativas))
        c2.metric("⏱️ AGING MÉDIO", f"{int(v_ativas['aging'].mean()) if not v_ativas.empty else 0} dias")
        c3.metric("👥 CANDIDATOS ATIVOS", len(df_c[df_c['status_geral'] != 'Finalizada']) if not df_c.empty else 0)

        st.subheader("🕒 Aging por Vaga")
        st.plotly_chart(px.bar(v_ativas, x='aging', y='nome_vaga', orientation='h', color_discrete_sequence=['#8DF768']), use_container_width=True)

# --- 7. ABA: VAGAS ---
elif menu == "🏢 VAGAS":
    with st.expander("➕ CADASTRAR NOVA VAGA"):
        with st.form("n_vaga", clear_on_submit=True):
            nv = st.text_input("Nome da Vaga")
            gv = st.text_input("Gestor Direto")
            av = st.selectbox("Área", ["Comercial", "Operações", "RH", "Tecnologia", "Marketing", "Financeiro"])
            if st.form_submit_button("CRIAR VAGA"):
                if nv:
                    executar_sql("INSERT INTO vagas (nome_vaga, area, status_vaga, gestor, data_abertura) VALUES (:n, :a, 'Aberta', :g, :d)",
                                 {"n": nv, "a": av, "g": gv, "d": datetime.now().date()})
                    st.rerun()

    df_v = carregar_vagas()
    for i, row in df_v.iterrows():
        row_id = row.get('id', i)
        with st.expander(f"🏢 {row['nome_vaga'].upper()} | {row['status_vaga']}"):
            col1, col2 = st.columns([3, 1])
            with col1:
                with st.form(f"ed_v_{row_id}"):
                    eg = st.text_input("Gestor", value=row['gestor'])
                    es = st.selectbox("Status", ["Aberta", "Pausada", "Finalizada"], index=["Aberta", "Pausada", "Finalizada"].index(row['status_vaga']))
                    if st.form_submit_button("SALVAR ALTERAÇÕES"):
                        executar_sql("UPDATE vagas SET gestor=:g, status_vaga=:s WHERE nome_vaga=:n", {"g": eg, "s": es, "n": row['nome_vaga']})
                        st.rerun()
            with col2:
                if st.button("🗑️ EXCLUIR", key=f"del_v_{row_id}", use_container_width=True):
                    executar_sql("DELETE FROM vagas WHERE nome_vaga=:n", {"n": row['nome_vaga']})
                    st.rerun()

# --- 8. ABA: CANDIDATOS ---
elif menu == "⚙️ CANDIDATOS":
    df_vagas = carregar_vagas()
    df_c = carregar_candidatos()

    with st.expander("➕ ADICIONAR NOVO CANDIDATO"):
        if not df_vagas.empty:
            with st.form("add_c", clear_on_submit=True):
                cn = st.text_input("Nome do Candidato")
                cv = st.selectbox("Vincular à Vaga", df_vagas["nome_vaga"].tolist())
                if st.form_submit_button("CADASTRAR"):
                    if cn:
                        h = f"➔ {datetime.now().strftime('%d/%m/%Y')}: Cadastro inicial"
                        executar_sql("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral, historico) VALUES (:n, :v, 'Triagem', :h)",
                                     {"n": cn, "v": cv, "h": h})
                        st.rerun()

    if not df_c.empty:
        for i, cand in df_c.iterrows():
            cand_id = cand.get('id', i)
            with st.expander(f"👤 {cand['candidato']} ({cand['status_geral']})"):
                etapas = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada"]
                idx_etapa = etapas.index(cand['status_geral']) if cand['status_geral'] in etapas else 0
                novo_st = st.selectbox("Mover Etapa", etapas, index=idx_etapa, key=f"st_{cand_id}")
                
                if st.button("ATUALIZAR STATUS", key=f"up_{cand_id}"):
                    novo_h = f"➔ {datetime.now().strftime('%d/%m/%Y')}: {novo_st}\n" + (cand['historico'] or "")
                    executar_sql("UPDATE candidatos SET status_geral=:s, historico=:h WHERE candidato=:n", {"s": novo_st, "h": novo_h, "n": cand['candidato']})
                    st.rerun()

# --- 9. ABA: ONBOARDING ---
elif menu == "🚀 ONBOARDING":
    df_on = pd.read_sql("SELECT * FROM candidatos WHERE status_geral = 'Finalizada'", engine)
    if not df_on.empty:
        sel_c = st.selectbox("Selecione o Colaborador:", df_on["candidato"].tolist())
        c_data = df_on[df_on["candidato"] == sel_c].iloc[0]
        items = {"envio_proposta": "✅ Proposta", "solic_documentos": "📄 Documentos", "solic_contrato": "✍️ Contrato", "solic_acessos": "🔑 Acessos"}
        res_on = {}
        cols = st.columns(4)
        for i, (key, label) in enumerate(items.items()):
            res_on[key] = cols[i].checkbox(label, value=bool(c_data.get(key, False)), key=f"chk_{sel_c}_{key}")
        if st.button("SALVAR PROGRESSO"):
            set_query = ", ".join([f"{k}=:{k}" for k in res_on.keys()])
            executar_sql(f"UPDATE candidatos SET {set_query} WHERE candidato=:n", {**res_on, "n": sel_c})
            st.rerun()
