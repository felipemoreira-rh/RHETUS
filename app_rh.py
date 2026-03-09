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
    html, body, [class*="css"], [data-testid="stSidebar"] { font-family: 'Space Grotesk', sans-serif !important; }
    .header-rh { font-size: 42px; font-weight: 700; color: #8DF768; margin-bottom: 30px; border-left: 10px solid #151514; padding-left: 15px; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE BANCO DE DADOS (SINGLETON) ---
@st.cache_resource
def get_engine():
    try:
        DB_URL = st.secrets["postgres"]["url"]
        return create_engine(DB_URL, pool_size=5, max_overflow=10, connect_args={"sslmode": "require"})
    except KeyError:
        st.error("Erro: 'postgres.url' não encontrado nos Secrets.")
        st.stop()

engine = get_engine()

# --- 3. FUNÇÕES DE DADOS (COM CACHE) ---
@st.cache_data(ttl=300) # Cache por 5 minutos
def carregar_vagas():
    return pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)

@st.cache_data(ttl=300)
def carregar_candidatos():
    return pd.read_sql("SELECT * FROM candidatos", engine)

def executar_sql(query, params=None):
    """Função auxiliar para escrita no banco com limpeza de cache"""
    try:
        with engine.begin() as conn:
            conn.execute(text(query), params or {})
        st.cache_data.clear() # Força recarregamento dos dados
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
                nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE
            );
            CREATE TABLE IF NOT EXISTS candidatos (
                id SERIAL PRIMARY KEY, 
                candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, historico TEXT,
                envio_proposta BOOLEAN DEFAULT FALSE, solic_documentos BOOLEAN DEFAULT FALSE,
                solic_contrato BOOLEAN DEFAULT FALSE, solic_acessos BOOLEAN DEFAULT FALSE
            );
        """))
        # Bloco de correção para tabelas pré-existentes sem a coluna ID
        conn.execute(text("ALTER TABLE vagas ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;"))
        conn.execute(text("ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;"))

inicializar_banco()

# --- 5. SIDEBAR E NAVEGAÇÃO ---
with st.sidebar:
    st.title("🏈 RH ETUS")
    st.divider()
    menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])

st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- 6. ABA: INDICADORES ---
if menu == "📊 INDICADORES":
    df_v = carregar_vagas()
    df_c = carregar_candidatos()
    
    if not df_v.empty:
        hoje = pd.Timestamp(datetime.now().date())
        df_v['data_abertura'] = pd.to_datetime(df_v['data_abertura'])
        v_ativas = df_v[df_v['status_vaga'] == 'Aberta'].copy()
        
        # Cálculo de Aging com segurança
        v_ativas['aging'] = v_ativas['data_abertura'].apply(lambda x: (hoje - x).days if pd.notnull(x) else 0)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 VAGAS ABERTAS", len(v_ativas))
        c2.metric("⏱️ AGING MÉDIO", f"{int(v_ativas['aging'].mean()) if not v_ativas.empty else 0} dias")
        c3.metric("👥 CANDIDATOS ATIVOS", len(df_c[df_c['status_geral'] != 'Finalizada']))

        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("🕒 Aging por Vaga")
            st.plotly_chart(px.bar(v_ativas, x='aging', y='nome_vaga', orientation='h', 
                                   color_discrete_sequence=['#8DF768']), use_container_width=True)
        with col_b:
            st.subheader("📊 Funil por Etapa (%)")
            if not df_c.empty:
                df_status = df_c.groupby(['vaga_vinculada', 'status_geral']).size().reset_index(name='qtd')
                fig = px.bar(df_status, y="vaga_vinculada", x="qtd", color="status_geral", orientation='h', barmode="relative")
                fig.update_layout(barnorm='percent', showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

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
                else: st.warning("O nome da vaga é obrigatório.")

    df_v = carregar_vagas()
    for _, row in df_v.iterrows():
        with st.expander(f"🏢 {row['nome_vaga'].upper()} | {row['status_vaga']}"):
            col1, col2 = st.columns([3, 1])
            with col1:
                with st.form(f"ed_v_{row['id']}"):
                    eg = st.text_input("Gestor", value=row['gestor'])
                    es = st.selectbox("Status", ["Aberta", "Pausada", "Finalizada"], index=["Aberta", "Pausada", "Finalizada"].index(row['status_vaga']))
                    if st.form_submit_button("SALVAR ALTERAÇÕES"):
                        executar_sql("UPDATE vagas SET gestor=:g, status_vaga=:s WHERE id=:id", {"g": eg, "s": es, "id": row['id']})
                        st.rerun()
            with col2:
                st.write("Ações")
                if st.button("🗑️ EXCLUIR", key=f"del_v_{row['id']}", use_container_width=True):
                    executar_sql("DELETE FROM vagas WHERE id=:id", {"id": row['id']})
                    st.rerun()

# --- 8. ABA: CANDIDATOS ---
elif menu == "⚙️ CANDIDATOS":
    df_vagas = carregar_vagas()
    df_c = carregar_candidatos()

    with st.expander("➕ ADICIONAR NOVO CANDIDATO"):
        if df_vagas.empty:
            st.warning("Cadastre uma vaga antes de adicionar candidatos.")
        else:
            with st.form("add_c", clear_on_submit=True):
                cn = st.text_input("Nome do Candidato")
                cv = st.selectbox("Vincular à Vaga", df_vagas["nome_vaga"].tolist())
                if st.form_submit_button("CADASTRAR"):
                    if cn:
                        h = f"➔ {datetime.now().strftime('%d/%m/%Y')}: Cadastro inicial"
                        executar_sql("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral, historico) VALUES (:n, :v, 'Triagem', :h)",
                                     {"n": cn, "v": cv, "h": h})
                        st.rerun()

    st.divider()
    
    if not df_c.empty:
        for v_nome in df_vagas["nome_vaga"].unique():
            cands_vaga = df_c[df_c['vaga_vinculada'] == v_nome]
            if not cands_vaga.empty:
                st.subheader(f"📁 {v_nome}")
                for _, cand in cands_vaga.iterrows():
                    with st.expander(f"👤 {cand['candidato']} ({cand['status_geral']})"):
                        etapas = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada"]
                        idx_etapa = etapas.index(cand['status_geral']) if cand['status_geral'] in etapas else 0
                        
                        c_edit, c_del = st.columns([3, 1])
                        novo_st = c_edit.selectbox("Mover Etapa", etapas, index=idx_etapa, key=f"st_{cand['id']}")
                        
                        if c_edit.button("ATUALIZAR STATUS", key=f"up_{cand['id']}"):
                            novo_h = f"➔ {datetime.now().strftime('%d/%m/%Y')}: {novo_st}\n" + (cand['historico'] or "")
                            executar_sql("UPDATE candidatos SET status_geral=:s, historico=:h WHERE id=:id", 
                                         {"s": novo_st, "h": novo_h, "id": cand['id']})
                            st.rerun()
                            
                        if c_del.button("EXCLUIR", key=f"del_c_{cand['id']}", use_container_width=True):
                            executar_sql("DELETE FROM candidatos WHERE id=:id", {"id": cand['id']})
                            st.rerun()
                        
                        st.caption("Histórico")
                        st.text(cand['historico'])

# --- 9. ABA: ONBOARDING ---
elif menu == "🚀 ONBOARDING":
    df_on = pd.read_sql("SELECT * FROM candidatos WHERE status_geral = 'Finalizada'", engine)
    
    if df_on.empty:
        st.info("Nenhum candidato em fase de Onboarding (Status 'Finalizada').")
    else:
        sel_c = st.selectbox("Selecione o Colaborador:", df_on["candidato"].tolist())
        c_data = df_on[df_on["candidato"] == sel_c].iloc[0]
        
        st.subheader(f"Checklist: {sel_c}")
        
        # Sistema de Checklist dinâmico
        items = {
            "envio_proposta": "✅ Envio de Proposta",
            "solic_documentos": "📄 Solicitação de Documentos",
            "solic_contrato": "✍️ Assinatura de Contrato",
            "solic_acessos": "🔑 Liberação de Acessos"
        }
        
        res_on = {}
        cols = st.columns(len(items))
        for i, (key, label) in enumerate(items.items()):
            res_on[key] = cols[i].checkbox(label, value=bool(c_data[key]), key=f"chk_{c_data['id']}_{key}")
            
        if st.button("SALVAR PROGRESSO", use_container_width=True):
            set_query = ", ".join([f"{k}=:{k}" for k in res_on.keys()])
            executar_sql(f"UPDATE candidatos SET {set_query} WHERE id=:id", {**res_on, "id": c_data["id"]})
            st.success("Onboarding atualizado!")
            st.rerun()
