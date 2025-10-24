import pandas as pd
import streamlit as st
import warnings
import re
import unicodedata
from typing import List, Dict

# --- DEFINICIÓN DE FUENTES DE DATOS PERMANENTES (11 PROVEEDORES) ---
# Se utiliza el parámetro 'output=csv' para que Pandas lo lea directamente
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
    "Granja": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSNLPa4CWzGrjoL2XEzoBYrkepJSJ7RzOzb5XqP2hXyg1RPodDUTHbdkfPQphGZ5K1XmRo1WQK0br4S/pub?output=csv",
}

# Generar la lista de proveedores (excluyendo NutriSana para el orden de la tabla)
orden_proveedores = [nombre for nombre in PROVEEDORES_GSPREAD.keys() if nombre != "NutriSana"]


# --- FUNCIÓN DE LIMPIEZA Y NORMALIZACIÓN DE ACENTOS ---
def normalizar_busqueda(texto: str) -> str:
    """Elimina acentos, convierte a minúsculas y normaliza el texto para la búsqueda."""
    if pd.isna(texto):
        return ""
    try:
        # Convertir a minúsculas
        texto = str(texto).lower()
        # Eliminar acentos y caracteres especiales (normalización Unicode)
        nfkd_form = unicodedata.normalize('NFKD', texto)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    except Exception:
        return ""


# --- FUNCIÓN DE PROCESAMIENTO Y CARGA DESDE URL ---
@st.cache_data(ttl=3600)
def cargar_proveedor_desde_url(url: str, nombre_proveedor: str) -> pd.DataFrame:
    """Carga y procesa un archivo de proveedor desde una URL de Google Sheets."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            # Leer el CSV directamente desde la URL
            df = pd.read_csv(url)

        # A: VERIFICACIÓN DE COLUMNAS (Obligatorio para Streamlit)
        required_cols = ['Producto y Descripcion', 'Precio']
        if not all(col in df.columns for col in required_cols):
             st.warning(f"⚠️ Error en {nombre_proveedor}: Columnas 'Producto y Descripcion' o 'Precio' no encontradas. Revise el encabezado de su hoja.")
             return pd.DataFrame()

        # B: LIMPIEZA Y PROCESAMIENTO DEL % VARIACION
        if '% Variacion' in df.columns:
            # 1. Eliminar el símbolo % si está presente
            df['% Variacion'] = df['% Variacion'].astype(str).str.replace('%', '', regex=False)
            df['% Variacion'] = pd.to_numeric(df['% Variacion'], errors='coerce')
            
            # 2. Ajustar porcentajes si el formato original era decimal (ej. 0.05 -> 5.0)
            df.loc[
                (df['% Variacion'].abs() < 1) & (df['% Variacion'].abs() > 0.001),
                '% Variacion'
            ] = df['% Variacion'] * 100

        # C: NORMALIZACIÓN DE LA COLUMNA DE BÚSQUEDA
        df['Producto y Descripcion Normalizada'] = df['Producto y Descripcion'].apply(normalizar_busqueda)
        
        return df

    except Exception as e:
        # Aquí capturamos el error 404 (URL rota o no pública)
        st.error(f"❌ Error al cargar los datos de {nombre_proveedor}. Revise la URL o el formato de la hoja: {e}")
        return pd.DataFrame()


# --- FUNCIÓN DE BÚSQUEDA ---
def buscar_y_comparar_precios_web(minorista_df: pd.DataFrame, minorista_nombre: str, mayoristas_dataframes_dict: Dict[str, pd.DataFrame], orden_proveedores: List[str], entrada_usuario: str) -> Dict[str, pd.DataFrame]:
    """Realiza la búsqueda y prepara los resultados para su visualización en Streamlit."""
    
    # Normalizar la entrada del usuario para buscar sin acentos
    entrada_normalizada = normalizar_busqueda(entrada_usuario)
    
    palabras_incluir = [p for p in entrada_normalizada.split() if not p.startswith('-')]
    palabras_excluir = [p.lstrip('-') for p in entrada_normalizada.split() if p.startswith('-')]
    
    if not palabras_incluir:
        return {}

    # Lógica de búsqueda OR o AND
    palabras_or = []
    if any('|' in p for p in palabras_incluir):
        palabras_or = [p.strip() for p in ' '.join(palabras_incluir).split('|') if p.strip()]
        
        def filtro_productos(descripcion):
             # La descripción a buscar ya está normalizada en 'Producto y Descripcion Normalizada'
             return any(p in descripcion for p in palabras_or) and not any(p in descripcion for p in palabras_excluir)
    else:
        def filtro_productos(descripcion):
             return all(p in descripcion for p in palabras_incluir) and not any(p in descripcion for p in palabras_excluir)

    resultados = {}
    
    # Búsqueda en el archivo minorista
    if not minorista_df.empty:
        minorista_filtrado = minorista_df[
            minorista_df['Producto y Descripcion Normalizada'].apply(filtro_productos)
        ].copy()
        if not minorista_filtrado.empty:
            resultados[minorista_nombre] = minorista_filtrado

    # Búsqueda en los archivos de los mayoristas
    for nombre_proveedor in orden_proveedores:
        df_mayorista = mayoristas_dataframes_dict.get(nombre_proveedor)
        if df_mayorista is None or df_mayorista.empty:
            continue
            
        df_filtrado = df_mayorista[
            df_mayorista['Producto y Descripcion Normalizada'].apply(filtro_productos)
        ].copy()
            
        if not df_filtrado.empty:
            resultados[nombre_proveedor] = df_filtrado
            
    return resultados


# --- FUNCIÓN DE FORMATO DE COLUMNAS PARA DISPLAY ---

def format_precio(p: float, nombre_proveedor: str) -> str:
    """
    Formatea el precio, aplicando la lógica condicional para Granja y la lógica
    original (que asume decimales o formato diferente) para otros.
    """
    if pd.isna(p) or p is None:
        return "N/D"

    try:
        # Convertir a número float si es necesario
        p = float(p)
        
        # LÓGICA ESPECIAL PARA GRANJA: El precio viene como entero (11285) sin decimales.
        if nombre_proveedor == "Granja":
            # Formatear el entero como separador de miles
            # Usamos f-string con formato de miles y el punto como separador (Argentina usa coma)
            # Pero Streamlit/Python usa punto por defecto en este formato. 
            # Reemplazamos el punto de miles por coma para el display final.
            return f"${int(p):,}".replace(",", ".") 
        
        # LÓGICA PARA LOS OTROS PROVEEDORES: Usar la lógica que ya funcionaba,
        # que asume que el precio ya viene bien formateado o con decimales.
        # Se asume que el valor en Sheets viene en el formato que funcionaba
        # con tu código anterior.
        
        # Aplicamos el formato estándar de miles con punto (.) y reemplazamos a coma (,)
        # para visualización argentina.
        return f"${p:,.2f}".replace(",", "_TEMP_").replace(".", ",").replace("_TEMP_", ".")
        
    except (ValueError, TypeError):
        return "N/D"


def format_variacion(v: float) -> str:
    """Formatea la variación con color y símbolo (HTML). Rojo para baja (<0), Verde para subida (>0)."""
    if pd.isna(v) or v == 0.0:
        return ''

    # Lógica de Color: Rojo para la BAJA (Oportunidad), Verde para la SUBIDA.
    simbolo = "▲" if v > 0 else "▼"
    color = "green" if v > 0 else "red"
    
    # Formato del número (ej: 10,3%)
    variacion_str = f"{abs(v):.1f}%".replace('.', ',')
    
    # Retornamos HTML para que st.markdown lo interprete
    return f'<span style="color:{color}; font-weight: bold;">{simbolo} {variacion_str}</span>'


# --- INTERFAZ STREAMLIT (MAIN) ---
st.title("Master Price de NutriSana " + '<span style="font-size: 50%; color: #888;">by GED</span>', unsafe_allow_html=True)
st.subheader("Comparador de Precios")

# 1. Carga de Datos al inicio (Automática)
st.sidebar.header("Estado de los Datos")

mayoristas_dataframes = {}
minorista_df = pd.DataFrame()
minorista_nombre = "NutriSana"
proveedores_cargados = 0

with st.spinner('Cargando datos permanentes desde Google Sheets...'):
    for nombre, url in PROVEEDORES_GSPREAD.items():
        df = cargar_proveedor_desde_url(url, nombre)
        if not df.empty:
            proveedores_cargados += 1
            if nombre == minorista_nombre:
                minorista_df = df
            else:
                mayoristas_dataframes[nombre] = df

st.sidebar.success(f"✅ {proveedores_cargados} de {len(PROVEEDORES_GSPREAD)} fuentes cargadas.")


# 2. Interfaz de Búsqueda
st.header("Búsqueda de Productos")
st.markdown("Consejo: Usa `-` para excluir palabras (ej: `almendras -leche`). Usa `|` para búsqueda OR (ej: `almendra | nuez`). La búsqueda ignora acentos.")
entrada_usuario = st.text_input("Ingrese el nombre del producto:", key="search_input")


# 3. Lógica y Visualización de Resultados
if entrada_usuario and proveedores_cargados > 0:
    resultados = buscar_y_comparar_precios_web(minorista_df, minorista_nombre, mayoristas_dataframes, orden_proveedores, entrada_usuario)
    
    st.markdown("\n" + "*"*50)
    st.markdown("### >>> RESULTADO DE LA BÚSQUEDA <<<")
    st.markdown("*"*50)
    
    if not resultados:
        st.warning("😔 No se encontraron productos que coincidan con las palabras clave.")
    else:
        
        # Itera sobre los resultados en el orden deseado
        for nombre_proveedor in [minorista_nombre] + orden_proveedores:
            if nombre_proveedor in resultados:
                df_filtrado = resultados[nombre_proveedor].copy()
                st.markdown(f"\n#### --- {nombre_proveedor.upper()} ---")

                # Preparar DataFrame para Streamlit: Aplicar formatos y reordenar
                df_display = pd.DataFrame({
                    # 1. Columna de Producto y Descripción (Limpieza y Capitalización)
                    'Producto y Descripcion': df_filtrado['Producto y Descripcion'].str.title(), 
                    
                    # 2. Columna de Precio (Lógica condicional)
                    'Precio': df_filtrado['Precio'].apply(lambda p: format_precio(p, nombre_proveedor)),
                    
                    # 3. Columna de Variación (Con colores en HTML)
                    'Var. Sem.': df_filtrado['% Variacion'].apply(format_variacion),
                })
                
                # Concatenar las columnas de texto (Producto y Precio) y la columna HTML (Var. Sem.)
                # Usamos st.markdown con to_html para renderizar los colores de la Var. Sem.
                st.write(df_display.style.to_html(index=False, escape=False), unsafe_allow_html=True)
