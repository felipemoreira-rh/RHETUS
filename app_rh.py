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

# --- 3. INICIALIZAÇÃO DE BANCO (Blindagem de Colunas) ---
def inicializar_banco():
    with engine.connect() as conn:
        # Criar tabelas se não existirem
        conn.execute(text("CREATE TABLE IF NOT EXISTS vagas (id SERIAL PRIMARY KEY, nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS candidatos (id SERIAL PRIMARY KEY, candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, entrevista_rh DATE, entrevista_gestor DATE, entrevista_cultura DATE, historico TEXT)"))
        
        # Forçar criação de colunas caso o banco já existisse sem elas
        colunas_necessarias = {
            "historico": "TEXT",
            "entrevista_rh": "DATE",
            "entrevista_gestor": "DATE",
            "entrevista_cultura": "DATE",
            "envio_proposta": "BOOLEAN DEFAULT FALSE"
        }
        for col, tipo in colunas_necessarias.items():
            try:
                conn.execute(text(f"ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS {col} {tipo}"))
                conn.commit()
            except:
                pass
        conn.commit()

inicializar_banco()

# --- 4. CSS CUSTOMIZADO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    html, body, [class*="css"], [data-testid="stSidebar"] { font-family: 'Space Grotesk', sans-serif !important; }
    .header-rh { font-size: 42px; font-weight: 700; color: #8DF768; margin-bottom: 20px; border-left: 10px solid #151514; padding-left: 15px; }
    div[data-testid="stExpander"] { border: 1px solid #333; border-radius: 10px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. FUNÇÕES DE APOIO ---
def carregar_vagas():
    return pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)

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

# --- 9. CANDIDATOS (ADICIONAR E EXCLUIR) ---
elif menu == "⚙️ CANDIDATOS":
    df_vagas = carregar_vagas()
    
    # 🟢 FORMULÁRIO DE INCLUSÃO
    st.markdown("### ➕ Adicionar Novo Candidato")
    if not df_vagas.empty:
        with st.container(border=True):
            with st.form("form_add_cand", clear_on_submit=True):
                c1, c2 = st.columns(2)
                nome_novo = c1.text_input("Nome do Candidato")
                vaga_vinculo = c2.selectbox("Vaga", df_vagas["nome_vaga"].tolist())
                
                if st.form_submit_button("✅ CADASTRAR NO BANCO"):
                    if nome_novo:
                        with engine.connect() as conn:
                            log_inicial = f"➔ {datetime.now().strftime('%d/%m/%Y %H:%M')}: Cadastro realizado (Triagem)\n"
                            conn.execute(text("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral, historico) VALUES (:n, :v, 'Triagem', :h)"),
                                         {"n": nome_novo, "v": vaga_vinculo, "h": log_inicial})
                            conn.commit()
                        st.success(f"Candidato {nome_novo} cadastrado!")
                        st.rerun()
                    else: st.error("Insira o nome.")
    else:
        st.warning("⚠️ Crie uma vaga primeiro na aba 'Vagas'.")

    st.divider()

    # 🔍 GESTÃO E EXCLUSÃO
    st.markdown("### 🔍 Gestão de Candidatos")
    # Busca todas as colunas para evitar o KeyError
    df_c = pd.read_sql("SELECT * FROM candidatos ORDER BY id DESC", engine)
    
    if df_c.empty:
        st.info("Nenhum candidato cadastrado ainda.")
    else:
        status_list = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista gestor", "Entrevista Cultura", "Finalizada"]
        
        for _, cand in df_c.iterrows():
            # Tratamento seguro para a coluna 'historico' e outras
            hist_valor = cand.get('historico', "") if pd.notnull(cand.get('historico')) else ""
            vaga_valor = cand.get('vaga_vinculada', "Sem Vaga")

            with st.expander(f"👤 {cand['candidato'].upper()} | {vaga_valor} | Status: {cand['status_geral']}"):
                col_edit, col_del = st.columns([4, 1])
                
                with col_edit:
                    n_status = st.selectbox("Mudar Fase", status_list, 
                                            index=status_list.index(cand['status_geral']) if cand['status_geral'] in status_list else 0, 
                                            key=f"st_{cand['id']}")
                    
                    if st.button("💾 Salvar Alterações", key=f"sv_{cand['id']}", use_container_width=True):
                        if n_status != cand['status_geral']:
                            hist_valor = f"➔ {datetime.now().strftime('%d/%m/%Y %H:%M')}: Avançou para {n_status}\n" + hist_valor
                        
                        with engine.connect() as conn:
                            conn.execute(text("UPDATE candidatos SET status_geral=:s, historico=:h WHERE id=:id"),
                                         {"s": n_status, "h": hist_valor, "id": cand['id']})
                            conn.commit()
                        st.rerun()

                with col_del:
                    st.write("**Ação**")
                    if st.button("🗑️ EXCLUIR", key=f"del_{cand['id']}", type="secondary", use_container_width=True):
                        with engine.connect() as conn:
                            conn.execute(text("DELETE FROM candidatos WHERE id = :id"), {"id": cand['id']})
                            conn.commit()
                        st.warning("Candidato removido.")
                        st.rerun()
                
                if hist_valor:
                    st.caption("Linha do tempo:")
                    st.text(hist_valor)

# --- 10. ONBOARDING ---
elif menu == "🚀 ONBOARDING":
    st.subheader("Onboarding")
    df_on = pd.read_sql("SELECT * FROM candidatos WHERE status_geral = 'Finalizada'", engine)
    if df_on.empty:
        st.info("Nenhum candidato em onboarding.")
    else:
        st.dataframe(df_on, use_container_width=True)
