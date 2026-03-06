import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="RH ETUS - Media Holding", layout="wide", page_icon="🟢")

# --- 2. CSS IDENTIDADE ETUS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #3A3A3A !important; border-right: 1px solid #4A4A4A !important; }
    div[data-testid="stSidebar"] div.stRadio div[role="radiogroup"] label {
        background-color: #4A4A4A !important; border: 1px solid #5A5A5A !important;
        border-radius: 10px !important; padding: 18px !important; transition: all 0.3s ease-in-out !important;
    }
    div[data-testid="stSidebar"] div.stRadio div[role="radiogroup"] [data-checked="true"] + div label {
        background-color: #8DF768 !important; border: none !important;
    }
    .header-rh { font-size: 48px; font-weight: 700; color: #8DF768; border-left: 15px solid #151514; padding-left: 20px; text-transform: uppercase; }
    .stButton>button[kind="secondary"] { color: #ff4b4b !important; border-color: #ff4b4b !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LÓGICA DE DADOS ---
NOME_ARQUIVO = "gestao_rh_completa.xlsx"

def carregar_dados(aba):
    colunas_oficiais = [
        "Candidato", "Vaga Vinculada", "Status Geral", "Entrevista RH", 
        "Entrevista Gestor", "Teste Técnico", "Solicitar Doc", 
        "Foto/Curiosidade", "Contrato", "Equipamentos", 
        "Cadastro RH Gestor", "Data Inicio", "Aprovação Final"
    ]
    
    if os.path.exists(NOME_ARQUIVO):
        try:
            with pd.ExcelFile(NOME_ARQUIVO) as xls:
                if aba in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=aba)
                    if aba == "Candidatos":
                        # Limpeza de colunas fantasmas
                        col_del = ["Doc. Solicitada", "Foto/Curiosidades", "Contrato Solicitado", "Equip/Acessos Solicitados"]
                        df = df.drop(columns=[c for c in col_del if c in df.columns], errors='ignore')
                        
                        for col in colunas_oficiais:
                            if col not in df.columns:
                                df[col] = False if any(x in col for x in ["Doc", "Contrato", "Foto", "Equip", "Cad"]) else None
                        
                        datas = ["Entrevista RH", "Entrevista Gestor", "Data Inicio"]
                        for col in datas:
                            if col in df.columns:
                                df[col] = pd.to_datetime(df[col]).dt.date
                        return df[[c for c in colunas_oficiais if c in df.columns]]
            return pd.read_excel(NOME_ARQUIVO, sheet_name=aba)
        except: return criar_df_vazio(aba)
    return criar_df_vazio(aba)

def criar_df_vazio(aba):
    if aba == "Vagas":
        return pd.DataFrame(columns=["Nome da Vaga", "Área", "Status Vaga"])
    return pd.DataFrame(columns=[
        "Candidato", "Vaga Vinculada", "Status Geral", "Entrevista RH", 
        "Entrevista Gestor", "Teste Técnico", "Solicitar Doc", 
        "Foto/Curiosidade", "Contrato", "Equipamentos", 
        "Cadastro RH Gestor", "Data Inicio", "Aprovação Final"
    ])

def salvar_tudo():
    with pd.ExcelWriter(NOME_ARQUIVO, engine='openpyxl') as writer:
        st.session_state.vagas.to_excel(writer, sheet_name="Vagas", index=False)
        st.session_state.candidatos.to_excel(writer, sheet_name="Candidatos", index=False)

if 'vagas' not in st.session_state: st.session_state.vagas = carregar_dados("Vagas")
if 'candidatos' not in st.session_state: st.session_state.candidatos = carregar_dados("Candidatos")

# --- 4. SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    menu = st.radio("", ["📊 DASHBOARD", "🏢 VAGAS", "⚙️ FLUXO"], label_visibility="collapsed")
    st.divider()

# --- 5. CABEÇALHO ---
st.markdown('<div class="header-rh">RH ETUS</div>', unsafe_allow_html=True)

# --- 6. CONTEÚDO ---

# --- RECURSO: DASHBOARD RESTAURADO ---
if menu == "📊 DASHBOARD":
    df = st.session_state.candidatos
    
    if not df.empty:
        st.markdown("<style>[data-testid='stMetricValue'] { color: #8DF768 !important; font-size: 38px !important; }</style>", unsafe_allow_html=True)
        
        # Métricas Principais
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📌 TOTAL NO FUNIL", len(df))
        
        aprovados = len(df[df["Aprovação Final"] == "Sim"]) if "Aprovação Final" in df.columns else 0
        m2.metric("✅ CONTRATADOS", aprovados)
        
        # Checklist de Admissão
        chk_cols = ["Solicitar Doc", "Contrato", "Equipamentos"]
        existentes = [c for c in chk_cols if c in df.columns]
        if existentes:
            admissao_ok = len(df[df[existentes].all(axis=1)])
        else:
            admissao_ok = 0
        m3.metric("📦 ADMISSÃO OK", admissao_ok)
        
        vagas_abertas = len(st.session_state.vagas[st.session_state.vagas["Status Vaga"] == "Aberta"]) if not st.session_state.vagas.empty else 0
        m4.metric("🏢 VAGAS ABERTAS", vagas_abertas)

        st.divider()

        # Gráficos
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("Distribuição por Status")
            if "Status Geral" in df.columns:
                fig_status = px.bar(df["Status Geral"].value_counts().reset_index(), x="Status Geral", y="count", color_discrete_sequence=['#8DF768'])
                fig_status.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_status, use_container_width=True)
        
        with g2:
            st.subheader("Próximas Entrevistas")
            if "Entrevista RH" in df.columns and "Entrevista Gestor" in df.columns:
                agenda = df[df["Entrevista RH"].notna() | df["Entrevista Gestor"].notna()]
                if not agenda.empty:
                    st.dataframe(agenda[["Candidato", "Vaga Vinculada", "Entrevista RH", "Entrevista Gestor"]], use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhuma entrevista agendada.")

    else:
        st.info("O Dashboard aparecerá aqui assim que houver candidatos cadastrados no Fluxo.")

# --- RECURSO: VAGAS (COM EXCLUSÃO) ---
elif menu == "🏢 VAGAS":
    st.subheader("Gerenciar Ecossistema de Vagas")
    with st.form("nova_vaga"):
        n = st.text_input("Nome da Nova Vaga")
        if st.form_submit_button("CADASTRAR VAGA"):
            if n:
                st.session_state.vagas = pd.concat([st.session_state.vagas, pd.DataFrame([{"Nome da Vaga": n, "Área": "Geral", "Status Vaga": "Aberta"}])], ignore_index=True)
                salvar_tudo()
                st.rerun()
    
    st.divider()
    c_ed, c_del = st.columns([2, 1])
    with c_ed:
        st.markdown("### Editar Vagas")
        v_ed = st.data_editor(st.session_state.vagas, num_rows="dynamic", key="v_ed_key", use_container_width=True)
        if st.button("💾 SALVAR ALTERAÇÕES"):
            st.session_state.vagas = v_ed
            salvar_tudo()
            st.success("Vagas Salvas!")
            st.rerun()

    with c_del:
        st.markdown("### Excluir Vaga")
        vaga_opcoes = ["-- Selecionar --"] + st.session_state.vagas["Nome da Vaga"].tolist()
        vaga_sel = st.selectbox("Vaga para apagar:", vaga_opcoes, key="del_v_sel")
        if st.button("🗑️ APAGAR DEFINITIVAMENTE", type="secondary"):
            if vaga_sel != "-- Selecionar --":
                st.session_state.vagas = st.session_state.vagas[st.session_state.vagas["Nome da Vaga"] != vaga_sel]
                st.session_state.candidatos = st.session_state.candidatos[st.session_state.candidatos["Vaga Vinculada"] != vaga_sel]
                salvar_tudo()
                st.rerun()

# --- RECURSO: FLUXO (COM STATUS ATUALIZADOS) ---
elif menu == "⚙️ FLUXO":
    if st.session_state.vagas.empty:
        st.warning("Cadastre uma vaga primeiro.")
    else:
        v_list = st.session_state.vagas["Nome da Vaga"].unique().tolist()
        tabs = st.tabs(v_list)
        for i, v_nome in enumerate(v_list):
            with tabs[i]:
                df_v = st.session_state.candidatos[st.session_state.candidatos["Vaga Vinculada"] == v_nome].copy()
                
                b1, b2 = st.columns(2)
                with b1:
                    if st.button(f"➕ NOVO CANDIDATO", key=f"add_{v_nome}"):
                        novo = pd.DataFrame([{
                            "Candidato": "Nome", "Vaga Vinculada": v_nome, "Status Geral": "Vaga aberta",
                            "Entrevista RH": None, "Entrevista Gestor": None, "Teste Técnico": "Não",
                            "Solicitar Doc": False, "Foto/Curiosidade": False, "Contrato": False,
                            "Equipamentos": False, "Cadastro RH Gestor": False, "Data Inicio": None, "Aprovação Final": "Não"
                        }])
                        st.session_state.candidatos = pd.concat([st.session_state.candidatos, novo], ignore_index=True)
                        salvar_tudo()
                        st.rerun()
                with b2:
                    ex_c = st.selectbox("Excluir:", ["--"] + df_v["Candidato"].tolist(), key=f"sel_c_{v_nome}")
                    if st.button("🗑️ APAGAR CANDIDATO", key=f"btn_c_{v_nome}", type="secondary") and ex_c != "--":
                        st.session_state.candidatos = st.session_state.candidatos[~((st.session_state.candidatos["Candidato"] == ex_c) & (st.session_state.candidatos["Vaga Vinculada"] == v_nome))]
                        salvar_tudo()
                        st.rerun()

                df_ed = st.data_editor(
                    df_v, key=f"ed_v_{v_nome}", use_container_width=True, hide_index=True,
                    column_config={
                        "Status Geral": st.column_config.SelectboxColumn("Status", options=["Vaga aberta", "Triagem", "Entrevista RH", "Entrevista gestor", "Solicitação de documentos", "Solicitação de contratos", "Finalizada"]),
                        "Entrevista RH": st.column_config.DateColumn("📅 RH", format="DD/MM/YYYY"),
                        "Entrevista Gestor": st.column_config.DateColumn("📅 Gestor", format="DD/MM/YYYY"),
                        "Data Inicio": st.column_config.DateColumn("🚀 Início", format="DD/MM/YYYY"),
                        "Teste Técnico": st.column_config.SelectboxColumn("📝 Teste", options=["Sim", "Não"]),
                        "Solicitar Doc": st.column_config.CheckboxColumn("📂 Doc"),
                        "Foto/Curiosidade": st.column_config.CheckboxColumn("📸 Foto"),
                        "Contrato": st.column_config.CheckboxColumn("📜 Cont."),
                        "Equipamentos": st.column_config.CheckboxColumn("💻 Equip."),
                        "Cadastro RH Gestor": st.column_config.CheckboxColumn("✅ Cad."),
                        "Aprovação Final": st.column_config.SelectboxColumn("Aprovado?", options=["Sim", "Não"])
                    }
                )
                if st.button("💾 SALVAR FLUXO", key=f"save_f_{v_nome}"):
                    df_others = st.session_state.candidatos[st.session_state.candidatos["Vaga Vinculada"] != v_nome]
                    st.session_state.candidatos = pd.concat([df_others, df_ed], ignore_index=True)
                    salvar_tudo()
                    st.success("Salvo!")
                    st.rerun()