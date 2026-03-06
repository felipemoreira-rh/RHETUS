import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
import os
from datetime import datetime

# -----------------------------------
# CONFIGURAÇÃO
# -----------------------------------
st.set_page_config(
    page_title="RH ETUS - Gestão",
    layout="wide",
    page_icon="🏈"
)

# -----------------------------------
# PASTA PARA CURRÍCULOS
# -----------------------------------
UPLOAD_DIR = "curriculos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -----------------------------------
# CONEXÃO BANCO
# -----------------------------------
try:
    DB_URL = st.secrets["postgres"]["url"]
    engine = create_engine(DB_URL, connect_args={"sslmode": "require"})
except KeyError:
    st.error("Erro ao conectar no banco.")
    st.stop()

# -----------------------------------
# INICIALIZAÇÃO BANCO
# -----------------------------------
def inicializar_banco():

    with engine.connect() as conn:

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS vagas (
            id SERIAL PRIMARY KEY,
            nome_vaga TEXT,
            gestor TEXT,
            status_vaga TEXT,
            data_abertura DATE
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS candidatos (
            id SERIAL PRIMARY KEY,
            candidato TEXT,
            vaga_vinculada TEXT,
            status_geral TEXT,
            historico TEXT,
            curriculo TEXT
        )
        """))

        conn.commit()

inicializar_banco()

# -----------------------------------
# FUNÇÕES
# -----------------------------------
def carregar_vagas():
    return pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)

def carregar_candidatos():
    return pd.read_sql("SELECT * FROM candidatos ORDER BY id DESC", engine)

# -----------------------------------
# SIDEBAR
# -----------------------------------
with st.sidebar:

    st.title("🏈 ETUS RH")

    menu = st.radio(
        "Menu",
        [
            "📊 Dashboard",
            "🏢 Vagas",
            "👥 Candidatos"
        ]
    )

st.title("Sistema de Gestão de Recrutamento")

# -----------------------------------
# DASHBOARD
# -----------------------------------
if menu == "📊 Dashboard":

    df_c = carregar_candidatos()
    df_v = carregar_vagas()

    col1, col2, col3 = st.columns(3)

    col1.metric("Vagas abertas", len(df_v))
    col2.metric("Total candidatos", len(df_c))

    if not df_c.empty:

        finalizados = len(df_c[df_c["status_geral"]=="Finalizada"])
        col3.metric("Contratados", finalizados)

        st.subheader("Funil de recrutamento")

        funil = df_c["status_geral"].value_counts().reset_index()
        funil.columns = ["Etapa","Quantidade"]

        fig = px.funnel(funil,x="Quantidade",y="Etapa")
        st.plotly_chart(fig,use_container_width=True)

# -----------------------------------
# VAGAS
# -----------------------------------
elif menu == "🏢 Vagas":

    st.subheader("Cadastro de vagas")

    with st.form("form_vaga"):

        nome = st.text_input("Nome da vaga")
        gestor = st.text_input("Gestor responsável")

        submit = st.form_submit_button("Cadastrar vaga")

        if submit:

            if nome:

                with engine.connect() as conn:

                    conn.execute(text("""
                    INSERT INTO vagas
                    (nome_vaga, gestor, status_vaga, data_abertura)
                    VALUES (:n,:g,'Aberta',:d)
                    """),
                    {
                        "n":nome,
                        "g":gestor,
                        "d":datetime.now().date()
                    })

                    conn.commit()

                st.success("Vaga criada")

            else:
                st.error("Digite o nome da vaga")

    st.divider()

    st.subheader("Vagas cadastradas")

    st.dataframe(carregar_vagas(),use_container_width=True)

# -----------------------------------
# CANDIDATOS
# -----------------------------------
elif menu == "👥 Candidatos":

    df_vagas = carregar_vagas()

    tab1,tab2,tab3 = st.tabs(
        ["➕ Novo candidato","📋 Gestão","📊 Pipeline"]
    )

# -----------------------------------
# NOVO CANDIDATO
# -----------------------------------
    with tab1:

        st.subheader("Cadastrar candidato")

        if df_vagas.empty:
            st.warning("Crie uma vaga primeiro")
        else:

            with st.form("form_candidato",clear_on_submit=True):

                col1,col2 = st.columns(2)

                nome = col1.text_input("Nome")
                vaga = col2.selectbox(
                    "Vaga",
                    df_vagas["nome_vaga"].tolist()
                )

                curriculo = st.file_uploader(
                    "Upload do currículo",
                    type=["pdf","doc","docx"]
                )

                submit = st.form_submit_button("Cadastrar")

                if submit:

                    if not nome:
                        st.error("Digite o nome")
                    else:

                        caminho = None

                        if curriculo:

                            caminho = os.path.join(
                                UPLOAD_DIR,
                                curriculo.name
                            )

                            with open(caminho,"wb") as f:
                                f.write(curriculo.getbuffer())

                        log = f"{datetime.now().strftime('%d/%m/%Y %H:%M')} Cadastro"

                        with engine.connect() as conn:

                            conn.execute(text("""
                            INSERT INTO candidatos
                            (candidato,vaga_vinculada,status_geral,historico,curriculo)
                            VALUES (:n,:v,'Triagem',:h,:c)
                            """),
                            {
                                "n":nome,
                                "v":vaga,
                                "h":log,
                                "c":caminho
                            })

                            conn.commit()

                        st.success("Candidato cadastrado")
                        st.rerun()

# -----------------------------------
# GESTÃO
# -----------------------------------
    with tab2:

        df_c = carregar_candidatos()

        if df_c.empty:
            st.info("Nenhum candidato")
        else:

            etapas = [
                "Triagem",
                "Entrevista RH",
                "Teste Técnico",
                "Entrevista gestor",
                "Entrevista Cultura",
                "Finalizada"
            ]

            for _,cand in df_c.iterrows():

                with st.expander(
                    f"{cand['candidato']} | {cand['vaga_vinculada']} | {cand['status_geral']}"
                ):

                    status = st.selectbox(
                        "Status",
                        etapas,
                        index=etapas.index(cand["status_geral"])
                        if cand["status_geral"] in etapas else 0,
                        key=f"status{cand['id']}"
                    )

                    if st.button(
                        "Salvar",
                        key=f"save{cand['id']}"
                    ):

                        hist = cand["historico"] or ""

                        if status != cand["status_geral"]:
                            hist = f"{datetime.now().strftime('%d/%m/%Y %H:%M')} mudou para {status}\n"+hist

                        with engine.connect() as conn:

                            conn.execute(text("""
                            UPDATE candidatos
                            SET status_geral=:s,
                            historico=:h
                            WHERE id=:id
                            """),
                            {
                                "s":status,
                                "h":hist,
                                "id":cand["id"]
                            })

                            conn.commit()

                        st.success("Atualizado")
                        st.rerun()

                    if cand["curriculo"]:

                        st.download_button(
                            "Baixar currículo",
                            open(cand["curriculo"],"rb"),
                            file_name=os.path.basename(cand["curriculo"])
                        )

                    if st.button(
                        "Excluir",
                        key=f"del{cand['id']}"
                    ):

                        with engine.connect() as conn:

                            conn.execute(
                                text("DELETE FROM candidatos WHERE id=:id"),
                                {"id":cand["id"]}
                            )

                            conn.commit()

                        st.warning("Candidato excluído")
                        st.rerun()

# -----------------------------------
# PIPELINE KANBAN
# -----------------------------------
    with tab3:

        st.subheader("Pipeline de seleção")

        df_c = carregar_candidatos()

        etapas = [
            "Triagem",
            "Entrevista RH",
            "Teste Técnico",
            "Entrevista gestor",
            "Entrevista Cultura",
            "Finalizada"
        ]

        cols = st.columns(len(etapas))

        for i,etapa in enumerate(etapas):

            with cols[i]:

                st.markdown(f"### {etapa}")

                candidatos = df_c[
                    df_c["status_geral"]==etapa
                ]

                for _,cand in candidatos.iterrows():

                    st.info(cand["candidato"])
