import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Os dados que você forneceu
dados_totais = {
    "Mês": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"],
    "Custo": [261554.66, 267902.94, 272756.06, 281187.74, 283075.06, 282339.74, 286653.62, 288124.26, 288859.58, 290330.22, 290330.22, 290330.22]
}
df_trend = pd.DataFrame(dados_totais)

# 2. Resumo Executivo (KPIs)
total_ano = df_trend["Custo"].sum()
crescimento = (df_trend["Custo"].iloc[-1] / df_trend["Custo"].iloc[0]) - 1

col1, col2 = st.columns(2)
col1.metric("Custo Total Anual", f"R$ {total_ano/1000000:.2f} Milhões")
col2.metric("Inflação da Carteira (Jan a Dez)", f"{crescimento*100:.1f}%", delta="Aumento de custo", delta_color="inverse")

# 3. Gráfico Elegante (Barra + Linha de Tendência)
st.markdown("##### Evolução do Custo Total ao longo do Ano")

# Arredondando para 'k' para ficar limpo
df_trend['Texto'] = df_trend['Custo'].apply(lambda x: f"R$ {x/1000:.0f}k")

fig = px.bar(
    df_trend, 
    x="Mês", 
    y="Custo", 
    text='Texto',
    title="Curva de estabilização nos meses finais"
)

# Adicionando a linha vermelha por cima das barras para mostrar a subida
fig.add_scatter(
    x=df_trend['Mês'], 
    y=df_trend['Custo'], 
    mode='lines+markers',
    line=dict(color='#cc0000', width=3),
    marker=dict(size=8),
    showlegend=False
)

fig.update_traces(marker_color='#d3d3d3', textposition='outside') # Barras cinzas, linha vermelha
fig.update_layout(template="plotly_white", yaxis_visible=False, xaxis_title="")

st.plotly_chart(fig, use_container_width=True)
