import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    .vaga-header { background-color: rgba(141, 247, 104, 0.2); color: inherit; padding: 12px; border-radius: 8px; margin-top: 20px; margin-bottom: 10px; font-weight: bold; border-left: 5px solid #8DF768; }
    .curriculo-box { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #8DF768; color: #f0f0f0; margin-top: 15px; }
    .stProgress > div > div > div > div { background-color: #8DF768; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE BANCO DE DADOS ---
@st.cache_resource
def get_engine():
    try:
        DB_URL = st.secrets["postgres"]["url"]
        return create_engine(DB_URL, pool_size=10, max_overflow=20, connect_args={"sslmode": "require"})
    except Exception as e:
        st.error(f"Erro de conexão: {e}"); st.stop()

engine = get_engine()

# --- 3. FUNÇÕES DE APOIO ---
def executar_sql(query, params=None):
    try:
        with engine.begin() as conn:
            conn.execute(text(query), params or {})
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro SQL: {e}"); return False

@st.cache_data(ttl=1)
def carregar_dados(tabela):
    try:
        with engine.connect() as conn:
            return pd.read_sql(text(f"SELECT * FROM {tabela} ORDER BY id DESC"), conn)
    except:
        return pd.DataFrame()

# --- 4. BANCO DE DADOS (ESTRUTURA COMPLETA E ATUALIZADA) ---
with engine.begin() as conn:
    # 1. CRIAÇÃO DE TABELAS (Caso não existam)
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS vagas (
            id SERIAL PRIMARY KEY, 
            nome_vaga TEXT, 
            area TEXT, 
            status_vaga TEXT, 
            gestor TEXT, 
            data_abertura DATE, 
            data_fechamento DATE, 
            empresa TEXT
        );
    """))
    
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS candidatos (
            id SERIAL PRIMARY KEY, 
            candidato TEXT, 
            vaga_vinculada TEXT, 
            status_geral TEXT, 
            arquivo_cv BYTEA, 
            envio_proposta BOOLEAN DEFAULT FALSE, 
            solic_documentos BOOLEAN DEFAULT FALSE, 
            solic_contrato BOOLEAN DEFAULT FALSE, 
            solic_acessos BOOLEAN DEFAULT FALSE,
            indicacao BOOLEAN DEFAULT FALSE,
            nome_indicador TEXT,
            data_inicio DATE,
            data_proposta DATE,
            data_documentos DATE,
            data_foto_curiosidades DATE,
            data_contrato DATE,
            data_equipamentos DATE
        );
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS contratos_estagio (
            id SERIAL PRIMARY KEY, 
            estagiario TEXT, 
            instituicao TEXT, 
            data_inicio DATE, 
            data_fim DATE, 
            time_equipe TEXT, 
            solic_contrato_dp BOOLEAN DEFAULT FALSE, 
            assina_etus BOOLEAN DEFAULT FALSE, 
            assina_faculdade BOOLEAN DEFAULT FALSE, 
            envio_juridico BOOLEAN DEFAULT FALSE
        );
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS controle_experiencia (
            id SERIAL PRIMARY KEY, 
            nome TEXT, 
            cargo TEXT, 
            time_equipe TEXT, 
            data_inicio DATE, 
            av1_feito BOOLEAN DEFAULT FALSE, 
            av1_data DATE, 
            av1_responsavel TEXT, 
            av2_feito BOOLEAN DEFAULT FALSE, 
            av2_data DATE, 
            av2_responsavel TEXT
        );
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS colaboradores_ativos (
            id SERIAL PRIMARY KEY, 
            nome TEXT, 
            tipo TEXT, 
            data_admissao DATE, 
            cad_starbem BOOLEAN DEFAULT FALSE, 
            incl_amil BOOLEAN DEFAULT FALSE, 
            ifood_ativo BOOLEAN DEFAULT FALSE, 
            equipamento_entregue BOOLEAN DEFAULT FALSE
        );
    """))

  # 2. MIGRATIONS 
    migrations = [
    "ALTER TABLE pagamentos_gerais ADD COLUMN IF NOT EXISTS valor_pg NUMERIC;",
    "ALTER TABLE pagamentos_gerais ADD COLUMN IF NOT EXISTS data_envio DATE;",
    "ALTER TABLE pagamentos_gerais ADD COLUMN IF NOT EXISTS data_pagamento DATE;",
    "ALTER TABLE pagamentos_gerais ADD COLUMN IF NOT EXISTS motivo TEXT;"
        "ALTER TABLE vagas ADD COLUMN IF NOT EXISTS empresa TEXT;",
        "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS indicacao BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS nome_indicador TEXT;",
        "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS data_inicio DATE;",
        "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS data_proposta DATE;",
        "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS data_documentos DATE;",
        "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS data_foto_curiosidades DATE;",
        "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS data_contrato DATE;",
        "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS data_equipamentos DATE;",
        "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS boas_vindas BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS data_boas_vindas DATE;"
    ]
    for sql in migrations:
        try:
            conn.execute(text(sql))
        except Exception:
            pass
# --- 5. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): 
        st.image("logo.png", use_container_width=True)
    st.divider()
    area_sel = st.selectbox("GERENCIAMENTO", ["RH - Recrutamento", "DP - Departamento Pessoal", "Financeiro & Notas"])
    
    if area_sel == "RH - Recrutamento":
        menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])
    elif area_sel == "DP - Departamento Pessoal":
        menu = st.radio("NAVEGAÇÃO", ["📊 DASHBOARD DP", "🎓 ESTAGIÁRIOS", "👥 COLABORADORES", "⏳ PERÍODO DE EXPERIÊNCIA"])
    else:
        # Importante: o texto aqui deve ser exatamente igual ao usado nos 'elif menu == ...'
        menu = st.radio("NAVEGAÇÃO", ["🍔 IFOOD", "💸 OUTROS PAGAMENTOS"])

st.markdown(f'<div class="header-rh">{menu}</div>', unsafe_allow_html=True)

# --- 6. MÓDULO INDICADORES (COM CONTADOR DE DIAS) ---
if menu == "📊 DASHBOARD RH":
    df_v = carregar_dados("vagas")
    df_c = carregar_dados("candidatos")
    
    if not df_v.empty:
        vagas_abertas = df_v[df_v['status_vaga'] == 'Aberta'].copy()
        
        if not vagas_abertas.empty:
            vagas_abertas['data_abertura'] = pd.to_datetime(vagas_abertas['data_abertura']).dt.date
            vagas_abertas['dias_aberta'] = vagas_abertas['data_abertura'].apply(lambda x: (date.today() - x).days if x else 0)
            media_dias = vagas_abertas['dias_aberta'].mean()
        else:
            media_dias = 0

        c1, c2, c3 = st.columns(3)
        c1.metric("📌 VAGAS ATIVAS", len(vagas_abertas))
        c2.metric("⏳ MÉDIA TEMPO ABERTA", f"{int(media_dias)} dias")
        
        if not df_c.empty:
            st.divider()
            col_l, col_r = st.columns(2)
            with col_l:
                st.subheader("📊 Funil de Recrutamento")
                ordem = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada"]
                cnt = df_c['status_geral'].value_counts().reindex(ordem).fillna(0).reset_index()
                st.plotly_chart(px.funnel(cnt, x='count', y='status_geral', color_discrete_sequence=['#8DF768']), use_container_width=True)
            with col_r:
                st.subheader("👥 Candidatos por Vaga")
                st.plotly_chart(px.pie(df_c, names='vaga_vinculada', hole=0.4), use_container_width=True)
# --- 7. MÓDULO VAGAS (COM EDIÇÃO COMPLETA) ---
elif menu == "🏢 VAGAS":
    lista_empresas = ["ETUS", "BHAZ", "Evolution", "E3J", "No Name"]
    lista_times = ["RH", "Jurídico", "Financeiro", "Dados", "CRO", "Desenvolvimento", "Jornalismo", "Marketing", "SRE", "Retenção", "Monetização", "Comunidade", "Conteúdo", "Produto"]

    with st.expander("➕ CADASTRAR NOVA VAGA"):
        with st.form("nv"):
            col1, col2 = st.columns(2)
            nv = col1.text_input("Nome da Vaga")
            gv = col2.text_input("Gestor")
            
            col3, col4 = st.columns(2)
            ev = col3.selectbox("Empresa", lista_empresas)
            av = col4.selectbox("Time", lista_times)
            
            if st.form_submit_button("CRIAR"):
                executar_sql("INSERT INTO vagas (nome_vaga, area, status_vaga, gestor, data_abertura, empresa) VALUES (:n, :a, 'Aberta', :g, :d, :e)", 
                            {"n":nv,"a":av,"g":gv,"d":date.today(), "e":ev})
                st.rerun()

    df_v = carregar_dados("vagas")
    for _, row in df_v.iterrows():
        with st.expander(f"🏢 {row['nome_vaga']} | {row.get('empresa', '---')} ({row['status_vaga']})"):
            with st.form(f"edv{row['id']}"):
                c1, c2 = st.columns(2)
                v_nome = c1.text_input("Vaga", value=row['nome_vaga'])
                v_gestor = c2.text_input("Gestor", value=row['gestor'] if row['gestor'] else "")
                
                c3, c4 = st.columns(2)
                e_idx = lista_empresas.index(row['empresa']) if row['empresa'] in lista_empresas else 0
                v_empresa = c3.selectbox("Empresa", lista_empresas, index=e_idx)
                
                t_idx = lista_times.index(row['area']) if row['area'] in lista_times else 0
                v_area = c4.selectbox("Time", lista_times, index=t_idx)
                
                c5, c6 = st.columns(2)
                v_data = c5.date_input("Data Abertura", value=row['data_abertura'] if row['data_abertura'] else date.today())
                ns = c6.selectbox("Status", ["Aberta", "Pausada", "Finalizada"], 
                                 index=["Aberta", "Pausada", "Finalizada"].index(row['status_vaga']))
                
                if st.form_submit_button("SALVAR ALTERAÇÕES"):
                    df_f = date.today() if ns == "Finalizada" else None
                    executar_sql("""UPDATE vagas SET nome_vaga=:nv, area=:a, status_vaga=:s, gestor=:g, 
                                 data_abertura=:da, data_fechamento=:df, empresa=:e WHERE id=:id""", 
                                 {"nv":v_nome, "a":v_area, "s":ns, "g":v_gestor, "da":v_data, "df":df_f, "e":v_empresa, "id":row['id']})
                    st.rerun()
            
            if st.button(f"🗑️ Excluir Vaga", key=f"delv{row['id']}"):
                executar_sql("DELETE FROM vagas WHERE id=:id", {"id":row['id']})
                st.rerun()

# --- 8. MÓDULO CANDIDATOS ---
elif menu == "⚙️ CANDIDATOS":
    df_v = carregar_dados("vagas")
    df_c = carregar_dados("candidatos")
    
    with st.expander("➕ NOVO CANDIDATO"):
        with st.form("nc"):
            nc = st.text_input("Nome")
            vnc = st.selectbox("Vaga", df_v['nome_vaga'].tolist() if not df_v.empty else ["Geral"])
            if st.form_submit_button("ADICIONAR"):
                executar_sql("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral) VALUES (:n, :v, 'Triagem')", {"n":nc,"v":vnc})
                st.rerun()

    if not df_c.empty:
        for v_nome in df_c['vaga_vinculada'].unique():
            st.markdown(f'<div class="vaga-header">🏢 VAGA: {v_nome.upper()}</div>', unsafe_allow_html=True)
            for _, cr in df_c[df_c['vaga_vinculada'] == v_nome].iterrows():
                with st.expander(f"👤 {cr['candidato']} - {cr['status_geral']}"):
                    # FORMULÁRIO DE EDIÇÃO DE DADOS
                    with st.form(f"f_edit_{cr['id']}"):
                        c_nome = st.text_input("Nome do Candidato", value=cr['candidato'])
                        
                        col_ind1, col_ind2 = st.columns(2)
                        c_ind = col_ind1.checkbox("Possui Indicação?", value=bool(cr.get('indicacao', False)), key=f"check_ind_{cr['id']}")
                        c_quem = col_ind2.text_input("Nome de quem indicou", value=cr.get('nome_indicador', "") if cr.get('nome_indicador') else "")
                        
                        etapas = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Entrevista Cultura", "Finalizada", "Perda"]
                        idx_etapa = etapas.index(cr['status_geral']) if cr['status_geral'] in etapas else 0
                        ns = st.selectbox("Etapa Atual", etapas, index=idx_etapa)
                        
                        if st.form_submit_button("SALVAR DADOS"):
                            executar_sql("UPDATE candidatos SET candidato=:n, indicacao=:ind, nome_indicador=:ni, status_geral=:s WHERE id=:id",
                                        {"n": c_nome, "ind": c_ind, "ni": c_quem, "s": ns, "id": cr['id']})
                            st.rerun()

                    # LÓGICA DE CONTRATAÇÃO (Só aparece se for Finalizada)
                    if ns == "Finalizada":
                        st.info("✨ Fase de contratação")
                        c_data = st.date_input("Data de Admissão", value=date.today(), key=f"dt_adm_{cr['id']}")
                        if st.button("Confirmar e Enviar ao DP", key=f"btn_dp_{cr['id']}"):
                            # Envia para Colaboradores e Experiência
                            executar_sql("INSERT INTO colaboradores_ativos (nome, tipo, data_admissao) VALUES (:n, 'CLT', :d)", {"n": cr['candidato'], "d": c_data})
                            executar_sql("INSERT INTO controle_experiencia (nome, cargo, time_equipe, data_inicio) VALUES (:n, :c, 'A definir', :d)", 
                                        {"n": cr['candidato'], "c": cr['vaga_vinculada'], "d": c_data})
                            st.success("Integrado com sucesso!")
                            st.rerun()

                    # DOWNLOAD CV E EXCLUSÃO
                    st.divider()
                    col_cv, col_del = st.columns(2)
                    with col_cv:
                        if cr.get('arquivo_cv') is not None:
                            st.download_button("📥 Baixar CV", cr['arquivo_cv'], f"CV_{cr['candidato']}.pdf", key=f"dl_{cr['id']}")
                        else:
                            st.caption("Sem currículo anexado.")
                    with col_del:
                        if st.button(f"🗑️ Excluir", key=f"del_{cr['id']}"):
                            executar_sql("DELETE FROM candidatos WHERE id=:id", {"id":cr['id']})
                            st.rerun()
# --- 9. MÓDULO ONBOARDING (DESIGN COMPACTO EM 2 COLUNAS) ---
# --- 9. MÓDULO ONBOARDING (COM EXPANDERS E DESIGN COMPACTO) ---
elif menu == "🚀 ONBOARDING":
    st.markdown("### 🚀 Gestão de Onboarding")
    st.caption("Clique no nome do candidato para expandir e gerir as etapas.")
    
    df_c = carregar_dados("candidatos")
    # Filtramos apenas candidatos contratados (status Finalizada)
    df_onboarding = df_c[df_c['status_geral'] == 'Finalizada']

    if not df_onboarding.empty:
        for _, row in df_onboarding.iterrows():
            # O st.expander permite minimizar e expandir a visualização
            with st.expander(f"👤 {row['candidato']} | Vaga: {row['vaga_vinculada']}"):
                
                with st.form(f"form_onb_exp_{row['id']}"):
                    # Linha 1: Planeamento de Data
                    st.markdown("**📅 Planeamento de Entrada**")
                    v_ini = st.date_input("Data Prevista de Início", 
                                         value=row.get('data_inicio') if row.get('data_inicio') else date.today(),
                                         label_visibility="collapsed")
                    
                    st.divider()
                    
                    # Função interna para renderizar as linhas de checklist
                    def render_onb_row(label, icon, key_check, key_date):
                        r_c1, r_c2, r_c3 = st.columns([0.2, 1.3, 1.5])
                        with r_c1:
                            check = st.checkbox("", value=bool(row.get(key_check, False)), key=f"chk_{key_check}_{row['id']}")
                        with r_c2:
                            st.markdown(f"{icon} {label}")
                        with r_c3:
                            dt = st.date_input("Data", 
                                              value=row.get(key_date) if row.get(key_date) else date.today(), 
                                              key=f"dt_{key_date}_{row['id']}",
                                              label_visibility="collapsed")
                        return check, dt

                    # Organização em duas colunas dentro do expander
                    st.markdown("**📝 Checklist de Processos**")
                    col_esq, col_dir = st.columns(2)

                    with col_esq:
                        c_prop, d_prop = render_onb_row("Proposta", "📨", "envio_proposta", "data_proposta")
                        c_doc, d_doc = render_onb_row("Documentos", "📂", "solic_documentos", "data_documentos")
                        c_foto, d_foto = render_onb_row("Foto/Curiosidades", "📸", "foto_curiosidades", "data_foto_curiosidades")

                    with col_dir:
                        c_cont, d_cont = render_onb_row("Contrato", "✍️", "solic_contrato", "data_contrato")
                        c_acess, d_acess = render_onb_row("Equipamentos", "💻", "solic_acessos", "data_equipamentos")
                        c_bv, d_bv = render_onb_row("Boas-vindas", "🎉", "boas_vindas", "data_boas_vindas")

                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Botão de Gravar
                    if st.form_submit_button("💾 GRAVAR PROGRESSO", use_container_width=True):
                        executar_sql("""
                            UPDATE candidatos SET 
                            data_inicio=:di,
                            envio_proposta=:cp, data_proposta=:dp,
                            solic_documentos=:cd, data_documentos=:dd,
                            solic_contrato=:cc, data_contrato=:dc,
                            solic_acessos=:ca, data_equipamentos=:de,
                            boas_vindas=:bv, data_boas_vindas=:dbv
                            WHERE id=:id
                        """, {
                            "di": v_ini, "cp": c_prop, "dp": d_prop, "cd": c_doc, "dd": d_doc,
                            "cc": c_cont, "dc": d_cont, "ca": c_acess, "de": d_acess, 
                            "bv": c_bv, "dbv": d_bv, "id": row['id']
                        })
                        st.success(f"Onboarding de {row['candidato']} atualizado!")
                        st.rerun()
            
            # Pequeno espaçamento entre expanders
            st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
            
    else:
        st.info("Não existem candidatos contratados para onboarding no momento.")
# --- 10. MÓDULO DASHBOARD DP ---
elif menu == "📊 DASHBOARD DP":
    st.subheader("Indicadores de Departamento Pessoal")
    
    # CARREGAMENTO DE DADOS
    df_col = carregar_dados("colaboradores_ativos")
    df_est = carregar_dados("contratos_estagio")
    df_exp = carregar_dados("controle_experiencia")
    df_c = carregar_dados("candidatos") # Necessário para o alerta de indicações

    if not df_col.empty:
        # MÉTRICAS TOTAIS
        c1, c2, c3, c4 = st.columns(4)
        total_clt = len(df_col[df_col['tipo'] == 'CLT'])
        total_pj = len(df_col[df_col['tipo'] == 'PJ'])
        total_est = len(df_est)
        
        c1.metric("👥 TOTAL ATIVOS", len(df_col) + total_est)
        c2.metric("📄 CLT", total_clt)
        c3.metric("🤝 PJ", total_pj)
        c4.metric("🎓 ESTAGIÁRIOS", total_est)

        st.divider()

        # GRÁFICOS LADO A LADO
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.subheader("Distribuição por Vínculo")
            fig_vinculo = px.pie(
                values=[total_clt, total_pj, total_est], 
                names=['CLT', 'PJ', 'Estágio'],
                hole=0.4,
                color_discrete_sequence=['#8DF768', '#00d4ff', '#ffeb3b']
            )
            st.plotly_chart(fig_vinculo, use_container_width=True)

        with col_g2:
            st.subheader("Estagiários por Time")
            if not df_est.empty:
                fig_est = px.bar(df_est, x='time_equipe', color='time_equipe', title="Distribuição de Estagiários")
                st.plotly_chart(fig_est, use_container_width=True)
            else:
                st.info("Sem estagiários cadastrados para exibir no gráfico.")

        # --- SEÇÃO DE ALERTAS ---
        st.divider()
        st.markdown('<div class="vaga-header">⚠️ PAINEL DE ALERTAS E PENDÊNCIAS</div>', unsafe_allow_html=True)
        
        col_a1, col_a2 = st.columns(2)

        # ALERTA 1: AVALIAÇÕES DE EXPERIÊNCIA
        with col_a1:
            st.markdown("##### ⏳ Avaliações de 90 dias (Próximos 7 dias)")
            hoje = date.today()
            alertas_exp = []
            if not df_exp.empty:
                for _, r in df_exp.iterrows():
                    # Garantir que data_inicio é um objeto de data
                    data_inicio = pd.to_datetime(r['data_inicio']).date()
                    d90 = data_inicio + pd.Timedelta(days=90)
                    # Alerta se não foi feito e se faltam 7 dias ou já venceu
                    if not r['av2_feito'] and (d90 - hoje).days <= 7:
                        alertas_exp.append(f"🟠 **{r['nome']}**: Vencimento em {d90.strftime('%d/%m/%Y')}")
            
            if alertas_exp:
                for a in alertas_exp:
                    st.warning(a)
            else:
                st.success("Nenhuma avaliação de 90 dias pendente para breve.")

        # ALERTA 2: PAGAMENTO DE INDICAÇÕES
        with col_a2:
            st.markdown("##### 💰 Bônus de Indicação (Pós 90 dias)")
            avisos_pagamento = []
            
            # Filtra candidatos que foram indicados e contratados (Finalizada)
            if not df_c.empty:
                contratados_ind = df_c[(df_c['status_geral'] == 'Finalizada') & (df_c['indicacao'] == True)]
                
                for _, cand in contratados_ind.iterrows():
                    # Cruzar com a data de início real no controle de experiência
                    if not df_exp.empty:
                        exp_v = df_exp[df_exp['nome'] == cand['candidato']]
                        if not exp_v.empty:
                            data_ini = pd.to_datetime(exp_v.iloc[0]['data_inicio']).date()
                            data_liberacao_pg = data_ini + pd.Timedelta(days=90)
                            
                            if hoje >= data_liberacao_pg:
                                avisos_pagamento.append(
                                    f"✅ **Liberado**: Pagar bônus para **{cand['nome_indicador']}** "
                                    f"(Indicação de {cand['candidato']})"
                                )
            
            if avisos_pagamento:
                for aviso in avisos_pagamento:
                    st.info(aviso)
            else:
                st.write("Sem pagamentos de indicação pendentes no momento.")
    else:
        st.info("Adicione colaboradores ativos para visualizar os indicadores de DP.")
# --- 11. MÓDULO ESTAGIÁRIOS ---
elif menu == "🎓 ESTAGIÁRIOS":
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("📝 Novo Registro")
        with st.form("f_est"):
            n, i = st.text_input("Nome"), st.text_input("Instituição")
            t = st.selectbox("Time", ["Tecnologia", "Comercial", "Operações", "RH", "Financeiro"])
            di, df = st.date_input("Início"), st.date_input("Fim")
            if st.form_submit_button("CADASTRAR"):
                executar_sql("INSERT INTO contratos_estagio (estagiario, instituicao, data_inicio, data_fim, time_equipe) VALUES (:n, :i, :di, :df, :t)", {"n":n,"i":i,"di":di,"df":df, "t":t}); st.rerun()
    with col2:
        df_e = carregar_dados("contratos_estagio")
        for _, r in df_e.iterrows():
            with st.expander(f"👤 {r['estagiario']}"):
                ca, cb, cc, cd = st.columns(4)
                s, ae, af, ej = ca.checkbox("Solic.", value=bool(r['solic_contrato_dp']), key=f"s{r['id']}"), cb.checkbox("ETUS", value=bool(r['assina_etus']), key=f"ae{r['id']}"), cc.checkbox("Facul.", value=bool(r['assina_faculdade']), key=f"af{r['id']}"), cd.checkbox("Jurid.", value=bool(r['envio_juridico']), key=f"ej{r['id']}")
                if st.button("Salvar Status", key=f"svest{r['id']}"):
                    executar_sql("UPDATE contratos_estagio SET solic_contrato_dp=:s, assina_etus=:ae, assina_faculdade=:af, envio_juridico=:ej WHERE id=:id", {"s":s,"ae":ae,"af":af,"ej":ej,"id":r['id']}); st.rerun()
                if st.button("🗑️ Excluir", key=f"delest{r['id']}"):
                    executar_sql("DELETE FROM contratos_estagio WHERE id=:id", {"id":r['id']}); st.rerun()

# --- 12. MÓDULO FINANCEIRO (IFOOD) ---
elif menu == "🍔 IFOOD":
    st.subheader("Gestão de Notas Fiscais - iFood")
    
    with st.expander("➕ CADASTRAR NOVA NOTA IFOOD"):
        with st.form("form_ifood"):
            c1, c2 = st.columns(2)
            eni = c1.selectbox("Empresa", ["ETUS", "BHAZ", "Evolution", "E3J", "No Name"], key="if_e")
            mni = c2.selectbox("Mês de Referência", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"], key="if_m")
            uni = st.file_uploader("Upload da NF (PDF)", type=["pdf"], key="if_u")
            
            if st.form_submit_button("SALVAR NOTA IFOOD"):
                if uni:
                    executar_sql("INSERT INTO notas_fiscais_ifood (empresa, mes_referencia, arquivo_nf, nome_arquivo, data_upload) VALUES (:e, :m, :a, :n, :d)",
                                {"e":eni, "m":mni, "a":uni.read(), "n":uni.name, "d":date.today()})
                    st.success("Nota salva!")
                    st.rerun()

    df_if = carregar_dados("notas_fiscais_ifood")
    if not df_if.empty:
        for _, r in df_if.iterrows():
            with st.expander(f"🍴 {r['mes_referencia']} - {r['empresa']}"):
                st.download_button("📥 Baixar NF", r['arquivo_nf'], r['nome_arquivo'], key=f"dl_if_{r['id']}")
                if st.button(f"🗑️ Excluir", key=f"del_if_{r['id']}"):
                    executar_sql("DELETE FROM notas_fiscais_ifood WHERE id=:id", {"id":r['id']})
                    st.rerun()

# --- 13. MÓDULO FINANCEIRO (OUTROS PAGAMENTOS) ---
elif menu == "💸 OUTROS PAGAMENTOS":
    st.subheader("Gestão de Outros Pagamentos")
    
    with st.expander("➕ LANÇAR NOVO PAGAMENTO"):
        with st.form("form_pg_geral"):
            c1, c2 = st.columns(2)
            epg = c1.selectbox("Empresa", ["Plusdin São Bernardo", "Projeto Consegui Aprender"], key="pg_e")
            mpg = c2.selectbox("Mês de Referência", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"], key="pg_m")
            
            c3, c4 = st.columns([1, 2])
            val_pg = c3.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f")
            motivo_pg = c4.text_input("Motivo do Pagamento")

            c5, c6 = st.columns(2)
            d_envio = c5.date_input("Data de Envio", value=date.today())
            d_pago = c6.date_input("Data de Pagamento", value=date.today())

            upg = st.file_uploader("Comprovante (PDF)", type=["pdf"], key="pg_u")
            
            if st.form_submit_button("REGISTRAR PAGAMENTO"):
                if upg:
                    executar_sql("""
                        INSERT INTO pagamentos_gerais 
                        (empresa, categoria, mes_referencia, arquivo_pg, nome_arquivo, data_upload, valor_pg, data_envio, data_pagamento, motivo) 
                        VALUES (:e, 'Geral', :m, :a, :n, :d, :v, :de, :dp, :mo)
                    """, {"e":epg, "m":mpg, "a":upg.read(), "n":upg.name, "d":date.today(), "v":val_pg, "de":d_envio, "dp":d_pago, "mo":motivo_pg})
                    st.success("Pagamento registrado!")
                    st.rerun()

    df_pg = carregar_dados("pagamentos_gerais")
    if not df_pg.empty:
        total = df_pg['valor_pg'].sum() if 'valor_pg' in df_pg.columns else 0
        st.metric("Total em Outros Pagamentos", f"R$ {total:,.2f}")
        for _, row in df_pg.iterrows():
            with st.expander(f"💰 R$ {row.get('valor_pg', 0):,.2f} | {row['empresa']} - {row.get('motivo', '')}"):
                st.download_button("📥 Baixar PDF", row['arquivo_pg'], row['nome_arquivo'], key=f"dl_pg_{row['id']}")
                if st.button(f"🗑️ Excluir Registro", key=f"del_pg_{row['id']}"):
                    executar_sql("DELETE FROM pagamentos_gerais WHERE id=:id", {"id":row['id']})
                    st.rerun()
                        
# --- 13. MÓDULO OUTROS PAGAMENTOS (FILTRO CORRETO) ---
elif menu == "💸 OUTROS PAGAMENTOS":
    st.subheader("Pagamentos Plusdin São Bernardo e Projeto Consegui Aprender")
    lista_pg = ["Plusdin São Bernardo", "Projeto Consegui Aprender"]
    col_u, col_l = st.columns([1, 2])
    with col_u:
        st.markdown('<div class="vaga-header">📤 NOVO LANÇAMENTO</div>', unsafe_allow_html=True)
        with st.form("f_pg"):
            emp = st.selectbox("Empresa", lista_pg)
            cat = st.radio("Categoria", ["PSB", "MDP"], horizontal=True)
            mes = st.selectbox("Mês", ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"])
            arq = st.file_uploader("PDF Comprovante", type="pdf")
            if st.form_submit_button("SALVAR PAGAMENTO"):
                if arq: executar_sql("INSERT INTO pagamentos_gerais (empresa, categoria, mes_referencia, arquivo_pg, nome_arquivo, data_upload) VALUES (:e,:c,:m,:a,:n,:d)", {"e":emp,"c":cat,"m":mes,"a":arq.getvalue(),"n":arq.name,"d":date.today()}); st.rerun()
    with col_l:
        st.markdown('<div class="vaga-header">🔍 CONSULTA PAGAMENTOS</div>', unsafe_allow_html=True)
        f_pg = st.multiselect("Filtrar por Empresa Geral", lista_pg, default=lista_pg)
        df_pg = carregar_dados("pagamentos_gerais")
        if not df_pg.empty:
            for _, r in df_pg[df_pg['empresa'].isin(f_pg)].iterrows():
                with st.expander(f"💰 {r['empresa']} | {r['categoria']} - {r['mes_referencia']}"):
                    st.download_button("📥 Baixar", r['arquivo_pg'], r['nome_arquivo'], key=f"dlpg{r['id']}")
                    if st.button("🗑️ Excluir", key=f"delpg{r['id']}"): executar_sql("DELETE FROM pagamentos_gerais WHERE id=:id", {"id":r['id']}); st.rerun()

# --- 14. MÓDULO PERÍODO DE EXPERIÊNCIA (REFORMULADO E COMPLETO) ---
elif menu == "⏳ PERÍODO DE EXPERIÊNCIA":
    st.subheader("Controle de Avaliação de Experiência (90 dias)")
    col_cad, col_gst = st.columns([1, 2])
    
    with col_cad:
        st.markdown('<div class="vaga-header">➕ CADASTRAR NOVO PERÍODO</div>', unsafe_allow_html=True)
        with st.form("f_exp_cad", clear_on_submit=True):
            n_exp = st.text_input("Nome do Prestador/Estagiário")
            c_exp = st.text_input("Cargo")
            t_exp = st.selectbox("Time", ["Tecnologia", "Comercial", "Operações", "RH", "Financeiro", "Marketing"])
            d_ini = st.date_input("Data de Início", value=date.today())
            if st.form_submit_button("CADASTRAR CONTROLE"):
                if n_exp:
                    executar_sql("INSERT INTO controle_experiencia (nome, cargo, time_equipe, data_inicio) VALUES (:n, :c, :t, :d)", 
                                {"n": n_exp, "c": c_exp, "t": t_exp, "d": d_ini})
                    st.success("Cadastrado!"); st.rerun()

    with col_gst:
        st.markdown('<div class="vaga-header">📋 GESTÃO DE AVALIAÇÕES (90 DIAS)</div>', unsafe_allow_html=True)
        df_exp = carregar_dados("controle_experiencia")
        
        if not df_exp.empty:
            for _, r in df_exp.iterrows():
                d90 = r['data_inicio'] + pd.Timedelta(days=90)
                # Status visual no título do expander
                status_texto = "🟢 FINALIZADA" if r['av2_feito'] else "🟡 PENDENTE"
                
                with st.expander(f"{status_texto} | 👤 {r['nome']} | Limite: {d90.strftime('%d/%m/%Y')}"):
                    # --- LINHA 1: CHECKBOX E DATA ---
                    c1, c2 = st.columns(2)
                    with c1:
                        v2 = st.checkbox("Avaliação feita", value=bool(r['av2_feito']), key=f"v2{r['id']}")
                    with c2:
                        dt2 = st.date_input("Data da realização", value=r['av2_data'] if r['av2_data'] else d90, key=f"dt2{r['id']}")
                    
                    # --- LINHA 2: AVALIADOR ---
                    r2 = st.text_input("Avaliador responsável", value=r['av2_responsavel'] or "", key=f"r2{r['id']}", placeholder="Nome do gestor...")
                    
                    st.markdown("---")
                    
                    # --- LINHA 3: BOTÕES LADO A LADO ---
                    col_btn_salvar, col_btn_excluir, col_filler = st.columns([1, 1, 1.5])
                    
                    with col_btn_salvar:
                        if st.button("💾 Salvar Avaliação", key=f"svexp{r['id']}", use_container_width=True):
                            executar_sql("""
                                UPDATE controle_experiencia 
                                SET av2_feito=:v2, av2_responsavel=:r2, av2_data=:dt2 
                                WHERE id=:id
                            """, {"v2": v2, "r2": r2, "dt2": dt2, "id": r['id']})
                            st.success("Alterações salvas!")
                            st.rerun()
                            
                    with col_btn_excluir:
                        if st.button("🗑️ Excluir", key=f"delexp{r['id']}", use_container_width=True):
                            executar_sql("DELETE FROM controle_experiencia WHERE id=:id", {"id": r['id']})
                            st.warning("Registro removido.")
                            st.rerun()
        else:
            st.info("Nenhum registro de experiência encontrado.")

# --- 15. MÓDULO COLABORADORES ---
elif menu == "👥 COLABORADORES":
    st.subheader("Gestão de Benefícios e Contratos")
    df_col = carregar_dados("colaboradores_ativos")
    
    lista_modalidades = ["CLT", "PJ", "Estagiário", "Trainee", "Freelancer"]

    with st.expander("➕ CADASTRAR NOVO COLABORADOR MANUALMENTE"):
        with st.form("f_col_manual"):
            n_col = st.text_input("Nome")
            t_col = st.selectbox("Tipo de Contratação", lista_modalidades)
            d_adm = st.date_input("Data de Admissão", value=date.today())
            if st.form_submit_button("CADASTRAR"):
                executar_sql("INSERT INTO colaboradores_ativos (nome, tipo, data_admissao) VALUES (:n, :t, :d)", 
                            {"n":n_col, "t":t_col, "d":d_adm})
                st.success("Colaborador cadastrado!"); st.rerun()

    if not df_col.empty:
        for _, r in df_col.iterrows():
            with st.expander(f"👤 {r['nome']} [{r['tipo']}]"):
                c_tipo, c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1, 1])
                
                # Permite alterar o tipo de contratação de quem já está na lista
                novo_tipo = c_tipo.selectbox("Alterar Tipo", lista_modalidades, 
                                            index=lista_modalidades.index(r['tipo']) if r['tipo'] in lista_modalidades else 0,
                                            key=f"tipo{r['id']}")
                
                star = c1.checkbox("Starbem", value=bool(r['cad_starbem']), key=f"star{r['id']}")
                amil = c2.checkbox("AMIL", value=bool(r['incl_amil']), key=f"amil{r['id']}")
                ifoo = c3.checkbox("iFood", value=bool(r['ifood_ativo']), key=f"ifoo{r['id']}")
                equi = c4.checkbox("Equipamento", value=bool(r['equipamento_entregue']), key=f"equi{r['id']}")
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("💾 Salvar Alterações", key=f"svb{r['id']}"):
                    executar_sql("""
                        UPDATE colaboradores_ativos 
                        SET tipo=:t, cad_starbem=:s, incl_amil=:a, ifood_ativo=:i, equipamento_entregue=:e 
                        WHERE id=:id
                    """, {"t":novo_tipo, "s":star, "a":amil, "i":ifoo, "e":equi, "id":r['id']})
                    st.success("Dados atualizados!"); st.rerun()
                
                if col_btn2.button("🗑️ Excluir Colaborador", key=f"delcol{r['id']}"):
                    executar_sql("DELETE FROM colaboradores_ativos WHERE id=:id", {"id":r['id']})
                    st.rerun()


































