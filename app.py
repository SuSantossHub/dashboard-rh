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
    try:
        # Garante que é número e formata: 1234.56 -> R$ 1.234,56
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
    termos_financeiros = ["custo", "valor", "total", "orçado", "realizado", "budget"]
    
    for col in df.columns:
        # Verifica se o nome da coluna tem algum termo financeiro (ignorando maiúsculas)
        eh_financeiro = any(termo in col.lower() for termo in termos_financeiros)
        # Ou se o conteúdo tem "R$"
        tem_cifrao = df[col].dtype == "object" and df[col].astype(str).str.contains("R\$").any()
        
        if eh_financeiro or tem_cifrao:
             if df[col].dtype == "object":
                # Limpa sujeiras de texto (R$, espaços, pontos)
                df[col] = df[col].astype(str).str.replace("R$", "", regex=False)
                df[col] = df[col].str.replace(" ", "", regex=False)
                df[col] = df[col].str.replace(".", "", regex=False) # Tira ponto de milhar
                df[col] = df[col].str.replace(",", ".", regex=False) # Vira ponto decimal
             # Converte para número
             df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

df = load_data(gid_selecionado)

if df is None:
    st.error("Erro ao carregar dados. Verifique a conexão com o Google Sheets.")
    st.stop()

# --- DETECTOR INTELIGENTE DE COLUNAS ---
# Isso resolve o problema de "Benefício" com acento vs "Beneficio" sem acento
def achar_coluna(df, termos):
    for col in df.columns:
        if any(t in col.lower() for t in termos):
            return col
    return None

col_orcado = achar_coluna(df, ["orçado", "orcado"])
col_realizado = achar_coluna(df, ["realizado", "executado"])
col_beneficio = achar_coluna(df, ["beneficio", "benefício"])
col_mes = achar_coluna(df, ["mês", "mes", "data"])
col_unidade = achar_coluna(df, ["unidade", "filial", "local"])
col_status = achar_coluna(df, ["status", "situação"])

# --- LÓGICA DE EXIBIÇÃO ---

# === CENÁRIO 1: VISÃO 2026 (COM PAINEL DE METAS) ===
if "2026" in aba_selecionada and "Orçamento" in aba_selecionada:
    
    st.header("🎯 Painel Executivo 2026: Orçado vs Realizado")
    
    # --- PAINEL DE METAS (BUDGET) ---
    st.markdown("### 📌 Indicadores de Meta (Budget)")
    
    META_ORCAMENTO_MENSAL = 286000.00
    META_ORCAMENTO_ANUAL = 3432000.00
    
    if col_realizado:
        total_realizado_acumulado = df[col_realizado].sum()
    else:
        total_realizado_acumulado = 0
    
    saldo_anual = META_ORCAMENTO_ANUAL - total_realizado_acumulado
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Budget Mensal (Meta)", formatar_moeda(META_ORCAMENTO_MENSAL))
    with c2: st.metric("Budget Anual (Meta)", formatar_moeda(META_ORCAMENTO_ANUAL))
    with c3: st.metric("Realizado Acumulado", formatar_moeda(total_realizado_acumulado))
    with c4: st.metric("Saldo Disponível", formatar_moeda(saldo_anual), delta=formatar_moeda(saldo_anual))

    st.markdown("---")

    # --- FILTROS ---
    st.sidebar.subheader("Filtros 2026")
    df_filtered = df.copy()
    
    # Lista de colunas identificadas para filtrar
    cols_para_filtro = [col_mes, col_unidade, col_beneficio, col_status]
    
    for col in cols_para_filtro:
        if col: # Se a coluna foi encontrada na planilha
            opcoes = sorted(df[col].astype(str).unique())
            escolha = st.sidebar.multiselect(f"{col}:", options=opcoes, default=opcoes)
            if escolha:
                df_filtered = df_filtered[df_filtered[col].isin(escolha)]

    # --- GRÁFICOS ---
    g1, g2 = st.columns(2)
    
    with g1:
        st.subheader("Evolução Mensal")
        if col_orcado and col_realizado and col_mes:
            df_mes = df_filtered.groupby(col_mes)[[col_orcado, col_realizado]].sum().reset_index()
            fig_evolucao = px.bar(
                df_mes, x=col_mes, y=[col_orcado, col_realizado],
                barmode="group", title="Orçado vs Realizado", text_auto=".2s",
                color_discrete_map={col_orcado: "#1f77b4", col_realizado: "#ff7f0e"}
            )
            # Formatação R$ no Eixo Y
            fig_evolucao.update_layout(yaxis_tickprefix="R$ ", hovermode="x unified")
            st.plotly_chart(fig_evolucao, use_container_width=True)
            
    with g2:
        st.subheader("Share por Benefício")
        # AQUI ESTAVA O PROBLEMA: Agora usamos 'col_beneficio' que acha com ou sem acento
        if col_beneficio and col_realizado:
            df_ben = df_filtered.groupby(col_beneficio)[col_realizado].sum().reset_index()
            # Gráfico de Pizza (Rosca)
            fig_pizza = px.pie(
                df_ben, 
                values=col_realizado, 
                names=col_beneficio, 
                hole=0.4
            )
            st.plotly_chart(fig_pizza, use_container_width=True)
        else:
            st.warning("Não foi possível gerar este gráfico. Verifique se as colunas 'Benefício' e 'Realizado' existem.")

    # --- TABELA DE DETALHAMENTO ---
    st.markdown("---")
    st.subheader("Detalhamento Analítico")
    
    # 1. Filtra colunas indesejadas (sem usar lista quebrada)
    colunas_finais = []
    for c in df_filtered.columns:
        if c not in ["ID", "Unnamed: 0"]:
            colunas_finais.append(c)
    
    df_display = df_filtered[colunas_finais].copy()
    
    # 2. Aplica formatação R$ visualmente
    termos_dinheiro = ["custo", "valor", "total", "orçado", "realizado", "budget"]
    
    for col in df_display.columns:
        # Se for numérico e tiver nome de dinheiro
        if pd.api.types.is_numeric_dtype(df_display[col]):
            if any(t in col.lower() for t in termos_dinheiro):
                df_display[col] = df_display[col].apply(formatar_moeda)

    # 3. Mostra tabela sem índice numérico
    st.dataframe(df_display, hide_index=True, use_container_width=True)

# === CENÁRIO 2: OUTRAS ABAS ===
else:
    st.header(f"Visualização: {aba_selecionada}")
    
    df_display_geral = df.copy()
    
    # Tenta formatar dinheiro se achar colunas numéricas
    termos_dinheiro = ["custo", "valor", "total", "orçado", "realizado", "budget"]
    for col in df_display_geral.columns:
         if pd.api.types.is_numeric_dtype(df_display_geral[col]):
            if any(t in col.lower() for t in termos_dinheiro):
                df_display_geral[col] = df_display_geral[col].apply(formatar_moeda)
             
    st.dataframe(df_display_geral, hide_index=True, use_container_width=True)
