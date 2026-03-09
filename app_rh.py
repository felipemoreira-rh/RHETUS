import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from datetime import datetime
import os

# --- 1. CONFIGURAÇÃO E ESTILO (CORRIGIDO PARA TEMAS CLARO/ESCURO) ---
st.set_page_config(
    page_title="RH ETUS - Gestão Pro", 
    layout="wide", 
    page_icon="logo.png" 
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    
    /* Fonte Global */
    html, body, [class*="css"], [data-testid="stSidebar"] { 
        font-family: 'Space Grotesk', sans-serif !important; 
    }
    
    /* Cabeçalho Principal Adaptável */
    .header-rh { 
        font-size: 42px; 
        font-weight: 700; 
        color: #8DF768; /* Mantemos o verde ETUS que funciona em ambos */
        margin-bottom: 30px; 
        border-left: 10px solid #8DF768; 
        padding-left: 15px; 
    }
    
    /* Ajuste nos Cards de Métricas para visibilidade */
    [data-testid="stMetricValue"] {
        font-size: 28px !important;
    }
    
    /* Estilo dos cabeçalhos de vaga na aba Candidatos */
    .vaga-header { 
        background-color: rgba(141, 247, 104, 0.2); 
        color: inherit; /* Segue a cor do texto do tema atual */
        padding: 10px; 
        border-radius: 5px; 
        margin-top: 20px; 
        margin-bottom: 10px; 
        font-weight: bold;
        border-left: 5px solid #8DF768;
    }
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

inicializar_banco()

# --- 5. SIDEBAR ---
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

        # Métricas em colunas (O Streamlit cuidará das cores do texto automaticamente agora)
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
                fig_funil.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_funil, use_container_width=True)

        with col_right:
            st.subheader("❌ Motivos de Perda")
            if not df_c.empty and df_c['motivo_perda'].notnull().any():
                df_perda = df_c[df_c['motivo_perda'].notnull()]
                fig_perda = px.pie(df_perda, names='motivo_perda', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_perda.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_perda, use_container_width=True)
            else:
                st.info("Sem dados de perda registrados.")

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
        with st.expander(f"🏢 {row['nome_vaga'].upper()} | {row['status_vaga']}"):
            col1, col2 = st.columns([3, 1])
            with col1:
                with st.form(f"ed_v_{row['id']}"):
                    eg = st.text_input("Gestor", value=row['gestor'])
                    es = st.selectbox("Status", ["Aberta", "Pausada", "Finalizada"], index=["Aberta", "Pausada", "Finalizada"].index(row['status_vaga']))
                    if st.form_submit_button("SALVAR ALTERAÇÕES"):
                        data_f = datetime.now().date() if es == "Finalizada" else None
                        executar_sql("UPDATE vagas SET gestor=:g, status_vaga=:s, data_fechamento=:df WHERE id=:id", 
                                     {"g": eg, "s": es, "df": data_f, "id": row['id']})
                        st.rerun()
            with col2:
                if st.button("🗑️ EXCLUIR", key=f"del_v_{row['id']}", use_container_width=True):
                    executar_sql("DELETE FROM vagas WHERE id=:id", {"id": row['id']})
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

    if not df_vagas.empty:
        for _, vaga_row in df_vagas.iterrows():
            vaga_nome = vaga_row['nome_vaga']
            cands_da_vaga = df_c[df_c['vaga_vinculada'] == vaga_nome]
            
            if not cands_da_vaga.empty:
                st.markdown(f'<div class="vaga-header">🏢 VAGA: {vaga_nome.upper()}</div>', unsafe_allow_html=True)
                
                for i, cand in cands_da_vaga.iterrows():
                    with st.expander(f"👤 {cand['candidato']} ({cand['status_geral']})"):
                        etapas = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada"]
                        idx_etapa = etapas.index(cand['status_geral']) if cand['status_geral'] in etapas else 0
                        
                        c_edit, c_del = st.columns([3, 1])
                        with c_edit:
                            novo_st = st.selectbox("Mover Etapa", etapas, index=idx_etapa, key=f"st_{cand['id']}")
                            if st.button("ATUALIZAR STATUS", key=f"up_{cand['id']}"):
                                novo_h = f"➔ {datetime.now().strftime('%d/%m/%Y')}: {novo_st}\n" + (cand['historico'] or "")
                                executar_sql("UPDATE candidatos SET status_geral=:s, historico=:h WHERE id=:id", 
                                             {"s": novo_st, "h": novo_h, "id": cand['id']})
                                st.rerun()
                        with c_del:
                            st.write("---")
                            motivo = st.selectbox("Motivo da Saída", ["-", "Pretensão Salarial", "Falta de Fit Cultural", "Desistência", "Reprovado Técnico", "Outros"], key=f"mot_{cand['id']}")
                            if st.button("❌ REGISTRAR PERDA", key=f"perda_{cand['id']}"):
                                if motivo != "-":
                                    executar_sql("UPDATE candidatos SET motivo_perda=:m, status_geral='Perda' WHERE id=:id", {"m": motivo, "id": cand['id']})
                                    st.rerun()
                                else: st.warning("Selecione um motivo.")
    else:
        st.info("Cadastre uma vaga primeiro.")

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
            executar_sql(f"UPDATE candidatos SET {set_query} WHERE id=:id", {**res_on, "id": c_data['id']})
            st.rerun()
