import pandas as pd
import streamlit as st
import re
import unicodedata
from typing import List, Dict

# --- CORRECCIÓN DE ERROR: NECESITA IMPORTAR Dict y List de typing ---
# El error NameError previo se corrigió al añadir List y Dict al import.

# --- DEFINICIÓN DE FUENTES DE DATOS PERMANENTES (11 PROVEEDORES) ---
PROVEEDORES_GSPREAD = {
    "NutriSana": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQQalLyAjQf428gCk1370q_gFDbdvHxISf7ZJ445PGNcDqWJc1NYZDnCw5uPK7gOcp7FsyHgOti1DEW/pub?output=csv",
    "Distrimay": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQCyAsWTWw1Yr7rlYXPUf6J84bxskPI4HQeeofaD5ayRWr--PHuEQ88XvtVwNn-tfNjODzQfBNOMx8P/pub?output=csv",
    "ByC": "https://docs.google.com/spreadsheets/d/e/2PACX-1vRPanQSsCEcNUhDHWnEi8T6gNpXS0Gt2UPc9-UxZ4VUVXtwRH-57Y3-UIFBPz5v0zp3EClpiFWIBcNY/pub?output=csv",
    "Salteño": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQIbSgI_6QffZvWzxiYxq9lZifQcxQNjAvqmocdX3teIhzfMH5JIO3QfgPpfqYREAxP4nZGeZjlMKN8/pub?output=csv",
    "Activate": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQYc-1NKWS-BPVgGmAAYWNGvBZbX4Ct39DKdCdrbKDDuy9g-qgpntMn38jEDn6D_Y7Fury5pgFEklLo/pub?output=csv",
    "Mercadito": "https://docs.google.com/spreadsheets/d/e/2PACX-1vRB4oq8P5PMVmQfozZhhwEZpp5gvhPbX0d4VKaUXkFtdU__9Cgb_CYEg_Y5_T7AOCLPwnxDlqsjIKy2/pub?output=csv",
    "Adicon": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQa-lp-5_43z1AD_yxcTiHg67XfF8bia-rmwzh-IJMMJEQfDFHI9ubIbXP3sPGr9kj1nkuQtwN3EmMy/pub?output=csv",
    "Adrian": "https://docs.google.com/spreadsheets/d/e/2PACX-1vQCK0Q1WP5bQ0P9_Xazw3TYYpgs0LOLT2A7ZDeMGrV8aZ0bUJQkjBT9hYQu8UryQcJN6SgBFQgxyPuR/pub?output=csv",
    "Naturista": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSSnB4VhOGvIBgNusRrQRlvorvJ0YkBtnkj5rrRhyDfERIzSD8Ewx8K96PgMlOjDqXzGd4ZqL3bvu7s/pub?output=csv",
    "Sta Ana": "https://docs.google.com/spreadsheets/d/e/2PACX-1vRRfZimr5ZlRootml7K1YRC8P-UvkB4FGnHnsnOt0R_0WiVkEwsBSlh5Dk6RvVd6WVQbVz7k-cqBcwG/pub?output=csv",
    "FM": "https://docs.google.com/spreadsheets/d/e/2PACX-1vRTO3xb4zobFRkVdM6q5B_DqVQYuy5kdUv_YdRysyvGTEjb4hx-H1bWpuB9X08pKg/pub?output=csv",
     # Tienda suspendida  (no envió actualización) "Granja": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSNLPa4CWzGrjoL2XEzoBYrkepJSJ7RzOzb5XqP2hXyg1RPodDUTHbdkfPQphGZ5K1XmRo1WQK0br4S/pub?output=csv",
}
orden_proveedores = [nombre for nombre in PROVEEDORES_GSPREAD.keys() if nombre != "NutriSana"]

# --- FUNCIONES DE UTILIDAD ---

def normalizar_busqueda(texto: str) -> str:
    """Elimina acentos y convierte a minúsculas para búsquedas sin diacríticos."""
    if not isinstance(texto, str):
        return ""
    texto = texto.lower().replace('ñ', 'n')
    # Normalización para eliminar acentos (diacríticos)
    texto = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in texto if unicodedata.category(c) != 'Mn')


@st.cache_data(ttl=3600)
def cargar_proveedor_desde_url(url: str, nombre_proveedor: str) -> pd.DataFrame:
    """Carga y procesa un archivo de proveedor desde una URL de Google Sheets (formato CSV)."""
    try:
        df = pd.read_csv(url)
        
        # 1. Asegurarse de que las columnas críticas existen (Caso Granja/Otros)
        if 'Producto y Descripcion' not in df.columns or 'Precio' not in df.columns:
             # Devuelve un DataFrame vacío si faltan columnas esenciales
             return pd.DataFrame()

        # 2. Procesamiento del % Variacion 
        if '% Variacion' not in df.columns:
             df['% Variacion'] = 0.0 # Valor por defecto 
        else:
             # Limpieza del símbolo % (en caso de que el sheet lo tenga como texto)
             df['% Variacion'] = df['% Variacion'].astype(str).str.replace('%', '', regex=False)
             df['% Variacion'] = pd.to_numeric(df['% Variacion'], errors='coerce')
             
             # Conversión de decimales a porcentaje base 100 (ej: 0.05 -> 5.0)
             df.loc[
                 (df['% Variacion'] < 1) & (df['% Variacion'] > -1) & (df['% Variacion'] != 0.0),
                 '% Variacion'
             ] = df['% Variacion'] * 100

        # 3. Limpieza y Normalización de la descripción
        df['Producto y Descripcion'] = df['Producto y Descripcion'].astype(str).str.lower().apply(
             lambda x: re.sub(r'[\r\n]+', ' ', x).strip()
        )
        # Aplicar normalización sin acentos a la columna para la búsqueda (IMPORTANTE)
        df['Producto_Normalizado'] = df['Producto y Descripcion'].apply(normalizar_busqueda)

        return df

    except Exception:
        # st.error(f"❌ Error al cargar los datos de {nombre_proveedor}. Revise la URL o el formato de la hoja: {e}")
        return pd.DataFrame()


def buscar_y_comparar_precios_web(minorista_df: pd.DataFrame, minorista_nombre: str, mayoristas_dataframes_dict: Dict[str, pd.DataFrame], orden_proveedores: List[str], entrada_usuario: str) -> Dict[str, pd.DataFrame]:
    """Realiza la búsqueda y prepara los resultados para su visualización en Streamlit."""
    
    # Normalizar la entrada del usuario para buscar sin acentos
    entrada_usuario_normalizada = normalizar_busqueda(entrada_usuario)
    
    palabras_incluir = [p for p in entrada_usuario_normalizada.split() if not p.startswith('-')]
    palabras_excluir = [p.lstrip('-') for p in entrada_usuario_normalizada.split() if p.startswith('-')]
    
    if not palabras_incluir:
        return {}

    # Lógica de búsqueda OR o AND
    palabras_or = []
    if any('|' in p for p in palabras_incluir):
        palabras_or = [p.strip() for p in ' '.join(palabras_incluir).split('|') if p.strip()]
        def filtro_productos(descripcion_normalizada):
             return (any(p in descripcion_normalizada for p in palabras_or) and 
                     not any(p in descripcion_normalizada for p in palabras_excluir))
    else:
        def filtro_productos(descripcion_normalizada):
             return (all(p in descripcion_normalizada for p in palabras_incluir) and 
                     not any(p in descripcion_normalizada for p in palabras_excluir))

    resultados = {}
    
    todos_dfs = {minorista_nombre: minorista_df}
    todos_dfs.update(mayoristas_dataframes_dict)

    for nombre_proveedor, df in todos_dfs.items():
        if df.empty:
            continue
            
        # Buscar usando la columna Producto_Normalizado
        df_filtrado = df[
            df['Producto_Normalizado'].apply(filtro_productos)
        ].copy()
            
        if not df_filtrado.empty:
            resultados[nombre_proveedor] = df_filtrado
            
    return resultados


# --- FUNCIONES DE FORMATO PARA LA TABLA ---

def format_variacion(v):
    """Formatea el porcentaje de variación con color y símbolo (Rojo = Baja, Verde = Subida)."""
    if pd.notna(v) and v != 0.0:
        variacion_str = f"{abs(v):.1f}%".replace('.', ',')
        
        # Logica: Rojo (Oportunidad/Baja de precio), Verde (Subida de precio)
        if v < 0:
            return f'<span style="color: red; font-weight: bold;">▼ {variacion_str}</span>'
        else:
            return f'<span style="color: green; font-weight: bold;">▲ {variacion_str}</span>'
    return ''

def format_precio(p, nombre_proveedor):
    """Formatea el precio, ajustando la lógica de decimales para Granja."""
    try:
        # Conversión robusta a float, tratando el punto como separador decimal si existe
        price_float = float(str(p).replace('.', '').replace(',', '.'))
        
        # Lógica Condicional de Formato para Granja (asume que el valor ya es el precio entero 11285)
        if nombre_proveedor == "Granja":
             # Mostrar el valor entero con separador de miles.
             # Usamos locale=es_AR o similar en un entorno real, aquí simulamos con f-string:
             return f"${int(price_float):,}".replace(',', 'X').replace('.', ',').replace('X', '.')
        
        # Lógica para el resto de proveedores (asume que el valor viene en el formato que funcionó)
        # Aquí puedes dejar la lógica original que te funcionaba para los otros 10 proveedores.
        # Por ahora, usamos el mismo formato general, asumiendo que el valor en Sheets ya está ajustado.
        return f"${int(price_float):,}".replace(',', 'X').replace('.', ',').replace('X', '.')
        
    except (ValueError, TypeError):
        return "N/D"


# --- INTERFAZ STREAMLIT (MAIN) ---

# Título principal usando markdown para inyectar HTML de estilo para "by GED"
st.markdown("<h1>Master Price de NutriSana <span style='font-size: 50%; color: #888;'>by GED</span></h1>", unsafe_allow_html=True)
st.subheader("Comparador de Precios")

# 1. Carga de Datos al inicio (Automática)
st.sidebar.header("Estado de los Datos")

mayoristas_dataframes = {}
minorista_df = pd.DataFrame()
minorista_nombre = "NutriSana"
proveedores_cargados = 0

# Cargar todas las fuentes
for nombre, url in PROVEEDORES_GSPREAD.items():
    df = cargar_proveedor_desde_url(url, nombre)
    if not df.empty:
        proveedores_cargados += 1
        if nombre == minorista_nombre:
            minorista_df = df
        else:
            mayoristas_dataframes[nombre] = df

st.sidebar.success(f"✅ {proveedores_cargados} de {len(PROVEEDORES_GSPREAD)} fuentes cargadas.")

if proveedores_cargados < len(PROVEEDORES_GSPREAD):
    st.warning("⚠️ Algunas fuentes no pudieron cargarse. Revise la Publicación en la web.")

# 2. Interfaz de Búsqueda
st.header("Búsqueda de Productos")
st.markdown("Consejo: Usa **-** para excluir (ej: `almendras -leche`). Usa **|** para búsqueda OR (ej: `almendra | nuez`).")
entrada_usuario = st.text_input("Ingrese el nombre del producto:", key="search_input")

# 3. Lógica y Visualización de Resultados
if entrada_usuario and proveedores_cargados > 0:
    
    # Obtener el orden original de los proveedores (asegura que NutriSana vaya primero)
    orden_display = [minorista_nombre] + [p for p in orden_proveedores if p in mayoristas_dataframes]

    resultados = buscar_y_comparar_precios_web(minorista_df, minorista_nombre, mayoristas_dataframes, orden_proveedores, entrada_usuario)
    
    st.markdown("\n" + "*"*50)
    st.markdown("### >>> RESULTADO DE LA BÚSQUEDA <<<")
    st.markdown("*"*50)
    
    if not resultados:
        st.warning("😔 No se encontraron productos que coincidan con las palabras clave.")
    else:
        
        for nombre_proveedor in orden_display:
            if nombre_proveedor in resultados:
                df_filtrado = resultados[nombre_proveedor].copy()
                
                # Crear las columnas de display
                df_display = pd.DataFrame({
                    'Producto y Descripcion': df_filtrado['Producto y Descripcion'].str.title(), # Capitalizar para mejor lectura
                    'Precio': df_filtrado['Precio'].apply(lambda p: format_precio(p, nombre_proveedor)),
                    'Var. Sem.': df_filtrado['% Variacion'].apply(format_variacion),
                })
                
                st.markdown(f"\n#### --- {nombre_proveedor.upper()} ---")

                # Mostrar tabla: Oculta el índice y usa st.markdown para renderizar el HTML con los colores
                st.write(df_display.style.hide(axis="index").to_html(escape=False), unsafe_allow_html=True)






