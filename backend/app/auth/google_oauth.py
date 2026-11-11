import httpx
from authlib.integrations.starlette_client import OAuth

from app.core.config import settings

GOOGLE_CLIENT_ID = (settings.GOOGLE_CLIENT_ID or "").strip().strip("'\"")
GOOGLE_CLIENT_SECRET = (settings.GOOGLE_CLIENT_SECRET or "").strip().strip("'\"")
GOOGLE_REDIRECT_URI = (
    settings.GOOGLE_REDIRECT_URI
    or "http://localhost:8000/auth/google/callback"
).strip().strip("'\"").rstrip("/")

if not GOOGLE_CLIENT_ID:
    raise ValueError("GOOGLE_CLIENT_ID is not configured in settings")

if not GOOGLE_CLIENT_SECRET:
    raise ValueError("GOOGLE_CLIENT_SECRET is not configured in settings")

if not GOOGLE_REDIRECT_URI:
    raise ValueError("GOOGLE_REDIRECT_URI is not configured in settings")


oauth = OAuth()

oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
        "timeout": httpx.Timeout(20.0, connect=10.0),
    },
)
