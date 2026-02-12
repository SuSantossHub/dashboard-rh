import streamlit as st
import pandas as pd

# 1. Configuração da Página (Título da aba do navegador, layout largo)
st.set_page_config(page_title="Dashboard RH", layout="wide")

# 2. Título Principal
st.title("📊 Dashboard de Benefícios Corporativos")

# 3. Carregar os Dados
# O comando pd.read_csv lê o arquivo que criamos antes.
# O sep=',' diz que as colunas são separadas por vírgula.
df = pd.read_csv("dados.csv", sep=',')

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("Filtros")

# Filtro de Unidade
# df["Unidade"].unique() pega todos os nomes de unidades sem repetir
unidade_filtro = st.sidebar.multiselect(
    "Filtrar por Unidade:",
    options=df["Unidade"].unique(),
    default=df["Unidade"].unique() # Começa com todas selecionadas
)

# Filtro de Tier
tier_filtro = st.sidebar.multiselect(
    "Filtrar por Tier:",
    options=df["Tier"].unique(),
    default=df["Tier"].unique()
)

# Filtro de Status
status_filtro = st.sidebar.multiselect(
    "Filtrar por Status:",
    options=df["Status"].unique(),
    default=df["Status"].unique()
)

# 4. Aplicar os Filtros
# Aqui dizemos: "O novo dataframe (df_selection) só deve ter linhas onde..."
df_selection = df.query(
    "Unidade == @unidade_filtro & Tier == @tier_filtro & Status == @status_filtro"
)

# --- PAINEL DE KPIS (INDICADORES) ---
st.markdown("---") # Uma linha divisória visual
st.subheader("Visão Geral")

# Cálculos
# nunique() conta quantos IDs únicos existem (número de pessoas)
total_vidas = df_selection["ID"].nunique() 
# sum() soma todos os custos
custo_total = df_selection["Custo"].sum()
# mean() calcula a média
custo_medio = df_selection["Custo"].mean()

# Criar 3 colunas para mostrar os números lado a lado
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Total de Vidas Ativas", value=total_vidas)

with col2:
    # Formatação R$ {:,.2f} deixa bonito com vírgulas e pontos
    st.metric(label="Custo Total Mensal", value=f"R$ {custo_total:,.2f}")

with col3:
    st.metric(label="Custo Médio por Benefício", value=f"R$ {custo_medio:,.2f}")

st.markdown("---")

# --- ÁREA DE BUSCA DE COLABORADOR ---
st.subheader("🔍 Localizar Colaborador")
busca = st.text_input("Digite o Nome, E-mail ou ID do colaborador:")

if busca:
    # Se alguém digitou algo na busca...
    # Filtramos onde o nome OU email contém o texto digitado (case=False ignora maiúsculas/minúsculas)
    # astype(str) garante que o ID seja lido como texto para busca
    resultado_busca = df[
        df["Nome"].str.contains(busca, case=False) | 
        df["Email"].str.contains(busca, case=False) |
        df["ID"].astype(str).str.contains(busca)
    ]
    
    if not resultado_busca.empty:
        st.success(f"Encontramos {resultado_busca['ID'].nunique()} colaborador(es).")
        st.dataframe(resultado_busca)
    else:
        st.warning("Nenhum colaborador encontrado com esses dados.")

# --- TABELA GERAL (Opcional, para ver os dados filtrados) ---
st.markdown("---")
with st.expander("Visualizar Base de Dados Completa (Filtrada)"):
    st.dataframe(df_selection)
