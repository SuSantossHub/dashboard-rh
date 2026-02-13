import streamlit as st
import pandas as pd
import plotly.express as px
import unicodedata

# 1. Configuração da Página
st.set_page_config(page_title="Dashboard RH Executivo", layout="wide")
st.title("📊 Dashboard de Benefícios Corporativos")

# --- CONFIGURAÇÃO DE GIDs (ABAS) ---
SHEET_ID = "10lEeyQAAOaHqpUTOfdMzaHgjfBpuNIHeCRabsv43WTQ"

# IDs das abas
GID_2026 = "1350897026"
GID_2025 = "1743422062"
GID_DASH_2025 = "2124043219"

# Menu de Navegação
OPCOES_MENU = [
    "Orçamento x Realizado | 2026",
    "Orçamento x Realizado | 2025",
    "Comparativo: 2025 vs 2026 (De/Para)",
    "Dashboard Trimestral"
]

# --- BARRA LATERAL ---
st.sidebar.header("Navegação")
aba_selecionada = st.sidebar.selectbox("Escolha a Visão:", OPCOES_MENU)

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

# --- CORREÇÃO DO MAPA DE MESES (SINTAXE ARRUMADA) ---
MAPA_MESES = {
    'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
}

def get_mes_ordem(nome_mes):
    # Pega as 3 primeiras letras (jan, fev...)
    chave = str(nome_mes).lower()[:3]
    return MAPA_MESES.get(chave, 99)

def get_trimestre(nome_mes):
    ordem = get_mes_ordem(nome_mes)
    if 1 <= ordem <= 3: return "Q1 (Jan-Mar)"
    elif 4 <= ordem <= 6: return "Q2 (Abr-Jun)"
    elif 7 <= ordem <= 9: return "Q3 (Jul-Set)"
    elif 10 <= ordem <= 12: return "Q4 (Out-Dez)"
    return "Desconhecido"

# --- DETECTOR INTELIGENTE DE COLUNAS ---
def achar_coluna(df, termos):
    colunas_normalizadas = {col: remover_acentos(col) for col in df.columns}
    for termo in termos:
        termo_limpo = remover_acentos(termo)
        for col_original, col_limpa in colunas_normalizadas.items():
            if termo_limpo in col_limpa:
                return col_original
    return None

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

# Identifica qual GID carregar baseado na seleção
gid_atual = GID_2026 # Padrão
if "2025" in aba_selecionada and "Comparativo" not in aba_selecionada:
    gid_atual = GID_2025
elif "Comparativo" in aba_selecionada:
    gid_atual = None # Caso especial, carrega os dois

# ==============================================================================
# VISÃO: COMPARATIVO 2025 vs 2026 (DE/PARA)
# ==============================================================================
if "Comparativo" in aba_selecionada:
    st.header("⚖️ Comparativo Anual: 2025 vs 2026")
    
    with st.spinner("Carregando dados de ambos os anos..."):
        df_2025 = load_data(GID_2025)
        df_2026 = load_data(GID_2026)
    
    if df_2025 is not None and df_2026 is not None:
        # Padroniza colunas
        col_realizado_25 = achar_coluna(df_2025, ["realizado", "executado", "soma"])
        col_mes_25 = achar_coluna(df_2025, ["mês", "mes", "data"])
        
        col_realizado_26 = achar_coluna(df_2026, ["realizado", "executado", "soma"])
        col_mes_26 = achar_coluna(df_2026, ["mês", "mes", "data"])

        # Calcula Totais
        total_25 = df_2025[col_realizado_25].sum()
        total_26 = df_2026[col_realizado_26].sum()
        delta = total_26 - total_25
        delta_perc = (delta / total_25 * 100) if total_25 > 0 else 0

        # KPIs Comparativos
        k1, k2, k3 = st.columns(3)
        k1.metric("Total 2025", formatar_moeda(total_25))
        k2.metric("Total 2026", formatar_moeda(total_26))
        k3.metric("Variação (R$)", formatar_moeda(delta), delta=f"{delta_perc:.1f}%", delta_color="inverse")

        st.markdown("---")
        
        # Gráfico Comparativo Mensal
        st.subheader("Evolução Mensal: 2025 vs 2026")
        
        # Prepara dados 2025
        df_chart_25 = df_2025.groupby(col_mes_25)[col_realizado_25].sum().reset_index()
        df_chart_25.columns = ['Mês', 'Valor']
        df_chart_25['Ano'] = '2025'
        
        # Prepara dados 2026
        df_chart_26 = df_2026.groupby(col_mes_26)[col_realizado_26].sum().reset_index()
        df_chart_26.columns = ['Mês', 'Valor']
        df_chart_26['Ano'] = '2026'
        
        # Junta tudo
        df_combined = pd.concat([df_chart_25, df_chart_26])
        
        # Ordenação
        df_combined['ordem'] = df_combined['Mês'].apply(get_mes_ordem)
        df_combined = df_combined.sort_values('ordem')
        
        # Gráfico Lado a Lado
        fig_comp = px.bar(
            df_combined, x="Mês", y="Valor", color="Ano", barmode="group",
            text_auto='.2s',
            color_discrete_map={'2025': '#D3D3D3', '2026': '#8B0000'} # 2025 Cinza, 2026 Vermelho
        )
        fig_comp.update_layout(template="plotly_white", yaxis_tickprefix="R$ ")
        st.plotly_chart(fig_comp, use_container_width=True)

    else:
        st.error("Erro ao carregar uma das planilhas para comparação.")

# ==============================================================================
# VISÃO: ORÇAMENTO x REALIZADO (2025 ou 2026)
# ==============================================================================
elif "Orçamento" in aba_selecionada:
    df = load_data(gid_atual)
    if df is not None:
        ano_titulo = "2026" if "2026" in aba_selecionada else "2025"
        st.header(f"🎯 Painel Executivo {ano_titulo}")
        
        # Identifica colunas
        col_orcado = achar_coluna(df, ["orçado", "orcado", "budget", "meta"])
        col_realizado = achar_coluna(df, ["realizado", "executado", "gasto", "soma"])
        col_beneficio = achar_coluna(df, ["beneficio", "benefício"])
        col_mes = achar_coluna(df, ["mês", "mes", "data"])
        col_unidade = achar_coluna(df, ["unidade", "filial"])

        # Filtros
        st.sidebar.subheader("Filtros")
        df_filtered = df.copy()
        
        if col_mes:
            meses = sorted(df[col_mes].astype(str).unique(), key=get_mes_ordem)
            sel_mes = st.sidebar.multiselect("Mês:", meses, default=meses)
            if sel_mes: df_filtered = df_filtered[df_filtered[col_mes].isin(sel_mes)]
            
        if col_beneficio:
            bens = sorted(df[col_beneficio].astype(str).unique())
            sel_ben = st.sidebar.multiselect("Benefício:", bens, default=bens)
            if sel_ben: df_filtered = df_filtered[df_filtered[col_beneficio].isin(sel_ben)]

        # KPIs
        realizado = df_filtered[col_realizado].sum() if col_realizado else 0
        BUDGET_ANUAL = 3432000.00
        saldo = BUDGET_ANUAL - realizado
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Budget Mensal", "R$ 286.000,00")
        c2.metric("Budget Anual", formatar_moeda(BUDGET_ANUAL))
        c3.metric("Realizado YTD", formatar_moeda(realizado))
        c4.metric("Saldo Anual", formatar_moeda(saldo), delta=formatar_moeda(saldo))
        
        st.markdown("---")
        
        # Gráficos
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("Evolução Mensal")
            if col_mes and col_realizado:
                vars_plot = []
                if col_orcado: vars_plot.append(col_orcado)
                if col_realizado: vars_plot.append(col_realizado)
                
                df_chart = df_filtered.groupby(col_mes)[vars_plot].sum().reset_index()
                df_chart['ordem'] = df_chart[col_mes].apply(get_mes_ordem)
                df_chart = df_chart.sort_values('ordem')
                
                df_melted = df_chart.melt(id_vars=[col_mes], value_vars=vars_plot, var_name="Tipo", value_name="Valor")
                
                cores = {col_realizado: '#8B0000'}
                if col_orcado: cores[col_orcado] = '#D3D3D3'
                
                fig = px.bar(df_melted, x=col_mes, y="Valor", color="Tipo", barmode="group", 
                             text_auto='.2s', color_discrete_map=cores)
                fig.update_layout(template="plotly_white", yaxis_tickprefix="R$ ", 
                                  xaxis={'categoryorder':'array', 'categoryarray': df_chart[col_mes].unique()})
                st.plotly_chart(fig, use_container_width=True)
        
        with g2:
            st.subheader("Share por Benefício")
            if col_beneficio and col_realizado:
                df_pizza = df_filtered.groupby(col_beneficio)[col_realizado].sum().reset_index()
                df_pizza = df_pizza.sort_values(col_realizado, ascending=False)
                fig_p = px.pie(df_pizza, values=col_realizado, names=col_beneficio, hole=0.5,
                               color_discrete_sequence=px.colors.sequential.Reds_r)
                fig_p.update_traces(textposition='inside', textinfo='percent+label', textfont=dict(color='black'))
                fig_p.update_layout(showlegend=False)
                st.plotly_chart(fig_p, use_container_width=True)

        # Tabela Matricial
        st.markdown("---")
        st.subheader("📑 Visão Matricial")
        if col_beneficio and col_mes and col_realizado:
            try:
                pivot = df_filtered.pivot_table(index=col_beneficio, columns=col_mes, values=col_realizado, aggfunc='sum', fill_value=0)
                pivot = pivot[sorted(pivot.columns, key=get_mes_ordem)] # Ordena colunas
                pivot["Total Anual"] = pivot.sum(axis=1)
                pivot = pivot.sort_values("Total Anual", ascending=False)
                
                # Linha Total
                linha_total = pivot.sum()
                linha_total.name = "TOTAL GERAL"
                pivot = pd.concat([pivot, linha_total.to_frame().T])
                
                # Estilo
                styler = pivot.style.format("R$ {:,.2f}")
                cols_heat = [c for c in pivot.columns if c != "Total Anual"]
                styler = styler.background_gradient(cmap="Reds", subset=(pivot.index[:-1], cols_heat), vmin=0)
                styler = styler.applymap(lambda x: "background-color: #f0f2f6; color: black; font-weight: bold;", subset=["Total Anual"])
                
                def highlight_total_row(s):
                    return ['background-color: #d3d3d3; color: black; font-weight: bold' if s.name == 'TOTAL GERAL' else '' for _ in s]
                styler = styler.apply(highlight_total_row, axis=1)
                
                st.dataframe(styler, use_container_width=True)
            except Exception as e:
                st.warning(f"Erro ao gerar matriz: {e}")

# ==============================================================================
# VISÃO: DASHBOARD TRIMESTRAL
# ==============================================================================
elif "Dashboard" in aba_selecionada:
    st.header("📊 Dashboard Executivo e Trimestral")
    df = load_data(GID_DASH_2025) # Usa o GID específico do Dashboard se necessário, ou o de 2025
    if df is None: df = load_data(GID_2025) # Fallback

    if df is not None:
        col_realizado = achar_coluna(df, ["realizado", "executado", "soma"])
        col_mes = achar_coluna(df, ["mês", "mes", "data"])
        col_beneficio = achar_coluna(df, ["beneficio", "benefício"])

        if col_mes:
            # Cria coluna Trimestre
            df['Trimestre'] = df[col_mes].apply(get_trimestre)
            
            # Filtro Trimestre
            tris = sorted(df['Trimestre'].unique())
            sel_tri = st.sidebar.multiselect("Trimestre:", tris)
            df_dash = df[df['Trimestre'].isin(sel_tri)] if sel_tri else df.copy()

            # Gráfico 1: Trimestre
            st.subheader("Custo por Trimestre (Quarters)")
            if col_realizado:
                df_tri = df_dash.groupby('Trimestre')[col_realizado].sum().reset_index()
                fig_q = px.bar(df_tri, x='Trimestre', y=col_realizado, text_auto='.2s', 
                               color_discrete_sequence=['#8B0000'])
                fig_q.update_layout(template="plotly_white", yaxis_tickprefix="R$ ")
                st.plotly_chart(fig_q, use_container_width=True)

            # Gráfico 2: Benefício
            st.subheader("Total Realizado por Benefício")
            if col_beneficio and col_realizado:
                df_ben = df_dash.groupby(col_beneficio)[col_realizado].sum().reset_index()
                df_ben = df_ben.sort_values(col_realizado, ascending=False)
                fig_b = px.bar(df_ben, x=col_beneficio, y=col_realizado, text_auto='.2s',
                               color=col_realizado, color_continuous_scale="Reds")
                fig_b.update_layout(template="plotly_white", yaxis_tickprefix="R$ ")
                st.plotly_chart(fig_b, use_container_width=True)
        else:
            st.warning("Coluna de Mês não encontrada para calcular trimestres.")
