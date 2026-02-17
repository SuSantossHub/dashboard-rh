import streamlit as st
import pandas as pd
import plotly.express as px
import unicodedata
import os
import base64

# 1. Configuração da Página (DEVE SER O PRIMEIRO COMANDO)
st.set_page_config(page_title="Dashboard RH Executivo", layout="wide")

# ==============================================================================
# FUNÇÕES AUXILIARES PARA O BACKGROUND
# ==============================================================================
def get_base64_of_bin_file(bin_file):
    """Lê um arquivo de imagem e converte para string Base64 para usar no CSS."""
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_png_as_page_bg(png_file):
    """Injeta CSS para definir a imagem de fundo da página inteira."""
    bin_str = get_base64_of_bin_file(png_file)
    page_bg_img = '''
    <style>
    /* Isso atinge o container principal do Streamlit */
    [data-testid="stAppViewContainer"] {
    background-image: url("data:image/jpg;base64,%s");
    background-size: cover; /* Faz a imagem cobrir tudo sem distorcer */
    background-position: center center; /* Centraliza a imagem */
    background-repeat: no-repeat; /* Não repete a imagem */
    background-attachment: fixed; /* A imagem fica fixa ao rolar */
    }
    
    /* Opcional: Deixa o fundo da barra lateral semi-transparente para combinar */
    [data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.8);
    }
    
    /* Estilo para caixa de login ficar legível */
    .login-box {
        background-color: rgba(0, 0, 0, 0.7); /* Fundo preto semi-transparente */
        padding: 30px;
        border-radius: 15px;
        color: white; /* Texto branco */
        text-align: center;
    }
    /* Força a cor branca nos títulos dentro da caixa */
    .login-box h1, .login-box h3, .login-box p, .login-box label {
         color: white !important;
    }
    </style>
    ''' % bin_str
    st.markdown(page_bg_img, unsafe_allow_html=True)

# ==============================================================================
# 🔒 SISTEMA DE LOGIN (COM BACKGROUND TELA CHEIA)
# ==============================================================================
def check_password():
    """Retorna True se o usuário tiver a senha correta."""

    def password_entered():
        """Verifica se a senha digitada bate com a definida aqui."""
        # --- CREDENCIAIS ---
        USUARIO_CORRETO = "Benefits Opers"
        SENHA_CORRETA = "BenefitsV4Company"
        # -------------------

        if st.session_state["username"] == USUARIO_CORRETO and \
           st.session_state["password"] == SENHA_CORRETA:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Limpa senha da memória
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    # --- CONFIGURAÇÃO DO VISUAL DA TELA DE LOGIN ---
    
    # 1. Aplica a imagem de fundo se ela existir
    if os.path.exists("capa_login.jpg"):
        set_png_as_page_bg("capa_login.jpg")
    else:
        st.warning("⚠️ Imagem 'capa_login.jpg' não encontrada no GitHub.")

    # 2. Cria colunas para centralizar o formulário na tela
    # Usamos [1, 2, 1] para criar um espaço vazio na esquerda, o formulário no meio, e espaço na direita
    col_esq, col_centro, col_dir = st.columns([1, 2, 1])

    with col_centro:
        st.markdown("<br><br>", unsafe_allow_html=True) # Empurra um pouco para baixo
        
        # Abre um container para agrupar os elementos do login
        with st.container():
            # Injeta um HTML para criar uma "caixa" escura semi-transparente
            # Isso garante que o texto fique legível sobre qualquer foto
            st.markdown("""
                <div class="login-box">
                    <h1>🔒 Acesso Restrito</h1>
                    <h3>Diretoria RH & Benefits Operations</h3>
                    <p>Entre com as credenciais corporativas V4 para visualizar os dados sensíveis.</p>
                </div>
            """, unsafe_allow_html=True)

            # Inputs do Streamlit (ficam abaixo do texto, mas dentro da mesma área visual)
            st.text_input("Usuário", key="username")
            st.text_input("Senha", type="password", key="password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("Entrar no Painel", on_click=password_entered, type="primary", use_container_width=True)

            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("🚫 Acesso negado. Verifique suas credenciais.")
        
        st.markdown("<br><br>", unsafe_allow_html=True)
            
    return False

# 🛑 BLOQUEIO: Se não logar, o código para aqui.
if not check_password():
    st.stop()

# ==============================================================================
# 🚀 ÁREA LOGADA: DASHBOARD COMPLETO
# ==============================================================================
# (O CSS do fundo não se aplica aqui porque a função check_password já terminou)

st.title("📊 Dashboard de Benefícios Corporativos")

# --- BARRA LATERAL (LOGOUT) ---
st.sidebar.success(f"👤 Logado: **{st.session_state['username']}**")
if st.sidebar.button("Sair / Logout"):
    st.session_state["password_correct"] = False
    st.rerun()

st.sidebar.markdown("---")

# --- CONFIGURAÇÃO DE GIDs (ABAS) ---
SHEET_ID = "10lEeyQAAOaHqpUTOfdMzaHgjfBpuNIHeCRabsv43WTQ"
GID_2026 = "1350897026"
GID_2025 = "1743422062"
GID_DASH_2025 = "2124043219"

# Menu de Navegação
OPCOES_MENU = [
    "Orçamento x Realizado | 2026",
    "Orçamento x Realizado | 2025",
    "Comparativo: 2025 vs 2026 (De/Para)",
    "Dashboard Trimestral"
]

st.sidebar.header("Navegação")
aba_selecionada = st.sidebar.selectbox("Escolha a Visão:", OPCOES_MENU)

# --- FUNÇÕES UTILITÁRIAS ---
def formatar_moeda(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return valor

def remover_acentos(texto):
    try:
        nfkd = unicodedata.normalize('NFKD', str(texto))
        return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    except:
        return str(texto).lower()

# MAPA DE MESES PARA ORDENAÇÃO
MAPA_MESES = {
    'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
}

def get_mes_ordem(nome_mes):
    chave = str(nome_mes).lower()[:3]
    return MAPA_MESES.get(chave, 99)

def get_trimestre(nome_mes):
    ordem = get_mes_ordem(nome_mes)
    if 1 <= ordem <= 3: return "Q1 (Jan-Mar)"
    elif 4 <= ordem <= 6: return "Q2 (Abr-Jun)"
    elif 7 <= ordem <= 9: return "Q3 (Jul-Set)"
    elif 10 <= ordem <= 12: return "Q4 (Out-Dez)"
    return "Outros"

# --- DETECTOR INTELIGENTE DE COLUNAS ---
def achar_coluna(df, termos):
    colunas_normalizadas = {col: remover_acentos(col) for col in df.columns}
    for termo in termos:
        termo_limpo = remover_acentos(termo)
        for col_original, col_limpa in colunas_normalizadas.items():
            if termo_limpo in col_limpa:
                return col_original
    return None

# --- CARREGAMENTO DE DADOS ---
@st.cache_data
def load_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
    except Exception as e:
        return None

    termos_financeiros = ["custo", "valor", "total", "orçado", "realizado", "budget", "soma", "sum"]
    
    for col in df.columns:
        col_norm = remover_acentos(col)
        eh_financeiro = any(remover_acentos(t) in col_norm for t in termos_financeiros)
        tem_cifrao = df[col].dtype == "object" and df[col].astype(str).str.contains("R\$").any()
        
        if eh_financeiro or tem_cifrao:
             if df[col].dtype == "object":
                df[col] = df[col].astype(str).str.replace("R$", "", regex=False)
                df[col] = df[col].str.replace(" ", "", regex=False)
                df[col] = df[col].str.replace(".", "", regex=False)
                df[col] = df[col].str.replace(",", ".", regex=False)
             df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

# Identifica qual GID carregar
gid_atual = GID_2026 
if "2025" in aba_selecionada and "Comparativo" not in aba_selecionada:
    gid_atual = GID_2025
elif "Comparativo" in aba_selecionada:
    gid_atual = None 

# ==============================================================================
# VISÃO: COMPARATIVO 2025 vs 2026
# ==============================================================================
if "Comparativo" in aba_selecionada:
    st.header("⚖️ Comparativo Anual: 2025 vs 2026")
    
    with st.spinner("Carregando dados..."):
        df_2025 = load_data(GID_2025)
        df_2026 = load_data(GID_2026)
    
    if df_2025 is not None and df_2026 is not None:
        col_real = achar_coluna(df_2025, ["realizado", "executado", "soma"])
        col_mes_25 = achar_coluna(df_2025, ["mês", "mes", "data"])
        col_mes_26 = achar_coluna(df_2026, ["mês", "mes", "data"])

        total_25 = df_2025[col_real].sum()
        total_26 = df_2026[col_real].sum()
        delta = total_26 - total_25
        delta_perc = (delta / total_25 * 100) if total_25 > 0 else 0

        k1, k2, k3 = st.columns(3)
        k1.metric("Total 2025", formatar_moeda(total_25))
        k2.metric("Total 2026", formatar_moeda(total_26))
        k3.metric("Variação", formatar_moeda(delta), delta=f"{delta_perc:.1f}%", delta_color="inverse")

        st.markdown("---")
        st.subheader("Evolução Mensal Comparada")
        
        # Prepara dados
        df_c25 = df_2025.groupby(col_mes_25)[col_real].sum().reset_index()
        df_c25.columns = ['Mês', 'Valor']
        df_c25['Ano'] = '2025'
        
        df_c26 = df_2026.groupby(col_mes_26)[col_real].sum().reset_index()
        df_c26.columns = ['Mês', 'Valor']
        df_c26['Ano'] = '2026'
        
        df_comb = pd.concat([df_c25, df_c26])
        df_comb['ordem'] = df_comb['Mês'].apply(get_mes_ordem)
        df_comb = df_comb.sort_values('ordem')
        
        fig = px.bar(df_comb, x="Mês", y="Valor", color="Ano", barmode="group",
                     text_auto='.2s', color_discrete_map={'2025': '#D3D3D3', '2026': '#8B0000'})
        fig.update_layout(template="plotly_white", yaxis_tickprefix="R$ ")
        st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# VISÃO: ORÇAMENTO x REALIZADO (2025 ou 2026)
# ==============================================================================
elif "Orçamento" in aba_selecionada:
    df = load_data(gid_atual)
    if df is not None:
        ano = "2026" if "2026" in aba_selecionada else "2025"
        st.header(f"🎯 Painel Executivo {ano}")
        
        col_orc = achar_coluna(df, ["orçado", "orcado", "budget"])
        col_real = achar_coluna(df, ["realizado", "executado", "soma"])
        col_ben = achar_coluna(df, ["beneficio", "benefício"])
        col_mes = achar_coluna(df, ["mês", "mes", "data"])
        col_unid = achar_coluna(df, ["unidade", "filial"])

        # Filtros
        st.sidebar.subheader("Filtros")
        df_filt = df.copy()
        
        if col_mes:
            meses = sorted(df[col_mes].astype(str).unique(), key=get_mes_ordem)
            sel_m = st.sidebar.multiselect("Mês:", meses, default=meses)
            if sel_m: df_filt = df_filt[df_filt[col_mes].isin(sel_m)]
