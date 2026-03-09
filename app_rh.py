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
    .parecer-box { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #8DF768; color: #f0f0f0; margin-top: 15px; white-space: pre-wrap; line-height: 1.6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONFIGURAÇÃO IA ---
def configurar_ia():
    if "GEMINI_API_KEY" in st.secrets:
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            # Tentamos o Flash primeiro sem o prefixo 'models/'
            return genai.GenerativeModel('gemini-1.5-flash')
        except Exception:
            # Fallback para o Pro caso o Flash dê erro de versão
            return genai.GenerativeModel('gemini-pro')
    return None

model_ai = configurar_ia()

# --- 3. MOTOR DE BANCO DE DADOS ---
@st.cache_resource
def get_engine():
    try:
        DB_URL = st.secrets["postgres"]["url"]
        return create_engine(DB_URL, pool_size=5, max_overflow=10, connect_args={"sslmode": "require"})
    except:
        st.error("Erro na conexão com o banco de dados."); st.stop()

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
    try: return pd.read_sql(f"SELECT * FROM {tabela} ORDER BY id DESC", engine)
    except: return pd.DataFrame()

def extrair_texto_pdf(file):
    reader = PdfReader(file)
    texto = ""
    for page in reader.pages:
        c = page.extract_text()
        if c: texto += c
    return texto

def gerar_parecer_ia(nome_cand, nome_vaga, texto_cv, s_atual, s_pret):
    if not model_ai: return "IA não configurada nos Secrets."
    
    prompt = f"""
    Como Especialista em Recrutamento, gere um parecer técnico para o candidato {nome_cand} (Vaga: {nome_vaga}).
    Analista Responsável: Felipe da Silva Moreira Cristo.
    Estrutura obrigatória: 
    1. Formação e Acadêmico. 
    2. Resumo da Experiência. 
    3. Análise Salarial (Atual: {s_atual} / Pretensão: {s_pret}). 
    4. Soft Skills. 
    5. Adequação à Vaga. 
    6. Veredito Final.
    Currículo: {texto_cv}
    """
    try:
        response = model_ai.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro na geração: {str(e)}"

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

# --- 5. INICIALIZAÇÃO DO BANCO ---
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS vagas (id SERIAL PRIMARY KEY, nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE, data_fechamento DATE);
        CREATE TABLE IF NOT EXISTS candidatos (id SERIAL PRIMARY KEY, candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, historico TEXT, motivo_perda TEXT, envio_proposta BOOLEAN DEFAULT FALSE, solic_documentos BOOLEAN DEFAULT FALSE, solic_contrato BOOLEAN DEFAULT FALSE, solic_acessos BOOLEAN DEFAULT FALSE, parecer_ia TEXT);
        CREATE TABLE IF NOT EXISTS contratos_estagio (id SERIAL PRIMARY KEY, estagiario TEXT, instituicao TEXT, data_inicio DATE, data_fim DATE, status_contrato TEXT, time_equipe TEXT, funcao TEXT, solic_contrato_dp BOOLEAN DEFAULT FALSE, assina_etus BOOLEAN DEFAULT FALSE, assina_faculdade BOOLEAN DEFAULT FALSE, envio_juridico BOOLEAN DEFAULT FALSE);
        DO $$ BEGIN 
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
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write("**📍 Gestão**")
                            ns = st.selectbox("Status", ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada", "Perda"], key=f"s{cr['id']}", index=0)
                            if st.button("Salvar Status", key=f"b{cr['id']}"):
                                executar_sql("UPDATE candidatos SET status_geral=:s WHERE id=:id", {"s":ns,"id":cr['id']}); st.rerun()
                        
                        with c2:
                            st.write("**🤖 IA**")
                            cv = st.file_uploader("Upload CV (PDF)", type="pdf", key=f"p{cr['id']}")
                            sa = st.text_input("Salário Atual", key=f"sa{cr['id']}")
                            sp = st.text_input("Pretensão", key=f"sp{cr['id']}")
                            if cv and st.button("✨ Gerar Parecer", key=f"gi{cr['id']}"):
                                with st.spinner("Analisando..."):
                                    txt = extrair_texto_pdf(cv)
                                    resultado = gerar_parecer_ia(cr['candidato'], vr['nome_vaga'], txt, sa, sp)
                                    executar_sql("UPDATE candidatos SET parecer_ia=:p WHERE id=:id", {"p":resultado,"id":cr['id']})
                                    st.rerun()
                        
                        if 'parecer_ia' in cr and pd.notnull(cr['parecer_ia']) and str(cr['parecer_ia']).strip() != "":
                            st.markdown(f'<div class="parecer-box">{cr["parecer_ia"]}</div>', unsafe_allow_html=True)
                            pdf = gerar_pdf_parecer(cr['parecer_ia'])
                            st.download_button("📥 Baixar PDF", pdf, f"Parecer_{cr['candidato']}.pdf", "application/pdf", key=f"dl{cr['id']}")

# --- ABAS DE APOIO ---
elif menu == "📊 INDICADORES":
    df_c = carregar_dados("candidatos")
    if not df_c.empty:
        cnt = df_c['status_geral'].value_counts().reset_index()
        st.plotly_chart(px.funnel(cnt, x='count', y='status_geral', color_discrete_sequence=['#8DF768']))

elif menu == "🏢 VAGAS":
    with st.form("v"):
        n = st.text_input("Vaga"); g = st.text_input("Gestor")
        if st.form_submit_button("Criar"):
            executar_sql("INSERT INTO vagas (nome_vaga, status_vaga, gestor, data_abertura) VALUES (:n, 'Aberta', :g, :d)", {"n":n,"g":g,"d":date.today()}); st.rerun()
    st.dataframe(carregar_dados("vagas"))

elif menu == "🚀 ONBOARDING":
    df = carregar_dados("candidatos")
    st.write("Candidatos aprovados aguardando onboarding.")
    st.dataframe(df[df['status_geral'] == 'Finalizada'] if not df.empty else df)

elif menu == "📊 DASHBOARD DP":
    st.write("Controle de contratos e prazos.")
    st.dataframe(carregar_dados("contratos_estagio"))

elif menu == "🎓 ESTAGIÁRIOS":
    with st.form("e"):
        n = st.text_input("Nome"); f = st.date_input("Fim Contrato")
        if st.form_submit_button("Cadastrar"):
            executar_sql("INSERT INTO contratos_estagio (estagiario, data_fim) VALUES (:n, :f)", {"n":n,"f":f}); st.rerun()
    st.dataframe(carregar_dados("contratos_estagio"))
