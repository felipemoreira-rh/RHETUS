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

# --- 3. REPARO E INICIALIZAÇÃO DO BANCO ---
def inicializar_banco():
    with engine.connect() as conn:
        # Garante estrutura básica das tabelas e IDs
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vagas (
                id SERIAL PRIMARY KEY, 
                nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS candidatos (
                id SERIAL PRIMARY KEY, candidato TEXT, vaga_vinculada TEXT, 
                status_geral TEXT, historico TEXT
            )
        """))
        conn.commit()
        
        # Manutenção de colunas extras
        c_cols = {
            "entrevista_rh": "DATE", "entrevista_gestor": "DATE", "entrevista_cultura": "DATE",
            "envio_proposta": "BOOLEAN DEFAULT FALSE", "solic_documentos": "BOOLEAN DEFAULT FALSE",
            "solic_contrato": "BOOLEAN DEFAULT FALSE", "solic_acessos": "BOOLEAN DEFAULT FALSE"
        }
        for col, tipo in c_cols.items():
            try: 
                conn.execute(text(f"ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS {col} {tipo}"))
                conn.commit()
            except: pass

def reparar_id_manual():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE vagas ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY"))
            conn.execute(text("ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY"))
            conn.commit()
            st.success("✅ Banco Reparado!")
        except Exception as e:
            st.error(f"Erro no reparo: {e}")

inicializar_banco()

# --- 4. CSS (ESTILO ETUS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    html, body, [class*="css"], [data-testid="stSidebar"] { font-family: 'Space Grotesk', sans-serif !important; }
    
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] p { color: #777777 !important; font-size: 18px !important; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] input:checked + div p { color: #8DF768 !important; font-weight: 700 !important; }

    [data-testid="stStatusWidget"] { visibility: hidden; }
    [data-testid="stStatusWidget"]::before {
        content: '🏈'; visibility: visible; position: fixed; top: 25px; right: 35px; font-size: 32px;
        animation: footballSpiral 1.2s ease-in-out infinite;
    }
    @keyframes footballSpiral {
        0% { transform: translateY(0px) rotate(0deg); }
        50% { transform: translateY(-8px) rotate(180deg) scale(1.1); }
        100% { transform: translateY(0px) rotate(360deg); }
    }
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
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])

st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- 7. INDICADORES ---
if menu == "📊 INDICADORES":
    df_v = carregar_vagas()
    df_c = pd.read_sql("SELECT * FROM candidatos", engine)
    
    if not df_v.empty and not df_c.empty:
        hoje = pd.Timestamp(datetime.now().date())
        df_v['data_abertura'] = pd.to_datetime(df_v['data_abertura'])
        v_ativas = df_v[df_v['status_vaga'] == 'Aberta'].copy()
        v_ativas['aging'] = v_ativas['data_abertura'].apply(lambda x: (hoje - x).days)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📌 VAGAS ABERTAS", len(v_ativas))
        c2.metric("⏱️ AGING MÉDIO", f"{int(v_ativas['aging'].mean()) if not v_ativas.empty else 0} dias")
        c3.metric("👥 CANDIDATOS ATIVOS", len(df_c[df_c['status_geral'] != 'Finalizada']))
        c4.metric("✅ CONTRATAÇÕES", len(df_c[df_c['status_geral'] == 'Finalizada']))

        st.divider()
        st.subheader("🕒 Tempo de Abertura por Vaga (Aging)")
        fig_aging = px.bar(v_ativas, x='aging', y='nome_vaga', orientation='h', color='aging', color_continuous_scale='Greens')
        st.plotly_chart(fig_aging, use_container_width=True)

        st.subheader("📊 Distribuição de Candidatos por Etapa (%)")
        df_status = df_c.groupby(['vaga_vinculada', 'status_geral']).size().reset_index(name='quantidade')
        fig_pct = px.bar(df_status, y="vaga_vinculada", x="quantidade", color="status_geral", orientation='h', barmode="relative", text_auto=True, color_discrete_sequence=px.colors.sequential.Greens_r)
        fig_pct.update_layout(barnorm='percent', xaxis_title="Porcentagem (%)")
        st.plotly_chart(fig_pct, use_container_width=True)
    else:
        st.info("💡 Adicione dados para ver os indicadores.")

# --- 8. VAGAS (COM EDIÇÃO E REPARO) ---
elif menu == "🏢 VAGAS":
    st.subheader("Gestão de Vagas")
    if st.button("🛠️ REPARAR BANCO (ID)"): reparar_id_manual()

    with st.expander("➕ CADASTRAR NOVA VAGA"):
        with st.form("n_vaga", clear_on_submit=True):
            n_v = st.text_input("Nome da Vaga"); a_v = st.selectbox("Departamento", ["Comercial", "Operações", "Tecnologia", "RH", "Marketing"])
            g_v = st.text_input("Gestor"); d_ab = st.date_input("Data Abertura", value=datetime.now())
            if st.form_submit_button("CRIAR VAGA"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO vagas (nome_vaga, area, status_vaga, gestor, data_abertura) VALUES (:n, :a, 'Aberta', :g, :d)"), {"n": n_v, "a": a_v, "g": g_v, "d": d_ab}); conn.commit()
                st.rerun()

    df_v = carregar_vagas()
    for _, row in df_v.iterrows():
        if 'id' not in row or pd.isna(row['id']):
            st.error(f"Vaga '{row['nome_vaga']}' sem ID. Clique no botão de reparo acima."); continue
        
        with st.expander(f"🏢 {row['nome_vaga'].upper()} | Status: {row['status_vaga']}"):
            with st.form(key=f"ed_v_{row['id']}"):
                eg = st.text_input("Gestor", value=row['gestor'])
                ea = st.selectbox("Área", ["Comercial", "Operações", "Tecnologia", "RH", "Marketing"], index=0)
                es = st.selectbox("Status", ["Aberta", "Pausada", "Cancelada", "Finalizada"], index=0)
                if st.form_submit_button("💾 SALVAR"):
                    with engine.connect() as conn:
                        conn.execute(text("UPDATE vagas SET gestor=:g, area=:a, status_vaga=:s WHERE id=:id"), {"g": eg, "a": ea, "s": es, "id": row['id']}); conn.commit()
                    st.rerun()
            if st.button(f"🗑️ EXCLUIR VAGA", key=f"del_v_{row['id']}"):
                with engine.connect() as conn:
                    conn.execute(text("DELETE FROM vagas WHERE id=:id"), {"id": row['id']}); conn.commit()
                st.rerun()

# --- 9. CANDIDATOS (INCLUIR E EXCLUIR) ---
elif menu == "⚙️ CANDIDATOS":
    df_vagas = carregar_vagas()
    st.subheader("➕ Novo Candidato")
    if not df_vagas.empty:
        with st.form("add_cand", clear_on_submit=True):
            cn = st.text_input("Nome"); cv = st.selectbox("Vaga", df_vagas["nome_vaga"].tolist())
            if st.form_submit_button("CADASTRAR"):
                with engine.connect() as conn:
                    h = f"➔ {datetime.now().strftime('%d/%m/%Y')}: Triagem\n"
                    conn.execute(text("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral, historico) VALUES (:n, :v, 'Triagem', :h)"), {"n": cn, "v": cv, "h": h}); conn.commit()
                st.rerun()
        
        st.divider()
        v_sel = st.selectbox("Filtrar Vaga:", ["Todos"] + df_vagas["nome_vaga"].tolist())
        df_c = pd.read_sql("SELECT * FROM candidatos", engine) if v_sel == "Todos" else carregar_candidatos_vaga(v_sel)
        
        for _, cand in df_c.iterrows():
            with st.expander(f"👤 {cand['candidato'].upper()} | {cand['status_geral']}"):
                col_st, col_del = st.columns([3, 1])
                novo_st = col_st.selectbox("Mover Etapa", ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista gestor", "Entrevista Cultura", "Finalizada"], key=f"st_{cand['id']}")
                if col_st.button(f"💾 ATUALIZAR", key=f"sv_{cand['id']}"):
                    with engine.connect() as conn:
                        h = f"➔ {datetime.now().strftime('%d/%m/%Y')}: {novo_st}\n" + (cand['historico'] if cand['historico'] else "")
                        conn.execute(text("UPDATE candidatos SET status_geral=:s, historico=:h WHERE id=:id"), {"s": novo_st, "h": h, "id": cand['id']}); conn.commit()
                    st.rerun()
                if col_del.button("🗑️ EXCLUIR", key=f"del_{cand['id']}"):
                    with engine.connect() as conn:
                        conn.execute(text("DELETE FROM candidatos WHERE id=:id"), {"id": cand['id']}); conn.commit()
                    st.rerun()

# --- 10. ONBOARDING ---
elif menu == "🚀 ONBOARDING":
    df_ap = pd.read_sql("SELECT * FROM candidatos WHERE status_geral = 'Finalizada'", engine)
    if not df_ap.empty:
        sel = st.selectbox("Colaborador:", df_ap["candidato"].tolist())
        st.write(f"Checklist para {sel} em desenvolvimento...")
    else:
        st.info("Nenhum candidato finalizado para Onboarding.")
