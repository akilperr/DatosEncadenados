"""
ETL de parques/jardines del Ayuntamiento de Madrid hacia MongoDB.

E: Extrae datos de la API de datos.madrid.es (parques y jardines)
T: Transforma al esquema que usará DataRun
L: Carga en la colección 'parks' de la BD 'datarun' en MongoDB
"""

import requests
from pymongo import MongoClient

# ==========================
# CONFIGURACIÓN
# ==========================

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "datarun"
PARKS_COLLECTION = "parks"

# URL de ejemplo de parques/jardines del Ayto. de Madrid (puedes cambiarla por la oficial que uséis)
PARKS_URL = (
    "https://datos.madrid.es/egob/catalogo/200761-0-parques-jardines.json"
)

# Opcional: límite de registros (para pruebas)
MAX_PARKS = 200  # None para todos


# ==========================
# CONEXIÓN MONGO
# ==========================

def get_mongo_client():
    return MongoClient(MONGO_URI)


# ==========================
# EXTRACT
# ==========================

def extract_parks():
    """
    Llama a la API del Ayuntamiento y devuelve la lista bruta de parques.
    El formato típico de datos.madrid.es es un JSON con un array '@graph'.
    """
    params = {
        "format": "json"
    }

    print("Descargando datos de parques desde datos.madrid.es...")
    resp = requests.get(PARKS_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    parks_raw = data.get("@graph", [])
    if MAX_PARKS:
        parks_raw = parks_raw[:MAX_PARKS]

    print(f"  -> Extraídos {len(parks_raw)} registros brutos.")
    return parks_raw


# ==========================
# TRANSFORM
# ==========================

def transform_park(raw):
    """
    Transforma un registro bruto de la API al esquema interno de DataRun.
    Estructura objetivo:

    {
      "name": "Parque del Retiro",
      "address": "Calle X...",
      "location": { "type": "Point", "coordinates": [lon, lat] },
      "source": "datos.madrid.es"
    }
    """

    name = raw.get("title")

    # Dirección
    address_info = raw.get("address", {})
    address = address_info.get("street-address")

    # Coordenadas
    location_info = raw.get("location", {})
    lat = location_info.get("latitude")
    lon = location_info.get("longitude")

    # Algunos registros pueden no tener coordenadas; los ignoramos
    if lat is None or lon is None:
        return None

    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return None

    park_doc = {
        "name": name,
        "address": address,
        "location": {
            "type": "Point",
            "coordinates": [lon, lat]   # GeoJSON: [longitud, latitud]
        },
        "source": "datos.madrid.es"
    }

    # Podemos añadir equipamiento si viene en el JSON
    equipment = raw.get("equipment")
    if equipment:
        park_doc["equipment"] = equipment

    # Horario si existe
    schedule = raw.get("schedule")
    if schedule:
        park_doc["schedule"] = schedule

    return park_doc


def transform_parks(parks_raw):
    """
    Aplica transform_park a todos los registros brutos
    y filtra los que no se pueden transformar (sin coordenadas, etc.).
    """
    transformed = []
    for raw in parks_raw:
        doc = transform_park(raw)
        if doc is not None:
            transformed.append(doc)

    print(f"  -> Transformados {len(transformed)} registros válidos.")
    return transformed


# ==========================
# LOAD
# ==========================

def load_parks_to_mongo(parks_docs, drop_before=True):
    """
    Carga los documentos de parques en MongoDB.
    drop_before=True borra previamente la colección (para recargas ETL).
    """
    client = get_mongo_client()
    db = client[DB_NAME]
    col = db[PARKS_COLLECTION]

    if drop_before:
        print("Eliminando colección anterior de parques (si existe)...")
        col.drop()

    if not parks_docs:
        print("No hay parques que cargar.")
        return

    result = col.insert_many(parks_docs)
    print(f"  -> Insertados {len(result.inserted_ids)} parques en MongoDB.")

    # Creamos un índice geoespacial sobre 'location' para futuras consultas
    col.create_index([("location", "2dsphere")])
    print("  -> Índice geoespacial creado sobre 'location'.")


# ==========================
# PIPELINE ETL COMPLETO
# ==========================

def run_etl_parks():
    parks_raw = extract_parks()
    parks_docs = transform_parks(parks_raw)
    load_parks_to_mongo(parks_docs)


if __name__ == "__main__":
    run_etl_parks()
    print("ETL de parques finalizado correctamente.")