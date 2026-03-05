import streamlit as st
import pandas as pd
import plotly.express as px
import unicodedata
import os
import base64
import numpy as np

# ==============================================================================
# 1. Configuração da Página
# ==============================================================================
st.set_page_config(
    page_title="Dashboard de Benefícios | V4 Company", 
    layout="wide",
    page_icon="favicon.png",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return ""

def set_png_as_page_bg(png_file):
    bin_str = get_base64_of_bin_file(png_file)
    if bin_str:
        page_bg_img = '''
        <style>
        [data-testid="stAppViewContainer"] {
            background-image: url("data:image/jpg;base64,%s");
            background-size: cover;
            background-position: center center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }
        [data-testid="stSidebar"] {
            background-color: rgba(255, 255, 255, 0.95);
        }
        .login-box {
            background-color: rgba(0, 0, 0, 0.85);
            padding: 40px;
            border-radius: 15px;
            color: white;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.1);
        }
        .login-box h1 { font-size: 26px; color: white !important; margin-bottom: 10px; }
        .login-box h3 { font-size: 18px; color: #ff4b4b !important; margin-top: 0; font-weight: 500; margin-bottom: 20px; }
        .login-box p { font-size: 14px; color: #cccccc !important; }
        
        .stProgress > div > div > div > div { background-color: #ff4b4b; }
        .home-title {
            margin-bottom: 0px;
            display: flex;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap; 
        }
        button[data-baseweb="tab"] {
            font-size: 16px !important;
            font-weight: 600 !important;
        }
        .dataframe { font-size: 14px !important; }
        
        /* Estilos das Tags de Benefícios */
        .badge-base { padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; color: white; display: inline-block; margin-right: 5px; margin-bottom: 5px; }
        .bg-saude { background-color: #cc0000; }
        .bg-educacao { background-color: #0044cc; }
        .bg-outros { background-color: #ff9900; color: black !important; }
        </style>
        ''' % bin_str
        st.markdown(page_bg_img, unsafe_allow_html=True)

def formatar_moeda(valor):
    try:
        if pd.isna(valor): return "R$ 0,00"
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def remover_acentos(texto):
    try:
        nfkd = unicodedata.normalize('NFKD', str(texto))
        return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    except:
        return str(texto).lower()

def get_mes_ordem(nome_mes):
    MAPA_MESES = {'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
                  'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12}
    return MAPA_MESES.get(str(nome_mes).lower()[:3], 99)

def limpar_nome_mes(nome_sujo):
    try:
        return str(nome_sujo).split('.')[0].split('/')[0].capitalize()[:3]
    except:
        return str(nome_sujo)

def achar_coluna(df, termos):
    colunas_normalizadas = {col: remover_acentos(col) for col in df.columns}
    for termo in termos:
        termo_limpo = remover_acentos(termo)
        for col_original, col_limpa in colunas_normalizadas.items():
            if termo_limpo in col_limpa:
                return col_original
    return None

@st.cache_data(ttl=600)
def load_data(gid):
    if not gid: return None
    PUB_ID = "2PACX-1vRDOYmkYSNo7Ttbw0GM5YhDH3nYafq-Jg2o-fk1LaFOYjRw9oKQhwVe8YvBTdrmtOdzVsQdw-koM2oz"
    url = f"https://docs.google.com/spreadsheets/d/e/{PUB_ID}/pub?gid={gid}&single=true&output=csv"
    
    try:
        df = pd.read_csv(url)
        termos_financeiros = ["custo", "valor", "total", "orçado", "realizado", "budget", "soma", "sum", "mensalidade", "preço"]
        for col in df.columns:
            col_norm = remover_acentos(col)
            eh_financeiro = any(t in col_norm for t in termos_financeiros)
            
            primeiro_valor = df[col].dropna().iloc[0] if not df[col].dropna().empty else ""
            tem_cifrao = "R$" in str(primeiro_valor)
            
            if eh_financeiro or tem_cifrao:
                 if df[col].dtype == "object":
                    df[col] = df[col].astype(str).str.replace("R$", "", regex=False)
                    df[col] = df[col].str.replace(" ", "", regex=False)
                    df[col] = df[col].str.replace(".", "", regex=False) 
                    df[col] = df[col].str.replace(",", ".", regex=False) 
                 df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df
    except:
        return None

def padronizar_colunas(df, nome_beneficio):
    if df is None or df.empty: return None

    col_razao = achar_coluna(df, ["razão social", "razao social", "empresa", "cliente", "nome fantasia", "unidade", "franquia"])
    col_status = achar_coluna(df, ["status", "situacao"])
    col_plano = achar_coluna(df, ["plano", "produto"])
    col_tipo_usuario = achar_coluna(df, ["usuário", "usuario", "tipo"]) 
    col_nome = achar_coluna(df, ["nome", "beneficiario", "colaborador"])
    col_valor_titular = achar_coluna(df, ["valor titular", "custo titular"])
    col_valor_dep = achar_coluna(df, ["valor dependente", "custo dependente"])
    col_valor_unico = achar_coluna(df, ["valor", "custo", "preço", "mensalidade"])

    if not col_razao: return None 

    if col_status: df = df[df[col_status].astype(str).str.lower() == 'active'].copy()
    
    df['Custo_Calculado'] = 0.0
    if col_tipo_usuario and col_valor_titular and col_valor_dep:
        df['Custo_Calculado'] = np.where(df[col_tipo_usuario].astype(str).str.lower().str.contains('titular'), df[col_valor_titular], df[col_valor_dep])
    elif col_valor_unico:
        df['Custo_Calculado'] = df[col_valor_unico]
    df['Custo_Calculado'] = df['Custo_Calculado'].fillna(0)

    if col_plano: df['Benefício_Final'] = df[col_plano]
    else: df['Benefício_Final'] = nome_beneficio

    df = df.rename(columns={col_razao: 'Razão Social', col_nome: 'Nome', 'Benefício_Final': 'Benefício'})
    
    if 'Regional' not in df.columns:
        col_reg = achar_coluna(df, ["regional", "região", "estado"])
        df['Regional'] = df[col_reg] if col_reg else 'Geral'
        
    cols_uteis = ['Razão Social', 'Benefício', 'Custo_Calculado', 'Nome', 'Regional']
    if 'Nome' not in df.columns: df['Nome'] = 'Colaborador'
    return df[cols_uteis]

def processar_consultas(df):
    if df is None or df.empty: return None
    
    col_razao = achar_coluna(df, ["razão social", "razao social", "empresa"])
    col_status = achar_coluna(df, ["status consulta", "status"])
    col_especialidade = achar_coluna(df, ["especialidade", "tipo consulta"])
    col_data = achar_coluna(df, ["data consulta", "data"])
    
    if not col_razao: return None
    
    mapping = {col_razao: 'Razão Social'}
    if col_status: mapping[col_status] = 'Status_Consulta'
    if col_especialidade: mapping[col_especialidade] = 'Especialidade'
    if col_data: mapping[col_data] = 'Data'
    
    df = df.rename(columns=mapping)
    if 'Status_Consulta' not in df.columns: df['Status_Consulta'] = 'Realizada'
    if 'Especialidade' not in df.columns: df['Especialidade'] = 'Geral'
    
    return df[['Razão Social', 'Status_Consulta', 'Especialidade']]

# ==============================================================================
# 🔒 SISTEMA DE LOGIN
# ==============================================================================
def check_password():
    CREDENCIAIS = {"Admin Opers": "BenefitsV4Company", "diretoria": "V4Diretoria2026"}
    def password_entered():
        user = st.session_state.get("username", "")
        pwd = st.session_state.get("password", "")
        if user in CREDENCIAIS and pwd == CREDENCIAIS[user]:
            st.session_state["password_correct"] = True
            st.session_state["usuario_logado"] = user
            st.session_state["role"] = "admin" if user == "Admin Opers" else "viewer"
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False): return True
    if os.path.exists("capa_login.jpg.jpg"): set_png_as_page_bg("capa_login.jpg.jpg")
    elif os.path.exists("capa_login.jpg"): set_png_as_page_bg("capa_login.jpg")

    col_esq, col_centro, col_dir = st.columns([1, 2, 1])
    with col_centro:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container():
            st.markdown("""<div class="login-box"><h1>🔒 Acesso Restrito</h1><h3>Diretoria & Benefits Operations</h3><p>Entre com as credenciais corporativas V4.</p></div>""", unsafe_allow_html=True)
            st.text_input("Usuário", key="username")
            st.text_input("Senha", type="password", key="password")
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("Entrar no Painel", on_click=password_entered, type="primary", use_container_width=True)
            if "password_correct" in st.session_state and not st.session_state["password_correct"]: st.error("🚫 Usuário ou senha incorretos.")
        st.markdown("<br><br>", unsafe_allow_html=True)
    return False

if not check_password(): st.stop()

# ==============================================================================
# FUNÇÃO DE RECARREGAR PÁGINA (Tratamento de versão Streamlit)
# ==============================================================================
def recarregar_app():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# ==============================================================================
# NAVEGAÇÃO
# ==============================================================================
usuario_atual = st.session_state.get("usuario_logado", "Visitante")
role = st.session_state.get("role", "viewer")
st.sidebar.success(f"👤 **{usuario_atual}**")
if role == "admin": st.sidebar.caption("🔧 Modo Admin Ativo")
st.sidebar.markdown("---")

GID_2026 = "1350897026"
GID_2025 = "1743422062"

# 🔴 GIDS DA BASE DE DADOS
GID_BASE_COMPLETA = "1919747553" # Saúde
GID_WYDEN = "" 
GID_EP = "" 
GID_STAAGE = ""
GID_CONSULTAS = "" # Consultas

OPCOES_MENU = ["Início", "Orçamento de Benefícios", "Análise Financeira", "Benefits Efficiency Map"]
st.sidebar.header("Navegação")
aba_selecionada = st.sidebar.radio("Escolha a Visão:", OPCOES_MENU, label_visibility="collapsed")

st.sidebar.markdown("<br><br><br>", unsafe_allow_html=True) 

# --- BOTÃO DE ATUALIZAÇÃO BLINDADO ---
if st.sidebar.button("🔄 Atualizar Dados", use_container_width=True):
    st.cache_data.clear()
    recarregar_app()

# --- BOTÃO DE SAIR BLINDADO ---
if st.sidebar.button("Sair / Logout", use_container_width=True):
    st.session_state["password_correct"] = False
    recarregar_app()

# ==============================================================================
# LÓGICA DAS TELAS
# ==============================================================================

if aba_selecionada == "Início":
    st.markdown("<br>", unsafe_allow_html=True)
    logo_b64 = ""
    if os.path.exists("favicon.png"): logo_b64 = get_base64_of_bin_file("favicon.png")
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height: 65px;">' if logo_b64 else ""
    st.markdown(f"""
        <div style="background-color: #1e1e1e; padding: 35px; border-radius: 12px; border-left: 6px solid #ff4b4b; box-shadow: 0 4px 10px rgba(0,0,0,0.4); margin-bottom: 30px;">
            <h1 class="home-title" style="color: white; margin-top: 0px;">{logo_html} Benefits Platform</h1>
            <h3 style="color: #ff4b4b; font-weight: 500; margin-top: 15px; margin-bottom: 10px;">Bem-vindos ao V4 Benefits Intelligence Platform.</h3>
            <p style="color: #cccccc; font-size: 16px; max-width: 900px; margin-bottom: 0px;">Plataforma estratégica para gestão e inteligência dos benefícios V4.</p>
        </div>
    """, unsafe_allow_html=True)

    # GRÁFICO EXECUTIVO BLINDADO
    st.markdown("---")
    st.subheader("📈 Visão Executiva: Evolução do Custo Anual")
    st.caption("Acompanhamento da estabilização de custos de benefícios (Períodos 1 a 12).")
    
    dados_totais = {
        "Período": ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "P11", "P12"],
        "Custo": [261554.66, 267902.94, 272756.06, 281187.74, 283075.06, 282339.74, 286653.62, 288124.26, 288859.58, 290330.22, 290330.22, 290330.22]
    }
    df_trend = pd.DataFrame(dados_totais)
    total_ano = df_trend["Custo"].sum()
    media_mes = df_trend["Custo"].mean()
    crescimento = (df_trend["Custo"].iloc[-1] / df_trend["Custo"].iloc[0]) - 1

    col1, col2, col3 = st.columns(3)
    col1.metric("Custo Total Anual", f"R$ {total_ano/1000000:.2f} Milhões")
    col2.metric("Média por Período", f"R$ {media_mes/1000:.1f}k")
    col3.metric("Inflação da Carteira (P1 a P12)", f"+{crescimento*100:.1f}%", delta="Aumento estabilizado", delta_color="inverse")

    df_trend['Texto_Exibicao'] = df_trend['Custo'].apply(lambda x: f"R$ {x/1000:.0f}k")
    fig_executivo = px.bar(df_trend, x="Período", y="Custo", text='Texto_Exibicao')
    fig_executivo.add_scatter(x=df_trend['Período'], y=df_trend['Custo'], mode='lines+markers', name='Curva', line=dict(color='#cc0000', width=3), marker=dict(size=8, color='#cc0000'), showlegend=False)
    fig_executivo.update_traces(marker_color='#d3d3d3', textposition='outside')
    fig_executivo.update_layout(template="plotly_white", yaxis_visible=False, xaxis_title="", height=350, margin=dict(t=30, b=0, l=0, r=0))
    st.plotly_chart(fig_executivo, use_container_width=True)

elif aba_selecionada == "Orçamento de Benefícios":
    st.header("🎯 Orçamento de Benefícios")
    st.markdown("<br>", unsafe_allow_html=True)
    
    def renderizar_aba_orcamento(ano, gid_atual):
        try:
            df = load_data(gid_atual)
            if df is None or df.empty:
                st.warning(f"Os dados de {ano} não foram encontrados ou estão vazios.")
                return

            st.markdown("##### 🔍 Filtros de Visualização")
            f1, f2 = st.columns(2)
            df_filt = df.copy()
            col_mes = achar_coluna(df, ["mês", "mes", "data"])
            col_ben = achar_coluna(df, ["beneficio", "benefício"])
            col_real = achar_coluna(df, ["realizado", "executado", "soma"])
            col_orc = achar_coluna(df, ["orçado", "orcado", "budget"])

            if col_mes:
                meses = sorted(df[col_mes].astype(str).unique(), key=get_mes_ordem)
                sel_m = f1.multiselect("Filtrar por Mês:", meses, key=f"m_{ano}")
                if sel_m: df_filt = df_filt[df_filt[col_mes].isin(sel_m)]
            if col_ben:
                bens = sorted(df[col_ben].astype(str).unique())
                sel_b = f2.multiselect("Filtrar por Benefício:", bens, key=f"b_{ano}")
                if sel_b: df_filt = df_filt[df_filt[col_ben].isin(sel_b)]
            st.markdown("<br>", unsafe_allow_html=True)

            realizado = df_filt[col_real].sum() if col_real else 0
            BUDGET_ANUAL = 3432000.00
            saldo_diferenca = BUDGET_ANUAL - realizado
            perc_uso = realizado / BUDGET_ANUAL if BUDGET_ANUAL > 0 else 0
            cor_percentual = "normal" if perc_uso <= 1.0 else "inverse"
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Budget Mensal", "R$ 286.000,00")
            c2.metric("Budget Anual", formatar_moeda(BUDGET_ANUAL))
            c3.metric("Realizado YTD", formatar_moeda(realizado), delta=f"{perc_uso*100:.1f}% consumido", delta_color=cor_percentual)
            c4.metric("Saldo Anual", formatar_moeda(saldo_diferenca))
            
            st.markdown("---")
            g1, g2 = st.columns(2)
            with g1:
                st.subheader("Evolução Mensal")
                if col_mes and col_real:
                    vars_p = [col_real]
                    if col_orc: vars_p.insert(0, col_orc)
                    df_c = df_filt.groupby(col_mes)[vars_p].sum().reset_index()
                    df_c['ordem'] = df_c[col_mes].apply(get_mes_ordem)
                    df_c = df_c.sort_values('ordem')
                    df_c['Mes_Clean'] = df_c[col_mes].apply(limpar_nome_mes)
                    if not df_c.empty:
                        df_m = df_c.melt(id_vars=['Mes_Clean', 'ordem'], value_vars=vars_p, var_name="Tipo", value_name="Valor")
                        cores = {col_real: '#CC0000'}; 
                        if col_orc: cores[col_orc] = '#D3D3D3'
                        fig = px.bar(df_m, x="Mes_Clean", y="Valor", color="Tipo", barmode="group", text_auto='.2s', color_discrete_map=cores)
                        fig.add_scatter(x=df_c['Mes_Clean'], y=df_c[col_real], mode='lines+markers', name='Tendência', line=dict(color='#ffffff', width=2.5, shape='spline'), marker=dict(size=8, color='#ffffff', line=dict(width=1, color='#000000')), showlegend=False)
                        fig.update_layout(template="plotly_white", yaxis_tickprefix="R$ ", xaxis_title="", xaxis={'categoryorder':'array', 'categoryarray': df_c['Mes_Clean'].unique()})
                        st.plotly_chart(fig, use_container_width=True)
            with g2:
                st.subheader("Distribuição Estratégica")
                if col_ben and col_real:
                    df_p = df_filt.groupby(col_ben)[col_real].sum().reset_index()
                    total_real = df_p[col_real].sum()
                    if total_real > 0:
                        df_p['Percentual'] = df_p[col_real] / total_real
                        df_final_p = df_p.sort_values(col_real, ascending=True)
                        df_final_p['Cor'] = df_final_p.apply(lambda x: '#990000' if x[col_real] == df_final_p[col_real].max() else '#ff4b4b', axis=1)
                        df_final_p['Texto'] = df_final_p.apply(lambda x: f"R$ {x[col_real]:,.0f}".replace(',','_').replace('.',',').replace('_','.') + f" ({x['Percentual']*100:.1f}%)", axis=1)
                        fig_p = px.bar(df_final_p, y=col_ben, x=col_real, orientation='h', text='Texto')
                        fig_p.update_traces(marker_color=df_final_p['Cor'], textposition='inside', insidetextanchor='middle', textfont=dict(color='white', size=13))
                        fig_p.update_layout(template="plotly_white", xaxis_visible=False, yaxis_title="", margin=dict(l=0, r=0, t=10, b=0), height=400)
                        st.plotly_chart(fig_p, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📑 Visão Matricial Detalhada")
            if col_ben and col_mes and col_real and not df_filt.empty:
                piv = df_filt.pivot_table(index=col_ben, columns=col_mes, values=col_real, aggfunc='sum', fill_value=0)
                piv = piv[sorted(piv.columns, key=get_mes_ordem)]
                piv.columns = [limpar_nome_mes(c) for c in piv.columns]
                piv["Total Anual"] = piv.sum(axis=1)
                piv = piv.sort_values("Total Anual", ascending=False)
                lin_tot = piv.sum(); lin_tot.name = "TOTAL GERAL"
                piv = pd.concat([piv, lin_tot.to_frame().T])
                sty = piv.style.format("R$ {:,.2f}")
                cols = [c for c in piv.columns if c != "Total Anual"]
                sty = sty.background_gradient(cmap="Reds", subset=(piv.index[:-1], cols), vmin=0)
                sty = sty.applymap(lambda x: "background-color: #f0f2f6; color: black; font-weight: bold;", subset=["Total Anual"])
                st.dataframe(sty, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao renderizar a visão de orçamento. Verifique as colunas da planilha. Detalhe técnico: {e}")

    tab_2026, tab_2025 = st.tabs(["📅 Visão 2026", "📅 Visão 2025"])
    with tab_2026: renderizar_aba_orcamento("2026", GID_2026)
    with tab_2025: renderizar_aba_orcamento("2025", GID_2025)

elif aba_selecionada == "Análise Financeira":
    st.header("⚖️ Análise Financeira (Mês a Mês)")
    st.caption("Selecione o mês abaixo para comparar o desempenho exato entre 2025 e 2026.")
    try:
        with st.spinner("Carregando dados..."):
            df_2025 = load_data(GID_2025)
            df_2026 = load_data(GID_2026)
        
        if df_2025 is not None and df_2026 is not None:
            col_real_25 = achar_coluna(df_2025, ["realizado", "executado", "soma", "custo", "valor"])
            col_real_26 = achar_coluna(df_2026, ["realizado", "executado", "soma", "custo", "valor"])
            col_mes_25 = achar_coluna(df_2025, ["mês", "mes", "data"])
            col_mes_26 = achar_coluna(df_2026, ["mês", "mes", "data"])
            col_ben_25 = achar_coluna(df_2025, ["beneficio", "benefício"])
            col_ben_26 = achar_coluna(df_2026, ["beneficio", "benefício"])

            if all([col_real_25, col_real_26, col_mes_25, col_mes_26, col_ben_25, col_ben_26]):
                f1, f2 = st.columns(2)
                LISTA_MESES_EXTENSO = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
                mes_selecionado = f1.selectbox("📅 Selecione o Mês:", LISTA_MESES_EXTENSO, index=0)
                
                ordem_mes = get_mes_ordem(mes_selecionado)
                df_25_m = df_2025[df_2025[col_mes_25].apply(get_mes_ordem) == ordem_mes]
                df_26_m = df_2026[df_2026[col_mes_26].apply(get_mes_ordem) == ordem_mes]
                
                bens_25 = df_25_m[col_ben_25].unique().tolist() if not df_25_m.empty else []
                bens_26 = df_26_m[col_ben_26].unique().tolist() if not df_26_m.empty else []
                bens_total = sorted(list(set(bens_25) | set(bens_26)))
                
                sel_ben = f2.multiselect("🔍 Filtrar Benefícios (Opcional):", bens_total)
                
                if sel_ben:
                    df_25_final = df_25_m[df_25_m[col_ben_25].isin(sel_ben)]
                    df_26_final = df_26_m[df_26_m[col_ben_26].isin(sel_ben)]
                else:
                    df_25_final = df_25_m
                    df_26_final = df_26_m
                    
                total_25 = df_25_final[col_real_25].sum() if not df_25_final.empty else 0
                total_26 = df_26_final[col_real_26].sum() if not df_26_final.empty else 0
                delta = total_26 - total_25
                delta_perc = (delta / total_25 * 100) if total_25 > 0 else 0
                
                st.markdown(f"### Resultados de **{mes_selecionado}**")
                k1, k2, k3 = st.columns(3)
                k1.metric("Realizado 2025", formatar_moeda(total_25))
                k2.metric("Realizado 2026", formatar_moeda(total_26))
                k3.metric("Diferença (R$)", formatar_moeda(delta), delta=f"{delta_perc:.1f}%", delta_color="inverse")
                
                st.markdown("---")
                
                view_25 = df_25_final.groupby(col_ben_25)[col_real_25].sum().reset_index() if not df_25_final.empty else pd.DataFrame(columns=[col_ben_25, col_real_25])
                view_25.columns = ['Benefício', 'Valor']; view_25['Ano'] = '2025'
                
                view_26 = df_26_final.groupby(col_ben_26)[col_real_26].sum().reset_index() if not df_26_final.empty else pd.DataFrame(columns=[col_ben_26, col_real_26])
                view_26.columns = ['Benefício', 'Valor']; view_26['Ano'] = '2026'
                
                df_chart = pd.concat([view_25, view_26]).sort_values('Valor', ascending=False)
                if not df_chart.empty:
                    fig = px.bar(df_chart, x="Benefício", y="Valor", color="Ano", barmode="group", text_auto='.2s', color_discrete_map={'2025': '#999999', '2026': '#CC0000'}, height=500)
                    fig.update_layout(template="plotly_white", yaxis_tickprefix="R$ ", xaxis_title=None, yaxis_title="Custo Realizado")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(f"Sem dados financeiros lançados para o mês de {mes_selecionado}.")
            else:
                st.warning("⚠️ Algumas colunas não foram encontradas (Mês, Benefício ou Valor) na planilha. Verifique a aba original.")
        else:
            st.info("Carregando planilhas financeiras...")
    except Exception as e:
        st.error(f"Erro na Análise Financeira. Detalhe técnico: {e}")

elif aba_selecionada == "Benefits Efficiency Map":
    st.header("🗺️ Benefits Efficiency Map")
    st.caption("Visão estratégica de escala, custo e eficiência por Razão Social (Unificando Saúde e Educação).")

    try:
        df_saude = padronizar_colunas(load_data(GID_BASE_COMPLETA), "V4 - Starbem")
        df_wyden = padronizar_colunas(load_data(GID_WYDEN), "Wyden")
        df_ep = padronizar_colunas(load_data(GID_EP), "English Pass")
        df_staage = padronizar_colunas(load_data(GID_STAAGE), "Staage")

        dfs = [d for d in [df_saude, df_wyden, df_ep, df_staage] if d is not None]
        df_detalhado = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

        df_consultas_raw = load_data(GID_CONSULTAS)
        df_consultas = processar_consultas(df_consultas_raw)

        if df_detalhado.empty and df_consultas is None:
            st.info("ℹ️ Para ver a visão completa, insira os GIDs das abas no final do código.")
            mock_data = {
                "Razão Social": ["REGECOM MARKETING LTDA"]*5 + ["V4 COMPANY S.A."]*10,
                "Benefício": ["V4 - Starbem"]*5 + ["V4 - Starbem"]*10,
                "Custo_Calculado": [59.90]*15,
                "Nome": [f"Funcionario {i}" for i in range(15)],
                "Regional": ["Geral"]*15
            }
            df_detalhado = pd.DataFrame(mock_data)
            df_consultas = pd.DataFrame([{"Razão Social": "V4 COMPANY S.A.", "Status_Consulta": "Finalizado", "Especialidade": "Psicólogo"}]*20)

        st.markdown("##### 🩺 Filtros de Utilização (Consultas)")
        fc1, fc2 = st.columns(2)
        
        qtd_consultas_por_empresa = pd.DataFrame(columns=['Razão Social', 'Total_Consultas']) 
        
        if df_consultas is not None and not df_consultas.empty:
            status_opcoes = sorted(df_consultas['Status_Consulta'].dropna().unique())
            sel_status = fc1.multiselect("Status da Consulta:", status_opcoes, default=[s for s in status_opcoes if 'finalizado' in str(s).lower()])
            esp_opcoes = sorted(df_consultas['Especialidade'].dropna().unique())
            sel_esp = fc2.multiselect("Especialidade:", esp_opcoes)
            
            df_cons_filt = df_consultas.copy()
            if sel_status: df_cons_filt = df_cons_filt[df_cons_filt['Status_Consulta'].isin(sel_status)]
            if sel_esp: df_cons_filt = df_cons_filt[df_cons_filt['Especialidade'].isin(sel_esp)]
            
            qtd_consultas_por_empresa = df_cons_filt.groupby('Razão Social').size().reset_index(name='Total_Consultas')
        else:
            st.caption("Dados de consultas não disponíveis ou GID não configurado.")

        st.markdown("---")

        if not df_detalhado.empty:
            df_agg = df_detalhado.groupby(['Razão Social']).agg(
                Vidas=('Custo_Calculado', 'count'),
                Custo_Total=('Custo_Calculado', 'sum'),
                Lista_Beneficios=('Benefício', lambda x: list(set(x)))
            ).reset_index()
            
            df_agg = pd.merge(df_agg, qtd_consultas_por_empresa, on='Razão Social', how='left')
            df_agg['Total_Consultas'] = df_agg['Total_Consultas'].fillna(0).astype(int)
            df_agg['Per Capita'] = df_agg.apply(lambda x: x['Custo_Total'] / x['Vidas'] if x['Vidas'] > 0 else 0, axis=1)
            
            media_pc = df_agg['Per Capita'].mean()
            total_vidas = df_agg['Vidas'].sum()
            total_consultas_geral = df_agg['Total_Consultas'].sum()

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Per Capita Médio", formatar_moeda(media_pc))
            k2.metric("Vidas Ativas 👥", int(total_vidas))
            k3.metric("Consultas Filtradas 🩺", int(total_consultas_geral))
            
            utilizacao = (total_consultas_geral / total_vidas) if total_vidas > 0 else 0
            k4.metric("Média Consultas/Vida", f"{utilizacao:.2f}")

            std_pc = df_agg['Per Capita'].std() if len(df_agg) > 1 else 0
            def classificar(val):
                if val > media_pc + std_pc: return '🔴 Alto'
                elif val < media_pc - std_pc: return '🟢 Eficiente'
                return '🟡 Na Média'
            df_agg['Status'] = df_agg['Per Capita'].apply(classificar)

            col_grafico, col_ranking = st.columns([6, 4])
            with col_grafico:
                st.markdown("##### 🎯 Escala vs. Eficiência")
                fig_scatter = px.scatter(
                    df_agg, x='Vidas', y='Per Capita', size='Custo_Total', color='Status',
                    hover_name='Razão Social', hover_data=['Total_Consultas'], size_max=40,
                    color_discrete_map={'🔴 Alto': '#cc0000', '🟡 Na Média': '#ff4b4b', '🟢 Eficiente': '#2e7d32'}
                )
                fig_scatter.add_hline(y=media_pc, line_dash="dot", line_color="#ffffff", annotation_text="Média")
                fig_scatter.update_layout(template="plotly_white", height=450, margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig_scatter, use_container_width=True)

            with col_ranking:
                st.markdown("##### 🏆 Top Utilizadores (Consultas)")
                df_ranking = df_agg[['Razão Social', 'Vidas', 'Total_Consultas']].sort_values(by='Total_Consultas', ascending=False).head(10)
                st.dataframe(df_ranking.style.background_gradient(cmap='Reds', subset=['Total_Consultas']), hide_index=True, use_container_width=True, height=450)

            st.markdown("---")
            st.markdown("##### 🔍 Raio-X Detalhado (Por Razão Social)")
            
            lista_razao = sorted(df_agg['Razão Social'].unique())
            razao_sel = st.selectbox("Selecione a Razão Social para investigar:", ["Selecione..."] + lista_razao)

            if razao_sel != "Selecione...":
                df_filtrado = df_detalhado[df_detalhado['Razão Social'] == razao_sel]
                dados_resumo = df_agg[df_agg['Razão Social'] == razao_sel].iloc[0]
                
                st.markdown(f"#### Detalhes: **{razao_sel}**")
                
                html_tags = ""
                lista_bens = dados_resumo['Lista_Beneficios']
                if isinstance(lista_bens, list):
                    for ben in lista_bens:
                        classe_cor = "bg-outros"
                        nome_clean = str(ben).lower()
                        if "starbem" in nome_clean or "saúde" in nome_clean: classe_cor = "bg-saude"
                        elif "english" in nome_clean or "wyden" in nome_clean: classe_cor = "bg-educacao"
                        html_tags += f"<span class='badge-base {classe_cor}'>{ben}</span>"
                st.markdown(html_tags, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

                r1, r2, r3, r4 = st.columns(4)
                r1.metric("Custo Total", formatar_moeda(dados_resumo['Custo_Total']))
                r2.metric("Per Capita", formatar_moeda(dados_resumo['Per Capita']))
                r3.metric("Vidas Ativas", int(dados_resumo['Vidas']))
                r4.metric("Consultas Realizadas", int(dados_resumo['Total_Consultas']))
                
                col_d1, col_d2 = st.columns([1, 1])
                with col_d1:
                    st.markdown("**Composição do Custo:**")
                    df_bar = df_filtrado.groupby('Benefício')['Custo_Calculado'].sum().reset_index().sort_values('Custo_Calculado')
                    df_bar['Texto'] = df_bar['Custo_Calculado'].apply(lambda x: formatar_moeda(x))
                    fig_bar = px.bar(df_bar, y='Benefício', x='Custo_Calculado', orientation='h', text='Texto')
                    fig_bar.update_traces(marker_color='#ff4b4b', textposition='inside', insidetextanchor='middle', textfont=dict(color='white'))
                    fig_bar.update_layout(template="plotly_white", height=300, xaxis_visible=False, yaxis_title="")
                    st.plotly_chart(fig_bar, use_container_width=True)
                    
                with col_d2:
                    st.markdown("**Top Especialidades Consultadas:**")
                    if df_consultas is not None and not df_consultas.empty:
                        df_cons_empresa = df_consultas[df_consultas['Razão Social'] == razao_sel]
                        if not df_cons_empresa.empty:
                            top_esp = df_cons_empresa['Especialidade'].value_counts().reset_index()
                            top_esp.columns = ['Especialidade', 'Qtd']
                            fig_pie = px.pie(top_esp.head(5), values='Qtd', names='Especialidade', hole=0.4)
                            fig_pie.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
                            st.plotly_chart(fig_pie, use_container_width=True)
                        else:
                            st.info("Nenhuma consulta registrada para esta empresa.")
                    else:
                        st.caption("Dados de consultas indisponíveis.")
    except Exception as e:
        st.error(f"Erro ao processar o Mapa de Eficiência. Detalhe técnico: {e}")
