import os, json, time
from datetime import datetime, timedelta
from django.conf import settings
import threading

def reinitialiser_fichier():
    file_path = os.path.join('data/latlng.json')
    # Charger les positions existantes
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            positions = json.load(f)
    else:
        positions = {}

    # Nouvelle position à appliquer à tous les ESP32
    lat = 14.692425
    lon = -16.466784

    # Réinitialiser chaque id_esp32
    for id_esp32 in positions.keys():
        positions[id_esp32] = {
            'latitude': round(lat, 6),
            'longitude': round(lon, 6),
            'timestamp': datetime.now().isoformat()
        }

    # Sauvegarder
    with open(file_path, 'w') as f:
        json.dump(positions, f, indent=2)
    print(f"[{datetime.now()}] ➤ latlng.json réinitialisé pour tous les ESP32.")

def delai():
    now = datetime.now()
    target = now.replace(hour=1, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return (target - now).total_seconds()

def appliquer_reinitialisation():
    while True:
        wait_time = delai()
        print(f"Attente de {int(wait_time)} secondes avant le reset de latlng.json")
        time.sleep(wait_time)
        reinitialiser_fichier()
