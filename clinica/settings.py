"""
Configuración del Sistema Web de Gestión para la Clínica Veterinaria.

Todas las credenciales se leen del archivo .env (ver .env.example), de modo que
ninguna contraseña queda escrita en el código fuente (RNF-04, sección 6.1.4).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def env_bool(nombre, por_defecto=False):
    valor = os.environ.get(nombre)
    if valor is None:
        return por_defecto
    return valor.strip().lower() in ('1', 'true', 'si', 'sí', 'yes', 'on')


def env_list(nombre, por_defecto=''):
    return [x.strip() for x in os.environ.get(nombre, por_defecto).split(',') if x.strip()]


# ---------------------------------------------------------------------------
# Seguridad
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get('SECRET_KEY', 'solo-para-desarrollo-cambie-esta-clave')
DEBUG = env_bool('DEBUG', True)
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', '')

# ---------------------------------------------------------------------------
# Aplicaciones (una aplicación Django por módulo, Tabla 5.6)
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Terceros
    'crispy_forms',
    'crispy_bootstrap5',
    # Módulos del sistema
    'usuarios',
    'pacientes',
    'citas',
    'notificaciones',
    'reportes',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Sirve los archivos estáticos (CSS/JS) también con DEBUG=False
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Toda página exige sesión iniciada, salvo las marcadas con @login_not_required (RNF-03)
    'django.contrib.auth.middleware.LoginRequiredMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'clinica.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'clinica' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'clinica.context_processors.datos_generales',
            ],
        },
    },
]

WSGI_APPLICATION = 'clinica.wsgi.application'

# ---------------------------------------------------------------------------
# Base de datos: MySQL en producción, SQLite opcional en desarrollo (Tabla 3.6)
# ---------------------------------------------------------------------------
DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite').lower()

if DB_ENGINE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'clinica_veterinaria'),
            'USER': os.environ.get('DB_USER', 'root'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Contraseñas (PBKDF2 por defecto en Django, RF-04)
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'
SESSION_COOKIE_AGE = 60 * 60 * 10          # La sesión dura una jornada (10 horas)
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# ---------------------------------------------------------------------------
# Idioma y zona horaria
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Guatemala'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Archivos estáticos
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'clinica' / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ---------------------------------------------------------------------------
# Formularios (Django Crispy Forms con Bootstrap 5)
# ---------------------------------------------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# Clases CSS de Bootstrap para los mensajes de Django
from django.contrib.messages import constants as message_constants  # noqa: E402

MESSAGE_TAGS = {
    message_constants.DEBUG: 'secondary',
    message_constants.INFO: 'info',
    message_constants.SUCCESS: 'success',
    message_constants.WARNING: 'warning',
    message_constants.ERROR: 'danger',
}

# ---------------------------------------------------------------------------
# Correo electrónico (sección 6.1.6). La configuración también puede
# cambiarse desde el sistema: Administración > Configuración de correo (RF-17).
# ---------------------------------------------------------------------------
if os.environ.get('EMAIL_MODO', 'smtp').lower() == 'console':
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_HOST_USER = os.environ.get('EMAIL_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or 'no-responder@clinica.local'

# ---------------------------------------------------------------------------
# Parámetros propios del sistema
# ---------------------------------------------------------------------------
CLINICA_NOMBRE = os.environ.get('CLINICA_NOMBRE', 'Clínica Veterinaria')
CLINICA_TELEFONO = os.environ.get('CLINICA_TELEFONO', '')
CLINICA_DIRECCION = os.environ.get('CLINICA_DIRECCION', 'Amatitlán, Guatemala')
CITA_DURACION_MINUTOS = int(os.environ.get('CITA_DURACION_MINUTOS', '30'))

# ---------------------------------------------------------------------------
# Seguridad adicional cuando DEBUG=False (producción)
# ---------------------------------------------------------------------------
if not DEBUG:
    SESSION_COOKIE_HTTPONLY = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_CONTENT_TYPE_NOSNIFF = True
    # Active estas dos líneas cuando el sitio funcione con HTTPS (sección 6.1.7)
    SESSION_COOKIE_SECURE = env_bool('USAR_HTTPS', False)
    CSRF_COOKIE_SECURE = env_bool('USAR_HTTPS', False)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'consola': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'notificaciones': {'handlers': ['consola'], 'level': 'INFO'},
    },
}
