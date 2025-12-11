from django.apps import AppConfig


class IndicatorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'indicators'
    
    def ready(self):
        """
        Initialize app components after Django is ready.
        Skip dash app during migrations for clean database operations.
        """
        import sys
        
        # Skip dash initialization during database operations
        skip_commands = ['makemigrations', 'migrate', 'createsuperuser', 'flush']
        if any(cmd in sys.argv for cmd in skip_commands):
            return
        
        # Safe to import now - dash_apps.py uses dynamic layout (no module-level DB queries)
        try:
            from . import dash_apps
        except Exception as e:
            # Log but don't crash - allows Django to start even if dash has issues
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not initialize dash app: {e}")
