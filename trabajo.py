import pandas as pd
import streamlit as st
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
from geopy.distance import geodesic
from opencage.geocoder import OpenCageGeocode

# Función para cargar los datos de los centros de discapacidad
def load_centros(filepath):
    try:
        return pd.read_csv(filepath, sep=';', encoding='utf-8')
    except pd.errors.ParserError as e:
        st.error(f"Error leyendo el archivo {filepath}: {e}")
        return pd.read_csv(filepath, sep=';', encoding='utf-8', error_bad_lines=False)

# Función para dividir la columna 'geo_point_2d' en 'x' e 'y'
def split_geo_point(df):
    if 'geo_point_2d' not in df.columns:
        raise KeyError("La columna 'geo_point_2d' no está presente en el DataFrame")
    df[['y', 'x']] = df['geo_point_2d'].str.split(',', expand=True).astype(float)
    return df

# Cargar los datos de los centros de discapacidad
centros_fisica = load_centros('discapacitat-fisica-discapacidad-fisica.csv')
centros_fisica = split_geo_point(centros_fisica)

centros_sensorial = load_centros('discapacitat-sensorial-discapacidad-sensorial.csv')
centros_sensorial = split_geo_point(centros_sensorial)

centros_intelectual = load_centros('discapacitat-intellectual-discapacidad-intelectual.csv')
centros_intelectual = split_geo_point(centros_intelectual)

# Cargar los datos de los parkings de movilidad reducida
parkings_mr = load_centros('aparcaments-persones-mobilitat-reduida-aparcamientos-personas-movilidad-reducida.csv')
parkings_mr = split_geo_point(parkings_mr)

# Configuración de la página de Streamlit
st.set_page_config(page_title="Centros de Discapacidad y Parkings", layout="wide")

# Título de la aplicación
st.markdown("<h1 style='text-align: center; color: #4CAF50;'>Centros de Discapacidad y Parkings de Movilidad Reducida</h1>", unsafe_allow_html=True)

# Descripción de la aplicación
st.markdown("""
<div style='text-align: center;'>
    <p>Esta aplicación te ayudará a encontrar centros de discapacidad y parkings de movilidad reducida cercanos.</p>
    <p>Puedes buscar un centro específico o una dirección, de forma que te mostraremos los parkings cercanos y la distancia.</p>
</div>
""", unsafe_allow_html=True)

# Selección del tipo de búsqueda
tipo_busqueda = st.sidebar.radio("Seleccione el tipo de búsqueda", ["Centro específico", "Dirección"])

# Selector de tipo de discapacidad
tipo_discapacidad = st.sidebar.selectbox("Seleccione el tipo de discapacidad", ["Física", "Sensorial", "Intelectual"])

# Filtrar datos según tipo de discapacidad
if tipo_discapacidad == "Física":
    centros = centros_fisica
elif tipo_discapacidad == "Sensorial":
    centros = centros_sensorial
else:
    centros = centros_intelectual

# Radio de búsqueda
radio_busqueda = st.sidebar.slider("Radio de búsqueda (metros)", min_value=50, max_value=2000, step=50, value=500)

# OpenCage API key
opencage_key = 'f1c6a77fb5fb4e5aa55916161cff9d35'  # Reemplaza con tu clave API de OpenCage
geocoder = OpenCageGeocode(opencage_key)

# Función para encontrar parkings cercanos
def find_nearby_parkings(parkings, radio, centro_seleccionado_coords):
    nearby_parkings = []
    for _, parking in parkings.iterrows():
        parking_coords = (parking['y'], parking['x'])
        distance = geodesic(centro_seleccionado_coords, parking_coords).meters
        if distance <= radio:
            parking['Distancia al centro (en metros)'] = distance
            nearby_parkings.append(parking)
    
    if nearby_parkings:
        return pd.DataFrame(nearby_parkings).drop_duplicates()
    else:
        return pd.DataFrame(columns=['Nombre Places / Número Plazas', 'geo_point_2d', 'Distancia al centro (en metros)'])  # Retornar un DataFrame vacío si no se encuentran parkings cercanos

# Función para encontrar centros cercanos a una dirección
def find_nearest_centro(address, centros):
    result = geocoder.geocode(address)
    if not result:
        return pd.DataFrame(), None  # Retornar DataFrame vacío si no se encuentra la dirección
    
    user_coords = (result[0]['geometry']['lat'], result[0]['geometry']['lng'])
    centros['distance'] = centros.apply(lambda row: geodesic(user_coords, (row['y'], row['x'])).meters if pd.notnull(row['y']) and pd.notnull(row['x']) else float('inf'), axis=1)
    nearest_centro = centros.loc[centros['distance'].idxmin()]
    return nearest_centro, user_coords

# Mostrar los resultados en función del tipo de búsqueda
if tipo_busqueda == "Centro específico":
    centro_especifico_nombre = st.sidebar.selectbox("Seleccione el centro", centros['equipamien'].unique())
    centro_seleccionado = centros[centros['equipamien'] == centro_especifico_nombre].iloc[0]
    centro_seleccionado_coords = (centro_seleccionado['y'], centro_seleccionado['x'])
    parkings_cercanos = find_nearby_parkings(parkings_mr, radio_busqueda, centro_seleccionado_coords)
    
    # Mostrar el nombre del centro
    st.header(f"Centro Seleccionado: {centro_especifico_nombre}")
    
    # Crear el mapa
    m = folium.Map(location=[centro_seleccionado['y'], centro_seleccionado['x']], zoom_start=14)
    
    # Agregar el centro seleccionado al mapa
    folium.Marker(
        location=[centro_seleccionado['y'], centro_seleccionado['x']],
        popup=f"{centro_especifico_nombre}",
        icon=folium.Icon(color='blue', icon='info-sign', prefix='fa')
    ).add_to(m)

    # Agregar parkings al mapa
    parkings_cluster = MarkerCluster(name="Parkings de Movilidad Reducida").add_to(m)
    for _, parking in parkings_cercanos.iterrows():
        folium.Marker(
            location=[parking['y'], parking['x']],
            popup=f"Parking - {parking['Nombre Places / Número Plazas']}",
            icon=folium.Icon(color='green', icon='car', prefix='fa')
        ).add_to(parkings_cluster)
    
    # Mostrar el mapa en Streamlit
    folium_static(m)
    
    # Mostrar los datos en tabla
    st.subheader("Parkings Cercanos")
    if not parkings_cercanos.empty:
        parkings_cercanos = parkings_cercanos.rename(columns={'geo_point_2d': 'Coordenadas de la plaza'})
        st.dataframe(parkings_cercanos[['Nombre Places / Número Plazas', 'Coordenadas de la plaza', 'Distancia al centro (en metros)']])
    else:
        st.info("No se encontraron parkings cercanos.")

elif tipo_busqueda == "Dirección":
    direccion = st.sidebar.text_input("Ingrese la dirección:")
    if direccion:
        nearest_centro, user_coords = find_nearest_centro(direccion, centros)
        if not nearest_centro.empty:
            # Crear el mapa
            m = folium.Map(location=[user_coords[0], user_coords[1]], zoom_start=14)

            # Agregar la dirección al mapa
            folium.Marker(
                location=[user_coords[0], user_coords[1]],
                popup=f"Dirección: {direccion}",
                icon=folium.Icon(color='blue', icon='info-sign', prefix='fa')
            ).add_to(m)

            # Agregar el centro más cercano al mapa
            folium.Marker(
                location=[nearest_centro['y'], nearest_centro['x']],
                popup=f"{nearest_centro['equipamien']}",
                icon=folium.Icon(color='red', icon='info-sign', prefix='fa')
            ).add_to(m)

            # Buscar parkings cercanos al centro más cercano
            parkings_cercanos = find_nearby_parkings(parkings_mr, radio_busqueda, (nearest_centro['y'], nearest_centro['x']))
            
            # Mostrar los parkings cercanos en el mapa
            parkings_cluster = MarkerCluster(name="Parkings de Movilidad Reducida").add_to(m)
            for _, parking in parkings_cercanos.iterrows():
                    folium.Marker(
                    location=[parking['y'], parking['x']],
                    popup=f"Parking - {parking['Nombre Places / Número Plazas']}",
                    icon=folium.Icon(color='green', icon='car', prefix='fa')
                ).add_to(parkings_cluster)
            
            # Mostrar el mapa en Streamlit
            folium_static(m)
            
            # Mostrar los parkings cercanos en tabla
            st.subheader(f"Parkings Cercanos al Centro más Cercano: {nearest_centro['equipamien']}")
            if not parkings_cercanos.empty:
                parkings_cercanos = parkings_cercanos.rename(columns={'geo_point_2d': 'Coordenadas de la plaza'})
                st.dataframe(parkings_cercanos[['Nombre Places / Número Plazas', 'Coordenadas de la plaza', 'Distancia al centro (en metros)']])
            else:
                st.info("No se encontraron parkings cercanos.")
            
            # Mostrar la distancia desde la dirección ingresada al centro más cercano
            st.sidebar.markdown(f"Distancia al centro más cercano: {nearest_centro['distance']/1000:.2f} km")
        else:
            st.error("No se encontró la dirección especificada.")
