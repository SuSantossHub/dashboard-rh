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
        .dataframe { font-size: 14px !important; }
        
        /* Estilos das Tags de Benefícios */
        .badge-base { padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; color: white; display: inline-block; margin-right: 5px; margin-bottom: 5px; }
        .bg-saude { background-color: #cc0000; }
        .bg-educacao { background-color: #0044cc; }
        .bg-outros { background-color: #ff9900; color: black !important; }
        </style>
        ''' % bin_str
        st.markdown(page_bg_img, unsafe_allow_html=True)
    except:
        pass

def formatar_moeda(valor):
    try:
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
    except:
        return None

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
# RENDERIZAR ORÇAMENTO
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
        
        # MUDANÇA AQUI: O delta de % consumido agora está abaixo do Realizado YTD
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
        if col_ben and col_mes and col_real:
            try:
                piv = df_filt.pivot_table(index=col_ben, columns=col_mes, values=col_real, aggfunc='sum', fill_value=0)
                piv = piv[sorted(piv.columns, key=get_mes_ordem)]
