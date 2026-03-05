import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import unicodedata
import os
import base64
import numpy as np

# ==============================================================================
# 1. Configuração da Página
# ==============================================================================
st.set_page_config(
    page_title="Dashboard Financeiro de Pessoas | V4", 
    layout="wide",
    page_icon="favicon.png",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return ""

def set_png_as_page_bg(png_file):
    bin_str = get_base64_of_bin_file(png_file)
    if bin_str:
        page_bg_img = '''
        <style>
        [data-testid="stAppViewContainer"] {
            background-image: url("data:image/jpg;base64,%s");
            background-size: cover;
            background-position: center center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }
        [data-testid="stSidebar"] {
            background-color: rgba(255, 255, 255, 0.95);
        }
        .login-box {
            background-color: rgba(0, 0, 0, 0.85);
            padding: 40px;
            border-radius: 15px;
            color: white;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.1);
        }
        .login-box h1 { font-size: 26px; color: white !important; margin-bottom: 10px; }
        .login-box h3 { font-size: 18px; color: #ff4b4b !important; margin-top: 0; font-weight: 500; margin-bottom: 20px; }
        .login-box p { font-size: 14px; color: #cccccc !important; }
        
        .stProgress > div > div > div > div { background-color: #ff4b4b; }
        .home-title {
            margin-bottom: 0px;
            display: flex;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap; 
        }
        button[data-baseweb="tab"] {
            font-size: 16px !important;
            font-weight: 600 !important;
        }
        .dataframe { font-size: 14px !important; }
        
        /* Estilos das Tags de Benefícios */
        .badge-base { padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; color: white; display: inline-block; margin-right: 5px; margin-bottom: 5px; }
        .bg-saude { background-color: #cc0000; }
        .bg-educacao { background-color: #0044cc; }
        .bg-outros { background-color: #ff9900; color: black !important; }
        </style>
        ''' % bin_str
        st.markdown(page_bg_img, unsafe_allow_html=True)

def formatar_moeda(valor):
    try:
        if pd.isna(valor): return "R$ 0,00"
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def remover_acentos(texto):
    try:
        nfkd = unicodedata.normalize('NFKD', str(texto))
        return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    except:
        return str(texto).lower()

def get_mes_ordem(nome_mes):
    MAPA_MESES = {'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
                  'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12}
    return MAPA_MESES.get(str(nome_mes).lower()[:3], 99)

def limpar_nome_mes(nome_sujo):
    try:
        return str(nome_sujo).split('.')[0].split('/')[0].capitalize()[:3]
    except:
        return str(nome_sujo)

def achar_coluna(df, termos):
    colunas_normalizadas = {col: remover_acentos(col) for col in df.columns}
    for termo in termos:
        termo_limpo = remover_acentos(termo)
        for col_original, col_limpa in colunas_normalizadas.items():
            if termo_limpo in col_limpa:
                return col_original
    return None

@st.cache_data(ttl=600)
def load_data(gid):
    if not gid: return None
    PUB_ID = "2PACX-1vRDOYmkYSNo7Ttbw0GM5YhDH3nYafq-Jg2o-fk1LaFOYjRw9oKQhwVe8YvBTdrmtOdzVsQdw-koM2oz"
    url = f"https://docs.google.com/spreadsheets/d/e/{PUB_ID}/pub?gid={gid}&single=true&output=csv"
    
    try:
        df = pd.read_csv(url)
        termos_financeiros = ["custo", "valor", "total", "orçado", "realizado", "budget", "soma", "mensalidade", "preço"]
        for col in df.columns:
            col_norm = remover_acentos(col)
            eh_financeiro = any(t in col_norm for t in termos_financeiros)
            
            primeiro_valor = df[col].dropna().iloc[0] if not df[col].dropna().empty else ""
            tem_cifrao = "R$" in str(primeiro_valor)
            
            if eh_financeiro or tem_cifrao:
                 if df[col].dtype == "object":
                    df[col] = df[col].astype(str).str.replace("R$", "", regex=False)
                    df[col] = df[col].str.replace(" ", "", regex=False)
                    df[col] = df[col].str.replace(".", "", regex=False) 
                    df[col] = df[col].str.replace(",", ".", regex=False) 
                 df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df
    except:
        return None

def padronizar_colunas(df, nome_beneficio):
    if df is None or df.empty: return None

    col_razao = achar_coluna(df, ["razão social", "razao social", "empresa", "cliente", "nome fantasia", "unidade"])
    col_status = achar_coluna(df, ["status", "situacao"])
    col_plano = achar_coluna(df, ["plano", "produto"])
    col_tipo_usuario = achar_coluna(df, ["usuário", "usuario", "tipo"]) 
    col_nome = achar_coluna(df, ["nome", "beneficiario", "colaborador"])
    col_valor_titular = achar_coluna(df, ["valor titular", "custo titular"])
    col_valor_dep = achar_coluna(df, ["valor dependente", "custo dependente"])
    col_valor_unico = achar_coluna(df, ["valor", "custo", "preço", "mensalidade"])

    if not col_razao: return None 
    if col_status: df = df[df[col_status].astype(str).str.lower() == 'active'].copy()
    
    df['Custo_Calculado'] = 0.0
    if col_tipo_usuario and col_valor_titular and col_valor_dep:
        df['Custo_Calculado'] = np.where(df[col_tipo_usuario].astype(str).str.lower().str.contains('titular'), df[col_valor_titular], df[col_valor_dep])
    elif col_valor_unico:
        df['Custo_Calculado'] = df[col_valor_unico]
    df['Custo_Calculado'] = df['Custo_Calculado'].fillna(0)

    if col_plano: df['Benefício_Final'] = df[col_plano]
    else: df['Benefício_Final'] = nome_beneficio

    df = df.rename(columns={col_razao: 'Razão Social', col_nome: 'Nome', 'Benefício_Final': 'Benefício'})
    
    if 'Regional' not in df.columns:
        col_reg = achar_coluna(df, ["regional", "região", "estado"])
        df['Regional'] = df[col_reg] if col_reg else 'Geral'
        
    cols_uteis = ['Razão Social', 'Benefício', 'Custo_Calculado', 'Nome', 'Regional']
    if 'Nome' not in df.columns: df['Nome'] = 'Colaborador'
    return df[cols_uteis]

def processar_consultas(df):
    if df is None or df.empty: return None
    col_razao = achar_coluna(df, ["razão social", "razao social", "empresa"])
    col_status = achar_coluna(df, ["status consulta", "status"])
    col_especialidade = achar_coluna(df, ["especialidade", "tipo consulta"])
    if not col_razao: return None
    
    mapping = {col_razao: 'Razão Social'}
    if col_status: mapping[col_status] = 'Status_Consulta'
    if col_especialidade: mapping[col_especialidade] = 'Especialidade'
    
    df = df.rename(columns=mapping)
    if 'Status_Consulta' not in df.columns: df['Status_Consulta'] = 'Realizada'
    if 'Especialidade' not in df.columns: df['Especialidade'] = 'Geral'
    
    return df[['Razão Social', 'Status_Consulta', 'Especialidade']]

# ==============================================================================
# 🔒 SISTEMA DE LOGIN
# ==============================================================================
def check_password():
    CREDENCIAIS = {"Admin Opers": "BenefitsV4Company", "diretoria": "V4Diretoria2026"}
    def password_entered():
        user = st.session_state.get("username", "")
        pwd = st.session_state.get("password", "")
        if user in CREDENCIAIS and pwd == CREDENCIAIS[user]:
            st.session_state["password_correct"] = True
            st.session_state["usuario_logado"] = user
            st.session_state["role"] = "admin" if user == "Admin Opers" else "viewer"
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False): return True
    if os.path.exists("capa_login.jpg.jpg"): set_png_as_page_bg("capa_login.jpg.jpg")
    elif os.path.exists("capa_login.jpg"): set_png_as_page_bg("capa_login.jpg")

    col_esq, col_centro, col_dir = st.columns([1, 2, 1])
    with col_centro:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container():
            st.markdown("""<div class="login-box"><h1>🔒 Acesso Restrito</h1><h3>People Analytics Financeiro V4</h3><p>Entre com as credenciais corporativas V4.</p></div>""", unsafe_allow_html=True)
            st.text_input("Usuário", key="username")
            st.text_input("Senha", type="password", key="password")
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("Entrar no Painel", on_click=password_entered, type="primary", use_container_width=True)
            if "password_correct" in st.session_state and not st.session_state["password_correct"]: st.error("🚫 Usuário ou senha incorretos.")
        st.markdown("<br><br>", unsafe_allow_html=True)
    return False

if not check_password(): st.stop()

def recarregar_app():
    if hasattr(st, "rerun"): st.rerun()
    else: st.experimental_rerun()

# ==============================================================================
# NAVEGAÇÃO EXPANDIDA
# ==============================================================================
usuario_atual = st.session_state.get("usuario_logado", "Visitante")
role = st.session_state.get("role", "viewer")
st.sidebar.success(f"👤 **{usuario_atual}**")
if role == "admin": st.sidebar.caption("🔧 Modo Admin Ativo")
st.sidebar.markdown("---")

GID_2026 = "1350897026"
GID_2025 = "1743422062"
GID_BASE_COMPLETA = "1919747553" # Saúde
GID_WYDEN = "" 
GID_EP = "" 
GID_STAAGE = ""
GID_CONSULTAS = "" # Consultas

OPCOES_MENU = [
    "Início", 
    "Visão Global de Pessoas",        # NOVO
    "Orçamento de Benefícios", 
    "Análise Financeira", 
    "Benefits Efficiency Map",
    "Sazonalidade Preditiva",         # NOVO
    "Simulador & Reinvestimento"      # NOVO
]
st.sidebar.header("Navegação Estratégica")
aba_selecionada = st.sidebar.radio("Escolha a Visão:", OPCOES_MENU, label_visibility="collapsed")

st.sidebar.markdown("<br><br><br>", unsafe_allow_html=True) 
if st.sidebar.button("🔄 Atualizar Dados", use_container_width=True):
    st.cache_data.clear()
    recarregar_app()
if st.sidebar.button("Sair / Logout", use_container_width=True):
    st.session_state["password_correct"] = False
    recarregar_app()

# ==============================================================================
# LÓGICA DAS TELAS
# ==============================================================================

if aba_selecionada == "Início":
    st.markdown("<br>", unsafe_allow_html=True)
    logo_b64 = ""
    if os.path.exists("favicon.png"): logo_b64 = get_base64_of_bin_file("favicon.png")
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height: 65px;">' if logo_b64 else ""
    st.markdown(f"""
        <div style="background-color: #1e1e1e; padding: 35px; border-radius: 12px; border-left: 6px solid #ff4b4b; box-shadow: 0 4px 10px rgba(0,0,0,0.4); margin-bottom: 30px;">
            <h1 class="home-title" style="color: white; margin-top: 0px;">{logo_html} People Analytics Financeiro</h1>
            <h3 style="color: #ff4b4b; font-weight: 500; margin-top: 15px; margin-bottom: 10px;">Inteligência de Custos e Benefícios V4.</h3>
            <p style="color: #cccccc; font-size: 16px; max-width: 900px; margin-bottom: 0px;">Painel executivo para gestão de folha, acompanhamento orçamentário, predição de sazonalidade e simulador de reinvestimento em talentos.</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📈 Visão Executiva: Evolução do Custo Anual de Benefícios")
    st.caption("Acompanhamento da estabilização de custos (Períodos 1 a 12).")
    
    dados_totais = {
        "Período": ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "P11", "P12"],
        "Custo": [261554.66, 267902.94, 272756.06, 281187.74, 283075.06, 282339.74, 286653.62, 288124.26, 288859.58, 290330.22, 290330.22, 290330.22]
    }
    df_trend = pd.DataFrame(dados_totais)
    total_ano = df_trend["Custo"].sum()
    media_mes = df_trend["Custo"].mean()
    crescimento = (df_trend["Custo"].iloc[-1] / df_trend["Custo"].iloc[0]) - 1

    col1, col2, col3 = st.columns(3)
    col1.metric("Custo Total Anual", f"R$ {total_ano/1000000:.2f} Milhões")
    col2.metric("Média por Período", f"R$ {media_mes/1000:.1f}k")
    col3.metric("Inflação da Carteira (P1 a P12)", f"+{crescimento*100:.1f}%", delta="Aumento estabilizado", delta_color="inverse")

    df_trend['Texto_Exibicao'] = df_trend['Custo'].apply(lambda x: f"R$ {x/1000:.0f}k")
    fig_executivo = px.bar(df_trend, x="Período", y="Custo", text='Texto_Exibicao')
    fig_executivo.add_scatter(x=df_trend['Período'], y=df_trend['Custo'], mode='lines+markers', name='Curva', line=dict(color='#cc0000', width=3), marker=dict(size=8, color='#cc0000'), showlegend=False)
    fig_executivo.update_traces(marker_color='#d3d3d3', textposition='outside')
    fig_executivo.update_layout(template="plotly_white", yaxis_visible=False, xaxis_title="", height=350, margin=dict(t=30, b=0, l=0, r=0))
    st.plotly_chart(fig_executivo, use_container_width=True)

# ------------------------------------------------------------------------------
# 🆕 NOVA TELA: VISÃO GLOBAL DE PESSOAS
# ------------------------------------------------------------------------------
elif aba_selecionada == "Visão Global de Pessoas":
    st.header("🏢 Visão Global do Custo de Pessoas")
    st.caption("Integração de Folha de Pagamento, Encargos e Benefícios (Base Demonstrativa).")
    
    st.info("ℹ️ **Módulo em Desenvolvimento:** Esta tela exibirá dados reais assim que as planilhas de Folha/RH forem integradas.")
    
    # Dados Simulados (Mockup de Folha)
    mock_folha = 15000000 # 15 Milhões em Folha
    mock_encargos = 6000000 # 6 Milhões em Encargos
    mock_beneficios = 3383444 # Nossos 3.3 Milhões Reais
    custo_total_pessoas = mock_folha + mock_encargos + mock_beneficios
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Custo Total de Pessoas (Ano)", formatar_moeda(custo_total_pessoas))
    c2.metric("Folha Salarial Bruta", formatar_moeda(mock_folha))
    c3.metric("Encargos Trabalhistas (INSS/FGTS)", formatar_moeda(mock_encargos))
    c4.metric("Custo de Benefícios", formatar_moeda(mock_beneficios))
    
    st.markdown("---")
    col_g1, col_g2 = st.columns([1, 1])
    
    with col_g1:
        st.markdown("**Composição do Custo de Headcount**")
        df_composicao = pd.DataFrame({
            "Categoria": ["Salários Líquidos", "Encargos", "Benefícios"],
            "Valor": [mock_folha, mock_encargos, mock_beneficios]
        })
        fig_donut
