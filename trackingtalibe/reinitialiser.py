import os, json, time
from datetime import datetime, timedelta
from django.conf import settings
import threading

def reinitialiser_fichier():
    file_path = os.path.join(settings.MEDIA_ROOT, 'positions.json')
    with open(file_path, 'w') as f:
        json.dump({}, f)
    print(f"[{datetime.now()}] ➤ positions.json réinitialisé.")

def delai():
    now = datetime.now()
    target = now.replace(hour=1, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return (target - now).total_seconds()

def appliquer_reinitialisation():
    while True:
        wait_time = delai()
        print(f"Attente de {int(wait_time)} secondes avant le reset de positions.json")
        time.sleep(wait_time)
        reinitialiser_fichier()
