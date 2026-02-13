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
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- CARREGAMENTO DE DADOS ---
@st.cache_data
def load_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
    except:
        return None

    # Limpeza e Conversão de Colunas Financeiras
    # Adicionei "Orçado Mês" e "Realizado Mês" caso existam na planilha
    termos_financeiros = ["Custo", "Valor", "Total", "Orçado", "Realizado"]
    
    for col in df.columns:
        # Se o nome da coluna tem termos financeiros ou o conteúdo tem R$
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
    
    # Valores fixos que você solicitou
    META_ORCAMENTO_MENSAL = 286000.00
    META_ORCAMENTO_ANUAL = 3432000.00
    
    # Cálculo do Realizado (Soma da coluna Custo Realizado da planilha)
    total_realizado_acumulado = df["Custo Realizado"].sum() if "Custo Realizado" in df.columns else 0
    
    # Economia (Meta Anual - O que já gastamos)
    # OBS: Se quiser comparar apenas até o mês atual, a lógica mudaria, 
    # mas aqui estamos comparando com o Budget Total do ano.
    saldo_anual = META_ORCAMENTO_ANUAL - total_realizado_acumulado
    
    # Layout das Metas
    col_meta1, col_meta2, col_meta3, col_meta4 = st.columns(4)
    
    with col_meta1:
        st.metric("Budget Mensal (Meta)", formatar_moeda(META_ORCAMENTO_MENSAL))
        
    with col_meta2:
        st.metric("Budget Anual (Meta)", formatar_moeda(META_ORCAMENTO_ANUAL))
        
    with col_meta3:
        # Mostra quanto já foi gasto de verdade segundo a planilha
        st.metric("Realizado Acumulado (YTD)", formatar_moeda(total_realizado_acumulado))
        
    with col_meta4:
        # Se for positivo (Verde) = Economia. Se negativo (Vermelho) = Estouro.
        st.metric(
            "Saldo / Economia Disponível", 
            formatar_moeda(saldo_anual), 
            delta=formatar_moeda(saldo_anual)
        )

    st.markdown("---")

    # --- FILTROS ---
    st.sidebar.subheader("Filtros 2026")
    df_filtered = df.copy()
    colunas_filtro = ["Mês", "Unidade", "Beneficio", "Status"]
    for col in colunas_filtro:
        if col in df.columns:
            opcoes = sorted(df[col].astype(str).unique())
            escolha = st.sidebar.multiselect(f"{col}:", options=opcoes, default=opcoes)
            if escolha:
                df_filtered = df_filtered[df_filtered[col].isin(escolha)]

    # --- GRÁFICOS INTERATIVOS ---
    c_graf1, c_graf2 = st.columns(2)
    
    with c_graf1:
        st.subheader("Evolução Mensal")
        if "Mês" in df_filtered.columns and "Custo Realizado" in df_filtered.columns:
            # Agrupa por mês
            df_mes = df_filtered.groupby("Mês")[["Custo Orçado", "Custo Realizado"]].sum().reset_index()
            
            # Gráfico de Linha/Barra
            fig_evolucao = px.bar(
                df_mes, x="Mês", y=["Custo Orçado", "Custo Realizado"],
                barmode="group",
                title="Orçado vs Realizado por Mês",
                text_auto=".2s",
                color_discrete_map={"Custo Orçado": "#1f77b4", "Custo Realizado": "#ff7f0e"} # Azul e Laranja
            )
            # Formatação R$ no Eixo Y e no Hover
            fig_evolucao.update_layout(yaxis_tickprefix="R$ ", hovermode="x unified")
            st.plotly_chart(fig_evolucao, use_container_width=True)
            
    with c_graf2:
        st.subheader("Share por Benefício")
        if "Beneficio" in df_filtered.columns:
            df_ben = df_filtered.groupby("Beneficio")["Custo Realizado"].sum().reset_index()
            fig_pizza = px.pie(
                df_ben, values="Custo Realizado", names="Beneficio", 
                hole=0.4, # Gráfico de Rosca
                title="Distribuição de Custos"
            )
            fig_pizza.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_pizza, use_container_width=True)

    # --- TABELA LIMPA (SEM ÍNDICE NUMÉRICO) ---
    st.markdown("---")
    st.subheader("Detalhamento Analítico")
    
    # Selecionar colunas principais para não ficar poluído
    cols_para_mostrar = [c for c in df_filtered.columns if c not in ["ID", "Unnamed: 0"]]
    
    # hide_index=True remove a primeira coluna de numeração (0, 1, 2...)
    st.dataframe(
        df_filtered[cols_para_mostrar].style.format(precision=2), # Formata com 2 casas decimais
        hide_index=True,
        use_container_width=True
    )

# === CENÁRIO 2: OUTRAS ABAS (2025, TABELAS DINÂMICAS) ===
else:
    st.header(f"Visualização: {aba_selecionada}")
    
    # Filtros Genéricos
    st.sidebar.subheader("Filtros Gerais")
    df_outros = df.copy()
    if "Unidade" in df.columns:
        unidade = st.sidebar.multiselect("Unidade", df["Unidade"].unique())
        if unidade: df_outros = df_outros[df_outros["Unidade"].isin(unidade)]
        
    # Exibição Simples
    st.dataframe(df_outros, hide_index=True, use_container_width=True)
