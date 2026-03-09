import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from datetime import datetime, date
import os
import google.generativeai as genai
from pypdf import PdfReader
from fpdf import FPDF

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RH ETUS - Gestão Pro", layout="wide", page_icon="logo.png")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    html, body, [class*="css"], [data-testid="stSidebar"] { font-family: 'Space Grotesk', sans-serif !important; }
    .header-rh { font-size: 42px; font-weight: 700; color: #8DF768; margin-bottom: 30px; border-left: 10px solid #8DF768; padding-left: 15px; }
    .vaga-header { background-color: rgba(141, 247, 104, 0.2); color: inherit; padding: 12px; border-radius: 8px; margin-top: 20px; margin-bottom: 10px; font-weight: bold; border-left: 5px solid #8DF768; }
    .parecer-box { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #8DF768; color: #f0f0f0; margin-top: 15px; white-space: pre-wrap; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONFIGURAÇÃO IA ---
model_ai = None
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model_ai = genai.GenerativeModel('gemini-1.5-flash-latest')

# --- 3. MOTOR DE BANCO DE DADOS ---
@st.cache_resource
def get_engine():
    try:
        DB_URL = st.secrets["postgres"]["url"]
        return create_engine(DB_URL, pool_size=5, max_overflow=10, connect_args={"sslmode": "require"})
    except:
        st.stop()

engine = get_engine()

# --- 4. FUNÇÕES DE APOIO ---
def executar_sql(query, params=None):
    try:
        with engine.begin() as conn:
            conn.execute(text(query), params or {})
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro SQL: {e}"); return False

@st.cache_data(ttl=2)
def carregar_dados(tabela):
    try: 
        df = pd.read_sql(f"SELECT * FROM {tabela} ORDER BY id DESC", engine)
        return df
    except: 
        return pd.DataFrame()

def extrair_texto_pdf(file):
    reader = PdfReader(file)
    texto = ""
    for page in reader.pages:
        content = page.extract_text()
        if content: texto += content
    return texto

def gerar_parecer_ia(nome_cand, nome_vaga, texto_cv, s_atual, s_pret):
    prompt = f"""
    Gere um parecer técnico detalhado para: {nome_cand} na vaga {nome_vaga}.
    Analista Responsável: Felipe da Silva Moreira Cristo.
    Siga rigorosamente os 6 tópicos: Formação, Experiência, Salário Atual ({s_atual}), Pretensão ({s_pret}), Soft Skills e Adequação.
    Use linguagem formal e parágrafos curtos. Conteúdo do CV: {texto_cv}
    """
    response = model_ai.generate_content(prompt)
    return response.text

def gerar_pdf_parecer(texto_parecer):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "RH ETUS - PARECER TECNICO", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", "", 11)
    txt = texto_parecer.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 7, txt)
    return pdf.output()

# --- 5. INICIALIZAÇÃO E ATUALIZAÇÃO DO BANCO ---
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS vagas (id SERIAL PRIMARY KEY, nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE, data_fechamento DATE);
        CREATE TABLE IF NOT EXISTS candidatos (id SERIAL PRIMARY KEY, candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, historico TEXT, motivo_perda TEXT, envio_proposta BOOLEAN DEFAULT FALSE, solic_documentos BOOLEAN DEFAULT FALSE, solic_contrato BOOLEAN DEFAULT FALSE, solic_acessos BOOLEAN DEFAULT FALSE, parecer_ia TEXT);
        CREATE TABLE IF NOT EXISTS contratos_estagio (id SERIAL PRIMARY KEY, estagiario TEXT, instituicao TEXT, data_inicio DATE, data_fim DATE, status_contrato TEXT, time_equipe TEXT, funcao TEXT, solic_contrato_dp BOOLEAN DEFAULT FALSE, assina_etus BOOLEAN DEFAULT FALSE, assina_faculdade BOOLEAN DEFAULT FALSE, envio_juridico BOOLEAN DEFAULT FALSE);
        
        -- Garante que a coluna parecer_ia existe (caso a tabela tenha sido criada antes)
        DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='candidatos' AND column_name='parecer_ia') THEN
                ALTER TABLE candidatos ADD COLUMN parecer_ia TEXT;
            END IF;
        END $$;
    """))

# --- 6. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    area_sel = st.selectbox("GERENCIAMENTO", ["RH - Recrutamento", "DP - Departamento Pessoal"])
    if area_sel == "RH - Recrutamento":
        menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])
    else:
        menu = st.radio("NAVEGAÇÃO", ["📊 DASHBOARD DP", "🎓 ESTAGIÁRIOS"])

st.markdown(f'<div class="header-rh">{menu}</div>', unsafe_allow_html=True)

# --- 7. MÓDULO RH: CANDIDATOS ---
if menu == "⚙️ CANDIDATOS":
    df_v = carregar_dados("vagas"); df_c = carregar_dados("candidatos")
    
    with st.expander("➕ NOVO CANDIDATO"):
        if not df_v.empty:
            with st.form("nc"):
                nc = st.text_input("Nome"); vnc = st.selectbox("Vaga", df_v['nome_vaga'].tolist())
                if st.form_submit_button("ADICIONAR"):
                    executar_sql("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral) VALUES (:n, :v, 'Triagem')", {"n":nc,"v":vnc}); st.rerun()
    
    for _, vr in df_v.iterrows():
        if not df_c.empty:
            lista = df_c[df_c['vaga_vinculada'] == vr['nome_vaga']]
            if not lista.empty:
                st.markdown(f'<div class="vaga-header">🏢 {vr["nome_vaga"].upper()}</div>', unsafe_allow_html=True)
                for _, cr in lista.iterrows():
                    with st.expander(f"👤 {cr['candidato']} - {cr['status_geral']}"):
                        c_et, c_ia = st.columns(2)
                        with c_et:
                            status_opcoes = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada", "Perda"]
                            idx_atual = status_opcoes.index(cr['status_geral']) if cr['status_geral'] in status_opcoes else 0
                            ns = st.selectbox("Etapa", status_opcoes, key=f"s{cr['id']}", index=idx_atual)
                            if st.button("Salvar Etapa", key=f"b{cr['id']}"):
                                executar_sql("UPDATE candidatos SET status_geral=:s WHERE id=:id", {"s":ns,"id":cr['id']}); st.rerun()
                        
                        with c_ia:
                            st.write("**🤖 IA: Gerar Parecer**")
                            cv = st.file_uploader("PDF do Currículo", type="pdf", key=f"p{cr['id']}")
                            sa = st.text_input("Salário Atual", key=f"sa{cr['id']}")
                            sp = st.text_input("Pretensão", key=f"sp{cr['id']}")
                            if cv and st.button("✨ Analisar e Salvar", key=f"gi{cr['id']}"):
                                with st.spinner("IA Trabalhando..."):
                                    txt_cv = extrair_texto_pdf(cv)
                                    pi_gerado = gerar_parecer_ia(cr['candidato'], vr['nome_vaga'], txt_cv, sa, sp)
                                    executar_sql("UPDATE candidatos SET parecer_ia=:p WHERE id=:id", {"p":pi_gerado,"id":cr['id']})
                                    st.success("Parecer gerado com sucesso!")
                                    st.rerun()
                        
                        # VERIFICAÇÃO SEGURA DA COLUNA 'parecer_ia'
                        if 'parecer_ia' in cr and pd.notnull(cr['parecer_ia']) and str(cr['parecer_ia']).strip() != "":
                            st.divider()
                            st.markdown("### 📄 Parecer Técnico Detalhado")
                            st.markdown(f'<div class="parecer-box">{cr["parecer_ia"]}</div>', unsafe_allow_html=True)
                            
                            pdf_data = gerar_pdf_parecer(cr['parecer_ia'])
                            st.download_button(
                                label="📥 Baixar Parecer em PDF",
                                data=pdf_data,
                                file_name=f"Parecer_{cr['candidato'].replace(' ', '_')}.pdf",
                                mime="application/pdf",
                                key=f"dl{cr['id']}"
                            )

# --- MANTENDO AS OUTRAS ABAS (DEMAIS MÓDULOS) ---
elif menu == "📊 INDICADORES":
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
                st.subheader("❌ Motivos de Perda")
                if 'motivo_perda' in df_c and df_c['motivo_perda'].notnull().any():
                    st.plotly_chart(px.pie(df_c[df_c['motivo_perda'].notnull()], names='motivo_perda', hole=0.4), use_container_width=True)

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

elif menu == "🚀 ONBOARDING":
    df_on = carregar_dados("candidatos")
    if not df_on.empty:
        df_on = df_on[df_on["status_geral"] == "Finalizada"]
        if not df_on.empty:
            sel = st.selectbox("Colaborador:", df_on["candidato"].tolist())
            c_data = df_on[df_on["candidato"] == sel].iloc[0]
            col1, col2, col3, col4 = st.columns(4)
            p = col1.checkbox("Proposta", value=bool(c_data['envio_proposta']), key="on1")
            d = col2.checkbox("Docs", value=bool(c_data['solic_documentos']), key="on2")
            c = col3.checkbox("Contrato", value=bool(c_data['solic_contrato']), key="on3")
            a = col4.checkbox("Acessos", value=bool(c_data['solic_acessos']), key="on4")
            if st.button("Salvar Onboarding"):
                executar_sql("UPDATE candidatos SET envio_proposta=:p, solic_documentos=:d, solic_contrato=:c, solic_acessos=:a WHERE id=:id", {"p":p,"d":d,"c":c,"a":a,"id":c_data['id']}); st.rerun()

elif menu == "📊 DASHBOARD DP":
    df_est = carregar_dados("contratos_estagio")
    if not df_est.empty:
        df_est['data_fim'] = pd.to_datetime(df_est['data_fim'], errors='coerce')
        df_est['data_inicio'] = pd.to_datetime(df_est['data_inicio'], errors='coerce')
        hoje = pd.Timestamp(date.today())
        df_est['doc_concluida'] = (df_est['solic_contrato_dp'] == True) & (df_est['assina_etus'] == True) & (df_est['assina_faculdade'] == True) & (df_est['envio_juridico'] == True)
        c1, c2, c3 = st.columns(3)
        c1.metric("🎓 TOTAL", len(df_est))
        alerta = len(df_est[(df_est['data_fim'] >= hoje) & ((df_est['data_fim'] - hoje).dt.days <= 30)])
        c2.metric("⚠️ VENCENDO (30 DIAS)", alerta)
        c3.metric("✅ CONCLUÍDOS", len(df_est[df_est['doc_concluida'] == True]))
        st.divider(); col_l, col_r = st.columns(2)
        with col_l:
            st.subheader("🚨 Pendências")
            for _, r in df_est[df_est['doc_concluida'] == False].iterrows():
                f = [k for k,v in {'Solic.':r['solic_contrato_dp'],'ETUS':r['assina_etus'],'Facul.':r['assina_faculdade'],'Jurid.':r['envio_juridico']}.items() if not v]
                st.warning(f"**{r['estagiario']}** | Falta: {', '.join(f)}")
        with col_r:
            st.subheader("📅 Timeline")
            for _, r in df_est[df_est['doc_concluida'] == True].iterrows():
                total = (r['data_fim'] - r['data_inicio']).days
                prog = max(0, min(100, int(((hoje - r['data_inicio']).days/total)*100))) if total > 0 else 0
                st.write(f"**{r['estagiario']}**")
                st.progress(prog/100); st.caption(f"Fim em: {r['data_fim'].strftime('%d/%m/%Y')}")

elif menu == "🎓 ESTAGIÁRIOS":
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("📝 Novo Registro")
        with st.form("f_est", clear_on_submit=True):
            n = st.text_input("Nome"); i = st.text_input("Instituição"); f = st.text_input("Função")
            t = st.selectbox("Time", ["Tecnologia", "Comercial", "Marketing", "Operações", "RH", "Financeiro", "Outros"])
            di = st.date_input("Início"); df = st.date_input("Término")
            if st.form_submit_button("CADASTRAR"):
                executar_sql("INSERT INTO contratos_estagio (estagiario, instituicao, funcao, time_equipe, data_inicio, data_fim) VALUES (:n, :i, :f, :t, :di, :df)", 
                             {"n": n, "i": i, "f": f, "t": t, "di": di, "df": df}); st.rerun()
    with col2:
        st.subheader("📋 Gestão")
        df_e = carregar_dados("contratos_estagio")
        if not df_e.empty:
            for _, r in df_e.iterrows():
                is_ok = all([r.get('solic_contrato_dp'), r.get('assina_etus'), r.get('assina_faculdade'), r.get('envio_juridico')])
                with st.expander(f"👤 {r['estagiario']} {'✅' if is_ok else '⏳'}"):
                    ca, cb, cc, cd = st.columns(4)
                    s = ca.checkbox("Solicit.", value=bool(r.get('solic_contrato_dp')), key=f"s{r['id']}")
                    ae = cb.checkbox("ETUS", value=bool(r.get('assina_etus')), key=f"ae{r['id']}")
                    af = cc.checkbox("Facul.", value=bool(r.get('assina_faculdade')), key=f"af{r['id']}")
                    ej = cd.checkbox("Jurid.", value=bool(r.get('envio_juridico')), key=f"ej{r['id']}")
                    if st.button("Salvar", key=f"sv{r['id']}"):
                        executar_sql("UPDATE contratos_estagio SET solic_contrato_dp=:s, assina_etus=:ae, assina_faculdade=:af, envio_juridico=:ej WHERE id=:id", {"s":s,"ae":ae,"af":af,"ej":ej,"id":r['id']}); st.rerun()
                    if st.button("🗑️ Excluir", key=f"dl{r['id']}"):
                        executar_sql("DELETE FROM contratos_estagio WHERE id=:id", {"id":r['id']}); st.rerun()
