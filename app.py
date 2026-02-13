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

    termos_financeiros = ["custo", "valor", "total", "orçado", "realizado", "budget"]
    
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

if "2026" in aba_selecionada and "Orçamento" in aba_selecionada:
    
    st.header("🎯 Painel Executivo 2026")
    
    # --- PAINEL DE METAS ---
    META_ORCAMENTO_MENSAL = 286000.00
    META_ORCAMENTO_ANUAL = 3432000.00
    
    total_realizado_acumulado = df[col_realizado].sum() if col_realizado else 0
    saldo_anual = META_ORCAMENTO_ANUAL - total_realizado_acumulado
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Budget Mensal", formatar_moeda(META_ORCAMENTO_MENSAL))
    c2.metric("Budget Anual", formatar_moeda(META_ORCAMENTO_ANUAL))
    c3.metric("Realizado YTD", formatar_moeda(total_realizado_acumulado))
    # Saldo continua verde se positivo (bom) e vermelho se negativo (ruim), padrão de finanças.
    c4.metric("Saldo Disponível", formatar_moeda(saldo_anual), delta=formatar_moeda(saldo_anual))

    st.markdown("---")

    # --- FILTROS ---
    st.sidebar.subheader("Filtros")
    df_filtered = df.copy()
    
    cols_para_filtro = [col_mes, col_unidade, col_beneficio, col_status]
    for col in cols_para_filtro:
        if col:
            opcoes = sorted(df[col].astype(str).unique())
            escolha = st.sidebar.multiselect(f"{col}:", options=opcoes, default=opcoes)
            if escolha:
                df_filtered = df_filtered[df_filtered[col].isin(escolha)]

    # --- GRÁFICOS (AGORA EM VERMELHO) ---
    g1, g2 = st.columns(2)
    
    # GRÁFICO 1: EVOLUÇÃO MENSAL
    with g1:
        st.subheader("Evolução Mensal")
        
        if col_mes:
            vars_to_plot = []
            if col_orcado: vars_to_plot.append(col_orcado)
            if col_realizado: vars_to_plot.append(col_realizado)
            
            if vars_to_plot:
                df_melted = df_filtered.groupby(col_mes)[vars_to_plot].sum().reset_index()
                df_melted = df_melted.melt(id_vars=[col_mes], value_vars=vars_to_plot, var_name="Tipo", value_name="Valor")
                
                # Mapa de cores VERMELHO: Orçado (Cinza Claro), Realizado (Vermelho Escuro)
                mapa_cores = {}
                if col_orcado: mapa_cores[col_orcado] = "#D3D3D3" # Cinza Neutro
                if col_realizado: mapa_cores[col_realizado] = "#8B0000" # Vermelho Sangue (DarkRed)
                
                fig_evolucao = px.bar(
                    df_melted, 
                    x=col_mes, 
                    y="Valor", 
                    color="Tipo",
                    barmode="group",
                    text_auto='.2s',
                    color_discrete_map=mapa_cores
                )
                
                fig_evolucao.update_layout(
                    template="plotly_white",
                    yaxis_tickprefix="R$ ",
                    hovermode="x unified",
                    legend=dict(orientation="h", y=1.1)
                )
                st.plotly_chart(fig_evolucao, use_container_width=True)
            else:
                st.warning("Sem dados de valor (Orçado/Realizado) para exibir.")
        else:
            st.warning("Coluna de 'Mês' não encontrada.")
            
    # GRÁFICO 2: SHARE POR BENEFÍCIO (DEGRADÊ DE VERMELHOS)
    with g2:
        st.subheader("Share por Benefício")
        if col_beneficio and col_realizado:
            df_ben = df_filtered.groupby(col_beneficio)[col_realizado].sum().reset_index()
            df_ben = df_ben.sort_values(by=col_realizado, ascending=False)
            
            fig_pizza = px.pie(
                df_ben, 
                values=col_realizado, 
                names=col_beneficio, 
                hole=0.5,
                # Muda para tons de Vermelho (Reds_r = Reds Reversed)
                color_discrete_sequence=px.colors.sequential.Reds_r 
            )
            fig_pizza.update_traces(textinfo='percent') 
            fig_pizza.update_layout(template="plotly_white")
            st.plotly_chart(fig_pizza, use_container_width=True)

    # --- TABELA ---
    st.markdown("---")
    st.subheader("Detalhamento Analítico")
    
    colunas_finais = [c for c in df_filtered.columns if c not in ["ID", "Unnamed: 0"]]
    df_display = df_filtered[colunas_finais].copy()
    
    termos_dinheiro = ["custo", "valor", "total", "orçado", "realizado", "budget"]
    for col in df_display.columns:
        if pd.api.types.is_numeric_dtype(df_display[col]):
            if any(t in col.lower() for t in termos_dinheiro):
                df_display[col] = df_display[col].apply(formatar_moeda)

    st.dataframe(df_display, hide_index=True, use_container_width=True)

else:
    # OUTRAS ABAS
    st.header(f"Visualização: {aba_selecionada}")
    st.dataframe(df, hide_index=True, use_container_width=True)
