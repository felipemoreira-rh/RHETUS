import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

def enviar_email_foto(email_candidato, nome_candidato):
  
    meu_email = "seu_email@gmail.com"
    minha_senha = st.secrets["email"]["password"] 
    
    msg = MIMEMultipart()
    msg['Subject'] = f"Boas-vindas Etus! 🚀 - Foto e Curiosidades de {nome_candidato}"
    msg['From'] = meu_email
    msg['To'] = email_candidato

    corpo = f"""
    <html>
    <body>
        <p>Olá, <strong>{nome_candidato}</strong>!</p>
        <p>Parabéns pela sua aprovação em nosso processo seletivo! 🎉<br>
        Agora, gostaríamos de conhecer um pouco mais sobre você.</p>
        <p>Por isso, pedimos que nos envie através do formulário abaixo:</p>
        <ul>
            <li>Uma foto sua, conforme as orientações;</li>
            <li>Três curiosidades sobre você (hobby, talento, mania, lugar favorito...);</li>
        </ul>
        <p>Essas informações serão usadas na sua apresentação à equipe. 😄<br>
        <strong>Contamos com seu envio até 22/01/2026.</strong></p>
        <p>🎯 <strong>Orientações para a foto:</strong><br>
        - Foto do peito para cima;<br>
        - Fundo neutro (parede branca, cinza ou clara);<br>
        - Corpo reto e olhando para frente;<br>
        - De preferência sorrindo;<br>
        - Evite bonés, óculos escuros ou filtros.</p>
        <p>👉 <strong>Gentileza preencher:</strong> <a href='https://docs.google.com/forms/d/e/1FAIpQLSd1o4x5jALKryUJraNB7GZB6xyJXJj5nRTs30dw_0ZFoVf9KQ/viewform'>Formulário de Apresentação</a></p>
        <br>
    </body>
    </html>
    """
    msg.attach(MIMEText(corpo, 'html'))

   
    try:
        with open("orientacao_foto.jpg", 'rb') as f:
            img = MIMEImage(f.read())
            img.add_header('Content-Disposition', 'attachment', filename="orientacao_foto.jpg")
            msg.attach(img)
    except:
        pass 

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(meu_email, minha_senha)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Erro ao enviar: {e}")
        return False
        
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
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

# --- 3. FUNÇÕES DE APOIO E AUTOMAÇÃO ---
def executar_sql(query, params=None):
    try:
        with engine.begin() as conn:
            conn.execute(text(query), params or {})
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro SQL: {e}")
        return False

# --- FUNÇÃO DE ENVIO DE E-MAIL (ONBOARDING) ---
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

def enviar_email_foto(email_candidato, nome_candidato):
    try:
        meu_email = "seu_email@gmail.com"  
        minha_senha = st.secrets["email"]["password"] 
        
        msg = MIMEMultipart()
        msg['Subject'] = f"Boas-vindas Etus! 🚀 - Foto e Curiosidades de {nome_candidato}"
        msg['From'] = meu_email
        msg['To'] = email_candidato

        corpo = f"""
        <html>
        <body style="font-family: sans-serif;">
            <p>Olá, <strong>{nome_candidato}</strong>!</p>
            <p>Parabéns pela sua aprovação em nosso processo seletivo! 🎉<br>
            Agora, gostaríamos de conhecer um pouco mais sobre você.</p>
            <p>Por isso, pedimos que nos envie:</p>
            <ul>
                <li>Uma foto sua, conforme as orientações abaixo;</li>
                <li>Três curiosidades sobre você (vale hobby, talento, mania, lugar favorito, algo inusitado…);</li>
            </ul>
            <p>Essas informações serão usadas na sua apresentação à equipe. 😄<br>
            <strong>Contamos com seu envio até 22/01/2026.</strong></p>
            <p>🎯 <strong>Orientações para a foto:</strong><br>
            - Foto do peito para cima;<br>
            - Fundo neutro (parede branca, cinza ou clara);<br>
            - Corpo reto e olhando para frente;<br>
            - De preferência sorrindo;<br>
            - Evite bonés, óculos escuros ou filtros.</p>
            <p>👉 <strong>Gentileza preencher:</strong> <a href='https://docs.google.com/forms/d/e/1FAIpQLSd1o4x5jALKryUJraNB7GZB6xyJXJj5nRTs30dw_0ZFoVf9KQ/viewform?usp=sf_link'>Link do Formulário</a></p>
        </body>
        </html>
        """
        msg.attach(MIMEText(corpo, 'html'))

       
        if os.path.exists("orientacao_foto.jpg"):
            with open("orientacao_foto.jpg", 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-Disposition', 'attachment', filename="orientacao_foto.jpg")
                msg.attach(img)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(meu_email, minha_senha)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False

@st.cache_data(ttl=1)
def carregar_dados(tabela):
    try:
        with engine.connect() as conn:
            return pd.read_sql(text(f"SELECT * FROM {tabela} ORDER BY id DESC"), conn)
    except:
        return pd.DataFrame()

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
        "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS email TEXT;"
        "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS email TEXT;",
        "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS foto_curiosidades BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS data_foto_curiosidades DATE;"
        "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS indicado_por TEXT;",
    "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS valor_bonus REAL DEFAULT 0.0;"
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
if menu == "📊 INDICADORES":
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

# --- 8. MÓDULO CANDIDATOS (EDIÇÃO CORRIGIDA) ---
elif menu == "⚙️ CANDIDATOS":
    st.markdown("### 👥 Gestão de Candidatos")
    
    df_v = carregar_dados("vagas")
    df_c = carregar_dados("candidatos")
    
    # 1. FORMULÁRIO DE NOVO CADASTRO (Expander Único)
    with st.expander("➕ CADASTRAR NOVO CANDIDATO"):
        with st.form("form_novo_cand_unico", clear_on_submit=True):
            c1, c2 = st.columns(2)
            n_novo = c1.text_input("Nome*")
            e_novo = c2.text_input("E-mail*")
            
            v_list = df_v['nome_vaga'].tolist() if not df_v.empty else ["Geral"]
            v_sel = c1.selectbox("Vaga Vinculada", v_list)
            
            st.divider()
            st.markdown("🎁 **Bônus de Indicação**")
            col_ind1, col_ind2 = st.columns(2)
            ind_novo = col_ind1.text_input("Quem indicou?")
            val_novo = col_ind2.number_input("Valor Bônus (R$)", min_value=0.0, step=50.0, value=0.0)
            
            if st.form_submit_button("💾 SALVAR NOVO CANDIDATO"):
                if n_novo and e_novo:
                    sql_ins = """
                        INSERT INTO candidatos (candidato, email, vaga_vinculada, status_geral, indicado_por, valor_bonus) 
                        VALUES (:n, :e, :v, 'Triagem', :i, :val)
                    """
                    executar_sql(sql_ins, {"n": n_novo, "e": e_novo, "v": vaga_sel, "i": ind_novo, "val": val_novo})
                    st.success(f"Candidato {n_novo} cadastrado!")
                    st.rerun()
                else:
                    st.error("Preencha os campos obrigatórios (*)")

    st.divider()

    # 2. LISTAGEM AGRUPADA POR VAGA (Apenas uma vez)
    if not df_c.empty:
        busca = st.text_input("🔍 Buscar candidato pelo nome...", placeholder="Digite para filtrar...")
        df_base = df_c[df_c['candidato'].str.contains(busca, case=False)] if busca else df_c
        
        vagas_com_candidatos = sorted(df_base['vaga_vinculada'].unique().tolist())
        
        if not vagas_com_candidatos:
            st.warning("Nenhum candidato encontrado.")
        else:
            abas = st.tabs(vagas_com_candidatos)
            
            for i, vaga_nome in enumerate(vagas_com_candidatos):
                with abas[i]:
                    df_vaga = df_base[df_base['vaga_vinculada'] == vaga_nome]
                    st.caption(f"📌 {len(df_vaga)} candidato(s) nesta vaga")
                    
                    for _, cand in df_vaga.iterrows():
                        st_atual = cand['status_geral']
                        icone = "🔵" if st_atual == 'Triagem' else "🟢" if st_atual == 'Finalizada' else "🟡"
                        
                        with st.expander(f"{icone} {cand['candidato'].upper()}"):
                            edit_mode = st.toggle("🔓 Liberar Edição", key=f"tog_ed_{cand['id']}")
                            
                            with st.form(key=f"edit_form_final_{cand['id']}"):
                                col1, col2 = st.columns(2)
                                
                                edit_nome = col1.text_input("Nome", value=cand['candidato'], disabled=not edit_mode)
                                edit_email = col2.text_input("E-mail", value=cand.get('email', ''), disabled=not edit_mode)
                                
                                idx_v = v_list.index(cand['vaga_vinculada']) if cand['vaga_vinculada'] in v_list else 0
                                edit_vaga = col1.selectbox("Vaga", v_list, index=idx_v, disabled=not edit_mode)
                                
                                st_opts = ["Triagem", "Entrevista RH", "Teste Técnico", "Entrevista Gestor", "Aprovado", "Finalizada", "Reprovado"]
                                idx_s = st_opts.index(st_atual) if st_atual in st_opts else 0
                                edit_status = col2.selectbox("Status", st_opts, index=idx_s, disabled=not edit_mode)
                                
                                edit_ind = col1.text_input("Indicado por", value=cand.get('indicado_por', ''), disabled=not edit_mode)
                                edit_val = col2.number_input("Valor Bônus", value=float(cand.get('valor_bonus', 0)), disabled=not edit_mode)

                                b_salvar = st.form_submit_button("💾 SALVAR ALTERAÇÕES", use_container_width=True, disabled=not edit_mode)
                                b_excluir = st.form_submit_button("🗑️ EXCLUIR CANDIDATO", use_container_width=True)

                                if b_salvar and edit_mode:
                                    sql_up = """
                                        UPDATE candidatos SET 
                                        candidato=:n, email=:e, vaga_vinculada=:v, 
                                        status_geral=:s, indicado_por=:i, valor_bonus=:val 
                                        WHERE id=:id
                                    """
                                    executar_sql(sql_up, {"n": edit_nome, "e": edit_email, "v": edit_vaga, "s": edit_status, "i": edit_ind, "val": edit_val, "id": cand['id']})
                                    st.success("Atualizado!")
                                    st.rerun()
                                    
                                if b_excluir:
                                    executar_sql("DELETE FROM candidatos WHERE id=:id", {"id": cand['id']})
                                    st.rerun()
    else:
        st.info("Nenhum candidato cadastrado.")

# --- 9. MÓDULO ONBOARDING (COM CHAVE DE DESBLOQUEIO) ---
elif menu == "🚀 ONBOARDING":
    st.markdown("### 🚀 Gestão de Onboarding")
    df_c = carregar_dados("candidatos")
    
    if not df_c.empty:
        df_onboarding = df_c[df_c['status_geral'] == 'Finalizada']
    else:
        df_onboarding = pd.DataFrame()

    if not df_onboarding.empty:
        for _, row in df_onboarding.iterrows():
            with st.expander(f"👤 {row['candidato']} - {row['vaga_vinculada']}"):
                
                # --- ALERTA DE BÔNUS (90 DIAS) ---
                indicador = row.get('indicado_por')
                valor = row.get('valor_bonus', 0)
                data_inicio = row.get('data_inicio')

                if indicador and valor > 0 and data_inicio:
                    dt_inicio = pd.to_datetime(data_inicio).date()
                    data_pagamento_bonus = dt_inicio + timedelta(days=90)
                    dias_restantes = (data_pagamento_bonus - date.today()).days

                    if dias_restantes <= 90:
                        status_bonus = "🔴 VENCIDO" if dias_restantes <= 0 else f"⏳ EM {dias_restantes} DIAS"
                        st.warning(f"💰 **BÔNUS:** {indicador} recebe R$ {valor:.2f} em {data_pagamento_bonus.strftime('%d/%m/%Y')} ({status_bonus})")

                # --- CHAVE DE DESBLOQUEIO ---
                # Esta chave permite que você edite os campos que estavam travados
                liberar_edicao = st.toggle("🔓 Liberar Edição do Checklist", key=f"lib_onb_{row['id']}")

                with st.form(key=f"onb_f_final_unlock_{row['id']}"):
                    st.markdown("**📅 Planejamento de Entrada**")
                    d_ini_val = pd.to_datetime(row['data_inicio']).date() if row.get('data_inicio') else date.today()
                    v_ini = st.date_input("Data Prevista de Início", value=d_ini_val, key=f"d_in_{row['id']}")
                    
                    st.divider()
                    st.markdown("**📝 Checklist de Integração**")
                    col1, col2 = st.columns(2)
                    
                    # Lógica de travas baseada na chave "liberar_edicao"
                    ja_enviou_email = bool(row.get('foto_curiosidades'))
                    ja_recebeu_foto = row.get('data_foto_curiosidades') is not None

                    with col1:
                        c_prop = st.checkbox("Envio de Proposta", value=bool(row.get('envio_proposta')), key=f"c_pr_{row['id']}")
                        c_doc = st.checkbox("Solicitação de Documentos", value=bool(row.get('solic_documentos')), key=f"c_dc_{row['id']}")
                        
                        # Travado APENAS se já foi enviado E a chave de liberação estiver desligada
                        c_foto_email = st.checkbox("Disparar E-mail (Foto/Curiosidades)", 
                                             value=ja_enviou_email, 
                                             disabled=(ja_enviou_email and not liberar_edicao), 
                                             key=f"c_ft_mail_{row['id']}")
                    
                    with col2:
                        c_cont = st.checkbox("Assinatura de Contrato", value=bool(row.get('solic_contrato')), key=f"c_ct_{row['id']}")
                        c_acess = st.checkbox("Acessos e Equipamentos", value=bool(row.get('solic_acessos')), key=f"c_ac_{row['id']}")
                        
                        # Travado APENAS se já houver data E a chave de liberação estiver desligada
                        c_foto_concluido = st.checkbox("Envio de foto e curiosidade", 
                                                      value=ja_recebeu_foto, 
                                                      disabled=(ja_recebeu_foto and not liberar_edicao), 
                                                      key=f"c_ft_chk_{row['id']}")

                    if st.form_submit_button("💾 GRAVAR PROGRESSO", use_container_width=True):
                        # Lógica de E-mail: Dispara apenas se o e-mail não tivesse sido enviado antes
                        if c_foto_email and not ja_enviou_email:
                            if row.get('email'):
                                if enviar_email_foto(row['email'], row['candidato']):
                                    st.toast("📧 E-mail enviado!", icon="✅")
                            else:
                                st.error("Candidato sem e-mail.")

                        # Tratamento da data para o SQL
                        if c_foto_concluido:
                            # Se já tinha data, mantém. Se não tinha e marcou agora, põe HOJE.
                            valor_data_foto = row.get('data_foto_curiosidades') if ja_recebeu_foto else date.today()
                        else:
                            # Se desmarcou (usando a chave de liberação), volta para nulo
                            valor_data_foto = None

                        params_save = {
                            "di": v_ini, "cp": c_prop, "cd": c_doc,
                            "cf": c_foto_email, "dfc": valor_data_foto,
                            "cc": c_cont, "ca": c_acess, "id": row['id']
                        }
                        
                        sql_up = """
                            UPDATE candidatos SET 
                            data_inicio=:di, envio_proposta=:cp, solic_documentos=:cd,
                            foto_curiosidades=:cf, data_foto_curiosidades=:dfc,
                            solic_contrato=:cc, solic_acessos=:ca
                            WHERE id=:id
                        """
                        if executar_sql(sql_up, params_save):
                            st.success("Dados salvos!")
                            st.rerun()
    else:
        st.info("Nenhum onboarding pendente.")
      
# --- 10. MÓDULO DASHBOARD DP (ATUALIZADO COM % DE CONTRATO) ---
elif menu == "📊 DASHBOARD DP":
    st.subheader("Indicadores de Departamento Pessoal")
    
    # CARREGAMENTO DE DADOS
    df_col = carregar_dados("colaboradores_ativos")
    df_est = carregar_dados("contratos_estagio")
    df_exp = carregar_dados("controle_experiencia")
    df_c = carregar_dados("candidatos") 

    if not df_col.empty or not df_est.empty:
        # --- MÉTRICAS DE TOPO ---
        c1, c2, c3, c4 = st.columns(4)
        total_clt = len(df_col[df_col['tipo'] == 'CLT']) if not df_col.empty else 0
        total_pj = len(df_col[df_col['tipo'] == 'PJ']) if not df_col.empty else 0
        total_est = len(df_est) if not df_est.empty else 0
        
        c1.metric("👥 TOTAL ATIVOS", (len(df_col) if not df_col.empty else 0) + total_est)
        c2.metric("📄 CLT", total_clt)
        c3.metric("🤝 PJ", total_pj)
        c4.metric("🎓 ESTAGIÁRIOS", total_est)

        st.divider()

        # --- GRÁFICOS DE DISTRIBUIÇÃO ---
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("Distribuição por Vínculo")
            fig_vinculo = px.pie(values=[total_clt, total_pj, total_est], names=['CLT', 'PJ', 'Estágio'],
                                hole=0.4, color_discrete_sequence=['#8DF768', '#00d4ff', '#ffeb3b'])
            st.plotly_chart(fig_vinculo, use_container_width=True)
        with col_g2:
            st.subheader("Estagiários por Time")
            if not df_est.empty:
                fig_est_bar = px.bar(df_est, x='time_equipe', color='time_equipe', title="Quantidade por Área")
                st.plotly_chart(fig_est_bar, use_container_width=True)

        # --- EVOLUÇÃO TEMPORAL ---
        st.divider()
        st.subheader("📈 Evolução de Contratos de Estágio")
        if not df_est.empty and 'data_inicio' in df_est.columns:
            df_est_timeline = df_est.copy()
            df_est_timeline['data_inicio'] = pd.to_datetime(df_est_timeline['data_inicio'])
            df_counts = df_est_timeline.groupby(df_est_timeline['data_inicio'].dt.to_period('M')).size().reset_index(name='Quantidade')
            df_counts['Mês/Ano'] = df_counts['data_inicio'].astype(str)
            fig_evolucao = px.line(df_counts, x='Mês/Ano', y='Quantidade', markers=True, line_shape="spline", color_discrete_sequence=['#8DF768'])
            st.plotly_chart(fig_evolucao, use_container_width=True)

        # --- NOVO: % DE CUMPRIMENTO DO CONTRATO ---
        st.divider()
        st.subheader("⏳ Progresso dos Contratos de Estágio")
        if not df_est.empty:
            df_prog = df_est.copy()
            hoje = date.today()
            
            def calcular_perc(row):
                try:
                    inicio = pd.to_datetime(row['data_inicio']).date()
                    fim = pd.to_datetime(row['data_fim']).date()
                    total = (fim - inicio).days
                    passado = (hoje - inicio).days
                    if total <= 0: return 100.0
                    return min(max(float(passado / total * 100), 0.0), 100.0)
                except: return 0.0

            df_prog['% Cumprido'] = df_prog.apply(calcular_perc, axis=1)
            df_prog = df_prog.sort_values('% Cumprido', ascending=True)

            fig_prog = px.bar(
                df_prog, 
                x='% Cumprido', 
                y='estagiario', 
                orientation='h',
                text='% Cumprido',
                color='% Cumprido',
                color_continuous_scale='RdYlGn_r', # Inverte: verde no início, vermelho no fim
                range_x=[0, 100]
            )
            fig_prog.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            st.plotly_chart(fig_prog, use_container_width=True)
        else:
            st.info("Sem dados de vigência para calcular o progresso.")

        # --- PAINEL DE ALERTAS ---
        st.divider()
        st.markdown('<div class="vaga-header">⚠️ PAINEL DE ALERTAS E PENDÊNCIAS</div>', unsafe_allow_html=True)
        col_a1, col_a2 = st.columns(2)
        hoje_dt = date.today()

        with col_a1:
            st.markdown("##### ⏳ Avaliações de 90 dias (Próximos 7 dias)")
            alertas_exp = []
            if not df_exp.empty:
                for _, r in df_exp.iterrows():
                    if r['data_inicio']:
                        d90 = pd.to_datetime(r['data_inicio']).date() + timedelta(days=90)
                        if not r.get('av2_feito') and (d90 - hoje_dt).days <= 7:
                            alertas_exp.append(f"🟠 **{r['nome']}**: Vencimento em {d90.strftime('%d/%m/%Y')}")
            if alertas_exp:
                for a in alertas_exp: st.warning(a)
            else: st.success("Nenhuma avaliação de 90 dias pendente.")

        with col_a2:
            st.markdown("##### 💰 Bônus de Indicação (Pós 90 dias)")
            avisos_pagamento = []
            if not df_c.empty:
                contratados_ind = df_c[(df_c['status_geral'] == 'Finalizada') & (df_c['indicado_por'].notnull())]
                for _, cand in contratados_ind.iterrows():
                    if cand['data_inicio']:
                        data_liberacao = pd.to_datetime(cand['data_inicio']).date() + timedelta(days=90)
                        if hoje_dt >= data_liberacao:
                            avisos_pagamento.append(f"✅ **Liberado**: {cand['indicado_por']} (Indicação de {cand['candidato']})")
            if avisos_pagamento:
                for aviso in avisos_pagamento: st.info(aviso)
            else: st.success("Sem bônus pendentes de liberação.")
    else:
        st.info("Nenhum dado de colaborador ou estagiário encontrado.")
        
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
    
    with st.expander("➕ LANÇAR NOVO PAGAMENTO", expanded=True):
        with st.form("form_pg_geral"):
            c1, c2 = st.columns(2)
            epg = epg = st.selectbox("Empresa", ["Plusdin São Bernardo", "Projeto Consegui Aprender"], key="pg_e_new")
            mpg = c2.selectbox("Mês de Referência", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"], key="pg_m_new")
            
            c3, c4 = st.columns([1, 2])
            val_pg = c3.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f")
            motivo_pg = c4.text_input("Motivo do Pagamento (Ex: Internet, Aluguel)")

            c5, c6 = st.columns(2)
            d_envio = c5.date_input("Data de Envio", value=date.today())
            d_pago = c6.date_input("Data de Pagamento", value=date.today())

            upg = st.file_uploader("Comprovante (PDF)", type=["pdf"], key="pg_u_new")
            
            if st.form_submit_button("REGISTRAR PAGAMENTO"):
                if upg:
                    executar_sql("""
                        INSERT INTO pagamentos_gerais 
                        (empresa, categoria, mes_referencia, arquivo_pg, nome_arquivo, data_upload, valor_pg, data_envio, data_pagamento, motivo) 
                        VALUES (:e, 'Geral', :m, :a, :n, :d, :v, :de, :dp, :mo)
                    """, {"e":epg, "m":mpg, "a":upg.read(), "n":upg.name, "d":date.today(), "v":val_pg, "de":d_envio, "dp":d_pago, "mo":motivo_pg})
                    st.success("Pagamento registrado!")
                    st.rerun()

    st.markdown("### 🔍 Histórico de Pagamentos")
    df_pg = carregar_dados("pagamentos_gerais")
    if not df_pg.empty:
        f_emp = st.multiselect("Filtrar Empresa", df_pg['empresa'].unique(), default=df_pg['empresa'].unique())
        df_filtered = df_pg[df_pg['empresa'].isin(f_emp)]
        
        for _, row in df_filtered.iterrows():
            valor = row.get('valor_pg', 0)
            with st.expander(f"💰 R$ {valor:,.2f} | {row['empresa']} - {row.get('motivo', 'S/M')}"):
                col_b1, col_b2 = st.columns(2)
                col_b1.download_button("📥 Baixar Comprovante", row['arquivo_pg'], row['nome_arquivo'], key=f"dl_pg_{row['id']}")
                if col_b2.button(f"🗑️ Excluir Registro", key=f"del_pg_{row['id']}"):
                    executar_sql("DELETE FROM pagamentos_gerais WHERE id=:id", {"id":row['id']})
                    st.rerun()

# --- 14. MÓDULO DASHBOARD FINANCEIRO ---
elif menu == "📊 DASHBOARD FINANCEIRO":
    st.subheader("Análise de Custos e Notas")
    
    df_pg = carregar_dados("pagamentos_gerais")
    df_if = carregar_dados("notas_fiscais_ifood")
    
    if not df_pg.empty:
        total_acumulado = df_pg['valor_pg'].sum()
        qtd_pagamentos = len(df_pg)
        qtd_ifood = len(df_if)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Gasto Total", f"R$ {total_acumulado:,.2f}")
        m2.metric("Qtd. Pagamentos", f"{qtd_pagamentos} registros")
        m3.metric("Notas iFood", f"{qtd_ifood} docs")

        st.divider()
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("**💰 Gastos por Empresa**")
            gastos_emp = df_pg.groupby('empresa')['valor_pg'].sum().reset_index()
            fig_emp = px.pie(gastos_emp, values='valor_pg', names='empresa', hole=0.4, 
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_emp, use_container_width=True)
            
        with col_g2:
            st.markdown("**📅 Gastos por Mês de Referência**")
            gastos_mes = df_pg.groupby('mes_referencia')['valor_pg'].sum().reset_index()
            meses_ordem = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
            gastos_mes['mes_referencia'] = pd.Categorical(gastos_mes['mes_referencia'], categories=meses_ordem, ordered=True)
            gastos_mes = gastos_mes.sort_values('mes_referencia')
            
            fig_mes = px.line(gastos_mes, x='mes_referencia', y='valor_pg', markers=True, line_shape="spline")
            fig_mes.update_traces(line_color='#8DF768')
            st.plotly_chart(fig_mes, use_container_width=True)

        st.markdown("**📑 Ranking de Maiores Despesas**")
        ranking = df_pg.nlargest(5, 'valor_pg')[['empresa', 'motivo', 'valor_pg', 'mes_referencia']]
        st.table(ranking.style.format({"valor_pg": "R$ {:,.2f}"}))
    else:
        st.info("Aguardando dados para gerar indicadores financeiros.")
        
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
                status_texto = "🟢 FINALIZADA" if r['av2_feito'] else "🟡 PENDENTE"
                
                with st.expander(f"{status_texto} | 👤 {r['nome']} | Limite: {d90.strftime('%d/%m/%Y')}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        v2 = st.checkbox("Avaliação feita", value=bool(r['av2_feito']), key=f"v2{r['id']}")
                    with c2:
                        dt2 = st.date_input("Data da realização", value=r['av2_data'] if r['av2_data'] else d90, key=f"dt2{r['id']}")
                    
                    r2 = st.text_input("Avaliador responsável", value=r['av2_responsavel'] or "", key=f"r2{r['id']}", placeholder="Nome do gestor...")
                    
                    st.markdown("---")
                    
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







































