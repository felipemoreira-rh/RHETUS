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
        conn.execute(text("CREATE TABLE IF NOT EXISTS vagas (id SERIAL PRIMARY KEY, nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS candidatos (id SERIAL PRIMARY KEY, candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, entrevista_rh DATE, entrevista_gestor DATE, entrevista_cultura DATE, historico TEXT)"))
        # Colunas extras de Onboarding
        for col in ["envio_proposta", "solic_documentos", "solic_contrato", "solic_acessos"]:
            try: conn.execute(text(f"ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS {col} BOOLEAN DEFAULT FALSE"))
            except: pass
        conn.commit()

inicializar_banco()

# --- 4. CSS CUSTOMIZADO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    html, body, [class*="css"], [data-testid="stSidebar"] { font-family: 'Space Grotesk', sans-serif !important; }
    .header-rh { font-size: 42px; font-weight: 700; color: #8DF768; margin-bottom: 20px; border-left: 10px solid #151514; padding-left: 15px; }
    .stButton button { border-radius: 8px; }
    div[data-testid="stExpander"] { border: 1px solid #333; border-radius: 10px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. FUNÇÕES DE APOIO ---
def carregar_vagas(): return pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)

# --- 6. SIDEBAR ---
with st.sidebar:
    st.title("🏈 ETUS RH")
    menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])

st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- 7. INDICADORES ---
if menu == "📊 INDICADORES":
    df_c = pd.read_sql("SELECT * FROM candidatos", engine)
    if not df_c.empty:
        st.metric("Total de Candidatos", len(df_c))
        fig = px.pie(df_c, names='status_geral', title="Candidatos por Etapa", color_discrete_sequence=px.colors.sequential.Greens_r)
        st.plotly_chart(fig)
    else: st.info("Sem dados para o Dashboard.")

# --- 8. VAGAS ---
elif menu == "🏢 VAGAS":
    st.subheader("Cadastro de Vagas")
    with st.form("nova_vaga"):
        n_v = st.text_input("Nome da Vaga")
        g_v = st.text_input("Gestor")
        if st.form_submit_button("CRIAR VAGA"):
            with engine.connect() as conn:
                conn.execute(text("INSERT INTO vagas (nome_vaga, status_vaga, gestor, data_abertura) VALUES (:n, 'Aberta', :g, :d)"), 
                             {"n": n_v, "g": g_v, "d": datetime.now().date()}); conn.commit()
            st.rerun()
    st.dataframe(carregar_vagas(), use_container_width=True)

# --- 9. CANDIDATOS ---
elif menu == "⚙️ CANDIDATOS":

    df_vagas = carregar_vagas()

    tab_add, tab_manage = st.tabs(["➕ Novo Candidato", "📋 Gestão de Candidatos"])

    # -------------------------
    # ABA 1 - CADASTRAR
    # -------------------------
    with tab_add:

        st.subheader("Adicionar Novo Candidato")

        if not df_vagas.empty:

            with st.form("novo_candidato", clear_on_submit=True):

                col1, col2 = st.columns(2)

                nome = col1.text_input("Nome do Candidato")
                vaga = col2.selectbox("Vaga", df_vagas["nome_vaga"].tolist())

                submit = st.form_submit_button("Cadastrar")

                if submit:

                    if nome:

                        with engine.connect() as conn:

                            log = f"➔ {datetime.now().strftime('%d/%m/%Y %H:%M')}: Cadastro realizado\n"

                            conn.execute(
                                text("""
                                INSERT INTO candidatos 
                                (candidato, vaga_vinculada, status_geral, historico)
                                VALUES (:n, :v, 'Triagem', :h)
                                """),
                                {"n": nome, "v": vaga, "h": log}
                            )

                            conn.commit()

                        st.success("Candidato cadastrado!")
                        st.rerun()

                    else:
                        st.error("Digite o nome do candidato")

        else:
            st.warning("Crie uma vaga primeiro.")

    # -------------------------
    # ABA 2 - GESTÃO
    # -------------------------
    with tab_manage:

        st.subheader("Gestão de Candidatos")

        df_c = pd.read_sql("SELECT * FROM candidatos ORDER BY id DESC", engine)

        if df_c.empty:
            st.info("Nenhum candidato cadastrado.")
        else:

            status_list = [
                "Triagem",
                "Entrevista RH",
                "Teste Técnico",
                "Entrevista gestor",
                "Entrevista Cultura",
                "Finalizada"
            ]

            for _, cand in df_c.iterrows():

                with st.expander(f"{cand['candidato']} | {cand['vaga_vinculada']} | {cand['status_geral']}"):

                    novo_status = st.selectbox(
                        "Status",
                        status_list,
                        index=status_list.index(cand['status_geral']) if cand['status_geral'] in status_list else 0,
                        key=f"status_{cand['id']}"
                    )

                    if st.button("Salvar", key=f"save_{cand['id']}"):

                        historico = cand["historico"] if cand["historico"] else ""

                        if novo_status != cand["status_geral"]:
                            historico = f"➔ {datetime.now().strftime('%d/%m/%Y %H:%M')}: Avançou para {novo_status}\n" + historico

                        with engine.connect() as conn:

                            conn.execute(
                                text("""
                                UPDATE candidatos
                                SET status_geral=:s, historico=:h
                                WHERE id=:id
                                """),
                                {"s": novo_status, "h": historico, "id": cand["id"]}
                            )

                            conn.commit()

                        st.success("Atualizado!")
                        st.rerun()

                    if st.button("Excluir", key=f"del_{cand['id']}"):

                        with engine.connect() as conn:

                            conn.execute(
                                text("DELETE FROM candidatos WHERE id=:id"),
                                {"id": cand["id"]}
                            )

                            conn.commit()

                        st.warning("Candidato excluído")
                        st.rerun()

                    if cand["historico"]:
                        st.text(cand["historico"])

# --- 10. ONBOARDING ---
elif menu == "🚀 ONBOARDING":
    st.subheader("Onboarding")
    st.write("Candidatos marcados como 'Finalizada' aparecerão aqui.")


