import streamlit as st
import pandas as pd
import plotly.express as px
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
    .vaga-header { background-color: rgba(141, 247, 104, 0.2); color: inherit; padding: 10px; border-radius: 5px; margin-top: 20px; margin-bottom: 10px; font-weight: bold; border-left: 5px solid #8DF768; }
    .status-vencido { color: #FF4B4B; font-weight: bold; }
    .status-alerta { color: #FFA500; font-weight: bold; }
    .status-ok { color: #28A745; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE BANCO DE DADOS ---
@st.cache_resource
def get_engine():
    try:
        DB_URL = st.secrets["postgres"]["url"]
        return create_engine(DB_URL, pool_size=5, max_overflow=10, connect_args={"sslmode": "require"})
    except:
        st.stop()

engine = get_engine()

# --- 3. FUNÇÕES DE DADOS ---
def executar_sql(query, params=None):
    try:
        with engine.begin() as conn:
            conn.execute(text(query), params or {})
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro: {e}")
        return False

@st.cache_data(ttl=60)
def carregar_dados(tabela):
    return pd.read_sql(f"SELECT * FROM {tabela}", engine)

# --- 4. INICIALIZAÇÃO DO BANCO ---
def inicializar_banco():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vagas (id SERIAL PRIMARY KEY, nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE, data_fechamento DATE);
            CREATE TABLE IF NOT EXISTS candidatos (id SERIAL PRIMARY KEY, candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, historico TEXT, motivo_perda TEXT, envio_proposta BOOLEAN DEFAULT FALSE, solic_documentos BOOLEAN DEFAULT FALSE, solic_contrato BOOLEAN DEFAULT FALSE, solic_acessos BOOLEAN DEFAULT FALSE);
            CREATE TABLE IF NOT EXISTS contratos_estagio (id SERIAL PRIMARY KEY, estagiario TEXT, instituicao TEXT, data_inicio DATE, data_fim DATE, status_contrato TEXT);
        """))
inicializar_banco()

# --- 5. SIDEBAR COM MENUS SEPARADOS (RH E DP) ---
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.markdown("## 🏢 RH ETUS")
    
    st.divider()
    area_selecionada = st.selectbox("GERENCIAMENTO", ["RH - Recrutamento", "DP - Departamento Pessoal"])
    st.divider()

    if area_selecionada == "RH - Recrutamento":
        st.subheader("MENU RH")
        menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])
    else:
        st.subheader("MENU DP")
        menu = st.radio("NAVEGAÇÃO", ["🎓 ESTAGIÁRIOS", "📄 DOCUMENTOS"])

st.markdown(f'<div class="header-rh">{menu}</div>', unsafe_allow_html=True)

# --- 6. LÓGICA DAS ABAS ---

# --- MÓDULO RH: INDICADORES (RESTAURADO) ---
if menu == "📊 INDICADORES":
    df_v = carregar_dados("vagas")
    df_c = carregar_dados("candidatos")
    
    if not df_v.empty:
        df_v['data_abertura'] = pd.to_datetime(df_v['data_abertura'], errors='coerce')
        df_v['data_fechamento'] = pd.to_datetime(df_v['data_fechamento'], errors='coerce')
        
        # Cálculo Time-To-Hire
        df_fechadas = df_v[df_v['status_vaga'] == 'Finalizada'].copy().dropna(subset=['data_abertura', 'data_fechamento'])
        avg_tth = int((df_fechadas['data_fechamento'] - df_fechadas['data_abertura']).dt.days.mean()) if not df_fechadas.empty else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 VAGAS ATIVAS", len(df_v[df_v['status_vaga'] == 'Aberta']))
        c2.metric("⏱️ TIME-TO-HIRE MÉDIO", f"{avg_tth} dias")
        c3.metric("👥 CANDIDATOS ATIVOS", len(df_c[~df_c['status_geral'].isin(['Finalizada', 'Perda'])]) if not df_c.empty else 0)

        st.divider()
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("📊 Conversão por Etapa")
            if not df_c.empty:
                ordem_etapas = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada"]
                contagem_etapas = df_c['status_geral'].value_counts().reindex(ordem_etapas).fillna(0).reset_index()
                contagem_etapas.columns = ['Etapa', 'Candidatos']
                fig_funil = px.funnel(contagem_etapas, x='Candidatos', y='Etapa', color_discrete_sequence=['#8DF768'])
                fig_funil.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_funil, use_container_width=True)

        with col_right:
            st.subheader("❌ Motivos de Perda")
            if not df_c.empty and df_c['motivo_perda'].notnull().any():
                df_perda = df_c[df_c['motivo_perda'].notnull()]
                fig_perda = px.pie(df_perda, names='motivo_perda', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_perda.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_perda, use_container_width=True)
            else:
                st.info("Sem dados de perda registrados.")

# --- MÓDULO DP: ESTAGIÁRIOS ---
# --- MÓDULO DP: ESTAGIÁRIOS (COM EDIÇÃO E BARRA DE PROGRESSO) ---
if menu == "🎓 ESTAGIÁRIOS":
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📝 Novo Contrato")
        with st.form("form_estagio", clear_on_submit=True):
            nome = st.text_input("Nome do Estagiário")
            inst = st.text_input("Instituição de Ensino")
            d_ini = st.date_input("Início do Contrato", value=date.today())
            d_fim = st.date_input("Término do Contrato")
            if st.form_submit_button("CADASTRAR"):
                executar_sql("INSERT INTO contratos_estagio (estagiario, instituicao, data_inicio, data_fim, status_contrato) VALUES (:n, :i, :di, :df, 'Ativo')",
                             {"n": nome, "i": inst, "di": d_ini, "df": d_fim})
                st.rerun()

    with col2:
        st.subheader("📅 Gestão de Vencimentos")
        df_est = carregar_dados("contratos_estagio")
        
        if not df_est.empty:
            hoje = date.today()
            
            for _, row in df_est.iterrows():
                d_ini_val = pd.to_datetime(row['data_inicio']).date()
                d_fim_val = pd.to_datetime(row['data_fim']).date()
                
                # Cálculo de Tempo e Progresso
                total_dias = (d_fim_val - d_ini_val).days
                dias_decorridos = (hoje - d_ini_val).days
                dias_restantes = (d_fim_val - hoje).days
                
                # Evitar divisão por zero e limitar entre 0 e 100%
                percentual = max(0, min(100, int((dias_decorridos / total_dias) * 100))) if total_dias > 0 else 0
                
                # Definição de Alerta Visual
                if dias_restantes < 0:
                    status_txt, css, cor_barra = "🔴 VENCIDO", "status-vencido", "red"
                elif dias_restantes <= 30:
                    status_txt, css, cor_barra = f"🟡 VENCE EM {dias_restantes} DIAS", "status-alerta", "orange"
                else:
                    status_txt, css, cor_barra = "🟢 EM DIA", "status-ok", "green"
                
                with st.expander(f"👤 {row['estagiario']} ({status_txt})"):
                    # --- VISUALIZAÇÃO DO TEMPO ---
                    st.write(f"**Instituição:** {row['instituicao']}")
                    st.caption(f"Período: {d_ini_val.strftime('%d/%m/%Y')} até {d_fim_val.strftime('%d/%m/%Y')}")
                    st.progress(percentual / 100)
                    st.info(f"O contrato está {percentual}% concluído. Restam {max(0, dias_restantes)} dias.")
                    
                    st.divider()
                    
                    # --- EDIÇÃO E EXCLUSÃO ---
                    c_edit, c_del = st.columns(2)
                    
                    with c_edit:
                        if st.button("📝 Editar Dados", key=f"btn_ed_{row['id']}"):
                            st.session_state[f"editando_{row['id']}"] = True
                    
                    with c_del:
                        if st.button("🗑️ Excluir", key=f"btn_del_{row['id']}", use_container_width=True):
                            executar_sql("DELETE FROM contratos_estagio WHERE id=:id", {"id": row['id']})
                            st.rerun()

                    # Formulário de Edição (aparece apenas se clicado)
                    if st.session_state.get(f"editando_{row['id']}", False):
                        with st.form(f"form_ed_{row['id']}"):
                            en = st.text_input("Nome", value=row['estagiario'])
                            ei = st.text_input("Instituição", value=row['instituicao'])
                            edf = st.date_input("Nova Data Término", value=d_fim_val)
                            
                            c_salvar, c_cancelar = st.columns(2)
                            if c_salvar.form_submit_button("SALVAR ALTERAÇÕES"):
                                executar_sql("UPDATE contratos_estagio SET estagiario=:n, instituicao=:i, data_fim=:df WHERE id=:id",
                                             {"n": en, "i": ei, "df": edf, "id": row['id']})
                                st.session_state[f"editando_{row['id']}"] = False
                                st.rerun()
                            if c_cancelar.form_submit_button("CANCELAR"):
                                st.session_state[f"editando_{row['id']}"] = False
                                st.rerun()
        else:
            st.info("Nenhum contrato de estágio registrado.")

# --- MÓDULO RH: OUTRAS ABAS ---
elif menu == "🏢 VAGAS":
    with st.expander("➕ NOVA VAGA"):
        with st.form("n_vaga"):
            nv = st.text_input("Nome da Vaga"); gv = st.text_input("Gestor")
            if st.form_submit_button("CRIAR"):
                executar_sql("INSERT INTO vagas (nome_vaga, status_vaga, gestor, data_abertura) VALUES (:n, 'Aberta', :g, :d)", {"n": nv, "g": gv, "d": date.today()}); st.rerun()
    df_v = carregar_dados("vagas")
    for _, row in df_v.iterrows():
        with st.expander(f"🏢 {row['nome_vaga'].upper()}"):
            st.write(f"Gestor: {row['gestor']}")

elif menu == "⚙️ CANDIDATOS":
    df_vagas = carregar_dados("vagas")
    df_c = carregar_dados("candidatos")
    if not df_vagas.empty:
        for _, v_row in df_vagas.iterrows():
            cands = df_c[df_c['vaga_vinculada'] == v_row['nome_vaga']]
            if not cands.empty:
                st.markdown(f'<div class="vaga-header">🏢 VAGA: {v_row["nome_vaga"].upper()}</div>', unsafe_allow_html=True)
                for _, cand in cands.iterrows():
                    st.write(f"👤 {cand['candidato']} - {cand['status_geral']}")

elif menu == "🚀 ONBOARDING":
    st.info("Módulo de Onboarding ativo.")

