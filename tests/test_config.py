import pytest
from pydantic import ValidationError
from app.core.config import Settings, INSECURE_DEFAULT_SECRET


def test_development_allows_default_secret():
    s = Settings(
        ENVIRONMENT="development",
        SECRET_KEY=INSECURE_DEFAULT_SECRET,
    )
    assert s.ENVIRONMENT == "development"
    assert s.SECRET_KEY == INSECURE_DEFAULT_SECRET


def test_production_rejects_default_insecure_secret():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=INSECURE_DEFAULT_SECRET,
        )
    assert "Insecure or default SECRET_KEY is prohibited in production" in str(exc_info.value)


def test_production_rejects_short_secret():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="short-secret-under-32-chars",
        )
    assert "at least 32 characters" in str(exc_info.value)


def test_production_accepts_strong_secret():
    strong_secret = "a" * 32
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY=strong_secret,
        DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
        FRONTEND_URL="https://ytgenius.example.com",
        GOOGLE_REDIRECT_URI="https://api.ytgenius.example.com/auth/google/callback",
    )
    assert s.ENVIRONMENT == "production"
    assert s.SECRET_KEY == strong_secret
    assert s.DATABASE_URL == "postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db"
    assert s.FRONTEND_URL == "https://ytgenius.example.com"
    assert s.GOOGLE_REDIRECT_URI == "https://api.ytgenius.example.com/auth/google/callback"


def test_production_rejects_localhost_database_url():
    strong_secret = "a" * 32
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=strong_secret,
            DATABASE_URL="postgresql://postgres:postgres@localhost:5432/youtube_qa_db",
            FRONTEND_URL="https://ytgenius.example.com",
        )
    assert "Production requires an explicit, non-localhost DATABASE_URL" in str(exc_info.value)


def test_production_rejects_localhost_frontend_url():
    strong_secret = "a" * 32
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=strong_secret,
            DATABASE_URL="postgresql://prod_user:pass@prod-db.internal:5432/ytgenius_db",
            FRONTEND_URL="http://localhost:3000",
        )
    assert "Production requires an explicit, non-localhost FRONTEND_URL" in str(exc_info.value)


def test_trusted_proxies_parsing():
    s = Settings(TRUSTED_PROXIES="10.0.0.1, 10.0.0.2 , 192.168.1.1")
    assert s.TRUSTED_PROXIES == ["10.0.0.1", "10.0.0.2", "192.168.1.1"]


def test_production_configuration_fields():
    """Verify new production database pool and session configuration defaults."""
    s = Settings()
    assert s.WORKERS == 4
    assert s.DB_POOL_SIZE == 5
    assert s.DB_MAX_OVERFLOW == 5
    assert s.DB_POOL_RECYCLE == 1800
    assert s.MAX_REQUEST_BODY_SIZE_BYTES == 10 * 1024 * 1024
    assert s.SESSION_SECRET_KEY is None
    assert s.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES == 30
    assert s.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES == 30
    assert s.OTP_EXPIRE_MINUTES == 5
    assert s.OTP_RESEND_COOLDOWN_SECONDS == 60
    assert s.OTP_MAX_ATTEMPTS == 5
    assert s.VECTOR_DIMENSION == 384
    assert s.EMBEDDING_MODEL == "all-MiniLM-L6-v2"
    assert s.RERANKER_MODEL == "cross-encoder/ms-marco-MiniLM-L-6-v2"
    assert s.QDRANT_COLLECTION == "youtube_video_chunks"
    assert s.ALGORITHM == "HS256"


def test_jwt_algorithm_allowed():
    for algo in ["HS256", "HS384", "hs512"]:
        s = Settings(ALGORITHM=algo)
        assert s.ALGORITHM == algo.upper()


def test_jwt_algorithm_rejects_unsafe_none():
    with pytest.raises(ValidationError) as exc:
        Settings(ALGORITHM="none")
    assert "Insecure or unsupported JWT algorithm" in str(exc.value)


def test_jwt_algorithm_rejects_unknown():
    with pytest.raises(ValidationError) as exc:
        Settings(ALGORITHM="RS256")
    assert "Insecure or unsupported JWT algorithm" in str(exc.value)


# ---------------------------------------------------------------------------
# Google OAuth Redirect URI Validation Tests
# ---------------------------------------------------------------------------

def test_production_accepts_valid_https_callback():
    """1. Valid public HTTPS callback accepted in production."""
    strong_secret = "a" * 32
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY=strong_secret,
        DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
        FRONTEND_URL="https://ytgenius.example.com",
        GOOGLE_REDIRECT_URI="https://api.ytgenius.example.com/auth/google/callback",
    )
    assert s.GOOGLE_REDIRECT_URI == "https://api.ytgenius.example.com/auth/google/callback"


def test_production_rejects_missing_callback():
    """2. Missing or empty callback rejected in production."""
    strong_secret = "a" * 32
    # Missing/omitted callback (falls back to dev default which is rejected in production)
    with pytest.raises(ValidationError) as exc_omitted:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=strong_secret,
            DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
            FRONTEND_URL="https://ytgenius.example.com",
        )
    assert "Production requires" in str(exc_omitted.value)

    # Explicitly empty callback
    with pytest.raises(ValidationError) as exc_empty:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=strong_secret,
            DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
            FRONTEND_URL="https://ytgenius.example.com",
            GOOGLE_REDIRECT_URI="",
        )
    assert "Production requires an explicit, non-localhost HTTPS GOOGLE_REDIRECT_URI" in str(exc_empty.value)


def test_production_rejects_http_callback():
    """3. HTTP callback rejected in production."""
    strong_secret = "a" * 32
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=strong_secret,
            DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
            FRONTEND_URL="https://ytgenius.example.com",
            GOOGLE_REDIRECT_URI="http://api.ytgenius.example.com/auth/google/callback",
        )
    assert "HTTPS scheme" in str(exc_info.value)


def test_production_rejects_localhost_callback():
    """4. Localhost callback rejected in production."""
    strong_secret = "a" * 32
    for uri in [
        "https://localhost/auth/google/callback",
        "https://localhost:8000/auth/google/callback",
        "https://sub.localhost/auth/google/callback",
    ]:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY=strong_secret,
                DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
                FRONTEND_URL="https://ytgenius.example.com",
                GOOGLE_REDIRECT_URI=uri,
            )
        assert "Localhost is not allowed" in str(exc_info.value)


def test_production_rejects_ipv4_loopback_callback():
    """5. IPv4 loopback rejected in production."""
    strong_secret = "a" * 32
    for ip in ["127.0.0.1", "127.0.0.2", "127.1.2.3"]:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY=strong_secret,
                DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
                FRONTEND_URL="https://ytgenius.example.com",
                GOOGLE_REDIRECT_URI=f"https://{ip}:8000/auth/google/callback",
            )
        assert "Loopback IP address" in str(exc_info.value)


def test_production_rejects_ipv6_loopback_callback():
    """6. IPv6 loopback rejected in production."""
    strong_secret = "a" * 32
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=strong_secret,
            DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
            FRONTEND_URL="https://ytgenius.example.com",
            GOOGLE_REDIRECT_URI="https://[::1]:8000/auth/google/callback",
        )
    assert "Loopback IP address" in str(exc_info.value)


def test_production_rejects_incorrect_callback_path():
    """7. Incorrect callback path rejected in production."""
    strong_secret = "a" * 32
    for path in [
        "/oauth/callback",
        "/auth/google",
        "/callback",
        "/auth/google/callback/extra",
        "/auth/google/callback/",
    ]:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY=strong_secret,
                DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
                FRONTEND_URL="https://ytgenius.example.com",
                GOOGLE_REDIRECT_URI=f"https://api.ytgenius.example.com{path}",
            )
        assert "path must be exactly '/auth/google/callback'" in str(exc_info.value)


def test_production_rejects_trailing_slash_callback_path():
    """Review 1 regression: Trailing slash variant must be strictly rejected in production."""
    strong_secret = "a" * 32
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=strong_secret,
            DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
            FRONTEND_URL="https://ytgenius.example.com",
            GOOGLE_REDIRECT_URI="https://api.ytgenius.example.com/auth/google/callback/",
        )
    assert "path must be exactly '/auth/google/callback'" in str(exc_info.value)


def test_production_accepts_valid_public_ip_callback():
    """Review 2: Public globally-routable IPv4 address is accepted if policy allows."""
    strong_secret = "a" * 32
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY=strong_secret,
        DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
        FRONTEND_URL="https://ytgenius.example.com",
        GOOGLE_REDIRECT_URI="https://93.184.216.34/auth/google/callback",
    )
    assert s.GOOGLE_REDIRECT_URI == "https://93.184.216.34/auth/google/callback"


def test_production_rejects_private_and_reserved_ips():
    """Review 2: Private, link-local, unique-local, unspecified, and reserved IPs rejected in production."""
    strong_secret = "a" * 32
    rejected_hosts = [
        "10.0.0.1",              # Private IPv4 (10/8)
        "172.16.0.1",            # Private IPv4 (172.16/12)
        "192.168.1.1",           # Private IPv4 (192.168/16)
        "169.254.1.1",           # Link-local IPv4
        "0.0.0.0",               # Unspecified IPv4
        "224.0.0.1",             # Multicast IPv4
        "240.0.0.1",             # Reserved IPv4
        "[fe80::1]",             # Link-local IPv6
        "[fc00::1]",             # Unique-local IPv6
        "[fd12:3456:789a::1]",   # Unique-local IPv6
        "[::]",                  # Unspecified IPv6
    ]
    for host in rejected_hosts:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY=strong_secret,
                DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
                FRONTEND_URL="https://ytgenius.example.com",
                GOOGLE_REDIRECT_URI=f"https://{host}/auth/google/callback",
            )
        assert "Non-public IP address" in str(exc_info.value)


def test_production_rejects_credential_bearing_urls():
    """Review 2: URLs with embedded username/password rejected in production."""
    strong_secret = "a" * 32
    for cred_url in [
        "https://user:password@api.ytgenius.example.com/auth/google/callback",
        "https://user@api.ytgenius.example.com/auth/google/callback",
    ]:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY=strong_secret,
                DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
                FRONTEND_URL="https://ytgenius.example.com",
                GOOGLE_REDIRECT_URI=cred_url,
            )
        assert "embedded user credentials" in str(exc_info.value)


def test_production_rejects_malformed_hostnames_and_ipv6_brackets():
    """Review 3: Malformed IPv6 brackets and invalid DNS hostnames reject cleanly."""
    strong_secret = "a" * 32
    malformed_uris = [
        "https://[::1/auth/google/callback",
        "https://[invalid-ipv6]/auth/google/callback",
        "https://api..ytgenius.com/auth/google/callback",
        "https://-bad.domain.com/auth/google/callback",
        "https://bad-.domain.com/auth/google/callback",
        "https://api ytgenius com/auth/google/callback",
    ]
    for bad_uri in malformed_uris:
        with pytest.raises(ValidationError):
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY=strong_secret,
                DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
                FRONTEND_URL="https://ytgenius.example.com",
                GOOGLE_REDIRECT_URI=bad_uri,
            )


def test_production_rejects_malformed_uri():
    """8. Malformed URI rejected in production."""
    strong_secret = "a" * 32
    for bad_uri in [
        "https://",
        "not_a_valid_url",
        "https://api.ytgenius.example.com:70000/auth/google/callback",
        "https://api.ytgenius.example.com/auth/google/callback?query=1",
        "https://api.ytgenius.example.com/auth/google/callback#frag",
    ]:
        with pytest.raises(ValidationError):
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY=strong_secret,
                DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
                FRONTEND_URL="https://ytgenius.example.com",
                GOOGLE_REDIRECT_URI=bad_uri,
            )


def test_development_localhost_callback_remains_valid():
    """9. Development localhost callback remains valid."""
    s1 = Settings(ENVIRONMENT="development")
    assert s1.GOOGLE_REDIRECT_URI == "http://localhost:8000/auth/google/callback"

    s2 = Settings(
        ENVIRONMENT="development",
        GOOGLE_REDIRECT_URI="http://localhost:8001/auth/google/callback",
    )
    assert s2.GOOGLE_REDIRECT_URI == "http://localhost:8001/auth/google/callback"


# ---------------------------------------------------------------------------
# Task 9: IP Classification and Port Validation Regression Tests
# ---------------------------------------------------------------------------

def test_production_rejects_cgnat_shared_address_space():
    """1 & 2. Production rejects 100.64.0.1 and another address in 100.64.0.0/10 (RFC 6598)."""
    strong_secret = "a" * 32
    cgnat_addresses = ["100.64.0.1", "100.127.255.254"]
    for ip in cgnat_addresses:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY=strong_secret,
                DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
                FRONTEND_URL="https://ytgenius.example.com",
                GOOGLE_REDIRECT_URI=f"https://{ip}/auth/google/callback",
            )
        assert "Non-public IP address" in str(exc_info.value)


def test_production_rejects_multicast_ips():
    """3 & 4. Production rejects IPv4 and IPv6 multicast addresses."""
    strong_secret = "a" * 32
    multicast_hosts = [
        "224.0.0.1",           # IPv4 multicast
        "239.255.255.250",     # IPv4 multicast
        "[ff02::1]",           # IPv6 multicast
        "[ff00::1]",           # IPv6 multicast
    ]
    for host in multicast_hosts:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY=strong_secret,
                DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
                FRONTEND_URL="https://ytgenius.example.com",
                GOOGLE_REDIRECT_URI=f"https://{host}/auth/google/callback",
            )
        assert "Non-public IP address" in str(exc_info.value)


def test_production_accepts_valid_global_ips():
    """5 & 6. Production accepts valid global IPv4 and IPv6 addresses."""
    strong_secret = "a" * 32
    valid_ips = [
        ("93.184.216.34", "https://93.184.216.34/auth/google/callback"),
        ("8.8.8.8", "https://8.8.8.8/auth/google/callback"),
        ("[2606:4700:4700::1111]", "https://[2606:4700:4700::1111]/auth/google/callback"),
        ("[2001:4860:4860::8888]", "https://[2001:4860:4860::8888]/auth/google/callback"),
    ]
    for _, uri in valid_ips:
        s = Settings(
            ENVIRONMENT="production",
            SECRET_KEY=strong_secret,
            DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
            FRONTEND_URL="https://ytgenius.example.com",
            GOOGLE_REDIRECT_URI=uri,
        )
        assert s.GOOGLE_REDIRECT_URI == uri


def test_production_rejects_explicit_empty_port():
    """7. Production rejects an explicitly empty port specification."""
    strong_secret = "a" * 32
    empty_port_uris = [
        "https://example.com:/auth/google/callback",
        "https://api.ytgenius.example.com:/auth/google/callback",
        "https://[2606:4700:4700::1111]:/auth/google/callback",
    ]
    for uri in empty_port_uris:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY=strong_secret,
                DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
                FRONTEND_URL="https://ytgenius.example.com",
                GOOGLE_REDIRECT_URI=uri,
            )
        assert "empty port specification" in str(exc_info.value)


def test_production_accepts_standard_url_without_port():
    """8. Production accepts standard HTTPS URL without a port."""
    strong_secret = "a" * 32
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY=strong_secret,
        DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
        FRONTEND_URL="https://ytgenius.example.com",
        GOOGLE_REDIRECT_URI="https://api.ytgenius.example.com/auth/google/callback",
    )
    assert s.GOOGLE_REDIRECT_URI == "https://api.ytgenius.example.com/auth/google/callback"


def test_production_accepts_explicit_valid_ports():
    """9. Production accepts explicit valid ports."""
    strong_secret = "a" * 32
    valid_port_uris = [
        "https://api.ytgenius.example.com:443/auth/google/callback",
        "https://api.ytgenius.example.com:8443/auth/google/callback",
        "https://[2606:4700:4700::1111]:443/auth/google/callback",
        "https://[2606:4700:4700::1111]:8443/auth/google/callback",
    ]
    for uri in valid_port_uris:
        s = Settings(
            ENVIRONMENT="production",
            SECRET_KEY=strong_secret,
            DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
            FRONTEND_URL="https://ytgenius.example.com",
            GOOGLE_REDIRECT_URI=uri,
        )
        assert s.GOOGLE_REDIRECT_URI == uri


def test_production_rejects_non_numeric_zero_and_out_of_range_ports():
    """10. Production rejects non-numeric, zero, and out-of-range ports."""
    strong_secret = "a" * 32
    bad_port_uris = [
        "https://example.com:abc/auth/google/callback",
        "https://example.com:0/auth/google/callback",
        "https://example.com:65536/auth/google/callback",
        "https://example.com:70000/auth/google/callback",
        "https://[2606:4700:4700::1111]:0/auth/google/callback",
        "https://[2606:4700:4700::1111]:99999/auth/google/callback",
    ]
    for uri in bad_port_uris:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY=strong_secret,
                DATABASE_URL="postgresql://prod_user:strong_password@prod-db.internal:5432/ytgenius_db",
                FRONTEND_URL="https://ytgenius.example.com",
                GOOGLE_REDIRECT_URI=uri,
            )
        assert "Invalid port" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Docker Compose Interpolation Tests
# ---------------------------------------------------------------------------

def _evaluate_compose_redirect_uri(env_overrides: dict) -> str:
    """Evaluate GOOGLE_REDIRECT_URI from docker-compose.yml template.

    Attempts native 'docker compose config' first if available in the execution
    environment; falls back to exact template evaluation based on the specification
    in docker-compose.yml.
    """
    import os
    import re
    import shutil
    import subprocess
    from pathlib import Path

    compose_file = Path(__file__).resolve().parents[1] / "docker-compose.yml"
    assert compose_file.exists(), "docker-compose.yml not found"
    content = compose_file.read_text(encoding="utf-8")
    pattern = r"GOOGLE_REDIRECT_URI=\$\{GOOGLE_REDIRECT_URI:-http://localhost:\$\{PORT:-8000\}/auth/google/callback\}"
    assert re.search(pattern, content) is not None, "Expected GOOGLE_REDIRECT_URI pattern missing from docker-compose.yml"

    # Try live docker compose config if CLI is functional
    if shutil.which("docker"):
        env = os.environ.copy()
        if "GOOGLE_REDIRECT_URI" not in env_overrides:
            env.pop("GOOGLE_REDIRECT_URI", None)
        if "PORT" not in env_overrides:
            env.pop("PORT", None)
        env.update({
            "POSTGRES_PASSWORD": "dummy_postgres_pass",
            "SECRET_KEY": "a" * 32,
            "FRONTEND_URL": "https://example.com",
        })
        env.update(env_overrides)
        try:
            null_device = "NUL" if os.name == "nt" else "/dev/null"
            res = subprocess.run(
                ["docker", "compose", "--env-file", null_device, "config"],
                capture_output=True,
                text=True,
                env=env,
                timeout=10,
            )
            if res.returncode == 0:
                match = re.search(r"GOOGLE_REDIRECT_URI:\s*(\S+)", res.stdout)
                if match:
                    return match.group(1).strip()
        except Exception:
            pass

    # Fallback to pure template evaluation matching Docker Compose interpolation spec
    if env_overrides.get("GOOGLE_REDIRECT_URI"):
        return env_overrides["GOOGLE_REDIRECT_URI"]
    port = env_overrides.get("PORT") or "8000"
    return f"http://localhost:{port}/auth/google/callback"


def test_compose_default_port_interpolation():
    """10. Compose default port interpolation."""
    uri = _evaluate_compose_redirect_uri({})
    assert uri == "http://localhost:8000/auth/google/callback"


def test_compose_custom_port_interpolation():
    """11. Compose custom port interpolation."""
    uri = _evaluate_compose_redirect_uri({"PORT": "8001"})
    assert uri == "http://localhost:8001/auth/google/callback"


def test_compose_explicit_callback_override():
    """12. Explicit callback override."""
    uri = _evaluate_compose_redirect_uri({"GOOGLE_REDIRECT_URI": "https://custom.example.com/auth/google/callback"})
    assert uri == "https://custom.example.com/auth/google/callback"


def test_db_pool_configuration_defaults():
    """Verify conservative database pool defaults and max backend connection budget."""
    s = Settings()
    assert s.WORKERS == 4
    assert s.DB_POOL_SIZE == 5
    assert s.DB_MAX_OVERFLOW == 5
    assert s.DB_POOL_RECYCLE == 1800
    assert s.DB_POOL_TIMEOUT == 30
    # Single deployment budget: WORKERS * (DB_POOL_SIZE + DB_MAX_OVERFLOW) = 40
    assert s.max_backend_db_connections == 40
    assert 97 - s.max_backend_db_connections == 57  # single-deployment headroom
    # Overlapping / rolling deployment budget (2 simultaneous instances) = 80
    assert 2 * s.max_backend_db_connections == 80
    assert 97 - (2 * s.max_backend_db_connections) == 17  # rolling-deployment headroom


def test_db_pool_custom_configuration():
    """Verify custom database pool and worker parameters."""
    s = Settings(WORKERS=2, DB_POOL_SIZE=8, DB_MAX_OVERFLOW=2, DB_POOL_RECYCLE=600, DB_POOL_TIMEOUT=15)
    assert s.WORKERS == 2
    assert s.DB_POOL_SIZE == 8
    assert s.DB_MAX_OVERFLOW == 2
    assert s.DB_POOL_RECYCLE == 600
    assert s.DB_POOL_TIMEOUT == 15
    assert s.max_backend_db_connections == 20


def test_sqlalchemy_engine_pool_configuration():
    """Verify that SQLAlchemy engine actually applies configured pool parameters."""
    from sqlalchemy import create_engine
    from sqlalchemy.pool import QueuePool

    s = Settings(DB_POOL_SIZE=7, DB_MAX_OVERFLOW=3, DB_POOL_RECYCLE=900, DB_POOL_TIMEOUT=15)
    engine = create_engine(
        "postgresql://user:pass@localhost:5432/testdb",
        pool_size=s.DB_POOL_SIZE,
        max_overflow=s.DB_MAX_OVERFLOW,
        pool_recycle=s.DB_POOL_RECYCLE,
        pool_timeout=s.DB_POOL_TIMEOUT,
    )
    assert isinstance(engine.pool, QueuePool)
    assert engine.pool.size() == 7
    assert engine.pool._max_overflow == 3
    assert engine.pool._recycle == 900
    assert engine.pool._timeout == 15


def test_db_pool_zero_overflow_allowed():
    """Verify DB_MAX_OVERFLOW=0 is allowed (disables overflow connections beyond pool)."""
    s = Settings(DB_MAX_OVERFLOW=0)
    assert s.DB_MAX_OVERFLOW == 0
    assert s.max_backend_db_connections == 20


def test_db_pool_invalid_values():
    """Verify validation rejects zero/negative pool size, negative overflow, or non-positive timeouts."""
    with pytest.raises(ValidationError):
        Settings(DB_POOL_SIZE=0)
    with pytest.raises(ValidationError):
        Settings(DB_POOL_SIZE=-1)
    with pytest.raises(ValidationError):
        Settings(DB_POOL_SIZE="invalid")
    with pytest.raises(ValidationError):
        Settings(DB_MAX_OVERFLOW=-1)
    with pytest.raises(ValidationError):
        Settings(DB_MAX_OVERFLOW="invalid")
    with pytest.raises(ValidationError):
        Settings(DB_POOL_RECYCLE=0)
    with pytest.raises(ValidationError):
        Settings(DB_POOL_TIMEOUT=-5)


def test_worker_configuration_defaults_and_custom():
    """Verify Uvicorn worker settings defaults and overrides."""
    s_default = Settings()
    assert s_default.WORKERS == 4

    s_custom = Settings(WORKERS=8)
    assert s_custom.WORKERS == 8


def test_worker_configuration_rejects_invalid():
    """Verify validation rejects zero, negative, or non-integer worker counts."""
    with pytest.raises(ValidationError):
        Settings(WORKERS=0)
    with pytest.raises(ValidationError):
        Settings(WORKERS=-2)
    with pytest.raises(ValidationError):
        Settings(WORKERS="abc")


def test_compose_workers_and_db_pool_interpolation():
    """Verify docker-compose.yml properly parameterizes WORKERS, DB_POOL_SIZE, and DB_MAX_OVERFLOW."""
    from pathlib import Path
    compose_file = Path(__file__).resolve().parents[1] / "docker-compose.yml"
    assert compose_file.exists()
    content = compose_file.read_text(encoding="utf-8")
    assert "WORKERS=${WORKERS:-4}" in content
    assert "DB_POOL_SIZE=${DB_POOL_SIZE:-5}" in content
    assert "DB_MAX_OVERFLOW=${DB_MAX_OVERFLOW:-5}" in content


def test_dockerfile_workers_configuration():
    """Verify backend/Dockerfile specifies default WORKERS=4 and parameterized CMD."""
    from pathlib import Path
    dockerfile = Path(__file__).resolve().parents[1] / "backend" / "Dockerfile"
    assert dockerfile.exists()
    content = dockerfile.read_text(encoding="utf-8")
    assert "WORKERS=4" in content
    assert "--workers ${WORKERS:-4}" in content
