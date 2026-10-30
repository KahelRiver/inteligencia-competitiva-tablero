import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. CONFIGURACIÓN DE LA PÁGINA WEB
st.set_page_config(page_title="Tablero Competitivo", layout="wide", initial_sidebar_state="expanded")
st.title("🏆 Inteligencia Competitiva: Top 5 + Proximidad BanCoppel")

# 2. CARGA DE DATOS
@st.cache_data
def cargar_datos():
    df_viv = pd.read_excel('Base_Maestra_Vivienda_2026_VF4.xlsx', sheet_name='Base_Maestra')
    
    try:
        # Lee directamente el CSV comprimido con el nombre exacto que está en GitHub
        df_rc = pd.read_csv('RC_ALL_Cruce_Demografico(VF4)_2026.csv.zip', compression='zip', low_memory=False)
                
        if 'Institucion' in df_rc.columns:
            df_rc.rename(columns={'Institucion': 'Institución'}, inplace=True)
        df_master = pd.concat([df_viv, df_rc], ignore_index=True)
    except FileNotFoundError:
        st.warning("No se encontró el archivo de Consumo. Mostrando solo Vivienda.")
        df_master = df_viv
        
    df_master['Periodo'] = df_master['Periodo'].astype(str)
    
    # PLANCHADO DE ESTADOS (Compactar mayúsculas y minúsculas)
    df_master['Estado'] = df_master['Estado'].fillna('DESCONOCIDO').astype(str).str.upper().str.strip()
    
    # FILTRADO GLOBAL DE SECTOR (ELIMINAR BANCA DE DESARROLLO)
    if 'Sector' in df_master.columns:
        sector_limpio = df_master['Sector'].astype(str).str.upper().str.strip()
        df_master = df_master[sector_limpio != 'BANCA DE DESARROLLO']
        
    bancos_desarrollo = [
        'BANOBRAS', 'SOCIEDAD HIPOTECARIA FEDERAL', 'NAFIN', 
        'BANCOMEXT', 'BANCO DEL BIENESTAR', 'BANJÉRCITO', 'BANJERCITO'
    ]
    inst_limpia = df_master['Institución'].astype(str).str.upper().str.strip()
    df_master = df_master[~inst_limpia.isin(bancos_desarrollo)]
    
    # FILTRADO Y MAYÚSCULAS DE CARTERAS CLAVE
    df_master['Tipo de Cartera'] = df_master['Tipo de Cartera'].fillna('DESCONOCIDO').astype(str).str.upper().str.strip()
    carteras_validas = ['HIPOTECARIO', 'AUTOMOTRIZ', 'NÓMINA', 'PERSONALES', 'TARJETAS DE CRÉDITO']
    df_master = df_master[df_master['Tipo de Cartera'].isin(carteras_validas)]
    
    return df_master

df_master = cargar_datos()

# 3. CONSTRUCCIÓN DE LA BARRA LATERAL
st.sidebar.header("🎛️ Filtros del Tablero")

nivel = st.sidebar.radio("Nivel Geográfico", ["Nacional", "Estatal"])

estado_seleccionado = None
if nivel == "Estatal":
    estados_disponibles = [est for est in df_master['Estado'].unique() if est != 'DESCONOCIDO']
    estado_seleccionado = st.sidebar.selectbox("Selecciona un Estado", sorted(estados_disponibles))

periodo_seleccionado = st.sidebar.selectbox("Periodo", sorted(df_master['Periodo'].unique(), reverse=True))
cartera_seleccionada = st.sidebar.selectbox("Tipo de Cartera (Producto)", sorted(df_master['Tipo de Cartera'].unique()))

metrica_seleccionada = st.sidebar.radio("Métrica a Evaluar", ["Saldo Total", "Número de Créditos", "IMOR"])
genero_seleccionado = st.sidebar.selectbox("Género", ["Total", "Hombres", "Mujeres"])

# 4. MOTOR INTELIGENTE ON-THE-FLY (Calcula Rankings e IMOR en vivo)
df_filtrado = df_master[(df_master['Periodo'] == periodo_seleccionado) & 
                        (df_master['Tipo de Cartera'] == cartera_seleccionada)]

if nivel == "Estatal":
    df_filtrado = df_filtrado[df_filtrado['Estado'] == estado_seleccionado]

df_plot = df_filtrado.copy()
df_agrupado = pd.DataFrame() 

if not df_plot.empty:
    
    # LÓGICA MATEMÁTICA EN TIEMPO REAL
    if metrica_seleccionada == "IMOR":
        if cartera_seleccionada == "HIPOTECARIO":
            if genero_seleccionado == "Hombres": df_plot = df_plot[df_plot['Género'] == 'Hombre']
            elif genero_seleccionado == "Mujeres": df_plot = df_plot[df_plot['Género'] == 'Mujer']
            
            df_plot['Saldo_Eval'] = df_plot['Saldo Total'].fillna(0)
            df_plot['CV_Eval'] = np.where(df_plot['Etapa de Deterioro'] == 3, df_plot['Saldo Total'], 0)
        else: # Consumo
            if genero_seleccionado == "Hombres":
                df_plot['Saldo_Eval'] = df_plot['Saldo Total H'].fillna(0)
                df_plot['CV_Eval'] = df_plot['Saldo Etapa 3 H'].fillna(0)
            elif genero_seleccionado == "Mujeres":
                df_plot['Saldo_Eval'] = df_plot['Saldo Total M'].fillna(0)
                df_plot['CV_Eval'] = df_plot['Saldo Etapa 3 M'].fillna(0)
            else:
                df_plot['Saldo_Eval'] = df_plot['Total de Saldo'].fillna(0)
                df_plot['CV_Eval'] = df_plot['Saldo Etapa 3'].fillna(0)

        df_agrupado = df_plot.groupby(['Institución', 'Grupo Bancario'])[['Saldo_Eval', 'CV_Eval']].sum().reset_index()
        df_agrupado = df_agrupado[df_agrupado['Saldo_Eval'] > 0] 
        
        df_agrupado['Valor_Grafica'] = (df_agrupado['CV_Eval'] / df_agrupado['Saldo_Eval']) * 100
        df_agrupado = df_agrupado[df_agrupado['Valor_Grafica'] > 0]
        
        df_agrupado = df_agrupado.sort_values(by=['Valor_Grafica', 'Institución'], ascending=[False, True]).reset_index(drop=True)
        df_agrupado['Rank_Final'] = np.arange(1, len(df_agrupado) + 1)

    else: # Saldo Total o Créditos
        if cartera_seleccionada == "HIPOTECARIO":
            if genero_seleccionado == "Hombres": df_plot = df_plot[df_plot['Género'] == 'Hombre']
            elif genero_seleccionado == "Mujeres": df_plot = df_plot[df_plot['Género'] == 'Mujer']
            
            df_plot['Valor_Grafica'] = df_plot[metrica_seleccionada].fillna(0)
        else: # Consumo
            if metrica_seleccionada == "Saldo Total":
                if genero_seleccionado == "Hombres": df_plot['Valor_Grafica'] = df_plot['Saldo Total H'].fillna(0)
                elif genero_seleccionado == "Mujeres": df_plot['Valor_Grafica'] = df_plot['Saldo Total M'].fillna(0)
                else: df_plot['Valor_Grafica'] = df_plot['Total de Saldo'].fillna(0)
            else: # Número de Créditos
                if genero_seleccionado == "Hombres": df_plot['Valor_Grafica'] = df_plot['Total Creditos H'].fillna(0)
                elif genero_seleccionado == "Mujeres": df_plot['Valor_Grafica'] = df_plot['Total Creditos M'].fillna(0)
                else: df_plot['Valor_Grafica'] = df_plot['Número de Créditos'].fillna(0)

        df_agrupado = df_plot.groupby(['Institución', 'Grupo Bancario'])['Valor_Grafica'].sum().reset_index()
        df_agrupado = df_agrupado[df_agrupado['Valor_Grafica'] > 0]
        
        df_agrupado['Rank_Final'] = df_agrupado['Valor_Grafica'].rank(ascending=False, method='min')

# 5. LÓGICA DE TOP 5 + PROXIMIDAD BANCOPPEL
if not df_agrupado.empty:

    bancoppel_data = df_agrupado[df_agrupado['Grupo Bancario'] == 'BanCoppel']

    if metrica_seleccionada == "IMOR":
        top_5 = df_agrupado.nsmallest(5, 'Rank_Final').copy()
        df_final = top_5.copy()

        if not bancoppel_data.empty:
            rank_bancoppel = int(bancoppel_data['Rank_Final'].iloc[0])
            
            if rank_bancoppel > 5:
                rango_bancoppel = df_agrupado[
                    (df_agrupado['Rank_Final'] >= rank_bancoppel - 2) &
                    (df_agrupado['Rank_Final'] <= rank_bancoppel + 2)
                ].copy()
                df_final = pd.concat([top_5, rango_bancoppel], ignore_index=True).drop_duplicates(subset=['Institución'])

        df_final = df_final.sort_values(by='Rank_Final', ascending=True).copy()
        df_final['Rank_Texto'] = df_final['Rank_Final'].astype(int).astype(str)

    else:
        top_5 = df_agrupado[df_agrupado['Rank_Final'] <= 5].copy()
        df_final = top_5.copy()

        if not bancoppel_data.empty:
            rank_bancoppel = bancoppel_data['Rank_Final'].iloc[0]
            rango_bancoppel = df_agrupado[
                (df_agrupado['Rank_Final'] >= rank_bancoppel - 2) &
                (df_agrupado['Rank_Final'] <= rank_bancoppel + 2)
            ].copy()
            df_final = pd.concat([top_5, rango_bancoppel]).drop_duplicates(subset=['Institución'])

        df_final = df_final.sort_values(by='Rank_Final', ascending=True).copy()
        df_final['Rank_Texto'] = df_final['Rank_Final'].astype(int).astype(str)

    # 6. CONSTRUCCIÓN DE LA GRÁFICA
    if not df_final.empty:
        colores_grupos = {
            'G7': '#808080',
            'BanCoppel': '#0033A0',
            'Resto del Mercado': '#90EE90',
            'Similares Seleccionados': '#FFA500',
            'Neobancos': '#9370DB'
        }

        formato_hover = '%{x:.2f}%' if metrica_seleccionada == "IMOR" else '%{x:,.0f}'
        df_plot_visual = df_final.iloc[::-1].copy()

        fig = px.bar(
            df_plot_visual,
            x='Valor_Grafica',
            y='Institución',
            orientation='h',
            text='Rank_Texto',
            color='Grupo Bancario',
            color_discrete_map=colores_grupos,
            title=f"Ranking {nivel} - {metrica_seleccionada} ({cartera_seleccionada} - {genero_seleccionado})"
        )

        fig.update_layout(
            yaxis={'categoryorder': 'array', 'categoryarray': df_plot_visual['Institución']},
            height=600,
            showlegend=True,
            xaxis_title=metrica_seleccionada + (" (%)" if metrica_seleccionada == "IMOR" else ""),
            yaxis_title=""
        )

        fig.update_traces(
            textposition='outside',
            texttemplate='# %{text}',
            hovertemplate='<b>%{y}</b><br>Ranking: #%{text}<br>Valor: ' + formato_hover + '<extra></extra>'
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos de instituciones con saldo mayor a cero para este filtro.")
else:
    st.warning("No hay datos de instituciones con saldo mayor a cero para este filtro.")
