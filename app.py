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
    page_title="Dashboard de Benefícios | V4 Company", 
    layout="wide",
    page_icon="favicon.png",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. FUNÇÕES GERAIS E AUXILIARES
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
            eh_financeiro = any(t in col_norm for t in termos
