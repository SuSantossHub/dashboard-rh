import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuração da Página
st.set_page_config(page_title="Dashboard RH Multi-Anos", layout="wide")
st.title("📊 Dashboard de Benefícios Corporativos")

# --- CONFIGURAÇÃO DAS ABAS (GIDs ATUALIZADOS) ---
SHEET_ID = "10lEeyQAAOaHqpUTOfdMzaHgjfBpuNIHeCRabsv43WTQ"

# Dicionário com os Nomes que aparecem no menu e seus respectivos IDs (GIDs)
DICIONARIO_DE_ABAS = {
    "Orçamento x Realizado | 2026": "1350897026",
    "Tabela dinâmica - 2026": "763072509",
    "Orçamento x Realizado | 2025": "1743422062",
    "Tabela dinâmica 2025": "1039975619",
    "Dashboard - 2025": "2124043219"
}

# --- BARRA LATERAL DE NAVEGAÇÃO ---
st.sidebar.header("Navegação")
aba_selecionada = st.sidebar.selectbox(
    "Escolha a Visão:", 
    list(DICIONARIO_DE_ABAS.keys())
)

# Pega o ID (gid) correspondente à escolha
gid_selecionado = DICIONARIO_DE_ABAS[aba_selecionada]

# --- FUNÇÃO DE CARREGAMENTO INTELIGENTE ---
@st.cache_data
def load_data(gid):
    # Monta o link específico para a aba escolhida usando o GID
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    
    try:
        df = pd.read_csv(url)
    except Exception as e:
        return None

    # --- LIMPEZA DE DADOS FINANCEIROS ---
    # Varre todas as colunas. Se parecer dinheiro, limpa e converte para número.
    # Isso serve tanto para 2025 quanto 2026.
    colunas_para_limpar = ["Custo Orçado", "Custo Realizado", "Valor", "Total", "Custo", "Soma de Custo Orçado", "Soma de Custo Realizado"]
    
    for col in df.columns:
        # Se o nome da coluna estiver na lista acima OU se tiver cifrão nos dados
        if col in colunas_para_limpar or (df[col].dtype == "object" and df[col].astype(str).str.contains("R\$").any()):
             if df[col].dtype == "object":
                # Remove R$, remove ponto de milhar e troca vírgula por ponto
                df[col] = df[col].astype(str).str.replace("R$", "", regex=False)
                df[col] = df[col].str.replace(" ", "", regex=False) # Tira espaços vazios
                df[col] = df[col].str.replace(".", "", regex=False)
                df[col] = df[col].str.replace(",", ".", regex=False)
                
             # Converte para número
             df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    
    return df

# Carrega os dados da aba escolhida
df = load_data(gid_selecionado)

if df is None:
    st.error(f"Erro ao carregar a aba '{aba_selecionada}'. Verifique se a planilha está publicada na web (Arquivo > Compartilhar > Publicar na Web).")
    st.stop()


# --- LÓGICA DE EXIBIÇÃO: O QUE MOSTRAR EM CADA ABA? ---

# CASO 1: ABAS DETALHADAS (ORÇAMENTO X REALIZADO)
# Se o nome da aba tem "Orçamento", mostramos os gráficos bonitos
if "Orçamento" in aba_selecionada:
    
    st.markdown(f"### 📅 Visualizando: {aba_selecionada}")
    
    # --- FILTROS LATERAIS ---
    st.sidebar.subheader("Filtros")
    df_selection = df.copy()
    
    # Filtros Dinâmicos (cria filtro se a coluna existir)
    for coluna in ["Unidade", "Tier", "Status", "Beneficio"]:
        if coluna in df.columns:
            opcoes = sorted(df[coluna].astype(str).unique())
            escolha = st.sidebar.multiselect(f"Filtrar {coluna}:", options=opcoes, default=opcoes)
            if escolha:
                df_selection = df_selection[df_selection[coluna].isin(escolha)]

    # --- KPIS (NUMERÕES) ---
    # Verifica se as colunas de custo existem antes de calcular
    if "Custo Orçado" in df_selection.columns and "Custo Realizado" in df_selection.columns:
        total_orcado = df_selection["Custo Orçado"].sum()
        total_realizado = df_selection["Custo Realizado"].sum()
        diferenca = total_orcado - total_realizado

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Orçado", f"R$ {total_orcado:,.2f}")
        col2.metric("Total Realizado", f"R$ {total_realizado:,.2f}")
        col3.metric("Economia", f"R$ {diferenca:,.2f}", delta=f"{diferenca:,.2f}")
        
        st.markdown("---")
        
        # --- GRÁFICOS ---
        col_g1, col_g2 = st.columns(2)
        
        # Gráfico 1: Comparativo Total
        with col_g1:
            st.subheader("Comparativo Geral")
            # Prepara dados
            df_melted = df_selection.melt(
                value_vars=["Custo Orçado", "Custo Realizado"], 
                var_name="Tipo", 
                value_name="Valor"
            )
            df_grouped = df_melted.groupby("Tipo")["Valor"].sum().reset_index()
            
            fig1 = px.bar(
                df_grouped, x="Tipo", y="Valor", color="Tipo", text_auto=".2s", 
                color_discrete_map={"Custo Orçado": "#1f77b4", "Custo Realizado": "#ff7f0e"}
            )
            st.plotly_chart(fig1, use_container_width=True)

        # Gráfico 2: Por Benefício
        with col_g2:
            st.subheader("Por Benefício")
            if "Beneficio" in df_selection.columns:
                df_ben = df_selection.groupby("Beneficio")[["Custo Orçado", "Custo Realizado"]].sum().reset_index()
                df_ben_melted = df_ben.melt(id_vars=["Beneficio"], var_name="Tipo", value_name="Valor")
                
                fig2 = px.bar(
                    df_ben_melted, y="Beneficio", x="Valor", color="Tipo", 
                    barmode="group", orientation='h', height=400
                )
                st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("⚠️ As colunas 'Custo Orçado' e 'Custo Realizado' não foram encontradas nesta aba.")

    # --- BUSCA ---
    st.markdown("---")
    with st.expander("🔍 Busca de Colaborador (Clique para abrir)"):
        busca = st.text_input("Digite Nome ou ID:")
        if busca:
            mask = df.apply(lambda x: x.astype(str).str.contains(busca, case=False, na=False)).any(axis=1)
            st.dataframe(df[mask])
        else:
            st.dataframe(df_selection)


# CASO 2: ABAS DE RESUMO (TABELAS DINÂMICAS E DASHBOARDS DO EXCEL)
# Se for qualquer outra aba, mostramos a tabela pura, pois a estrutura muda muito
else:
    st.markdown(f"### 📑 Visualizando Tabela: {aba_selecionada}")
    st.info("Esta visão exibe os dados consolidados da planilha original.")
    
    # Exibe a tabela completa
    st.dataframe(df, use_container_width=True)
    
    # Gráfico Rápido Automático (se possível)
    cols_numericas = df.select_dtypes(include=['float64', 'int64']).columns
    cols_texto = df.select_dtypes(include=['object']).columns
    
    if len(cols_numericas) > 0 and len(cols_texto) > 0:
        st.markdown("---")
        st.markdown("**Gerador de Gráfico Rápido:**")
        c_x, c_y = st.columns(2)
        eixo_x = c_x.selectbox("Eixo X (Categorias)", options=cols_texto)
        eixo_y = c_y.selectbox("Eixo Y (Valores)", options=cols_numericas)
        
        fig_din = px.bar(df, x=eixo_x, y=eixo_y, title=f"{eixo_y} por {eixo_x}")
        st.plotly_chart(fig_din, use_container_width=True)
