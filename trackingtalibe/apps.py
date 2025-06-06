from django.apps import AppConfig
import threading

class TrackingtalibeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'trackingtalibe'
def ready(self):
    import trackingtalibe.signals

class TrackingtalibeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'trackingtalibe'

    def ready(self):
        from .reinitialiser import appliquer_reinitialisation
        t = threading.Thread(target=appliquer_reinitialisation, daemon=True)
        t.start()