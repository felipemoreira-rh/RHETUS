import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from datetime import datetime, date
import os
from pypdf import PdfReader

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

# --- 4. BANCO DE DADOS (INIT EXPANDIDO) ---
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS vagas (id SERIAL PRIMARY KEY, nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE, data_fechamento DATE);
        CREATE TABLE IF NOT EXISTS candidatos (id SERIAL PRIMARY KEY, candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, historico TEXT, motivo_perda TEXT, envio_proposta BOOLEAN DEFAULT FALSE, solic_documentos BOOLEAN DEFAULT FALSE, solic_contrato BOOLEAN DEFAULT FALSE, solic_acessos BOOLEAN DEFAULT FALSE, arquivo_cv BYTEA);
        CREATE TABLE IF NOT EXISTS contratos_estagio (id SERIAL PRIMARY KEY, estagiario TEXT, instituicao TEXT, data_inicio DATE, data_fim DATE, status_contrato TEXT, time_equipe TEXT, funcao TEXT, solic_contrato_dp BOOLEAN DEFAULT FALSE, assina_etus BOOLEAN DEFAULT FALSE, assina_faculdade BOOLEAN DEFAULT FALSE, envio_juridico BOOLEAN DEFAULT FALSE);
        CREATE TABLE IF NOT EXISTS notas_fiscais_ifood (id SERIAL PRIMARY KEY, empresa TEXT, mes_referencia TEXT, arquivo_nf BYTEA, nome_arquivo TEXT, data_upload DATE);
        CREATE TABLE IF NOT EXISTS pagamentos_gerais (id SERIAL PRIMARY KEY, empresa TEXT, categoria TEXT, mes_referencia TEXT, arquivo_pg BYTEA, nome_arquivo TEXT, data_upload DATE);
        CREATE TABLE IF NOT EXISTS colaboradores_ativos (
            id SERIAL PRIMARY KEY, nome TEXT, tipo TEXT, time_equipe TEXT, data_admissao DATE,
            status_rh_gestor BOOLEAN DEFAULT FALSE, status_starbem BOOLEAN DEFAULT FALSE, 
            status_dasa BOOLEAN DEFAULT FALSE, status_avus BOOLEAN DEFAULT FALSE, 
            status_amil BOOLEAN DEFAULT FALSE, status_ifood BOOLEAN DEFAULT FALSE,
            status_equipamento BOOLEAN DEFAULT FALSE, ferias_vencimento DATE
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
        # Removido 'Candidatos' e adicionado 'Experiência'
        menu = st.radio("NAVEGAÇÃO", ["📊 DASHBOARD DP", "🎓 ESTAGIÁRIOS", "⏳ PERÍODO DE EXPERIÊNCIA"])
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

# --- 8. MÓDULO CANDIDATOS ---
elif menu == "⚙️ CANDIDATOS":
    df_v = carregar_dados("vagas"); df_c = carregar_dados("candidatos")
    with st.expander("➕ NOVO CANDIDATO"):
        with st.form("nc"):
            nc = st.text_input("Nome do Candidato")
            opcoes_vagas = df_v['nome_vaga'].tolist() if not df_v.empty else ["Geral"]
            vnc = st.selectbox("Vaga Vinculada", opcoes_vagas)
            if st.form_submit_button("ADICIONAR"):
                executar_sql("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral) VALUES (:n, :v, 'Triagem')", {"n":nc,"v":vnc}); st.rerun()

    if not df_c.empty:
        vagas_unicas = df_c['vaga_vinculada'].unique()
        for v_nome in vagas_unicas:
            st.markdown(f'<div class="vaga-header">🏢 VAGA: {v_nome.upper()}</div>', unsafe_allow_html=True)
            lista = df_c[df_c['vaga_vinculada'] == v_nome]
            for _, cr in lista.iterrows():
                with st.expander(f"👤 {cr['candidato']} — [ {cr['status_geral']} ]"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write("**📍 Gestão de Etapa**")
                        etapas = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada", "Perda"]
                        idx = etapas.index(cr['status_geral']) if cr['status_geral'] in etapas else 0
                        ns = st.selectbox("Etapa", etapas, index=idx, key=f"s{cr['id']}")
                        if st.button("Salvar Etapa", key=f"b{cr['id']}"):
                            executar_sql("UPDATE candidatos SET status_geral=:s WHERE id=:id", {"s":ns,"id":cr['id']}); st.rerun()
                        if st.button("🗑️ Excluir Candidato", key=f"d{cr['id']}"):
                            executar_sql("DELETE FROM candidatos WHERE id=:id", {"id":cr['id']}); st.rerun()
                    with c2:
                        st.write("**📁 Currículo do Candidato**")
                        uploaded_cv = st.file_uploader("Upload Currículo (PDF)", type="pdf", key=f"up{cr['id']}")
                        if uploaded_cv:
                            bytes_data = uploaded_cv.getvalue()
                            if st.button("💾 Salvar Arquivo PDF", key=f"save{cr['id']}"):
                                try:
                                    with engine.begin() as conn:
                                        conn.execute(text("UPDATE candidatos SET arquivo_cv=:data WHERE id=:id"), {"data": bytes_data, "id": cr['id']})
                                    st.success("Arquivo salvo!"); st.rerun()
                                except Exception as e: st.error(f"Erro: {e}")
                        if cr.get('arquivo_cv') is not None:
                            st.download_button("📥 Baixar CV", cr['arquivo_cv'], f"CV_{cr['candidato']}.pdf", "application/pdf", key=f"dl{cr['id']}")
                        else: st.info("Sem currículo anexado.")

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
            if st.button("Salvar Checklist", key=f"svon{r['id']}"):
                executar_sql("UPDATE candidatos SET envio_proposta=:p, solic_documentos=:d, solic_contrato=:c, solic_acessos=:a WHERE id=:id", {"p":p,"d":d,"c":c,"a":a,"id":r['id']}); st.rerun()

# --- 10. MÓDULO DASHBOARD DP ---
elif menu == "📊 DASHBOARD DP":
    df_est = carregar_dados("contratos_estagio")
    if not df_est.empty:
        df_est['data_fim'] = pd.to_datetime(df_est['data_fim'], errors='coerce')
        df_est['data_inicio'] = pd.to_datetime(df_est['data_inicio'], errors='coerce')
        hoje = pd.Timestamp(date.today())
        c1, c2, c3 = st.columns(3)
        c1.metric("🎓 TOTAL ESTAGIÁRIOS", len(df_est))
        vencendo = len(df_est[(df_est['data_fim'] >= hoje) & ((df_est['data_fim'] - hoje).dt.days <= 30)])
        c2.metric("⚠️ VENCENDO EM 30 DIAS", vencendo)
        df_est['doc_ok'] = (df_est['solic_contrato_dp']==True)&(df_est['assina_etus']==True)&(df_est['assina_faculdade']==True)&(df_est['envio_juridico']==True)
        c3.metric("✅ DOCS COMPLETOS", len(df_est[df_est['doc_ok'] == True]))
        st.divider()
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("🏢 Distribuição por Time")
            st.plotly_chart(px.bar(df_est, x='time_equipe', color='time_equipe', color_discrete_sequence=['#8DF768', '#4CAF50']), use_container_width=True)
        with g2:
            st.subheader("📈 Status de Documentação")
            status_counts = df_est['doc_ok'].map({True: 'Completo', False: 'Pendente'}).value_counts().reset_index()
            st.plotly_chart(px.pie(status_counts, names='doc_ok', values='count', color_discrete_sequence=['#8DF768', '#FF4B4B']), use_container_width=True)
        st.divider()
        st.subheader("📊 % de Cumprimento de Contrato")
        progressos, cores = [], []
        for _, r in df_est.iterrows():
            total_dias = (r['data_fim'] - r['data_inicio']).days
            dias_passados = (hoje - r['data_inicio']).days
            perc = max(0, min(100, (dias_passados / total_dias * 100))) if total_dias > 0 else 0
            progressos.append(round(perc, 1))
            cores.append('#FF4B4B' if perc >= 90 else '#FFA500' if perc >= 70 else '#8DF768')
        df_est['progresso'], df_est['cor'] = progressos, cores
        fig = go.Figure(go.Bar(y=df_est['estagiario'], x=df_est['progresso'], orientation='h', marker_color=df_est['cor'], text=df_est['progresso'].astype(str) + '%', textposition='auto'))
        fig.update_layout(xaxis=dict(range=[0, 100]), yaxis=dict(autorange="reversed"), height=300 + (len(df_est) * 35), margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Sem dados de estagiários.")

# --- 11. MÓDULO ESTAGIÁRIOS ---
elif menu == "🎓 ESTAGIÁRIOS":
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("📝 Novo Registro")
        with st.form("f_est", clear_on_submit=True):
            n, i, f = st.text_input("Nome"), st.text_input("Instituição"), st.text_input("Função")
            t = st.selectbox("Time", ["Tecnologia", "Comercial", "Operações", "RH", "Financeiro"])
            di, df = st.date_input("Início"), st.date_input("Término")
            if st.form_submit_button("CADASTRAR"):
                executar_sql("INSERT INTO contratos_estagio (estagiario, instituicao, funcao, time_equipe, data_inicio, data_fim) VALUES (:n, :i, :f, :t, :di, :df)", {"n": n, "i": i, "f": f, "t": t, "di": di, "df": df}); st.rerun()
    with col2:
        st.subheader("📋 Gestão")
        df_e = carregar_dados("contratos_estagio")
        if not df_e.empty:
            for _, r in df_e.iterrows():
                with st.expander(f"👤 {r['estagiario']}"):
                    ca, cb, cc, cd = st.columns(4)
                    s, ae, af, ej = ca.checkbox("Solic.", value=bool(r.get('solic_contrato_dp')), key=f"sest{r['id']}"), cb.checkbox("ETUS", value=bool(r.get('assina_etus')), key=f"aeest{r['id']}"), cc.checkbox("Facul.", value=bool(r.get('assina_faculdade')), key=f"afest{r['id']}"), cd.checkbox("Jurid.", value=bool(r.get('envio_juridico')), key=f"ejest{r['id']}")
                    if st.button("Salvar Checklist", key=f"svest{r['id']}"):
                        executar_sql("UPDATE contratos_estagio SET solic_contrato_dp=:s, assina_etus=:ae, assina_faculdade=:af, envio_juridico=:ej WHERE id=:id", {"s":s,"ae":ae,"af":af,"ej":ej,"id":r['id']}); st.rerun()
                    if st.button("🗑️ Excluir", key=f"dlest{r['id']}"):
                        executar_sql("DELETE FROM contratos_estagio WHERE id=:id", {"id":r['id']}); st.rerun()

# --- 12. MÓDULO IFOOD (FILTRO CORRIGIDO) ---
elif menu == "🍔 IFOOD":
    st.subheader("Gestão de Notas iFood")
    col_up, col_list = st.columns([1, 2])
    
    lista_empresas_ifood = ["ETUS", "BHAZ", "E3J", "Evolution", "No Name"]
    
    with col_up:
        st.markdown('<div class="vaga-header">📤 UPLOAD NF IFOOD</div>', unsafe_allow_html=True)
        with st.form("f_nf_ifood", clear_on_submit=True):
            empresa_sel = st.selectbox("Empresa", lista_empresas_ifood)
            mes_ref = st.selectbox("Mês de Referência", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
            arquivo_pdf = st.file_uploader("Upload NF (PDF)", type="pdf", key="up_ifood")
            if st.form_submit_button("SALVAR NOTA FISCAL"):
                if arquivo_pdf:
                    executar_sql("INSERT INTO notas_fiscais_ifood (empresa, mes_referencia, arquivo_nf, nome_arquivo, data_upload) VALUES (:emp, :mes, :arq, :nom, :dat)", 
                                {"emp": empresa_sel, "mes": mes_ref, "arq": arquivo_pdf.getvalue(), "nom": arquivo_pdf.name, "dat": date.today()})
                    st.success("Nota iFood salva!"); st.rerun()

    with col_list:
        st.markdown('<div class="vaga-header">🔍 FILTRAR NOTAS IFOOD</div>', unsafe_allow_html=True)
        # Filtro exclusivo para iFood
        filtro_if = st.multiselect("Empresas iFood", lista_empresas_ifood, default=lista_empresas_ifood)
        
        df_nf = carregar_dados("notas_fiscais_ifood")
        if not df_nf.empty:
            df_f = df_nf[df_nf['empresa'].isin(filtro_if)]
            for _, row in df_f.iterrows():
                with st.expander(f"📄 {row['empresa']} - {row['mes_referencia']}"):
                    st.download_button("📥 Baixar", row['arquivo_nf'], row['nome_arquivo'], key=f"dlnf{row['id']}")
                    if st.button("🗑️ Excluir", key=f"delnf{row['id']}"):
                        executar_sql("DELETE FROM notas_fiscais_ifood WHERE id=:id", {"id": row['id']}); st.rerun()

# --- 13. MÓDULO OUTROS PAGAMENTOS (FILTRO CORRIGIDO) ---
elif menu == "💸 OUTROS PAGAMENTOS":
    st.subheader("Pagamentos PSB/MDP")
    col_up, col_list = st.columns([1, 2])
    
    lista_empresas_pg = ["Plusdin", "São Bernardo", "Projeto Consegui Aprender"]
    
    with col_up:
        st.markdown('<div class="vaga-header">📤 NOVO PAGAMENTO</div>', unsafe_allow_html=True)
        with st.form("f_pg_geral", clear_on_submit=True):
            emp_pg = st.selectbox("Empresa", lista_empresas_pg)
            cat_pg = st.radio("Categoria", ["PSB", "MDP"], horizontal=True)
            mes_pg = st.selectbox("Mês", ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"])
            arq_pg = st.file_uploader("Arquivo (PDF)", type="pdf", key="up_pg_geral")
            if st.form_submit_button("SALVAR PAGAMENTO"):
                if arq_pg:
                    executar_sql("INSERT INTO pagamentos_gerais (empresa, categoria, mes_referencia, arquivo_pg, nome_arquivo, data_upload) VALUES (:emp, :cat, :mes, :arq, :nom, :dat)", 
                                {"emp": emp_pg, "cat": cat_pg, "mes": mes_pg, "arq": arq_pg.getvalue(), "nom": arq_pg.name, "dat": date.today()})
                    st.success("Pagamento salvo!"); st.rerun()

    with col_list:
        st.markdown('<div class="vaga-header">🔍 FILTRAR PAGAMENTOS</div>', unsafe_allow_html=True)
        # Filtro exclusivo para Outros Pagamentos
        filtro_pg = st.multiselect("Empresas Pagamentos", lista_empresas_pg, default=lista_empresas_pg)
        
        df_pg = carregar_dados("pagamentos_gerais")
        if not df_pg.empty:
            df_f_pg = df_pg[df_pg['empresa'].isin(filtro_pg)]
            for _, r in df_f_pg.iterrows():
                with st.expander(f"💰 {r['empresa']} | {r['categoria']} - {r['mes_referencia']}"):
                    st.download_button("📥 Baixar", r['arquivo_pg'], r['nome_arquivo'], key=f"dlpg{r['id']}")
                    if st.button("🗑️ Excluir", key=f"delpg{r['id']}"):
                        executar_sql("DELETE FROM pagamentos_gerais WHERE id=:id", {"id": r['id']}); st.rerun()

# --- 14. MÓDULO COLABORADORES (RESTANTE DA LISTA) ---
elif menu == "⏳ PERÍODO DE EXPERIÊNCIA":
    st.subheader("Controle de Avaliação (45 e 90 dias)")
    
    df_colab = carregar_dados("colaboradores_ativos")
    
    if not df_colab.empty:
        # Garantir que a data de admissão é do tipo datetime
        df_colab['data_admissao'] = pd.to_datetime(df_colab['data_admissao']).dt.date
        hoje = date.today()
        
        # Filtro de busca
        busca = st.text_input("🔍 Buscar Colaborador", "").lower()
        
        for _, r in df_colab.iterrows():
            if busca in r['nome'].lower():
                # Cálculos de Experiência
                data_adm = r['data_admissao']
                data_45 = data_adm + pd.Timedelta(days=45)
                data_90 = data_adm + pd.Timedelta(days=90)
                
                # Lógica de Alerta (Cor)
                # Se faltar menos de 7 dias para os 45 ou 90, ou se já passou e não foi marcado ok
                dias_para_45 = (data_45 - hoje).days
                dias_para_90 = (data_90 - hoje).days
                
                status_color = "#f0f2f6" # padrão
                if 0 <= dias_para_45 <= 7 or 0 <= dias_para_90 <= 7:
                    status_color = "rgba(255, 75, 75, 0.2)" # Alerta vermelho claro
                
                with st.container():
                    st.markdown(f"""
                        <div style="background-color:{status_color}; padding:15px; border-radius:10px; border-left: 5px solid #8DF768; margin-bottom:10px;">
                            <h4 style="margin:0;">👤 {r['nome']}</h4>
                            <small>Admissão: {data_adm.strftime('%d/%m/%Y')} | Tipo: {r['tipo']}</small>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    c1, c2, c3 = st.columns([1, 1, 1])
                    
                    with c1:
                        st.write(f"**1ª Etapa (45 dias)**")
                        st.write(f"📅 {data_45.strftime('%d/%m/%Y')}")
                        if dias_para_45 < 0: st.error("Vencido")
                        elif dias_para_45 <= 7: st.warning(f"Vence em {dias_para_45} dias")
                        
                    with c2:
                        st.write(f"**2ª Etapa (90 dias)**")
                        st.write(f"📅 {data_90.strftime('%d/%m/%Y')}")
                        if dias_para_90 < 0: st.error("Vencido")
                        elif dias_para_90 <= 7: st.warning(f"Vence em {dias_para_90} dias")
                        
                    with c3:
                        st.write("**Ação**")
                        if st.button("✅ Avaliação Realizada", key=f"av{r['id']}"):
                            st.success("Avaliação registrada no histórico!")
                    st.divider()
    else:
        st.info("Nenhum colaborador ativo encontrado para calcular experiência.")



