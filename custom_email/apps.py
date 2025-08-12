from django.apps import AppConfig

class CustomEmailConfig(AppConfig):
    name = 'custom_email'

    def ready(self):
        from . import signals