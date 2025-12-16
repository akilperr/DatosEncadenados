import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import base64

# ===============================
# CONFIG
# ===============================
st.set_page_config(
    page_title="DataRun – Visualización",
    layout="wide"
)

st.title("DataRun – Recomendación de parques para correr")

def set_background(image_file):
    with open(image_file, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
def set_background(image_file):
    with open(image_file, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    
    st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url("data:image/jpg;base64,{encoded}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}

    /* Contenedor principal */
    .block-container {{
        background-color: rgba(255, 255, 255, 0.85);
        padding: 2rem;
        border-radius: 10px;
        max-width: 82%;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

   
    
# Aplicar fondo
set_background("background.jpg")

# ===============================
# FUNCIONES AUXILIARES
# ===============================

def interpretar_clima(score):
    if score >= 30:
        return "🌞 Muy buen tiempo (sin lluvia significativa)"
    elif score >= 20:
        return "🌤 Buen tiempo (con nubosidad)"
    elif score >= 10:
        return "🌥 Tiempo regular (precaución)"
    else:
        return "🌧 Mal tiempo (lluvia o temperaturas adversas)"


# ===============================
# CARGA DE DATOS
# ===============================
try:
    df = pd.read_csv("datarun_dashboard.csv")
except FileNotFoundError:
    st.error("No se encontró el archivo de resultados. Ejecuta primero consulta.py.")
    st.stop()

if df.empty:
    st.error("El archivo de resultados está vacío.")
    st.stop()

# Mejor parque
best = df.sort_values("final_score", ascending=False).iloc[0]
user_lat = best["user_lat"]
user_lon = best["user_lon"]

# ===============================
# LAYOUT
# ===============================
col1, col2 = st.columns([2, 1])

# ===============================
# MAPA
# ===============================
with col1:
    st.subheader("Mapa interactivo")

    m = folium.Map(
        location=[best["location_lat"], best["location_lon"]],
        zoom_start=13
    )

    # Marcador usuario
    folium.Marker(
        [user_lat, user_lon],
        popup="Tu ubicación",
        icon=folium.Icon(color="blue", icon="user")
    ).add_to(m)

    # Marcador parque
    folium.Marker(
        [best["location_lat"], best["location_lon"]],
        popup=f"{best['name']}",
        icon=folium.Icon(color="green", icon="tree")
    ).add_to(m)

    st_folium(m, width=800, height=500)

# ===============================
# INFO DETALLADA
# ===============================
with col2:
    st.subheader("Detalles del parque recomendado")
    st.write("")
    st.write("")
    st.write("")
    # Nombre del parque (ligeramente grande)
    st.markdown(
        f"""
        <div style="font-size:20px; font-weight:600; margin-bottom:4px;">
            {best['name']}
        </div>
        """,
        unsafe_allow_html=True
    )

    # Dirección
    st.markdown(
        f"""
        <div style="font-size:14px; color:#555; margin-bottom:8px;">
            <b>Dirección:</b> {best['address']}
        </div>
        """,
        unsafe_allow_html=True
    )

    # Distancia + tiempo (misma línea)
    st.markdown(
        f"""
        <div style="font-size:15px; line-height:1.4; margin-bottom:4px;">
             <b>Distancia:</b> {best['distance_km']:.2f} km
            &nbsp;&nbsp;|&nbsp;&nbsp;
             <b>Tiempo:</b> {best['route_minutes']:.1f} min
        </div>
        """,
        unsafe_allow_html=True
    )

    # Elevación
    st.markdown(
        f"""
        <div style="font-size:15px; line-height:1.4; margin-bottom:8px;">
            <b>Elevación:</b> {best['elevation']:.2f} m
            (<i>{best['elevation_category']}</i>)
        </div>
        """,
        unsafe_allow_html=True
    )

    # Clima
    st.markdown(
        f"""
        <div style="font-size:14px; margin-bottom:6px;">
             <b>Clima:</b> {interpretar_clima(best['weather_score'])}
        </div>
        """,
        unsafe_allow_html=True
    )

    # Score final
    st.markdown(
        f"""
        <div style="font-size:14px; font-weight:500;">
             <b>Score final:</b> {best['final_score']}
        </div>
        """,
        unsafe_allow_html=True
    )

    # Fecha
    st.markdown(
        f"""
        <div style="font-size:12px; color:#777; margin-top:6px;">
            📅 Día analizado: {best['day']}
        </div>
        """,
        unsafe_allow_html=True
    )
# ===============================
# FOOTER
# ===============================
st.markdown("---")
st.caption("DataRun · Prueba de concepto · Integración de datos masivos")