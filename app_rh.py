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
    .vaga-header { background-color: rgba(141, 247, 104, 0.2); color: inherit; padding: 12px; border-radius: 8px; margin-top: 20px; margin-bottom: 10px; font-weight: bold; border-left: 5px solid #8DF768; }
    .curriculo-box { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #8DF768; color: #f0f0f0; margin-top: 15px; }
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

# --- 4. BANCO DE DADOS (INIT COMPLETO E CORRIGIDO) ---
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS vagas (id SERIAL PRIMARY KEY, nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE, data_fechamento DATE);
        
        CREATE TABLE IF NOT EXISTS candidatos (id SERIAL PRIMARY KEY, candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, historico TEXT, motivo_perda TEXT, envio_proposta BOOLEAN DEFAULT FALSE, solic_documentos BOOLEAN DEFAULT FALSE, solic_contrato BOOLEAN DEFAULT FALSE, solic_acessos BOOLEAN DEFAULT FALSE, arquivo_cv BYTEA);
        
        CREATE TABLE IF NOT EXISTS contratos_estagio (id SERIAL PRIMARY KEY, estagiario TEXT, instituicao TEXT, data_inicio DATE, data_fim DATE, status_contrato TEXT, time_equipe TEXT, funcao TEXT, solic_contrato_dp BOOLEAN DEFAULT FALSE, assina_etus BOOLEAN DEFAULT FALSE, assina_faculdade BOOLEAN DEFAULT FALSE, envio_juridico BOOLEAN DEFAULT FALSE);

        CREATE TABLE IF NOT EXISTS colaboradores_ativos (
            id SERIAL PRIMARY KEY, nome TEXT, tipo TEXT, time_equipe TEXT, data_admissao DATE,
            cad_rh_gestor BOOLEAN DEFAULT FALSE, cad_starbem BOOLEAN DEFAULT FALSE, cad_dasa BOOLEAN DEFAULT FALSE, 
            cad_avus BOOLEAN DEFAULT FALSE, incl_amil BOOLEAN DEFAULT FALSE, doc_amil BOOLEAN DEFAULT FALSE,
            ifood_ativo BOOLEAN DEFAULT FALSE, lingo_pass BOOLEAN DEFAULT FALSE, wellhub BOOLEAN DEFAULT FALSE,
            equipamento_entregue BOOLEAN DEFAULT FALSE, acessos_ok BOOLEAN DEFAULT FALSE, ponto_clt_estag BOOLEAN DEFAULT FALSE
        );

        CREATE TABLE IF NOT EXISTS notas_fiscais_ifood (id SERIAL PRIMARY KEY, empresa TEXT, mes_referencia TEXT, arquivo_nf BYTEA, nome_arquivo TEXT, data_upload DATE);

        CREATE TABLE IF NOT EXISTS pagamentos_gerais (id SERIAL PRIMARY KEY, empresa TEXT, categoria TEXT, mes_referencia TEXT, arquivo_pg BYTEA, nome_arquivo TEXT, data_upload DATE);
    """))

# --- 5. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    area_sel = st.selectbox("GERENCIAMENTO", ["RH - Recrutamento", "DP - Departamento Pessoal", "Operações & Benefícios", "Financeiro & iFood"])
    
    if area_sel == "RH - Recrutamento":
        menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])
    elif area_sel == "DP - Departamento Pessoal":
        menu = st.radio("NAVEGAÇÃO", ["📊 DASHBOARD DP", "🎓 ESTAGIÁRIOS", "👥 COLABORADORES"])
    elif area_sel == "Operações & Benefícios":
        menu = st.radio("NAVEGAÇÃO", ["🎁 BEM-ESTAR", "📢 COMUNICADOS", "🎒 EQUIPAMENTOS"])
    else:
        menu = st.radio("NAVEGAÇÃO", ["💰 PAGAMENTOS GERAIS"])

st.markdown(f'<div class="header-rh">{menu}</div>', unsafe_allow_html=True)

# --- 6. MÓDULO INDICADORES ---
if menu == "📊 INDICADORES":
    df_v = carregar_dados("vagas"); df_c = carregar_dados("candidatos")
    if not df_v.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 VAGAS ATIVAS", len(df_v[df_v['status_vaga'] == 'Aberta']))
        if not df_c.empty:
            st.divider(); col_l, col_r = st.columns(2)
            with col_l:
                st.subheader("📊 Funil de Recrutamento")
                ordem = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada"]
                cnt = df_c['status_geral'].value_counts().reindex(ordem).fillna(0).reset_index()
                st.plotly_chart(px.funnel(cnt, x='count', y='status_geral', color_discrete_sequence=['#8DF768']), use_container_width=True)
            with col_r:
                st.subheader("👥 Candidatos por Vaga")
                st.plotly_chart(px.pie(df_c, names='vaga_vinculada', hole=0.4), use_container_width=True)

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
            with st.form(f"edv{row['id']}"):
                ns = st.selectbox("Status", ["Aberta", "Pausada", "Finalizada"], index=["Aberta", "Pausada", "Finalizada"].index(row['status_vaga']))
                if st.form_submit_button("ATUALIZAR"):
                    df = date.today() if ns == "Finalizada" else None
                    executar_sql("UPDATE vagas SET status_vaga=:s, data_fechamento=:df WHERE id=:id", {"s":ns,"df":df,"id":row['id']}); st.rerun()

# --- 8. MÓDULO CANDIDATOS ---
elif menu == "⚙️ CANDIDATOS":
    df_v = carregar_dados("vagas"); df_c = carregar_dados("candidatos")
    with st.expander("➕ NOVO CANDIDATO"):
        with st.form("nc"):
            nc = st.text_input("Nome"); vnc = st.selectbox("Vaga Vinculada", df_v['nome_vaga'].tolist() if not df_v.empty else ["Geral"])
            if st.form_submit_button("ADICIONAR"):
                executar_sql("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral) VALUES (:n, :v, 'Triagem')", {"n":nc,"v":vnc}); st.rerun()
    if not df_c.empty:
        for v_nome in df_c['vaga_vinculada'].unique():
            st.markdown(f'<div class="vaga-header">🏢 VAGA: {v_nome.upper()}</div>', unsafe_allow_html=True)
            for _, cr in df_c[df_c['vaga_vinculada'] == v_nome].iterrows():
                with st.expander(f"👤 {cr['candidato']} — [ {cr['status_geral']} ]"):
                    c1, c2 = st.columns(2)
                    with c1:
                        ns = st.selectbox("Etapa", ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada", "Perda"], index=["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada", "Perda"].index(cr['status_geral']), key=f"s{cr['id']}")
                        if st.button("Salvar Etapa", key=f"b{cr['id']}"):
                            executar_sql("UPDATE candidatos SET status_geral=:s WHERE id=:id", {"s":ns,"id":cr['id']}); st.rerun()
                    with c2:
                        up_cv = st.file_uploader("Currículo (PDF)", type="pdf", key=f"up{cr['id']}")
                        if up_cv and st.button("💾 Salvar PDF", key=f"sv{cr['id']}"):
                            executar_sql("UPDATE candidatos SET arquivo_cv=:d WHERE id=:id", {"d":up_cv.getvalue(), "id":cr['id']}); st.rerun()
                        if cr.get('arquivo_cv'): st.download_button("📥 Baixar CV", cr['arquivo_cv'], f"CV_{cr['candidato']}.pdf", key=f"dl{cr['id']}")

# --- 9. MÓDULO ONBOARDING ---
elif menu == "🚀 ONBOARDING":
    df_c = carregar_dados("candidatos")
    aprovados = df_c[df_c['status_geral'] == 'Finalizada'] if not df_c.empty else pd.DataFrame()
    for _, r in aprovados.iterrows():
        with st.expander(f"🚀 {r['candidato']}"):
            c1, c2, c3, c4 = st.columns(4)
            p, d, c, a = c1.checkbox("Proposta", value=bool(r['envio_proposta']), key=f"p{r['id']}"), c2.checkbox("Docs", value=bool(r['solic_documentos']), key=f"d{r['id']}"), c3.checkbox("Contrato", value=bool(r['solic_contrato']), key=f"c{r['id']}"), c4.checkbox("Acessos", value=bool(r['solic_acessos']), key=f"a{r['id']}")
            if st.button("Salvar & Efetivar", key=f"svon{r['id']}"):
                executar_sql("UPDATE candidatos SET envio_proposta=:p, solic_documentos=:d, solic_contrato=:c, solic_acessos=:a WHERE id=:id", {"p":p,"d":d,"c":c,"a":a,"id":r['id']})
                if p and d and c and a: executar_sql("INSERT INTO colaboradores_ativos (nome, data_admissao) VALUES (:n, :da)", {"n":r['candidato'], "da":date.today()}); st.success("Efetivado!"); st.rerun()

# --- 10. DASHBOARD DP ---
elif menu == "📊 DASHBOARD DP":
    df_est = carregar_dados("contratos_estagio")
    if not df_est.empty:
        df_est['data_fim'] = pd.to_datetime(df_est['data_fim']); df_est['data_inicio'] = pd.to_datetime(df_est['data_inicio']); hoje = pd.Timestamp(date.today())
        c1, c2, c3 = st.columns(3)
        c1.metric("🎓 TOTAL ESTAGIÁRIOS", len(df_est))
        venc = len(df_est[(df_est['data_fim'] >= hoje) & ((df_est['data_fim'] - hoje).dt.days <= 30)])
        c2.metric("⚠️ VENCENDO (30D)", venc)
        
        st.subheader("📊 % Cumprimento de Contrato")
        for _, r in df_est.iterrows():
            total = (r['data_fim'] - r['data_inicio']).days
            passado = (hoje - r['data_inicio']).days
            perc = max(0, min(100, (passado / total * 100))) if total > 0 else 0
            st.write(f"**{r['estagiario']}** ({round(perc,1)}%)")
            st.progress(perc/100)

# --- 11. ESTAGIÁRIOS ---
elif menu == "🎓 ESTAGIÁRIOS":
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("📝 Novo")
        with st.form("f_est", clear_on_submit=True):
            n, i, t = st.text_input("Nome"), st.text_input("Instituição"), st.selectbox("Time", ["Tecnologia", "Comercial", "Operações", "RH", "Financeiro"])
            di, df = st.date_input("Início"), st.date_input("Término")
            if st.form_submit_button("CADASTRAR"): executar_sql("INSERT INTO contratos_estagio (estagiario, instituicao, time_equipe, data_inicio, data_fim) VALUES (:n, :i, :t, :di, :df)", {"n":n,"i":i,"t":t,"di":di,"df":df}); st.rerun()
    with col2:
        df_e = carregar_dados("contratos_estagio")
        for _, r in df_e.iterrows():
            with st.expander(f"👤 {r['estagiario']}"):
                c1, c2, c3, c4 = st.columns(4)
                s, ae, af, ej = c1.checkbox("Solic.", value=bool(r['solic_contrato_dp']), key=f"s{r['id']}"), c2.checkbox("ETUS", value=bool(r['assina_etus']), key=f"ae{r['id']}"), c3.checkbox("Facul.", value=bool(r['assina_faculdade']), key=f"af{r['id']}"), c4.checkbox("Jurid.", value=bool(r['envio_juridico']), key=f"ej{r['id']}")
                if st.button("Salvar", key=f"svest{r['id']}"): executar_sql("UPDATE contratos_estagio SET solic_contrato_dp=:s, assina_etus=:ae, assina_faculdade=:af, envio_juridico=:ej WHERE id=:id", {"s":s,"ae":ae,"af":af,"ej":ej,"id":r['id']}); st.rerun()

# --- 12. FINANCEIRO & IFOOD ---
elif menu == "💰 PAGAMENTOS GERAIS":
    t1, t2 = st.tabs(["🍔 iFOOD", "💸 PSB/MDP GERAL"])
    with t1:
        st.subheader("Gestão de Notas iFood")
        c_up, c_list = st.columns([1, 2])
        with c_up:
            with st.form("f_ifood", clear_on_submit=True):
                emp = st.selectbox("Empresa", ["ETUS", "BHAZ", "E3J", "Evolution", "No Name"])
                mes = st.selectbox("Mês", ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"])
                arq = st.file_uploader("Nota (PDF)", type="pdf", key="up_if")
                if st.form_submit_button("SALVAR NF"):
                    if arq: executar_sql("INSERT INTO notas_fiscais_ifood (empresa, mes_referencia, arquivo_nf, nome_arquivo, data_upload) VALUES (:e, :m, :a, :n, :d)", {"e":emp,"m":mes,"a":arq.getvalue(),"n":arq.name,"d":date.today()}); st.rerun()
        with c_list:
            df_if = carregar_dados("notas_fiscais_ifood")
            for _, r in df_if.iterrows():
                with st.expander(f"📄 {r['empresa']} - {r['mes_referencia']}"):
                    st.download_button("📥 Baixar", r['arquivo_nf'], r['nome_arquivo'], key=f"dlif{r['id']}")
                    if st.button("🗑️", key=f"delif{r['id']}"): executar_sql("DELETE FROM notas_fiscais_ifood WHERE id=:id", {"id":r['id']}); st.rerun()
    
    with t2:
        st.subheader("Pagamentos Plusdin, São Bernardo e Projeto")
        c_up2, c_list2 = st.columns([1, 2])
        with c_up2:
            with st.form("f_geral", clear_on_submit=True):
                emp2 = st.selectbox("Empresa", ["Plusdin", "São Bernardo", "Projeto Consegui Aprender"])
                cat2 = st.radio("Categoria", ["PSB", "MDP"], horizontal=True)
                mes2 = st.selectbox("Mês", ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"], key="mes2")
                arq2 = st.file_uploader("Arquivo (PDF)", type="pdf", key="up_gr")
                if st.form_submit_button("SALVAR PAGAMENTO"):
                    if arq2: executar_sql("INSERT INTO pagamentos_gerais (empresa, categoria, mes_referencia, arquivo_pg, nome_arquivo, data_upload) VALUES (:e, :c, :m, :a, :n, :d)", {"e":emp2,"c":cat2,"m":mes2,"a":arq2.getvalue(),"n":arq2.name,"d":date.today()}); st.rerun()
        with c_list2:
            df_gr = carregar_dados("pagamentos_gerais")
            for _, r in df_gr.iterrows():
                with st.expander(f"💰 {r['empresa']} - {r['categoria']}"):
                    st.download_button("📥 Baixar", r['arquivo_pg'], r['nome_arquivo'], key=f"dlgr{r['id']}")
                    if st.button("🗑️", key=f"delgr{r['id']}"): executar_sql("DELETE FROM pagamentos_gerais WHERE id=:id", {"id":r['id']}); st.rerun()
