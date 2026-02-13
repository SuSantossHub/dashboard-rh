import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuração da Página
st.set_page_config(page_title="Dashboard RH Executivo", layout="wide")
st.title("📊 Dashboard de Benefícios Corporativos")

# --- CONFIGURAÇÃO DAS ABAS (GIDs) ---
SHEET_ID = "10lEeyQAAOaHqpUTOfdMzaHgjfBpuNIHeCRabsv43WTQ"

DICIONARIO_DE_ABAS = {
    "Orçamento x Realizado | 2026": "1350897026",
    "Tabela dinâmica - 2026": "763072509",
    "Orçamento x Realizado | 2025": "1743422062",
    "Tabela dinâmica 2025": "1039975619",
    "Dashboard - 2025": "2124043219"
}

# --- BARRA LATERAL ---
st.sidebar.header("Navegação")
aba_selecionada = st.sidebar.selectbox("Escolha a Visão:", list(DICIONARIO_DE_ABAS.keys()))
gid_selecionado = DICIONARIO_DE_ABAS[aba_selecionada]

# --- FUNÇÃO DE FORMATAÇÃO ---
def formatar_moeda(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return valor

# --- CARREGAMENTO DE DADOS ---
@st.cache_data
def load_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
    except:
        return None

    termos_financeiros = ["custo", "valor", "total", "orçado", "realizado", "budget", "soma", "sum"]
    
    for col in df.columns:
        eh_financeiro = any(termo in col.lower() for termo in termos_financeiros)
        tem_cifrao = df[col].dtype == "object" and df[col].astype(str).str.contains("R\$").any()
        
        if eh_financeiro or tem_cifrao:
             if df[col].dtype == "object":
                df[col] = df[col].astype(str).str.replace("R$", "", regex=False)
                df[col] = df[col].str.replace(" ", "", regex=False)
                df[col] = df[col].str.replace(".", "", regex=False)
                df[col] = df[col].str.replace(",", ".", regex=False)
             df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

df = load_data(gid_selecionado)

if df is None:
    st.error("Erro ao carregar dados. Verifique a conexão.")
    st.stop()

# --- DETECTOR INTELIGENTE DE COLUNAS ---
def achar_coluna(df, termos):
    for col in df.columns:
        if any(t in col.lower() for t in termos):
            return col
    return None

col_orcado = achar_coluna(df, ["orçado", "orcado", "budget", "meta"])
col_realizado = achar_coluna(df, ["realizado", "executado", "gasto"])
col_beneficio = achar_coluna(df, ["beneficio", "benefício"])
col_mes = achar_coluna(df, ["mês", "mes", "data"])
col_unidade = achar_coluna(df, ["unidade", "filial", "local"])
col_status = achar_coluna(df, ["status", "situação"])

# --- LÓGICA DE EXIBIÇÃO ---

# === CENÁRIO 1: ORÇAMENTO X REALIZADO 2026 (INTACTO) ===
if "2026" in aba_selecionada and "Orçamento" in aba_selecionada:
    
    st.header("🎯 Painel Executivo 2026")
    
    META_ORCAMENTO_MENSAL = 286000.00
    META_ORCAMENTO_ANUAL = 3432000.00
    
    total_realizado_acumulado = df[col_realizado].sum() if col_realizado else 0
    saldo_anual = META_ORCAMENTO_ANUAL - total_realizado_acumulado
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Budget Mensal", formatar_moeda(META_ORCAMENTO_MENSAL))
    c2.metric("Budget Anual", formatar_moeda(META_ORCAMENTO_ANUAL))
    c3.metric("Realizado YTD", formatar_moeda(total_realizado_acumulado))
    c4.metric("Saldo Disponível", formatar_moeda(saldo_anual), delta=formatar_moeda(saldo_anual))

    st.markdown("---")

    st.sidebar.subheader("Filtros")
    df_filtered = df.copy()
    
    cols_para_filtro = [col_mes, col_unidade
