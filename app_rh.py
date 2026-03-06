import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
import os

# --- 1. CONFIGURAÇÃO (Mantido) ---
st.set_page_config(page_title="RH ETUS - Gestão Pro", layout="wide", page_icon="🟢")

# --- 2. CONEXÃO (Mantido) ---
try:
    DB_URL = st.secrets["postgres"]["url"]
    engine = create_engine(DB_URL, connect_args={"sslmode": "require"})
except KeyError:
    st.error("Erro nos Secrets.")
    st.stop()

# --- 3. INICIALIZAÇÃO DE NOVAS COLUNAS (Essencial para as novas etapas) ---
def inicializar_banco():
    etapas = [
        "envio_proposta", "solic_documentos", "solic_fotos", "solic_contrato",
        "solic_acessos", "cad_rh_gestor", "cad_starbem", "cad_dasa", 
        "cad_avus", "agend_onboarding", "envio_gestor"
    ]
    with engine.connect() as conn:
        for etapa in etapas:
            # Tenta adicionar a coluna caso ela não exista (Postgres)
            try:
                conn.execute(text(f"ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS {etapa} BOOLEAN DEFAULT FALSE"))
                conn.commit()
            except Exception:
                pass

inicializar_banco()

# --- 4. CSS (Mantido e Adicionado Estilo de Checklist) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif !important; }
    .header-rh { font-size: 42px; font-weight: 700; color: #8DF768; margin-bottom: 30px; border-left: 10px solid #151514; padding-left: 15px; }
    .candidate-card { background-color: #1E1E1E; padding: 20px; border-radius: 12px; border: 1px solid #333; margin-bottom: 20px; }
    .onboarding-title { color: #8DF768; font-weight: bold; font-size: 24px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. FUNÇÕES DE BANCO ---
def carregar_vagas():
    return pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)

def carregar_candidatos_vaga(v_nome):
    query = text("SELECT * FROM candidatos WHERE vaga_vinculada = :v ORDER BY id DESC")
    return pd.read_sql(query, engine, params={"v": v_nome})

def carregar_aprovados():
    # Carrega candidatos que estão com status de finalizado ou aprovados
    return pd.read_sql("SELECT * FROM candidatos WHERE status_geral = 'Finalizada' OR aprovacao_final = 'Sim'", engine)

# --- 6. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    # ADICIONADA A NOVA OPÇÃO "🚀 ONBOARDING"
    menu = st.radio("NAVEGAÇÃO", ["📊 DASHBOARD", "🏢 GESTÃO DE VAGAS", "⚙️ FLUXO DE CANDIDATOS", "🚀 ONBOARDING"])

st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- [DASHBOARD, GESTÃO DE VAGAS, FLUXO - MANTIDOS CONFORME SEU CÓDIGO] ---
# (Pulei a repetição aqui para focar na novidade, mas mantenha-os no seu arquivo)

if menu == "📊 DASHBOARD":
    # ... (seu código original do dashboard)
    pass

elif menu == "🏢 GESTÃO DE VAGAS":
    # ... (seu código original das vagas)
    pass

elif menu == "⚙️ FLUXO DE CANDIDATOS":
    # ... (seu código original do fluxo)
    pass

# --- 7. NOVA ABA: ONBOARDING ---
elif menu == "🚀 ONBOARDING":
    st.subheader("Processo de Admissão e Onboarding")
    
    df_aprovados = carregar_aprovados()
    
    if df_aprovados.empty:
        st.info("Nenhum candidato aprovado no momento.")
    else:
        # Selecionar o candidato aprovado
        nomes_aprovados = df_aprovados["candidato"].tolist()
        selecionado = st.selectbox("Selecione o candidato para dar andamento:", nomes_aprovados)
        
        # Pegar dados do candidato selecionado
        cand_data = df_aprovados[df_aprovados["candidato"] == selecionado].iloc[0]
        
        st.markdown(f"<div class='onboarding-title'>Etapas para: {selecionado}</div>", unsafe_allow_html=True)
        st.caption(f"Vaga: {cand_data['vaga_vinculada']}")

        # Dicionário para mapear Etapa -> Coluna no Banco
        fluxo_onboarding = {
            "Envio de proposta": "envio_proposta",
            "Solicitação de documentos": "solic_documentos",
            "Solicitação de fotos e curiosidades": "solic_fotos",
            "Solicitação de contrato": "solic_contrato",
            "Solicitação de acessos e equipamentos": "solic_acessos",
            "Cadastro no RH Gestor": "cad_rh_gestor",
            "Cadastro no STARBEM": "cad_starbem",
            "Cadastro Dasa": "cad_dasa",
            "Cadastro AVUS": "cad_avus",
            "Agendamento de onboarding": "agend_onboarding",
            "Envio de início para gestor": "envio_gestor"
        }

        # Criar o checklist
        with st.container(border=True):
            col1, col2 = st.columns(2)
            
            novos_valores = {}
            
            # Divide as etapas em duas colunas visuais
            items = list(fluxo_onboarding.items())
            meio = len(items) // 2 + 1
            
            for i, (label, col_db) in enumerate(items):
                target_col = col1 if i < meio else col2
                # O checkbox já vem marcado se o valor no banco for True
                novos_valores[col_db] = target_col.checkbox(label, value=bool(cand_data[col_db]), key=f"chk_{cand_data['id']}_{col_db}")

        # Botão para salvar o progresso
        if st.button("💾 Salvar Progresso do Onboarding", use_container_width=True):
            with engine.connect() as conn:
                set_query = ", ".join([f"{k} = :{k}" for k in novos_valores.keys()])
                query = text(f"UPDATE candidatos SET {set_query} WHERE id = :id")
                params = novos_valores
                params["id"] = int(cand_data["id"])
                
                conn.execute(query, params)
                conn.commit()
            st.success(f"Progresso de {selecionado} atualizado com sucesso!")
            st.rerun()
