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
    st.error("Erro nos Secrets: Verifique se a URL do Postgres está configurada corretamente.")
    st.stop()

# --- 3. INICIALIZAÇÃO AUTOMÁTICA DE COLUNAS ---
def inicializar_banco():
    # Lista de todas as colunas necessárias para o Onboarding
    colunas_onboarding = [
        "envio_proposta", "solic_documentos", "solic_fotos", "solic_contrato",
        "solic_acessos", "cad_rh_gestor", "cad_starbem", "cad_dasa", 
        "cad_avus", "agend_onboarding", "envio_gestor"
    ]
    with engine.connect() as conn:
        for col in colunas_onboarding:
            try:
                # Tenta adicionar a coluna caso não exista (Sintaxe PostgreSQL)
                conn.execute(text(f"ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS {col} BOOLEAN DEFAULT FALSE"))
                conn.commit()
            except Exception:
                pass # Ignora se já existir ou se houver erro de permissão momentâneo

# Rodar inicialização
inicializar_banco()

# --- 4. CSS MODERNIZAÇÃO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif !important; }
    .header-rh { font-size: 42px; font-weight: 700; color: #8DF768; margin-bottom: 30px; border-left: 10px solid #151514; padding-left: 15px; }
    .candidate-card { background-color: #1E1E1E; padding: 20px; border-radius: 12px; border: 1px solid #333; margin-bottom: 20px; transition: transform 0.2s; }
    .candidate-card:hover { border-color: #8DF768; transform: translateY(-2px); }
    .candidate-name { font-size: 20px; font-weight: 700; color: #FFFFFF; margin-bottom: 5px; }
    .candidate-status { font-size: 14px; color: #8DF768; text-transform: uppercase; letter-spacing: 1px; }
    .onboarding-title { color: #8DF768; font-weight: bold; font-size: 24px; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. FUNÇÕES DE BANCO ---
def carregar_vagas():
    return pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)

def carregar_candidatos_vaga(v_nome):
    query = text("SELECT * FROM candidatos WHERE vaga_vinculada = :v ORDER BY id DESC")
    return pd.read_sql(query, engine, params={"v": v_nome})

def carregar_aprovados():
    # Traz candidatos com status 'Finalizada' ou que foram marcados com aprovação final 'Sim'
    return pd.read_sql("SELECT * FROM candidatos WHERE status_geral = 'Finalizada' OR aprovacao_final = 'Sim' ORDER BY candidato", engine)

# --- 6. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    menu = st.radio("NAVEGAÇÃO", ["📊 DASHBOARD", "🏢 GESTÃO DE VAGAS", "⚙️ FLUXO DE CANDIDATOS", "🚀 ONBOARDING"])

st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- 7. DASHBOARD ---
if menu == "📊 DASHBOARD":
    df_c = pd.read_sql("SELECT * FROM candidatos", engine)
    if not df_c.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 CANDIDATOS ATIVOS", len(df_c))
        # Verifica se a coluna aprovacao_final existe antes de filtrar
        if "aprovacao_final" in df_c.columns:
            c2.metric("✅ CONTRATAÇÕES", len(df_c[df_c["aprovacao_final"] == "Sim"]))
        else:
            c2.metric("✅ CONTRATAÇÕES", "0")
        
        c3.metric("🏢 VAGAS NO SISTEMA", len(pd.read_sql("SELECT * FROM vagas", engine)))
        st.divider()
        fig = px.pie(df_c, names="status_geral", hole=.4, color_discrete_sequence=['#8DF768', '#4A4A4A', '#222222'])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Ainda não há dados para exibir no Dashboard.")

# --- 8. VAGAS ---
elif menu == "🏢 GESTÃO DE VAGAS":
    st.subheader("Painel de Vagas")
    with st.expander("➕ CRIAR NOVA VAGA", expanded=False):
        with st.form("f_vaga"):
            n_v = st.text_input("Nome da Vaga")
            a_v = st.selectbox("Departamento", ["Comercial", "Operações", "Tecnologia", "RH", "Marketing"])
            if st.form_submit_button("CONFIRMAR CRIAÇÃO"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO vagas (nome_vaga, area, status_vaga) VALUES (:n, :a, 'Aberta')"), {"n": n_v, "a": a_v})
                    conn.commit()
                st.rerun()

    st.divider()
    df_v = carregar_vagas()
    for _, row in df_v.iterrows():
        col1, col2 = st.columns([4, 1])
        col1.info(f"**{row['nome_vaga']}** | {row['area']}")
        if col2.button("🗑️ APAGAR", key=f"del_{row['nome_vaga']}"):
            with engine.connect() as conn:
                conn.execute(text("DELETE FROM candidatos WHERE vaga_vinculada = :v"), {"v": row['nome_vaga']})
                conn.execute(text("DELETE FROM vagas WHERE nome_vaga = :v"), {"v": row['nome_vaga']})
                conn.commit()
            st.rerun()

# --- 9. FLUXO DE CANDIDATOS ---
elif menu == "⚙️ FLUXO DE CANDIDATOS":
    df_vagas = carregar_vagas()
    if df_vagas.empty:
        st.warning("Cadastre uma vaga primeiro.")
    else:
        v_sel = st.selectbox("Selecione a Vaga:", df_vagas["nome_vaga"].tolist())
        
        with st.popover("➕ Adicionar Candidato nesta Vaga"):
            nome_novo = st.text_input("Nome completo")
            if st.button("Salvar Candidato"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral) VALUES (:c, :v, 'Vaga aberta')"), {"c": nome_novo, "v": v_sel})
                    conn.commit()
                st.rerun()

        st.divider()
        df_c = carregar_candidatos_vaga(v_sel)
        if df_c.empty:
            st.info("Nenhum candidato nesta vaga.")
        else:
            # LISTA ATUALIZADA COM 'TESTE TÉCNICO'
            opcoes_status = [
                "Vaga aberta", 
                "Triagem", 
                "Entrevista RH", 
                "Teste Técnico", # <-- Novo status adicionado aqui
                "Entrevista gestor", 
                "Solicitação de documentos", 
                "Solicitação de contratos", 
                "Finalizada"
            ]
            
            for idx, cand in df_c.iterrows():
                with st.container():
                    st.markdown(f'<div class="candidate-card"><div class="candidate-name">{cand["candidato"]}</div><div class="candidate-status">{cand["status_geral"]}</div></div>', unsafe_allow_html=True)
                    
                    c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 1])
                    
                    # Tenta encontrar o índice do status atual; se não achar (ex: status antigo), volta para o 0
                    try:
                        idx_status = opcoes_status.index(cand['status_geral'])
                    except ValueError:
                        idx_status = 0

                    novo_status = c1.selectbox("Mudar Status", opcoes_status, index=idx_status, key=f"st_{cand['id']}")
                    
                    d_rh = cand['entrevista_rh'] if pd.notnull(cand['entrevista_rh']) else datetime.now()
                    d_gs = cand['entrevista_gestor'] if pd.notnull(cand['entrevista_gestor']) else datetime.now()
                    
                    data_rh = c2.date_input("📅 Entrev. RH", value=d_rh, key=f"rh_{cand['id']}")
                    data_gestor = c3.date_input("📅 Entrev. Gestor", value=d_gs, key=f"gs_{cand['id']}")
                    
                    if c4.button("💾", key=f"sv_{cand['id']}"):
                        with engine.connect() as conn:
                            conn.execute(text("""
                                UPDATE candidatos SET status_geral = :s, entrevista_rh = :rh, entrevista_gestor = :gs 
                                WHERE id = :id
                            """), {"s": novo_status, "rh": data_rh, "gs": data_gestor, "id": cand['id']})
                            conn.commit()
                        st.toast(f"Atualizado!")
                        st.rerun()
                    
                    if c4.button("🗑️", key=f"del_c_{cand['id']}"):
                        with engine.connect() as conn:
                            conn.execute(text("DELETE FROM candidatos WHERE id = :id"), {"id": cand['id']})
                            conn.commit()
                        st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)
# --- 10. NOVA ABA: ONBOARDING ---
elif menu == "🚀 ONBOARDING":
    st.subheader("Processo de Admissão")
    df_aprovados = carregar_aprovados()
    
    if df_aprovados.empty:
        st.info("Para acompanhar um onboarding, mude o status do candidato para 'Finalizada' no Fluxo.")
    else:
        selecionado = st.selectbox("Selecione o candidato aprovado:", df_aprovados["candidato"].tolist())
        cand_data = df_aprovados[df_aprovados["candidato"] == selecionado].iloc[0]
        
        st.markdown(f"<div class='onboarding-title'>Checklist: {selecionado}</div>", unsafe_allow_html=True)
        
        fluxo = {
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

        with st.container(border=True):
            col1, col2 = st.columns(2)
            novos_valores = {}
            items = list(fluxo.items())
            
            for i, (label, col_db) in enumerate(items):
                target_col = col1 if i < 6 else col2
                # Valor atual do banco
                valor_atual = bool(cand_data[col_db]) if col_db in cand_data else False
                novos_valores[col_db] = target_col.checkbox(label, value=valor_atual, key=f"onb_{cand_data['id']}_{col_db}")

        if st.button("💾 Salvar Evolução", use_container_width=True):
            with engine.connect() as conn:
                set_clause = ", ".join([f"{k} = :{k}" for k in novos_valores.keys()])
                query = text(f"UPDATE candidatos SET {set_clause} WHERE id = :id")
                params = novos_valores
                params["id"] = int(cand_data["id"])
                conn.execute(query, params)
                conn.commit()
            st.success("Progresso salvo!")
            st.rerun()

