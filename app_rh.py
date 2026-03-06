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

# --- 3. INICIALIZAÇÃO E REPARO (Blindagem contra erros de ID) ---
def inicializar_banco():
    with engine.connect() as conn:
        # Garante estrutura básica
        conn.execute(text("CREATE TABLE IF NOT EXISTS vagas (id SERIAL PRIMARY KEY, nome_vaga TEXT, area TEXT, status_vaga TEXT, gestor TEXT, data_abertura DATE)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS candidatos (id SERIAL PRIMARY KEY, candidato TEXT, vaga_vinculada TEXT, status_geral TEXT, historico TEXT)"))
        
        # Colunas de Onboarding
        on_cols = {
            "envio_proposta": "BOOLEAN DEFAULT FALSE", "solic_documentos": "BOOLEAN DEFAULT FALSE",
            "solic_contrato": "BOOLEAN DEFAULT FALSE", "solic_acessos": "BOOLEAN DEFAULT FALSE",
            "entrevista_rh": "DATE", "entrevista_gestor": "DATE", "entrevista_cultura": "DATE"
        }
        for col, tipo in on_cols.items():
            try: conn.execute(text(f"ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS {col} {tipo}")); conn.commit()
            except: pass
        conn.commit()

def reparar_banco_id():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE vagas ADD COLUMN IF NOT EXISTS id SERIAL"))
            conn.execute(text("ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS id SERIAL"))
            conn.commit()
            st.success("✅ Banco sincronizado!")
        except:
            st.info("O banco já utiliza identificadores por nome.")

inicializar_banco()

# --- 4. CSS (ESTILO ETUS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
    html, body, [class*="css"], [data-testid="stSidebar"] { font-family: 'Space Grotesk', sans-serif !important; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] p { color: #777777 !important; font-size: 18px !important; }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] input:checked + div p { color: #8DF768 !important; font-weight: 700 !important; }
    .header-rh { font-size: 42px; font-weight: 700; color: #8DF768; margin-bottom: 30px; border-left: 10px solid #151514; padding-left: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. FUNÇÕES DE DADOS ---
def carregar_vagas(): return pd.read_sql("SELECT * FROM vagas ORDER BY nome_vaga", engine)
def carregar_candidatos(): return pd.read_sql("SELECT * FROM candidatos", engine)

# --- 6. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    st.divider()
    menu = st.radio("NAVEGAÇÃO", ["📊 INDICADORES", "🏢 VAGAS", "⚙️ CANDIDATOS", "🚀 ONBOARDING"])

st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- 7. INDICADORES ---
if menu == "📊 INDICADORES":
    df_v = carregar_vagas(); df_c = carregar_candidatos()
    if not df_v.empty:
        hoje = pd.Timestamp(datetime.now().date())
        df_v['data_abertura'] = pd.to_datetime(df_v['data_abertura'])
        v_ativas = df_v[df_v['status_vaga'] == 'Aberta'].copy()
        v_ativas['aging'] = v_ativas['data_abertura'].apply(lambda x: (hoje - x).days)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 VAGAS ABERTAS", len(v_ativas))
        c2.metric("⏱️ AGING MÉDIO", f"{int(v_ativas['aging'].mean()) if not v_ativas.empty else 0} dias")
        c3.metric("👥 CANDIDATOS ATIVOS", len(df_c[df_c['status_geral'] != 'Finalizada']))

        st.subheader("🕒 Tempo de Abertura por Vaga (Aging)")
        st.plotly_chart(px.bar(v_ativas, x='aging', y='nome_vaga', orientation='h', color_discrete_sequence=['#8DF768']), use_container_width=True)

        st.subheader("📊 Distribuição por Etapa (%)")
        df_status = df_c.groupby(['vaga_vinculada', 'status_geral']).size().reset_index(name='qtd')
        fig = px.bar(df_status, y="vaga_vinculada", x="qtd", color="status_geral", orientation='h', barmode="relative")
        fig.update_layout(barnorm='percent'); st.plotly_chart(fig, use_container_width=True)

# --- 8. VAGAS ---
elif menu == "🏢 VAGAS":
    if st.button("🛠️ REPARAR IDs"): reparar_banco_id()
    with st.expander("➕ CADASTRAR NOVA VAGA"):
        with st.form("n_vaga"):
            nv = st.text_input("Nome da Vaga"); gv = st.text_input("Gestor")
            av = st.selectbox("Área", ["Comercial", "Operações", "Tecnologia", "RH", "Marketing"])
            if st.form_submit_button("CRIAR"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO vagas (nome_vaga, area, status_vaga, gestor, data_abertura) VALUES (:n, :a, 'Aberta', :g, :d)"), {"n": nv, "a": av, "g": gv, "d": datetime.now().date()}); conn.commit()
                st.rerun()

    df_v = carregar_vagas()
    for i, row in df_v.iterrows():
        vid = row['id'] if 'id' in row and pd.notnull(row['id']) else f"idx_{i}"
        with st.expander(f"🏢 {row['nome_vaga'].upper()} | {row['status_vaga']}"):
            with st.form(f"ed_v_{vid}"):
                eg = st.text_input("Gestor", value=row['gestor'])
                es = st.selectbox("Status", ["Aberta", "Pausada", "Finalizada"], index=0)
                if st.form_submit_button("💾 SALVAR"):
                    with engine.connect() as conn:
                        if 'id' in row and pd.notnull(row['id']): conn.execute(text("UPDATE vagas SET gestor=:g, status_vaga=:s WHERE id=:id"), {"g": eg, "s": es, "id": row['id']})
                        else: conn.execute(text("UPDATE vagas SET gestor=:g, status_vaga=:s WHERE nome_vaga=:n"), {"g": eg, "s": es, "n": row['nome_vaga']})
                        conn.commit()
                    st.rerun()
            if st.button("🗑️ EXCLUIR VAGA", key=f"del_v_{vid}"):
                with engine.connect() as conn:
                    if 'id' in row and pd.notnull(row['id']): conn.execute(text("DELETE FROM vagas WHERE id=:id"), {"id": row['id']})
                    else: conn.execute(text("DELETE FROM vagas WHERE nome_vaga=:n"), {"n": row['nome_vaga']})
                    conn.commit()
                st.rerun()

# --- 9. CANDIDATOS (AGRUPADOS POR VAGA) ---
elif menu == "⚙️ CANDIDATOS":
    df_vagas = carregar_vagas()
    df_c = carregar_candidatos()
    
    # --- FORMULÁRIO DE ADIÇÃO ---
    with st.expander("➕ ADICIONAR NOVO CANDIDATO"):
        with st.form("add_c", clear_on_submit=True):
            cn = st.text_input("Nome do Candidato")
            # Só permite selecionar vagas que existem
            lista_vagas = df_vagas["nome_vaga"].tolist() if not df_vagas.empty else ["Nenhuma vaga cadastrada"]
            cv = st.selectbox("Vincular à Vaga", lista_vagas)
            
            if st.form_submit_button("CADASTRAR"):
                if cn and cv != "Nenhuma vaga cadastrada":
                    with engine.connect() as conn:
                        h = f"➔ {datetime.now().strftime('%d/%m/%Y')}: Cadastro inicial na Triagem"
                        conn.execute(text("INSERT INTO candidatos (candidato, vaga_vinculada, status_geral, historico) VALUES (:n, :v, 'Triagem', :h)"), 
                                     {"n": cn, "v": cv, "h": h})
                        conn.commit()
                    st.success(f"{cn} adicionado à vaga {cv}!")
                    st.rerun()
                else:
                    st.error("Preencha o nome e selecione uma vaga válida.")

    st.divider()

    # --- LISTAGEM AGRUPADA POR VAGA ---
    st.subheader("👥 Gestão por Processo Seletivo")
    
    if df_vagas.empty:
        st.info("Nenhuma vaga cadastrada. Crie uma vaga primeiro na aba '🏢 VAGAS'.")
    elif df_c.empty:
        st.info("Nenhum candidato cadastrado ainda.")
    else:
        # Loop pelas vagas para criar os agrupamentos
        for _, vaga in df_vagas.iterrows():
            nome_v = vaga['nome_vaga']
            # Filtra candidatos desta vaga específica
            cands_vaga = df_c[df_c['vaga_vinculada'] == nome_v]
            
            # Só exibe a seção da vaga se houver candidatos ou se você quiser ver todas
            count_cands = len(cands_vaga)
            
            # Título da Vaga com contador
            with st.container():
                st.markdown(f"#### 📁 Vaga: {nome_v.upper()} ({count_cands})")
                
                if count_cands == 0:
                    st.caption("Nenhum candidato nesta vaga.")
                else:
                    # Exibe os candidatos daquela vaga
                    for i, cand in cands_vaga.iterrows():
                        cid = cand['id'] if 'id' in cand and pd.notnull(cand['id']) else f"cidx_{i}"
                        
                        # Expander individual do candidato dentro da seção da vaga
                        with st.expander(f"👤 {cand['candidato'].upper()} | Etapa: {cand['status_geral']}"):
                            col_st, col_del = st.columns([3, 1])
                            
                            # Atualização de Status
                            etapas = ["Triagem", "Entrevista RH", "teste técnico", "Entrevista gestor", "Entrevista Cultura", "Finalizada"]
                            idx_atual = etapas.index(cand['status_geral']) if cand['status_geral'] in etapas else 0
                            
                            novo_st = col_st.selectbox("Mover para:", etapas, index=idx_atual, key=f"sel_{cid}")
                            
                            if col_st.button("💾 ATUALIZAR STATUS", key=f"btn_sv_{cid}"):
                                with engine.connect() as conn:
                                    novo_h = f"➔ {datetime.now().strftime('%d/%m/%Y')}: Movido para {novo_st}\n" + (cand['historico'] or "")
                                    if 'id' in cand and pd.notnull(cand['id']):
                                        conn.execute(text("UPDATE candidatos SET status_geral=:s, historico=:h WHERE id=:id"), {"s": novo_st, "h": novo_h, "id": cand['id']})
                                    else:
                                        conn.execute(text("UPDATE candidatos SET status_geral=:s, historico=:h WHERE candidato=:n AND vaga_vinculada=:v"), {"s": novo_st, "h": novo_h, "n": cand['candidato'], "v": nome_v})
                                    conn.commit()
                                st.rerun()
                            
                            # Exclusão
                            if col_del.button("🗑️ EXCLUIR", key=f"btn_del_{cid}", use_container_width=True):
                                with engine.connect() as conn:
                                    if 'id' in cand and pd.notnull(cand['id']):
                                        conn.execute(text("DELETE FROM candidatos WHERE id=:id"), {"id": cand['id']})
                                    else:
                                        conn.execute(text("DELETE FROM candidatos WHERE candidato=:n AND vaga_vinculada=:v"), {"n": cand['candidato'], "v": nome_v})
                                    conn.commit()
                                st.rerun()
                            
                            # Exibição do Histórico
                            if cand['historico']:
                                st.divider()
                                st.caption("📜 Histórico de movimentações:")
                                st.text(cand['historico'])
                st.markdown("---") # Linha separadora entre vagas

# --- 10. ONBOARDING (RESTAURADO) ---
elif menu == "🚀 ONBOARDING":
    df_ap = pd.read_sql("SELECT * FROM candidatos WHERE status_geral = 'Finalizada'", engine)
    if not df_ap.empty:
        sel = st.selectbox("Selecione o Novo Colaborador:", df_ap["candidato"].tolist())
        c_data = df_ap[df_ap["candidato"] == sel].iloc[0]
        
        st.markdown(f"### 📋 Checklist de Onboarding: {sel}")
        checks = {"Envio Proposta": "envio_proposta", "Documentos": "solic_documentos", "Contrato": "solic_contrato", "Acessos": "solic_acessos"}
        
        novos_on = {}
        c_on1, c_on2 = st.columns(2)
        for i, (label, db_col) in enumerate(checks.items()):
            col_target = c_on1 if i < 2 else c_on2
            novos_on[db_col] = col_target.checkbox(label, value=bool(c_data.get(db_col, False)), key=f"on_{c_data.get('id', i)}_{db_col}")
        
        if st.button("💾 SALVAR ONBOARDING", use_container_width=True):
            with engine.connect() as conn:
                sets = ", ".join([f"{k}=:{k}" for k in novos_on.keys()])
                # Identifica por ID ou Nome para segurança
                if 'id' in c_data and pd.notnull(c_data['id']):
                    conn.execute(text(f"UPDATE candidatos SET {sets} WHERE id=:id"), {**novos_on, "id": c_data["id"]})
                else:
                    conn.execute(text(f"UPDATE candidatos SET {sets} WHERE candidato=:n"), {**novos_on, "n": sel})
                conn.commit()
            st.success("Progresso salvo!"); st.rerun()
    else:
        st.info("💡 Mova candidatos para o status 'Finalizada' para iniciar o Onboarding.")


