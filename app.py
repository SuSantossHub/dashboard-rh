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
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_png_as_page_bg(png_file):
    try:
        bin_str = get_base64_of_bin_file(png_file)
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
        .badge-wyden { background-color: #cc0000; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
        .badge-ep { background-color: #0044cc; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
        .badge-staage { background-color: #ff9900; color: black; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
        
        /* Ajuste de tabelas */
        .dataframe { font-size: 14px !important; }
        </style>
        ''' % bin_str
        st.markdown(page_bg_img, unsafe_allow_html=True)
    except:
        pass

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
    # Se não tiver GID, retorna None para evitar erro de conexão
    if not gid:
        return None
        
    SHEET_ID = "10lEeyQAAOaHqpUTOfdMzaHgjfBpuNIHeCRabsv43WTQ"
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
    except:
        return None

    termos_financeiros = ["custo", "valor", "total", "orçado", "realizado", "budget", "soma", "sum", "mensalidade", "coparticipacao"]
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

def padronizar_colunas(df, nome_beneficio):
    if df is None or df.empty:
        return None # Retorna None para facilitar o filtro depois
    
    col_inv = achar_coluna(df, ["investidor", "dono", "sócio", "nome"])
    col_uni = achar_coluna(df, ["unidade", "franquia", "loja", "polo"])
    col_reg = achar_coluna(df, ["regional", "região", "estado", "uf"])
    col_cus = achar_coluna(df, ["valor", "custo", "preço", "mensalidade", "total"])
    
    if not col_inv: col_inv = "Investidor_Desc"
    if not col_uni: col_uni = "Unidade_Desc"
    
    df = df.rename(columns={
        col_inv: 'Investidor',
        col_uni: 'Unidade',
        col_reg: 'Regional',
        col_cus: 'Custo'
    })
    
    if 'Regional' not in df.columns: df['Regional'] = 'N/D'
    if 'Unidade' not in df.columns: df['Unidade'] = 'N/D'
    if 'Custo' not in df.columns: df['Custo'] = 0.0
    
    df['Benefício'] = nome_beneficio
    
    cols_finais = ['Investidor', 'Unidade', 'Regional', 'Custo', 'Benefício']
    cols_extras = [c for c in df.columns if c not in cols_finais]
    
    return df[cols_finais + cols_extras]

# ==============================================================================
# 🔒 SISTEMA DE LOGIN
# ==============================================================================
def check_password():
    CREDENCIAIS = {
        "Admin Opers": "BenefitsV4Company",  
        "diretoria": "V4Diretoria2026"       
    }

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

    if st.session_state.get("password_correct", False):
        return True

    if os.path.exists("capa_login.jpg.jpg"):
        set_png_as_page_bg("capa_login.jpg.jpg")
    elif os.path.exists("capa_login.jpg"):
        set_png_as_page_bg("capa_login.jpg")

    col_esq, col_centro, col_dir = st.columns([1, 2, 1])
    with col_centro:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container():
            st.markdown("""
                <div class="login-box">
                    <h1>🔒 Acesso Restrito</h1>
                    <h3>Diretoria & Benefits Operations</h3>
                    <p>Entre com as credenciais corporativas V4.</p>
                </div>
            """, unsafe_allow_html=True)

            st.text_input("Usuário", key="username")
            st.text_input("Senha", type="password", key="password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("Entrar no Painel", on_click=password_entered, type="primary", use_container_width=True)

            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("🚫 Usuário ou senha incorretos.")
        st.markdown("<br><br>", unsafe_allow_html=True)
            
    return False

if not check_password():
    st.stop()

# ==============================================================================
# FUNÇÃO DE RENDERIZAÇÃO ORÇAMENTO
# ==============================================================================
def renderizar_aba_orcamento(ano, gid_atual):
    df = load_data(gid_atual)
    
    if df is not None:
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
        c3.metric("Realizado YTD", formatar_moeda(realizado))
        c4.metric("Saldo Anual", formatar_moeda(saldo_diferenca), delta=f"{perc_uso*100:.1f}% consumido", delta_color=cor_percentual)
        
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
                
                df_m = df_c.melt(id_vars=['Mes_Clean', 'ordem'], value_vars=vars_p, var_name="Tipo", value_name="Valor")
                cores = {col_real: '#CC0000'}
                if col_orc: cores[col_orc] = '#D3D3D3'
                
                fig = px.bar(df_m, x="Mes_Clean", y="Valor", color="Tipo", barmode="group", text_auto='.2s', color_discrete_map=cores)
                fig.add_scatter(x=df_c['Mes_Clean'], y=df_c[col_real], mode='lines+markers', name='Tendência', line=dict(color='#ffffff', width=2.5, shape='spline'), marker=dict(size=8, color='#ffffff', line=dict(width=1, color='#000000')), showlegend=False)
                fig.update_layout(template="plotly_white", yaxis_tickprefix="R$ ", xaxis_title="", xaxis={'categoryorder':'array', 'categoryarray': df_c['Mes_Clean'].unique()})
                st.plotly_chart(fig, use_container_width=True)
        
        with g2:
            st.subheader("Distribuição Estratégica do Investimento")
            if col_ben and col_real:
                df_p = df_filt.groupby(col_ben)[col_real].sum().reset_index()
                total_real = df_p[col_real].sum()
                
                if total_real > 0:
                    df_p['Percentual'] = df_p[col_real] / total_real
                    df_principais = df_p[df_p['Percentual'] >= 0.03].copy()
                    df_menores = df_p[df_p['Percentual'] < 0.03]
                    
                    if not df_menores.empty:
                        df_outros = pd.DataFrame([{col_ben: 'Outros Benefícios', col_real: df_menores[col_real].sum(), 'Percentual': df_menores['Percentual'].sum()}])
                        df_final_p = pd.concat([df_principais, df_outros], ignore_index=True)
                    else:
                        df_final_p = df_principais
                        
                    df_final_p = df_final_p.sort_values(col_real, ascending=True)
                    valor_maximo = df_final_p[df_final_p[col_ben] != 'Outros Benefícios'][col_real].max()
                    
                    def cor_estrategica(linha):
                        if linha[col_ben] == 'Outros Benefícios': return '#808080' 
                        if linha[col_real] == valor_maximo: return '#990000' 
                        return '#ff4b4b' 
                        
                    df_final_p['Cor'] = df_final_p.apply(cor_estrategica, axis=1)
                    df_final_p['Texto_Exibicao'] = df_final_p.apply(lambda x: f"R$ {x[col_real]:,.0f}".replace(',','_').replace('.',',').replace('_','.') + f" ({x['Percentual']*100:.1f}%)", axis=1)
                    
                    fig_p = px.bar(df_final_p, y=col_ben, x=col_real, orientation='h', text='Texto_Exibicao')
                    fig_p.update_traces(marker_color=df_final_p['Cor'], textposition='inside', insidetextanchor='middle', textfont=dict(color='white', size=13))
                    fig_p.update_layout(template="plotly_white", xaxis_visible=False, yaxis_title="", margin=dict(l=0, r=0, t=10, b=0), height=400)
                    st.plotly_chart(fig_p, use_container_width=True)

        st.markdown("---")
        st.subheader("📑 Visão Matricial Detalhada")
        if col_ben and col_mes and col_real:
            try:
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
                sty = sty.apply(lambda s: ['background-color: #d3d3d3; color: black; font-weight: bold' if s.name == 'TOTAL GERAL' else '' for _ in s], axis=1)
                st.dataframe(sty, use_container_width=True)
            except:
                pass


# ==============================================================================
# 🚀 CONTROLE DE NAVEGAÇÃO
# ==============================================================================

usuario_atual = st.session_state.get("usuario_logado", "Visitante")
role = st.session_state.get("role", "viewer")

st.sidebar.success(f"👤 **{usuario_atual}**")
if role == "admin":
    st.sidebar.caption("🔧 Modo Admin Ativo")

st.sidebar.markdown("---")

GID_2026 = "1350897026"
GID_2025 = "1743422062"

# 🔴🔴🔴 INSIRA AQUI OS GIDs DAS 3 ABAS 🔴🔴🔴
GID_WYDEN = "1173982201" 
GID_EP = "587154330" 
GID_STAAGE = "1921348637"

OPCOES_MENU = [
    "Início",
    "Orçamento de Benefícios",
    "Análise Financeira",
    "Benefits Efficiency Map" 
]

st.sidebar.header("Navegação")
aba_selecionada = st.sidebar.radio("Escolha a Visão:", OPCOES_MENU, label_visibility="collapsed")

st.sidebar.markdown("<br><br><br><br><br>", unsafe_allow_html=True) 
if st.sidebar.button("Sair / Logout", use_container_width=True):
    st.session_state["password_correct"] = False
    st.rerun()

# ------------------------------------------------------------------------------
# LÓGICA DAS VISUALIZAÇÕES
# ------------------------------------------------------------------------------

# === PÁGINA INICIAL ===
if aba_selecionada == "Início":
    st.markdown("<br>", unsafe_allow_html=True)
    
    logo_html = ""
    if os.path.exists("favicon.png"):
        logo_b64 = get_base64_of_bin_file("favicon.png")
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height: 65px;">'

    st.markdown(f"""
        <div style="background-color: #1e1e1e; padding: 35px; border-radius: 12px; border-left: 6px solid #ff4b4b; box-shadow: 0 4px 10px rgba(0,0,0,0.4); margin-bottom: 30px;">
            <h1 class="home-title" style="color: white; margin-top: 0px;">
                {logo_html} Benefits Platform
            </h1>
            <h3 style="color: #ff4b4b; font-weight: 500; margin-top: 15px; margin-bottom: 10px;">
                Bem-vindos ao V4 Benefits Intelligence Platform.
            </h3>
            <p style="color: #cccccc; font-size: 16px; max-width: 900px; margin-bottom: 0px;">
                Plataforma estratégica para gestão e inteligência dos benefícios V4, reunindo orçamento, comparativos anuais e indicadores de performance em um único ambiente.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("Escolha uma opção no menu lateral para avançar.")

# === ORÇAMENTO ===
elif aba_selecionada == "Orçamento de Benefícios":
    st.header("🎯 Orçamento de Benefícios")
    st.markdown("<br>", unsafe_allow_html=True)
    tab_2026, tab_2025 = st.tabs(["📅 Visão 2026", "📅 Visão 2025"])
    with tab_2026: renderizar_aba_orcamento("2026", GID_2026)
    with tab_2025: renderizar_aba_orcamento("2025", GID_2025)

# === ANÁLISE FINANCEIRA ===
elif aba_selecionada == "Análise Financeira":
    st.header("⚖️ Análise Financeira (Mês a Mês)")
    st.caption("Selecione o mês abaixo para comparar o desempenho exato entre 2025 e 2026.")

    with st.spinner("Carregando dados..."):
        df_2025 = load_data(GID_2025)
        df_2026 = load_data(GID_2026)
    
    if df_2025 is not None and df_2026 is not None:
        col_real = achar_coluna(df_2025, ["realizado", "executado", "soma"])
        col_mes_25 = achar_coluna(df_2025, ["mês", "mes", "data"])
        col_mes_26 = achar_coluna(df_2026, ["mês", "mes", "data"])
        col_ben_25 = achar_coluna(df_2025, ["beneficio", "benefício"])
        col_ben_26 = achar_coluna(df_2026, ["beneficio", "benefício"])

        f1, f2 = st.columns(2)
        LISTA_MESES_EXTENSO = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
                       'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        mes_selecionado = f1.selectbox("📅 Selecione o Mês:", LISTA_MESES_EXTENSO, index=0)
        
        ordem_mes_selecionado = get_mes_ordem(mes_selecionado)
        df_25_m = df_2025[df_2025[col_mes_25].apply(get_mes_ordem) == ordem_mes_selecionado]
        df_26_m = df_2026[df_2026[col_mes_26].apply(get_mes_ordem) == ordem_mes_selecionado]

        bens_25 = df_25_m[col_ben_25].unique() if col_ben_25 else []
        bens_26 = df_26_m[col_ben_26].unique() if col_ben_26 else []
        todos_bens = sorted(list(set(bens_25) | set(bens_26)))
        
        sel_ben = f2.multiselect("🔍 Filtrar Benefícios (Opcional):", todos_bens)

        if sel_ben:
            df_25_final = df_25_m[df_25_m[col_ben_25].isin(sel_ben)]
            df_26_final = df_26_m[df_26_m[col_ben_26].isin(sel_ben)]
            titulo_grafico = f"Comparativo por Benefício - {mes_selecionado}"
        else:
            df_25_final = df_25_m
            df_26_final = df_26_m
            titulo_grafico = f"Top Benefícios - {mes_selecionado} (2025 vs 2026)"

        total_25 = df_25_final[col_real].sum()
        total_26 = df_26_final[col_real].sum()
        delta = total_26 - total_25
        delta_perc = (delta / total_25 * 100) if total_25 > 0 else 0

        st.markdown(f"### Resultados de **{mes_selecionado}**")
        k1, k2, k3 = st.columns(3)
        k1.metric("Realizado 2025", formatar_moeda(total_25))
        k2.metric("Realizado 2026", formatar_moeda(total_26))
        k3.metric("Diferença (R$)", formatar_moeda(delta), delta=f"{delta_perc:.1f}%", delta_color="inverse")

        st.markdown("---")
        
        view_25 = df_25_final.groupby(col_ben_25)[col_real].sum().reset_index()
        view_25.columns = ['Benefício', 'Valor']
        view_25['Ano'] = '2025'
        
        view_26 = df_26_final.groupby(col_ben_26)[col_real].sum().reset_index()
        view_26.columns = ['Benefício', 'Valor']
        view_26['Ano'] = '2026'
        
        df_chart = pd.concat([view_25, view_26])
        
        if not sel_ben and len(df_chart['Benefício'].unique()) > 10:
            top_bens = df_chart.groupby('Benefício')['Valor'].sum().nlargest(10).index
            df_chart = df_chart[df_chart['Benefício'].isin(top_bens)]
            st.caption("ℹ️ Mostrando os top 10 benefícios por valor. Use o filtro opcional para ver outros.")

        df_chart = df_chart.sort_values('Valor', ascending=False)
        fig = px.bar(df_chart, x="Benefício", y="Valor", color="Ano", barmode="group", text_auto='.2s', color_discrete_map={'2025': '#999999', '2026': '#CC0000'}, height=500)
        fig.update_layout(template="plotly_white", yaxis_tickprefix="R$ ", xaxis_title=None, yaxis_title="Custo Realizado", legend_title="Ano", title=titulo_grafico)
        st.plotly_chart(fig, use_container_width=True)

# === NOVA TELA: BENEFITS EFFICIENCY MAP (COM DADOS REAIS WYDEN/EP/STAAGE) ===
elif aba_selecionada == "Benefits Efficiency Map":
    st.header("🗺️ Benefits Efficiency Map")
    st.caption("Visão estratégica de escala, custo e eficiência por unidade e investidor da rede.")

    # Carrega dados reais das 3 abas e padroniza
    df_wyden = padronizar_colunas(load_data(GID_WYDEN), "Wyden") if GID_WYDEN else None
    df_ep = padronizar_colunas(load_data(GID_EP), "English Pass") if GID_EP else None
    df_staage = padronizar_colunas(load_data(GID_STAAGE), "Staage") if GID_STAAGE else None
    
    # LISTA SEGURA PARA CONCATENAR (EVITA O ERRO VALUEERROR)
    dfs_para_juntar = [df for df in [df_wyden, df_ep, df_staage] if df is not None]
    
    if dfs_para_juntar:
        df_unificado = pd.concat(dfs_para_juntar, ignore_index=True)
    else:
        df_unificado = pd.DataFrame() # Vazio se não tiver dados

    # SE NÃO TIVER DADOS, USA O MOCK BONITO
    if df_unificado.empty:
        if not GID_WYDEN and not GID_EP and not GID_STAAGE:
            st.info("ℹ️ Exibindo dados simulados. Insira os GIDs de 'Wyden', 'EP' e 'Staage' no código para ver dados reais.")
        
        # MOCK DATA PREMIUM (Simulação)
        mock_data = {
            "Investidor": ["V4 Paulista"]*3 + ["V4 Rio"]*3 + ["V4 BH"]*2 + ["V4 Sul"]*2 + ["V4 Norte"]*2,
            "Unidade": ["Paulista Matriz"]*3 + ["Rio Copacabana"]*3 + ["BH Savassi"]*2 + ["Sul Gramado"]*2 + ["Norte Manaus"]*2,
            "Regional": ["SP Capital"]*3 + ["RJ Capital"]*3 + ["MG Capital"]*2 + ["RS Serra"]*2 + ["AM Capital"]*2,
            "Benefício": ["Wyden", "English Pass", "Staage", "Wyden", "English Pass", "Staage", "Wyden", "Staage", "Wyden", "English Pass", "Wyden", "Staage"],
            "Custo": [15000, 3000, 1500, 10000, 2000, 500, 15000, 3000, 2500, 500, 8000, 1000],
            "Vidas_Mock": [45, 10, 5, 20, 5, 2, 35, 10, 10, 2, 15, 5]
        }
        df_unificado = pd.DataFrame(mock_data)
        df_unificado = df_unificado.loc[df_unificado.index.repeat(df_unificado['Vidas_Mock'])].reset_index(drop=True)
        df_unificado['Custo'] = df_unificado['Custo'] / df_unificado['Vidas_Mock']

    # 1. FILTROS EM CASCATA
    st.markdown("##### 🔍 Filtros Estratégicos")
    f1, f2, f3 = st.columns(3)
    
    regionais = sorted(df_unificado['Regional'].astype(str).unique())
    sel_reg = f1.multiselect("1. Regional:", regionais)
    if sel_reg: df_unificado = df_unificado[df_unificado['Regional'].isin(sel_reg)]
    
    unidades = sorted(df_unificado['Unidade'].astype(str).unique())
    sel_uni = f2.multiselect("2. Unidade:", unidades)
    if sel_uni: df_unificado = df_unificado[df_unificado['Unidade'].isin(sel_uni)]
    
    investidores = sorted(df_unificado['Investidor'].astype(str).unique())
    sel_inv = f3.multiselect("3. Investidor:", investidores)
    if sel_inv: df_unificado = df_unificado[df_unificado['Investidor'].isin(sel_inv)]

    st.markdown("---")

    # 2. AGREGAÇÃO DE DADOS (KPIs)
    df_agg = df_unificado.groupby(['Unidade', 'Investidor', 'Regional']).agg(
        Vidas=('Custo', 'count'),
        Custo_Total=('Custo', 'sum'),
        Beneficios_Ativos=('Benefício', lambda x: list(set(x)))
    ).reset_index()
    
    df_agg['Per Capita'] = df_agg['Custo_Total'] / df_agg['Vidas']
    
    media_pc = df_agg['Per Capita'].mean()
    std_pc = df_agg['Per Capita'].std() if len(df_agg) > 1 else 0
    maior_pc = df_agg['Per Capita'].max()
    menor_pc = df_agg['Per Capita'].min()
    total_vidas = df_agg['Vidas'].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Per Capita Médio", formatar_moeda(media_pc))
    c2.metric("Maior Per Capita 🔴", formatar_moeda(maior_pc))
    c3.metric("Menor Per Capita 🟢", formatar_moeda(menor_pc))
    c4.metric("Vidas Filtradas 👥", int(total_vidas))

    def classificar(val):
        if val > media_pc + std_pc: return '🔴 Alto'
        elif val < media_pc - std_pc: return '🟢 Eficiente'
        return '🟡 Na Média'
    
    df_agg['Status'] = df_agg['Per Capita'].apply(classificar)

    col_grafico, col_ranking = st.columns([6, 4])
    
    with col_grafico:
        st.markdown("##### 🎯 Escala vs. Eficiência (Por Unidade)")
        fig_scatter = px.scatter(
            df_agg, x='Vidas', y='Per Capita', size='Custo_Total', color='Status',
            hover_name='Unidade', hover_data=['Investidor', 'Regional'], size_max=40,
            color_discrete_map={'🔴 Alto': '#cc0000', '🟡 Na Média': '#ff4b4b', '🟢 Eficiente': '#2e7d32'}
        )
        fig_scatter.add_hline(y=media_pc, line_dash="dot", line_color="#ffffff", annotation_text="Média")
        fig_scatter.update_layout(template="plotly_white", height=450, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_scatter, use_container_width=True)

    with col_ranking:
        st.markdown("##### 🏆 Ranking de Custo (Unidades)")
        df_ranking = df_agg[['Unidade', 'Vidas', 'Custo_Total', 'Per Capita']].sort_values(by='Per Capita', ascending=False).head(10)
        st.dataframe(df_ranking.style.format({'Custo_Total': 'R$ {:,.2f}', 'Per Capita': 'R$ {:,.2f}'}).background_gradient(cmap='Reds', subset=['Per Capita']), hide_index=True, use_container_width=True, height=450)

    st.markdown("---")
    st.markdown("##### 🔍 Raio-X Detalhado (Por Unidade)")
    
    lista_unidades_dd = sorted(df_agg['Unidade'].unique())
    uni_sel = st.selectbox("Selecione a Unidade para investigar:", ["Selecione..."] + lista_unidades_dd)

    if uni_sel != "Selecione...":
        df_detalhe = df_unificado[df_unificado['Unidade'] == uni_sel]
        dados_resumo = df_agg[df_agg['Unidade'] == uni_sel].iloc[0]
        
        st.markdown(f"#### Detalhes: **{uni_sel}** ({dados_resumo['Investidor']})")
        
        r1, r2, r3 = st.columns(3)
        r1.metric("Investimento Total", formatar_moeda(dados_resumo['Custo_Total']))
        r2.metric("Per Capita da Unidade", formatar_moeda(dados_resumo['Per Capita']))
        r3.metric("Vidas Ativas", int(dados_resumo['Vidas']))
        
        tags = ""
        for ben in dados_resumo['Beneficios_Ativos']:
            cor_class = "badge-wyden" if "Wyden" in ben else "badge-ep" if "English" in ben else "badge-staage"
            tags += f"<span class='{cor_class}'>{ben}</span> "
        st.markdown(f"**Benefícios Ativos:** {tags}", unsafe_allow_html=True)
        
        df_bar = df_detalhe.groupby('Benefício')['Custo'].sum().reset_index().sort_values('Custo')
        df_bar['Texto'] = df_bar['Custo'].apply(lambda x: formatar_moeda(x))
        
        fig_bar = px.bar(df_bar, y='Benefício', x='Custo', orientation='h', text='Texto', title="Composição do Custo por Benefício")
        fig_bar.update_traces(marker_color='#ff4b4b', textposition='inside', insidetextanchor='middle', textfont=dict(color='white'))
        fig_bar.update_layout(template="plotly_white", height=250, xaxis_visible=False, yaxis_title="")
        st.plotly_chart(fig_bar, use_container_width=True)
