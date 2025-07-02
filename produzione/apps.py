from django.apps import AppConfig

class ProduzioneConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'produzione'

    def ready(self):
        import produzione.signals

