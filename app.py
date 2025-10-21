import pandas as pd
import streamlit as st
import warnings
import re

# --- 1. DEFINICIÓN DE FUENTES DE DATOS PERMANENTES (PEGADAS DEL ARCHIVO PLANO) ---
# La aplicación leerá los datos directamente de estas URLs CSV publicadas en Google Sheets.
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
}

# La lista de nombres de proveedores (excepto el minorista)
# El nombre de la variable se corrige para que coincida con la definición de la Línea 6.
orden_proveedores = [nombre for nombre in PROVEEDORES_GSPREAD.keys() if nombre != "NutriSana"]
minorista_nombre = "NutriSana"

# --- 2. FUNCIÓN DE PROCESAMIENTO Y CARGA DESDE URL ---
# st.cache_data: Carga los datos automáticamente al inicio y los guarda por 1 hora (3600 segundos)
@st.cache_data(ttl=3600)
def cargar_proveedor_desde_url(url, nombre_proveedor):
    """Carga y procesa un archivo de proveedor desde una URL de Google Sheets (formato CSV)."""
    try:
        # 1. Cargar el CSV directamente desde la URL
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            # Asegura que las cabeceras se carguen correctamente
            df = pd.read_csv(url, encoding='utf-8') 

        # 2. Asegurarse de que las columnas críticas existen
        if 'Producto y Descripcion' not in df.columns or 'Precio' not in df.columns:
             st.warning(f"⚠️ Error en {nombre_proveedor}: Columnas 'Producto y Descripcion' o 'Precio' no encontradas. Revise el encabezado de su hoja.")
             return pd.DataFrame()

        # 3. Procesamiento del % Variacion 
        if '% Variacion' not in df.columns:
             df['% Variacion'] = pd.NA
        else:
             df['% Variacion'] = pd.to_numeric(df['% Variacion'], errors='coerce')
             # Normaliza los valores que son 0.0x para que sean porcentajes (ej. 0.05 -> 5.0)
             df.loc[
                 (df['% Variacion'].abs() < 1) & (df['% Variacion'] != 0.0),
                 '% Variacion'
             ] = df['% Variacion'] * 100

        # 4. Limpieza básica de la columna de descripción (a minúsculas y elimina saltos de línea)
        df['Producto y Descripcion'] = df['Producto y Descripcion'].astype(str).str.lower().apply(
             lambda x: re.sub(r'[\r\n]+', ' ', x).strip()
        )
        
        return df

    except Exception as e:
        st.error(f"❌ Error al cargar los datos de {nombre_proveedor}. Revise la URL o el formato de la hoja: {e}")
        return pd.DataFrame()

# --- 3. FUNCIÓN DE BÚSQUEDA ---
def buscar_y_comparar_precios_web(minorista_df, minorista_nombre, mayoristas_dataframes_dict, orden_proveedores, entrada_usuario):
    """Realiza la búsqueda y prepara los resultados para su visualización en Streamlit."""
    
    palabras_incluir = [p.lower() for p in entrada_usuario.split() if not p.startswith('-')]
    palabras_excluir = [p.lower().lstrip('-') for p in entrada_usuario.split() if p.startswith('-')]
    
    if not palabras_incluir:
        return {}

    # Lógica de búsqueda OR o AND
    palabras_or = []
    # Verifica si el usuario usó el separador OR (|)
    if any('|' in p for p in palabras_incluir):
        palabras_or = [p.strip() for p in ' '.join(palabras_incluir).split('|') if p.strip()]
        
        def filtro_productos(descripcion):
             # Filtro: Contiene AL MENOS una palabra OR y NO contiene ninguna de las excluidas
             return any(p in descripcion for p in palabras_or) and not any(p in descripcion for p in palabras_excluir)
    else:
        def filtro_productos(descripcion):
             # Filtro: Contiene TODAS las palabras INCLUIDAS y NO contiene ninguna de las excluidas
             return all(p in descripcion for p in palabras_incluir) and not any(p in descripcion for p in palabras_excluir)

    resultados = {}
    
    # Aplica filtro en el archivo minorista
    if not minorista_df.empty:
        minorista_filtrado = minorista_df[
            minorista_df['Producto y Descripcion'].apply(filtro_productos)
        ].copy()
        if not minorista_filtrado.empty:
            resultados[minorista_nombre] = minorista_filtrado

    # Aplica filtro en los archivos de los mayoristas
    for nombre_proveedor in orden_proveedores:
        df_mayorista = mayoristas_dataframes_dict.get(nombre_proveedor)
        if df_mayorista is None or df_mayorista.empty:
            continue
            
        df_filtrado = df_mayorista[
            df_mayorista['Producto y Descripcion'].apply(filtro_productos)
        ].copy()
            
        if not df_filtrado.empty:
            resultados[nombre_proveedor] = df_filtrado
            
    return resultados

# --- 4. FUNCIONES DE FORMATO PARA LA VISUALIZACIÓN EN STREAMLIT ---

def format_variacion(v):
    """Formatea la variación con color y símbolo usando Markdown de Streamlit."""
    if pd.notna(v) and v != 0.0:
        variacion_str = f"{abs(v):.1f}%".replace('.', ',')
        if v > 0:
            # Color Rojo (Advertencia/Precio subió)
            return f':red[▲ +{variacion_str}]' 
        else:
            # Color Verde (Oportunidad/Precio bajó)
            return f':green[▼ -{variacion_str}]'
    return ''

def format_precio(p):
    """Formatea el precio como moneda con separador de miles (ej: $1.234)."""
    try:
        # Limpieza robusta de la entrada y formateo
        p_str = str(p).replace('.', '').replace(',', '.')
        precio_int = int(float(p_str))
        return f"${precio_int:,}".replace(',', '.')
    except (ValueError, TypeError):
        return "N/D"

# --- INTERFAZ STREAMLIT (MAIN) ---
st.title("Master Price de NutriSana")
st.subheader("Comparador de Precios")


# 1. Carga de Datos al inicio (Automática)
st.sidebar.header("Estado de los Datos")

mayoristas_dataframes = {}
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
st.markdown("Consejo: Usa `-` para excluir palabras (ej: `almendras -leche`). Usa `|` para búsqueda OR (ej: `almendra | nuez`).")
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
        
        # Iterar sobre los resultados en el orden deseado
        for nombre_proveedor in [minorista_nombre] + orden_proveedores:
            if nombre_proveedor in resultados:
                df_filtrado = resultados[nombre_proveedor].copy()
                st.markdown(f"\n#### --- {nombre_proveedor.upper()} ---")

                # Preparar DataFrame para Streamlit Display
                df_display = pd.DataFrame({
                    'Precio': df_filtrado['Precio'].apply(format_precio),
                    'Var. Sem.': df_filtrado['% Variacion'].apply(format_variacion),
                    # Usamos .str.capitalize() para mejorar la lectura de la descripción en la tabla
                    'Producto y Descripcion': df_filtrado['Producto y Descripcion'].str.capitalize(), 
                })
                
                # Mostrar el DataFrame de Streamlit
                st.markdown(df_display.to_markdown(index=False), unsafe_allow_html=True)
