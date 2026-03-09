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

# --- 4. BANCO DE DADOS (INIT) ---
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS vagas (id SERIAL PRIMARY KEY, nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE, data_fechamento DATE);
        CREATE TABLE IF NOT EXISTS candidatos (id SERIAL PRIMARY KEY, candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, historico TEXT, motivo_perda TEXT, envio_proposta BOOLEAN DEFAULT FALSE, solic_documentos BOOLEAN DEFAULT FALSE, solic_contrato BOOLEAN DEFAULT FALSE, solic_acessos BOOLEAN DEFAULT FALSE, arquivo_cv BYTEA);
        CREATE TABLE IF NOT EXISTS contratos_estagio (id SERIAL PRIMARY KEY, estagiario TEXT, instituicao TEXT, data_inicio DATE, data_fim DATE, status_contrato TEXT, time_equipe TEXT, funcao TEXT, solic_contrato_dp BOOLEAN DEFAULT FALSE, assina_etus BOOLEAN DEFAULT FALSE, assina_faculdade BOOLEAN DEFAULT FALSE, envio_juridico BOOLEAN DEFAULT FALSE);
    """))

# --- 5. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    area_sel = st.selectbox("GERENCIAMENTO", ["RH - Recrutamento", "DP - Departamento Pessoal"])
    if area_sel == "RH - Recrutamento":
        menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])
    else:
        menu = st.radio("NAVEGAÇÃO", ["📊 DASHBOARD DP", "🎓 ESTAGIÁRIOS"])

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
                                    st.success("Arquivo salvo com sucesso!"); st.rerun()
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

# --- 10. MÓDULO DASHBOARD DP (ATUALIZADO COM GRÁFICO DE CUMPRIMENTO) ---
elif menu == "📊 DASHBOARD DP":
    df_est = carregar_dados("contratos_estagio")
    if not df_est.empty:
        df_est['data_fim'] = pd.to_datetime(df_est['data_fim'], errors='coerce')
        df_est['data_inicio'] = pd.to_datetime(df_est['data_inicio'], errors='coerce')
        hoje = pd.Timestamp(date.today())
        
        # 1. Indicadores
        c1, c2, c3 = st.columns(3)
        c1.metric("🎓 TOTAL", len(df_est))
        vencendo = len(df_est[(df_est['data_fim'] >= hoje) & ((df_est['data_fim'] - hoje).dt.days <= 30)])
        c2.metric("⚠️ VENCENDO EM 30 DIAS", vencendo)
        docs_ok = len(df_est[(df_est['solic_contrato_dp']==True)&(df_est['assina_etus']==True)&(df_est['assina_faculdade']==True)&(df_est['envio_juridico']==True)])
        c3.metric("✅ DOCS COMPLETOS", docs_ok)

        st.divider()
        st.subheader("📊 % de Cumprimento de Contrato")

        # 2. Cálculo de Progresso e Cores
        progressos = []
        cores = []
        for _, r in df_est.iterrows():
            total_dias = (r['data_fim'] - r['data_inicio']).days
            dias_passados = (hoje - r['data_inicio']).days
            
            # Garante limites entre 0 e 100%
            perc = max(0, min(100, (dias_passados / total_dias * 100))) if total_dias > 0 else 0
            progressos.append(round(perc, 1))
            
            # Lógica de Cor: Verde (Longe), Laranja (Perto), Vermelho (Vencendo/Vencido)
            if perc >= 90: cores.append('#FF4B4B') # Vermelho
            elif perc >= 70: cores.append('#FFA500') # Laranja
            else: cores.append('#8DF768') # Verde

        df_est['progresso'] = progressos
        df_est['cor'] = cores

        # 3. Gráfico de Barras Progressivo
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df_est['estagiario'],
            x=df_est['progresso'],
            orientation='h',
            marker_color=df_est['cor'],
            text=df_est['progresso'].astype(str) + '%',
            textposition='auto',
            hovertemplate="<b>%{y}</b><br>Cumprido: %{x}%<extra></extra>"
        ))
        fig.update_layout(
            xaxis=dict(title="Porcentagem Concluída", range=[0, 100]),
            yaxis=dict(autorange="reversed"),
            height=400 + (len(df_est) * 30), # Altura dinâmica baseada no número de estagiários
            margin=dict(l=0, r=0, t=30, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)

    else: st.info("Sem dados de estagiários.")

# --- 11. MÓDULO ESTAGIÁRIOS ---
elif menu == "🎓 ESTAGIÁRIOS":
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("📝 Novo Registro")
        with st.form("f_est", clear_on_submit=True):
            n = st.text_input("Nome"); i = st.text_input("Instituição"); f = st.text_input("Função")
            t = st.selectbox("Time", ["Tecnologia", "Comercial", "Operações", "RH", "Financeiro"])
            di = st.date_input("Início"); df = st.date_input("Término")
            if st.form_submit_button("CADASTRAR"):
                executar_sql("INSERT INTO contratos_estagio (estagiario, instituicao, funcao, time_equipe, data_inicio, data_fim) VALUES (:n, :i, :f, :t, :di, :df)", 
                             {"n": n, "i": i, "f": f, "t": t, "di": di, "df": df}); st.rerun()
    with col2:
        st.subheader("📋 Gestão")
        df_e = carregar_dados("contratos_estagio")
        if not df_e.empty:
            for _, r in df_e.iterrows():
                with st.expander(f"👤 {r['estagiario']}"):
                    ca, cb, cc, cd = st.columns(4)
                    s = ca.checkbox("Solicit.", value=bool(r.get('solic_contrato_dp')), key=f"sest{r['id']}")
                    ae = cb.checkbox("ETUS", value=bool(r.get('assina_etus')), key=f"aeest{r['id']}")
                    af = cc.checkbox("Facul.", value=bool(r.get('assina_faculdade')), key=f"afest{r['id']}")
                    ej = cd.checkbox("Jurid.", value=bool(r.get('envio_juridico')), key=f"ejest{r['id']}")
                    if st.button("Salvar Checklist", key=f"svest{r['id']}"):
                        executar_sql("UPDATE contratos_estagio SET solic_contrato_dp=:s, assina_etus=:ae, assina_faculdade=:af, envio_juridico=:ej WHERE id=:id", {"s":s,"ae":ae,"af":af,"ej":ej,"id":r['id']}); st.rerun()
                    if st.button("🗑️ Excluir", key=f"dlest{r['id']}"):
                        executar_sql("DELETE FROM contratos_estagio WHERE id=:id", {"id":r['id']}); st.rerun()
