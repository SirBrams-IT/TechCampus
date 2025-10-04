import os
from pathlib import Path
from decouple import config
import environ
import cloudinary
import cloudinary.uploader
import cloudinary.api


BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env()

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}


# 🔐 Secrets & API Keys
SECRET_KEY = config("SECRET_KEY")

GETOTP_BASE_URL = config("GETOTP_BASE_URL")
GETOTP_API_KEY = config("GETOTP_API_KEY")
GETOTP_AUTH_TOKEN = config("GETOTP_AUTH_TOKEN")

# 🚨 Security
DEBUG = False

AUTH_USER_MODEL = "TechApp.User"

USE_X_FORWARDED_HOST = True
ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "techcampus-r82w.onrender.com",
]

PORT = os.getenv("PORT", "8000")

# 📦 Installed Apps
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "daphne",
    "django.contrib.staticfiles",
    "channels",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "TechApp", # Handles the rest of functionality
    "ChatApp", #for messaging
    "cloudinary",
    "cloudinary_storage", 
    
]

SITE_ID = 1

# used for Google login too
LOGIN_REDIRECT_URL = "post_login_redirect"  
LOGOUT_REDIRECT_URL = "login"


# ⚙️ Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # ✅ Static files for production
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "TechCampuss.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # ✅ where 404.html / 500.html will live
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Use database cache as it's more reliable than local memory cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache_table',
    }
}

# Detect environment
ENVIRONMENT = os.environ.get("DJANGO_ENV", "development")  # default is development

ENVIRONMENT = os.environ.get("DJANGO_ENV", "development")

if ENVIRONMENT == "production":
    REDIS_URL = os.environ.get("REDIS_URL")
    if not REDIS_URL:
        raise ValueError("REDIS_URL is required in production")
    
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [REDIS_URL],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }


WSGI_APPLICATION = "TechCampuss.wsgi.application"
ASGI_APPLICATION = 'TechCampuss.asgi.application'

# 📦 Database (MySQL from Aiven)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="3306"),
    }
}

# 🔑 Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


#google env
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": config("GOOGLE_CLIENT_ID"),
            "secret": config("GOOGLE_CLIENT_SECRET"),
            "key": "",
        },
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
    }
}

SOCIALACCOUNT_ADAPTER = "TechApp.adapters.CustomSocialAccountAdapter"

# Recommended allauth settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True  # if you want usernames
ACCOUNT_UNIQUE_EMAIL = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"


# 🌍 Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# 🗂️ Static & Media Files Configuration
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ✅ Cloudinary media configuration
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

# (Optional fallback if Cloudinary is unavailable)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 26214400  # 25MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 26214400  # 25MB
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# 📧 Email Config
DEFAULT_FROM_EMAIL = 'SirBrams Tech Virtual Campus Support <no-reply@sirbramstech.com>'
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_USE_SSL = config("EMAIL_USE_SSL", default=False, cast=bool)

# M-Pesa Configuration
MPESA_CONSUMER_KEY = config("MPESA_CONSUMER_KEY", default="")
MPESA_CONSUMER_SECRET = config("MPESA_CONSUMER_SECRET", default="")
MPESA_BUSINESS_SHORTCODE = config("MPESA_BUSINESS_SHORTCODE", default="174379")
MPESA_PASSKEY = config("MPESA_PASSKEY", default="bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919")

# 🔐 CSRF
CSRF_TRUSTED_ORIGINS = [
    "https://techcampus-r82w.onrender.com",
    "http://techcampus-r82w.onrender.com",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# 🌩️ Cloudinary credentials (from .env)
cloudinary.config( 
    cloud_name = config("CLOUDINARY_CLOUD_NAME"), 
    api_key = config("CLOUDINARY_API_KEY"), 
    api_secret = config("CLOUDINARY_API_SECRET"), 
    secure = True
)

