import os
import urllib.parse
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


def sanitize_db_url(raw_url):
    """Sanitize and encode DATABASE_URL for robust PostgreSQL / SQLAlchemy parsing."""
    if not raw_url:
        return None
    url = raw_url.strip().strip("'\"")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    try:
        if "://" in url and "@" in url:
            scheme, rest = url.split("://", 1)
            user_pass, host_db = rest.rsplit("@", 1)
            if ":" in user_pass:
                user, password = user_pass.split(":", 1)
                password = urllib.parse.unquote(password)
                quoted_password = urllib.parse.quote(password, safe="")
                url = f"{scheme}://{user}:{quoted_password}@{host_db}"
    except Exception:
        pass

    if ("supabase.com" in url or "supabase.co" in url) and "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"

    return url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    _raw_db_url = sanitize_db_url(os.environ.get('DATABASE_URL'))

    SQLALCHEMY_DATABASE_URI = _raw_db_url or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")

