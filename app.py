import streamlit as st
import pandas as pd
import plotly.express as px
import unicodedata
import os
import base64

# 1. Configuração da Página (DEVE SER O PRIMEIRO COMANDO)
st.set_page_config(
    page_title="Dashboard RH Executivo",
    layout="wide",
    page_icon="favicon.png"
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
            background-color: rgba(0, 0, 0, 0.8);
            padding: 30px;
            border-radius: 15px;
            color: white;
            text-align: center;
        }
        .login-box h1, .login-box h3, .login-box p, .login-box label {
             color: white !important;
        }
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

# MAPA DE MESES PARA ORDENAÇÃO
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
    # ID DA PLANILHA (FIXO)
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
# 🔒 SISTEMA DE LOGIN SEGURO
# ==============================================================================
def check_password():
    """Retorna True se o usuário tiver a senha correta."""

    def password_entered():
        """Verifica se a senha digitada bate com a definida aqui."""
        USUARIO_CORRETO = "Benefits Opers"
        SENHA_CORRETA = "BenefitsV4Company"

        if st.session_state["username"] == USUARIO_CORRETO and \
           st.session_state["password"] == SENHA_CORRETA:
            st.session_state["password_correct"] = True
            # SALVA O NOME PARA EVITAR KEYERROR
            st.session_state["usuario_logado"] = st.session_state["username"]
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    # TELA DE LOGIN
    # Tenta carregar imagem com o nome duplo (.jpg.jpg) primeiro, depois o simples
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
                    <h3>Diretoria RH & Benefits Operations</h3>
                    <p>Entre com as credenciais corporativas V4 para visualizar os dados sensíveis.</p>
                </div>
            """, unsafe_allow_html=True)

            st.text_input("Usuário", key="username")
            st.text_input("Senha", type="password", key="password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("Entrar no Painel", on_click=password_entered, type="primary", use_container_width=True)

            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("🚫 Acesso negado. Verifique suas credenciais.")
        st.markdown("<br><br>", unsafe_allow_html=True)
            
    return False

if not check_password():
    st.stop()

# ==============================================================================
# 🚀 ÁREA LOGADA
# ==============================================================================

# Recupera o usuário de forma segura
usuario_atual = st.session_state.get("usuario_logado", "Diretoria")

st.sidebar.success(f"👤 Logado: **{usuario_atual}**")
if st.sidebar.button("Sair / Logout"):
    st.session_state["password_correct"] = False
    st.rerun()

st.sidebar.markdown("---")

# IDs DAS ABAS
GID_2026 = "1350897026"
GID_2025 = "1743422062"
GID_DASH_2025 = "2124043219" # ID da aba Dashboard - 2025

OPCOES_MENU = [
    "Orçamento x Realizado | 2026",
    "Orçamento x Realizado | 2025",
    "Comparativo: 2025 vs 2026 (De/Para)",
    "Dashboard Trimestral"
]

st.sidebar.header("Navegação")
aba_selecionada = st.sidebar.selectbox("Escolha a Visão:", OPCOES_MENU)

# ------------------------------------------------------------------------------
# LÓGICA DAS VISÕES
# ------------------------------------------------------------------------------

# === 1. VISÃO: DASHBOARD TRIMESTRAL (DADOS DA ABA DASHBOARD - 2025) ===
if "Trimestral" in aba_selecionada:
    st.header("📊 Dashboard Executivo e Trimestral")
    
    # Carrega dados da aba específica "Dashboard - 2025"
    df = load_data(GID_DASH_2025)
    
    # Se falhar, tenta a aba geral de 2025 como backup
    if df is None: df = load_data(GID_2025)

    if df is not None:
        col_real = achar_coluna(df, ["realizado", "executado", "soma"])
        col_mes = achar_coluna(df, ["mês", "mes", "data"])
        col_ben = achar_coluna(df, ["beneficio", "benefício"])

        if col_mes and col_real:
            # Cria Coluna de Trimestre
            df['Trimestre'] = df[col_mes].apply(get_trimestre)
            
            # Filtro Lateral
            st.sidebar.subheader("Filtros")
            tris = sorted(df['Trimestre'].unique())
            sel_t = st.sidebar.multiselect("Filtrar Trimestre:", tris)
            
            # Aplica Filtro
            df_d = df[df['Trimestre'].isin(sel_t)] if sel_t else df.copy()

            # --- LINHA 1: DOIS GRÁFICOS (BARRAS E ROSCA) ---
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("Total por Benefício")
                if col_ben:
                    df_ben = df_d.groupby(col_ben)[col_real].sum().reset_index()
                    df_ben = df_ben.sort_values(col_real, ascending=False)
                    # Gráfico de Barras Cinza/Escuro (Estilo Excel)
                    fig1 = px.bar(df_ben, x=col_ben, y=col_real, text_auto='.2s', 
                                  color_discrete_sequence=['#636EFA']) # Azul padrão ou cinza
                    fig1.update_layout(template="plotly_white", yaxis_tickprefix="R$ ")
                    st.plotly_chart(fig1, use_container_width=True)

            with c2:
                st.subheader("Custo por Trimestre")
                df_tri = df_d.groupby('Trimestre')[col_real].sum().reset_index()
                # Gráfico de Rosca (Donut)
                fig2 = px.pie(df_tri, values=col_real, names='Trimestre', hole=0.5,
                              color_discrete_sequence=px.colors.sequential.RdBu)
                fig2.update_traces(textinfo='percent+label')
                st.plotly_chart(fig2, use_container_width=True)

            # --- LINHA 2: GRÁFICO DE EVOLUÇÃO DETALHADA ---
            st.markdown("---")
            st.subheader("Evolução Mensal Detalhada (Por Benefício)")
            
            # Prepara dados para o gráfico agrupado
            if col_ben:
                df_evo = df_d.groupby([col_mes, col_ben])[col_real].sum().reset_index()
                
                # Ordena meses
                df_evo['ordem'] = df_evo[col_mes].apply(get_mes_ordem)
                df_evo = df_evo.sort_values('ordem')
                
                # Gráfico de Barras Agrupadas
                fig3 = px.bar(df_evo, x=col_mes, y=col_real, color=col_ben, barmode='group',
                              text_auto='.2s')
                fig3.update_layout(template="plotly_white", yaxis_tickprefix="R$ ", 
                                   xaxis={'categoryorder':'array', 'categoryarray': df_evo[col_mes].unique()})
                st.plotly_chart(fig3, use_container_width=True)

        else:
            st.warning("Não foi possível encontrar as colunas de 'Mês' ou 'Realizado' nesta planilha.")
    else:
        st.error("Erro ao carregar os dados da aba Dashboard - 2025.")


# === 2. VISÃO: COMPARATIVO 2025 vs 2026 ===
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

        k1, k2, k3 = st.columns(3)
        k1.metric("Total 2025", formatar_moeda(total_25))
        k2.metric("Total 2026", formatar_moeda(total_26))
        k3.metric("Variação", formatar_moeda(delta), delta=f"{delta_perc:.1f}%", delta_color="inverse")

        st.markdown("---")
        df_c25 = df_2025.groupby(col_mes_25)[col_real].sum().reset_index()
        df_c25.columns = ['Mês', 'Valor']; df_c25['Ano'] = '2025'
        df_c26 = df_2026.groupby(col_mes_26)[col_real].sum().reset_index()
        df_c26.columns = ['Mês', 'Valor']; df_c26['Ano'] = '2026'
        
        df_comb = pd.concat([df_c25, df_c26])
        df_comb['ordem'] = df_comb['Mês'].apply(get_mes_ordem)
        df_comb = df_comb.sort_values('ordem')
        
        fig = px.bar(df_comb, x="Mês", y="Valor", color="Ano", barmode="group",
                     text_auto='.2s', color_discrete_map={'2025': '#D3D3D3', '2026': '#8B0000'})
        fig.update_layout(template="plotly_white", yaxis_tickprefix="R$ ")
        st.plotly_chart(fig, use_container_width=True)

# === 3. VISÃO: ORÇAMENTO x REALIZADO ===
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

        # Filtros
        st.sidebar.subheader("Filtros")
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
                fig = px.bar(df_m, x=col_mes, y="Valor", color="Tipo", barmode="group", 
                             text_auto='.2s', color_discrete_map=cores)
                fig.update_layout(template="plotly_white", yaxis_tickprefix="R$ ",
                                  xaxis={'categoryorder':'array', 'categoryarray': df_c[col_mes].unique()})
                st.plotly_chart(fig, use_container_width=True)
        
        with g2:
            st.subheader("Share por Benefício")
            if col_ben and col_real:
                df_p = df_filt.groupby(col_ben)[col_real].sum().reset_index()
                df_p = df_p.sort_values(col_real, ascending=False)
                fig_p = px.pie(df_p, values=col_real, names=col_ben, hole=0.5,
                               color_discrete_sequence=px.colors.sequential.Reds_r)
                fig_p.update_traces(textposition='inside', textinfo='percent+label', textfont=dict(color='black'))
                fig_p.update_layout(showlegend=False)
                st.plotly_chart(fig_p, use_container_width=True)

        st.markdown("---")
        st.subheader("📑 Visão Matricial")
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
