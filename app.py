import streamlit as st
import pandas as pd
import plotly.express as px
import unicodedata

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

# Função para ordenar meses cronologicamente
def ordenar_dataset_por_mes(df, col_mes):
    mapa_meses = {
        'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
    }
    try:
        # Cria coluna auxiliar de ordem
        df['ordem_temp'] = df[col_mes].astype(str).str.lower().str[:3].map(mapa_meses).fillna(99)
        df_sorted = df.sort_values('ordem_temp')
        return df_sorted, df_sorted[col_mes].unique()
    except:
        return df, df[col_mes].unique()

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

df = load_data(gid_selecionado)

if df is None:
    st.error("Erro fatal ao carregar dados. Verifique a conexão com o Google Sheets.")
    st.stop()

# --- DETECTOR INTELIGENTE DE COLUNAS ---
def achar_coluna(df, termos):
    colunas_normalizadas = {col: remover_acentos(col) for col in df.columns}
    for termo in termos:
        termo_limpo = remover_acentos(termo)
        for col_original, col_limpa in colunas_normalizadas.items():
            if termo_limpo in col_limpa:
                return col_original
    return None

col_orcado = achar_coluna(df, ["orçado", "orcado", "budget", "meta"])
col_realizado = achar_coluna(df, ["realizado", "executado", "gasto", "soma"]) # Adicionei 'soma' para pegar colunas de pivot
col_beneficio = achar_coluna(df, ["beneficio", "benefício"])
col_mes = achar_coluna(df, ["mês", "mes", "data", "periodo"])
col_unidade = achar_coluna(df, ["unidade", "filial", "local"])
col_status = achar_coluna(df, ["status", "situação"])

# --- LÓGICA DE EXIBIÇÃO ---

# ==============================================================================
# VISUAL 1: ORÇAMENTO X REALIZADO (2026 E 2025)
# Aqui juntamos a lógica visual bonita e a tabela dinâmica embaixo
# ==============================================================================
if "Orçamento" in aba_selecionada or "Tabela dinâmica" in aba_selecionada:
    
    # Define o título baseado no ano selecionado
    ano = "2026" if "2026" in aba_selecionada else "2025"
    st.header(f"🎯 Painel Executivo {ano}")
    
    # --- FILTROS ---
    st.sidebar.subheader(f"Filtros {ano}")
    df_filtered = df.copy()
    
    cols_para_filtro = [col_mes, col_unidade, col_beneficio, col_status]
    for col in cols_para_filtro:
        if col and col in df.columns:
            opcoes = sorted(df[col].astype(str).unique())
            escolha = st.sidebar.multiselect(f"{col}:", options=opcoes, default=opcoes)
            if escolha:
                df_filtered = df_filtered[df_filtered[col].isin(escolha)]

    # --- KPIS (MÉTRICAS) ---
    # Para 2026 temos metas fixas, para 2025 calculamos do dataset
    meta_total = 0
    realizado_total = df_filtered[col_realizado].sum() if col_realizado else 0
    
    if "2026" in ano:
        meta_total = 3432000.00
        budget_mensal = 286000.00
    else:
        # Se for 2025, a meta é a soma da coluna "Orçado" (se existir)
        meta_total = df_filtered[col_orcado].sum() if col_orcado else 0
        budget_mensal = meta_total / 12 if meta_total > 0 else 0

    saldo = meta_total - realizado_total

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Budget Mensal (Médio)", formatar_moeda(budget_mensal))
    c2.metric("Budget Anual", formatar_moeda(meta_total))
    c3.metric("Realizado YTD", formatar_moeda(realizado_total))
    c4.metric("Saldo", formatar_moeda(saldo), delta=formatar_moeda(saldo))

    st.markdown("---")

    # --- GRÁFICOS (SUPERIOR) ---
    g1, g2 = st.columns(2)
    
    # 1. EVOLUÇÃO MENSAL
    with g1:
        st.subheader("Evolução Mensal")
        if col_mes and col_realizado:
            vars_plot = []
            if col_orcado: vars_plot.append(col_orcado)
            if col_realizado: vars_plot.append(col_realizado)
            
            df_chart = df_filtered.groupby(col_mes)[vars_plot].sum().reset_index()
            # Ordena Meses
            df_chart, ordem_meses = ordenar_dataset_por_mes(df_chart, col_mes)
            df_melted = df_chart.melt(id_vars=[col_mes], value_vars=vars_plot, var_name="Tipo", value_name="Valor")
            
            # Cores: Cinza e Vermelho
            cores = {}
            if col_orcado: cores[col_orcado] = "#D3D3D3"
            if col_realizado: cores[col_realizado] = "#8B0000"

            fig = px.bar(df_melted, x=col_mes, y="Valor", color="Tipo", barmode="group",
                         text_auto='.2s', color_discrete_map=cores)
            fig.update_layout(template="plotly_white", yaxis_tickprefix="R$ ", 
                              xaxis={'categoryorder':'array', 'categoryarray': ordem_meses},
                              legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig, use_container_width=True)
            
    # 2. SHARE POR BENEFÍCIO
    with g2:
        st.subheader("Share por Benefício")
        if col_beneficio and col_realizado:
            df_pizza = df_filtered.groupby(col_beneficio)[col_realizado].sum().reset_index()
            df_pizza = df_pizza.sort_values(col_realizado, ascending=False)
            
            fig_p = px.pie(df_pizza, values=col_realizado, names=col_beneficio, hole=0.5,
                           color_discrete_sequence=px.colors.sequential.Reds_r)
            fig_p.update_traces(textinfo='percent')
            fig_p.update_layout(template="plotly_white")
            st.plotly_chart(fig_p, use_container_width=True)

    # --- TABELA DINÂMICA (INFERIOR - A PEDIDO: JUNTO COM ORÇAMENTO) ---
    st.markdown("---")
    st.subheader(f"📑 Visão Matricial (Tabela Dinâmica {ano})")
    
    if col_beneficio and col_mes and col_realizado:
        try:
            # Pivot Table
            pivot = df_filtered.pivot_table(index=col_beneficio, columns=col_mes, values=col_realizado, aggfunc='sum', fill_value=0)
            
            # Ordena Colunas (Meses)
            pivot, _ = ordenar_dataset_por_mes(pivot.T.reset_index(), col_mes) # Truque para ordenar colunas
            pivot = pivot.set_index(col_mes).T # Volta ao normal
            
            # Coluna Total
            pivot["Total Anual"] = pivot.sum(axis=1)
            pivot = pivot.sort_values("Total Anual", ascending=False)
            
            # Estilo Heatmap Vermelho
            cols_meses = [c for c in pivot.columns if c != "Total Anual"]
            styler = pivot.style.background_gradient(cmap="Reds", subset=cols_meses, vmin=0)
            styler = styler.format("R$ {:,.2f}")
            styler = styler.applymap(lambda x: "background-color: #f0f2f6; font-weight: bold;", subset=["Total Anual"])
            
            st.dataframe(styler, use_container_width=True, height=500)
        except Exception as e:
            st.warning("Não foi possível gerar a matriz detalhada com os dados atuais.")
            st.dataframe(df_filtered.head())
    else:
        st.info("Faltam colunas (Benefício, Mês ou Realizado) para gerar a matriz.")


# ==============================================================================
# VISUAL 2: DASHBOARD - 2025 (RÉPLICA DO EXCEL)
# ==============================================================================
elif "Dashboard" in aba_selecionada:
    st.header("📊 Relatório de Benefícios (Réplica Excel)")
    
    # Filtros
    st.sidebar.subheader("Filtros Dashboard")
    df_dash = df.copy()
    if col_mes:
        meses = sorted(df_dash[col_mes].astype(str).unique())
        escolha_mes = st.sidebar.multiselect("Mês", meses, default=meses)
        if escolha_mes: df_dash = df_dash[df_dash[col_mes].isin(escolha_mes)]
        
    # --- LINHA 1: DOIS GRÁFICOS ---
    row1_1, row1_2 = st.columns([1, 1])
    
    # GRÁFICO 1: SUM de Realizado versus Benefício (Barra Vertical)
    with row1_1:
        st.markdown("**SUM de Realizado versus Benefício**")
        if col_beneficio and col_realizado:
            df_g1 = df_dash.groupby(col_beneficio)[col_realizado].sum().reset_index()
            # Ordena igual ao Excel (maior para menor visualmente costuma ser melhor, mas o Excel parecia aleatório, vou ordenar por valor)
            df_g1 = df_g1.sort_values(col_realizado, ascending=False)
            
            fig1 = px.bar(df_g1, x=col_beneficio, y=col_realizado, text_auto='.2s')
            fig1.update_traces(marker_color='#808080') # Cinza escuro como na imagem
            # Destaque para o maior (Saúde) em cinza mais escuro ou cor diferente se quiser
            fig1.update_layout(template="plotly_white", xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig1, use_container_width=True)
            
    # GRÁFICO 2: SUM de Realizado versus Mês (Rosca/Trimestre)
    with row1_2:
        st.markdown("**SUM de Realizado versus Mês (Distribuição)**")
        if col_mes and col_realizado:
            df_g2 = df_dash.groupby(col_mes)[col_realizado].sum().reset_index()
            
            # Gráfico de Rosca em Tons de Cinza
            fig2 = px.pie(df_g2, names=col_mes, values=col_realizado, hole=0.5,
                          color_discrete_sequence=px.colors.sequential.Greys_r)
            fig2.update_traces(textinfo='percent')
            fig2.update_layout(template="plotly_white")
            st.plotly_chart(fig2, use_container_width=True)

    # --- LINHA 2: GRÁFICO GRANDE ---
    st.markdown("---")
    st.markdown("**Evolução Detalhada: Realizado por Benefício e Mês**")
    
    # GRÁFICO 3: Barras Agrupadas (Timeline)
    if col_mes and col_beneficio and col_realizado:
        df_g3 = df_dash.groupby([col_mes, col_beneficio])[col_realizado].sum().reset_index()
        # Ordenação Cronológica
        df_g3, ordem_meses = ordenar_dataset_por_mes(df_g3, col_mes)
        
        # O gráfico do Excel mostra Mês no eixo X, Valor no Y, e cada benefício é uma barrinha agrupada
        fig3 = px.bar(df_g3, x=col_mes, y=col_realizado, color=col_beneficio, barmode="group",
                      color_discrete_sequence=px.colors.qualitative.G10) # Cores distintas para distinguir barras
        
        fig3.update_layout(
            template="plotly_white",
            xaxis={'categoryorder':'array', 'categoryarray': ordem_meses},
            yaxis_tickprefix="R$ ",
            legend=dict(orientation="v", y=1, x=1.02), # Legenda lateral
            height=500
        )
        st.plotly_chart(fig3, use_container_width=True)

# === CENÁRIO 3: PADRÃO DE SEGURANÇA ===
else:
    st.header(f"Visualização: {aba_selecionada}")
    st.dataframe(df, use_container_width=True)
