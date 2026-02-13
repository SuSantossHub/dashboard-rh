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
    # Transforma 'Mês' em 'mes', 'Orçado' em 'orcado'
    try:
        nfkd = unicodedata.normalize('NFKD', str(texto))
        return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    except:
        return str(texto).lower()

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

# --- DETECTOR INTELIGENTE DE COLUNAS (BLINDADO) ---
def achar_coluna(df, termos):
    colunas_normalizadas = {col: remover_acentos(col) for col in df.columns}
    for termo in termos:
        termo_limpo = remover_acentos(termo)
        for col_original, col_limpa in colunas_normalizadas.items():
            if termo_limpo in col_limpa:
                return col_original
    return None

col_orcado = achar_coluna(df, ["orçado", "orcado", "budget", "meta"])
col_realizado = achar_coluna(df, ["realizado", "executado", "gasto"])
col_beneficio = achar_coluna(df, ["beneficio", "benefício"])
col_mes = achar_coluna(df, ["mês", "mes", "data", "periodo"])
col_unidade = achar_coluna(df, ["unidade", "filial", "local"])
col_status = achar_coluna(df, ["status", "situação"])

# --- LÓGICA DE EXIBIÇÃO ---

# === CENÁRIO 1: ORÇAMENTO X REALIZADO 2026 ===
if "2026" in aba_selecionada and "Orçamento" in aba_selecionada:
    
    st.header("🎯 Painel Executivo 2026")
    
    META_ORCAMENTO_MENSAL = 286000.00
    META_ORCAMENTO_ANUAL = 3432000.00
    
    total_realizado_acumulado = df[col_realizado].sum() if col_realizado else 0
    saldo_anual = META_ORCAMENTO_ANUAL - total_realizado_acumulado
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Budget Mensal", formatar_moeda(META_ORCAMENTO_MENSAL))
    c2.metric("Budget Anual", formatar_moeda(META_ORCAMENTO_ANUAL))
    c3.metric("Realizado YTD", formatar_moeda(total_realizado_acumulado))
    c4.metric("Saldo Disponível", formatar_moeda(saldo_anual), delta=formatar_moeda(saldo_anual))

    st.markdown("---")

    st.sidebar.subheader("Filtros")
    df_filtered = df.copy()
    
    cols_para_filtro = [col_mes, col_unidade, col_beneficio, col_status]
    for col in cols_para_filtro:
        if col:
            opcoes = sorted(df[col].astype(str).unique())
            escolha = st.sidebar.multiselect(f"{col}:", options=opcoes, default=opcoes)
            if escolha:
                df_filtered = df_filtered[df_filtered[col].isin(escolha)]

    g1, g2 = st.columns(2)
    
    with g1:
        st.subheader("Evolução Mensal")
        if col_mes:
            vars_to_plot = []
            if col_orcado: vars_to_plot.append(col_orcado)
            if col_realizado: vars_to_plot.append(col_realizado)
            
            if vars_to_plot:
                # Tenta criar o gráfico dentro de um bloco protegido
                try:
                    df_melted = df_filtered.groupby(col_mes)[vars_to_plot].sum().reset_index()
                    df_melted = df_melted.melt(id_vars=[col_mes], value_vars=vars_to_plot, var_name="Tipo", value_name="Valor")
                    
                    # --- TENTATIVA DE ORDENAÇÃO DE MESES ---
                    try:
                        mapa_meses = {
                            'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
                            'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
                        }
                        # Pega as 3 primeiras letras, força minusculo e mapeia
                        df_melted['ordem'] = df_melted[col_mes].astype(str).str.lower().str[:3].map(mapa_meses)
                        df_melted['ordem'] = df_melted['ordem'].fillna(99) # Se não achar, joga pro fim
                        df_melted = df_melted.sort_values('ordem')
                    except:
                        pass # Se der erro na ordenação, segue a vida sem ordenar
                    # ---------------------------------------

                    mapa_cores = {}
                    if col_orcado: mapa_cores[col_orcado] = "#D3D3D3"
                    if col_realizado: mapa_cores[col_realizado] = "#8B0000"
                    
                    fig_evolucao = px.bar(
                        df_melted, x=col_mes, y="Valor", color="Tipo",
                        barmode="group", text_auto='.2s', color_discrete_map=mapa_cores
                    )
                    
                    fig_evolucao.update_layout(
                        template="plotly_white", 
                        yaxis_tickprefix="R$ ", 
                        hovermode="x unified", 
                        legend=dict(orientation="h", y=1.1),
                        xaxis={'categoryorder':'array', 'categoryarray': df_melted[col_mes].unique()}
                    )
                    st.plotly_chart(fig_evolucao, use_container_width=True)
                except Exception as e:
                    st.error(f"Não foi possível gerar o gráfico de barras: {e}")
            else:
                st.warning("Sem colunas de valor (Orçado/Realizado) identificadas.")
        else:
            st.warning("Coluna de Mês não encontrada.")
            
    with g2:
        st.subheader("Share por Benefício")
        if col_beneficio and col_realizado:
            try:
                df_ben = df_filtered.groupby(col_beneficio)[col_realizado].sum().reset_index()
                df_ben = df_ben.sort_values(by=col_realizado, ascending=False)
                
                fig_pizza = px.pie(
                    df_ben, values=col_realizado, names=col_beneficio, hole=0.5,
                    color_discrete_sequence=px.colors.sequential.Reds_r 
                )
                fig_pizza.update_traces(textinfo='percent') 
                fig_pizza.update_layout(template="plotly_white")
                st.plotly_chart(fig_pizza, use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao gerar gráfico de pizza: {e}")

    st.markdown("---")
    st.subheader("Detalhamento Analítico")
    
    try:
        colunas_finais = [c for c in df_filtered.columns if c not in ["ID", "Unnamed: 0"]]
        df_display = df_filtered[colunas_finais].copy()
        termos_dinheiro = ["custo", "valor", "total", "orçado", "realizado", "budget"]
        for col in df_display.columns:
            if pd.api.types.is_numeric_dtype(df_display[col]):
                if any(t in remover_acentos(col) for t in termos_dinheiro):
                    df_display[col] = df_display[col].apply(formatar_moeda)

        st.dataframe(df_display, hide_index=True, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao exibir tabela: {e}")

# === CENÁRIO 2: TABELA DINÂMICA 2026 ===
elif gid_selecionado == "763072509":
    st.header(f"📑 {aba_selecionada}")
    st.markdown("Visão matricial com destaque para custos elevados.")

    try:
        cols_limpas = [c for c in df.columns if "Unnamed" not in c and c != "ID"]
        df_pivot = df[cols_limpas].copy()
        cols_numericas = df_pivot.select_dtypes(include=['float64', 'int64']).columns
        
        styler = df_pivot.style.background_gradient(cmap="Reds", subset=cols_numericas)
        for col in cols_numericas:
            styler = styler.format(formatter="R$ {:,.2f}", subset=col)

        st.dataframe(styler, height=800, use_container_width=True)

        csv = df_pivot.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar Tabela em Excel (CSV)",
            data=csv,
            file_name='tabela_dinamica_2026.csv',
            mime='text/csv',
        )
    except Exception as e:
        st.error(f"Erro ao gerar tabela dinâmica: {e}")

# === CENÁRIO 3: OUTRAS ABAS ===
else:
    st.header(f"Visualização: {aba_selecionada}")
    df_display_geral = df.copy()
    try:
        termos_dinheiro = ["custo", "valor", "total", "orçado", "realizado", "budget"]
        for col in df_display_geral.columns:
             if pd.api.types.is_numeric_dtype(df_display_geral[col]):
                if any(t in remover_acentos(col) for t in termos_dinheiro):
                    df_display_geral[col] = df_display_geral[col].apply(formatar_moeda)
        st.dataframe(df_display_geral, hide_index=True, use_container_width=True)
    except:
        st.dataframe(df_display_geral, hide_index=True, use_container_width=True)
