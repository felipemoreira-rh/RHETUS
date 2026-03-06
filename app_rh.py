import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
import os
from datetime import datetime

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="RH ETUS - Gestão Pro", layout="wide", page_icon="🟢")

# --- 2. CONEXÃO ---
try:
    DB_URL = st.secrets["postgres"]["url"]
    engine = create_engine(DB_URL, connect_args={"sslmode": "require"})
except KeyError:
    st.error("Erro nos Secrets do banco de dados.")
    st.stop()

# --- 3. INICIALIZAÇÃO DE BANCO (Garante que as colunas existam) ---
def inicializar_banco():
    with engine.connect() as conn:
        # Colunas para VAGAS
        vagas_cols = {"gestor": "TEXT", "data_abertura": "DATE", "data_fechamento": "DATE"}
        for col, tipo in vagas_cols.items():
            try:
                conn.execute(text(f"ALTER TABLE vagas ADD COLUMN IF NOT EXISTS {col} {tipo}"))
                conn.commit()
            except: pass
        
        # Colunas para CANDIDATOS
        try:
            conn.execute(text("ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS entrevista_cultura DATE"))
            conn.commit()
        except: pass

        onboarding_cols = ["envio_proposta", "solic_documentos", "solic_fotos", "solic_contrato", "solic_acessos", "cad_rh_gestor", "cad_starbem", "cad_dasa", "cad_avus", "agend_onboarding", "envio_gestor"]
        for col in onboarding_cols:
            try:
                conn.execute(text(f"ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS {col} BOOLEAN DEFAULT FALSE"))
                conn.commit()
            except: pass

inicializar_banco()

# --- 4. CSS CUSTOMIZADO (Limpeza do Menu e Ícone de Carregamento) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    html, body, [class*="css"], [data-testid="stSidebar"] { font-family: 'Space Grotesk', sans-serif !important; }
    
    /* Remove a bolinha vermelha/seleção do menu lateral */
    [data-testid="stSidebar"] [data-testid="stWidgetSelectionColumn"] { display: none !important; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label { padding: 8px 0px !important; margin-left: -20px !important; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] p { color: #777777 !important; font-size: 18px !important; transition: 0.3s; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] input:checked + div p { color: #8DF768 !important; font-weight: 700 !important; font-size: 20px !important; }

    /* ÍCONE DE CARREGAMENTO: BOLA DE FUTEBOL AMERICANO */
    [data-testid="stStatusWidget"] { visibility: hidden; }
    [data-testid="stStatusWidget"]::before {
        content: '🏈'; 
        visibility: visible;
        position: fixed;
        top: 25px;
        right: 35px;
        font-size: 32px;
        z-index: 999999;
        animation: footballSpiral 1.2s ease-in-out infinite;
    }
    @keyframes footballSpiral {
        0% { transform: translateY(0px) rotate(0deg); filter: drop-shadow(0 0 0px #8DF768); }
        50% { transform: translateY(-8px) rotate(180deg) scale(1.1); filter: drop-shadow(0 0 12px #8DF768); }
        100% { transform: translateY(0px) rotate(360deg); }
    }

    .header-rh { font-size: 42px; font-weight: 700; color: #8DF768; margin-bottom: 30px; border-left: 10px solid #151514; padding-left: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. FUNÇÕES DE DADOS ---
def carregar_vagas():
    return pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)

def carregar_candidatos_vaga(v_nome):
    query = text("SELECT * FROM candidatos WHERE vaga_vinculada = :v ORDER BY candidato ASC")
    return pd.read_sql(query, engine, params={"v": v_nome})

def carregar_aprovados():
    return pd.read_sql("SELECT * FROM candidatos WHERE status_geral = 'Finalizada' OR aprovacao_final = 'Sim' ORDER BY candidato", engine)

# --- 6. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])

st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- 7. INDICADORES (AGING DE VAGAS) ---
# --- 7. INDICADORES (AGING E TEMPO POR ETAPA) ---
if menu == "📊 INDICADORES":
    df_v = carregar_vagas()
    df_c = pd.read_sql("SELECT * FROM candidatos", engine)
    
    if not df_v.empty:
        hoje = pd.Timestamp(datetime.now().date())
        df_v['data_abertura'] = pd.to_datetime(df_v['data_abertura'])
        
        # Cálculo de Aging Geral da Vaga
        df_v['dias_aberta'] = df_v.apply(
            lambda x: (hoje - x['data_abertura']).days if pd.isnull(x['data_fechamento']) 
            else (pd.to_datetime(x['data_fechamento']) - x['data_abertura']).days, axis=1
        )

        # MÉTRICAS NO TOPO
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📌 VAGAS ATIVAS", len(df_v[df_v['status_vaga'] == 'Aberta']))
        c2.metric("⏱️ MÉDIA DE FECHAMENTO", f"{int(df_v['dias_aberta'].mean())} d")
        c3.metric("👥 TOTAL CANDIDATOS", len(df_c))
        c4.metric("✅ CONTRATAÇÕES", len(df_c[df_c["status_geral"] == "Finalizada"]))

        st.divider()

        # --- NOVO: CÁLCULO DE TEMPO POR ETAPA ---
        st.subheader("⏳ Tempo de Permanência por Etapa (Dias)")
        
        if not df_c.empty:
            # Converter colunas para datetime
            for col in ['entrevista_rh', 'entrevista_gestor', 'entrevista_cultura']:
                df_c[col] = pd.to_datetime(df_c[col])
            
            # Cruzar com a data de abertura da vaga para saber o início
            df_analise = df_c.merge(df_v[['nome_vaga', 'data_abertura']], left_on='vaga_vinculada', right_on='nome_vaga')

            # Calcular intervalos (Ex: dias da abertura até o RH, do RH até o Gestor...)
            df_analise['Até Triagem/RH'] = (df_analise['entrevista_rh'] - df_analise['data_abertura']).dt.days
            df_analise['RH -> Gestor'] = (df_analise['entrevista_gestor'] - df_analise['entrevista_rh']).dt.days
            df_analise['Gestor -> Cultura'] = (df_analise['entrevista_cultura'] - df_analise['entrevista_gestor']).dt.days
            
            # Limpar valores negativos ou nulos para o gráfico
            cols_tempo = ['Até Triagem/RH', 'RH -> Gestor', 'Gestor -> Cultura']
            for c in cols_tempo:
                df_analise[c] = df_analise[c].apply(lambda x: x if x > 0 else 0)

            # Gráfico de Barras Empilhadas por Candidato
            fig_etapas = px.bar(
                df_analise, 
                x="candidato", 
                y=cols_tempo,
                title="Distribuição de Dias por Candidato",
                labels={"value": "Dias", "variable": "Etapa"},
                barmode="stack",
                color_discrete_sequence=["#8DF768", "#00CC96", "#636EFA"] # Tons de verde/azul
            )
            st.plotly_chart(fig_etapas, use_container_width=True)
            
            # Média Geral por Etapa
            st.write("**Média de dias em cada fase (Geral):**")
            m_col1, m_col2, m_col3 = st.columns(3)
            m_col1.info(f"Triagem: {df_analise['Até Triagem/RH'].mean():.1f} dias")
            m_col2.info(f"Com Gestor: {df_analise['RH -> Gestor'].mean():.1f} dias")
            m_col3.info(f"Cultura/Final: {df_analise['Gestor -> Cultura'].mean():.1f} dias")
        else:
            st.warning("Aguardando dados de candidatos para calcular as etapas.")

        st.divider()
        st.subheader("📋 Aging de Vagas Abertas")
        fig_aging = px.bar(df_v[df_v['status_vaga'] == 'Aberta'], x='dias_aberta', y='nome_vaga', orientation='h', 
                           color='dias_aberta', color_continuous_scale='Greens', text='dias_aberta')
        st.plotly_chart(fig_aging, use_container_width=True)

# --- 8. VAGAS ---
elif menu == "🏢 VAGAS":
    st.subheader("Gestão de Vagas")
    with st.expander("➕ CADASTRAR NOVA VAGA"):
        with st.form("nova_vaga"):
            n_v = st.text_input("Nome da Vaga")
            a_v = st.selectbox("Departamento", ["Comercial", "Operações", "Tecnologia", "RH", "Marketing"])
            g_v = st.text_input("Gestor")
            d_ab = st.date_input("Data Abertura", value=datetime.now())
            if st.form_submit_button("CRIAR"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO vagas (nome_vaga, area, status_vaga, gestor, data_abertura) VALUES (:n, :a, 'Aberta', :g, :d)"), 
                                 {"n": n_v, "a": a_v, "g": g_v, "d": d_ab})
                    conn.commit()
                st.rerun()

    df_v = carregar_vagas()
    for _, row in df_v.iterrows():
        with st.container(border=True):
            col_v1, col_v2 = st.columns([4, 1])
            col_v1.write(f"**{row['nome_vaga']}** | {row['area']} | Status: {row['status_vaga']}")
            if col_v2.button("EDITAR", key=f"ed_{row['nome_vaga']}"):
                st.info("Função de edição rápida em desenvolvimento.")

# --- 9. CANDIDATOS (VERSÃO LIMPA - CLIQUE PARA ABRIR) ---
elif menu == "⚙️ CANDIDATOS":
    df_vagas = carregar_vagas()
    if not df_vagas.empty:
        v_sel = st.selectbox("Selecione a Vaga para listar os candidatos:", df_vagas["nome_vaga"].tolist())
        st.divider()
        
        df_c = carregar_candidatos_vaga(v_sel)
        
        if df_c.empty:
            st.info("Nenhum candidato para esta vaga.")
        else:
            opcoes_status = ["Vaga aberta", "Triagem", "Entrevista RH", "Teste Técnico", "Entrevista gestor", "Entrevista Cultura", "Solicitação de documentos", "Solicitação de contratos", "Finalizada"]
            
            for _, cand in df_c.iterrows():
                # --- O EXPANDER É O QUE DEIXA A TELA LIMPA ---
                with st.expander(f"👤 {cand['candidato'].upper()}  |  Etapa: {cand['status_geral']}"):
                    st.write("")
                    c_status, c_agenda = st.columns([1, 2])
                    
                    with c_status:
                        st.markdown("**Alterar Etapa**")
                        novo_status = st.selectbox("Status", opcoes_status, 
                                                   index=opcoes_status.index(cand['status_geral']) if cand['status_geral'] in opcoes_status else 0, 
                                                   key=f"st_{cand['id']}", label_visibility="collapsed")
                    
                    with c_agenda:
                        st.markdown("**Agendamentos**")
                        ca1, ca2, ca3 = st.columns(3)
                        
                        def input_data(col, label, data_db, k):
                            check = col.checkbox(label, value=pd.notnull(data_db), key=f"ck_{k}_{cand['id']}")
                            if check:
                                return col.date_input("Data", value=data_db if pd.notnull(data_db) else datetime.now(), 
                                                       key=f"dt_{k}_{cand['id']}", label_visibility="collapsed")
                            return None

                        res_rh = input_data(ca1, "RH", cand['entrevista_rh'], "rh")
                        res_gs = input_data(ca2, "Gestor", cand['entrevista_gestor'], "gs")
                        res_cu = input_data(ca3, "Cultura", cand.get('entrevista_cultura'), "cu")
                    
                    st.write("")
                    if st.button(f"💾 SALVAR DADOS DE {cand['candidato'].split()[0].upper()}", key=f"sv_{cand['id']}", use_container_width=True):
                        with engine.connect() as conn:
                            conn.execute(text("UPDATE candidatos SET status_geral=:s, entrevista_rh=:rh, entrevista_gestor=:gs, entrevista_cultura=:cu WHERE id=:id"),
                                         {"s": novo_status, "rh": res_rh, "gs": res_gs, "cu": res_cu, "id": cand['id']})
                            conn.commit()
                        st.success("Atualizado!")
                        st.rerun()

# --- 10. ONBOARDING ---
elif menu == "🚀 ONBOARDING":
    df_aprovados = carregar_aprovados()
    if not df_aprovados.empty:
        selecionado = st.selectbox("Selecione o Novo Colaborador:", df_aprovados["candidato"].tolist())
        cand_data = df_aprovados[df_aprovados["candidato"] == selecionado].iloc[0]
        
        etapas = {"Envio Proposta": "envio_proposta", "Documentos": "solic_documentos", "Fotos": "solic_fotos", 
                  "Contrato": "solic_contrato", "Acessos": "solic_acessos", "RH Gestor": "cad_rh_gestor", 
                  "STARBEM": "cad_starbem", "Dasa": "cad_dasa", "AVUS": "cad_avus", 
                  "Agend. Onboarding": "agend_onboarding", "Envio Gestor": "envio_gestor"}
        
        novos = {}
        st.markdown(f"### Checklist: {selecionado}")
        c_on1, c_on2 = st.columns(2)
        for i, (label, col_db) in enumerate(etapas.items()):
            target = c_on1 if i < 6 else c_on2
            novos[col_db] = target.checkbox(label, value=bool(cand_data.get(col_db, False)), key=f"on_{cand_data['id']}_{col_db}")
            
        if st.button("💾 SALVAR ONBOARDING", use_container_width=True):
            with engine.connect() as conn:
                sets = ", ".join([f"{k}=:{k}" for k in novos.keys()])
                conn.execute(text(f"UPDATE candidatos SET {sets} WHERE id=:id"), {**novos, "id": int(cand_data["id"])})
                conn.commit()
            st.success("Progresso salvo!")
    else:
        st.info("Nenhum candidato aprovado para onboarding.")

