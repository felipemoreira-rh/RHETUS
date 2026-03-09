import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from datetime import datetime
import os

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(
    page_title="RH ETUS - Gestão Pro", 
    layout="wide", 
    page_icon="logo.png" 
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    html, body, [class*="css"], [data-testid="stSidebar"] { font-family: 'Space Grotesk', sans-serif !important; }
    .header-rh { font-size: 42px; font-weight: 700; color: #8DF768; margin-bottom: 30px; border-left: 10px solid #151514; padding-left: 15px; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE BANCO DE DADOS ---
@st.cache_resource
def get_engine():
    try:
        DB_URL = st.secrets["postgres"]["url"]
        return create_engine(DB_URL, pool_size=5, max_overflow=10, connect_args={"sslmode": "require"})
    except KeyError:
        st.error("Erro: 'postgres.url' não encontrado nos Secrets.")
        st.stop()

engine = get_engine()

# --- 3. FUNÇÕES DE DADOS ---
@st.cache_data(ttl=60)
def carregar_vagas():
    return pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)

@st.cache_data(ttl=60)
def carregar_candidatos():
    return pd.read_sql("SELECT * FROM candidatos", engine)

def executar_sql(query, params=None):
    try:
        with engine.begin() as conn:
            conn.execute(text(query), params or {})
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro na operação: {e}")
        return False

# --- 4. INICIALIZAÇÃO DO BANCO ---
def inicializar_banco():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vagas (
                id SERIAL PRIMARY KEY, 
                nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, 
                data_abertura DATE, data_fechamento DATE
            );
            CREATE TABLE IF NOT EXISTS candidatos (
                id SERIAL PRIMARY KEY, 
                candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, historico TEXT,
                motivo_perda TEXT,
                envio_proposta BOOLEAN DEFAULT FALSE, solic_documentos BOOLEAN DEFAULT FALSE,
                solic_contrato BOOLEAN DEFAULT FALSE, solic_acessos BOOLEAN DEFAULT FALSE
            );
        """))
        try: conn.execute(text("ALTER TABLE vagas ADD COLUMN IF NOT EXISTS data_fechamento DATE;"))
        except: pass
        try: conn.execute(text("ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS motivo_perda TEXT;"))
        except: pass
        try: conn.execute(text("ALTER TABLE vagas ADD COLUMN IF NOT EXISTS id SERIAL;"))
        except: pass

inicializar_banco()

# --- 5. SIDEBAR (DEFINIÇÃO DO MENU) ---
# Movido para cima para evitar o NameError
with st.sidebar:
    caminho_logo = "logo.png" 
    if os.path.exists(caminho_logo):
        st.image(caminho_logo, use_container_width=True)
    else:
        st.markdown("## 🏢 RH ETUS")
    st.divider()
    menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])

st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- 6. ABA: INDICADORES ---
if menu == "📊 INDICADORES":
    df_v = carregar_vagas()
    df_c = carregar_candidatos()
    
    if not df_v.empty:
        df_v['data_abertura'] = pd.to_datetime(df_v['data_abertura'], errors='coerce')
        df_v['data_fechamento'] = pd.to_datetime(df_v['data_fechamento'], errors='coerce')
        
        df_fechadas = df_v[df_v['status_vaga'] == 'Finalizada'].copy()
        df_fechadas = df_fechadas.dropna(subset=['data_abertura', 'data_fechamento'])
        
        if not df_fechadas.empty:
            df_fechadas['time_to_hire'] = (df_fechadas['data_fechamento'] - df_fechadas['data_abertura']).dt.days
            media_calc = df_fechadas['time_to_hire'].mean()
            avg_tth = int(media_calc) if pd.notnull(media_calc) else 0
        else:
            avg_tth = 0

        c1, c2, c3 = st.columns(3)
        c1.metric("📌 VAGAS ATIVAS", len(df_v[df_v['status_vaga'] == 'Aberta']))
        c2.metric("⏱️ TIME-TO-HIRE MÉDIO", f"{avg_tth} dias")
        
        cands_ativos = len(df_c[~df_c['status_geral'].isin(['Finalizada', 'Perda'])]) if not df_c.empty else 0
        c3.metric("👥 CANDIDATOS ATIVOS", cands_ativos)

        st.divider()
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("📊 Conversão por Etapa")
            if not df_c.empty:
                ordem_etapas = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada"]
                contagem_etapas = df_c['status_geral'].value_counts().reindex(ordem_etapas).fillna(0).reset_index()
                contagem_etapas.columns = ['Etapa', 'Candidatos']
                fig_funil = px.funnel(contagem_etapas, x='Candidatos', y='Etapa', color_discrete_sequence=['#8DF768'])
                st.plotly_chart(fig_funil, use_container_width=True)

        with col_right:
            st.subheader("❌ Motivos de Desistência/Perda")
            if not df_c.empty and df_c['motivo_perda'].notnull().any():
                df_perda = df_c[df_c['motivo_perda'].notnull()]
                fig_perda = px.pie(df_perda, names='motivo_perda', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_perda, use_container_width=True)
            else:
                st.info("Ainda não há dados de motivos de perda registrados.")

# --- 7. ABA: VAGAS ---
elif menu == "🏢 VAGAS":
    with st.expander("➕ CADASTRAR NOVA VAGA"):
        with st.form("n_vaga", clear_on_submit=True):
            nv = st.text_input("Nome da Vaga")
            gv = st.text_input("Gestor Direto")
            av = st.selectbox("Área", ["Comercial", "Operações", "RH", "Tecnologia", "Marketing", "Financeiro"])
            if st.form_submit_button("CRIAR VAGA"):
                if nv:
                    executar_sql("INSERT INTO vagas (nome_vaga, area, status_vaga, gestor, data_abertura) VALUES (:n, :a, 'Aberta', :g, :d)",
                                 {"n": nv, "a": av, "g": gv, "d": datetime.now().date()})
                    st.rerun()

    df_v = carregar_vagas()
    for i, row in df_v.iterrows():
        row_id = row.get('id', i)
        with st.expander(f"🏢 {row['nome_vaga'].upper()} | {row['status_vaga']}"):
            col1, col2 = st.columns([3, 1])
            with col1:
                with st.form(f"ed_v_{row_id}"):
                    eg = st.text_input("Gestor", value=row['gestor'])
                    es = st.selectbox("Status", ["Aberta", "Pausada", "Finalizada"], index=["Aberta", "Pausada", "Finalizada"].index(row['status_vaga']))
                    if st.form_submit_button("SALVAR ALTERAÇÕES"):
                        data_f = datetime.now().date() if es == "Finalizada" else None
                        executar_sql("UPDATE vagas SET gestor=:g, status_vaga=:s, data_fechamento=:df WHERE nome_vaga=:n", 
                                     {"g": eg, "s": es, "df": data_f, "n": row['nome_vaga']})
                        st.rerun()
            with col2:
                if st.button("🗑️ EXCLUIR", key=f"del_v_{row_id}", use_container_width=True):
                    executar_sql("DELETE FROM vagas WHERE nome_vaga=:n", {"n": row['nome_vaga']})
                    st.rerun()

# --- 8. ABA: CANDIDATOS ---
elif menu == "⚙️ CANDIDATOS":
    df_vagas = carregar_vagas()
    df_c = carregar_candidatos()
    with st.expander("➕ ADICIONAR NOVO CANDIDATO"):
        if not df_vagas.empty:
            with st.form("add_c", clear_on_submit=True):
                cn = st.text_input("Nome do Candidato")
                cv = st.selectbox("Vincular à Vaga", df_vagas["nome_vaga"].tolist())
                if st.form_submit_button("CADASTRAR"):
                    if cn:
                        h = f"➔ {datetime.now().strftime('%d/%m/%Y')}: Cadastro inicial"
                        executar_sql("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral, historico) VALUES (:n, :v, 'Triagem', :h)",
                                     {"n": cn, "v": cv, "h": h})
                        st.rerun()

    if not df_c.empty:
        for i, cand in df_c.iterrows():
            c_id = cand.get('id', i)
            with st.expander(f"👤 {cand['candidato']} ({cand['status_geral']})"):
                etapas = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada"]
                idx_etapa = etapas.index(cand['status_geral']) if cand['status_geral'] in etapas else 0
                c_edit, c_del = st.columns([3, 1])
                with c_edit:
                    novo_st = st.selectbox("Mover Etapa", etapas, index=idx_etapa, key=f"st_{c_id}")
                    if st.button("ATUALIZAR STATUS", key=f"up_{c_id}"):
                        novo_h = f"➔ {datetime.now().strftime('%d/%m/%Y')}: {novo_st}\n" + (cand['historico'] or "")
                        executar_sql("UPDATE candidatos SET status_geral=:s, historico=:h WHERE candidato=:n", 
                                     {"s": novo_st, "h": novo_h, "n": cand['candidato']})
                        st.rerun()
                with c_del:
                    st.write("---")
                    motivo = st.selectbox("Motivo da Saída", ["-", "Pretensão Salarial", "Falta de Fit Cultural", "Desistência", "Reprovado Técnico", "Outros"], key=f"mot_{c_id}")
                    if st.button("❌ REGISTRAR PERDA", key=f"perda_{c_id}"):
                        if motivo != "-":
                            executar_sql("UPDATE candidatos SET motivo_perda=:m, status_geral='Perda' WHERE candidato=:n", {"m": motivo, "n": cand['candidato']})
                            st.rerun()
                        else: st.warning("Selecione um motivo.")

# --- 9. ABA: ONBOARDING ---
elif menu == "🚀 ONBOARDING":
    df_on = pd.read_sql("SELECT * FROM candidatos WHERE status_geral = 'Finalizada'", engine)
    if not df_on.empty:
        sel_c = st.selectbox("Selecione o Colaborador:", df_on["candidato"].tolist())
        c_data = df_on[df_on["candidato"] == sel_c].iloc[0]
        items = {"envio_proposta": "✅ Proposta", "solic_documentos": "📄 Documentos", "solic_contrato": "✍️ Contrato", "solic_acessos": "🔑 Acessos"}
        res_on = {}
        cols = st.columns(4)
        for i, (key, label) in enumerate(items.items()):
            res_on[key] = cols[i].checkbox(label, value=bool(c_data.get(key, False)), key=f"chk_{sel_c}_{key}")
        if st.button("SALVAR PROGRESSO"):
            set_query = ", ".join([f"{k}=:{k}" for k in res_on.keys()])
            executar_sql(f"UPDATE candidatos SET {set_query} WHERE candidato=:n", {**res_on, "n": sel_c})
            st.rerun()
