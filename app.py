import streamlit as st
import pandas as pd
import plotly.express as px
import unicodedata
import os
import base64

# ==============================================================================
# 1. Configuração da Página (OTIMIZADO)
# ==============================================================================
st.set_page_config(
    page_title="Dashboard de Benefícios | V4 Company", 
    layout="wide",
    page_icon="favicon.png", # Mantém o ícone na aba do navegador (profissional)
    initial_sidebar_state="expanded"
)

# ==============================================================================
# FUNÇÕES AUXILIARES (VISUAL & DADOS)
# ==============================================================================
def get_base64_of_bin_file(bin_file):
    """Converte arquivo em texto para o HTML conseguir ler."""
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_png_as_page_bg(png_file):
    """Define a imagem de fundo."""
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
        /* Estilo da Caixa de Login */
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
        
        /* Esconde botão de deploy e menu hamburguer para diretoria se necessário */
        /* #MainMenu {visibility: hidden;} */
        /* footer {visibility: hidden;} */
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

# MAPAS DE TEMPO
MAPA_MESES = {'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
              'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12}

def get_mes_ordem(nome_mes):
    return MAPA_MESES.get(str(nome_mes).lower()[:3], 99)

def get_trimestre(nome_mes):
    ordem = get_mes_ordem(nome_mes)
    if 1 <= ordem <= 3: return "Q1 (Jan-Mar)"
    elif 4 <= ordem <= 6: return "Q2 (Abr-Jun)"
    elif 7 <= ordem <= 9: return "Q3 (Jul-Set)"
    elif 10 <= ordem <= 12: return "Q4 (Out-Dez)"
    return "Outros"

def achar_coluna(df, termos):
    colunas_normalizadas = {col: remover_acentos(col) for col in df.columns}
    for termo in termos:
        termo_limpo = remover_acentos(termo)
        for col_original, col_limpa in colunas_normalizadas.items():
            if termo_limpo in col_limpa:
                return col_original
    return None

@st.cache_data
def load_data(gid):
    SHEET_ID = "10lEeyQAAOaHqpUTOfdMzaHgjfBpuNIHeCRabsv43WTQ"
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
    except:
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

# ==============================================================================
# 🔒 SISTEMA DE LOGIN (MULTI-USUÁRIO)
# ==============================================================================
def check_password():
    # Definição dos Usuários e Senhas
    CREDENCIAIS = {
        "Admin Opers": "BenefitsV4Company",  # Acesso Total
        "diretoria": "V4Diretoria2026"       # Acesso Visualização
    }

    def password_entered():
        user = st.session_state.get("username", "")
        pwd = st.session_state.get("password", "")

        if user in CREDENCIAIS and pwd == CREDENCIAIS[user]:
            st.session_state["password_correct"] = True
            st.session_state["usuario_logado"] = user
            # Define o perfil (Role)
            st.session_state["role"] = "admin" if user == "Admin Opers" else "viewer"
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    # 1. Carrega Background
    if os.path.exists("capa_login.jpg.jpg"):
        set_png_as_page_bg("capa_login.jpg.jpg")
    elif os.path.exists("capa_login.jpg"):
        set_png_as_page_bg("capa_login.jpg")

    # 2. Layout Centralizado (SEM LOGO, APENAS TEXTO ATUALIZADO)
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
# 🚀 ÁREA LOGADA
# ==============================================================================

usuario_atual = st.session_state.get("usuario_logado", "Visitante")
role = st.session_state.get("role", "viewer")

# Barra Lateral Personalizada
st.sidebar.success(f"👤 **{usuario_atual}**")

# Se for admin, mostra opção de ajuste (simulado aqui como visualização crua)
if role == "admin":
    st.sidebar.caption("🔧 Modo Admin Ativo")

if st.sidebar.button("Sair / Logout"):
    st.session_state["password_correct"] = False
    st.rerun()

st.sidebar.markdown("---")

GID_2026 = "1350897026"
GID_2025 = "1743422062"
GID_DASH_2025 = "2124043219"

OPCOES_MENU = [
    "Orçamento x Realizado | 2026",
    "Orçamento x Realizado | 2025",
    "Comparativo: 2025 vs 2026 (De/Para)",
    "Dashboard Trimestral"
]

st.sidebar.header("Navegação")
aba_selecionada = st.sidebar.selectbox("Escolha a Visão:", OPCOES_MENU)

# ------------------------------------------------------------------------------
# LÓGICA DAS VISUALIZAÇÕES
# ------------------------------------------------------------------------------

if "Trimestral" in aba_selecionada:
    st.header("📊 Dashboard Executivo e Trimestral")
    df = load_data(GID_DASH_2025)
    if df is None: df = load_data(GID_2025)

    if df is not None:
        col_real = achar_coluna(df, ["realizado", "executado", "soma"])
        col_mes = achar_coluna(df, ["mês", "mes", "data"])
        col_ben = achar_coluna(df, ["beneficio", "benefício"])

        if col_mes and col_real:
            df['Trimestre'] = df[col_mes].apply(get_trimestre)
            tris = sorted(df['Trimestre'].unique())
            
            # Filtros bem visíveis para Diretoria
            st.sidebar.markdown("### 🔍 Filtros Inteligentes")
            sel_t = st.sidebar.multiselect("Filtrar Trimestre:", tris)
            
            df_d = df[df['Trimestre'].isin(sel_t)] if sel_t else df.copy()

            # KPIs de Cabeçalho (Para visualização rápida da Diretoria)
            total_periodo = df_d[col_real].sum()
            k1, k2 = st.columns(2)
            k1.metric("Total Selecionado", formatar_moeda(total_periodo))
            if sel_t:
                k2.info(f"Visualizando: {', '.join(sel_t)}")

            st.markdown("---")

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Total por Benefício")
                if col_ben:
                    df_ben = df_d.groupby(col_ben)[col_real].sum().reset_index()
                    df_ben = df_ben.sort_values(col_real, ascending=False)
                    fig1 = px.bar(df_ben, x=col_ben, y=col_real, text_auto='.2s', color_discrete_sequence=['#636EFA'])
                    fig1.update_layout(template="plotly_white", yaxis_tickprefix="R$ ")
                    st.plotly_chart(fig1, use_container_width=True)

            with c2:
                st.subheader("Share por Trimestre")
                df_tri = df_d.groupby('Trimestre')[col_real].sum().reset_index()
                fig2 = px.pie(df_tri, values=col_real, names='Trimestre', hole=0.6, color_discrete_sequence=px.colors.sequential.RdBu)
                fig2.update_traces(textinfo='percent+label')
                st.plotly_chart(fig2, use_container_width=True)

            st.markdown("---")
            st.subheader("Evolução Detalhada (Mensal)")
            if col_ben:
                df_evo = df_d.groupby([col_mes, col_ben])[col_real].sum().reset_index()
                df_evo['ordem'] = df_evo[col_mes].apply(get_mes_ordem)
                df_evo = df_evo.sort_values('ordem')
                fig3 = px.bar(df_evo, x=col_mes, y=col_real, color=col_ben, barmode='group', text_auto='.2s')
                fig3.update_layout(template="plotly_white", yaxis_tickprefix="R$ ", xaxis={'categoryorder':'array', 'categoryarray': df_evo[col_mes].unique()})
                st.plotly_chart(fig3, use_container_width=True)
        else:
            if role == "admin":
                st.error("Admin: Colunas 'Mês' ou 'Realizado' não encontradas. Verifique a planilha.")
            else:
                st.warning("Dados indisponíveis no momento.")

elif "Comparativo" in aba_selecionada:
    st.header("⚖️ Comparativo Anual: 2025 vs 2026")
    with st.spinner("Carregando dados..."):
        df_2025 = load_data(GID_2025)
        df_2026 = load_data(GID_2026)
    
    if df_2025 is not None and df_2026 is not None:
        col_real = achar_coluna(df_2025, ["realizado", "executado", "soma"])
        col_mes_25 = achar_coluna(df_2025, ["mês", "mes", "data"])
        col_mes_26 = achar_coluna(df_2026, ["mês", "mes", "data"])

        total_25 = df_2025[col_real].sum()
        total_26 = df_2026[col_real].sum()
        delta = total_26 - total_25
        delta_perc = (delta / total_25 * 100) if total_25 > 0 else 0

        # KPIs Grandes para a Diretoria
        st.markdown("### Resumo Executivo")
        k1, k2, k3 = st.columns(3)
        k1.metric("Total 2025", formatar_moeda(total_25))
        k2.metric("Total 2026", formatar_moeda(total_26))
        k3.metric("Variação (YoY)", formatar_moeda(delta), delta=f"{delta_perc:.1f}%", delta_color="inverse")

        st.markdown("---")
        df_c25 = df_2025.groupby(col_mes_25)[col_real].sum().reset_index()
        df_c25.columns = ['Mês', 'Valor']; df_c25['Ano'] = '2025'
        df_c26 = df_2026.groupby(col_mes_26)[col_real].sum().reset_index()
        df_c26.columns = ['Mês', 'Valor']; df_c26['Ano'] = '2026'
        
        df_comb = pd.concat([df_c25, df_c26])
        df_comb['ordem'] = df_comb['Mês'].apply(get_mes_ordem)
        df_comb = df_comb.sort_values('ordem')
        fig = px.bar(df_comb, x="Mês", y="Valor", color="Ano", barmode="group", text_auto='.2s', color_discrete_map={'2025': '#D3D3D3', '2026': '#8B0000'})
        fig.update_layout(template="plotly_white", yaxis_tickprefix="R$ ")
        st.plotly_chart(fig, use_container_width=True)

elif "Orçamento" in aba_selecionada:
    gid_atual = GID_2026 if "2026" in aba_selecionada else GID_2025
    df = load_data(gid_atual)
    
    if df is not None:
        ano = "2026" if "2026" in aba_selecionada else "2025"
        st.header(f"🎯 Painel Executivo {ano}")
        
        col_orc = achar_coluna(df, ["orçado", "orcado", "budget"])
        col_real = achar_coluna(df, ["realizado", "executado", "soma"])
        col_ben = achar_coluna(df, ["beneficio", "benefício"])
        col_mes = achar_coluna(df, ["mês", "mes", "data"])

        st.sidebar.markdown("### 🔍 Filtros")
        df_filt = df.copy()
        if col_mes:
            meses = sorted(df[col_mes].astype(str).unique(), key=get_mes_ordem)
            sel_m = st.sidebar.multiselect("Mês:", meses, default=meses)
            if sel_m: df_filt = df_filt[df_filt[col_mes].isin(sel_m)]
        if col_ben:
            bens = sorted(df[col_ben].astype(str).unique())
            sel_b = st.sidebar.multiselect("Benefício:", bens, default=bens)
            if sel_b: df_filt = df_filt[df_filt[col_ben].isin(sel_b)]

        realizado = df_filt[col_real].sum() if col_real else 0
        BUDGET_ANUAL = 3432000.00
        saldo = BUDGET_ANUAL - realizado
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Budget Mensal", "R$ 286.000,00")
        c2.metric("Budget Anual", formatar_moeda(BUDGET_ANUAL))
        c3.metric("Realizado YTD", formatar_moeda(realizado))
        c4.metric("Saldo Anual", formatar_moeda(saldo), delta=formatar_moeda(saldo))
        
        st.markdown("---")
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("Evolução Mensal")
            if col_mes and col_real:
                vars_p = []
                if col_orc: vars_p.append(col_orc)
                vars_p.append(col_real)
                df_c = df_filt.groupby(col_mes)[vars_p].sum().reset_index()
                df_c['ordem'] = df_c[col_mes].apply(get_mes_ordem)
                df_c = df_c.sort_values('ordem')
                df_m = df_c.melt(id_vars=[col_mes], value_vars=vars_p, var_name="Tipo", value_name="Valor")
                cores = {col_real: '#8B0000'}; 
                if col_orc: cores[col_orc] = '#D3D3D3'
                fig = px.bar(df_m, x=col_mes, y="Valor", color="Tipo", barmode="group", text_auto='.2s', color_discrete_map=cores)
                fig.update_layout(template="plotly_white", yaxis_tickprefix="R$ ", xaxis={'categoryorder':'array', 'categoryarray': df_c[col_mes].unique()})
                st.plotly_chart(fig, use_container_width=True)
        
        with g2:
            st.subheader("Share por Benefício")
            if col_ben and col_real:
                df_p = df_filt.groupby(col_ben)[col_real].sum().reset_index()
                df_p = df_p.sort_values(col_real, ascending=False)
                fig_p = px.pie(df_p, values=col_real, names=col_ben, hole=0.5, color_discrete_sequence=px.colors.sequential.Reds_r)
                fig_p.update_traces(textposition='inside', textinfo='percent+label', textfont=dict(color='black'))
                fig_p.update_layout(showlegend=False)
                st.plotly_chart(fig_p, use_container_width=True)

        st.markdown("---")
        st.subheader("📑 Visão Matricial Detalhada")
        if col_ben and col_mes and col_real:
            try:
                piv = df_filt.pivot_table(index=col_ben, columns=col_mes, values=col_real, aggfunc='sum', fill_value=0)
                piv = piv[sorted(piv.columns, key=get_mes_ordem)]
                piv["Total Anual"] = piv.sum(axis=1)
                piv = piv.sort_values("Total Anual", ascending=False)
                lin_tot = piv.sum(); lin_tot.name = "TOTAL GERAL"
                piv = pd.concat([piv, lin_tot.to_frame().T])
                sty = piv.style.format("R$ {:,.2f}")
                cols = [c for c in piv.columns if c != "Total Anual"]
                sty = sty.background_gradient(cmap="Reds", subset=(piv.index[:-1], cols), vmin=0)
                sty = sty.applymap(lambda x: "background-color: #f0f2f6; color: black; font-weight: bold;", subset=["Total Anual"])
                def dest_total(s):
                    return ['background-color: #d3d3d3; color: black; font-weight: bold' if s.name == 'TOTAL GERAL' else '' for _ in s]
                sty = sty.apply(dest_total, axis=1)
                st.dataframe(sty, use_container_width=True)
            except: pass
