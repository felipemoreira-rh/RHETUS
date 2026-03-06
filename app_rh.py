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

# --- 3. INICIALIZAÇÃO DE BANCO (Garante colunas de Datas e Histórico) ---
def inicializar_banco():
    with engine.connect() as conn:
        # Colunas de Vagas
        v_cols = {"gestor": "TEXT", "data_abertura": "DATE", "data_fechamento": "DATE"}
        for col, tipo in v_cols.items():
            try: conn.execute(text(f"ALTER TABLE vagas ADD COLUMN IF NOT EXISTS {col} {tipo}")); conn.commit()
            except: pass
        
        # Colunas de Candidatos (Incluindo HISTÓRICO e DATAS DE ETAPA)
        c_cols = {
            "entrevista_cultura": "DATE",
            "historico": "TEXT",
            "envio_proposta": "BOOLEAN DEFAULT FALSE",
            "solic_documentos": "BOOLEAN DEFAULT FALSE",
            "solic_fotos": "BOOLEAN DEFAULT FALSE",
            "solic_contrato": "BOOLEAN DEFAULT FALSE",
            "solic_acessos": "BOOLEAN DEFAULT FALSE",
            "cad_rh_gestor": "BOOLEAN DEFAULT FALSE",
            "cad_starbem": "BOOLEAN DEFAULT FALSE",
            "cad_dasa": "BOOLEAN DEFAULT FALSE",
            "cad_avus": "BOOLEAN DEFAULT FALSE",
            "agend_onboarding": "BOOLEAN DEFAULT FALSE",
            "envio_gestor": "BOOLEAN DEFAULT FALSE"
        }
        for col, tipo in c_cols.items():
            try: conn.execute(text(f"ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS {col} {tipo}")); conn.commit()
            except: pass

inicializar_banco()

# --- 4. CSS (ÍCONE DE CARREGAMENTO E MENU LIMPO) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    html, body, [class*="css"], [data-testid="stSidebar"] { font-family: 'Space Grotesk', sans-serif !important; }
    
    /* Remove a bolinha do menu lateral */
    [data-testid="stSidebar"] [data-testid="stWidgetSelectionColumn"] { display: none !important; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label { padding: 8px 0px !important; margin-left: -20px !important; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] p { color: #777777 !important; font-size: 18px !important; transition: 0.3s; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] input:checked + div p { color: #8DF768 !important; font-weight: 700 !important; font-size: 20px !important; }

    /* ANIMAÇÃO BOLA DE FUTEBOL AMERICANO (Carregamento) */
    [data-testid="stStatusWidget"] { visibility: hidden; }
    [data-testid="stStatusWidget"]::before {
        content: '🏈'; visibility: visible; position: fixed; top: 25px; right: 35px; font-size: 32px; z-index: 999999;
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
def carregar_vagas(): return pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)
def carregar_candidatos_vaga(v_nome):
    query = text("SELECT * FROM candidatos WHERE vaga_vinculada = :v ORDER BY candidato ASC")
    return pd.read_sql(query, engine, params={"v": v_nome})
def carregar_aprovados(): return pd.read_sql("SELECT * FROM candidatos WHERE status_geral = 'Finalizada' OR aprovacao_final = 'Sim' ORDER BY candidato", engine)

# --- 6. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])

st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- 7. INDICADORES (DASHBOARD DE PERFORMANCE) ---
if menu == "📊 INDICADORES":
    df_v = carregar_vagas()
    df_c = pd.read_sql("SELECT * FROM candidatos", engine)
    
    if not df_v.empty and not df_c.empty:
        hoje = pd.Timestamp(datetime.now().date())
        df_v['data_abertura'] = pd.to_datetime(df_v['data_abertura'])
        
        st.markdown("### 📈 Performance do Recrutamento")
        c1, c2, c3, c4 = st.columns(4)
        v_ativas = df_v[df_v['status_vaga'] == 'Aberta']
        avg_aging = int(v_ativas['data_abertura'].apply(lambda x: (hoje - x).days).mean()) if not v_ativas.empty else 0
        
        c1.metric("📌 VAGAS ABERTAS", len(v_ativas))
        c2.metric("⏱️ AGING MÉDIO", f"{avg_aging} dias")
        c3.metric("👥 CANDIDATOS ATIVOS", len(df_c[df_c['status_geral'] != 'Finalizada']))
        c4.metric("✅ CONTRATAÇÕES", len(df_c[df_c['status_geral'] == 'Finalizada']))

        st.divider()
        st.subheader("⏳ Lead Time por Etapa (Acumulado)")
        df_c['entrevista_rh'] = pd.to_datetime(df_c['entrevista_rh'])
        df_c['entrevista_gestor'] = pd.to_datetime(df_c['entrevista_gestor'])
        df_c['entrevista_cultura'] = pd.to_datetime(df_c['entrevista_cultura'])
        
        df_dash = df_c.merge(df_v[['nome_vaga', 'data_abertura']], left_on='vaga_vinculada', right_on='nome_vaga')
        df_dash['Abertura -> RH'] = (df_dash['entrevista_rh'] - df_dash['data_abertura']).dt.days.clip(lower=0)
        df_dash['RH -> Gestor'] = (df_dash['entrevista_gestor'] - df_dash['entrevista_rh']).dt.days.clip(lower=0)
        df_dash['Gestor -> Cultura'] = (df_dash['entrevista_cultura'] - df_dash['entrevista_gestor']).dt.days.clip(lower=0)
        
        fig_lead = px.bar(df_dash, y="candidato", x=['Abertura -> RH', 'RH -> Gestor', 'Gestor -> Cultura'],
                          orientation='h', barmode="stack", color_discrete_sequence=["#8DF768", "#4CAF50", "#1B5E20"])
        st.plotly_chart(fig_lead, use_container_width=True)
    else:
        st.info("💡 Sem dados suficientes para o Dashboard.")

# --- 8. VAGAS ---
elif menu == "🏢 VAGAS":
    st.subheader("Gestão de Vagas")
    with st.expander("➕ CADASTRAR NOVA VAGA"):
        with st.form("n_vaga"):
            n_v = st.text_input("Nome da Vaga"); a_v = st.selectbox("Departamento", ["Comercial", "Operações", "Tecnologia", "RH", "Marketing"])
            g_v = st.text_input("Gestor"); d_ab = st.date_input("Data Abertura", value=datetime.now())
            if st.form_submit_button("CRIAR VAGA"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO vagas (nome_vaga, area, status_vaga, gestor, data_abertura) VALUES (:n, :a, 'Aberta', :g, :d)"), {"n": n_v, "a": a_v, "g": g_v, "d": d_ab}); conn.commit()
                st.rerun()

    df_v = carregar_vagas()
    for _, row in df_v.iterrows():
        with st.container(border=True):
            st.write(f"**{row['nome_vaga']}** | {row['area']} | Gestor: {row['gestor']} | Status: {row['status_vaga']}")

# --- 9. CANDIDATOS (INCLUIR, GESTÃO E EXCLUIR) ---
elif menu == "⚙️ CANDIDATOS":
    df_vagas = carregar_vagas()
    
    # --- PARTE A: FORMULÁRIO PARA INCLUIR NOVO ---
    st.subheader("➕ Adicionar Novo Candidato")
    if not df_vagas.empty:
        with st.container(border=True):
            with st.form("form_novo_cand", clear_on_submit=True):
                col_n, col_v = st.columns(2)
                novo_nome = col_n.text_input("Nome do Candidato")
                vaga_alvo = col_v.selectbox("Vaga Vinculada", df_vagas["nome_vaga"].tolist())
                
                if st.form_submit_button("🚀 CADASTRAR NO BANCO"):
                    if novo_nome:
                        with engine.connect() as conn:
                            # Log inicial de cadastro
                            log_ini = f"➔ {datetime.now().strftime('%d/%m/%Y %H:%M')}: Cadastro realizado (Triagem)\n"
                            conn.execute(text("""
                                INSERT INTO candidatos (candidato, vaga_vinculada, status_geral, historico) 
                                VALUES (:n, :v, 'Triagem', :h)
                            """), {"n": novo_nome, "v": vaga_alvo, "h": log_ini})
                            conn.commit()
                        st.success(f"Candidato {novo_nome} adicionado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Por favor, preencha o nome do candidato.")
    else:
        st.warning("⚠️ Você precisa cadastrar uma Vaga primeiro na aba 'Vagas'.")

    st.divider()

    # --- PARTE B: GESTÃO DOS EXISTENTES ---
    if not df_vagas.empty:
        v_sel = st.selectbox("Filtrar candidatos por Vaga:", df_vagas["nome_vaga"].tolist())
        df_c = carregar_candidatos_vaga(v_sel)
        
        if df_c.empty: 
            st.info("Nenhum candidato cadastrado para esta vaga.")
        else:
            opcoes_status = ["Vaga aberta", "Triagem", "Entrevista RH", "Teste Técnico", "Entrevista gestor", "Entrevista Cultura", "Solicitação de documentos", "Solicitação de contratos", "Finalizada"]
            
            for _, cand in df_c.iterrows():
                # Expander para manter a tela limpa
                with st.expander(f"👤 {cand['candidato'].upper()}  |  Fase: {cand['status_geral']}"):
                    col_st, col_dt, col_del = st.columns([2, 3, 1])
                    
                    with col_st:
                        st.markdown("**Mover Etapa**")
                        novo_st = st.selectbox("Status", opcoes_status, 
                                             index=opcoes_status.index(cand['status_geral']) if cand['status_geral'] in opcoes_status else 1, 
                                             key=f"st_{cand['id']}")
                    
                    with col_dt:
                        st.markdown("**Agendamentos**")
                        c_rh, c_gs, c_cu = st.columns(3)
                        def input_dt(col, label, val, k):
                            if col.checkbox(label, value=pd.notnull(val), key=f"ck_{k}_{cand['id']}"):
                                return col.date_input("Data", value=val if pd.notnull(val) else datetime.now(), key=f"dt_{k}_{cand['id']}", label_visibility="collapsed")
                            return None
                        
                        res_rh = input_dt(c_rh, "RH", cand.get('entrevista_rh'), "rh")
                        res_gs = input_dt(c_gs, "Gestor", cand.get('entrevista_gestor'), "gs")
                        res_cu = input_dt(c_cu, "Cultura", cand.get('entrevista_cultura'), "cu")

                    # BOTÕES DE AÇÃO (SALVAR E EXCLUIR)
                    st.write("---")
                    c_save, c_empty, c_delete = st.columns([2, 2, 1])
                    
                    if c_save.button(f"💾 SALVAR ALTERAÇÕES", key=f"sv_{cand['id']}", use_container_width=True):
                        hist = cand.get('historico') if cand.get('historico') else ""
                        if novo_st != cand['status_geral']:
                            log = f"➔ {datetime.now().strftime('%d/%m/%Y %H:%M')}: De '{cand['status_geral']}' para '{novo_st}'\n"
                            hist = log + str(hist)

                        with engine.connect() as conn:
                            conn.execute(text("""
                                UPDATE candidatos 
                                SET status_geral=:s, entrevista_rh=:rh, entrevista_gestor=:gs, entrevista_cultura=:cu, historico=:h 
                                WHERE id=:id
                            """), {"s": novo_st, "rh": res_rh, "gs": res_gs, "cu": res_cu, "h": str(hist), "id": cand['id']})
                            conn.commit()
                        st.rerun()

                    if c_delete.button(f"🗑️ EXCLUIR", key=f"del_{cand['id']}", type="secondary", use_container_width=True):
                        with engine.connect() as conn:
                            conn.execute(text("DELETE FROM candidatos WHERE id = :id"), {"id": cand['id']})
                            conn.commit()
                        st.warning(f"{cand['candidato']} removido.")
                        st.rerun()

                    if cand.get('historico'):
                        st.caption("📜 Histórico:")
                        st.text(cand['historico'])

# --- 10. ONBOARDING ---
elif menu == "🚀 ONBOARDING":
    df_ap = carregar_aprovados()
    if not df_ap.empty:
        sel = st.selectbox("Colaborador:", df_ap["candidato"].tolist())
        c_data = df_ap[df_ap["candidato"] == sel].iloc[0]
        st.markdown(f"### Checklist: {sel}")
        checks = {"Envio Proposta": "envio_proposta", "Documentos": "solic_documentos", "Contrato": "solic_contrato", "Acessos": "solic_acessos"}
        novos_on = {}
        c_on1, c_on2 = st.columns(2)
        for i, (l, d) in enumerate(checks.items()):
            target = c_on1 if i < 2 else c_on2
            novos_on[d] = target.checkbox(l, value=bool(c_data.get(d, False)), key=f"o_{c_data['id']}_{d}")
        
        if st.button("SALVAR ONBOARDING"):
            with engine.connect() as conn:
                sets = ", ".join([f"{k}=:{k}" for k in novos_on.keys()])
                conn.execute(text(f"UPDATE candidatos SET {sets} WHERE id=:id"), {**novos_on, "id": int(c_data["id"])}); conn.commit()
            st.success("Onboarding atualizado!")

