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
            return genai.GenerativeModel('gemini-1.5-flash')
        except:
            return genai.GenerativeModel('gemini-pro')
    return None

model_ai = configurar_ia()

# --- 3. MOTOR DE BANCO DE DADOS ---
@st.cache_resource
def get_engine():
    try:
        DB_URL = st.secrets["postgres"]["url"]
        return create_engine(DB_URL, pool_size=10, max_overflow=20, connect_args={"sslmode": "require"})
    except Exception as e:
        st.error(f"Erro de conexão: {e}"); st.stop()

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

@st.cache_data(ttl=1)
def carregar_dados(tabela):
    try:
        with engine.connect() as conn:
            return pd.read_sql(text(f"SELECT * FROM {tabela} ORDER BY id DESC"), conn)
    except:
        return pd.DataFrame()

def extrair_texto_pdf(file):
    reader = PdfReader(file)
    texto = ""
    for page in reader.pages:
        c = page.extract_text()
        if c: texto += c
    return texto

def gerar_parecer_ia(nome_cand, nome_vaga, texto_cv, s_atual, s_pret):
    if not model_ai: return "IA não configurada."
    prompt = f"Gere um parecer técnico para {nome_cand} na vaga {nome_vaga}. Analista: Felipe Cristo. Tópicos: Formação, Experiência, Salário (Atual: {s_atual}/Pretensão: {s_pret}), Soft Skills e Adequação. CV: {texto_cv}"
    try:
        response = model_ai.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro na IA: {str(e)}"

def gerar_pdf_parecer(texto_parecer):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "RH ETUS - PARECER TECNICO", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", "", 11)
    txt = texto_parecer.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 7, txt)
    return pdf.output(dest='S').encode('latin-1')

# --- 5. BANCO DE DADOS (INIT) ---
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS vagas (id SERIAL PRIMARY KEY, nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE, data_fechamento DATE);
        CREATE TABLE IF NOT EXISTS candidatos (id SERIAL PRIMARY KEY, candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, historico TEXT, motivo_perda TEXT, envio_proposta BOOLEAN DEFAULT FALSE, solic_documentos BOOLEAN DEFAULT FALSE, solic_contrato BOOLEAN DEFAULT FALSE, solic_acessos BOOLEAN DEFAULT FALSE, parecer_ia TEXT);
        CREATE TABLE IF NOT EXISTS contratos_estagio (id SERIAL PRIMARY KEY, estagiario TEXT, instituicao TEXT, data_inicio DATE, data_fim DATE, status_contrato TEXT, time_equipe TEXT, funcao TEXT, solic_contrato_dp BOOLEAN DEFAULT FALSE, assina_etus BOOLEAN DEFAULT FALSE, assina_faculdade BOOLEAN DEFAULT FALSE, envio_juridico BOOLEAN DEFAULT FALSE);
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

# --- 7. MÓDULO CANDIDATOS (RESTAURADO E MELHORADO) ---
if menu == "⚙️ CANDIDATOS":
    df_v = carregar_dados("vagas")
    df_c = carregar_dados("candidatos")
    
    with st.expander("➕ NOVO CANDIDATO"):
        with st.form("nc"):
            nc = st.text_input("Nome do Candidato")
            opcoes_vagas = df_v['nome_vaga'].tolist() if not df_v.empty else ["Sem Vaga Definida"]
            vnc = st.selectbox("Vaga Vinculada", opcoes_vagas)
            if st.form_submit_button("ADICIONAR"):
                executar_sql("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral) VALUES (:n, :v, 'Triagem')", {"n":nc,"v":vnc})
                st.rerun()

    if df_c.empty:
        st.info("Nenhum candidato encontrado.")
    else:
        # Lógica para não deixar candidatos "sumirem": agrupa por vaga, mas mostra todos
        vagas_com_candidatos = df_c['vaga_vinculada'].unique()
        
        for v_nome in vagas_com_candidatos:
            st.markdown(f'<div class="vaga-header">🏢 VAGA: {v_nome.upper()}</div>', unsafe_allow_html=True)
            lista = df_c[df_c['vaga_vinculada'] == v_nome]
            
            for _, cr in lista.iterrows():
                with st.expander(f"👤 {cr['candidato']} — [ {cr['status_geral']} ]"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write("**📍 Gestão**")
                        etapas = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada", "Perda"]
                        idx = etapas.index(cr['status_geral']) if cr['status_geral'] in etapas else 0
                        ns = st.selectbox("Alterar Etapa", etapas, index=idx, key=f"sel{cr['id']}")
                        if st.button("Atualizar Status", key=f"btn{cr['id']}"):
                            executar_sql("UPDATE candidatos SET status_geral=:s WHERE id=:id", {"s":ns,"id":cr['id']})
                            st.rerun()
                        
                        if st.button("🗑️ Remover Candidato", key=f"delc{cr['id']}"):
                            executar_sql("DELETE FROM candidatos WHERE id=:id", {"id":cr['id']})
                            st.rerun()

                    with c2:
                        st.write("**🤖 Parecer IA**")
                        cv = st.file_uploader("Upload CV (PDF)", type="pdf", key=f"pdf{cr['id']}")
                        sa = st.text_input("Salário Atual", key=f"sa{cr['id']}", value=cr.get('historico', ''))
                        sp = st.text_input("Pretensão", key=f"sp{cr['id']}", value=cr.get('motivo_perda', ''))
                        
                        if cv and st.button("✨ Gerar Parecer", key=f"gen{cr['id']}"):
                            with st.spinner("IA analisando..."):
                                txt_cv = extrair_texto_pdf(cv)
                                parecer = gerar_parecer_ia(cr['candidato'], v_nome, txt_cv, sa, sp)
                                # Salvamos os valores de salário nos campos de histórico/motivo temporariamente se necessário
                                executar_sql("UPDATE candidatos SET parecer_ia=:p, historico=:sa, motivo_perda=:sp WHERE id=:id", 
                                             {"p":parecer, "sa":sa, "sp":sp, "id":cr['id']})
                                st.rerun()
                    
                    if cr.get('parecer_ia'):
                        st.markdown("---")
                        st.markdown(f'<div class="parecer-box">{cr["parecer_ia"]}</div>', unsafe_allow_html=True)
                        pdf_data = gerar_pdf_parecer(cr['parecer_ia'])
                        st.download_button("📥 Baixar Parecer (PDF)", pdf_data, f"Parecer_{cr['candidato']}.pdf", "application/pdf", key=f"dl{cr['id']}")

# --- 8. OUTROS MÓDULOS (RESTAURADOS COMPLETOS) ---
elif menu == "📊 INDICADORES":
    df_c = carregar_dados("candidatos")
    if not df_c.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Funil de Recrutamento")
            st.plotly_chart(px.funnel(df_c['status_geral'].value_counts().reset_index(), x='count', y='status_geral', color_discrete_sequence=['#8DF768']))
        with col2:
            st.subheader("Distribuição por Vaga")
            st.plotly_chart(px.pie(df_c, names='vaga_vinculada', hole=0.4))

elif menu == "🏢 VAGAS":
    with st.expander("➕ CADASTRAR NOVA VAGA"):
        with st.form("fv"):
            n = st.text_input("Nome da Vaga"); a = st.text_input("Área"); g = st.text_input("Gestor")
            if st.form_submit_button("CRIAR"):
                executar_sql("INSERT INTO vagas (nome_vaga, area, status_vaga, gestor, data_abertura) VALUES (:n, :a, 'Aberta', :g, :d)", 
                             {"n":n,"a":a,"g":g,"d":date.today()}); st.rerun()
    df_v = carregar_dados("vagas")
    st.dataframe(df_v, use_container_width=True)

elif menu == "🚀 ONBOARDING":
    df_c = carregar_dados("candidatos")
    aprovados = df_c[df_c['status_geral'] == 'Finalizada'] if not df_c.empty else pd.DataFrame()
    if aprovados.empty:
        st.info("Nenhum candidato em 'Finalizada'.")
    else:
        for _, r in aprovados.iterrows():
            with st.expander(f"🚀 Onboarding: {r['candidato']}"):
                c1, c2, c3, c4 = st.columns(4)
                p = c1.checkbox("Proposta", value=bool(r['envio_proposta']), key=f"p1{r['id']}")
                d = c2.checkbox("Documentos", value=bool(r['solic_documentos']), key=f"d1{r['id']}")
                c = c3.checkbox("Contrato", value=bool(r['solic_contrato']), key=f"c1{r['id']}")
                a = c4.checkbox("Acessos", value=bool(r['solic_acessos']), key=f"a1{r['id']}")
                if st.button("Salvar", key=f"svon{r['id']}"):
                    executar_sql("UPDATE candidatos SET envio_proposta=:p, solic_documentos=:d, solic_contrato=:c, solic_acessos=:a WHERE id=:id",
                                 {"p":p,"d":d,"c":c,"a":a,"id":r['id']}); st.rerun()

elif menu == "📊 DASHBOARD DP":
    df_e = carregar_dados("contratos_estagio")
    if not df_e.empty:
        st.metric("Total Estagiários", len(df_e))
        st.dataframe(df_e, use_container_width=True)

elif menu == "🎓 ESTAGIÁRIOS":
    with st.form("fe"):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nome"); i = c2.text_input("Instituição")
        if st.form_submit_button("CADASTRAR"):
            executar_sql("INSERT INTO contratos_estagio (estagiario, instituicao) VALUES (:n, :i)"); st.rerun()
    st.dataframe(carregar_dados("contratos_estagio"), use_container_width=True)
