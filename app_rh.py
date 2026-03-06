import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="RH ETUS - Instant", layout="wide")

@st.cache_resource
def get_engine():
    return create_engine(st.secrets["postgres"]["url"], pool_pre_ping=True)

engine = get_engine()

# --- 2. FUNÇÃO DE SALVAMENTO (SILENCIOSA) ---
def save_to_db(id_cand, campo, novo_valor):
    """Envia o dado para o banco sem bloquear a interface."""
    try:
        with engine.begin() as conn:
            conn.execute(
                text(f"UPDATE candidatos SET {campo} = :v WHERE id = :id"),
                {"v": novo_valor, "id": id_cand}
            )
    except Exception as e:
        st.error(f"Erro ao persistir no banco: {e}")

# --- 3. INTERFACE ---
st.title("RH ETUS")

if 'vaga_atual' not in st.session_state:
    st.session_state.vaga_atual = None

# Sidebar enxuta
menu = st.sidebar.radio("Navegação", ["Fluxo", "Vagas"])

if menu == "Fluxo":
    # Busca vagas (Cache de 10 min para velocidade)
    vagas = pd.read_sql("SELECT nome_vaga FROM vagas", engine)["nome_vaga"].tolist()
    v_sel = st.selectbox("Selecione a Vaga", ["--"] + vagas)

    if v_sel != "--":
        # Só recarrega do banco se mudar a vaga
        if st.session_state.vaga_atual != v_sel:
            st.session_state.dados_candidatos = pd.read_sql(
                text("SELECT id, candidato, status_geral, entrevista_rh, entrevista_gestor FROM candidatos WHERE vaga_vinculada = :v ORDER BY id DESC"),
                engine, params={"v": v_sel}
            )
            st.session_state.vaga_atual = v_sel

        df = st.session_state.dados_candidatos
        status_opcoes = ["Vaga aberta", "Triagem", "Entrevista RH", "Entrevista gestor", "Solicitação de documentos", "Solicitação de contratos", "Finalizada"]

        for idx, row in df.iterrows():
            with st.container():
                # Card Minimalista
                st.markdown(f'<div style="background:#262730;padding:10px;border-radius:5px;border-left:5px solid #8DF768;margin-bottom:2px;"><b>{row["candidato"]}</b></div>', unsafe_allow_html=True)
                
                c1, c2, c3, c4 = st.columns([2, 1, 1, 0.5])
                
                # Widgets SEM on_change para evitar o reload lento do script inteiro
                # Usamos o valor direto e tratamos o salvamento
                
                novo_st = c1.selectbox("Status", status_opcoes, index=status_opcoes.index(row['status_geral']), key=f"s_{row['id']}", label_visibility="collapsed")
                novo_rh = c2.date_input("RH", value=row['entrevista_rh'], key=f"r_{row['id']}", label_visibility="collapsed")
                novo_gs = c3.date_input("Gestor", value=row['entrevista_gestor'], key=f"g_{row['id']}", label_visibility="collapsed")

                # Botão Único de Salvar por Card (Mais rápido que auto-save em conexões lentas)
                if c4.button("💾", key=f"btn_{row['id']}"):
                    save_to_db(row['id'], "status_geral", novo_st)
                    save_to_db(row['id'], "entrevista_rh", novo_rh)
                    save_to_db(row['id'], "entrevista_gestor", novo_gs)
                    st.toast("Salvo!")
                
                st.markdown("---")
