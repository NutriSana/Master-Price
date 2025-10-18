import pandas as pd
import streamlit as st
import re
# Ya no necesitamos os, glob, o sys

# ... (Definición de 'procesar_proveedor_gestion' se mantiene,
#      pero debe aceptar un objeto FileUploader de Streamlit) ...

def procesar_proveedor_gestion_streamlit(uploaded_file):
    # Carga el archivo desde el objeto subido, no desde una ruta de disco
    try:
        # st.cache_data asegura que el DataFrame no se recargue innecesariamente
        @st.cache_data
        def load_data(file):
            return pd.read_excel(file)

        df = load_data(uploaded_file)
        # ... (La lógica de limpieza de columnas y % Variacion es la misma) ...
        # ... (Se elimina el manejo de FileNotFoundError) ...
        return df
    except Exception as e:
        st.error(f"❌ Error al leer el archivo Excel: {e}")
        return pd.DataFrame()

# --- Main de la aplicación Streamlit ---
st.title("🔍 Master Price de NutriSana 🔍")

# Título Secundario (st.header o st.subheader, usa subheader para que sea más pequeño)
st.subheader("Comparador de Precios by ged")

# Se usa un File Uploader para cada tipo de archivo
minorista_file = st.sidebar.file_uploader("Subir Archivo Minorista (Nutrisana)", type=["xlsx"])
mayorista_files = st.sidebar.file_uploader("Subir Archivos Mayoristas", type=["xlsx"], accept_multiple_files=True)

minorista_df = pd.DataFrame()
mayoristas_dataframes = {}

# Procesamiento del Minorista
if minorista_file:
    minorista_df = procesar_proveedor_gestion_streamlit(minorista_file)
    st.sidebar.success("Minorista cargado con éxito.")

# Procesamiento de Mayoristas
if mayorista_files:
    for f in mayorista_files:
        nombre = f.name.split('_')[0].title() # Extraer el nombre del archivo
        df = procesar_proveedor_gestion_streamlit(f)
        if not df.empty:
            mayoristas_dataframes[nombre] = df
    st.sidebar.success(f"{len(mayoristas_dataframes)} Mayoristas cargados.")


# 2. Búsqueda
st.header("Búsqueda de Productos")
entrada_usuario = st.text_input("Ingrese el nombre del producto ('almendra | nuez', '-leche')", key="search_input")

if entrada_usuario:
    # (El resto de la función 'buscar_y_comparar_precios' se adaptaría aquí,
    #  sustituyendo el input/while por la lógica de filtrado de pandas)

    palabras_incluir = [p.lower() for p in entrada_usuario.split() if not p.startswith('-')]
    palabras_excluir = [p.lower().lstrip('-') for p in entrada_usuario.split() if p.startswith('-')]
    
    # ... (Aquí iría la lógica de filtrado OR/AND y exclusión) ...

    resultados = {}
    
    # Ejemplo de filtrado (simplificado)
    def filtro_productos(descripcion):
        return all(p in descripcion for p in palabras_incluir) and not any(p in descripcion for p in palabras_excluir)

    # Filtrar minorista
    if not minorista_df.empty:
        df_filtrado = minorista_df[minorista_df['Producto y Descripcion'].astype(str).str.lower().apply(filtro_productos)].copy()
        if not df_filtrado.empty:
            resultados['NutriSana'] = df_filtrado

    # Filtrar mayoristas
    for nombre, df in mayoristas_dataframes.items():
        df_filtrado = df[df['Producto y Descripcion'].astype(str).str.lower().apply(filtro_productos)].copy()
        if not df_filtrado.empty:
            resultados[nombre] = df_filtrado

    # 3. Mostrar Resultados
    st.subheader("Resultados:")
    if resultados:
        for nombre_proveedor, df_filtrado in resultados.items():
            st.markdown(f"### --- {nombre_proveedor.upper()} ---")
            
            # Formatear la variación para la visualización en la tabla
            def format_variacion(v):
                if pd.notna(v) and v != 0.0:
                    variacion_str = f"{abs(v):.1f}%".replace('.', ',')
                    return f"({variacion_str})" if v < 0 else f"+{variacion_str}"
                return ''

            df_display = df_filtrado[['Producto y Descripcion', 'Precio', '% Variacion']].copy()
            df_display['% Variacion'] = df_display['% Variacion'].apply(format_variacion)
            df_display['Precio'] = df_display['Precio'].apply(lambda p: f"${int(p):,}".replace(',', '.'))
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.warning("😔 No se encontraron productos que coincidan con las palabras clave.")
