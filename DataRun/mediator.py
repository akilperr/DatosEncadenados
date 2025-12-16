"""
Mediador de DataRun
--------------------
Este módulo actúa como capa de integración virtual: consulta
en tiempo real las APIs necesarias y devuelve datos normalizados.
"""

import requests
from datetime import datetime, timedelta


# =============== CONFIG ===============

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
GOOGLE_ELEVATION_URL = "https://maps.googleapis.com/maps/api/elevation/json"
GOOGLE_DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"

GOOGLE_API_KEY = "AIzaSyAHYvig6NG0s88m--HfLg5hplCiuRBHPTQ"    # <-- pon tu API KEY


# =============== MÉTODOS DEL MEDIADOR ===============


def get_weather_score_for_date(lat, lon, date):
    """
    Obtiene la previsión horaria SOLO del día seleccionado por el usuario.
    Devuelve un score de "buen clima para correr" en ese día concreto.
    """

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation",
        "start_date": date.isoformat(),
        "end_date": date.isoformat(),
        "timezone": "Europe/Madrid"
    }

    r = requests.get(OPEN_METEO_URL, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    temps = data["hourly"]["temperature_2m"]
    precs = data["hourly"]["precipitation"]

    score = 0

    for t, p in zip(temps, precs):
        if p > 2:  # lluvia fuerte
            continue
        if 10 <= t <= 24:
            score += 2
        elif 5 <= t < 10 or 24 < t <= 28:
            score += 1

    return score

def get_elevation(lat, lon):
    """
    Obtiene elevación media usando Google Elevation.
    Categoriza el terreno para el informe final del análisis.
    """

    params = {
        "locations": f"{lat},{lon}",
        "key": GOOGLE_API_KEY
    }

    r = requests.get(GOOGLE_ELEVATION_URL, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    if not data.get("results"):
        return None, "desconocido"

    elevation = data["results"][0]["elevation"]

    # Clasificación simple:
    if elevation < 650:
        cat = "llano"
    elif elevation < 750:
        cat = "moderado"
    else:
        cat = "elevado"

    return elevation, cat


def get_best_route(user_lat, user_lon, park_lat, park_lon):
    """
    Servicio externo funcional obligatorio:
    Google Directions API para ruta más cómoda.
    Retorna duración estimada (minutos).
    """

    params = {
        "origin": f"{user_lat},{user_lon}",
        "destination": f"{park_lat},{park_lon}",
        "mode": "walking",
        "key": GOOGLE_API_KEY
    }

    r = requests.get(GOOGLE_DIRECTIONS_URL, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    if not data.get("routes"):
        return None

    leg = data["routes"][0]["legs"][0]
    duration_sec = leg["duration"]["value"]

    return duration_sec / 60.0  # minutos
