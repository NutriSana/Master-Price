import pandas as pd
import streamlit as st
import warnings
import re
import unicodedata 

# --- 1. DEFINICIÓN DE FUENTES DE DATOS PERMANENTES (PEGADAS DEL ARCHIVO PLANO) ---
# FIX aplicado a Adicon: Cambiado '/sheets/' por '/spreadsheets/' 
# Si NutriSana falla, la URL debe ser re-publicada y pegada aquí.
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

orden_proveedores = [nombre for nombre in PROVEEDORES_GSPREAD.keys() if nombre != "NutriSana"]
minorista_nombre = "NutriSana"


# --- FUNCIÓN AUXILIAR PARA LA BÚSQUEDA SIN ACENTOS ---
def normalizar_busqueda(texto):
    """Convierte texto a minúsculas y elimina acentos para una búsqueda agnóstica al acento."""
    if pd.isna(texto):
        return ""
    
    # 1. Normalizar a formato NFD (separa la letra del acento)
    nfkd_form = unicodedata.normalize('NFD', str(texto).lower())
    # 2. Remover los caracteres diacríticos (acentos)
    texto_sin_acento = "".join(c for c in nfkd_form if not unicodedata.combining(c))
    
    # 3. Limpieza y retorno
    return re.sub(r'[\r\n]+', ' ', texto_sin_acento).strip()


# --- 2. FUNCIÓN DE PROCESAMIENTO Y CARGA DESDE URL ---
@st.cache_data(ttl=3600)
def cargar_proveedor_desde_url(url, nombre_proveedor):
    """Carga y procesa un archivo de proveedor desde una URL de Google Sheets (formato CSV)."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            # Aseguramos que la columna se lea como texto antes de limpiarla
            df = pd.read_csv(url, encoding='utf-8', dtype={'Producto y Descripcion': str}) 

        if 'Producto y Descripcion' not in df.columns or 'Precio' not in df.columns:
             st.warning(f"⚠️ Error en {nombre_proveedor}: Columnas 'Producto y Descripcion' o 'Precio' no encontradas. Revise el encabezado de su hoja.")
             return pd.DataFrame()

        # Normalización de la descripción al cargar los datos
        df['Producto y Descripcion (Normalizada)'] = df['Producto y Descripcion'].apply(normalizar_busqueda)

        # Procesa % Variacion
        if '% Variacion' not in df.columns:
             df['% Variacion'] = pd.NA
        else:
             # Elimina el símbolo '%' antes de la conversión numérica
             df['% Variacion'] = df['% Variacion'].astype(str).str.replace('%', '', regex=False).str.strip()
             
             df['% Variacion'] = pd.to_numeric(df['% Variacion'], errors='coerce')
             
             # Conversión si el porcentaje está en formato 0.05
             df.loc[
                 (df['% Variacion'].abs() < 1) & (df['% Variacion'] != 0.0),
                 '% Variacion'
             ] = df['% Variacion'] * 100
        
        return df

    except Exception as e:
        # Muestra el error específico para ayudar al usuario a diagnosticar URL
        st.error(f"❌ Error al cargar los datos de {nombre_proveedor}. Revise la URL o el formato de la hoja: {e}")
        return pd.DataFrame()

# --- 3. FUNCIÓN DE BÚSQUEDA ---
def buscar_y_comparar_precios_web(minorista_df, minorista_nombre, mayoristas_dataframes_dict, orden_proveedores, entrada_usuario):
    """Realiza la búsqueda utilizando la columna normalizada y prepara los resultados."""
    
    # Normalizar la entrada del usuario inmediatamente
    entrada_normalizada = normalizar_busqueda(entrada_usuario)
    
    palabras_incluir = [p for p in entrada_normalizada.split() if not p.startswith('-')]
    palabras_excluir = [p.lstrip('-') for p in entrada_normalizada.split() if p.startswith('-')]
    
    if not palabras_incluir:
        return {}

    palabras_or = []
    if any('|' in p for p in palabras_incluir):
        palabras_or = [p.strip() for p in ' '.join(palabras_incluir).split('|') if p.strip()]
        
        # Filtra usando la columna normalizada
        def filtro_productos(descripcion_normalizada):
             return any(p in descripcion_normalizada for p in palabras_or) and not any(p in descripcion_normalizada for p in palabras_excluir)
    else:
        # Filtra usando la columna normalizada
        def filtro_productos(descripcion_normalizada):
             return all(p in descripcion_normalizada for p in palabras_incluir) and not any(p in descripcion_normalizada for p in palabras_excluir)

    resultados = {}
    
    # Aplica filtro en la columna 'Producto y Descripcion (Normalizada)'
    def aplicar_filtro(df):
        return df[df['Producto y Descripcion (Normalizada)'].apply(filtro_productos)].copy()

    if not minorista_df.empty:
        minorista_filtrado = aplicar_filtro(minorista_df)
        if not minorista_filtrado.empty:
            resultados[minorista_nombre] = minorista_filtrado

    for nombre_proveedor in orden_proveedores:
        df_mayorista = mayoristas_dataframes_dict.get(nombre_proveedor)
        if df_mayorista is None or df_mayorista.empty:
            continue
            
        df_filtrado = aplicar_filtro(df_mayorista)
            
        if not df_filtrado.empty:
            resultados[nombre_proveedor] = df_filtrado
            
    return resultados

# --- 4. FUNCIONES DE FORMATO PARA LA VISUALIZACIÓN EN STREAMLIT ---

def format_variacion(v):
    """
    Formatea la variación con color y símbolo.
    Lógica Comercial: Precio más bajo (Negativo) -> ROJO (Alerta de Oportunidad).
    Precio más alto (Positivo) -> Verde (Alerta de Advertencia).
    """
    if pd.notna(v) and v != 0.0:
        variacion_str = f"{abs(v):.1f}%".replace('.', ',')
        if v < 0:
            # Color Rojo: Precio bajó (Oportunidad, Resaltar)
            return f':red[▼ {variacion_str}]' 
        else:
            # Color Verde: Precio subió (Advertencia/Cuidado)
            return f':green[▲ +{variacion_str}]'
    return ''

def format_precio(p):
    """Formatea el precio como moneda con separador de miles (ej: $1.234)."""
    try:
        p_str = str(p).replace('.', '').replace(',', '.')
        precio_int = int(float(p_str))
        return f"${precio_int:,}".replace(',', '.')
    except (ValueError, TypeError):
        return "N/D"

# --- INTERFAZ STREAMLIT (MAIN) ---
# FIX: Usamos st.markdown con HTML para ajustar el tamaño del texto "by GED" 
st.markdown("<h1>Master Price de NutriSana <span style='font-size: 50%;'>by GED</span></h1>", unsafe_allow_html=True)
st.subheader("Comparador de Precios")

# 1. Carga de Datos al inicio (Automática)
st.sidebar.header("Estado de los Datos")

mayoristas_dataframes = {}
minorista_df = pd.DataFrame()
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
st.markdown("Ahora puedes buscar **sin preocuparte por los acentos** (ej: `arandano` encontrará `arándano`).")
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

                # Preparar DataFrame para Streamlit Display (ORDEN DE COLUMNAS SOLICITADO: Producto, Precio, Var)
                df_display = pd.DataFrame({
                    # Mostrar la descripción original (no la normalizada)
                    'Producto y Descripcion': df_filtrado['Producto y Descripcion'].str.title(), 
                    'Precio': df_filtrado['Precio'].apply(format_precio),                            
                    'Var. Sem.': df_filtrado['% Variacion'].apply(format_variacion),                 
                })
                
                # Mostrar el DataFrame de Streamlit
                st.markdown(df_display.to_markdown(index=False), unsafe_allow_html=True)


