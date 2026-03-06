import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
import os

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="RH ETUS - Sistema de Recrutamento", layout="wide", page_icon="🟢")

# --- 2. CONEXÃO COM O BANCO ---
try:
    DB_URL = st.secrets["postgres"]["url"]
    engine = create_engine(DB_URL, connect_args={"sslmode": "require"})
except KeyError:
    st.error("Configure a URL do banco de dados nos Secrets do Streamlit.")
    st.stop()

# --- 3. CSS IDENTIDADE ETUS (MELHORADO) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif !important; }
    
    /* Título estilizado */
    .header-rh { font-size: 48px; font-weight: 700; color: #8DF768; border-left: 15px solid #151514; padding-left: 20px; margin-bottom: 20px; }
    
    /* Estilização de botões */
    .stButton>button { border-radius: 8px !important; }
    .stButton>button[kind="secondary"] { color: #ff4b4b !important; border-color: #ff4b4b !important; }
    
    /* Cards de Vagas */
    .vaga-card { background-color: #262730; padding: 20px; border-radius: 10px; border-left: 5px solid #8DF768; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNÇÕES DE BANCO ---
def carregar_vagas():
    return pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)

def carregar_candidatos_vaga(v_nome):
    query = text("SELECT * FROM candidatos WHERE vaga_vinculada = :v ORDER BY id")
    return pd.read_sql(query, engine, params={"v": v_nome})

# --- 5. SIDEBAR (LOGO E MENU) ---
with st.sidebar:
    # Tenta carregar a logo
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.markdown("### [LOGO ETUS]")
    
    st.divider()
    menu = st.radio("NAVEGAÇÃO", ["📊 DASHBOARD", "🏢 GESTÃO DE VAGAS", "⚙️ FLUXO DE CANDIDATOS"])
    st.divider()
    st.info("Sistema conectado ao Neon Cloud (AWS)")

st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- 6. MENU: DASHBOARD ---
if menu == "📊 DASHBOARD":
    df_c = pd.read_sql("SELECT * FROM candidatos", engine)
    if not df_c.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 TOTAL NO FUNIL", len(df_c))
        c2.metric("✅ CONTRATADOS", len(df_c[df_c["aprovacao_final"] == "Sim"]))
        c3.metric("📂 VAGAS TOTAIS", len(pd.read_sql("SELECT * FROM vagas", engine)))
        
        st.divider()
        st.subheader("Distribuição por Etapa")
        fig = px.bar(df_c["status_geral"].value_counts().reset_index(), x="status_geral", y="count", 
                     color_discrete_sequence=['#8DF768'], template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("O Dashboard aparecerá assim que houver dados cadastrados.")

# --- 7. MENU: GESTÃO DE VAGAS ---
elif menu == "🏢 GESTÃO DE VAGAS":
    st.subheader("Criação e Controle de Vagas")
    
    # Cadastro de Nova Vaga (Sem parecer planilha)
    with st.expander("➕ CADASTRAR NOVA VAGA", expanded=True):
        with st.form("form_vaga"):
            c1, c2 = st.columns([2, 1])
            nome_nv = c1.text_input("Título da Vaga", placeholder="Ex: Gestor de Tráfego")
            area_nv = c2.selectbox("Área", ["Comercial", "TI", "RH", "Operacional", "Marketing", "Outros"])
            if st.form_submit_button("CRIAR VAGA"):
                if nome_nv:
                    with engine.connect() as conn:
                        conn.execute(text("INSERT INTO vagas (nome_vaga, area, status_vaga) VALUES (:n, :a, 'Aberta') ON CONFLICT DO NOTHING"), 
                                     {"n": nome_nv, "a": area_nv})
                        conn.commit()
                    st.success(f"Vaga '{nome_nv}' criada!")
                    st.rerun()

    st.divider()
    
    # Listagem de Vagas com opção de Exclusão
    df_v = carregar_vagas()
    if not df_v.empty:
        for idx, row in df_v.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.markdown(f"**{row['nome_vaga']}** | {row['area']}")
                
                # Botão de Excluir Vaga
                if col3.button("🗑️ EXCLUIR VAGA", key=f"del_v_{idx}"):
                    with engine.connect() as conn:
                        # Deleta candidatos vinculados primeiro por causa da integridade
                        conn.execute(text("DELETE FROM candidatos WHERE vaga_vinculada = :v"), {"v": row['nome_vaga']})
                        conn.execute(text("DELETE FROM vagas WHERE nome_vaga = :v"), {"v": row['nome_vaga']})
                        conn.commit()
                    st.warning(f"Vaga '{row['nome_vaga']}' removida!")
                    st.rerun()
                st.markdown("---")

# --- 8. MENU: FLUXO DE CANDIDATOS ---
elif menu == "⚙️ FLUXO DE CANDIDATOS":
    df_vagas = carregar_vagas()
    if df_vagas.empty:
        st.warning("Cadastre uma vaga no menu '🏢 GESTÃO DE VAGAS' primeiro.")
    else:
        v_list = df_vagas["nome_vaga"].tolist()
        v_sel = st.selectbox("Selecione a Vaga para gerenciar:", v_list)
        
        st.divider()
        
        # Ações do Candidato
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("### Adicionar")
            with st.form("add_cand", clear_on_submit=True):
                nome_c = st.text_input("Nome do Candidato")
                if st.form_submit_button("ADICIONAR AO FLUXO"):
                    if nome_c:
                        with engine.connect() as conn:
                            conn.execute(text("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral) VALUES (:c, :v, 'Vaga aberta')"), 
                                         {"c": nome_c, "v": v_sel})
                            conn.commit()
                        st.rerun()

        with c2:
            st.markdown("### Acompanhamento")
            df_c = carregar_candidatos_vaga(v_sel)
            
            if not df_c.empty:
                # Tabela editável para controle fino
                df_ed = st.data_editor(
                    df_c, key=f"ed_{v_sel}", use_container_width=True, hide_index=True,
                    column_config={
                        "id": None, "vaga_vinculada": None, # Oculta colunas desnecessárias
                        "status_geral": st.column_config.SelectboxColumn("Etapa", options=["Vaga aberta", "Triagem", "Entrevista RH", "Entrevista gestor", "Solicitação de documentos", "Solicitação de contratos", "Finalizada"]),
                        "aprovacao_final": st.column_config.SelectboxColumn("Aprovado?", options=["Sim", "Não"]),
                        "candidato": "Nome"
                    }
                )
                
                col_save, col_del = st.columns([1, 1])
                if col_save.button("💾 SALVAR ALTERAÇÕES", use_container_width=True):
                    with engine.connect() as conn:
                        conn.execute(text("DELETE FROM candidatos WHERE vaga_vinculada = :v"), {"v": v_sel})
                        df_ed.to_sql("candidatos", engine, if_exists="append", index=False)
                        conn.commit()
                    st.success("Alterações salvas no banco!")

                # Opção de excluir candidato específico
                cand_para_apagar = col_del.selectbox("Apagar Candidato:", ["--"] + df_c["candidato"].tolist(), label_visibility="collapsed")
                if col_del.button("🗑️ REMOVER SELECIONADO", type="secondary", use_container_width=True) and cand_para_apagar != "--":
                    with engine.connect() as conn:
                        conn.execute(text("DELETE FROM candidatos WHERE candidato = :c AND vaga_vinculada = :v"), {"c": cand_para_apagar, "v": v_sel})
                        conn.commit()
                    st.rerun()
            else:
                st.info("Nenhum candidato para esta vaga.")
