import streamlit as st
import pandas as pd
from datetime import date, timedelta
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# ════════════════════════════════════════════════════════════
# 1. CONFIG & TEMA VISUAL (ETUS v4 Light)
# ════════════════════════════════════════════════════════════
st.set_page_config(page_title="ETUS · Sistema Integrado", layout="wide", page_icon="logo.png")

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#eef1f6; --surf:#ffffff; --card:#ffffff; --card2:#f5f7fa; --card3:#eef1f6;
  --b1:rgba(0,0,0,0.07); --b2:rgba(0,0,0,0.13); --b3:rgba(0,0,0,0.2);
  --txt:#1a2035; --mut:#6b7a99; --dim:#9eacc0; --hint:#c8d0de;
  --nav:#0f1929; --nav2:#162034; --nav-txt:#e8edf5; --nav-mut:#6b80a0;
  --green:#0d7a3e; --green-bg:#e8f5ee; --green-border:#b2ddc4;
  --blue:#1565c0;  --blue-bg:#e8f0fb;  --blue-border:#aac4ed;
  --amber:#b45309; --amber-bg:#fef3e2; --amber-border:#f6cc7e;
  --red:#c0392b;   --red-bg:#fdecea;   --red-border:#f5b7b0;
  --purple:#6d28d9;--purple-bg:#f0ebfe;--purple-border:#c4aaee;
  --cyan:#0277bd;  --cyan-bg:#e1f2fb;  --cyan-border:#90caf9;
  --fd:'Syne',sans-serif; --fb:'DM Sans',sans-serif;
  --r:10px; --r2:7px; --r3:5px;
  --shadow:0 1px 3px rgba(0,0,0,.08),0 4px 16px rgba(0,0,0,.05);
  --shadow-lg:0 2px 8px rgba(0,0,0,.1),0 8px 32px rgba(0,0,0,.06);
}
html, body, [class*="css"] { font-family: var(--fb) !important; font-size: 13px; background: var(--bg) !important; color: var(--txt) !important; }
.main .block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { background: var(--nav) !important; border-right: none !important; }
section[data-testid="stSidebar"] > div { padding: 0 !important; }
section[data-testid="stSidebar"] * { color: var(--nav-mut) !important; font-family: var(--fb) !important; }
header[data-testid="stHeader"] { display: none !important; }
.etus-topbar { background: #fff; border-bottom: 1px solid var(--b1); padding: 0 24px; height: 52px; display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; box-shadow: 0 1px 4px rgba(0,0,0,.06); margin-bottom: 20px; }
.tb-title { font-family: var(--fd); font-size: 16px; font-weight: 700; color: var(--txt); display: flex; align-items: center; gap: 7px; }
.tb-crumb { font-size: 11px; color: var(--mut); }
.tb-meta  { font-size: 10px; color: var(--mut); }
.sb-logo { font-family: var(--fd); font-size: 20px; font-weight: 800; color: #60a5fa; letter-spacing: -1px; }
.sb-tagline { font-size: 9px; color: var(--nav-mut); letter-spacing: 2.5px; text-transform: uppercase; margin-top: 3px; }
.sb-section { font-size: 9px; color: var(--nav-mut); letter-spacing: 2px; text-transform: uppercase; padding: 10px 0 4px; font-weight: 600; }
.krow { display: grid; gap: 12px; margin-bottom: 16px; }
.krow-4 { grid-template-columns: repeat(4,1fr); }
.krow-3 { grid-template-columns: repeat(3,1fr); }
.krow-2 { grid-template-columns: repeat(2,1fr); }
.kc { background: #fff; border: 1px solid var(--b1); border-radius: var(--r); padding: 16px 18px; position: relative; overflow: hidden; transition: box-shadow .2s, transform .2s; box-shadow: var(--shadow); }
.kc:hover { box-shadow: var(--shadow-lg); transform: translateY(-1px); }
.kc::before { content:''; position:absolute; top:0; left:0; right:0; height:3px; background:var(--ac,transparent); border-radius:3px 3px 0 0; }
.kc.g { --ac:var(--green); background:linear-gradient(135deg,#fff 80%,rgba(13,122,62,.04)); }
.kc.b { --ac:var(--blue);  background:linear-gradient(135deg,#fff 80%,rgba(21,101,192,.04)); }
.kc.a { --ac:var(--amber); background:linear-gradient(135deg,#fff 80%,rgba(180,83,9,.04)); }
.kc.r { --ac:var(--red);   background:linear-gradient(135deg,#fff 80%,rgba(192,57,43,.04)); }
.kc.p { --ac:var(--purple);background:linear-gradient(135deg,#fff 80%,rgba(109,40,217,.04)); }
.kc.c { --ac:var(--cyan);  background:linear-gradient(135deg,#fff 80%,rgba(2,119,189,.04)); }
.kc-icon { width:32px; height:32px; border-radius:var(--r2); display:flex; align-items:center; justify-content:center; font-size:14px; margin-bottom:10px; }
.kc.g .kc-icon{background:var(--green-bg)} .kc.b .kc-icon{background:var(--blue-bg)} .kc.a .kc-icon{background:var(--amber-bg)} .kc.r .kc-icon{background:var(--red-bg)} .kc.p .kc-icon{background:var(--purple-bg)} .kc.c .kc-icon{background:var(--cyan-bg)}
.kc-label { font-size:9px; color:var(--mut); text-transform:uppercase; letter-spacing:1.3px; margin-bottom:4px; font-weight:600; }
.kc-val { font-family:var(--fd); font-size:26px; font-weight:700; line-height:1; margin-bottom:6px; }
.kc.g .kc-val{color:var(--green)} .kc.b .kc-val{color:var(--blue)} .kc.a .kc-val{color:var(--amber)} .kc.r .kc-val{color:var(--red)} .kc.p .kc-val{color:var(--purple)} .kc.c .kc-val{color:var(--cyan)}
.kc-trend { display:inline-flex; align-items:center; gap:3px; font-size:10px; padding:2px 7px; border-radius:20px; font-weight:500; }
.kc-trend.up{background:var(--green-bg);color:var(--green)} .kc-trend.dn{background:var(--red-bg);color:var(--red)} .kc-trend.nt{background:var(--amber-bg);color:var(--amber)} .kc-trend.ok{background:var(--green-bg);color:var(--green)}
.kc-meta { font-size:10px; color:var(--mut); margin-top:4px; }
.panel { background: #fff; border: 1px solid var(--b1); border-radius: var(--r); padding: 18px; box-shadow: var(--shadow); margin-bottom: 14px; transition: box-shadow .2s; }
.panel:hover { box-shadow: var(--shadow-lg); }
.panel-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; }
.panel-title { font-family:var(--fd); font-size:12px; font-weight:600; color:var(--txt); display:flex; align-items:center; gap:7px; }
.panel-dot { width:6px; height:6px; border-radius:50%; flex-shrink:0; }
.bdg { font-size:10px; padding:2px 9px; border-radius:20px; font-weight:600; display:inline-flex; align-items:center; gap:4px; }
.bdg.ok    {background:var(--green-bg);color:var(--green);border:1px solid var(--green-border)}
.bdg.bad   {background:var(--red-bg);color:var(--red);border:1px solid var(--red-border)}
.bdg.warn  {background:var(--amber-bg);color:var(--amber);border:1px solid var(--amber-border)}
.bdg.info  {background:var(--blue-bg);color:var(--blue);border:1px solid var(--blue-border)}
.bdg.purple{background:var(--purple-bg);color:var(--purple);border:1px solid var(--purple-border)}
.bdg.gray  {background:var(--card2);color:var(--mut);border:1px solid var(--b1)}
.notif { border-radius:var(--r2); padding:10px 14px; margin-bottom:14px; display:flex; align-items:center; gap:10px; font-size:12px; }
.notif.warn{background:var(--amber-bg);border:1px solid var(--amber-border);color:var(--amber)}
.notif.ok  {background:var(--green-bg);border:1px solid var(--green-border);color:var(--green)}
.notif.info{background:var(--blue-bg);border:1px solid var(--blue-border);color:var(--blue)}
.notif.red {background:var(--red-bg);border:1px solid var(--red-border);color:var(--red)}
.sla-item { margin-bottom:16px; }
.sla-header { display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:6px; }
.sla-name { font-size:12.5px; font-weight:600; color:var(--txt); }
.sla-dept { font-size:10px; color:var(--mut); margin-top:2px; }
.sla-days { font-family:var(--fd); font-size:22px; font-weight:700; line-height:1; }
.sla-days-lbl { font-size:9px; color:var(--mut); }
.sla-track { height:8px; background:var(--b1); border-radius:4px; overflow:hidden; }
.sla-fill  { height:100%; border-radius:4px; }
.sla-tags  { display:flex; gap:5px; margin-top:7px; flex-wrap:wrap; }
.prog-item { display:flex; align-items:center; gap:12px; margin-bottom:10px; }
.prog-name { font-size:11px; width:160px; flex-shrink:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--txt); }
.prog-track { flex:1; height:20px; background:var(--card2); border-radius:5px; overflow:hidden; border:1px solid var(--b1); }
.prog-fill  { height:100%; border-radius:5px; display:flex; align-items:center; padding-left:8px; font-size:9px; font-weight:700; color:#fff; }
.prog-pct   { font-family:var(--fd); font-size:11px; font-weight:700; width:38px; text-align:right; flex-shrink:0; }
.pe-card { display:flex; align-items:center; padding:12px 14px; background:#fff; border:1px solid var(--b1); border-radius:var(--r2); margin-bottom:7px; gap:12px; box-shadow:var(--shadow); }
.pe-dot  { width:10px; height:10px; border-radius:50%; flex-shrink:0; }
.pe-info { flex:1; min-width:0; }
.pe-name { font-size:12px; font-weight:600; color:var(--txt); }
.pe-meta { font-size:10px; color:var(--mut); margin-top:1px; }
.bonus-alert { background:var(--amber-bg); border:1px solid var(--amber-border); border-radius:var(--r2); padding:10px 14px; font-size:12px; color:var(--amber); margin-bottom:10px; }
.d-legend { display:flex; flex-direction:column; gap:9px; margin-top:14px; }
.d-leg-item { display:flex; align-items:center; gap:9px; }
.d-leg-swatch { width:9px; height:9px; border-radius:2px; flex-shrink:0; }
.d-leg-name { font-size:11px; flex:1; color:var(--txt); }
.d-leg-val  { font-family:var(--fd); font-size:12px; font-weight:700; color:var(--txt); }
.d-leg-pct  { font-size:10px; color:var(--mut); width:28px; text-align:right; }
table { width:100%; border-collapse:collapse; }
thead tr { border-bottom:2px solid var(--b1); }
th { font-size:9px; color:var(--mut); text-transform:uppercase; letter-spacing:1.2px; padding:9px 12px; text-align:left; font-weight:600; background:var(--card2); }
tbody tr { border-bottom:1px solid var(--b1); }
tbody tr:hover { background:var(--blue-bg); }
td { padding:11px 12px; font-size:12px; color:var(--txt); }
.empty-state { text-align:center; padding:44px 20px; color:var(--mut); }
.empty-icon  { font-size:36px; margin-bottom:10px; opacity:.4; }
.empty-title { font-size:13px; font-weight:500; margin-bottom:4px; }
.empty-sub   { font-size:11px; }
div[data-testid="stExpander"] { background:#fff !important; border:1px solid var(--b1) !important; border-radius:var(--r2) !important; margin-bottom:8px !important; box-shadow:var(--shadow) !important; }
div[data-testid="stExpander"]:hover { border-color:var(--b2) !important; box-shadow:var(--shadow-lg) !important; }
div[data-testid="stForm"] { border:none !important; padding:0 !important; }
label[data-testid="stWidgetLabel"] p { font-size:9px !important; color:var(--mut) !important; text-transform:uppercase !important; letter-spacing:1px !important; font-weight:600 !important; }
button[kind="primary"] { background:var(--blue) !important; border-color:var(--blue) !important; font-family:var(--fb) !important; font-size:11px !important; font-weight:600 !important; border-radius:var(--r2) !important; }
button[kind="secondary"] { background:#fff !important; border:1px solid var(--b1) !important; color:var(--mut) !important; font-family:var(--fb) !important; font-size:11px !important; border-radius:var(--r2) !important; }
div[data-testid="metric-container"] { background:#fff !important; border:1px solid var(--b1) !important; border-radius:var(--r) !important; padding:14px 16px !important; box-shadow:var(--shadow) !important; }
div[data-testid="stTabs"] [data-baseweb="tab-list"] { background:var(--card2) !important; border:1px solid var(--b1) !important; border-radius:var(--r2) !important; padding:3px !important; gap:2px !important; }
div[data-testid="stTabs"] [data-baseweb="tab"] { border-radius:5px !important; font-size:11px !important; font-family:var(--fb) !important; color:var(--mut) !important; }
div[data-testid="stTabs"] [aria-selected="true"] { background:#fff !important; color:var(--txt) !important; font-weight:500 !important; box-shadow:0 1px 4px rgba(0,0,0,.1) !important; }
[data-testid="stSidebarNav"] { display:none; }
.stAlert { border-radius:var(--r2) !important; font-size:12px !important; }
.stDownloadButton button { background:#fff !important; border:1px solid var(--b1) !important; color:var(--blue) !important; font-size:11px !important; border-radius:var(--r2) !important; }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# 2. BANCO DE DADOS
# ════════════════════════════════════════════════════════════
@st.cache_resource
def get_engine():
    try:
        DB_URL = st.secrets["postgres"]["url"]
        return create_engine(DB_URL, pool_size=10, max_overflow=20, connect_args={"sslmode": "require"})
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        st.stop()

engine = get_engine()

def executar_sql(query, params=None):
    try:
        with engine.begin() as conn:
            conn.execute(text(query), params or {})
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro SQL: {e}")
        return False

TABELAS_PERMITIDAS = {
    "vagas","candidatos","contratos_estagio","controle_experiencia",
    "colaboradores_ativos","notas_fiscais_ifood","pagamentos_gerais"
}
COLUNAS_BINARIAS = {
    "candidatos": ["arquivo_cv"],
    "notas_fiscais_ifood": ["arquivo_nf"],
    "pagamentos_gerais": ["arquivo_pg"],
}

@st.cache_data(ttl=30)
def carregar_dados(tabela):
    if tabela not in TABELAS_PERMITIDAS:
        return pd.DataFrame()
    try:
        excluir = COLUNAS_BINARIAS.get(tabela, [])
        with engine.connect() as conn:
            if excluir:
                res = conn.execute(text(f"SELECT * FROM {tabela} LIMIT 0"))
                cols = ", ".join(c for c in res.keys() if c not in excluir)
                return pd.read_sql(text(f"SELECT {cols} FROM {tabela} ORDER BY id DESC"), conn)
            return pd.read_sql(text(f"SELECT * FROM {tabela} ORDER BY id DESC"), conn)
    except Exception as e:
        st.warning(f"Erro ao carregar '{tabela}': {e}")
        return pd.DataFrame()

def carregar_arquivo(tabela, coluna, registro_id):
    if tabela not in TABELAS_PERMITIDAS:
        return None
    try:
        with engine.connect() as conn:
            row = conn.execute(text(f"SELECT {coluna} FROM {tabela} WHERE id=:id"), {"id":registro_id}).fetchone()
            return bytes(row[0]) if row and row[0] else None
    except Exception as e:
        st.error(f"Erro ao buscar arquivo: {e}")
        return None


# ════════════════════════════════════════════════════════════
# 3. E-MAIL
# ════════════════════════════════════════════════════════════
def enviar_email_foto(email_candidato, nome_candidato):
    try:
        meu_email = st.secrets["email"]["address"]
        minha_senha = st.secrets["email"]["password"]
        msg = MIMEMultipart()
        msg['Subject'] = f"Boas-vindas Etus! - Foto e Curiosidades de {nome_candidato}"
        msg['From'] = meu_email
        msg['To'] = email_candidato
        corpo = f"""<html><body style="font-family:sans-serif;">
            <p>Olá, <strong>{nome_candidato}</strong>! Parabéns pela aprovação!</p>
            <p>Envie: uma foto (peito para cima, fundo neutro, sorrindo, sem filtros) e três curiosidades suas.</p>
            <p><a href='https://docs.google.com/forms/d/e/1FAIpQLSd1o4x5jALKryUJraNB7GZB6xyJXJj5nRTs30dw_0ZFoVf9KQ/viewform?usp=sf_link'>Preencher formulário</a></p>
        </body></html>"""
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


# ════════════════════════════════════════════════════════════
# 4. INICIALIZAÇÃO DO BANCO
# ════════════════════════════════════════════════════════════
@st.cache_resource
def inicializar_banco():
    with engine.begin() as conn:
        conn.execute(text("""CREATE TABLE IF NOT EXISTS vagas (
            id SERIAL PRIMARY KEY, nome_vaga TEXT, area TEXT, status_vaga TEXT,
            gestor TEXT, data_abertura DATE, data_fechamento DATE, empresa TEXT);"""))
        conn.execute(text("""CREATE TABLE IF NOT EXISTS candidatos (
            id SERIAL PRIMARY KEY, candidato TEXT, email TEXT, vaga_vinculada TEXT,
            status_geral TEXT, arquivo_cv BYTEA, envio_proposta BOOLEAN DEFAULT FALSE,
            solic_documentos BOOLEAN DEFAULT FALSE, solic_contrato BOOLEAN DEFAULT FALSE,
            solic_acessos BOOLEAN DEFAULT FALSE, indicacao BOOLEAN DEFAULT FALSE,
            nome_indicador TEXT, data_inicio DATE, data_proposta DATE, data_documentos DATE,
            data_foto_curiosidades DATE, data_contrato DATE, data_equipamentos DATE,
            boas_vindas BOOLEAN DEFAULT FALSE, data_boas_vindas DATE,
            foto_curiosidades BOOLEAN DEFAULT FALSE, indicado_por TEXT, valor_bonus REAL DEFAULT 0.0);"""))
        conn.execute(text("""CREATE TABLE IF NOT EXISTS contratos_estagio (
            id SERIAL PRIMARY KEY, estagiario TEXT, instituicao TEXT, data_inicio DATE,
            data_fim DATE, time_equipe TEXT, solic_contrato_dp BOOLEAN DEFAULT FALSE,
            assina_etus BOOLEAN DEFAULT FALSE, assina_faculdade BOOLEAN DEFAULT FALSE,
            envio_juridico BOOLEAN DEFAULT FALSE);"""))
        conn.execute(text("""CREATE TABLE IF NOT EXISTS controle_experiencia (
            id SERIAL PRIMARY KEY, nome TEXT, cargo TEXT, time_equipe TEXT, data_inicio DATE,
            av1_feito BOOLEAN DEFAULT FALSE, av1_data DATE, av1_responsavel TEXT,
            av2_feito BOOLEAN DEFAULT FALSE, av2_data DATE, av2_responsavel TEXT);"""))
        conn.execute(text("""CREATE TABLE IF NOT EXISTS colaboradores_ativos (
            id SERIAL PRIMARY KEY, nome TEXT, tipo TEXT, data_admissao DATE,
            cad_starbem BOOLEAN DEFAULT FALSE, incl_amil BOOLEAN DEFAULT FALSE,
            ifood_ativo BOOLEAN DEFAULT FALSE, equipamento_entregue BOOLEAN DEFAULT FALSE);"""))
        conn.execute(text("""CREATE TABLE IF NOT EXISTS notas_fiscais_ifood (
            id SERIAL PRIMARY KEY, empresa TEXT, mes_referencia TEXT,
            arquivo_nf BYTEA, nome_arquivo TEXT, data_upload DATE);"""))
        conn.execute(text("""CREATE TABLE IF NOT EXISTS pagamentos_gerais (
            id SERIAL PRIMARY KEY, empresa TEXT, categoria TEXT, mes_referencia TEXT,
            arquivo_pg BYTEA, nome_arquivo TEXT, data_upload DATE,
            valor_pg NUMERIC, data_envio DATE, data_pagamento DATE, motivo TEXT);"""))
        migrations = [
            "ALTER TABLE vagas ADD COLUMN IF NOT EXISTS empresa TEXT;",
            "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS email TEXT;",
            "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS indicado_por TEXT;",
            "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS valor_bonus REAL DEFAULT 0.0;",
            "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS foto_curiosidades BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS data_foto_curiosidades DATE;",
            "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS boas_vindas BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS data_boas_vindas DATE;",
            "ALTER TABLE pagamentos_gerais ADD COLUMN IF NOT EXISTS valor_pg NUMERIC;",
            "ALTER TABLE pagamentos_gerais ADD COLUMN IF NOT EXISTS data_envio DATE;",
            "ALTER TABLE pagamentos_gerais ADD COLUMN IF NOT EXISTS data_pagamento DATE;",
            "ALTER TABLE pagamentos_gerais ADD COLUMN IF NOT EXISTS motivo TEXT;",
        ]
        for sql in migrations:
            try:
                conn.execute(text(sql))
            except Exception:
                pass

inicializar_banco()


# ════════════════════════════════════════════════════════════
# 5. HELPERS VISUAIS
# ════════════════════════════════════════════════════════════
def kpi_card(label, value, color="b", trend="", trend_type="nt", meta="", icon=""):
    color_map = {"g":"var(--green)","b":"var(--blue)","a":"var(--amber)",
                 "r":"var(--red)","p":"var(--purple)","c":"var(--cyan)"}
    c = color_map.get(color, "var(--blue)")
    trend_html = f'<span class="kc-trend {trend_type}">{trend}</span>' if trend else ""
    meta_html  = f'<div class="kc-meta">{meta}</div>' if meta else ""
    icon_html  = f'<div class="kc-icon">{icon}</div>' if icon else ""
    return f'<div class="kc {color}">{icon_html}<div class="kc-label">{label}</div><div class="kc-val" style="color:{c}">{value}</div><div>{trend_html}</div>{meta_html}</div>'

def krow(*cards, cols=None):
    n = cols or len(cards)
    cls = {4:"krow-4",3:"krow-3",2:"krow-2"}.get(n,"krow-4")
    return f'<div class="krow {cls}">{"".join(cards)}</div>'

def badge(text, kind="info"):
    return f'<span class="bdg {kind}">{text}</span>'

def notif(text, kind="info"):
    return f'<div class="notif {kind}">{text}</div>'

def panel_title(text, dot_color="var(--blue)"):
    return f'<div class="panel-title"><span class="panel-dot" style="background:{dot_color}"></span>{text}</div>'

def topbar(title, icon="", crumb="", meta=""):
    crumb_html = f'<span class="tb-crumb">{crumb} ›</span> ' if crumb else ""
    meta_html  = f'<span class="tb-meta">{meta}</span>' if meta else ""
    return f'<div class="etus-topbar"><div class="tb-title">{crumb_html}{icon} {title}</div><div>{meta_html}</div></div>'

def sla_bar(nome, area, dias, sla=30):
    pct = min(dias / sla * 100, 100)
    color = "#0d7a3e" if pct < 50 else "#b45309" if pct < 85 else "#c0392b"
    bdg_kind = "ok" if pct < 50 else "warn" if pct < 85 else "bad"
    return f"""<div class="sla-item">
      <div class="sla-header">
        <div><div class="sla-name">{nome}</div><div class="sla-dept">{area}</div></div>
        <div style="text-align:right"><div class="sla-days" style="color:{color}">{dias}</div><div class="sla-days-lbl">dias em aberto</div></div>
      </div>
      <div class="sla-track"><div class="sla-fill" style="width:{pct:.0f}%;background:{color}"></div></div>
      <div class="sla-tags">{badge("✓ dentro do SLA" if dias<=sla else "⚠ fora do SLA", bdg_kind)}</div>
    </div>"""

def prog_bar(nome, pct, color="#1565c0"):
    pct_int = min(int(pct), 100)
    return f"""<div class="prog-item">
      <div class="prog-name">{nome}</div>
      <div class="prog-track"><div class="prog-fill" style="width:{pct_int}%;background:{color}">{pct_int}%</div></div>
      <div class="prog-pct" style="color:{color}">{pct_int}%</div>
    </div>"""

def pe_card(nome, cargo, time, limite, status):
    dot_c = {"aprovado":"var(--green)","reprovado":"var(--red)"}.get(status,"var(--amber)")
    bdg_map = {"aprovado":("ok","✓ Aprovado"),"reprovado":("bad","✗ Reprovado")}
    bk, bl = bdg_map.get(status, ("warn","⏳ Pendente"))
    return f"""<div class="pe-card"><div class="pe-dot" style="background:{dot_c}"></div>
      <div class="pe-info"><div class="pe-name">{nome}</div><div class="pe-meta">{cargo} · {time} · Limite: {limite}</div></div>
      {badge(bl, bk)}</div>"""


# ════════════════════════════════════════════════════════════
# 6. SIDEBAR
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""<div style="padding:18px 16px 14px;border-bottom:1px solid rgba(255,255,255,.07)">
      <div class="sb-logo">● ETUS</div>
      <div class="sb-tagline">Sistema Integrado · RH & DP</div>
    </div>""", unsafe_allow_html=True)
    st.markdown('<div style="padding:10px 16px 4px"><div class="sb-section">Módulo</div></div>', unsafe_allow_html=True)
    area_sel = st.selectbox("", ["RH · Recrutamento","DP · Departamento Pessoal","Financeiro & Notas"], label_visibility="collapsed")
    st.markdown('<div style="padding:10px 16px 4px"><div class="sb-section">Navegação</div></div>', unsafe_allow_html=True)
    if area_sel == "RH · Recrutamento":
        menu = st.radio("", ["📊 Indicadores","🏢 Vagas","⚙️ Candidatos","🚀 Onboarding"], label_visibility="collapsed")
    elif area_sel == "DP · Departamento Pessoal":
        menu = st.radio("", ["📊 Dashboard DP","🎓 Estagiários","👥 Colaboradores","⏳ Período de Experiência"], label_visibility="collapsed")
    else:
        menu = st.radio("", ["🍔 iFood","💸 Outros Pagamentos","📊 Dashboard Financeiro"], label_visibility="collapsed")
    st.markdown("""<div style="position:absolute;bottom:0;left:0;right:0;padding:12px 18px;border-top:1px solid rgba(255,255,255,.07)">
      <div style="display:flex;align-items:center;gap:9px">
        <div style="width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,#3b82f6,#8b5cf6);display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;color:#fff;flex-shrink:0">RH</div>
        <div><div style="font-size:11px;font-weight:500;color:#e8edf5 !important">Equipe ETUS</div><div style="font-size:9px;color:var(--nav-mut)">Sistema ativo</div></div>
        <div style="margin-left:auto;display:flex;align-items:center;gap:4px;background:rgba(52,211,153,.1);border:1px solid rgba(52,211,153,.25);border-radius:20px;padding:3px 8px;font-size:9px;color:#34d399">
          <div style="width:5px;height:5px;background:#34d399;border-radius:50%"></div>live</div>
      </div>
    </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# 7. PÁGINAS
# ════════════════════════════════════════════════════════════

# ── INDICADORES ──────────────────────────────────────────
if menu == "📊 Indicadores":
    st.markdown(topbar("Indicadores de Recrutamento", "📊", "RH"), unsafe_allow_html=True)
    df_v = carregar_dados("vagas")
    df_c = carregar_dados("candidatos")
    vagas_ativas = pd.DataFrame()

    if not df_v.empty:
        df_v['data_abertura'] = pd.to_datetime(df_v['data_abertura']).dt.date
        hoje = date.today()
        df_v['dias_aberta'] = df_v.apply(
            lambda x: (x['data_fechamento'] - x['data_abertura']).days if pd.notnull(x.get('data_fechamento'))
            else (hoje - x['data_abertura']).days, axis=1)
        vagas_ativas = df_v[df_v['status_vaga'] == 'Aberta']
        media_dias = int(vagas_ativas['dias_aberta'].mean()) if not vagas_ativas.empty else 0
        total_c = len(df_c) if not df_c.empty else 0
        aprovados = len(df_c[df_c['status_geral'] == 'Finalizada']) if not df_c.empty else 0
        st.markdown(krow(
            kpi_card("Vagas Abertas", len(vagas_ativas), "g", icon="📋"),
            kpi_card("Média Tempo Aberta", f"{media_dias}d", "b", "meta 30d", "nt", icon="⏱"),
            kpi_card("Candidatos", total_c, "c", icon="👥"),
            kpi_card("Aprovados", aprovados, "p", icon="✅"), cols=4
        ), unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["⏱ SLA de Vagas", "📊 Funil & Distribuição"])
    with tab1:
        col_l, col_r = st.columns([1.6, 1])
        with col_l:
            st.markdown('<div class="panel">', unsafe_allow_html=True)
            st.markdown(panel_title("SLA por Vaga Aberta (meta: 30 dias)", "var(--green)"), unsafe_allow_html=True)
            if not vagas_ativas.empty:
                for _, row in vagas_ativas.sort_values('dias_aberta', ascending=False).iterrows():
                    st.markdown(sla_bar(row['nome_vaga'], row.get('area',''), int(row['dias_aberta'])), unsafe_allow_html=True)
            else:
                st.markdown('<div class="empty-state"><div class="empty-icon">📋</div><div class="empty-title">Nenhuma vaga aberta</div></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with col_r:
            st.markdown('<div class="panel">', unsafe_allow_html=True)
            st.markdown(panel_title("Candidatos por Vaga", "var(--blue)"), unsafe_allow_html=True)
            if not df_c.empty:
                fig = px.pie(df_c, names='vaga_vinculada', hole=0.55,
                             color_discrete_sequence=['#0d7a3e','#1565c0','#b45309','#6d28d9','#0277bd'])
                fig.update_layout(margin=dict(t=5,b=5,l=5,r=5), showlegend=True,
                                  legend=dict(font=dict(size=10,color="#6b7a99")),
                                  paper_bgcolor='rgba(0,0,0,0)', height=230)
                st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    with tab2:
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown('<div class="panel">', unsafe_allow_html=True)
            st.markdown(panel_title("Funil de Recrutamento", "var(--green)"), unsafe_allow_html=True)
            if not df_c.empty:
                ordem = ["Triagem","Entrevista RH","Teste Técnico","Entrevista Gestor","Aprovado","Finalizada"]
                cnt = df_c['status_geral'].value_counts().reindex(ordem).fillna(0).reset_index()
                fig = px.funnel(cnt, x='count', y='status_geral', color_discrete_sequence=['#1565c0'])
                fig.update_layout(margin=dict(t=5,b=5,l=5,r=5), paper_bgcolor='rgba(0,0,0,0)',
                                  plot_bgcolor='rgba(0,0,0,0)', height=270,
                                  yaxis=dict(tickfont=dict(size=10,color="#6b7a99")))
                st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with col_r:
            st.markdown('<div class="panel">', unsafe_allow_html=True)
            st.markdown(panel_title("Candidatos por Status", "var(--purple)"), unsafe_allow_html=True)
            if not df_c.empty:
                fig2 = px.bar(df_c['status_geral'].value_counts().reset_index(),
                              x='status_geral', y='count', color='count',
                              color_continuous_scale=['#aac4ed','#1565c0'])
                fig2.update_layout(margin=dict(t=5,b=5,l=5,r=5), showlegend=False,
                                   paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=270,
                                   xaxis=dict(tickfont=dict(size=10,color="#6b7a99")),
                                   yaxis=dict(tickfont=dict(size=10,color="#6b7a99"),gridcolor="rgba(0,0,0,0.05)"))
                st.plotly_chart(fig2, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)


# ── VAGAS ─────────────────────────────────────────────────
elif menu == "🏢 Vagas":
    st.markdown(topbar("Gestão de Vagas", "🏢", "RH"), unsafe_allow_html=True)
    lista_empresas = ["ETUS","BHAZ","Evolution","E3J","No Name"]
    lista_times = ["RH","Jurídico","Financeiro","Dados","CRO","Desenvolvimento","Jornalismo",
                   "Marketing","SRE","Retenção","Monetização","Comunidade","Conteúdo","Produto"]
    df_v = carregar_dados("vagas")

    if not df_v.empty:
        st.markdown(krow(
            kpi_card("Abertas",     len(df_v[df_v['status_vaga']=='Aberta']),     "g", icon="📋"),
            kpi_card("Finalizadas", len(df_v[df_v['status_vaga']=='Finalizada']), "b", icon="✅"),
            kpi_card("Pausadas",    len(df_v[df_v['status_vaga']=='Pausada']),    "a", icon="⏸"),
            cols=3
        ), unsafe_allow_html=True)

    with st.expander("➕ Cadastrar Nova Vaga"):
        with st.form("nv", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nv = c1.text_input("Título da Vaga")
            gv = c2.text_input("Gestor Responsável")
            c3, c4 = st.columns(2)
            ev = c3.selectbox("Empresa", lista_empresas)
            av = c4.selectbox("Time / Área", lista_times)
            if st.form_submit_button("Cadastrar Vaga", type="primary"):
                if nv:
                    executar_sql("INSERT INTO vagas (nome_vaga,area,status_vaga,gestor,data_abertura,empresa) VALUES (:n,:a,'Aberta',:g,:d,:e)",
                                 {"n":nv,"a":av,"g":gv,"d":date.today(),"e":ev})
                    st.rerun()

    df_v = carregar_dados("vagas")
    for _, row in df_v.iterrows():
        with st.expander(f"{row['nome_vaga']} · {row.get('empresa','—')} · {row['status_vaga']}"):
            with st.form(f"edv{row['id']}"):
                c1, c2 = st.columns(2)
                v_nome   = c1.text_input("Vaga", value=row['nome_vaga'])
                v_gestor = c2.text_input("Gestor", value=row['gestor'] or "")
                c3, c4 = st.columns(2)
                e_idx    = lista_empresas.index(row['empresa']) if row['empresa'] in lista_empresas else 0
                v_empresa = c3.selectbox("Empresa", lista_empresas, index=e_idx)
                t_idx    = lista_times.index(row['area']) if row['area'] in lista_times else 0
                v_area   = c4.selectbox("Time", lista_times, index=t_idx)
                c5, c6 = st.columns(2)
                v_data = c5.date_input("Abertura", value=row['data_abertura'] if row['data_abertura'] else date.today())
                ns = c6.selectbox("Status", ["Aberta","Pausada","Finalizada"],
                                  index=["Aberta","Pausada","Finalizada"].index(row['status_vaga']))
                cs, cd = st.columns(2)
                if cs.form_submit_button("Salvar", type="primary"):
                    df_f = date.today() if ns == "Finalizada" else None
                    executar_sql("UPDATE vagas SET nome_vaga=:nv,area=:a,status_vaga=:s,gestor=:g,data_abertura=:da,data_fechamento=:df,empresa=:e WHERE id=:id",
                                 {"nv":v_nome,"a":v_area,"s":ns,"g":v_gestor,"da":v_data,"df":df_f,"e":v_empresa,"id":row['id']})
                    st.rerun()
                if cd.form_submit_button("Excluir"):
                    executar_sql("DELETE FROM vagas WHERE id=:id", {"id":row['id']}); st.rerun()


# ── CANDIDATOS ────────────────────────────────────────────
elif menu == "⚙️ Candidatos":
    st.markdown(topbar("Gestão de Candidatos", "⚙️", "RH"), unsafe_allow_html=True)
    df_v = carregar_dados("vagas")
    df_c = carregar_dados("candidatos")
    v_list = df_v['nome_vaga'].tolist() if not df_v.empty else ["Geral"]

    with st.expander("➕ Cadastrar Novo Candidato"):
        with st.form("form_novo_cand", clear_on_submit=True):
            c1, c2 = st.columns(2)
            n_novo = c1.text_input("Nome*")
            e_novo = c2.text_input("E-mail*")
            v_sel  = c1.selectbox("Vaga Vinculada", v_list)
            ci1, ci2 = st.columns(2)
            ind_novo = ci1.text_input("Indicado por (opcional)")
            val_novo = ci2.number_input("Valor Bônus (R$)", min_value=0.0, step=50.0)
            if st.form_submit_button("Cadastrar Candidato", type="primary"):
                if n_novo and e_novo:
                    executar_sql("INSERT INTO candidatos (candidato,email,vaga_vinculada,status_geral,indicado_por,valor_bonus) VALUES (:n,:e,:v,'Triagem',:i,:val)",
                                 {"n":n_novo,"e":e_novo,"v":v_sel,"i":ind_novo,"val":val_novo})
                    st.success(f"✓ {n_novo} cadastrado!"); st.rerun()
                else:
                    st.error("Preencha nome e e-mail.")

    if not df_c.empty:
        busca = st.text_input("🔍 Buscar candidato...", placeholder="Digite o nome...")
        df_base = df_c[df_c['candidato'].str.contains(busca, case=False, na=False)] if busca else df_c
        vagas_com_cands = sorted(df_base['vaga_vinculada'].dropna().unique().tolist())
        st_opts = ["Triagem","Entrevista RH","Teste Técnico","Entrevista Gestor","Aprovado","Finalizada","Reprovado"]
        st_colors = {"Triagem":"info","Entrevista RH":"info","Teste Técnico":"purple","Entrevista Gestor":"purple","Aprovado":"ok","Finalizada":"ok","Reprovado":"bad"}

        if not vagas_com_cands:
            st.markdown('<div class="empty-state"><div class="empty-icon">🔍</div><div class="empty-title">Nenhum candidato encontrado</div></div>', unsafe_allow_html=True)
        else:
            abas = st.tabs(vagas_com_cands)
            for i, vaga_nome in enumerate(vagas_com_cands):
                with abas[i]:
                    df_vaga = df_base[df_base['vaga_vinculada'] == vaga_nome]
                    st.caption(f"📌 {len(df_vaga)} candidato(s)")
                    for _, cand in df_vaga.iterrows():
                        st_atual = cand['status_geral']
                        with st.expander(f"{cand['candidato'].upper()} · {badge(st_atual, st_colors.get(st_atual,'gray'))}"):
                            edit_mode = st.toggle("🔓 Liberar edição", key=f"tog_{cand['id']}")
                            with st.form(key=f"ef_{cand['id']}"):
                                c1, c2 = st.columns(2)
                                en = c1.text_input("Nome",    value=cand['candidato'],              disabled=not edit_mode)
                                ee = c2.text_input("E-mail",  value=cand.get('email','') or '',     disabled=not edit_mode)
                                idx_v = v_list.index(cand['vaga_vinculada']) if cand['vaga_vinculada'] in v_list else 0
                                ev2 = c1.selectbox("Vaga", v_list, index=idx_v,                     disabled=not edit_mode)
                                idx_s = st_opts.index(st_atual) if st_atual in st_opts else 0
                                es  = c2.selectbox("Status", st_opts, index=idx_s,                  disabled=not edit_mode)
                                ei  = c1.text_input("Indicado por", value=cand.get('indicado_por','') or '', disabled=not edit_mode)
                                ev3 = c2.number_input("Valor Bônus", value=float(cand.get('valor_bonus') or 0), disabled=not edit_mode)
                                bs, be = st.columns(2)
                                if bs.form_submit_button("Salvar", type="primary", disabled=not edit_mode, use_container_width=True):
                                    executar_sql("UPDATE candidatos SET candidato=:n,email=:e,vaga_vinculada=:v,status_geral=:s,indicado_por=:i,valor_bonus=:val WHERE id=:id",
                                                 {"n":en,"e":ee,"v":ev2,"s":es,"i":ei,"val":ev3,"id":cand['id']})
                                    st.success("✓ Atualizado!"); st.rerun()
                                if be.form_submit_button("Excluir", use_container_width=True):
                                    executar_sql("DELETE FROM candidatos WHERE id=:id", {"id":cand['id']}); st.rerun()
    else:
        st.markdown('<div class="empty-state"><div class="empty-icon">👥</div><div class="empty-title">Nenhum candidato cadastrado</div></div>', unsafe_allow_html=True)


# ── ONBOARDING ────────────────────────────────────────────
elif menu == "🚀 Onboarding":
    st.markdown(topbar("Gestão de Onboarding", "🚀", "RH"), unsafe_allow_html=True)
    df_c  = carregar_dados("candidatos")
    df_onb = df_c[df_c['status_geral'] == 'Finalizada'] if not df_c.empty else pd.DataFrame()

    if not df_onb.empty:
        pendentes = int(len(df_onb) - df_onb['solic_acessos'].fillna(False).sum())
        st.markdown(krow(
            kpi_card("Em Onboarding",       len(df_onb),                                  "g", icon="🚀"),
            kpi_card("Com Data de Início",   int(df_onb['data_inicio'].notna().sum()),     "b", icon="📅"),
            kpi_card("Pendências",           pendentes, "a" if pendentes else "g",
                     "atenção" if pendentes else "✓ ok", "dn" if pendentes else "ok",     icon="⚠️"),
            cols=3
        ), unsafe_allow_html=True)

        for _, row in df_onb.iterrows():
            indicador = row.get('indicado_por')
            valor_b   = row.get('valor_bonus', 0)
            data_ini  = row.get('data_inicio')
            if indicador and valor_b and valor_b > 0 and data_ini:
                dt_ini = pd.to_datetime(data_ini).date()
                data_pg = dt_ini + timedelta(days=90)
                dias_r  = (data_pg - date.today()).days
                status_b = "🔴 VENCIDO" if dias_r <= 0 else f"⏳ em {dias_r} dias"
                st.markdown(f'<div class="bonus-alert">💰 <strong>Bônus:</strong> {indicador} recebe R$ {valor_b:.2f} em {data_pg.strftime("%d/%m/%Y")} — {status_b}</div>', unsafe_allow_html=True)

            passos = [bool(row.get('envio_proposta')), bool(row.get('solic_documentos')),
                      bool(row.get('foto_curiosidades')), bool(row.get('solic_contrato')), bool(row.get('solic_acessos'))]
            pct_prog = int(sum(passos) / len(passos) * 100)
            prog_color = "#0d7a3e" if pct_prog == 100 else "#1565c0" if pct_prog > 50 else "#b45309"

            with st.expander(f"👤 {row['candidato']} · {row['vaga_vinculada']} · {badge(f'{pct_prog}%', 'ok' if pct_prog==100 else 'info')}"):
                st.markdown(prog_bar("Progresso geral", pct_prog, prog_color), unsafe_allow_html=True)
                liberar = st.toggle("🔓 Liberar edição do checklist", key=f"lib_{row['id']}")

                with st.form(key=f"onb_{row['id']}"):
                    d_ini_val = pd.to_datetime(row['data_inicio']).date() if row.get('data_inicio') else date.today()
                    v_ini = st.date_input("📅 Data Prevista de Início", value=d_ini_val)
                    st.markdown("**Checklist de Integração**")
                    ja_email = bool(row.get('foto_curiosidades'))
                    ja_foto  = row.get('data_foto_curiosidades') is not None
                    c1, c2 = st.columns(2)
                    with c1:
                        c_prop  = st.checkbox("Envio de Proposta",          value=bool(row.get('envio_proposta')),  key=f"cp_{row['id']}")
                        c_doc   = st.checkbox("Solicitação de Documentos",  value=bool(row.get('solic_documentos')),key=f"cd_{row['id']}")
                        c_email = st.checkbox("Disparar E-mail Foto/Curios.",value=ja_email, disabled=(ja_email and not liberar), key=f"ce_{row['id']}")
                    with c2:
                        c_cont  = st.checkbox("Assinatura de Contrato",     value=bool(row.get('solic_contrato')),  key=f"cc_{row['id']}")
                        c_acess = st.checkbox("Acessos e Equipamentos",      value=bool(row.get('solic_acessos')),   key=f"ca_{row['id']}")
                        c_foto  = st.checkbox("Foto e curiosidade recebidas",value=ja_foto, disabled=(ja_foto and not liberar), key=f"cf_{row['id']}")
                    if st.form_submit_button("💾 Gravar Progresso", type="primary", use_container_width=True):
                        if c_email and not ja_email:
                            if row.get('email'):
                                if enviar_email_foto(row['email'], row['candidato']):
                                    st.toast("📧 E-mail enviado!", icon="✅")
                            else:
                                st.error("Candidato sem e-mail cadastrado.")
                        data_foto_val = row.get('data_foto_curiosidades') if ja_foto else (date.today() if c_foto else None)
                        if executar_sql("""UPDATE candidatos SET data_inicio=:di,envio_proposta=:cp,solic_documentos=:cd,
                            foto_curiosidades=:cf,data_foto_curiosidades=:dfc,solic_contrato=:cc,solic_acessos=:ca WHERE id=:id""",
                            {"di":v_ini,"cp":c_prop,"cd":c_doc,"cf":c_email,"dfc":data_foto_val,"cc":c_cont,"ca":c_acess,"id":row['id']}):
                            st.success("✓ Dados salvos!"); st.rerun()
    else:
        st.markdown('<div class="empty-state"><div class="empty-icon">🚀</div><div class="empty-title">Nenhum onboarding pendente</div><div class="empty-sub">Candidatos com status "Finalizada" aparecerão aqui</div></div>', unsafe_allow_html=True)


# ── DASHBOARD DP ──────────────────────────────────────────
elif menu == "📊 Dashboard DP":
    st.markdown(topbar("Dashboard · Departamento Pessoal", "📊", "DP"), unsafe_allow_html=True)
    df_col = carregar_dados("colaboradores_ativos")
    df_est = carregar_dados("contratos_estagio")
    df_exp = carregar_dados("controle_experiencia")
    df_c   = carregar_dados("candidatos")
    total_clt = len(df_col[df_col['tipo']=='CLT']) if not df_col.empty else 0
    total_pj  = len(df_col[df_col['tipo']=='PJ'])  if not df_col.empty else 0
    total_est = len(df_est) if not df_est.empty else 0
    total_all = (len(df_col) if not df_col.empty else 0) + total_est

    st.markdown(krow(
        kpi_card("Total Colaboradores", total_all,  "b", icon="👥"),
        kpi_card("Estagiários Ativos",  total_est,  "g", icon="🎓"),
        kpi_card("PJ",                  total_pj,   "c", icon="🤝"),
        kpi_card("CLT",                 total_clt,  "p", icon="📄"), cols=4
    ), unsafe_allow_html=True)

    col_l, col_r = st.columns([1.6, 1])
    with col_l:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown(panel_title("Progresso dos Contratos de Estágio", "var(--amber)"), unsafe_allow_html=True)
        if not df_est.empty:
            hoje = date.today()
            for _, r in df_est.iterrows():
                try:
                    ini = pd.to_datetime(r['data_inicio']).date()
                    fim = pd.to_datetime(r['data_fim']).date()
                    total_d = (fim - ini).days
                    passado = (hoje - ini).days
                    pct = min(max(passado / total_d * 100, 0), 100) if total_d > 0 else 100
                    color = "#0d7a3e" if pct < 60 else "#b45309" if pct < 85 else "#c0392b"
                    st.markdown(prog_bar(r['estagiario'], pct, color), unsafe_allow_html=True)
                except Exception:
                    pass
        else:
            st.markdown('<div class="empty-state"><div class="empty-icon">🎓</div><div class="empty-title">Sem contratos cadastrados</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_r:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown(panel_title("Distribuição por Vínculo", "var(--green)"), unsafe_allow_html=True)
        if total_all > 0:
            labels = ['Estagiários','PJ','CLT']
            vals   = [total_est, total_pj, total_clt]
            colors = ['#0d7a3e','#1565c0','#6d28d9']
            fig = go.Figure(go.Pie(labels=labels, values=vals, hole=0.6,
                                   marker=dict(colors=colors, line=dict(width=0))))
            fig.update_layout(margin=dict(t=5,b=5,l=5,r=5), showlegend=False,
                              paper_bgcolor='rgba(0,0,0,0)', height=180)
            st.plotly_chart(fig, use_container_width=True)
            legend_html = "".join([f'<div class="d-leg-item"><div class="d-leg-swatch" style="background:{c}"></div><div class="d-leg-name">{l}</div><div class="d-leg-val">{v}</div><div class="d-leg-pct">{v/total_all*100:.0f}%</div></div>'
                                   for l,v,c in zip(labels,vals,colors) if v > 0])
            st.markdown(f'<div class="d-legend">{legend_html}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    col_al, col_ar = st.columns(2)
    hoje_dt = date.today()
    with col_al:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown(panel_title("Avaliações de 90 dias (próximos 7 dias)", "var(--amber)"), unsafe_allow_html=True)
        alertas = []
        if not df_exp.empty:
            for _, r in df_exp.iterrows():
                if r['data_inicio']:
                    d90 = pd.to_datetime(r['data_inicio']).date() + timedelta(days=90)
                    if not r.get('av2_feito') and (d90 - hoje_dt).days <= 7:
                        alertas.append((r['nome'], d90))
        if alertas:
            for nome, d90 in alertas:
                st.markdown(f'<div class="pe-card"><div class="pe-dot" style="background:var(--amber)"></div><div class="pe-info"><div class="pe-name">{nome}</div><div class="pe-meta">Vencimento: {d90.strftime("%d/%m/%Y")}</div></div>{badge("⚠ pendente","warn")}</div>', unsafe_allow_html=True)
        else:
            st.markdown(notif("✓ Nenhuma avaliação vencendo nos próximos 7 dias", "ok"), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_ar:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown(panel_title("Bônus de Indicação liberados", "var(--green)"), unsafe_allow_html=True)
        avisos = []
        if not df_c.empty:
            for _, cand in df_c[(df_c['status_geral']=='Finalizada') & (df_c['indicado_por'].notna()) & (df_c['indicado_por']!='')].iterrows():
                if cand['data_inicio']:
                    data_lib = pd.to_datetime(cand['data_inicio']).date() + timedelta(days=90)
                    if hoje_dt >= data_lib:
                        avisos.append((cand['indicado_por'], cand['candidato']))
        if avisos:
            for ind, cand_n in avisos:
                st.markdown(f'<div class="pe-card"><div class="pe-dot" style="background:var(--green)"></div><div class="pe-info"><div class="pe-name">{ind}</div><div class="pe-meta">Indicação de {cand_n}</div></div>{badge("✓ liberado","ok")}</div>', unsafe_allow_html=True)
        else:
            st.markdown(notif("✓ Sem bônus pendentes de liberação", "ok"), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ── ESTAGIÁRIOS ───────────────────────────────────────────
elif menu == "🎓 Estagiários":
    st.markdown(topbar("Contratos de Estágio", "🎓", "DP"), unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1.4])
    with col1:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown(panel_title("Novo Registro", "var(--green)"), unsafe_allow_html=True)
        with st.form("f_est", clear_on_submit=True):
            n  = st.text_input("Nome Completo")
            i  = st.text_input("Instituição de Ensino")
            t  = st.selectbox("Time", ["Tecnologia","Comercial","Operações","RH","Financeiro","Marketing"])
            c1e, c2e = st.columns(2)
            di = c1e.date_input("Início")
            df_fim = c2e.date_input("Fim")
            if st.form_submit_button("Cadastrar Estagiário", type="primary", use_container_width=True):
                if n:
                    executar_sql("INSERT INTO contratos_estagio (estagiario,instituicao,data_inicio,data_fim,time_equipe) VALUES (:n,:i,:di,:df,:t)",
                                 {"n":n,"i":i,"di":di,"df":df_fim,"t":t})
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        df_e = carregar_dados("contratos_estagio")
        st.markdown(f'<div class="panel"><div class="panel-head">{panel_title("Estagiários Cadastrados","var(--blue)")}<span style="font-size:10px;color:var(--mut)">Total: <strong>{len(df_e)}</strong></span></div>', unsafe_allow_html=True)
        if not df_e.empty:
            for _, r in df_e.iterrows():
                checks = sum([bool(r['solic_contrato_dp']),bool(r['assina_etus']),bool(r['assina_faculdade']),bool(r['envio_juridico'])])
                with st.expander(f"{r['estagiario']} · {r['time_equipe']} · {badge(f'{checks}/4','ok' if checks==4 else 'warn')}"):
                    ca, cb, cc, cd = st.columns(4)
                    s  = ca.checkbox("Solic. DP",  value=bool(r['solic_contrato_dp']),  key=f"s{r['id']}")
                    ae = cb.checkbox("ETUS",        value=bool(r['assina_etus']),         key=f"ae{r['id']}")
                    af = cc.checkbox("Faculdade",   value=bool(r['assina_faculdade']),    key=f"af{r['id']}")
                    ej = cd.checkbox("Jurídico",    value=bool(r['envio_juridico']),      key=f"ej{r['id']}")
                    b1, b2 = st.columns(2)
                    if b1.button("Salvar", key=f"svest{r['id']}", type="primary", use_container_width=True):
                        executar_sql("UPDATE contratos_estagio SET solic_contrato_dp=:s,assina_etus=:ae,assina_faculdade=:af,envio_juridico=:ej WHERE id=:id",
                                     {"s":s,"ae":ae,"af":af,"ej":ej,"id":r['id']}); st.rerun()
                    if b2.button("Excluir", key=f"delest{r['id']}", use_container_width=True):
                        executar_sql("DELETE FROM contratos_estagio WHERE id=:id", {"id":r['id']}); st.rerun()
        else:
            st.markdown('<div class="empty-state"><div class="empty-icon">🎓</div><div class="empty-title">Nenhum estagiário cadastrado</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ── COLABORADORES ─────────────────────────────────────────
elif menu == "👥 Colaboradores":
    st.markdown(topbar("Gestão de Colaboradores", "👥", "DP"), unsafe_allow_html=True)
    df_col = carregar_dados("colaboradores_ativos")
    lista_mod = ["CLT","PJ","Estagiário","Trainee","Freelancer"]

    if not df_col.empty:
        total_pj2  = len(df_col[df_col['tipo']=='PJ'])
        total_clt2 = len(df_col[df_col['tipo']=='CLT'])
        pend_ben   = int(df_col[~df_col['cad_starbem'].fillna(False)].shape[0])
        st.markdown(krow(
            kpi_card("Total PJ",            total_pj2,  "b", icon="🤝"),
            kpi_card("CLT",                 total_clt2, "g", icon="📄"),
            kpi_card("Benefícios Pendentes", pend_ben,  "a" if pend_ben>0 else "g",
                     "atenção" if pend_ben>0 else "✓ ok", "dn" if pend_ben>0 else "ok", icon="💰"),
            cols=3
        ), unsafe_allow_html=True)

    with st.expander("➕ Cadastrar Novo Colaborador"):
        with st.form("f_col_manual", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            n_col = c1.text_input("Nome")
            t_col = c2.selectbox("Tipo", lista_mod)
            d_adm = c3.date_input("Admissão", value=date.today())
            if st.form_submit_button("Cadastrar", type="primary"):
                if n_col:
                    executar_sql("INSERT INTO colaboradores_ativos (nome,tipo,data_admissao) VALUES (:n,:t,:d)",
                                 {"n":n_col,"t":t_col,"d":d_adm}); st.rerun()

    if not df_col.empty:
        for _, r in df_col.iterrows():
            bens = sum([bool(r['cad_starbem']),bool(r['incl_amil']),bool(r['ifood_ativo']),bool(r['equipamento_entregue'])])
            with st.expander(f"{r['nome']} · {badge(r['tipo'],'info')} · {badge(f'{bens}/4 benefícios','ok' if bens==4 else 'warn')}"):
                c_tp,c1,c2,c3,c4 = st.columns([1.5,1,1,1,1])
                novo_tipo = c_tp.selectbox("Tipo",lista_mod,index=lista_mod.index(r['tipo']) if r['tipo'] in lista_mod else 0,key=f"tipo{r['id']}")
                star = c1.checkbox("Starbem",   value=bool(r['cad_starbem']),          key=f"star{r['id']}")
                amil = c2.checkbox("AMIL",       value=bool(r['incl_amil']),             key=f"amil{r['id']}")
                ifoo = c3.checkbox("iFood",       value=bool(r['ifood_ativo']),           key=f"ifoo{r['id']}")
                equi = c4.checkbox("Equip.",      value=bool(r['equipamento_entregue']),  key=f"equi{r['id']}")
                b1,b2 = st.columns(2)
                if b1.button("Salvar", key=f"svb{r['id']}", type="primary", use_container_width=True):
                    executar_sql("UPDATE colaboradores_ativos SET tipo=:t,cad_starbem=:s,incl_amil=:a,ifood_ativo=:i,equipamento_entregue=:e WHERE id=:id",
                                 {"t":novo_tipo,"s":star,"a":amil,"i":ifoo,"e":equi,"id":r['id']}); st.rerun()
                if b2.button("Excluir", key=f"delcol{r['id']}", use_container_width=True):
                    executar_sql("DELETE FROM colaboradores_ativos WHERE id=:id", {"id":r['id']}); st.rerun()
    else:
        st.markdown('<div class="empty-state"><div class="empty-icon">👥</div><div class="empty-title">Nenhum colaborador cadastrado</div></div>', unsafe_allow_html=True)


# ── PERÍODO DE EXPERIÊNCIA ────────────────────────────────
elif menu == "⏳ Período de Experiência":
    st.markdown(topbar("Período de Experiência · 90 dias", "⏳", "DP"), unsafe_allow_html=True)
    df_exp = carregar_dados("controle_experiencia")
    hoje_dt = date.today()

    vencendo = sum(1 for _, r in df_exp.iterrows()
                   if r['data_inicio'] and not r.get('av2_feito')
                   and (pd.to_datetime(r['data_inicio']).date() + timedelta(days=90) - hoje_dt).days <= 30) if not df_exp.empty else 0
    if vencendo > 0:
        st.markdown(notif(f"⏰ {vencendo} avaliação(ões) vencem nos próximos 30 dias.", "warn"), unsafe_allow_html=True)

    col_cad, col_gst = st.columns([1, 1.6])
    with col_cad:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown(panel_title("Cadastrar Novo Período", "var(--green)"), unsafe_allow_html=True)
        with st.form("f_exp_cad", clear_on_submit=True):
            n_exp = st.text_input("Nome do Prestador / Estagiário")
            c_exp = st.text_input("Cargo")
            t_exp = st.selectbox("Time", ["Tecnologia","Comercial","Operações","RH","Financeiro","Marketing"])
            d_ini = st.date_input("Data de Início", value=date.today())
            if st.form_submit_button("Cadastrar", type="primary", use_container_width=True):
                if n_exp:
                    executar_sql("INSERT INTO controle_experiencia (nome,cargo,time_equipe,data_inicio) VALUES (:n,:c,:t,:d)",
                                 {"n":n_exp,"c":c_exp,"t":t_exp,"d":d_ini})
                    st.success("✓ Cadastrado!"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col_gst:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown(panel_title("Gestão de Avaliações", "var(--blue)"), unsafe_allow_html=True)
        if not df_exp.empty:
            for _, r in df_exp.iterrows():
                d90 = pd.to_datetime(r['data_inicio']).date() + timedelta(days=90)
                status_t = "aprovado" if r['av2_feito'] else "pendente"
                st.markdown(pe_card(r['nome'], r['cargo'] or '', r['time_equipe'] or '', d90.strftime('%d/%m/%Y'), status_t), unsafe_allow_html=True)
                with st.expander(f"Editar — {r['nome']}"):
                    c1e, c2e = st.columns(2)
                    v2  = c1e.checkbox("Avaliação feita", value=bool(r['av2_feito']), key=f"v2{r['id']}")
                    dt2_val = r['av2_data'] if r['av2_data'] is not None else d90
                    dt2 = c2e.date_input("Data da avaliação", value=dt2_val, key=f"dt2{r['id']}")
                    r2  = st.text_input("Avaliador responsável", value=r['av2_responsavel'] or '', key=f"r2{r['id']}")
                    b1, b2 = st.columns(2)
                    if b1.button("Salvar", key=f"svexp{r['id']}", type="primary", use_container_width=True):
                        executar_sql("UPDATE controle_experiencia SET av2_feito=:v2,av2_responsavel=:r2,av2_data=:dt2 WHERE id=:id",
                                     {"v2":v2,"r2":r2,"dt2":dt2,"id":r['id']}); st.success("✓ Salvo!"); st.rerun()
                    if b2.button("Excluir", key=f"delexp{r['id']}", use_container_width=True):
                        executar_sql("DELETE FROM controle_experiencia WHERE id=:id", {"id":r['id']}); st.rerun()
        else:
            st.markdown('<div class="empty-state"><div class="empty-icon">⏳</div><div class="empty-title">Nenhum período cadastrado</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ── IFOOD ─────────────────────────────────────────────────
elif menu == "🍔 iFood":
    st.markdown(topbar("Notas Fiscais · iFood", "🍔", "Financeiro"), unsafe_allow_html=True)
    df_if = carregar_dados("notas_fiscais_ifood")
    st.markdown(krow(
        kpi_card("Notas Cadastradas", len(df_if), "g", icon="📄"),
        kpi_card("Empresas", df_if['empresa'].nunique() if not df_if.empty else 0, "b", icon="🏢"),
        cols=2
    ), unsafe_allow_html=True)

    with st.expander("➕ Cadastrar Nova Nota iFood"):
        with st.form("form_ifood", clear_on_submit=True):
            c1, c2 = st.columns(2)
            eni = c1.selectbox("Empresa", ["ETUS","BHAZ","Evolution","E3J","No Name"])
            mni = c2.selectbox("Mês de Referência", ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"])
            uni = st.file_uploader("Upload da NF (PDF)", type=["pdf"])
            if st.form_submit_button("Salvar Nota iFood", type="primary"):
                if uni:
                    executar_sql("INSERT INTO notas_fiscais_ifood (empresa,mes_referencia,arquivo_nf,nome_arquivo,data_upload) VALUES (:e,:m,:a,:n,:d)",
                                 {"e":eni,"m":mni,"a":uni.read(),"n":uni.name,"d":date.today()})
                    st.success("✓ Nota salva!"); st.rerun()

    if not df_if.empty:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown(panel_title("Histórico de Notas", "var(--green)"), unsafe_allow_html=True)
        html_t = "<table><thead><tr><th>Empresa</th><th>Mês Ref.</th><th>Arquivo</th><th>Data Upload</th></tr></thead><tbody>"
        for _, r in df_if.iterrows():
            html_t += f"<tr><td style='font-weight:600'>{r['empresa']}</td><td>{r['mes_referencia']}</td><td style='color:var(--blue)'>{r['nome_arquivo']}</td><td style='color:var(--mut)'>{r['data_upload']}</td></tr>"
        html_t += "</tbody></table>"
        st.markdown(html_t, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        for _, r in df_if.iterrows():
            with st.expander(f"📄 {r['mes_referencia']} · {r['empresa']}"):
                arq = carregar_arquivo("notas_fiscais_ifood", "arquivo_nf", r['id'])
                c1, c2 = st.columns(2)
                if arq:
                    c1.download_button("📥 Baixar NF", arq, r['nome_arquivo'], key=f"dl_if_{r['id']}")
                else:
                    c1.caption("Arquivo indisponível")
                if c2.button("🗑️ Excluir", key=f"del_if_{r['id']}"):
                    executar_sql("DELETE FROM notas_fiscais_ifood WHERE id=:id", {"id":r['id']}); st.rerun()
    else:
        st.markdown('<div class="empty-state"><div class="empty-icon">🍔</div><div class="empty-title">Nenhuma nota cadastrada</div><div class="empty-sub">Clique em "+ Cadastrar Nova Nota iFood" para começar</div></div>', unsafe_allow_html=True)


# ── OUTROS PAGAMENTOS ─────────────────────────────────────
elif menu == "💸 Outros Pagamentos":
    st.markdown(topbar("Outros Pagamentos", "💸", "Financeiro"), unsafe_allow_html=True)
    df_pg = carregar_dados("pagamentos_gerais")
    total_val = float(df_pg['valor_pg'].sum()) if not df_pg.empty else 0
    st.markdown(krow(
        kpi_card("Registros",       len(df_pg),              "b", icon="📋"),
        kpi_card("Valor Acumulado", f"R$ {total_val:,.0f}", "g", icon="💰"),
        cols=2
    ), unsafe_allow_html=True)

    with st.expander("➕ Lançar Novo Pagamento", expanded=True):
        with st.form("form_pg_geral", clear_on_submit=True):
            c1, c2 = st.columns(2)
            epg = c1.selectbox("Empresa", ["Plusdin São Bernardo","Projeto Consegui Aprender"])
            mpg = c2.selectbox("Mês de Referência", ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"])
            c3, c4 = st.columns([1,2])
            val_pg    = c3.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f")
            motivo_pg = c4.text_input("Motivo (Ex: Internet, Aluguel)")
            c5, c6 = st.columns(2)
            d_envio = c5.date_input("Data de Envio",     value=date.today())
            d_pago  = c6.date_input("Data de Pagamento", value=date.today())
            upg = st.file_uploader("Comprovante (PDF)", type=["pdf"])
            if st.form_submit_button("Registrar Pagamento", type="primary"):
                if upg:
                    executar_sql("""INSERT INTO pagamentos_gerais (empresa,categoria,mes_referencia,arquivo_pg,nome_arquivo,data_upload,valor_pg,data_envio,data_pagamento,motivo)
                        VALUES (:e,'Geral',:m,:a,:n,:d,:v,:de,:dp,:mo)""",
                        {"e":epg,"m":mpg,"a":upg.read(),"n":upg.name,"d":date.today(),"v":val_pg,"de":d_envio,"dp":d_pago,"mo":motivo_pg})
                    st.success("✓ Pagamento registrado!"); st.rerun()

    if not df_pg.empty:
        f_emp = st.multiselect("Filtrar Empresa", df_pg['empresa'].unique(), default=list(df_pg['empresa'].unique()))
        df_f  = df_pg[df_pg['empresa'].isin(f_emp)]
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown(panel_title("Histórico de Pagamentos", "var(--blue)"), unsafe_allow_html=True)
        html_t = "<table><thead><tr><th>Empresa</th><th>Motivo</th><th>Mês Ref.</th><th>Valor</th><th>Data Pgto</th></tr></thead><tbody>"
        for _, r in df_f.iterrows():
            val = r.get('valor_pg') or 0
            html_t += f"<tr><td style='font-weight:600'>{r['empresa']}</td><td>{r.get('motivo','—')}</td><td style='color:var(--mut)'>{r['mes_referencia']}</td><td style='font-weight:700;color:var(--green)'>R$ {float(val):,.2f}</td><td style='color:var(--mut)'>{r.get('data_pagamento','—')}</td></tr>"
        html_t += "</tbody></table>"
        st.markdown(html_t, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        for _, row in df_f.iterrows():
            val = row.get('valor_pg') or 0
            with st.expander(f"R$ {float(val):,.2f} · {row['empresa']} · {row.get('motivo','—')}"):
                cb1, cb2 = st.columns(2)
                arq = carregar_arquivo("pagamentos_gerais", "arquivo_pg", row['id'])
                if arq:
                    cb1.download_button("📥 Baixar Comprovante", arq, row['nome_arquivo'], key=f"dl_pg_{row['id']}")
                else:
                    cb1.caption("Arquivo indisponível")
                if cb2.button("🗑️ Excluir", key=f"del_pg_{row['id']}"):
                    executar_sql("DELETE FROM pagamentos_gerais WHERE id=:id", {"id":row['id']}); st.rerun()
    else:
        st.markdown('<div class="empty-state"><div class="empty-icon">💸</div><div class="empty-title">Nenhum pagamento registrado</div></div>', unsafe_allow_html=True)


# ── DASHBOARD FINANCEIRO ──────────────────────────────────
elif menu == "📊 Dashboard Financeiro":
    st.markdown(topbar("Dashboard Financeiro", "📊", "Financeiro"), unsafe_allow_html=True)
    df_pg = carregar_dados("pagamentos_gerais")
    df_if = carregar_dados("notas_fiscais_ifood")

    if not df_pg.empty:
        total_ac = float(df_pg['valor_pg'].sum())
        st.markdown(krow(
            kpi_card("Gasto Total",  f"R$ {total_ac:,.0f}", "r", icon="💸"),
            kpi_card("Pagamentos",    len(df_pg),            "b", icon="📋"),
            kpi_card("Notas iFood",   len(df_if),            "g", icon="🍔"),
            cols=3
        ), unsafe_allow_html=True)

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown('<div class="panel">', unsafe_allow_html=True)
            st.markdown(panel_title("Gastos por Empresa", "var(--green)"), unsafe_allow_html=True)
            gastos_emp = df_pg.groupby('empresa')['valor_pg'].sum().reset_index()
            fig = px.pie(gastos_emp, values='valor_pg', names='empresa', hole=0.5,
                         color_discrete_sequence=['#0d7a3e','#1565c0','#b45309','#6d28d9','#0277bd'])
            fig.update_layout(margin=dict(t=5,b=5,l=5,r=5), paper_bgcolor='rgba(0,0,0,0)',
                              legend=dict(font=dict(size=10,color="#6b7a99")), height=240)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_r:
            st.markdown('<div class="panel">', unsafe_allow_html=True)
            st.markdown(panel_title("Gastos por Mês", "var(--blue)"), unsafe_allow_html=True)
            meses_ordem = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
            gastos_mes = df_pg.groupby('mes_referencia')['valor_pg'].sum().reset_index()
            gastos_mes['mes_referencia'] = pd.Categorical(gastos_mes['mes_referencia'], categories=meses_ordem, ordered=True)
            gastos_mes = gastos_mes.sort_values('mes_referencia')
            fig2 = px.line(gastos_mes, x='mes_referencia', y='valor_pg', markers=True,
                           line_shape="spline", color_discrete_sequence=['#1565c0'])
            fig2.update_layout(margin=dict(t=5,b=5,l=5,r=5), paper_bgcolor='rgba(0,0,0,0)',
                               plot_bgcolor='rgba(0,0,0,0)', height=240,
                               xaxis=dict(tickfont=dict(size=10,color="#6b7a99"), gridcolor="rgba(0,0,0,0.05)"),
                               yaxis=dict(tickfont=dict(size=10,color="#6b7a99"), gridcolor="rgba(0,0,0,0.05)"))
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown(panel_title("Ranking de Maiores Despesas", "var(--red)"), unsafe_allow_html=True)
        ranking = df_pg.nlargest(5, 'valor_pg')[['empresa','motivo','valor_pg','mes_referencia']]
        html_r = "<table><thead><tr><th>#</th><th>Empresa</th><th>Motivo</th><th>Mês</th><th>Valor</th></tr></thead><tbody>"
        for i, (_, r) in enumerate(ranking.iterrows(), 1):
            html_r += f"<tr><td style='font-family:var(--fd);font-weight:700;color:var(--mut)'>{i}</td><td style='font-weight:600'>{r['empresa']}</td><td>{r.get('motivo','—')}</td><td style='color:var(--mut)'>{r['mes_referencia']}</td><td style='font-weight:700;color:var(--red)'>R$ {float(r['valor_pg']):,.2f}</td></tr>"
        html_r += "</tbody></table>"
        st.markdown(html_r, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-state"><div class="empty-icon">📊</div><div class="empty-title">Aguardando dados financeiros</div><div class="empty-sub">Registre pagamentos para visualizar os indicadores</div></div>', unsafe_allow_html=True)
