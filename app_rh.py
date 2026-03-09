import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from datetime import datetime, date
import os

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RH ETUS - Gestão Pro", layout="wide", page_icon="logo.png")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    html, body, [class*="css"], [data-testid="stSidebar"] { font-family: 'Space Grotesk', sans-serif !important; }
    .header-rh { font-size: 42px; font-weight: 700; color: #8DF768; margin-bottom: 30px; border-left: 10px solid #8DF768; padding-left: 15px; }
    .vaga-header { background-color: rgba(141, 247, 104, 0.2); color: inherit; padding: 10px; border-radius: 5px; margin-top: 20px; margin-bottom: 10px; font-weight: bold; border-left: 5px solid #8DF768; }
    .status-vencido { color: #FF4B4B; font-weight: bold; }
    .status-alerta { color: #FFA500; font-weight: bold; }
    .status-ok { color: #28A745; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE BANCO DE DADOS ---
@st.cache_resource
def get_engine():
    try:
        DB_URL = st.secrets["postgres"]["url"]
        return create_engine(DB_URL, pool_size=5, max_overflow=10, connect_args={"sslmode": "require"})
    except:
        st.error("Erro nas credenciais do banco de dados.")
        st.stop()

engine = get_engine()

# --- 3. FUNÇÕES DE DADOS ---
def executar_sql(query, params=None):
    try:
        with engine.begin() as conn:
            conn.execute(text(query), params or {})
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro: {e}")
        return False

@st.cache_data(ttl=60)
def carregar_dados(tabela):
    return pd.read_sql(f"SELECT * FROM {tabela}", engine)

# --- 4. INICIALIZAÇÃO DO BANCO ---
def inicializar_banco():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vagas (id SERIAL PRIMARY KEY, nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE, data_fechamento DATE);
            CREATE TABLE IF NOT EXISTS candidatos (id SERIAL PRIMARY KEY, candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, historico TEXT, motivo_perda TEXT, envio_proposta BOOLEAN DEFAULT FALSE, solic_documentos BOOLEAN DEFAULT FALSE, solic_contrato BOOLEAN DEFAULT FALSE, solic_acessos BOOLEAN DEFAULT FALSE);
            CREATE TABLE IF NOT EXISTS contratos_estagio (id SERIAL PRIMARY KEY, estagiario TEXT, instituicao TEXT, data_inicio DATE, data_fim DATE, status_contrato TEXT);
        """))
        # Atualização automática de colunas para o módulo DP
        colunas_dp = [
            ("time_equipe", "TEXT"), ("funcao", "TEXT"), 
            ("solic_contrato_dp", "BOOLEAN DEFAULT FALSE"), ("assina_etus", "BOOLEAN DEFAULT FALSE"), 
            ("assina_faculdade", "BOOLEAN DEFAULT FALSE"), ("envio_juridico", "BOOLEAN DEFAULT FALSE")
        ]
        for col, tipo in colunas_dp:
            try: conn.execute(text(f"ALTER TABLE contratos_estagio ADD COLUMN IF NOT EXISTS {col} {tipo};"))
            except: pass

inicializar_banco()

# --- 5. SIDEBAR COM MENUS SEPARADOS ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    else: st.markdown("## 🏢 RH ETUS")
    st.divider()
    area_selecionada = st.selectbox("GERENCIAMENTO", ["RH - Recrutamento", "DP - Departamento Pessoal"])
    st.divider()
    if area_selecionada == "RH - Recrutamento":
        menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])
    else:
        menu = st.radio("NAVEGAÇÃO", ["📊 DASHBOARD DP", "🎓 ESTAGIÁRIOS", "📄 DOCUMENTOS"])

st.markdown(f'<div class="header-rh">{menu}</div>', unsafe_allow_html=True)

# --- 6. LÓGICA DAS ABAS ---

# --- MÓDULO DP: DASHBOARD ---
if menu == "📊 DASHBOARD DP":
    df_est = carregar_dados("contratos_estagio")
    if not df_est.empty:
        df_est['data_fim'] = pd.to_datetime(df_est['data_fim'], errors='coerce')
        df_est['data_inicio'] = pd.to_datetime(df_est['data_inicio'], errors='coerce')
        hoje = pd.Timestamp(date.today())

        # Lógica de Conclusão: Todas as 4 etapas marcadas
        df_est['doc_concluida'] = (
            (df_est['solic_contrato_dp'] == True) & 
            (df_est['assina_etus'] == True) & 
            (df_est['assina_faculdade'] == True) & 
            (df_est['envio_juridico'] == True)
        )

        df_pendentes = df_est[df_est['doc_concluida'] == False]
        df_concluidos = df_est[df_est['doc_concluida'] == True]

        c1, c2, c3 = st.columns(3)
        c1.metric("🎓 TOTAL", len(df_est))
        c2.metric("⏳ PENDENTES DOC.", len(df_pendentes))
        c3.metric("✅ CONCLUÍDOS DOC.", len(df_concluidos))

        st.divider()
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("🚨 Pendências de Documentação")
            if not df_pendentes.empty:
                for _, row in df_pendentes.iterrows():
                    faltando = []
                    if not row['solic_contrato_dp']: faltando.append("Solicitação")
                    if not row['assina_etus']: faltando.append("Assin. ETUS")
                    if not row['assina_faculdade']: faltando.append("Assin. Facul.")
                    if not row['envio_juridico']: faltando.append("Jurídico")
                    st.warning(f"**{row['estagiario']}** | Pendente: {', '.join(faltando)}")
            else: st.success("Tudo em dia!")

        with col_right:
            st.subheader("📅 Controle de Vencimentos (Concluídos)")
            if not df_concluidos.empty:
                for _, row in df_concluidos.iterrows():
                    total_d = (row['data_fim'] - row['data_inicio']).days
                    passado = (hoje - row['data_inicio']).days
                    prog = max(0, min(100, int((passado/total_d)*100))) if total_d > 0 else 0
                    st.write(f"**{row['estagiario']}** ✅")
                    st.progress(prog/100)
                    st.caption(f"Vence em: {row['data_fim'].strftime('%d/%m/%Y')}")
            else: st.info("Sem contratos 100% concluídos.")
    else: st.info("Sem dados.")

# --- MÓDULO DP: GESTÃO DE ESTAGIÁRIOS ---
elif menu == "🎓 ESTAGIÁRIOS":
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("📝 Novo Registro")
        with st.form("f_est", clear_on_submit=True):
            n = st.text_input("Nome"); i = st.text_input("Instituição")
            f = st.text_input("Função"); t = st.selectbox("Time", ["Tecnologia", "Comercial", "Marketing", "Operações", "RH", "Financeiro", "Outros"])
            di = st.date_input("Início"); df = st.date_input("Término")
            if st.form_submit_button("CADASTRAR"):
                executar_sql("INSERT INTO contratos_estagio (estagiario, instituicao, funcao, time_equipe, data_inicio, data_fim) VALUES (:n, :i, :f, :t, :di, :df)", 
                             {"n": n, "i": i, "f": f, "t": t, "di": di, "df": df}); st.rerun()

    with col2:
        st.subheader("📋 Gestão e Etapas")
        df_e = carregar_dados("contratos_estagio")
        if not df_e.empty:
            for _, row in df_e.iterrows():
                is_ok = all([row.get('solic_contrato_dp'), row.get('assina_etus'), row.get('assina_faculdade'), row.get('envio_juridico')])
                with st.expander(f"👤 {row['estagiario']} {'✅' if is_ok else '⏳'}"):
                    st.write(f"**Função:** {row.get('funcao')} | **Time:** {row.get('time_equipe')}")
                    c_a, c_b, c_c, c_d = st.columns(4)
                    s = c_a.checkbox("Solicit.", value=bool(row.get('solic_contrato_dp')), key=f"s{row['id']}")
                    ae = c_b.checkbox("ETUS", value=bool(row.get('assina_etus')), key=f"ae{row['id']}")
                    af = c_c.checkbox("Facul.", value=bool(row.get('assina_faculdade')), key=f"af{row['id']}")
                    ej = c_d.checkbox("Jurid.", value=bool(row.get('envio_juridico')), key=f"ej{row['id']}")
                    if st.button("Salvar Progresso", key=f"sv{row['id']}"):
                        executar_sql("UPDATE contratos_estagio SET solic_contrato_dp=:s, assina_etus=:ae, assina_faculdade=:af, envio_juridico=:ej WHERE id=:id", 
                                     {"s": s, "ae": ae, "af": af, "ej": ej, "id": row['id']}); st.rerun()
                    if st.button("🗑️ Excluir", key=f"dl{row['id']}"):
                        executar_sql("DELETE FROM contratos_estagio WHERE id=:id", {"id": row['id']}); st.rerun()
        else: st.info("Cadastre um estagiário.")

# --- MÓDULO RH: INDICADORES ---
elif menu == "📊 INDICADORES":
    df_v = carregar_dados("vagas")
    df_c = carregar_dados("candidatos")
    if not df_v.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 VAGAS ATIVAS", len(df_v[df_v['status_vaga'] == 'Aberta']))
        if not df_c.empty:
            ordem = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada"]
            cnt = df_c['status_geral'].value_counts().reindex(ordem).fillna(0).reset_index()
            fig = px.funnel(cnt, x='count', y='status_geral', color_discrete_sequence=['#8DF768'])
            st.plotly_chart(fig, use_container_width=True)

# --- DEMAIS MÓDULOS (ESTRUTURA MANTIDA) ---
elif menu == "🏢 VAGAS":
    st.write("Gestão de Vagas Ativas")
elif menu == "⚙️ CANDIDATOS":
    st.write("Gestão de Fluxo de Candidatos")
elif menu == "🚀 ONBOARDING":
    st.write("Checklist de Entrada")
elif menu == "📄 DOCUMENTOS":
    st.write("Repositório de Documentos DP")
