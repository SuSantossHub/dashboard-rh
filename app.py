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

# --- FUNÇÃO DE FORMATAÇÃO DE MOEDA (BRASIL) ---
def formatar_moeda(valor):
    # Transforma o número em texto: R$ 1.000,00
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

    # Termos que indicam que uma coluna é dinheiro
    termos_financeiros = ["Custo", "Valor", "Total", "Orçado", "Realizado", "Budget"]
    
    for col in df.columns:
        # Se o nome da coluna tem termos financeiros OU o conteúdo tem R$
        eh_financeiro = any(termo in col for termo in termos_financeiros)
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

# --- LÓGICA DE EXIBIÇÃO ---

# === CENÁRIO 1: VISÃO 2026 (COM PAINEL DE METAS ESPECÍFICO) ===
if "2026" in aba_selecionada and "Orçamento" in aba_selecionada:
    
    st.header("🎯 Painel Executivo 2026: Orçado vs Realizado")
    
    # --- PAINEL SECUNDÁRIO (METAS FIXAS SOLICITADAS) ---
    st.markdown("### 📌 Indicadores de Meta (Budget)")
    
    META_ORCAMENTO_MENSAL = 286000.00
    META_ORCAMENTO_ANUAL = 3432000.00
    
    # Soma de tudo que é "Realizado" na planilha (procura colunas com esse nome)
    coluna_realizado = [c for c in df.columns if "Realizado" in c]
    if coluna_realizado:
        total_realizado_acumulado = df[coluna_realizado[0]].sum()
    else:
        total_realizado_acumulado = 0
    
    saldo_anual = META_ORCAMENTO_ANUAL - total_realizado_acumulado
    
    # Layout das Metas
    col_meta1, col_meta2, col_meta3, col_meta4 = st.columns(4)
    with col_meta1:
        st.metric("Budget Mensal (Meta)", formatar_moeda(META_ORCAMENTO_MENSAL))
    with col_meta2:
        st.metric("Budget Anual (Meta)", formatar_moeda(META_ORCAMENTO_ANUAL))
    with col_meta3:
        st.metric("Realizado Acumulado (YTD)", formatar_moeda(total_realizado_acumulado))
    with col_meta4:
        st.metric("Saldo Disponível", formatar_moeda(saldo_anual), delta=formatar_moeda(saldo_anual))

    st.markdown("---")

    # --- FILTROS ---
    st.sidebar.subheader("Filtros 2026")
    df_filtered = df.copy()
    
    # Filtros inteligentes (só mostra o que existe)
    colunas_possiveis = ["Mês", "Unidade", "Beneficio", "Status"]
    for col in colunas_possiveis:
        if col in df.columns:
            opcoes = sorted(df[col].astype(str).unique())
            escolha = st.sidebar.multiselect(f"{col}:", options=opcoes, default=opcoes)
            if escolha:
                df_filtered = df_filtered[df_filtered[col].isin(escolha)]

    # --- GRÁFICOS ---
    c_graf1, c_graf2 = st.columns(2)
    
    with c_graf1:
        st.subheader("Evolução Mensal")
        # Tenta achar as colunas certas para o gráfico
        col_orcado = [c for c in df.columns if "Orçado" in c]
        col_realizado = [c for c in df.columns if "Realizado" in c]
        col_mes = [c for c in df.columns if "Mês" in c or "Mes" in c]
        
        if col_orcado and col_realizado and col_mes:
            df_mes = df_filtered.groupby(col_mes[0])[[col_orcado[0], col_realizado[0]]].sum().reset_index()
            fig_evolucao = px.bar(
                df_mes, x=col_mes[0], y=[col_orcado[0], col_realizado[0]],
                barmode="group", title="Orçado vs Realizado", text_auto=".2s",
                color_discrete_map={col_orcado[0]: "#1f77b4", col_realizado[0]: "#ff7f0e"}
            )
            fig_evolucao.update_layout(yaxis_tickprefix="R$ ", hovermode="x unified")
            st.plotly_chart(fig_evolucao, use_container_width=True)
            
    with c_graf2:
        st.subheader("Share por Benefício")
        if "Beneficio" in df_filtered.columns and col_realizado:
            df_ben = df_filtered.groupby("Beneficio")[col_realizado[0]].sum().reset_index()
            fig_pizza = px.pie(df_ben, values=col_realizado[0], names="Beneficio", hole=0.4)
            fig_pizza.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_pizza, use_container_width=True)

    # --- TABELA DE DETALHAMENTO (AQUI ESTÁ A CORREÇÃO VISUAL) ---
    st.markdown("---")
    st.subheader("Detalhamento Analítico")
    
    # 1. Seleciona colunas (tira ID e Unnamed)
    cols_para_mostrar = [c
