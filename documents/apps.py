from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'documents'

    def ready(self):
        import logging
        # Suppress noisy PostHog logging from ChromaDB
        logging.getLogger("posthog").setLevel(logging.CRITICAL)
