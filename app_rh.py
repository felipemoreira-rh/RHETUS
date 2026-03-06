import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
import os
from datetime import datetime

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="RH ETUS - Gestão Pro", layout="wide", page_icon="🏈")

# --- 2. CONEXÃO ---
try:
    DB_URL = st.secrets["postgres"]["url"]
    engine = create_engine(DB_URL, connect_args={"sslmode": "require"})
except KeyError:
    st.error("Erro nos Secrets do banco de dados.")
    st.stop()

# --- 3. INICIALIZAÇÃO DE BANCO ---
def inicializar_banco():
    with engine.connect() as conn:
        # Tabelas básicas se não existirem
        conn.execute(text("CREATE TABLE IF NOT EXISTS vagas (id SERIAL PRIMARY KEY, nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS candidatos (id SERIAL PRIMARY KEY, candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, entrevista_rh DATE, entrevista_gestor DATE, entrevista_cultura DATE, historico TEXT)"))
        
        # Colunas de Onboarding (Caso não existam)
        c_cols = ["envio_proposta", "solic_documentos", "solic_contrato", "solic_acessos"]
        for col in c_cols:
            try: conn.execute(text(f"ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS {col} BOOLEAN DEFAULT FALSE")); conn.commit()
            except: pass
        conn.commit()

inicializar_banco()

# --- 4. CSS CUSTOMIZADO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    html, body, [class*="css"], [data-testid="stSidebar"] { font-family: 'Space Grotesk', sans-serif !important; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] p { color: #777777 !important; font-size: 18px !important; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] input:checked + div p { color: #8DF768 !important; font-weight: 700 !important; }
    .header-rh { font-size: 42px; font-weight: 700; color: #8DF768; margin-bottom: 30px; border-left: 10px solid #151514; padding-left: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. FUNÇÕES DE DADOS ---
def carregar_vagas(): return pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)
def carregar_candidatos_vaga(v_nome):
    query = text("SELECT * FROM candidatos WHERE vaga_vinculada = :v ORDER BY candidato ASC")
    return pd.read_sql(query, engine, params={"v": v_nome})

# --- 6. SIDEBAR ---
with st.sidebar:
    st.title("🏈 ETUS RH")
    menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])

st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- 7. INDICADORES (RESUMIDO) ---
if menu == "📊 INDICADORES":
    st.subheader("Painel de Controle")
    df_c = pd.read_sql("SELECT * FROM candidatos", engine)
    if not df_c.empty:
        st.metric("Total de Candidatos", len(df_c))
        fig = px.pie(df_c, names='status_geral', title="Distribuição por Etapa", color_discrete_sequence=px.colors.sequential.Greens_r)
        st.plotly_chart(fig)
    else:
        st.info("Sem dados para exibir.")

# --- 8. VAGAS ---
elif menu == "🏢 VAGAS":
    st.subheader("Gestão de Vagas")
    with st.expander("➕ CADASTRAR NOVA VAGA"):
        with st.form("n_vaga"):
            n_v = st.text_input("Nome da Vaga")
            a_v = st.selectbox("Departamento", ["Comercial", "Operações", "Tecnologia", "RH", "Marketing"])
            g_v = st.text_input("Gestor")
            if st.form_submit_button("CRIAR VAGA"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO vagas (nome_vaga, area, status_vaga, gestor, data_abertura) VALUES (:n, :a, 'Aberta', :g, :d)"), 
                                 {"n": n_v, "a": a_v, "g": g_v, "d": datetime.now().date()})
                    conn.commit()
                st.rerun()
    
    df_v = carregar_vagas()
    st.dataframe(df_v, use_container_width=True)

# --- 9. CANDIDATOS (INCLUSÃO E EXCLUSÃO) ---
elif menu == "⚙️ CANDIDATOS":
    df_vagas = carregar_vagas()
    
    if df_vagas.empty:
        st.warning("⚠️ Você precisa cadastrar uma VAGA antes de adicionar candidatos.")
    else:
        # --- BLOCO DE INCLUSÃO (SEMPRE VISÍVEL) ---
        st.subheader("➕ Novo Candidato")
        with st.expander("Clique aqui para cadastrar um novo candidato", expanded=False):
            with st.form("form_add_cand", clear_on_submit=True):
                c_nome = st.text_input("Nome do Candidato")
                c_vaga = st.selectbox("Vincular à Vaga", df_vagas["nome_vaga"].tolist())
                if st.form_submit_button("SALVAR NOVO CANDIDATO"):
                    if c_nome:
                        with engine.connect() as conn:
                            log_init = f"➔ {datetime.now().strftime('%d/%m/%Y %H:%M')}: Iniciou em 'Triagem'\n"
                            conn.execute(text("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral, historico) VALUES (:n, :v, 'Triagem', :h)"),
                                         {"n": c_nome, "v": c_vaga, "h": log_init})
                            conn.commit()
                        st.success(f"Candidato {c_nome} cadastrado com sucesso!")
                        st.rerun()
                    else:
                        st.error("O nome é obrigatório.")

        st.divider()

        # --- LISTAGEM E EDIÇÃO ---
        st.subheader("🔍 Gestão de Inscritos")
        v_sel = st.selectbox("Selecione a Vaga para ver os candidatos:", ["Todos"] + df_vagas["nome_vaga"].tolist())
        
        if v_sel == "Todos":
            df_c = pd.read_sql("SELECT * FROM candidatos ORDER BY candidato ASC", engine)
        else:
            df_c = carregar_candidatos_vaga(v_sel)

        if df_c.empty:
            st.info("Nenhum candidato encontrado.")
        else:
            opcoes_status = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista gestor", "Entrevista Cultura", "Finalizada"]
            
            for _, cand in df_c.iterrows():
                with st.expander(f"👤 {cand['candidato'].upper()} ({cand['status_geral']})"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        novo_st = st.selectbox("Alterar Status", opcoes_status, index=opcoes_status.index(cand['status_geral']) if cand['status_geral'] in opcoes_status else 0, key=f"st_{cand['id']}")
                        
                        # Datas das Etapas
                        d_rh = st.date_input("Data RH", value=cand['entrevista_rh'] if pd.notnull(cand['entrevista_rh']) else None, key=f"drh_{cand['id']}")
                        d_gs = st.date_input("Data Gestor", value=cand['entrevista_gestor'] if pd.notnull(cand['entrevista_gestor']) else None, key=f"dgs_{cand['id']}")

                    with col2:
                        st.write("**Ações**")
                        # Botão Salvar
                        if st.button("💾 Salvar", key=f"sv_{cand['id']}", use_container_width=True):
                            h_atual = cand['historico'] if cand['historico'] else ""
                            if novo_st != cand['status_geral']:
                                h_atual = f"➔ {datetime.now().strftime('%d/%m/%Y %H:%M')}: Mudou para {novo_st}\n" + h_atual
                            
                            with engine.connect() as conn:
                                conn.execute(text("UPDATE candidatos SET status_geral=:s, entrevista_rh=:rh, entrevista_gestor=:gs, historico=:h WHERE id=:id"),
                                             {"s": novo_st, "rh": d_rh, "gs": d_gs, "h": h_atual, "id": cand['id']})
                                conn.commit()
                            st.rerun()
                        
                        # Botão Excluir
                        if st.button("🗑️ Excluir", key=f"del_{cand['id']}", use_container_width=True):
                            with engine.connect() as conn:
                                conn.execute(text("DELETE FROM candidatos WHERE id = :id"), {"id": cand['id']})
                                conn.commit()
                            st.rerun()

                    if cand['historico']:
                        st.caption("Histórico:")
                        st.text(cand['historico'])

# --- 10. ONBOARDING (SIMPLIFICADO) ---
elif menu == "🚀 ONBOARDING":
    st.subheader("Processo de Admissão")
    df_c = pd.read_sql("SELECT * FROM candidatos WHERE status_geral = 'Finalizada'", engine)
    if df_c.empty:
        st.info("Nenhum candidato finalizado para onboarding.")
    else:
        st.dataframe(df_c[["candidato", "vaga_vinculada"]])
