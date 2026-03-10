import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from datetime import datetime, date
import os

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RH ETUS - Gestão Pro", layout="wide", page_icon="logo.png")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    html, body, [class*="css"], [data-testid="stSidebar"] { font-family: 'Space Grotesk', sans-serif !important; }
    .header-rh { font-size: 42px; font-weight: 700; color: #8DF768; margin-bottom: 30px; border-left: 10px solid #8DF768; padding-left: 15px; }
    .vaga-header { background-color: rgba(141, 247, 104, 0.2); padding: 12px; border-radius: 8px; margin-top: 20px; font-weight: bold; border-left: 5px solid #8DF768; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE BANCO DE DADOS ---
@st.cache_resource
def get_engine():
    try:
        DB_URL = st.secrets["postgres"]["url"]
        return create_engine(DB_URL, pool_size=10, max_overflow=20, connect_args={"sslmode": "require"})
    except Exception as e:
        st.error(f"Erro de conexão: {e}"); st.stop()

engine = get_engine()

# --- 3. FUNÇÕES DE APOIO ---
def executar_sql(query, params=None):
    try:
        with engine.begin() as conn:
            conn.execute(text(query), params or {})
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro SQL: {e}"); return False

@st.cache_data(ttl=1)
def carregar_dados(tabela):
    try:
        with engine.connect() as conn:
            return pd.read_sql(text(f"SELECT * FROM {tabela} ORDER BY id DESC"), conn)
    except:
        return pd.DataFrame()

# --- 4. BANCO DE DADOS (INIT EXPANDIDO) ---
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS vagas (id SERIAL PRIMARY KEY, nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE, data_fechamento DATE);
        CREATE TABLE IF NOT EXISTS candidatos (id SERIAL PRIMARY KEY, candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, arquivo_cv BYTEA, envio_proposta BOOLEAN DEFAULT FALSE, solic_documentos BOOLEAN DEFAULT FALSE, solic_contrato BOOLEAN DEFAULT FALSE, solic_acessos BOOLEAN DEFAULT FALSE);
        CREATE TABLE IF NOT EXISTS contratos_estagio (id SERIAL PRIMARY KEY, estagiario TEXT, instituicao TEXT, data_inicio DATE, data_fim DATE, time_equipe TEXT, solic_contrato_dp BOOLEAN DEFAULT FALSE, assina_etus BOOLEAN DEFAULT FALSE, assina_faculdade BOOLEAN DEFAULT FALSE, envio_juridico BOOLEAN DEFAULT FALSE);
        CREATE TABLE IF NOT EXISTS colaboradores (
            id SERIAL PRIMARY KEY, nome TEXT, tipo TEXT, time_equipe TEXT, data_admissao DATE,
            status_rh_gestor BOOLEAN DEFAULT FALSE, status_starbem BOOLEAN DEFAULT FALSE, 
            status_dasa BOOLEAN DEFAULT FALSE, status_avus BOOLEAN DEFAULT FALSE, 
            status_amil BOOLEAN DEFAULT FALSE, status_ifood BOOLEAN DEFAULT FALSE,
            status_equipamento BOOLEAN DEFAULT FALSE, ferias_vencimento DATE
        );
        CREATE TABLE IF NOT EXISTS eventos (id SERIAL PRIMARY KEY, titulo TEXT, data_evento DATE, tipo TEXT);
    """))

# --- 5. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    area_sel = st.selectbox("GERENCIAMENTO", ["Recrutamento", "DP & Operações", "Benefícios & Engajamento"])
    
    if area_sel == "Recrutamento":
        menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])
    elif area_sel == "DP & Operações":
        menu = st.radio("NAVEGAÇÃO", ["📊 DASHBOARD DP", "🎓 ESTAGIÁRIOS", "👥 COLABORADORES", "💰 FINANCEIRO & VIAGENS"])
    else:
        menu = st.radio("NAVEGAÇÃO", ["🎁 BENEFÍCIOS", "📅 EVENTOS & COMUNICADOS"])

st.markdown(f'<div class="header-rh">{menu}</div>', unsafe_allow_html=True)

# --- 6. MÓDULO INDICADORES (R&S) ---
if menu == "📊 INDICADORES":
    df_v = carregar_dados("vagas"); df_c = carregar_dados("candidatos")
    if not df_v.empty:
        c1, c2 = st.columns(2)
        c1.metric("📌 VAGAS ATIVAS", len(df_v[df_v['status_vaga'] == 'Aberta']))
        if not df_c.empty:
            st.subheader("📊 Funil de Recrutamento")
            ordem = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada"]
            cnt = df_c['status_geral'].value_counts().reindex(ordem).fillna(0).reset_index()
            st.plotly_chart(px.funnel(cnt, x='count', y='status_geral', color_discrete_sequence=['#8DF768']), use_container_width=True)

# --- 7. MÓDULO VAGAS ---
elif menu == "🏢 VAGAS":
    with st.expander("➕ CADASTRAR NOVA VAGA"):
        with st.form("nv"):
            nv = st.text_input("Vaga"); gv = st.text_input("Gestor"); av = st.selectbox("Área", ["Tecnologia", "Comercial", "Operações", "RH", "Financeiro"])
            if st.form_submit_button("CRIAR"):
                executar_sql("INSERT INTO vagas (nome_vaga, area, status_vaga, gestor, data_abertura) VALUES (:n, :a, 'Aberta', :g, :d)", {"n":nv,"a":av,"g":gv,"d":date.today()}); st.rerun()
    df_v = carregar_dados("vagas")
    for _, row in df_v.iterrows():
        with st.expander(f"🏢 {row['nome_vaga']} ({row['status_vaga']})"):
            st.write(f"**Gestor:** {row['gestor']} | **Abertura:** {row['data_abertura']}")
            if st.button("Fechar Vaga", key=f"fv{row['id']}"):
                executar_sql("UPDATE vagas SET status_vaga='Finalizada', data_fechamento=:d WHERE id=:id", {"d":date.today(), "id":row['id']}); st.rerun()

# --- 8. MÓDULO CANDIDATOS ---
elif menu == "⚙️ CANDIDATOS":
    df_v = carregar_dados("vagas"); df_c = carregar_dados("candidatos")
    with st.expander("➕ NOVO CANDIDATO"):
        with st.form("nc"):
            nc = st.text_input("Nome")
            vnc = st.selectbox("Vaga", df_v['nome_vaga'].tolist() if not df_v.empty else ["Geral"])
            if st.form_submit_button("ADICIONAR"):
                executar_sql("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral) VALUES (:n, :v, 'Triagem')", {"n":nc,"v":vnc}); st.rerun()
    if not df_c.empty:
        for _, cr in df_c.iterrows():
            with st.expander(f"👤 {cr['candidato']} ({cr['vaga_vinculada']})"):
                ns = st.selectbox("Mudar Etapa", ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada", "Perda"], key=f"st{cr['id']}")
                if st.button("Salvar Etapa", key=f"bt{cr['id']}"):
                    executar_sql("UPDATE candidatos SET status_geral=:s WHERE id=:id", {"s":ns,"id":cr['id']}); st.rerun()

# --- 9. MÓDULO ONBOARDING ---
elif menu == "🚀 ONBOARDING":
    df_c = carregar_dados("candidatos")
    aprovados = df_c[df_c['status_geral'] == 'Finalizada']
    for _, r in aprovados.iterrows():
        with st.expander(f"🚀 {r['candidato']}"):
            c1, c2, c3, c4 = st.columns(4)
            p = c1.checkbox("Proposta", value=bool(r['envio_proposta']), key=f"p{r['id']}")
            d = c2.checkbox("Docs", value=bool(r['solic_documentos']), key=f"d{r['id']}")
            c = c3.checkbox("Contrato", value=bool(r['solic_contrato']), key=f"c{r['id']}")
            a = c4.checkbox("Acessos", value=bool(r['solic_acessos']), key=f"a{r['id']}")
            if st.button("Efetivar no Sistema", key=f"ef{r['id']}"):
                executar_sql("INSERT INTO colaboradores (nome, tipo, data_admissao) VALUES (:n, 'CLT', :d)", {"n":r['candidato'], "d":date.today()})
                executar_sql("DELETE FROM candidatos WHERE id=:id", {"id":r['id']}); st.rerun()

# --- 10. MÓDULO DASHBOARD DP ---
elif menu == "📊 DASHBOARD DP":
    df_est = carregar_dados("contratos_estagio")
    if not df_est.empty:
        df_est['data_fim'] = pd.to_datetime(df_est['data_fim']); df_est['data_inicio'] = pd.to_datetime(df_est['data_inicio'])
        hoje = pd.Timestamp(date.today())
        
        c1, c2, c3 = st.columns(3)
        c1.metric("🎓 ESTAGIÁRIOS", len(df_est))
        venc = len(df_est[(df_est['data_fim'] - hoje).dt.days <= 30])
        c2.metric("⚠️ VENCENDO (30D)", venc)
        
        st.subheader("📊 % de Cumprimento de Contrato")
        for _, r in df_est.iterrows():
            total = (r['data_fim'] - r['data_inicio']).days
            passado = (hoje - r['data_inicio']).days
            perc = max(0, min(100, (passado/total*100))) if total > 0 else 0
            cor = "red" if perc > 90 else "green"
            st.write(f"**{r['estagiario']}**")
            st.progress(perc/100)

# --- 11. NOVO MÓDULO: COLABORADORES (Atividades: PJ, CLT, Férias) ---
elif menu == "👥 COLABORADORES":
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("📝 Novo Colaborador")
        with st.form("f_col"):
            n = st.text_input("Nome"); t = st.selectbox("Tipo", ["CLT", "PJ", "Estagiário"])
            tm = st.selectbox("Time", ["Tecnologia", "Comercial", "Operações", "RH", "Financeiro"])
            dt = st.date_input("Admissão")
            if st.form_submit_button("CADASTRAR"):
                executar_sql("INSERT INTO colaboradores (nome, tipo, time_equipe, data_admissao) VALUES (:n, :t, :tm, :dt)", {"n":n,"t":t,"tm":tm,"dt":dt}); st.rerun()
    with col2:
        st.subheader("📋 Gestão Ativa")
        df_col = carregar_dados("colaboradores")
        for _, r in df_col.iterrows():
            with st.expander(f"👤 {r['nome']} [{r['tipo']}]"):
                c1, c2, c3 = st.columns(3)
                eq = c1.checkbox("Equipamento", value=bool(r['status_equipamento']), key=f"eq{r['id']}")
                rhg = c2.checkbox("RH Gestor", value=bool(r['status_rh_gestor']), key=f"rhg{r['id']}")
                ifo = c3.checkbox("Ifood", value=bool(r['status_ifood']), key=f"ifo{r['id']}")
                if st.button("Atualizar Dados", key=f"upc{r['id']}"):
                    executar_sql("UPDATE colaboradores SET status_equipamento=:eq, status_rh_gestor=:rhg, status_ifood=:ifo WHERE id=:id", {"eq":eq,"rhg":rhg,"ifo":ifo,"id":r['id']}); st.rerun()

# --- 12. NOVO MÓDULO: BENEFÍCIOS (Atividades: AMIL, Starbem, Dasa, AVUS) ---
elif menu == "🎁 BENEFÍCIOS":
    st.subheader("🏥 Gestão de Saúde e Bem-estar")
    df_b = carregar_dados("colaboradores")
    if not df_b.empty:
        for _, r in df_b.iterrows():
            with st.expander(f"📦 Benefícios: {r['nome']}"):
                c1, c2, c3, c4 = st.columns(4)
                ami = c1.checkbox("AMIL", value=bool(r['status_amil']), key=f"ami{r['id']}")
                sta = c2.checkbox("Starbem", value=bool(r['status_starbem']), key=f"sta{r['id']}")
                das = c3.checkbox("Dasa", value=bool(r['status_dasa']), key=f"das{r['id']}")
                avu = c4.checkbox("AVUS", value=bool(r['status_avus']), key=f"avu{r['id']}")
                if st.button("Salvar Benefícios", key=f"svb{r['id']}"):
                    executar_sql("UPDATE colaboradores SET status_amil=:ami, status_starbem=:sta, status_dasa=:das, status_avus=:avu WHERE id=:id", 
                                 {"ami":ami,"sta":sta,"das":das,"avu":avu,"id":r['id']}); st.rerun()

# --- 13. MÓDULO ESTAGIÁRIOS ---
elif menu == "🎓 ESTAGIÁRIOS":
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("📝 Novo Registro")
        with st.form("f_est", clear_on_submit=True):
            n = st.text_input("Nome"); i = st.text_input("Instituição")
            t = st.selectbox("Time", ["Tecnologia", "Comercial", "Operações", "RH", "Financeiro"])
            di = st.date_input("Início"); df = st.date_input("Término")
            if st.form_submit_button("CADASTRAR"):
                executar_sql("INSERT INTO contratos_estagio (estagiario, instituicao, time_equipe, data_inicio, data_fim) VALUES (:n, :i, :t, :di, :df)", 
                             {"n": n, "i": i, "t": t, "di": di, "df": df}); st.rerun()
    with col2:
        df_e = carregar_dados("contratos_estagio")
        for _, r in df_e.iterrows():
            with st.expander(f"👤 {r['estagiario']}"):
                ca, cb, cc, cd = st.columns(4)
                s = ca.checkbox("Solicit.", value=bool(r.get('solic_contrato_dp')), key=f"sest{r['id']}")
                ae = cb.checkbox("ETUS", value=bool(r.get('assina_etus')), key=f"aeest{r['id']}")
                af = cc.checkbox("Facul.", value=bool(r.get('assina_faculdade')), key=f"afest{r['id']}")
                ej = cd.checkbox("Jurid.", value=bool(r.get('envio_juridico')), key=f"ejest{r['id']}")
                if st.button("Salvar", key=f"svest{r['id']}"):
                    executar_sql("UPDATE contratos_estagio SET solic_contrato_dp=:s, assina_etus=:ae, assina_faculdade=:af, envio_juridico=:ej WHERE id=:id", {"s":s,"ae":ae,"af":af,"ej":ej,"id":r['id']}); st.rerun()

# --- 14. NOVO MÓDULO: EVENTOS & COMUNICADOS ---
elif menu == "📅 EVENTOS & COMUNICADOS":
    st.subheader("📢 Mural da Empresa")
    with st.form("f_ev"):
        tit = st.text_input("Título do Comunicado/Evento")
        tip = st.selectbox("Tipo", ["Aniversariante", "Comunicado Slack", "Evento Presencial", "Entrada Portaria"])
        dat = st.date_input("Data")
        if st.form_submit_button("PUBLICAR"):
            executar_sql("INSERT INTO eventos (titulo, tipo, data_evento) VALUES (:t, :tp, :d)", {"t":tit,"tp":tip,"d":dat}); st.rerun()
    
    df_ev = carregar_dados("eventos")
    if not df_ev.empty:
        st.table(df_ev[['data_evento', 'tipo', 'titulo']])

# --- 15. NOVO MÓDULO: FINANCEIRO & VIAGENS ---
elif menu == "💰 FINANCEIRO & VIAGENS":
    st.info("Módulo para controle de Pagamentos PSB/MDP, NFs Ifood e Controle de Viagens/Uber.")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("💸 Pagamentos & NFs")
        st.write("- Recargas Ifood (SLA: 24h)")
        st.write("- Envio de NFs para Financeiro")
    with c2:
        st.subheader("✈️ Viagens & Uber")
        st.write("- Inclusão Uber Business")
        st.write("- Compra de Passagens/Hospedagem")
