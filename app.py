import pandas as pd
import streamlit as st
import warnings
import re
import unicodedata
# --- CORRECCIÓN ---
# Añadir 'List' a la importación de typing
from typing import Dict, Any, List 

# --- DEFINICIÓN DE FUENTES DE DATOS PERMANENTES (11 Proveedores) ---
# Se utiliza el nombre del proveedor como clave. 
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

# La lista de nombres de proveedores se genera automáticamente desde el diccionario
orden_proveedores = [nombre for nombre in PROVEEDORES_GSPREAD.keys() if nombre != "NutriSana"]


# --- FUNCIONES DE LIMPIEZA Y PROCESAMIENTO ---

def normalizar_busqueda(texto: str) -> str:
    """Elimina acentos, convierte a minúsculas y limpia el texto para la búsqueda."""
    if not isinstance(texto, str):
        return ""
    # 1. Normalizar Unicode para separar acentos y diéresis de la letra base
    normalized = unicodedata.normalize('NFD', texto.lower())
    # 2. Eliminar caracteres diacríticos (acentos, virgulillas)
    # Criterio: mantén solo el carácter si no es un Mark (Mn)
    no_accents = ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')
    # 3. Limpiar caracteres especiales y dejar solo letras, números y espacios
    return re.sub(r'[^a-z0-9\s]', '', no_accents).strip()


@st.cache_data(ttl=3600)
def cargar_proveedor_desde_url(url: str, nombre_proveedor: str) -> pd.DataFrame:
    """Carga y procesa un archivo de proveedor desde una URL de Google Sheets (formato CSV)."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            # Leer el archivo CSV directamente desde la URL
            df = pd.read_csv(url)

        # Verificar encabezados
        required_cols = ['Producto y Descripcion', 'Precio']
        if not all(col in df.columns for col in required_cols):
             st.warning(f"⚠️ Error en {nombre_proveedor}: Columnas {required_cols} no encontradas. Revise el encabezado de su hoja.")
             return pd.DataFrame()

        # 1. Procesamiento de la Variación (% Variacion)
        if '% Variacion' not in df.columns:
             df['% Variacion'] = 0.0 # Inicializar si no existe
        else:
             # Limpiar el símbolo % para permitir conversión numérica
             df['% Variacion'] = df['% Variacion'].astype(str).str.replace('%', '', regex=False)
             df['% Variacion'] = pd.to_numeric(df['% Variacion'], errors='coerce')
             
             # Conversión de decimales a porcentaje base 100
             df.loc[
                 (df['% Variacion'] < 1) & (df['% Variacion'] > -1) & (df['% Variacion'] != 0.0),
                 '% Variacion'
             ] = df['% Variacion'] * 100

        # 2. Limpieza y normalización de la descripción (Crucial para la búsqueda con/sin acento)
        df['Producto y Descripcion Original'] = df['Producto y Descripcion'].astype(str)
        df['Producto y Descripcion'] = df['Producto y Descripcion Original'].apply(normalizar_busqueda)
        
        return df

    except Exception as e:
        st.error(f"❌ Error al cargar los datos de {nombre_proveedor}. Revise la URL o el formato de la hoja: {e}")
        return pd.DataFrame()


def buscar_y_comparar_precios_web(minorista_df: pd.DataFrame, minorista_nombre: str, mayoristas_dataframes_dict: Dict[str, pd.DataFrame], orden_proveedores: List[str], entrada_usuario: str) -> Dict[str, pd.DataFrame]:
    """Realiza la búsqueda en los DataFrames cargados utilizando la normalización."""
    
    # Normalizar la entrada del usuario para la búsqueda
    entrada_normalizada = normalizar_busqueda(entrada_usuario)
    palabras_incluir = [p for p in entrada_normalizada.split() if not p.startswith('-')]
    palabras_excluir = [p.lstrip('-') for p in entrada_normalizada.split() if p.startswith('-')]
    
    if not palabras_incluir:
        return {}

    # Lógica de búsqueda OR o AND
    palabras_or = []
    if any('|' in p for p in palabras_incluir):
        palabras_or = [p.strip() for p in ' '.join(palabras_incluir).split('|') if p.strip()]
        def filtro_productos(descripcion_normalizada):
             return any(p in descripcion_normalizada for p in palabras_or) and not any(p in descripcion_normalizada for p in palabras_excluir)
    else:
        def filtro_productos(descripcion_normalizada):
             return all(p in descripcion_normalizada for p in palabras_incluir) and not any(p in descripcion_normalizada for p in palabras_excluir)

    resultados = {}
    
    # Iterar sobre todos los proveedores (minorista + mayoristas)
    todos_proveedores = {minorista_nombre: minorista_df, **mayoristas_dataframes_dict}
    
    for nombre_proveedor, df_proveedor in todos_proveedores.items():
        if df_proveedor is None or df_proveedor.empty:
            continue
            
        df_filtrado = df_proveedor[
            # Aplicar filtro sobre la columna normalizada 'Producto y Descripcion'
            df_proveedor['Producto y Descripcion'].apply(filtro_productos)
        ].copy()
            
        if not df_filtrado.empty:
            resultados[nombre_proveedor] = df_filtrado
            
    return resultados


# --- FUNCIONES DE VISUALIZACIÓN ---

def format_variacion(v: Any) -> str:
    """Formatea el porcentaje de variación con símbolos y color."""
    if pd.isna(v) or v == 0.0:
        return ''
    
    variacion = float(v)
    variacion_str = f"{abs(variacion):.1f}%".replace('.', ',')
    
    # Lógica: Baja el precio (negativo) -> OPORTUNIDAD (Rojo)
    if variacion > 0: # Sube el precio
        color = "green"
        simbolo = "▲"
    else: # Baja el precio o es la oportunidad
        color = "red"
        simbolo = "▼"
        
    return f':{color}[{simbolo} {variacion_str}]'

def format_precio(p: Any, nombre_proveedor: str) -> str:
    """
    Formatea el precio, aplicando una lógica especial para Granja (que viene sin decimales).
    """
    try:
        # Intenta limpiar el precio primero
        p_str = str(p).replace(',', '').replace('$', '').strip()
        
        if not p_str:
            return "N/D"

        precio_num = float(p_str)
        
        # --- LÓGICA CONDICIONAL ---
        if nombre_proveedor == "Granja":
            # Granja ya viene como número entero (11285), sin decimales, 
            # ya que el script de extracción redondeó. Usar el punto como separador de miles.
            
            # Formatear el número entero como string con separadores de miles
            formato_miles = f"{int(precio_num):,}".replace(',', '#') # Usar # temporalmente
            formato_final = formato_miles.replace('.', ',').replace('#', '.') # Convertir Python's , a . para miles
            
            # Ajustamos para el caso de números pequeños (sin separador de miles)
            if not '.' in formato_final: 
                formato_final = formato_final.replace(',', '.')

            return f"${formato_final}"
        else:
            # Lógica original para las otras tiendas (asume precio_num ya incluye decimales si los tenía)
            # Usamos el separador de miles '.' y la coma ',' como separador decimal (Convención Arg)
            
            # Formatear con el punto para miles y la coma para decimales.
            # Primero formateamos con el formato standard (e.g., 1,234.56)
            # Determinar si hay decimales significativos para no truncar a .00
            if abs(precio_num) % 1 == 0:
                formato_standar = f"{precio_num:,.0f}" 
            else:
                formato_standar = f"{precio_num:,.2f}"
            
            # Reemplazamos la convención: 1,234.56 -> 1.234,56
            if '.' in formato_standar: # Si tiene decimales (e.g., 1,234.56)
                formato_arg = formato_standar.replace('.', '#').replace(',', '.').replace('#', ',') # 1.234,56
            else: # Si es entero (e.g., 1,234)
                 formato_arg = formato_standar.replace(',', '.') # 1.234
                 
            return f"${formato_arg}"
            
    except (ValueError, TypeError):
        return "N/D"


# --- INTERFAZ STREAMLIT (MAIN) ---
st.title("Master Price de NutriSana")
st.markdown('<span style="font-size: 50%;">by GED</span>', unsafe_allow_html=True)
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
st.markdown("Consejo: Usa '-' para excluir. Ejemplo: 'almendras -leche'. Usa '|' para búsqueda OR. Ejemplo: 'almendra | nuez'")
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
        
        for nombre_proveedor in [minorista_nombre] + orden_proveedores:
            if nombre_proveedor in resultados:
                df_filtrado = resultados[nombre_proveedor].copy()
                st.markdown(f"\n#### --- {nombre_proveedor.upper()} ---")

                # Preparar DataFrame para Streamlit
                df_display = pd.DataFrame({
                    # Usar la columna original para mostrar el texto con mayúsculas y acentos
                    'Producto y Descripcion': df_filtrado['Producto y Descripcion Original'].str.title(), 
                    # Aplicar formato condicional al precio
                    'Precio': df_filtrado['Precio'].apply(lambda p: format_precio(p, nombre_proveedor)),
                    # Aplicar formato condicional a la variación
                    'Var. Sem.': df_filtrado['% Variacion'].apply(format_variacion),
                })
                
                # Mostrar tabla con formato
                st.dataframe(df_display, use_container_width=True, hide_index=True)
