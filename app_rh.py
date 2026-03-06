import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from datetime import datetime

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RH ETUS - Gestão Pro", layout="wide", page_icon="🏈")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif !important; }
    .header-rh { font-size: 42px; font-weight: 700; color: #8DF768; border-left: 10px solid #8DF768; padding-left: 15px; margin-bottom: 20px; }
    .stMetric { background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    div[data-testid="stExpander"] { border: 1px solid #444; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO COM O BANCO ---
try:
    DB_URL = st.secrets["postgres"]["url"]
    engine = create_engine(DB_URL, connect_args={"sslmode": "require"})
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- 3. MANUTENÇÃO AUTOMÁTICA DO BANCO (Evita o KeyError) ---
def ajustar_banco():
    with engine.connect() as conn:
        # Criar tabelas base
        conn.execute(text("CREATE TABLE IF NOT EXISTS vagas (id SERIAL PRIMARY KEY, nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS candidatos (id SERIAL PRIMARY KEY, candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, historico TEXT)"))
        
        # Lista de colunas que o app precisa para não quebrar
        colunas = {
            "entrevista_rh": "DATE",
            "entrevista_gestor": "DATE",
            "entrevista_cultura": "DATE",
            "historico": "TEXT"
        }
        for col, tipo in colunas.items():
            try:
                conn.execute(text(f"ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS {col} {tipo}"))
            except: pass
        conn.commit()

ajustar_banco()

# --- 4. CARREGAMENTO DE DADOS ---
def get_vagas(): return pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)
def get_candidatos(): return pd.read_sql("SELECT * FROM candidatos", engine)

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("🏈 ETUS RH")
    menu = st.radio("NAVEGAÇÃO", ["📊 DASHBOARD", "🏢 VAGAS", "👥 CANDIDATOS"])

st.markdown(f'<div class="header-rh">RH ETUS - {menu}</div>', unsafe_allow_html=True)

# --- 6. ABA: DASHBOARD ---
if menu == "📊 DASHBOARD":
    df_c = get_candidatos()
    df_v = get_vagas()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Vagas Abertas", len(df_v))
    c2.metric("Total Candidatos", len(df_c))
    c3.metric("Em Entrevista", len(df_c[df_c['status_geral'].str.contains('Entrevista', na=False)]))
    
    st.divider()
    if not df_c.empty:
        fig = px.bar(df_c, x='status_geral', title="Candidatos por Etapa", color_discrete_sequence=['#8DF768'])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aguardando dados para gerar gráficos.")

# --- 7. ABA: VAGAS ---
elif menu == "🏢 VAGAS":
    with st.expander("➕ CADASTRAR NOVA VAGA"):
        with st.form("f_vaga"):
            n = st.text_input("Nome da Vaga")
            g = st.text_input("Gestor Responsável")
            if st.form_submit_button("CRIAR"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO vagas (nome_vaga, gestor, status_vaga, data_abertura) VALUES (:n, :g, 'Aberta', :d)"),
                                 {"n": n, "g": g, "d": datetime.now().date()})
                    conn.commit()
                st.rerun()
    
    st.subheader("Lista de Vagas")
    st.table(get_vagas()[["nome_vaga", "gestor", "status_vaga"]])

# --- 8. ABA: CANDIDATOS ---
elif menu == "👥 CANDIDATOS":
    df_vagas = get_vagas()
    
    # FORMULÁRIO DE INCLUSÃO
    st.subheader("➕ Novo Candidato")
    if not df_vagas.empty:
        with st.form("add_c", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("Nome do Candidato")
            vaga = col2.selectbox("Vaga", df_vagas["nome_vaga"].tolist())
            if st.form_submit_button("CADASTRAR CANDIDATO"):
                if nome:
                    with engine.connect() as conn:
                        log = f"➔ {datetime.now().strftime('%d/%m/%Y')}: Iniciou Triagem"
                        conn.execute(text("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral, historico) VALUES (:n, :v, 'Triagem', :h)"),
                                     {"n": nome, "v": vaga, "h": log})
                        conn.commit()
                    st.success("Cadastrado!")
                    st.rerun()
    else:
        st.warning("Cadastre uma vaga primeiro.")

    st.divider()
    
    # LISTA DE CANDIDATOS COM EXCLUSÃO
    st.subheader("🔍 Gestão")
    df_c = get_candidatos()
    
    status_opcoes = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada"]
    
    for _, cand in df_c.iterrows():
        with st.expander(f"👤 {cand['candidato']} | Vaga: {cand['vaga_vinculada']}"):
            c_edit, c_del = st.columns([3, 1])
            
            with c_edit:
                novo_st = st.selectbox("Status", status_opcoes, index=status_opcoes.index(cand['status_geral']) if cand['status_geral'] in status_opcoes else 0, key=f"st_{cand['id']}")
                if st.button("💾 Atualizar", key=f"bt_{cand['id']}"):
                    with engine.connect() as conn:
                        h_novo = f"{cand['historico']}\n➔ {datetime.now().strftime('%d/%m/%Y')}: Mudou para {novo_st}"
                        conn.execute(text("UPDATE candidatos SET status_geral=:s, historico=:h WHERE id=:id"),
                                     {"s": novo_st, "h": h_novo, "id": cand['id']})
                        conn.commit()
                    st.rerun()
            
            with c_del:
                st.write("---")
                if st.button("🗑️ EXCLUIR", key=f"del_{cand['id']}", help="Remover permanentemente"):
                    with engine.connect() as conn:
                        conn.execute(text("DELETE FROM candidatos WHERE id = :id"), {"id": cand['id']})
                        conn.commit()
                    st.rerun()
            
            if cand['historico']:
                st.caption("Histórico:")
                st.info(cand['historico'])
