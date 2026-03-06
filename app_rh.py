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
    st.error("Erro nos Secrets.")
    st.stop()

# --- 3. INICIALIZAÇÃO DE COLUNAS (Incluindo a de Cultura) ---
def inicializar_banco():
    # Colunas de Onboarding + Coluna de Data de Cultura
    colunas = [
        "envio_proposta", "solic_documentos", "solic_fotos", "solic_contrato",
        "solic_acessos", "cad_rh_gestor", "cad_starbem", "cad_dasa", 
        "cad_avus", "agend_onboarding", "envio_gestor"
    ]
    with engine.connect() as conn:
        # Garante a coluna de data para a entrevista de cultura
        try:
            conn.execute(text("ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS entrevista_cultura DATE"))
            conn.commit()
        except: pass

        for col in colunas:
            try:
                conn.execute(text(f"ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS {col} BOOLEAN DEFAULT FALSE"))
                conn.commit()
            except Exception: pass

inicializar_banco()

# --- 4. CSS MODERNIZAÇÃO (Sidebar e UI) ---
# --- CSS OPÇÃO 2 (Substitua na seção 4) ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1A1A1A 0%, #0A0A0A 100%) !important;
    }

    /* Estilo de "Pill" para as opções */
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
        gap: 10px;
    }

    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 10px 15px !important;
        transition: all 0.4s ease;
    }

    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
        background-color: rgba(141, 247, 104, 0.1);
        border-color: #8DF768;
    }

    /* Quando selecionado */
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] input:checked + div {
        background-color: rgba(141, 247, 104, 0.2) !important;
        border: 1px solid #8DF768 !important;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 5. FUNÇÕES DE BANCO ---
def carregar_vagas():
    return pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)

def carregar_candidatos_vaga(v_nome):
    query = text("SELECT * FROM candidatos WHERE vaga_vinculada = :v ORDER BY id DESC")
    return pd.read_sql(query, engine, params={"v": v_nome})

def carregar_aprovados():
    return pd.read_sql("SELECT * FROM candidatos WHERE status_geral = 'Finalizada' OR aprovacao_final = 'Sim' ORDER BY candidato", engine)

# --- 6. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    menu = st.radio("NAVEGAÇÃO", ["📊 DASHBOARD", "🏢 GESTÃO DE VAGAS", "⚙️ FLUXO DE CANDIDATOS", "🚀 ONBOARDING"])

st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- 7. DASHBOARD (Mantido) ---
if menu == "📊 DASHBOARD":
    df_c = pd.read_sql("SELECT * FROM candidatos", engine)
    if not df_c.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 CANDIDATOS ATIVOS", len(df_c))
        c2.metric("✅ CONTRATAÇÕES", len(df_c[df_c["status_geral"] == "Finalizada"]))
        c3.metric("🏢 VAGAS NO SISTEMA", len(pd.read_sql("SELECT * FROM vagas", engine)))
        st.divider()
        fig = px.pie(df_c, names="status_geral", hole=.4, color_discrete_sequence=['#8DF768', '#4A4A4A', '#222222'])
        st.plotly_chart(fig, use_container_width=True)

# --- 8. VAGAS (Mantido) ---
elif menu == "🏢 GESTÃO DE VAGAS":
    st.subheader("Painel de Vagas")
    with st.expander("➕ CRIAR NOVA VAGA"):
        with st.form("f_vaga"):
            n_v = st.text_input("Nome da Vaga")
            a_v = st.selectbox("Departamento", ["Comercial", "Operações", "Tecnologia", "RH", "Marketing"])
            if st.form_submit_button("CONFIRMAR"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO vagas (nome_vaga, area, status_vaga) VALUES (:n, :a, 'Aberta')"), {"n": n_v, "a": a_v})
                    conn.commit()
                st.rerun()

# --- 9. FLUXO DE CANDIDATOS (ORDEM: RH -> GESTOR -> CULTURA) ---
elif menu == "⚙️ FLUXO DE CANDIDATOS":
    df_vagas = carregar_vagas()
    if df_vagas.empty:
        st.warning("Cadastre uma vaga primeiro.")
    else:
        v_sel = st.selectbox("Selecione a Vaga:", df_vagas["nome_vaga"].tolist())
        st.divider()
        
        df_c = carregar_candidatos_vaga(v_sel)
        if df_c.empty:
            st.info("Nenhum candidato nesta vaga.")
        else:
            # STATUS REORDENADOS: Gestor agora vem antes de Cultura
            opcoes_status = [
                "Vaga aberta", "Triagem", "Entrevista RH", "Teste Técnico", 
                "Entrevista gestor", "Entrevista Cultura", # <-- Ordem alterada aqui
                "Solicitação de documentos", "Solicitação de contratos", "Finalizada"
            ]
            
            for idx, cand in df_c.iterrows():
                with st.container():
                    st.markdown(f'<div class="candidate-card"><div class="candidate-name">{cand["candidato"]}</div><div class="candidate-status">{cand["status_geral"]}</div></div>', unsafe_allow_html=True)
                    
                    # Colunas visuais reordenadas: c_rh, c_gest, c_cult
                    c_status, c_rh, c_gest, c_cult, c_btn = st.columns([1.8, 1.2, 1.2, 1.2, 0.5])
                    
                    # 1. Seletor de Status
                    novo_status = c_status.selectbox("Status", opcoes_status, 
                                                   index=opcoes_status.index(cand['status_geral']) if cand['status_geral'] in opcoes_status else 0, 
                                                   key=f"st_{cand['id']}")
                    
                    # Função para campo de data opcional (NULL se desmarcado)
                    def campo_data_opcional(coluna_st, label, valor_banco, chave):
                        tem_data = coluna_st.checkbox(f"Agendar {label}", value=pd.notnull(valor_banco), key=f"ch_{chave}")
                        if tem_data:
                            data_padrao = valor_banco if pd.notnull(valor_banco) else datetime.now()
                            return coluna_st.date_input(f"Data {label}", value=data_padrao, key=f"dt_{chave}")
                        return None

                    # 2. Renderização das datas na nova ordem visual
                    res_rh = campo_data_opcional(c_rh, "RH", cand['entrevista_rh'], f"rh_{cand['id']}")
                    res_gest = campo_data_opcional(c_gest, "Gestor", cand['entrevista_gestor'], f"gs_{cand['id']}")
                    res_cult = campo_data_opcional(c_cult, "Cultura", cand.get('entrevista_cultura'), f"cu_{cand['id']}")
                    
                    # 3. Botão Salvar
                    if c_btn.button("💾", key=f"sv_{cand['id']}", help="Salvar alterações"):
                        with engine.connect() as conn:
                            conn.execute(text("""
                                UPDATE candidatos SET 
                                status_geral = :s, 
                                entrevista_rh = :rh, 
                                entrevista_gestor = :gs,
                                entrevista_cultura = :cult
                                WHERE id = :id
                            """), {
                                "s": novo_status, 
                                "rh": res_rh, 
                                "gs": res_gest, 
                                "cult": res_cult, 
                                "id": cand['id']
                            })
                            conn.commit()
                        st.toast("Dados salvos!")
                        st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)

# --- 10. ONBOARDING (Mantido) ---
elif menu == "🚀 ONBOARDING":
    st.subheader("Processo de Admissão")
    df_aprovados = carregar_aprovados()
    if df_aprovados.empty:
        st.info("Nenhum candidato aprovado (Status 'Finalizada').")
    else:
        selecionado = st.selectbox("Candidato:", df_aprovados["candidato"].tolist())
        cand_data = df_aprovados[df_aprovados["candidato"] == selecionado].iloc[0]
        
        fluxo = ["envio_proposta", "solic_documentos", "solic_fotos", "solic_contrato", "solic_acessos", "cad_rh_gestor", "cad_starbem", "cad_dasa", "cad_avus", "agend_onboarding", "envio_gestor"]
        
        novos_valores = {}
        for etapa in fluxo:
            valor_atual = bool(cand_data[etapa]) if etapa in cand_data else False
            novos_valores[etapa] = st.checkbox(etapa.replace("_", " ").title(), value=valor_atual, key=f"onb_{cand_data['id']}_{etapa}")

        if st.button("💾 Salvar Onboarding"):
            with engine.connect() as conn:
                set_clause = ", ".join([f"{k} = :{k}" for k in novos_valores.keys()])
                conn.execute(text(f"UPDATE candidatos SET {set_clause} WHERE id = :id"), {**novos_valores, "id": int(cand_data["id"])})
                conn.commit()
            st.success("Salvo!")





