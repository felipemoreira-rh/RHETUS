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
    .stProgress > div > div > div > div { background-color: #8DF768; }
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

# --- 4. BANCO DE DADOS (INIT INDIVIDUAL - PREVINE OPERATIONALERROR) ---
with engine.begin() as conn:
    conn.execute(text("CREATE TABLE IF NOT EXISTS vagas (id SERIAL PRIMARY KEY, nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE, data_fechamento DATE);"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS candidatos (id SERIAL PRIMARY KEY, candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, arquivo_cv BYTEA, envio_proposta BOOLEAN DEFAULT FALSE, solic_documentos BOOLEAN DEFAULT FALSE, solic_contrato BOOLEAN DEFAULT FALSE, solic_acessos BOOLEAN DEFAULT FALSE);"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS contratos_estagio (id SERIAL PRIMARY KEY, estagiario TEXT, instituicao TEXT, data_inicio DATE, data_fim DATE, time_equipe TEXT, solic_contrato_dp BOOLEAN DEFAULT FALSE, assina_etus BOOLEAN DEFAULT FALSE, assina_faculdade BOOLEAN DEFAULT FALSE, envio_juridico BOOLEAN DEFAULT FALSE);"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS notas_fiscais_ifood (id SERIAL PRIMARY KEY, empresa TEXT, mes_referencia TEXT, arquivo_nf BYTEA, nome_arquivo TEXT, data_upload DATE);"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS pagamentos_gerais (id SERIAL PRIMARY KEY, empresa TEXT, categoria TEXT, mes_referencia TEXT, arquivo_pg BYTEA, nome_arquivo TEXT, data_upload DATE);"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS colaboradores_ativos (id SERIAL PRIMARY KEY, nome TEXT, tipo TEXT, data_admissao DATE, cad_starbem BOOLEAN DEFAULT FALSE, incl_amil BOOLEAN DEFAULT FALSE, ifood_ativo BOOLEAN DEFAULT FALSE, equipamento_entregue BOOLEAN DEFAULT FALSE);"))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS controle_experiencia (
            id SERIAL PRIMARY KEY, 
            nome TEXT, 
            cargo TEXT, 
            time_equipe TEXT, 
            data_inicio DATE, 
            av1_feito BOOLEAN DEFAULT FALSE, 
            av1_data DATE, 
            av1_responsavel TEXT, 
            av2_feito BOOLEAN DEFAULT FALSE, 
            av2_data DATE, 
            av2_responsavel TEXT
        );
    """))

# --- 5. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    area_sel = st.selectbox("GERENCIAMENTO", ["RH - Recrutamento", "DP - Departamento Pessoal", "Financeiro & Notas"])
    
    if area_sel == "RH - Recrutamento":
        menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])
    elif area_sel == "DP - Departamento Pessoal":
        menu = st.radio("NAVEGAÇÃO", ["📊 DASHBOARD DP", "🎓 ESTAGIÁRIOS", "👥 COLABORADORES", "⏳ PERÍODO DE EXPERIÊNCIA"])
    else:
        menu = st.radio("NAVEGAÇÃO", ["🍔 IFOOD", "💸 OUTROS PAGAMENTOS"])

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

# --- 8. MÓDULO CANDIDATOS (COM CONTRATAÇÃO E AUTOMAÇÃO PARA EXPERIÊNCIA) ---
elif menu == "⚙️ CANDIDATOS":
    df_v = carregar_dados("vagas")
    df_c = carregar_dados("candidatos")
    
    with st.expander("➕ NOVO CANDIDATO"):
        with st.form("nc"):
            nc = st.text_input("Nome")
            vnc = st.selectbox("Vaga", df_v['nome_vaga'].tolist() if not df_v.empty else ["Geral"])
            if st.form_submit_button("ADICIONAR"):
                executar_sql("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral) VALUES (:n, :v, 'Triagem')", {"n":nc,"v":vnc})
                st.rerun()

    if not df_c.empty:
        for v_nome in df_c['vaga_vinculada'].unique():
            st.markdown(f'<div class="vaga-header">🏢 VAGA: {v_nome.upper()}</div>', unsafe_allow_html=True)
            for _, cr in df_c[df_c['vaga_vinculada'] == v_nome].iterrows():
                with st.expander(f"👤 {cr['candidato']} - {cr['status_geral']}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        etapas = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada", "Perda"]
                        idx_etapa = etapas.index(cr['status_geral']) if cr['status_geral'] in etapas else 0
                        ns = st.selectbox("Etapa Atual", etapas, index=idx_etapa, key=f"s{cr['id']}")
                        
                        # Se marcar como Finalizada, abre opções de contratação
                        data_ini_contratado = None
                        if ns == "Finalizada":
                            st.info("✨ Candidato em fase de contratação")
                            foi_contratado = st.checkbox("Confirmar Contratação?", key=f"conf{cr['id']}")
                            if foi_contratado:
                                data_ini_contratado = st.date_input("Data de Início (Admissão)", value=date.today(), key=f"dt_ini{cr['id']}")
                        
                        if st.button("Salvar Status e Integrar", key=f"b{cr['id']}"):
                            # 1. Atualiza status do candidato
                            executar_sql("UPDATE candidatos SET status_geral=:s WHERE id=:id", {"s":ns,"id":cr['id']})
                            
                            # 2. Se Finalizada + Confirmar Contratação -> Automação DP
                            if ns == "Finalizada" and data_ini_contratado:
                                # A) Envia para Colaboradores Ativos
                                df_colab = carregar_dados("colaboradores_ativos")
                                if df_colab.empty or cr['candidato'] not in df_colab['nome'].values:
                                    executar_sql("INSERT INTO colaboradores_ativos (nome, tipo, data_admissao) VALUES (:n, 'CLT', :d)", 
                                                {"n": cr['candidato'], "d": data_ini_contratado})
                                
                                # B) Envia para Controle de Experiência (DP)
                                df_exp = carregar_dados("controle_experiencia")
                                if df_exp.empty or cr['candidato'] not in df_exp['nome'].values:
                                    executar_sql("""
                                        INSERT INTO controle_experiencia (nome, cargo, time_equipe, data_inicio) 
                                        VALUES (:n, :c, :t, :d)
                                    """, {
                                        "n": cr['candidato'], 
                                        "c": cr['vaga_vinculada'], 
                                        "t": "A definir", # Pode ser ajustado depois no DP
                                        "d": data_ini_contratado
                                    })
                                st.success(f"✅ {cr['candidato']} integrado ao DP (Colaboradores e Experiência)!")
                            st.rerun()
                    
                    with c2:
                        up_cv = st.file_uploader("Currículo (PDF)", type="pdf", key=f"up{cr['id']}")
                        if up_cv and st.button("💾 Salvar PDF", key=f"sv{cr['id']}"):
                            executar_sql("UPDATE candidatos SET arquivo_cv=:d WHERE id=:id", {"d":up_cv.getvalue(), "id":cr['id']})
                            st.rerun()
                            st.divider()
                    if st.button(f"🗑️ Excluir Candidato: {cr['candidato']}", key=f"delcan{cr['id']}"):
                        executar_sql("DELETE FROM candidatos WHERE id=:id", {"id":cr['id']})
                        st.warning(f"Candidato {cr['candidato']} removido.")
                        st.rerun()
                        
                        # Verificação segura da coluna de arquivo para evitar KeyError
                        tem_cv = False
                        if 'arquivo_cv' in cr:
                             if cr['arquivo_cv'] is not None: tem_cv = True
                        
                        if tem_cv:
                            st.download_button("📥 Baixar CV", cr['arquivo_cv'], f"CV_{cr['candidato']}.pdf", key=f"dl{cr['id']}")
                        else:
                            st.caption("Nenhum currículo anexado.")
# --- 9. MÓDULO ONBOARDING ---
elif menu == "🚀 ONBOARDING":
    df_c = carregar_dados("candidatos")
    aprovados = df_c[df_c['status_geral'] == 'Finalizada'] if not df_c.empty else pd.DataFrame()
    for _, r in aprovados.iterrows():
        with st.expander(f"🚀 {r['candidato']}"):
            c1, c2, c3, c4 = st.columns(4)
            p = c1.checkbox("Proposta", value=bool(r['envio_proposta']), key=f"p{r['id']}")
            d = c2.checkbox("Docs", value=bool(r['solic_documentos']), key=f"d{r['id']}")
            c = c3.checkbox("Contrato", value=bool(r['solic_contrato']), key=f"c{r['id']}")
            a = c4.checkbox("Acessos", value=bool(r['solic_acessos']), key=f"a{r['id']}")
            if st.button("Salvar Checklist", key=f"svon{r['id']}"):
                executar_sql("UPDATE candidatos SET envio_proposta=:p, solic_documentos=:d, solic_contrato=:c, solic_acessos=:a WHERE id=:id", {"p":p,"d":d,"c":c,"a":a,"id":r['id']}); st.success("Checklist Salvo!"); st.rerun()

# --- 10. MÓDULO DASHBOARD DP (RESTAURADO E CORRIGIDO) ---
elif menu == "📊 DASHBOARD DP":
    st.subheader("Indicadores de Departamento Pessoal")
    
    df_col = carregar_dados("colaboradores_ativos")
    df_est = carregar_dados("contratos_estagio")
    df_exp = carregar_dados("controle_experiencia") # Carregado aqui para uso nos KPIs
    
    if not df_col.empty:
        # --- LINHA 1: MÉTRICAS GERAIS ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("👥 TOTAL ATIVOS", len(df_col))
        c2.metric("👔 CLT/PJ", len(df_col[df_col['tipo'].isin(['CLT', 'PJ'])]))
        c3.metric("🎓 ESTAGIÁRIOS", len(df_col[df_col['tipo'] == 'Estagiário']))
        
        # Cálculo de Benefícios Concluídos
        check_cols = ['cad_starbem', 'incl_amil', 'ifood_ativo', 'equipamento_entregue']
        existentes = [col for col in check_cols if col in df_col.columns]
        
        if existentes:
            total_checks = df_col[existentes].sum().sum()
            max_possible = len(df_col) * len(existentes)
            perc_beneficios = (total_checks / max_possible * 100) if max_possible > 0 else 0
            c4.metric("✅ BENEFÍCIOS OK", f"{round(perc_beneficios, 1)}%")
        else:
            c4.metric("✅ BENEFÍCIOS OK", "0%")

        st.divider()

        # --- LINHA 2: GRÁFICOS ESTRATÉGICOS ---
        col_graph1, col_graph2 = st.columns(2)
        
        with col_graph1:
            st.markdown("**Distribuição por Tipo de Contrato**")
            fig_tipo = px.pie(df_col, names='tipo', hole=0.4, color_discrete_sequence=['#8DF768', '#1E1E1E', '#555555'])
            st.plotly_chart(fig_tipo, use_container_width=True)
            
        with col_graph2:
            st.markdown("**Acompanhamento de Contratos de Estágio**")
            if not df_est.empty:
                df_est['data_fim'] = pd.to_datetime(df_est['data_fim'])
                df_est['data_inicio'] = pd.to_datetime(df_est['data_inicio'])
                hoje_ts = pd.Timestamp(date.today())
                
                progress_data = []
                for _, r in df_est.iterrows():
                    total_dias = (r['data_fim'] - r['data_inicio']).days
                    passado = (hoje_ts - r['data_inicio']).days
                    perc = max(0, min(100, (passado / total_dias * 100))) if total_dias > 0 else 0
                    progress_data.append({"Estagiário": r['estagiario'], "Progresso": perc})
                
                df_prog = pd.DataFrame(progress_data)
                fig_prog = px.bar(df_prog, x='Progresso', y='Estagiário', orientation='h', 
                                  range_x=[0, 100], color_discrete_sequence=['#8DF768'])
                st.plotly_chart(fig_prog, use_container_width=True)
            else:
                st.info("Sem dados de estágio para exibir progresso.")

        # --- NOVO GRÁFICO: INDICADOR DE ADERÊNCIA (EXPERIÊNCIA) ---
        st.divider()
        st.markdown("**Qualidade e Aderência ao Prazo (Experiência 45/90 dias)**")
        
        if not df_exp.empty:
            hoje = date.today()
            no_prazo, atrasado_pendente = 0, 0
            
            for _, r in df_exp.iterrows():
                for dias in [45, 90]:
                    dt_limite = r['data_inicio'] + pd.Timedelta(days=dias)
                    campo_feito = r['av1_feito'] if dias == 45 else r['av2_feito']
                    campo_data = r['av1_data'] if dias == 45 else r['av2_data']
                    
                    if campo_feito:
                        if campo_data and campo_data <= dt_limite:
                            no_prazo += 1
                        else:
                            atrasado_pendente += 1
                    elif hoje > dt_limite:
                        atrasado_pendente += 1
            
            c_g1, c_g2 = st.columns([1, 2])
            with c_g1:
                total_total = no_prazo + atrasado_pendente
                perc_ad = (no_prazo / total_total * 100) if total_total > 0 else 100
                st.metric("🎯 ADERÊNCIA AO PRAZO", f"{round(perc_ad, 1)}%")
            
            with c_g2:
                fig_prazos = px.pie(names=["No Prazo", "Fora do Prazo / Pendente"], 
                                    values=[no_prazo, atrasado_pendente], 
                                    hole=0.4, height=300,
                                    color_discrete_map={"No Prazo": "#8DF768", "Fora do Prazo / Pendente": "#FF4B4B"})
                fig_prazos.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_prazos, use_container_width=True)
        else:
            st.info("Aguardando dados de experiência para gerar indicador de aderência.")

        # --- LINHA 3: ALERTAS DE VENCIMENTO DE EXPERIÊNCIA ---
        st.divider()
        st.markdown('<div class="vaga-header">⚠️ ALERTAS DE EXPERIÊNCIA PRÓXIMOS (7 DIAS)</div>', unsafe_allow_html=True)
        if not df_exp.empty:
            hoje = date.today()
            alertas = []
            for _, r in df_exp.iterrows():
                d45 = r['data_inicio'] + pd.Timedelta(days=45)
                d90 = r['data_inicio'] + pd.Timedelta(days=90)
                
                if not r['av1_feito'] and 0 <= (d45 - hoje).days <= 7:
                    alertas.append(f"🔴 **{r['nome']}**: 45 dias em {d45.strftime('%d/%m/%Y')}")
                if not r['av2_feito'] and 0 <= (d90 - hoje).days <= 7:
                    alertas.append(f"🟠 **{r['nome']}**: 90 dias em {d90.strftime('%d/%m/%Y')}")
            
            if alertas:
                for a in alertas: st.warning(a)
            else:
                st.success("Tudo em dia! Nenhuma avaliação vence nos próximos 7 dias.")
    else:
        st.info("Cadastre colaboradores ativos para visualizar os indicadores de DP.")

# --- 11. MÓDULO ESTAGIÁRIOS ---
elif menu == "🎓 ESTAGIÁRIOS":
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("📝 Novo Registro")
        with st.form("f_est"):
            n, i = st.text_input("Nome"), st.text_input("Instituição")
            t = st.selectbox("Time", ["Tecnologia", "Comercial", "Operações", "RH", "Financeiro"])
            di, df = st.date_input("Início"), st.date_input("Fim")
            if st.form_submit_button("CADASTRAR"):
                executar_sql("INSERT INTO contratos_estagio (estagiario, instituicao, data_inicio, data_fim, time_equipe) VALUES (:n, :i, :di, :df, :t)", {"n":n,"i":i,"di":di,"df":df, "t":t}); st.rerun()
    with col2:
        df_e = carregar_dados("contratos_estagio")
        for _, r in df_e.iterrows():
            with st.expander(f"👤 {r['estagiario']}"):
                ca, cb, cc, cd = st.columns(4)
                s, ae, af, ej = ca.checkbox("Solic.", value=bool(r['solic_contrato_dp']), key=f"s{r['id']}"), cb.checkbox("ETUS", value=bool(r['assina_etus']), key=f"ae{r['id']}"), cc.checkbox("Facul.", value=bool(r['assina_faculdade']), key=f"af{r['id']}"), cd.checkbox("Jurid.", value=bool(r['envio_juridico']), key=f"ej{r['id']}")
                if st.button("Salvar Status", key=f"svest{r['id']}"):
                    executar_sql("UPDATE contratos_estagio SET solic_contrato_dp=:s, assina_etus=:ae, assina_faculdade=:af, envio_juridico=:ej WHERE id=:id", {"s":s,"ae":ae,"af":af,"ej":ej,"id":r['id']}); st.rerun()
                if st.button("🗑️ Excluir", key=f"delest{r['id']}"):
                    executar_sql("DELETE FROM contratos_estagio WHERE id=:id", {"id":r['id']}); st.rerun()

# --- 12. MÓDULO IFOOD (FILTRO CORRETO) ---
elif menu == "🍔 IFOOD":
    st.subheader("Gestão iFood")
    lista_if = ["ETUS", "BHAZ", "E3J", "Evolution", "No Name"]
    col_u, col_l = st.columns([1, 2])
    with col_u:
        st.markdown('<div class="vaga-header">📤 UPLOAD NF IFOOD</div>', unsafe_allow_html=True)
        with st.form("f_if"):
            emp = st.selectbox("Empresa", lista_if)
            mes = st.selectbox("Mês", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
            arq = st.file_uploader("Anexar NF (PDF)", type="pdf")
            if st.form_submit_button("SALVAR NOTA"):
                if arq: executar_sql("INSERT INTO notas_fiscais_ifood (empresa, mes_referencia, arquivo_nf, nome_arquivo, data_upload) VALUES (:e,:m,:a,:n,:d)", {"e":emp,"m":mes,"a":arq.getvalue(),"n":arq.name,"d":date.today()}); st.rerun()
    with col_l:
        st.markdown('<div class="vaga-header">🔍 CONSULTA IFOOD</div>', unsafe_allow_html=True)
        f_if = st.multiselect("Filtrar por Empresa iFood", lista_if, default=lista_if)
        df_if = carregar_dados("notas_fiscais_ifood")
        if not df_if.empty:
            for _, r in df_if[df_if['empresa'].isin(f_if)].iterrows():
                with st.expander(f"📄 {r['empresa']} - {r['mes_referencia']}"):
                    st.download_button("📥 Baixar", r['arquivo_nf'], r['nome_arquivo'], key=f"dlif{r['id']}")
                    if st.button("🗑️ Excluir", key=f"delif{r['id']}"): executar_sql("DELETE FROM notas_fiscais_ifood WHERE id=:id", {"id":r['id']}); st.rerun()

# --- 13. MÓDULO OUTROS PAGAMENTOS (FILTRO CORRETO) ---
elif menu == "💸 OUTROS PAGAMENTOS":
    st.subheader("Pagamentos Plusdin, São Bernardo e Projeto")
    lista_pg = ["Plusdin", "São Bernardo", "Projeto Consegui Aprender"]
    col_u, col_l = st.columns([1, 2])
    with col_u:
        st.markdown('<div class="vaga-header">📤 NOVO LANÇAMENTO</div>', unsafe_allow_html=True)
        with st.form("f_pg"):
            emp = st.selectbox("Empresa", lista_pg)
            cat = st.radio("Categoria", ["PSB", "MDP"], horizontal=True)
            mes = st.selectbox("Mês", ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"])
            arq = st.file_uploader("PDF Comprovante", type="pdf")
            if st.form_submit_button("SALVAR PAGAMENTO"):
                if arq: executar_sql("INSERT INTO pagamentos_gerais (empresa, categoria, mes_referencia, arquivo_pg, nome_arquivo, data_upload) VALUES (:e,:c,:m,:a,:n,:d)", {"e":emp,"c":cat,"m":mes,"a":arq.getvalue(),"n":arq.name,"d":date.today()}); st.rerun()
    with col_l:
        st.markdown('<div class="vaga-header">🔍 CONSULTA PAGAMENTOS</div>', unsafe_allow_html=True)
        f_pg = st.multiselect("Filtrar por Empresa Geral", lista_pg, default=lista_pg)
        df_pg = carregar_dados("pagamentos_gerais")
        if not df_pg.empty:
            for _, r in df_pg[df_pg['empresa'].isin(f_pg)].iterrows():
                with st.expander(f"💰 {r['empresa']} | {r['categoria']} - {r['mes_referencia']}"):
                    st.download_button("📥 Baixar", r['arquivo_pg'], r['nome_arquivo'], key=f"dlpg{r['id']}")
                    if st.button("🗑️ Excluir", key=f"delpg{r['id']}"): executar_sql("DELETE FROM pagamentos_gerais WHERE id=:id", {"id":r['id']}); st.rerun()

# --- 14. MÓDULO PERÍODO DE EXPERIÊNCIA (COMPLETO) ---
elif menu == "⏳ PERÍODO DE EXPERIÊNCIA":
    st.subheader("Controle de Avaliação de Experiência (45 e 90 dias)")
    col_cad, col_gst = st.columns([1, 2])
    with col_cad:
        st.markdown('<div class="vaga-header">➕ CADASTRAR NOVO PERÍODO</div>', unsafe_allow_html=True)
        with st.form("f_exp_cad", clear_on_submit=True):
            n_exp = st.text_input("Nome do Prestador/Estagiário")
            c_exp = st.text_input("Cargo")
            t_exp = st.selectbox("Time", ["Tecnologia", "Comercial", "Operações", "RH", "Financeiro", "Marketing"])
            d_ini = st.date_input("Data de Início", value=date.today())
            if st.form_submit_button("CADASTRAR CONTROLE"):
                if n_exp:
                    executar_sql("INSERT INTO controle_experiencia (nome, cargo, time_equipe, data_inicio) VALUES (:n, :c, :t, :d)", {"n": n_exp, "c": c_exp, "t": t_exp, "d": d_ini})
                    st.success("Cadastrado!"); st.rerun()
    with col_gst:
        st.markdown('<div class="vaga-header">📋 GESTÃO DE AVALIAÇÕES</div>', unsafe_allow_html=True)
        df_exp = carregar_dados("controle_experiencia")
        if not df_exp.empty:
            for _, r in df_exp.iterrows():
                d45 = r['data_inicio'] + pd.Timedelta(days=45)
                d90 = r['data_inicio'] + pd.Timedelta(days=90)
                with st.expander(f"👤 {r['nome']} - {r['cargo']} ({r['time_equipe']})"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**1º Período (45d): {d45.strftime('%d/%m/%Y')}**")
                        v1 = st.checkbox("Avaliação 1 Feita", value=bool(r['av1_feito']), key=f"v1{r['id']}")
                        r1 = st.text_input("Avaliador 1", value=r['av1_responsavel'] or "", key=f"r1{r['id']}")
                        dt1 = st.date_input("Data Av. 1", value=r['av1_data'] if r['av1_data'] else d45, key=f"dt1{r['id']}")
                    with c2:
                        st.write(f"**2º Período (90d): {d90.strftime('%d/%m/%Y')}**")
                        v2 = st.checkbox("Avaliação 2 Feita", value=bool(r['av2_feito']), key=f"v2{r['id']}")
                        r2 = st.text_input("Avaliador 2", value=r['av2_responsavel'] or "", key=f"r2{r['id']}")
                        dt2 = st.date_input("Data Av. 2", value=r['av2_data'] if r['av2_data'] else d90, key=f"dt2{r['id']}")
                    
                    if st.button("💾 Salvar Dados de Experiência", key=f"svexp{r['id']}"):
                        executar_sql("UPDATE controle_experiencia SET av1_feito=:v1, av1_responsavel=:r1, av1_data=:dt1, av2_feito=:v2, av2_responsavel=:r2, av2_data=:dt2 WHERE id=:id", 
                                    {"v1": v1, "r1": r1, "dt1": dt1, "v2": v2, "r2": r2, "dt2": dt2, "id": r['id']})
                        st.success("Salvo!"); st.rerun()
                    if st.button("🗑️ Excluir Registro", key=f"delexp{r['id']}"):
                        executar_sql("DELETE FROM controle_experiencia WHERE id=:id", {"id": r['id']}); st.rerun()

# --- 15. MÓDULO COLABORADORES ---
elif menu == "👥 COLABORADORES":
    st.subheader("Gestão de Benefícios e Contratos")
    df_col = carregar_dados("colaboradores_ativos")
    
    lista_modalidades = ["CLT", "PJ", "Estagiário", "Trainee", "Freelancer"]

    with st.expander("➕ CADASTRAR NOVO COLABORADOR MANUALMENTE"):
        with st.form("f_col_manual"):
            n_col = st.text_input("Nome")
            t_col = st.selectbox("Tipo de Contratação", lista_modalidades)
            d_adm = st.date_input("Data de Admissão", value=date.today())
            if st.form_submit_button("CADASTRAR"):
                executar_sql("INSERT INTO colaboradores_ativos (nome, tipo, data_admissao) VALUES (:n, :t, :d)", 
                            {"n":n_col, "t":t_col, "d":d_adm})
                st.success("Colaborador cadastrado!"); st.rerun()

    if not df_col.empty:
        for _, r in df_col.iterrows():
            with st.expander(f"👤 {r['nome']} [{r['tipo']}]"):
                c_tipo, c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1, 1])
                
                # Permite alterar o tipo de contratação de quem já está na lista
                novo_tipo = c_tipo.selectbox("Alterar Tipo", lista_modalidades, 
                                            index=lista_modalidades.index(r['tipo']) if r['tipo'] in lista_modalidades else 0,
                                            key=f"tipo{r['id']}")
                
                star = c1.checkbox("Starbem", value=bool(r['cad_starbem']), key=f"star{r['id']}")
                amil = c2.checkbox("AMIL", value=bool(r['incl_amil']), key=f"amil{r['id']}")
                ifoo = c3.checkbox("iFood", value=bool(r['ifood_ativo']), key=f"ifoo{r['id']}")
                equi = c4.checkbox("Equipamento", value=bool(r['equipamento_entregue']), key=f"equi{r['id']}")
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("💾 Salvar Alterações", key=f"svb{r['id']}"):
                    executar_sql("""
                        UPDATE colaboradores_ativos 
                        SET tipo=:t, cad_starbem=:s, incl_amil=:a, ifood_ativo=:i, equipamento_entregue=:e 
                        WHERE id=:id
                    """, {"t":novo_tipo, "s":star, "a":amil, "i":ifoo, "e":equi, "id":r['id']})
                    st.success("Dados atualizados!"); st.rerun()
                
                if col_btn2.button("🗑️ Excluir Colaborador", key=f"delcol{r['id']}"):
                    executar_sql("DELETE FROM colaboradores_ativos WHERE id=:id", {"id":r['id']})
                    st.rerun()




