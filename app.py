import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuração da Página
st.set_page_config(page_title="Dashboard RH", layout="wide")
st.title("📊 Dashboard de Benefícios Corporativos")

# --- FUNÇÃO DE CARREGAMENTO DE DADOS ---
@st.cache_data
def load_data():
    # SEU LINK NOVO (Já ajustado para formato CSV para o Python entender)
    sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRDOYmkYSNo7Ttbw0GM5YhDH3nYafq-Jg2o-fk1LaFOYjRw9oKQhwVe8YvBTdrmtOdzVsQdw-koM2oz/pub?output=csv"
    
    # Lê os dados
    df = pd.read_csv(sheet_url)
    
    # --- LIMPEZA DE DADOS (CRUCIAL) ---
    # Converte colunas de dinheiro (que podem vir como texto "R$ 1.000,00") em números puros
    cols_financeiras = ["Custo Orçado", "Custo Realizado"]
    
    for col in cols_financeiras:
        if col in df.columns:
            # Se a coluna for lida como texto (object), limpamos os caracteres
            if df[col].dtype == "object":
                df[col] = df[col].astype(str).str.replace("R$", "", regex=False)
                df[col] = df[col].str.replace(".", "", regex=False) # Remove ponto de milhar
                df[col] = df[col].str.replace(",", ".", regex=False) # Troca vírgula por ponto decimal
            
            # Converte para número (float) e preenche vazios com 0
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            
    return df

# Tenta carregar os dados
try:
    df = load_data()
except Exception as e:
    st.error(f"Erro ao ler a planilha. Verifique se as colunas 'Custo Orçado' e 'Custo Realizado' existem. Detalhes: {e}")
    st.stop()

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("Filtros")

# Verifica se as colunas existem antes de criar filtros
if "Unidade" in df.columns:
    unidade_filtro = st.sidebar.multiselect(
        "Filtrar por Unidade:",
        options=sorted(df["Unidade"].unique().astype(str)),
        default=sorted(df["Unidade"].unique().astype(str))
    )
else:
    unidade_filtro = []

if "Tier" in df.columns:
    tier_filtro = st.sidebar.multiselect(
        "Filtrar por Tier:",
        options=sorted(df["Tier"].unique().astype(str)),
        default=sorted(df["Tier"].unique().astype(str))
    )
else:
    tier_filtro = []

if "Status" in df.columns:
    status_filtro = st.sidebar.multiselect(
        "Filtrar por Status:",
        options=sorted(df["Status"].unique().astype(str)),
        default=sorted(df["Status"].unique().astype(str))
    )
else:
    status_filtro = []

# Aplica os filtros apenas se as colunas existirem
df_selection = df.copy()
if unidade_filtro:
    df_selection = df_selection[df_selection["Unidade"].isin(unidade_filtro)]
if tier_filtro:
    df_selection = df_selection[df_selection["Tier"].isin(tier_filtro)]
if status_filtro:
    df_selection = df_selection[df_selection["Status"].isin(status_filtro)]

# --- PAINEL DE VISÃO GERAL (ORÇADO VS REALIZADO) ---
st.markdown("---")
st.subheader("Visão Geral Financeira")

# Garante que as colunas existem antes de somar
if "Custo Orçado" in df_selection.columns and "Custo Realizado" in df_selection.columns:
    total_orcado = df_selection["Custo Orçado"].sum()
    total_realizado = df_selection["Custo Realizado"].sum()
    diferenca = total_orcado - total_realizado

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Orçado", f"R$ {total_orcado:,.2f}")
    with col2:
        st.metric("Total Realizado", f"R$ {total_realizado:,.2f}")
    with col3:
        st.metric("Economia (Orçado - Realizado)", f"R$ {diferenca:,.2f}", delta=f"{diferenca:,.2f}")

    # --- GRÁFICOS ---
    st.markdown("---")
    col_graf1, col_graf2 = st.columns(2)

    # GRÁFICO 1: Comparativo Total
    with col_graf1:
        st.caption("Comparativo Total: Orçado x Realizado")
        df_melted_total = df_selection.melt(
            value_vars=["Custo Orçado", "Custo Realizado"], 
            var_name="Tipo de Custo", 
            value_name="Valor Total"
        )
        df_grouped_total = df_melted_total.groupby("Tipo de Custo")["Valor Total"].sum().reset_index()
        
        fig_total = px.bar(
            df_grouped_total,
            x="Tipo de Custo",
            y="Valor Total",
            color="Tipo de Custo",
            text_auto=".2s",
            color_discrete_map={"Custo Orçado": "#1f77b4", "Custo Realizado": "#ff7f0e"},
            template="plotly_white"
        )
        st.plotly_chart(fig_total, use_container_width=True)

    # GRÁFICO 2: Por Benefício
    with col_graf2:
        st.caption("Orçado x Realizado por Benefício")
        if "Beneficio" in df_selection.columns:
            df_por_beneficio = df_selection.groupby("Beneficio")[["Custo Orçado", "Custo Realizado"]].sum().reset_index()
            df_melted_beneficio = df_por_beneficio.melt(
                id_vars=["Beneficio"],
                value_vars=["Custo Orçado", "Custo Realizado"],
                var_name="Tipo de Custo",
                value_name="Valor"
            )
            fig_beneficio = px.bar(
                df_melted_beneficio,
                x="Valor",
                y="Beneficio",
                color="Tipo de Custo",
                barmode="group",
                text_auto=".2s",
                orientation='h',
                template="plotly_white"
            )
            st.plotly_chart(fig_beneficio, use_container_width=True)
else:
    st.warning("As colunas de custo não foram encontradas na planilha.")

# --- ÁREA DE BUSCA E TABELA ---
st.markdown("---")
with st.expander("🔍 Busca e Tabela Detalhada (Clique para expandir)"):
    busca = st.text_input("Buscar colaborador (Nome, E-mail ou ID):")
    if busca:
        # Filtra convertendo tudo para texto antes de buscar
        mask = df.apply(lambda x: x.astype(str).str.contains(busca, case=False, na=False)).any(axis=1)
        st.dataframe(df[mask])
    else:
        st.dataframe(df_selection)
