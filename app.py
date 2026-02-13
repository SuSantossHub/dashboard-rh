import streamlit as st
import pandas as pd
import plotly.express as px
import unicodedata

# 1. Configuração da Página
st.set_page_config(page_title="Dashboard RH Executivo", layout="wide")
st.title("📊 Dashboard de Benefícios Corporativos")

# --- CONFIGURAÇÃO DAS ABAS (GIDs) ---
SHEET_ID = "10lEeyQAAOaHqpUTOfdMzaHgjfBpuNIHeCRabsv43WTQ"

# Navegação Limpa
DICIONARIO_DE_ABAS = {
    "Orçamento x Realizado | 2026": "1350897026",
    "Orçamento x Realizado | 2025": "1743422062",
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

# Mapa de meses para ordenação
MAPA_MESES = {
    'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
}

def get_mes_ordem(nome_mes):
    chave = str(nome_mes).lower()[:3]
    return MAPA_MESES.get(chave, 99)

def get_trimestre(nome_mes):
    ordem = get_mes_ordem(nome_mes)
    if 1 <= ordem <= 3: return "Q1 (Jan-Mar)"
    elif 4 <= ordem <= 6: return "Q2 (Abr-Jun)"
    elif 7 <= ordem <= 9: return "Q3 (Jul-Set)"
    elif 10 <= ordem <= 12: return "Q4 (Out-Dez)"
    return "Outros"

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
col_realizado = achar_coluna(df, ["realizado", "executado", "gasto", "soma"])
col_beneficio = achar_coluna(df, ["beneficio", "benefício"])
col_mes = achar_coluna(df, ["mês", "mes", "data", "periodo"])
col_unidade = achar_coluna(df, ["unidade", "filial", "local"])
col_status = achar_coluna(df, ["status", "situação"])

# --- LÓGICA DE EXIBIÇÃO ---

# ==============================================================================
# VISUAL 1: ORÇAMENTO X REALIZADO (2026 E 2025)
# ==============================================================================
if "Orçamento" in aba_selecionada:
    
    ano_titulo = "2026" if "2026" in aba_selecionada else "2025"
    st.header(f"🎯 Painel Executivo {ano_titulo}")
    
    # --- FILTROS (ORGANIZADOS) ---
    st.sidebar.subheader(f"Filtros")
    df_filtered = df.copy()
    
    # Filtro de Mês (Cronológico)
    if col_mes and col_mes in df.columns:
        meses_disponiveis = df[col_mes].astype(str).unique()
        meses_ordenados = sorted(meses_disponiveis, key=get_mes_ordem)
        escolha_mes = st.sidebar.multiselect("Mês:", options=meses_ordenados, default=meses_ordenados)
        if escolha_mes:
            df_filtered = df_filtered[df_filtered[col_mes].isin(escolha_mes)]
            
    # Filtro de Benefício (Alfabético)
    if col_beneficio and col_beneficio in df.columns:
        beneficios_disponiveis = sorted(df[col_beneficio].astype(str).unique())
        escolha_ben = st.sidebar.multiselect("Benefício:", options=beneficios_disponiveis, default=beneficios_disponiveis)
        if escolha_ben:
            df_filtered = df_filtered[df_filtered[col_beneficio].isin(escolha_ben)]

    # Outros filtros
    if col_unidade and col_unidade in df.columns:
        opcoes = sorted(df[col_unidade].astype(str).unique())
        escolha = st.sidebar.multiselect("Unidade:", options=opcoes, default=opcoes)
        if escolha: df_filtered = df_filtered[df_filtered[col_unidade].isin(escolha)]

    # --- KPIS (MÉTRICAS FIXAS 286k) ---
    realizado_total = df_filtered[col_realizado].sum() if col_realizado else 0
    
    BUDGET_MENSAL = 286000.00
    BUDGET_ANUAL = 3432000.00 
    
    saldo = BUDGET_ANUAL - realizado_total

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Budget Mensal (Médio)", formatar_moeda(BUDGET_MENSAL))
    c2.metric("Budget Anual", formatar_moeda(BUDGET_ANUAL))
    c3.metric("Realizado YTD", formatar_moeda(realizado_total))
    c4.metric("Saldo Anual", formatar_moeda(saldo), delta=formatar_moeda(saldo))

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
            
            # Ordenação
            df_chart['ordem_temp'] = df_chart[col_mes].apply(get_mes_ordem)
            df_chart = df_chart.sort_values('ordem_temp')
            lista_meses_ordenada = df_chart[col_mes].unique()
            
            df_melted = df_chart.melt(id_vars=[col_mes], value_vars=vars_plot, var_name="Tipo", value_name="Valor")
            
            cores = {}
            if col_orcado: cores[col_orcado] = "#D3D3D3"
            if col_realizado: cores[col_realizado] = "#8B0000"

            fig = px.bar(df_melted, x=col_mes, y="Valor", color="Tipo", barmode="group",
                         text_auto='.2s', color_discrete_map=cores)
            fig.update_layout(template="plotly_white", yaxis_tickprefix="R$ ", 
                              xaxis={'categoryorder':'array', 'categoryarray': lista_meses_ordenada},
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
            
            fig_p.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                textfont=dict(color='#000000', size=14)
            )
            fig_p.update_layout(template="plotly_white", showlegend=False)
            st.plotly_chart(fig_p, use_container_width=True)

    # --- TABELA MATRICIAL (VISÃO CONSOLIDADA) ---
    st.markdown("---")
    st.subheader(f"📑 Visão Matricial de Custos")
    
    if col_beneficio and col_mes and col_realizado:
        try:
            # 1. Pivot Table
            pivot = df_filtered.pivot_table(index=col_beneficio, columns=col_mes, values=col_realizado, aggfunc='sum', fill_value=0)
            
            # 2. Ordena Colunas (Meses)
            colunas_meses = sorted(pivot.columns, key=get_mes_ordem)
            pivot = pivot[colunas_meses]
            
            # 3. Coluna Total Lateral (Renomeada)
            NOME_COLUNA_TOTAL = "Total Anual por Benefício"
            pivot[NOME_COLUNA_TOTAL] = pivot.sum(axis=1)
            pivot = pivot.sort_values(NOME_COLUNA_TOTAL, ascending=False)
            
            # 4. Linha Total Final (TOTAL GERAL)
            # Calculamos a soma de todas as colunas
            linha_total = pivot.sum()
            linha_total.name = "TOTAL GERAL"
            # Adiciona a linha ao final do dataframe
            pivot = pd.concat([pivot, linha_total.to_frame().T])

            # 5. Estilização
            
            # Define formatação de moeda para toda a tabela
            styler = pivot.style.format("R$ {:,.2f}")

            # Aplica Heatmap (Vermelho) SOMENTE nas colunas de meses e IGNORANDO a linha de Total Geral
            # (Para não distorcer a escala de cores com valores gigantes)
            # Pega todas as colunas menos a de Total
            cols_heatmap = [c for c in pivot.columns if c != NOME_COLUNA_TOTAL]
            # Pega todas as linhas menos a última (Total Geral)
            rows_heatmap = pivot.index[:-1]
            
            styler = styler.background_gradient(
                cmap="Reds", 
                subset=(rows_heatmap, cols_heatmap), # Aplica só no miolo da tabela
                vmin=0
            )
            
            # Estilo da Coluna "Total Anual por Benefício" (Cinza Claro)
            styler = styler.applymap(
                lambda x: "background-color: #f0f2f6; color: black; font-weight: bold;", 
                subset=[NOME_COLUNA_TOTAL]
            )

            # Estilo da Linha "TOTAL GERAL" (Cinza Escuro no Rodapé)
            # Usamos axis=1 para aplicar a linha inteira
            def estilo_linha_total(s):
                if s.name == "TOTAL GERAL":
                    return ['background-color: #d3d3d3; color: black; font-weight: bold; border-top: 2px solid #000000'] * len(s)
                else:
                    return [''] * len(s)

            styler = styler.apply(estilo_linha_total, axis=1)
            
            st.dataframe(styler, use_container_width=True, height=600)
            
            csv = pivot.to_csv().encode('utf-8')
            st.download_button("📥 Baixar Tabela Matricial", data=csv, file_name=f'matriz_{ano_titulo}.csv', mime='text/csv')
            
        except Exception as e:
            st.warning(f"Não foi possível gerar a matriz: {e}")
    else:
        st.info("Faltam colunas (Benefício, Mês ou Realizado) para gerar a matriz.")


# ==============================================================================
# VISUAL 2: DASHBOARD FINAL
# ==============================================================================
elif "Dashboard" in aba_selecionada:
    st.header("📊 Dashboard Executivo e Trimestral")
    
    st.sidebar.subheader("Filtros Dashboard")
    df_dash = df.copy()
    
    if col_mes:
        df_dash['Trimestre'] = df_dash[col_mes].apply(get_trimestre)
        trimestres = sorted(df_dash['Trimestre'].unique())
        escolha_tri = st.sidebar.multiselect("Filtrar Trimestre:", trimestres)
        if escolha_tri:
            df_dash = df_dash[df_dash['Trimestre'].isin(escolha_tri)]

    # GRÁFICO 1
    st.subheader("Custo por Trimestre (Quarters)")
    if 'Trimestre' in df_dash.columns and col_realizado:
        df_tri = df_dash.groupby('Trimestre')[col_realizado].sum().reset_index()
        fig_q = px.bar(df_tri, x='Trimestre', y=col_realizado, text_auto='.2s',
                       title="Evolução Trimestral", color_discrete_sequence=['#8B0000'])
        fig_q.update_layout(template="plotly_white", yaxis_tickprefix="R$ ")
        st.plotly_chart(fig_q, use_container_width=True)
    else:
        st.warning("Dados insuficientes para trimestres.")
        
    st.markdown("---")
    
    # GRÁFICO 2
    st.subheader("Total Realizado por Benefício")
    if col_beneficio and col_realizado:
        df_ben = df_dash.groupby(col_beneficio)[col_realizado].sum().reset_index()
        df_ben = df_ben.sort_values(col_realizado, ascending=False)
        fig_b = px.bar(df_ben, x=col_beneficio, y=col_realizado, text_auto='.2s',
                       color=col_realizado, color_continuous_scale="Reds")
        fig_b.update_layout(template="plotly_white", yaxis_tickprefix="R$ ", xaxis_title=None)
        st.plotly_chart(fig_b, use_container_width=True)

# === CENÁRIO ERRO ===
else:
    st.dataframe(df)
