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

# --- 4. BANCO DE DADOS (INIT COMPLETO) ---
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
        CREATE TABLE IF NOT EXISTS administrativo (id SERIAL PRIMARY KEY, item TEXT, status TEXT, valor FLOAT, data DATE, categoria TEXT);
    """))
with engine.begin() as conn:
    # (Mantendo as outras tabelas e adicionando a de Notas Ifood)
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS notas_fiscais_ifood (
            id SERIAL PRIMARY KEY, 
            empresa TEXT, 
            mes_referencia TEXT, 
            arquivo_nf BYTEA, 
            nome_arquivo TEXT,
            data_upload DATE
        );
    """))
    with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS pagamentos_gerais (
            id SERIAL PRIMARY KEY, 
            empresa TEXT, 
            categoria TEXT, -- PSB ou MDP
            mes_referencia TEXT, 
            arquivo_pg BYTEA, 
            nome_arquivo TEXT,
            data_upload DATE
        );
    """))

# --- 5. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    area_sel = st.selectbox("GERENCIAMENTO", ["RH - Recrutamento", "DP - Departamento Pessoal", "Operações & Benefícios", "Financeiro & Viagens"])
    
    if area_sel == "RH - Recrutamento":
        menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])
    elif area_sel == "DP - Departamento Pessoal":
        menu = st.radio("NAVEGAÇÃO", ["📊 DASHBOARD DP", "🎓 ESTAGIÁRIOS", "👥 COLABORADORES CLT/PJ"])
    elif area_sel == "Operações & Benefícios":
        menu = st.radio("NAVEGAÇÃO", ["🎁 GESTÃO DE BENEFÍCIOS", "📢 COMUNICADOS & PORTARIA", "🎒 EQUIPAMENTOS"])
    else:
        menu = st.radio("NAVEGAÇÃO", ["💰 PAGAMENTOS & IFOOD", "✈️ VIAGENS & UBER"])

st.markdown(f'<div class="header-rh">{menu}</div>', unsafe_allow_html=True)

# --- 6. MÓDULO INDICADORES (R&S) ---
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

# --- 8. MÓDULO CANDIDATOS (COM CURRÍCULO) ---
elif menu == "⚙️ CANDIDATOS":
    df_v = carregar_dados("vagas"); df_c = carregar_dados("candidatos")
    with st.expander("➕ NOVO CANDIDATO"):
        with st.form("nc"):
            nc = st.text_input("Nome"); vnc = st.selectbox("Vaga", df_v['nome_vaga'].tolist() if not df_v.empty else ["Geral"])
            if st.form_submit_button("ADICIONAR"):
                executar_sql("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral) VALUES (:n, :v, 'Triagem')", {"n":nc,"v":vnc}); st.rerun()
    if not df_c.empty:
        vagas_unicas = df_c['vaga_vinculada'].unique()
        for v_nome in vagas_unicas:
            st.markdown(f'<div class="vaga-header">🏢 VAGA: {v_nome.upper()}</div>', unsafe_allow_html=True)
            for _, cr in df_c[df_c['vaga_vinculada'] == v_nome].iterrows():
                with st.expander(f"👤 {cr['candidato']} — [ {cr['status_geral']} ]"):
                    c1, c2 = st.columns(2)
                    with c1:
                        etapas = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada", "Perda"]
                        ns = st.selectbox("Etapa", etapas, index=etapas.index(cr['status_geral']) if cr['status_geral'] in etapas else 0, key=f"s{cr['id']}")
                        if st.button("Salvar Etapa", key=f"b{cr['id']}"):
                            executar_sql("UPDATE candidatos SET status_geral=:s WHERE id=:id", {"s":ns,"id":cr['id']}); st.rerun()
                    with c2:
                        up_cv = st.file_uploader("Upload CV (PDF)", type="pdf", key=f"up{cr['id']}")
                        if up_cv and st.button("💾 Salvar PDF", key=f"save{cr['id']}"):
                            executar_sql("UPDATE candidatos SET arquivo_cv=:data WHERE id=:id", {"data": up_cv.getvalue(), "id": cr['id']}); st.success("Salvo!")
                        if cr.get('arquivo_cv'): st.download_button("📥 Baixar CV", cr['arquivo_cv'], f"CV_{cr['candidato']}.pdf", key=f"dl{cr['id']}")

# --- 9. MÓDULO ONBOARDING ---
elif menu == "🚀 ONBOARDING":
    df_c = carregar_dados("candidatos")
    aprovados = df_c[df_c['status_geral'] == 'Finalizada'] if not df_c.empty else pd.DataFrame()
    for _, r in aprovados.iterrows():
        with st.expander(f"🚀 {r['candidato']}"):
            c1, c2, c3, c4 = st.columns(4)
            p = c1.checkbox("Proposta", value=bool(r['envio_proposta']), key=f"pro{r['id']}")
            d = c2.checkbox("Docs", value=bool(r['solic_documentos']), key=f"doc{r['id']}")
            c = c3.checkbox("Contrato", value=bool(r['solic_contrato']), key=f"con{r['id']}")
            a = c4.checkbox("Acessos", value=bool(r['solic_acessos']), key=f"ace{r['id']}")
            if st.button("Salvar Checklist & Efetivar", key=f"svon{r['id']}"):
                executar_sql("UPDATE candidatos SET envio_proposta=:p, solic_documentos=:d, solic_contrato=:c, solic_acessos=:a WHERE id=:id", {"p":p,"d":d,"c":c,"a":a,"id":r['id']})
                if p and d and c and a:
                    executar_sql("INSERT INTO colaboradores_ativos (nome, data_admissao) VALUES (:n, :d)", {"n":r['candidato'], "d":date.today()})
                    st.success("Colaborador movido para Ativos!"); st.rerun()

# --- 10. MÓDULO DASHBOARD DP (INTEGRAL COM GRÁFICOS E BARRAS) ---
elif menu == "📊 DASHBOARD DP":
    df_est = carregar_dados("contratos_estagio")
    if not df_est.empty:
        df_est['data_fim'] = pd.to_datetime(df_est['data_fim']); df_est['data_inicio'] = pd.to_datetime(df_est['data_inicio'])
        hoje = pd.Timestamp(date.today())
        
        c1, c2, c3 = st.columns(3)
        c1.metric("🎓 TOTAL ESTAGIÁRIOS", len(df_est))
        venc = len(df_est[(df_est['data_fim'] >= hoje) & ((df_est['data_fim'] - hoje).dt.days <= 30)])
        c2.metric("⚠️ VENCENDO (30 DIAS)", venc)
        df_est['doc_ok'] = (df_est['solic_contrato_dp']==True)&(df_est['assina_etus']==True)&(df_est['assina_faculdade']==True)&(df_est['envio_juridico']==True)
        c3.metric("✅ DOCS COMPLETOS", len(df_est[df_est['doc_ok'] == True]))

        st.divider()
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("🏢 Por Time")
            st.plotly_chart(px.bar(df_est, x='time_equipe', color_discrete_sequence=['#8DF768']), use_container_width=True)
        with g2:
            st.subheader("📈 Status Docs")
            st.plotly_chart(px.pie(df_est, names='doc_ok', color='doc_ok', color_discrete_map={True:'#8DF768', False:'#FF4B4B'}), use_container_width=True)

        st.divider()
        st.subheader("📊 % de Cumprimento de Contrato")
        progressos, cores = [], []
        for _, r in df_est.iterrows():
            total_dias = (r['data_fim'] - r['data_inicio']).days
            passado = (hoje - r['data_inicio']).days
            perc = max(0, min(100, (passado / total_dias * 100))) if total_dias > 0 else 0
            progressos.append(round(perc, 1))
            cores.append('#FF4B4B' if perc >= 90 else '#FFA500' if perc >= 70 else '#8DF768')
        df_est['progresso'], df_est['cor'] = progressos, cores
        fig = go.Figure(go.Bar(y=df_est['estagiario'], x=df_est['progresso'], orientation='h', marker_color=df_est['cor'], text=df_est['progresso'].astype(str) + '%', textposition='auto'))
        fig.update_layout(xaxis=dict(range=[0, 100]), yaxis=dict(autorange="reversed"), height=300+(len(df_est)*35), margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

# --- 11. MÓDULO ESTAGIÁRIOS ---
elif menu == "🎓 ESTAGIÁRIOS":
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("📝 Novo Registro")
        with st.form("f_est", clear_on_submit=True):
            n = st.text_input("Nome"); i = st.text_input("Instituição"); t = st.selectbox("Time", ["Tecnologia", "Comercial", "Operações", "RH", "Financeiro"])
            di, df = st.date_input("Início"), st.date_input("Término")
            if st.form_submit_button("CADASTRAR"):
                executar_sql("INSERT INTO contratos_estagio (estagiario, instituicao, time_equipe, data_inicio, data_fim) VALUES (:n, :i, :t, :di, :df)", {"n": n, "i": i, "t": t, "di": di, "df": df}); st.rerun()
    with col2:
        df_e = carregar_dados("contratos_estagio")
        for _, r in df_e.iterrows():
            with st.expander(f"👤 {r['estagiario']}"):
                ca, cb, cc, cd = st.columns(4)
                s = ca.checkbox("Solicit.", value=bool(r['solic_contrato_dp']), key=f"sest{r['id']}")
                ae = cb.checkbox("ETUS", value=bool(r['assina_etus']), key=f"aeest{r['id']}")
                af = cc.checkbox("Facul.", value=bool(r['assina_faculdade']), key=f"afest{r['id']}")
                ej = cd.checkbox("Jurid.", value=bool(r['envio_juridico']), key=f"ejest{r['id']}")
                if st.button("Salvar Checklist", key=f"svest{r['id']}"):
                    executar_sql("UPDATE contratos_estagio SET solic_contrato_dp=:s, assina_etus=:ae, assina_faculdade=:af, envio_juridico=:ej WHERE id=:id", {"s":s,"ae":ae,"af":af,"ej":ej,"id":r['id']}); st.rerun()
                if st.button("🗑️ Excluir", key=f"dlest{r['id']}"): executar_sql("DELETE FROM contratos_estagio WHERE id=:id", {"id":r['id']}); st.rerun()

# --- 12. NOVO MÓDULO: BENEFÍCIOS (Toda sua lista de cadastros) ---
elif menu == "🎁 GESTÃO DE BENEFÍCIOS":
    df_at = carregar_dados("colaboradores_ativos")
    if not df_at.empty:
        for _, r in df_at.iterrows():
            with st.expander(f"📦 Benefícios & Cadastros: {r['nome']}"):
                st.write("**Cadastros em Plataformas:**")
                c1, c2, c3, c4 = st.columns(4)
                rhg = c1.checkbox("RH Gestor", value=bool(r['cad_rh_gestor']), key=f"rhg{r['id']}")
                stb = c2.checkbox("Starbem", value=bool(r['cad_starbem']), key=f"stb{r['id']}")
                das = c3.checkbox("Dasa", value=bool(r['cad_dasa']), key=f"das{r['id']}")
                avu = c4.checkbox("AVUS", value=bool(r['cad_avus']), key=f"avu{r['id']}")
                
                st.write("**Saúde & Bem-estar:**")
                c5, c6, c7, c8 = st.columns(4)
                ami = c5.checkbox("Inclusão AMIL", value=bool(r['incl_amil']), key=f"ami{r['id']}")
                dam = c6.checkbox("Doc Inclusão", value=bool(r['doc_amil']), key=f"dam{r['id']}")
                whub = c7.checkbox("Wellhub", value=bool(r['wellhub']), key=f"wh{r['id']}")
                lpas = c8.checkbox("LingoPass", value=bool(r['lingo_pass']), key=f"lp{r['id']}")
                
                if st.button("Salvar Atualizações", key=f"svb{r['id']}"):
                    executar_sql("""UPDATE colaboradores_ativos SET cad_rh_gestor=:rhg, cad_starbem=:stb, cad_dasa=:das, cad_avus=:avu, 
                                    incl_amil=:ami, doc_amil=:dam, wellhub=:whub, lingo_pass=:lpas WHERE id=:id""", 
                                    {"rhg":rhg,"stb":stb,"das":das,"avu":avu,"ami":ami,"dam":dam,"whub":whub,"lpas":lpas,"id":r['id']}); st.rerun()

# --- 13. NOVO MÓDULO: COMUNICADOS & PORTARIA ---
elif menu == "📢 COMUNICADOS & PORTARIA":
    st.subheader("Entradas de Portaria & Slack")
    col_a, col_b = st.columns(2)
    with col_a:
        with st.form("f_portaria"):
            nome_p = st.text_input("Nome p/ Portaria"); data_p = st.date_input("Data Entrada")
            if st.form_submit_button("Enviar p/ Portaria"): st.success(f"Solicitação de {nome_p} enviada!")
    with col_b:
        st.info("💡 **Dica Slack:** Utilize o canal #comunicados para Aniversariantes e Boas-vindas.")
        if st.button("Gerar Texto de Boas-vindas"): st.code(f"Bem-vindo(a) à ETUS! 🚀 Ficamos felizes em ter você conosco.")

# --- 14. NOVO MÓDULO: FINANCEIRO & VIAGENS ---
elif menu == "💰 PAGAMENTOS & IFOOD":
    tab_ifood, tab_outros = st.tabs(["🍔 GESTÃO IFOOD", "💸 OUTROS PAGAMENTOS (PSB/MDP)"])
    
    with tab_ifood:
        st.subheader("Notas Fiscais iFood")
        col_up_if, col_list_if = st.columns([1, 2])
        # ... (Mantém o código de upload do Ifood que já fizemos)
        # Filtro: ETUS, BHAZ, E3J, Evolution, No Name

    with tab_outros:
        st.subheader("Gestão de Pagamentos: Plusdin, São Bernardo e Projeto Consegui Aprender")
        
        col_up_pg, col_list_pg = st.columns([1, 2])
        
        with col_up_pg:
            st.markdown('<div class="vaga-header">📤 UPLOAD DE COMPROVANTE/NF</div>', unsafe_allow_html=True)
            with st.form("f_pag_geral", clear_on_submit=True):
                emp_pg = st.selectbox("Empresa", ["Plusdin", "São Bernardo", "Projeto Consegui Aprender"])
                cat_pg = st.radio("Categoria", ["PSB", "MDP"], horizontal=True)
                mes_pg = st.selectbox("Mês", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"], key="mes_pg")
                arq_pg = st.file_uploader("Arquivo (PDF)", type="pdf", key="arq_pg")
                
                if st.form_submit_button("SALVAR PAGAMENTO"):
                    if arq_pg:
                        executar_sql("""
                            INSERT INTO pagamentos_gerais (empresa, categoria, mes_referencia, arquivo_pg, nome_arquivo, data_upload) 
                            VALUES (:emp, :cat, :mes, :arq, :nom, :dat)
                        """, {"emp": emp_pg, "cat": cat_pg, "mes": mes_pg, "arq": arq_pg.getvalue(), "nom": arq_pg.name, "dat": date.today()})
                        st.success("Salvo com sucesso!")
                        st.rerun()
        
        with col_list_pg:
            st.markdown('<div class="vaga-header">🔍 CONSULTA DE PAGAMENTOS</div>', unsafe_allow_html=True)
            f_emp_pg = st.multiselect("Filtrar Empresa", ["Plusdin", "São Bernardo", "Projeto Consegui Aprender"], default=["Plusdin", "São Bernardo", "Projeto Consegui Aprender"])
            
            df_pg = carregar_dados("pagamentos_gerais")
            if not df_pg.empty:
                df_f_pg = df_pg[df_pg['empresa'].isin(f_emp_pg)]
                for _, r in df_f_pg.iterrows():
                    with st.expander(f"💰 {r['empresa']} | {r['categoria']} - {r['mes_referencia']}"):
                        st.write(f"Arquivo: {r['nome_arquivo']}")
                        st.download_button("📥 Baixar", r['arquivo_pg'], r['nome_arquivo'], key=f"dl_pg_{r['id']}")
                        if st.button("🗑️ Excluir", key=f"del_pg_{r['id']}"):
                            executar_sql("DELETE FROM pagamentos_gerais WHERE id=:id", {"id": r['id']})
                            st.rerun()
            else:
                st.info("Nenhum registro encontrado.")
# --- 15. GESTÃO DE COLABORADORES CLT/PJ ---
elif menu == "👥 COLABORADORES CLT/PJ":
    st.subheader("Gestão de Movimentações e Férias")
    df_ativos = carregar_dados("colaboradores_ativos")
    if not df_ativos.empty:
        st.dataframe(df_ativos[['nome', 'data_admissao']])


