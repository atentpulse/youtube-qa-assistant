import os
import httpx
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv

from app.core.config import settings

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID") or settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET") or settings.GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI") or settings.GOOGLE_REDIRECT_URI

if not GOOGLE_CLIENT_ID:
    raise ValueError("GOOGLE_CLIENT_ID is not set in the .env file")

if not GOOGLE_CLIENT_SECRET:
    raise ValueError("GOOGLE_CLIENT_SECRET is not set in the .env file")

if not GOOGLE_REDIRECT_URI:
    raise ValueError("GOOGLE_REDIRECT_URI is not set in the .env file")


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
