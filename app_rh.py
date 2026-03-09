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
    .vaga-header { background-color: rgba(141, 247, 104, 0.2); color: inherit; padding: 10px; border-radius: 5px; margin-top: 20px; margin-bottom: 10px; font-weight: bold; border-left: 5px solid #8DF768; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONFIGURAÇÃO IA ---
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model_ai = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Erro IA: {e}")

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

@st.cache_data(ttl=60)
def carregar_dados(tabela):
    try: return pd.read_sql(f"SELECT * FROM {tabela}", engine)
    except: return pd.DataFrame()

def extrair_texto_pdf(file):
    reader = PdfReader(file)
    texto = ""
    for page in reader.pages: texto += page.extract_text()
    return texto

def gerar_parecer_ia(nome_cand, nome_vaga, texto_cv, s_atual, s_pret):
    prompt = f"""
    PARECER RH — {nome_cand} — {nome_vaga} — Analista Responsável: Felipe da Silva Moreira Cristo
    Linguagem formal, objetiva, profissional, sem emojis.
    Estrutura obrigatória (6 tópicos):
    1. Perfil Acadêmico e Formação
    2. Experiência e Histórico Profissional
    3. Salário Atual
    4. Pretensão Salarial
    5. Soft Skills e Interesses Pessoais
    6. Adequação à Vaga e Potencial de Desenvolvimento
    Dados: Salário Atual: {s_atual}, Pretensão: {s_pret}, CV: {texto_cv}
    """
    response = model_ai.generate_content(prompt)
    return response.text

# --- NOVA FUNÇÃO: GERADOR DE PDF ---
def gerar_pdf_parecer(texto_parecer, nome_candidato):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "RH ETUS - PARECER TÉCNICO", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", "", 11)
    # Limpeza de caracteres que podem quebrar o PDF
    texto_limpo = texto_parecer.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 7, texto_limpo)
    return pdf.output()

# --- 5. INICIALIZAÇÃO DO BANCO ---
def inicializar_banco():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vagas (id SERIAL PRIMARY KEY, nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE, data_fechamento DATE);
            CREATE TABLE IF NOT EXISTS candidatos (id SERIAL PRIMARY KEY, candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, historico TEXT, motivo_perda TEXT, envio_proposta BOOLEAN DEFAULT FALSE, solic_documentos BOOLEAN DEFAULT FALSE, solic_contrato BOOLEAN DEFAULT FALSE, solic_acessos BOOLEAN DEFAULT FALSE, parecer_ia TEXT);
            CREATE TABLE IF NOT EXISTS contratos_estagio (id SERIAL PRIMARY KEY, estagiario TEXT, instituicao TEXT, data_inicio DATE, data_fim DATE, status_contrato TEXT, time_equipe TEXT, funcao TEXT, solic_contrato_dp BOOLEAN DEFAULT FALSE, assina_etus BOOLEAN DEFAULT FALSE, assina_faculdade BOOLEAN DEFAULT FALSE, envio_juridico BOOLEAN DEFAULT FALSE);
        """))
inicializar_banco()

# --- 6. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    area = st.selectbox("GERENCIAMENTO", ["RH - Recrutamento", "DP - Departamento Pessoal"])
    if area == "RH - Recrutamento":
        menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])
    else:
        menu = st.radio("NAVEGAÇÃO", ["📊 DASHBOARD DP", "🎓 ESTAGIÁRIOS"])

st.markdown(f'<div class="header-rh">{menu}</div>', unsafe_allow_html=True)

# --- 7. LÓGICA DE CANDIDATOS (COM DOWNLOAD PDF) ---
if menu == "⚙️ CANDIDATOS":
    df_v = carregar_dados("vagas"); df_c = carregar_dados("candidatos")
    if not df_v.empty:
        for _, vr in df_v.iterrows():
            cands = df_c[df_c['vaga_vinculada'] == vr['nome_vaga']]
            if not cands.empty:
                st.markdown(f'<div class="vaga-header">🏢 {vr["nome_vaga"].upper()}</div>', unsafe_allow_html=True)
                for _, cr in cands.iterrows():
                    with st.expander(f"👤 {cr['candidato']} - {cr['status_geral']}"):
                        col_etapa, col_ia_form = st.columns([1, 1])
                        with col_etapa:
                            ns = st.selectbox("Mover Etapa", ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada", "Perda"], key=f"st{cr['id']}")
                            if st.button("Salvar Etapa", key=f"upc{cr['id']}"):
                                executar_sql("UPDATE candidatos SET status_geral=:s WHERE id=:id", {"s":ns,"id":cr['id']}); st.rerun()
                        
                        with col_ia_form:
                            st.write("**🤖 Gerar Parecer com IA**")
                            cv_upload = st.file_uploader("Upload Currículo (PDF)", type="pdf", key=f"pdf_{cr['id']}")
                            s_at = st.text_input("Salário Atual", key=f"sat_{cr['id']}")
                            s_pr = st.text_input("Pretensão Salarial", key=f"spr_{cr['id']}")
                            if cv_upload and st.button("Analisar e Gerar Parecer", key=f"ai_{cr['id']}"):
                                with st.spinner("Processando..."):
                                    texto_extraido = extrair_texto_pdf(cv_upload)
                                    parecer_texto = gerar_parecer_ia(cr['candidato'], vr['nome_vaga'], texto_extraido, s_at, s_pr)
                                    executar_sql("UPDATE candidatos SET parecer_ia=:p WHERE id=:id", {"p": parecer_texto, "id": cr['id']})
                                    st.rerun()
                        
                        if cr.get('parecer_ia'):
                            st.divider()
                            st.markdown("#### 📄 Parecer Técnico")
                            st.info(cr['parecer_ia'])
                            
                            # BOTÃO DE DOWNLOAD PDF
                            pdf_bytes = gerar_pdf_parecer(cr['parecer_ia'], cr['candidato'])
                            st.download_button(
                                label="📥 Baixar Parecer em PDF",
                                data=pdf_bytes,
                                file_name=f"Parecer_RH_{cr['candidato'].replace(' ', '_')}.pdf",
                                mime="application/pdf",
                                key=f"dl_{cr['id']}"
                            )

# --- MANTENDO AS OUTRAS ABAS (DP, DASHBOARD, ETC) ---
elif menu == "📊 DASHBOARD DP":
    # (Inserir código anterior do Dashboard DP aqui - mantido conforme combinado)
    df_est = carregar_dados("contratos_estagio")
    if not df_est.empty:
        df_est['data_fim'] = pd.to_datetime(df_est['data_fim'], errors='coerce')
        df_est['data_inicio'] = pd.to_datetime(df_est['data_inicio'], errors='coerce')
        hoje = pd.Timestamp(date.today())
        df_est['doc_concluida'] = (df_est['solic_contrato_dp'] == True) & (df_est['assina_etus'] == True) & (df_est['assina_faculdade'] == True) & (df_est['envio_juridico'] == True)
        c1, c2, c3 = st.columns(3)
        c1.metric("🎓 TOTAL", len(df_est))
        c2.metric("⏳ PENDENTES", len(df_est[df_est['doc_concluida'] == False]))
        c3.metric("✅ CONCLUÍDOS", len(df_est[df_est['doc_concluida'] == True]))
        st.divider()
        cl, cr = st.columns(2)
        with cl:
            st.subheader("🚨 Pendências")
            for _, r in df_est[df_est['doc_concluida'] == False].iterrows():
                st.warning(f"**{r['estagiario']}**")
        with cr:
            st.subheader("📅 Vencimentos")
            for _, r in df_est[df_est['doc_concluida'] == True].iterrows():
                st.write(f"**{r['estagiario']}** | Vence em: {r['data_fim'].strftime('%d/%m/%Y')}")

elif menu == "🎓 ESTAGIÁRIOS":
    # (Inserir código anterior de Gestão de Estagiários aqui)
    st.write("Módulo de Estagiários Ativo")
    # ... (restante do código já validado anteriormente)
