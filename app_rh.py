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

# --- 3. FUNÇÕES DE DADOS (COM CACHE) ---
@st.cache_data(ttl=60)
def carregar_vagas():
    df = pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)
    return df

@st.cache_data(ttl=60)
def carregar_candidatos():
    df = pd.read_sql("SELECT * FROM candidatos", engine)
    return df

def executar_sql(query, params=None):
    try:
        with engine.begin() as conn:
            conn.execute(text(query), params or {})
        st.cache_data.clear() 
        return True
    except Exception as e:
        st.error(f"Erro na operação: {e}")
        return False

# --- 4. INICIALIZAÇÃO E MIGRAÇÃO (PREVINE KEYERROR: ID) ---
def inicializar_banco():
    with engine.begin() as conn:
        # Cria tabelas se não existirem
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vagas (
                nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE
            );
            CREATE TABLE IF NOT EXISTS candidatos (
                candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, historico TEXT
            );
        """))
        # Força a criação da coluna ID caso a tabela já existisse sem ela
        try: conn.execute(text("ALTER TABLE vagas ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;"))
        except: pass
        try: conn.execute(text("ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;"))
        except: pass
        # Colunas de Onboarding (Garantia)
        cols_on = ["envio_proposta", "solic_documentos", "solic_contrato", "solic_acessos"]
        for col in cols_on:
            try: conn.execute(text(f"ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS {col} BOOLEAN DEFAULT FALSE;"))
            except: pass

inicializar_banco()

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("🏈 RH ETUS")
    st.divider()
    menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])

st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- 6. INDICADORES ---
if menu == "📊 INDICADORES":
    df_v = carregar_vagas()
    df_c = carregar_candidatos()
    
    if not df_v.empty:
        hoje = pd.Timestamp(datetime.now().date())
        df_v['data_abertura'] = pd.to_datetime(df_v['data_abertura'])
        v_ativas = df_v[df_v['status_vaga'] == 'Aberta'].copy()
        v_ativas['aging'] = v_ativas['data_abertura'].apply(lambda x: (hoje - x).days if pd.notnull(x) else 0)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 VAGAS ABERTAS", len(v_ativas))
        c2.metric("⏱️ AGING MÉDIO", f"{int(v_ativas['aging'].mean()) if not v_ativas.empty else 0} dias")
        c3.metric("👥 CANDIDATOS ATIVOS", len(df_c[df_c['status_geral'] != 'Finalizada']) if not df_c.empty else 0)

        st.subheader("🕒 Aging por Vaga")
        st.plotly_chart(px.bar(v_ativas, x='aging', y='nome_vaga', orientation='h', color_discrete_sequence=['#8DF768']), use_container_width=True)

# --- 7. VAGAS (COM PROTEÇÃO DE ID) ---
elif menu == "🏢 VAGAS":
    with st.expander("➕ CADASTRAR NOVA VAGA"):
        with st.form("n_vaga", clear_on_submit=True):
            nv = st.text_input("Nome da Vaga")
            gv = st.text_input("Gestor")
            av = st.selectbox("Área", ["Comercial", "Operações", "RH", "Tecnologia", "Marketing"])
            if st.form_submit_button("CRIAR"):
                if nv:
                    executar_sql("INSERT INTO vagas (nome_vaga, area, status_vaga, gestor, data_abertura) VALUES (:n, :a, 'Aberta', :g, :d)",
                                 {"n": nv, "a": av, "g": gv, "d": datetime.now().date()})
                    st.rerun()

    df_v = carregar_vagas()
    for i, row in df_v.iterrows():
        # Usa o ID se existir, senão usa o índice da linha como chave visual (key)
        v_id = row['id'] if 'id' in df_v.columns else i
        
        with st.expander(f"🏢 {row['nome_vaga'].upper()} | {row['status_vaga']}"):
            col1, col2 = st.columns([3, 1])
            with col1:
                with st.form(f"ed_v_{v_id}"):
                    eg = st.text_input("Gestor", value=row['gestor'])
                    es = st.selectbox("Status", ["Aberta", "Pausada", "Finalizada"], index=["Aberta", "Pausada", "Finalizada"].index(row['status_vaga']))
                    if st.form_submit_button("SALVAR"):
                        if 'id' in df_v.columns:
                            executar_sql("UPDATE vagas SET gestor=:g, status_vaga=:s WHERE id=:id", {"g": eg, "s": es, "id": row['id']})
                        else:
                            executar_sql("UPDATE vagas SET gestor=:g, status_vaga=:s WHERE nome_vaga=:n", {"g": eg, "s": es, "n": row['nome_vaga']})
                        st.rerun()
            with col2:
                if st.button("🗑️ EXCLUIR", key=f"del_v_{v_id}"):
                    if 'id' in df_v.columns:
                        executar_sql("DELETE FROM vagas WHERE id=:id", {"id": row['id']})
                    else:
                        executar_sql("DELETE FROM vagas WHERE nome_vaga=:n", {"n": row['nome_vaga']})
                    st.rerun()

# --- 8. CANDIDATOS ---
elif menu == "⚙️ CANDIDATOS":
    df_vagas = carregar_vagas()
    df_c = carregar_candidatos()

    with st.expander("➕ ADICIONAR NOVO CANDIDATO"):
        with st.form("add_c", clear_on_submit=True):
            cn = st.text_input("Nome do Candidato")
            cv = st.selectbox("Vincular à Vaga", df_vagas["nome_vaga"].tolist() if not df_vagas.empty else ["Nenhuma"])
            if st.form_submit_button("CADASTRAR"):
                if cn and cv != "Nenhuma":
                    h = f"➔ {datetime.now().strftime('%d/%m/%Y')}: Cadastro inicial"
                    executar_sql("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral, historico) VALUES (:n, :v, 'Triagem', :h)",
                                 {"n": cn, "v": cv, "h": h})
                    st.rerun()

    if not df_c.empty:
        for v_nome in df_vagas["nome_vaga"].unique():
            cands = df_c[df_c['vaga_vinculada'] == v_nome]
            if not cands.empty:
                st.subheader(f"📁 {v_nome}")
                for i, cand in cands.iterrows():
                    c_id = cand['id'] if 'id' in df_c.columns else f"c_{i}"
                    with st.expander(f"👤 {cand['candidato']} | {cand['status_geral']}"):
                        etapas = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada"]
                        novo_st = st.selectbox("Mover para:", etapas, index=etapas.index(cand['status_geral']) if cand['status_geral'] in etapas else 0, key=f"sel_{c_id}")
                        
                        col_up, col_del = st.columns(2)
                        if col_up.button("ATUALIZAR", key=f"up_{c_id}"):
                            novo_h = f"➔ {datetime.now().strftime('%d/%m/%Y')}: {novo_st}\n" + (cand['historico'] or "")
                            if 'id' in df_c.columns:
                                executar_sql("UPDATE candidatos SET status_geral=:s, historico=:h WHERE id=:id", {"s": novo_st, "h": novo_h, "id": cand['id']})
                            else:
                                executar_sql("UPDATE candidatos SET status_geral=:s, historico=:h WHERE candidato=:n AND vaga_vinculada=:v", {"s": novo_st, "h": novo_h, "n": cand['candidato'], "v": v_nome})
                            st.rerun()
                        
                        if col_del.button("EXCLUIR", key=f"del_{c_id}"):
                            if 'id' in df_c.columns:
                                executar_sql("DELETE FROM candidatos WHERE id=:id", {"id": cand['id']})
                            else:
                                executar_sql("DELETE FROM candidatos WHERE candidato=:n AND vaga_vinculada=:v", {"n": cand['candidato'], "v": v_nome})
                            st.rerun()

# --- 9. ONBOARDING ---
elif menu == "🚀 ONBOARDING":
    df_on = carregar_candidatos()
    if not df_on.empty:
        df_on = df_on[df_on['status_geral'] == 'Finalizada']
    
    if df_on is None or df_on.empty:
        st.info("Nenhum candidato em 'Finalizada'.")
    else:
        sel = st.selectbox("Colaborador:", df_on["candidato"].tolist())
        c_data = df_on[df_on["candidato"] == sel].iloc[0]
        
        st.markdown(f"### Checklist: {sel}")
        cols = st.columns(4)
        chks = ["envio_proposta", "solic_documentos", "solic_contrato", "solic_acessos"]
        labels = ["Proposta", "Documentos", "Contrato", "Acessos"]
        novos_vals = {}
        
        for idx, col_db in enumerate(chks):
            # Fallback caso a coluna ainda não exista no DataFrame
            val_atual = bool(c_data[col_db]) if col_db in c_data else False
            novos_vals[col_db] = cols[idx].checkbox(labels[idx], value=val_atual, key=f"on_{sel}_{col_db}")
            
        if st.button("SALVAR ONBOARDING"):
            sets = ", ".join([f"{k}=:{k}" for k in novos_vals.keys()])
            if 'id' in df_on.columns:
                executar_sql(f"UPDATE candidatos SET {sets} WHERE id=:id", {**novos_vals, "id": c_data["id"]})
            else:
                executar_sql(f"UPDATE candidatos SET {sets} WHERE candidato=:n", {**novos_vals, "n": sel})
            st.success("Salvo!")
            st.rerun()
