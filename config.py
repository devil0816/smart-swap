import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

# Load environment variables from .env file
load_dotenv(os.path.join(basedir, '.env'))

# Determine database URI (Supabase PostgreSQL or fallback SQLite)
raw_db_url = os.environ.get('DATABASE_URL') or os.environ.get('SUPABASE_DB_URL')
if raw_db_url:
    # Supabase connection URIs may use 'postgres://' which SQLAlchemy 1.4+ deprecates in favor of 'postgresql://'
    if raw_db_url.startswith('postgres://'):
        database_uri = raw_db_url.replace('postgres://', 'postgresql://', 1)
    else:
        database_uri = raw_db_url
    
    # Auto-clean: remove accidental square brackets around password if left from [YOUR-PASSWORD]
    import re
    database_uri = re.sub(r':\[([^\]]+)\]@', r':\1@', database_uri)
else:
    database_uri = 'sqlite:///' + os.path.join(basedir, 'smart_swap.db')


# Determine environment mode
is_debug = os.environ.get('FLASK_DEBUG', 'True').lower() in ('1', 'true', 'yes')


class Config:
    # In production (FLASK_DEBUG=False), reject hardcoded fallback and enforce environment SECRET_KEY
    if not is_debug:
        secret = os.environ.get('SECRET_KEY')
        if not secret:
            raise ValueError("CRITICAL SECURITY ERROR: SECRET_KEY environment variable must be set in production mode!")
        SECRET_KEY = secret
    else:
        SECRET_KEY = os.environ.get('SECRET_KEY') or 'smart-swap-dev-secret-key-2026-exchange-platform'

    SQLALCHEMY_DATABASE_URI = database_uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Engine connection options (essential for cloud databases like Supabase)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,     # Automatically reconnects if connection was dropped by cloud pooler
        'pool_recycle': 300,       # Recycle connections every 5 minutes to avoid idle timeouts
    }
    
    # Session & Cookie Security Hardening (Enforce Secure flag in production HTTPS)
    SESSION_COOKIE_SECURE = not is_debug
    REMEMBER_COOKIE_SECURE = not is_debug
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    
    # Upload configuration
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    AVATAR_FOLDER = os.path.join(basedir, 'static', 'uploads', 'avatars')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB max upload
    
    # Platform settings
    ITEMS_PER_PAGE = 12
