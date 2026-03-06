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

# --- 3. INICIALIZAÇÃO DE BANCO ---
def inicializar_banco():
    with engine.connect() as conn:
        # Colunas novas para VAGAS
        vagas_cols = {"gestor": "TEXT", "data_abertura": "DATE", "data_fechamento": "DATE"}
        for col, tipo in vagas_cols.items():
            try:
                conn.execute(text(f"ALTER TABLE vagas ADD COLUMN IF NOT EXISTS {col} {tipo}"))
                conn.commit()
            except: pass
        
        # Colunas para candidatos
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

# --- 4. CSS (REMOÇÃO AGRESSIVA DE BOLINHAS E SELETORES) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    
    /* Fontes e Sidebar */
    html, body, [class*="css"], [data-testid="stSidebar"] { 
        font-family: 'Space Grotesk', sans-serif !important; 
    }
    [data-testid="stSidebar"] { background-color: #0E1117 !important; }

    /* 1. ESCONDE O CÍRCULO/BOTÃO (RADIO) EM SI */
    [data-testid="stSidebar"] div[role="radiogroup"] [data-testid="stWidgetSelectionColumn"] {
        display: none !important;
    }

    /* 2. REMOVE O ESPAÇAMENTO QUE A BOLINHA OCUPAVA */
    [data-testid="stSidebar"] div[role="radiogroup"] > div {
        gap: 0px !important;
    }

    /* 3. LIMPA QUALQUER FUNDO CINZA/VERMELHO AO CLICAR */
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
        padding: 10px 0px !important;
        cursor: pointer;
    }

    /* 4. ESTILO DO TEXTO (Navegação Limpa) */
    /* Texto Inativo */
    [data-testid="stSidebar"] div[role="radiogroup"] label p {
        color: #777777 !important;
        font-size: 18px !important;
        font-weight: 400 !important;
        margin-left: 0px !important;
        transition: all 0.3s ease;
    }

    /* Texto Selecionado (Destaque em Verde Etus) */
    [data-testid="stSidebar"] div[role="radiogroup"] input:checked + div p {
        color: #8DF768 !important;
        font-weight: 700 !important;
        font-size: 20px !important;
    }

    /* Hover no texto */
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover p {
        color: #FFFFFF !important;
    }

    /* --- CARREGAMENTO: BOLA DE FUTEBOL AMERICANO --- */
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
        100% { transform: translateY(0px) rotate(360deg); filter: drop-shadow(0 0 0px #8DF768); }
    }

    /* Layout Geral */
    .header-rh { font-size: 42px; font-weight: 700; color: #8DF768; margin-bottom: 30px; border-left: 10px solid #151514; padding-left: 15px; }
    .candidate-card { background-color: #1E1E1E; padding: 20px; border-radius: 12px; border: 1px solid #333; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. FUNÇÕES DE CARGA ---
def carregar_vagas():
    return pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)

def carregar_candidatos_vaga(v_nome):
    query = text("SELECT * FROM candidatos WHERE vaga_vinculada = :v ORDER BY id DESC")
    return pd.read_sql(query, engine, params={"v": v_nome})

def carregar_aprovados():
    return pd.read_sql("SELECT * FROM candidatos WHERE status_geral = 'Finalizada' OR aprovacao_final = 'Sim' ORDER BY candidato", engine)

# --- 6. SIDEBAR (NOMES DAS ABAS ATUALIZADOS) ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    # Nomes das abas atualizados conforme solicitado
    menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])

st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- 7. INDICADORES (DASHBOARD DE ENVELHECIMENTO DE VAGAS) ---
if menu == "📊 INDICADORES":
    df_v = carregar_vagas()
    df_c = pd.read_sql("SELECT * FROM candidatos", engine)
    
    if not df_v.empty:
        # --- CÁLCULO DE AGING (DIAS EM ABERTO) ---
        hoje = pd.Timestamp(datetime.now().date())
        
        # Converter datas e calcular dias
        df_v['data_abertura'] = pd.to_datetime(df_v['data_abertura'])
        df_v['data_fechamento'] = pd.to_datetime(df_v['data_fechamento'])
        
        # Se estiver aberta, usa HOJE. Se fechada, usa DATA FECHAMENTO.
        df_v['dias_aberta'] = df_v.apply(
            lambda x: (hoje - x['data_abertura']).days if pd.isnull(x['data_fechamento']) 
            else (x['data_fechamento'] - x['data_abertura']).days, axis=1
        )

        # --- CARDS DE MÉTRICAS ---
        c1, c2, c3, c4 = st.columns(4)
        vagas_ativas = len(df_v[df_v['status_vaga'] == 'Aberta'])
        media_dias = int(df_v['dias_aberta'].mean()) if not df_v.empty else 0
        vaga_mais_antiga = df_v[df_v['status_vaga'] == 'Aberta']['dias_aberta'].max()
        
        c1.metric("📌 VAGAS ATIVAS", vagas_ativas)
        c2.metric("⏱️ MÉDIA DE DIAS", f"{media_dias} dias")
        c3.metric("⚠️ VAGA MAIS ANTIGA", f"{vaga_mais_antiga if pd.notnull(vaga_mais_antiga) else 0} dias")
        c4.metric("✅ CONTRATAÇÕES", len(df_c[df_c["status_geral"] == "Finalizada"]))

        st.divider()

        # --- GRÁFICO DE AGING ---
        st.subheader("⏳ Tempo de Abertura por Vaga")
        
        # Filtrar apenas as que estão abertas para o gráfico de envelhecimento
        df_grafico = df_v[df_v['status_vaga'] == 'Aberta'].sort_values('dias_aberta', ascending=True)
        
        if not df_grafico.empty:
            fig_aging = px.bar(
                df_grafico,
                x='dias_aberta',
                y='nome_vaga',
                orientation='h',
                text='dias_aberta',
                labels={'dias_aberta': 'Dias em Aberto', 'nome_vaga': 'Vaga'},
                color='dias_aberta',
                color_continuous_scale=['#8DF768', '#F7D068', '#F76868'] # Verde -> Amarelo -> Vermelho
            )
            
            fig_aging.update_traces(textposition='outside', marker_line_color='rgb(8,48,107)', marker_line_width=1.5, opacity=0.8)
            fig_aging.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color="#FFFFFF",
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=False)
            )
            st.plotly_chart(fig_aging, use_container_width=True)
        else:
            st.info("Nenhuma vaga aberta no momento para exibir no gráfico.")

        # --- STATUS DOS CANDIDATOS ---
        st.divider()
        st.subheader("👥 Funil de Candidatos (Geral)")
        if not df_c.empty:
            fig_funil = px.pie(df_c, names="status_geral", hole=.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_funil, use_container_width=True)
    else:
        st.info("Cadastre vagas para visualizar os indicadores.")

# --- 8. VAGAS (ANTIGO GESTÃO DE VAGAS) ---
elif menu == "🏢 VAGAS":
    st.subheader("Painel de Vagas")
    with st.expander("➕ CRIAR NOVA VAGA"):
        with st.form("f_vaga"):
            n_v = st.text_input("Nome da Vaga")
            a_v = st.selectbox("Departamento", ["Comercial", "Operações", "Tecnologia", "RH", "Marketing"])
            g_v = st.text_input("Gestor Responsável")
            d_ab = st.date_input("Data Abertura", value=datetime.now())
            if st.form_submit_button("CONFIRMAR"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO vagas (nome_vaga, area, status_vaga, gestor, data_abertura) VALUES (:n, :a, 'Aberta', :g, :d)"), 
                                 {"n": n_v, "a": a_v, "g": g_v, "d": d_ab})
                    conn.commit()
                st.rerun()

    st.divider()
    df_v = carregar_vagas()
    for _, row in df_v.iterrows():
        v_id = row['id'] if 'id' in df_v.columns else None
        v_nome_orig = row['nome_vaga']
        v_key = v_id if v_id is not None else v_nome_orig
        
        d_ini = pd.to_datetime(row['data_abertura'])
        d_fim = pd.to_datetime(row['data_fechamento']) if pd.notnull(row['data_fechamento']) else datetime.now()
        dias = (d_fim - d_ini).days if pd.notnull(d_ini) else 0
        
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 2, 1])
            c1.markdown(f"**{row['nome_vaga']}** ({row['area']})\n\n👤 Gestor: {row.get('gestor', 'N/A')}")
            c2.write(f"⏱️ Aberta há: {dias} dias\n\n📅 Início: {row['data_abertura']}")
            
            if c3.button("📝 EDITAR", key=f"edbtn_{v_key}"):
                st.session_state[f"edit_vaga_{v_key}"] = True
            
            if st.session_state.get(f"edit_vaga_{v_key}"):
                with st.form(f"form_ed_{v_key}"):
                    novo_n = st.text_input("Nome", value=row['nome_vaga'])
                    novo_g = st.text_input("Gestor", value=row.get('gestor', ''))
                    novo_s = st.selectbox("Status", ["Aberta", "Fechada", "Pausada"], index=0)
                    dt_ab = st.date_input("Abertura", value=row['data_abertura'] if pd.notnull(row['data_abertura']) else datetime.now())
                    dt_fc = st.date_input("Fechamento", value=row['data_fechamento'] if pd.notnull(row['data_fechamento']) else None)
                    
                    if st.form_submit_button("SALVAR"):
                        with engine.connect() as conn:
                            params = {"n": novo_n, "g": novo_g, "s": novo_s, "da": dt_ab, "df": dt_fc}
                            if v_id is not None:
                                params["id"] = v_id
                                conn.execute(text("UPDATE vagas SET nome_vaga=:n, gestor=:g, status_vaga=:s, data_abertura=:da, data_fechamento=:df WHERE id=:id"), params)
                            else:
                                params["nome_orig"] = v_nome_orig
                                conn.execute(text("UPDATE vagas SET nome_vaga=:n, gestor=:g, status_vaga=:s, data_abertura=:da, data_fechamento=:df WHERE nome_vaga=:nome_orig"), params)
                            conn.commit()
                        st.session_state[f"edit_vaga_{v_key}"] = False
                        st.rerun()

# --- 9. CANDIDATOS (ANTIGO FLUXO DE CANDIDATOS) ---
elif menu == "⚙️ CANDIDATOS":
    df_vagas = carregar_vagas()
    if not df_vagas.empty:
        v_sel = st.selectbox("Vaga:", df_vagas["nome_vaga"].tolist())
        df_c = carregar_candidatos_vaga(v_sel)
        opcoes_status = ["Vaga aberta", "Triagem", "Entrevista RH", "Teste Técnico", "Entrevista gestor", "Entrevista Cultura", "Solicitação de documentos", "Solicitação de contratos", "Finalizada"]
        
        for _, cand in df_c.iterrows():
            with st.container():
                st.markdown(f'<div class="candidate-card"><b>{cand["candidato"]}</b> | {cand["status_geral"]}</div>', unsafe_allow_html=True)
                c_st, c_rh, c_gs, c_cu, c_bt = st.columns([1.5, 1, 1, 1, 0.5])
                n_status = c_st.selectbox("Status", opcoes_status, index=opcoes_status.index(cand['status_geral']) if cand['status_geral'] in opcoes_status else 0, key=f"s_{cand['id']}")
                
                def campo_dt(col, label, val, k):
                    if col.checkbox(f"Agendar {label}", value=pd.notnull(val), key=f"ck_{k}"):
                        return col.date_input(f"Data {label}", value=val if pd.notnull(val) else datetime.now(), key=f"dt_{k}")
                    return None

                res_rh = campo_dt(c_rh, "RH", cand['entrevista_rh'], f"rh_{cand['id']}")
                res_gs = campo_dt(c_gs, "Gestor", cand['entrevista_gestor'], f"gs_{cand['id']}")
                res_cu = campo_dt(c_cu, "Cultura", cand.get('entrevista_cultura'), f"cu_{cand['id']}")
                
                if c_bt.button("💾", key=f"sv_{cand['id']}"):
                    with engine.connect() as conn:
                        conn.execute(text("UPDATE candidatos SET status_geral=:s, entrevista_rh=:rh, entrevista_gestor=:gs, entrevista_cultura=:cu WHERE id=:id"),
                                     {"s": n_status, "rh": res_rh, "gs": res_gs, "cu": res_cu, "id": cand['id']})
                        conn.commit()
                    st.rerun()

# --- 10. ONBOARDING ---
# --- 10. ONBOARDING (NOME CORRIGIDO) ---
elif menu == "🚀 ONBOARDING":
    st.subheader("Onboarding de Aprovados")
    
    # Carregamos os candidatos que já foram aprovados ou finalizados
    df_aprovados = carregar_aprovados()
    
    if not df_aprovados.empty:
        # Seletor do Candidato
        selecionado = st.selectbox("Selecione o Novo Colaborador:", df_aprovados["candidato"].tolist())
        
        # Filtramos os dados apenas desse candidato
        cand_data = df_aprovados[df_aprovados["candidato"] == selecionado].iloc[0]
        
        st.markdown(f"### Checklist de Entrada: **{selecionado}**")
        st.caption(f"Vaga: {cand_data['vaga_vinculada']}")
        
        # Mapeamento de Labels Amigáveis para as Colunas do Banco
        etapas = {
            "Envio de Proposta": "envio_proposta",
            "Coleta de Documentos": "solic_documentos",
            "Fotos para Crachá/Perfil": "solic_fotos",
            "Assinatura de Contrato": "solic_contrato",
            "Criação de Acessos": "solic_acessos",
            "Cadastro RH/Gestor": "cad_rh_gestor",
            "Benefício: STARBEM": "cad_starbem",
            "Benefício: Dasa": "cad_dasa",
            "Benefício: AVUS": "cad_avus",
            "Agendamento de Onboarding": "agend_onboarding",
            "Envio ao Gestor": "envio_gestor"
        }
        
        novos_status = {}
        
        # Organizamos o Checklist em duas colunas para ocupar melhor a tela
        col_on1, col_on2 = st.columns(2)
        
        for i, (label, col_db) in enumerate(etapas.items()):
            # Alterna entre coluna 1 e 2
            target_col = col_on1 if i < 6 else col_on2
            
            # Pegamos o valor atual no banco (converte para bool para o checkbox)
            valor_atual = bool(cand_data.get(col_db, False))
            
            # Criamos o checkbox
            novos_status[col_db] = target_col.checkbox(
                label, 
                value=valor_atual, 
                key=f"chk_on_{cand_data['id']}_{col_db}"
            )
            
        st.divider()
        
        # Botão para Salvar as alterações no Onboarding
        if st.button("💾 SALVAR PROGRESSO DO ONBOARDING", use_container_width=True):
            with engine.connect() as conn:
                # Montamos o comando UPDATE dinamicamente
                clausula_set = ", ".join([f"{k} = :{k}" for k in novos_status.keys()])
                query_update = text(f"UPDATE candidatos SET {clausula_set} WHERE id = :id")
                
                # Executamos passando o dicionário de novos status + o ID do candidato
                conn.execute(query_update, {**novos_status, "id": int(cand_data["id"])})
                conn.commit()
                
            st.success(f"Progresso de {selecionado} atualizado com sucesso!")
            st.balloons() # Efeito visual de comemoração
            st.rerun()
    else:
        st.info("Ainda não há candidatos aprovados para iniciar o processo de Onboarding.")
        st.write("Dica: Altere o status de um candidato para 'Finalizada' ou marque 'Sim' em Aprovação Final na aba anterior.")







