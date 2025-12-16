"""
consulta.py
---------------------------------------
Interfaz lógica de DataRun.

- Permite seleccionar el día
- Usa una ubicación de salida (por defecto Puerta del Sol)
- Calcula el mejor parque para correr
- Exporta resultados para Google Data Studio / Looker
"""

import math
import csv
from datetime import datetime, timedelta
from pymongo import MongoClient

# Funciones del mediador
from mediator import (
    get_weather_score_for_date,
    get_elevation,
    get_best_route
)

# ===================================
# CONFIGURACIÓN
# ===================================

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "datarun"
PARKS_COLLECTION = "parks"

# Ubicación por defecto → Puerta del Sol
DEFAULT_LAT = 40.4168
DEFAULT_LON = -3.7038


# ===================================
# HERRAMIENTAS AUXILIARES
# ===================================

def haversine_km(lat1, lon1, lat2, lon2):
    """Distancia geográfica aproximada en km."""
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)

    return 2 * R * math.asin(math.sqrt(a))


def get_mongo_client():
    return MongoClient(MONGO_URI)


# ===================================
# CONSULTA PRINCIPAL
# ===================================

def best_park_for_day(user_lat, user_lon, day_offset, max_distance_km=15):
    """
    Devuelve:
    - mejor parque recomendado
    - lista completa de candidatos (para dashboard)
    """

    client = get_mongo_client()
    db = client[DB_NAME]
    parks_col = db[PARKS_COLLECTION]

    parks = list(parks_col.find({}))
    total = len(parks)

    target_date = datetime.today().date() + timedelta(days=day_offset)
    print(f"\n[INFO] Consultando clima para el día {target_date}…")

    weather_score = get_weather_score_for_date(user_lat, user_lon, target_date)

    mejor = None
    candidatos = []

    print(f"[INFO] Procesando {total} parques…")

    for i, park in enumerate(parks, start=1):
        lon, lat = park["location"]["coordinates"]
        print(f"  → [{i}/{total}] {park['name']}")

        dist = haversine_km(user_lat, user_lon, lat, lon)
        if dist > max_distance_km:
            continue

        elevation, elevation_cat = get_elevation(lat, lon)
        route_min = get_best_route(user_lat, user_lon, lat, lon)

        # Score combinado
        score = weather_score
        score -= dist
        if route_min:
            score -= route_min / 10

        candidato = {
            "day": target_date.isoformat(),
            "user_lat": user_lat,
            "user_lon": user_lon,
            "name": park["name"],
            "address": park.get("address"),
            "location_lat": lat,
            "location_lon": lon,
            "distance_km": round(dist, 2),
            "route_minutes": None if not route_min else round(route_min, 1),
            "elevation": elevation,
            "elevation_category": elevation_cat,
            "weather_score": weather_score,
            "final_score": round(score, 2)
        }

        candidatos.append(candidato)

        if mejor is None or candidato["final_score"] > mejor["final_score"]:
            mejor = candidato

    return mejor, candidatos


# ===================================
# EXPORTACIÓN PARA DASHBOARD
# ===================================

def export_table_to_csv(rows, filename="datarun_dashboard.csv"):
    if not rows:
        return

    headers = rows[0].keys()

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[INFO] Tabla exportada → {filename}")


# ===================================
# INTERFAZ DE USUARIO (CONSOLA)
# ===================================

def elegir_dia():
    print("\n=== PLANIFICADOR DE CARRERA (DataRun) ===")
    print("\n¿Para qué día quieres recibir recomendación?")
    print("  1 → Hoy")
    print("  2 → Mañana")
    print("  3 → En 2 días")
    print("  4 → En 3 días")
    print("  5 → En 4 días")
    print("  6 → En 5 días")
    print("  7 → En 6 días")
    print("  8 → En 7 días")

    while True:
        try:
            n = int(input("\nIntroduce un número (1–8): "))
            if 1 <= n <= 8:
                return n - 1
        except:
            pass
        print("Entrada no válida. Intenta de nuevo.")


def elegir_ubicacion():
    print("\n=== UBICACIÓN DE SALIDA ===")
    print("Por defecto: Puerta del Sol (Madrid)")
    print(f"Lat: {DEFAULT_LAT} | Lon: {DEFAULT_LON}")

    resp = input("\n¿Quieres introducir otra ubicación? (s/n): ").strip().lower()

    if resp == "s":
        while True:
            try:
                lat = float(input("Introduce latitud: "))
                lon = float(input("Introduce longitud: "))
                return lat, lon
            except:
                print("Coordenadas no válidas. Inténtalo de nuevo.")
    else:
        return DEFAULT_LAT, DEFAULT_LON


# ===================================
# MAIN (solo para consola)
# ===================================

if __name__ == "__main__":

    day_offset = elegir_dia()
    user_lat, user_lon = elegir_ubicacion()

    print(f"\n[INFO] Ubicación usada: lat={user_lat}, lon={user_lon}")
    print(f"\n=== Buscando el mejor parque… ===\n")

    mejor, candidatos = best_park_for_day(user_lat, user_lon, day_offset)

    export_table_to_csv(candidatos)

    if mejor:
        print("\n🏃 RECOMENDACIÓN FINAL:")
        print(f"   🌳 Parque:        {mejor['name']}")
        print(f"   📍 Dirección:     {mejor['address']}")
        print(f"   📏 Distancia:     {mejor['distance_km']} km")
        print(f"   🚶 Ruta:          {mejor['route_minutes']} min")
        print(f"   ⛰  Elevación:     {mejor['elevation']} m ({mejor['elevation_category']})")
        print(f"   🌤  Score clima:   {mejor['weather_score']}")
        print(f"   ⭐ Score final:    {mejor['final_score']}\n")
    else:
        print("No se encontraron parques dentro del radio especificado.")
