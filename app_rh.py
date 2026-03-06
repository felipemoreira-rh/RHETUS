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

# --- 3. INICIALIZAÇÃO E REPARO ---
def inicializar_banco():
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS vagas (nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS candidatos (candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, historico TEXT)"))
        conn.commit()

def reparar_banco_id():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE vagas ADD COLUMN IF NOT EXISTS id SERIAL"))
            conn.execute(text("ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS id SERIAL"))
            conn.commit()
            st.success("✅ Colunas de identificação sincronizadas!")
        except Exception as e:
            st.info("O banco já possui chaves ou não permite alteração direta. O app usará nomes como referência.")

inicializar_banco()

# --- 4. CSS (ESTILO ETUS) ---
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
def carregar_candidatos(): return pd.read_sql("SELECT * FROM candidatos", engine)

# --- 6. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS"])

st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- 7. INDICADORES ---
if menu == "📊 INDICADORES":
    df_v = carregar_vagas()
    df_c = carregar_candidatos()
    
    if not df_v.empty:
        hoje = pd.Timestamp(datetime.now().date())
        df_v['data_abertura'] = pd.to_datetime(df_v['data_abertura'])
        v_ativas = df_v[df_v['status_vaga'] == 'Aberta'].copy()
        v_ativas['aging'] = v_ativas['data_abertura'].apply(lambda x: (hoje - x).days)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 VAGAS ABERTAS", len(v_ativas))
        c2.metric("⏱️ AGING MÉDIO", f"{int(v_ativas['aging'].mean()) if not v_ativas.empty else 0} dias")
        c3.metric("👥 CANDIDATOS ATIVOS", len(df_c))

        st.subheader("🕒 Tempo de Abertura por Vaga (Aging)")
        st.plotly_chart(px.bar(v_ativas, x='aging', y='nome_vaga', orientation='h', color_discrete_sequence=['#8DF768']), use_container_width=True)

        st.subheader("📊 Distribuição por Etapa (%)")
        df_status = df_c.groupby(['vaga_vinculada', 'status_geral']).size().reset_index(name='qtd')
        fig = px.bar(df_status, y="vaga_vinculada", x="qtd", color="status_geral", orientation='h', barmode="relative")
        fig.update_layout(barnorm='percent')
        st.plotly_chart(fig, use_container_width=True)

# --- 8. VAGAS (COM BLINDAGEM DE ID) ---
elif menu == "🏢 VAGAS":
    if st.button("🛠️ REPARAR BANCO"): reparar_banco_id()
    
    with st.expander("➕ CADASTRAR NOVA VAGA"):
        with st.form("n_vaga"):
            nv = st.text_input("Nome da Vaga"); av = st.selectbox("Área", ["Comercial", "Operações", "Tecnologia", "RH", "Marketing"])
            gv = st.text_input("Gestor"); dv = st.date_input("Abertura", value=datetime.now())
            if st.form_submit_button("CRIAR"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO vagas (nome_vaga, area, status_vaga, gestor, data_abertura) VALUES (:n, :a, 'Aberta', :g, :d)"), {"n": nv, "a": av, "g": gv, "d": dv}); conn.commit()
                st.rerun()

    df_v = carregar_vagas()
    for i, row in df_v.iterrows():
        vid = row['id'] if 'id' in row and pd.notnull(row['id']) else f"idx_{i}"
        with st.expander(f"🏢 {row['nome_vaga'].upper()} | {row['status_vaga']}"):
            with st.form(f"ed_v_{vid}"):
                eg = st.text_input("Gestor", value=row['gestor'])
                es = st.selectbox("Status", ["Aberta", "Pausada", "Cancelada", "Finalizada"], index=0)
                if st.form_submit_button("💾 SALVAR"):
                    with engine.connect() as conn:
                        if 'id' in row and pd.notnull(row['id']):
                            conn.execute(text("UPDATE vagas SET gestor=:g, status_vaga=:s WHERE id=:id"), {"g": eg, "s": es, "id": row['id']})
                        else:
                            conn.execute(text("UPDATE vagas SET gestor=:g, status_vaga=:s WHERE nome_vaga=:n"), {"g": eg, "s": es, "n": row['nome_vaga']})
                        conn.commit()
                    st.rerun()
            if st.button("🗑️ EXCLUIR VAGA", key=f"del_v_{vid}"):
                with engine.connect() as conn:
                    if 'id' in row and pd.notnull(row['id']):
                        conn.execute(text("DELETE FROM vagas WHERE id=:id"), {"id": row['id']})
                    else:
                        conn.execute(text("DELETE FROM vagas WHERE nome_vaga=:n"), {"n": row['nome_vaga']})
                    conn.commit()
                st.rerun()

# --- 9. CANDIDATOS (COM BLINDAGEM DE ID) ---
elif menu == "⚙️ CANDIDATOS":
    df_vagas = carregar_vagas()
    with st.form("add_c"):
        cn = st.text_input("Nome"); cv = st.selectbox("Vaga", df_vagas["nome_vaga"].tolist() if not df_vagas.empty else ["Nenhuma"])
        if st.form_submit_button("➕ ADICIONAR"):
            with engine.connect() as conn:
                h = f"➔ {datetime.now().strftime('%d/%m/%Y')}: Cadastro"
                conn.execute(text("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral, historico) VALUES (:n, :v, 'Triagem', :h)"), {"n": cn, "v": cv, "h": h}); conn.commit()
            st.rerun()

    df_c = carregar_candidatos()
    for i, cand in df_c.iterrows():
        cid = cand['id'] if 'id' in cand and pd.notnull(cand['id']) else f"cidx_{i}"
        with st.expander(f"👤 {cand['candidato'].upper()} | {cand['status_geral']}"):
            ns = st.selectbox("Status", ["Triagem", "Entrevista", "Finalizada"], key=f"s_{cid}")
            if st.button("💾 ATUALIZAR", key=f"b_{cid}"):
                with engine.connect() as conn:
                    h = f"➔ {datetime.now().strftime('%d/%m/%Y')}: {ns}\n" + (cand['historico'] or "")
                    if 'id' in cand and pd.notnull(cand['id']):
                        conn.execute(text("UPDATE candidatos SET status_geral=:s, historico=:h WHERE id=:id"), {"s": ns, "h": h, "id": cand['id']})
                    else:
                        conn.execute(text("UPDATE candidatos SET status_geral=:s, historico=:h WHERE candidato=:n"), {"s": ns, "h": h, "n": cand['candidato']})
                    conn.commit()
                st.rerun()
            if st.button("🗑️ EXCLUIR", key=f"d_{cid}"):
                with engine.connect() as conn:
                    if 'id' in cand and pd.notnull(cand['id']):
                        conn.execute(text("DELETE FROM candidatos WHERE id=:id"), {"id": cand['id']})
                    else:
                        conn.execute(text("DELETE FROM candidatos WHERE candidato=:n"), {"n": cand['candidato']})
                    conn.commit()
                st.rerun()
                # --- 10. ONBOARDING ---
elif menu == "🚀 ONBOARDING":
    df_ap = pd.read_sql("SELECT * FROM candidatos WHERE status_geral = 'Finalizada'", engine)
    if not df_ap.empty:
        sel = st.selectbox("Colaborador:", df_ap["candidato"].tolist())
        st.write(f"Checklist para {sel} em desenvolvimento...")
    else:
        st.info("Nenhum candidato finalizado para Onboarding.")

