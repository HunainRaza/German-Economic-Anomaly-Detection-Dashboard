import environ
from core.settings.common import *

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# Initialize environment variables
env = environ.Env(
    # Set default values with production-appropriate settings
    # DEBUG=(bool, False),
    SECRET_KEY=(str, ''),  # Use a strong, unique secret key
    ALLOWED_HOSTS=(list, []),
    DB_NAME=(str, ''),
    DB_USER=(str, ''),
    DB_PASSWORD=(str, ''),
    DB_HOST=(str, ''),
    DB_PORT=(str, '5432'),
)

# Read .env file if it exists
environ.Env.read_env(os.path.join(BASE_DIR, 'dev.env'))

SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS=["*"]

# Database Configuration - Supabase PostgreSQL
DATABASES = {
    'default': {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": env('DB_NAME'),
        "USER": env('DB_USER'),
        "PASSWORD": env('DB_PASSWORD'),
        "HOST": env('DB_HOST'),
        "PORT": env('DB_PORT', default='5432'),
        'ATOMIC_REQUESTS': True
    }
}