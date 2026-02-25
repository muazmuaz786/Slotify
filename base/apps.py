from django.apps import AppConfig


class BaseConfig(AppConfig):
    name = 'base'

    def ready(self):
        # Register signal handlers
        import base.signals  # noqa: F401
