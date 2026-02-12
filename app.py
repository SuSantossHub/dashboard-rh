import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuração da Página
st.set_page_config(page_title="Dashboard RH GSheets", layout="wide")
st.title("📊 Dashboard de Benefícios (Conectado ao Google Sheets)")

# --- FUNÇÃO PARA CARREGAR DADOS (com cache para ficar rápido) ---
# O @st.cache_data faz com que o Streamlit não recarregue a planilha
# a cada clique, apenas quando ela muda ou após um tempo.
@st.cache_data
def load_data():
    # O TRUQUE DO LINK:
    # Pegamos seu link original e mudamos o final para 'export?format=csv'
    sheet_url = "https://docs.google.com/spreadsheets/d/1NcP0k_tFK2SN5cJtdqfka-cgFv6tZH1gn1sOS1n2BBw/export?format=csv"
    
    df = pd.read_csv(sheet_url)
    
    # --- LIMPEZA DE DADOS (CRUCIAL) ---
    # Garantir que as colunas de dinheiro sejam números (float).
    # O 'errors="coerce"' transforma textos estranhos em "Not a Number" (NaN) para não travar o app.
    df["Custo Orçado"] = pd.to_numeric(df["Custo Orçado"], errors="coerce").fillna(0)
    df["Custo Realizado"] = pd.to_numeric(df["Custo Realizado"], errors="coerce").fillna(0)
    
    return df

# Carrega os dados chamando a função acima
try:
    df = load_data()
except Exception as e:
    st.error(f"Erro ao conectar com o Google Sheets. Verifique o link e as permissões. Erro: {e}")
    st.stop()


# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("Filtros Globais")

# Filtros (usando sorted() para deixar a lista em ordem alfabética)
unidade_filtro = st.sidebar.multiselect(
    "Filtrar por Unidade:",
    options=sorted(df["Unidade"].unique()),
    default=sorted(df["Unidade"].unique())
)

tier_filtro = st.sidebar.multiselect(
    "Filtrar por Tier:",
    options=sorted(df["Tier"].unique()),
    default=sorted(df["Tier"].unique())
)

status_filtro = st.sidebar.multiselect(
    "Filtrar por Status:",
    options=sorted(df["Status"].unique()),
    default=sorted(df["Status"].unique())
)

# Aplicar os Filtros
df_selection = df.query(
    "Unidade == @unidade_filtro & Tier == @tier_filtro & Status == @status_filtro"
)

# --- PAINEL DE VISÃO GERAL (ORÇADO VS REALIZADO) ---
st.markdown("---")
st.header("Visão Geral Financeira")

# Cálculos Totais
total_orcado = df_selection["Custo Orçado"].sum()
total_realizado = df_selection["Custo Realizado"].sum()
diferenca = total_orcado - total_realizado

# Métricas Lado a Lado
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Orçado", f"R$ {total_orcado:,.2f}")
with col2:
    st.metric("Total Realizado", f"R$ {total_realizado:,.2f}")
with col3:
    # A métrica "delta" mostra a diferença com cor (verde se positivo, vermelho se negativo)
    # Aqui, se a diferença é positiva, significa que economizamos (verde).
    st.metric("Economia (Orçado - Realizado)", f"R$ {diferenca:,.2f}", delta=f"{diferenca:,.2f}")


# --- GRÁFICOS DETALHADOS ---
st.markdown("---")
col_graf1, col_graf2 = st.columns(2)

# GRÁFICO 1: Comparativo Geral (Barras lado a lado)
with col_graf1:
    st.subheader("Comparativo Total: Orçado x Realizado")
    
    # Precisamos "derreter" (melt) os dados para o formato que o gráfico gosta
    # Transformamos as duas colunas de custo em linhas.
    df_melted_total = df_selection.melt(
        value_vars=["Custo Orçado", "Custo Realizado"], 
        var_name="Tipo de Custo", 
        value_name="Valor Total"
    )
    # Agrupamos para somar tudo
    df_grouped_total = df_melted_total.groupby("Tipo de Custo")["Valor Total"].sum().reset_index()
    
    # Criando o gráfico
    fig_total = px.bar(
        df_grouped_total,
        x="Tipo de Custo",
        y="Valor Total",
        color="Tipo de Custo", # Cores diferentes para cada barra
        text_auto=".2s", # Mostra o valor em cima da barra (abreviado, ex: 10k)
        color_discrete_map={"Custo Orçado": "#1f77b4", "Custo Realizado": "#ff7f0e"}, # Cores personalizadas
        template="plotly_white"
    )
    st.plotly_chart(fig_total, use_container_width=True)


# GRÁFICO 2: Comparativo por Benefício
with col_graf2:
    st.subheader("Orçado x Realizado por Benefício")
    
    # Agrupar por benefício e somar os custos
    df_por_beneficio = df_selection.groupby("Beneficio")[["Custo Orçado", "Custo Realizado"]].sum().reset_index()
    
    # "Derreter" novamente para poder comparar lado a lado no gráfico
    df_melted_beneficio = df_por_beneficio.melt(
        id_vars=["Beneficio"],
        value_vars=["Custo Orçado", "Custo Realizado"],
        var_name="Tipo de Custo",
        value_name="Valor"
    )

    # Criando o gráfico de barras agrupadas (barmode='group')
    fig_beneficio = px.bar(
        df_melted_beneficio,
        x="Valor",
        y="Beneficio",
        color="Tipo de Custo",
        barmode="group", # Isso coloca as barras uma do lado da outra, não empilhadas
        text_auto=".2s",
        orientation='h', # Barras horizontais ficam melhores para ler os nomes
        height=400,
        template="plotly_white"
    )
    st.plotly_chart(fig_beneficio, use_container_width=True)


# --- ÁREA DE BUSCA E TABELA ---
st.markdown("---")
with st.expander("🔍 Busca e Tabela Detalhada (Clique para expandir)"):
    busca = st.text_input("Buscar colaborador (Nome, E-mail ou ID):")
    if busca:
        resultado_busca = df[
            df["Nome"].str.contains(busca, case=False, na=False) | 
            df["Email"].str.contains(busca, case=False, na=False) |
            df["ID"].astype(str).str.contains(busca)
        ]
        st.dataframe(resultado_busca)
    else:
        # Mostra a tabela filtrada pelos filtros laterais se não houver busca
        st.dataframe(df_selection)
