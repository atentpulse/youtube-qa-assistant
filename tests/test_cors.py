def test_cors_preflight_allowed_web_origin(client):
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    }
    response = client.options("/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_rejected_origin(client):
    headers = {
        "Origin": "http://malicious-site.com",
        "Access-Control-Request-Method": "POST",
    }
    response = client.options("/health", headers=headers)
    assert response.headers.get("access-control-allow-origin") != "http://malicious-site.com"


def test_cors_chrome_extension_origin(client):
    from app.core import settings
    # Add a mock extension ID dynamically to settings
    settings.CHROME_EXTENSION_IDS = ["abcdefghijklmno123456"]
    
    headers = {
        "Origin": "chrome-extension://abcdefghijklmno123456",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "chrome-extension://abcdefghijklmno123456"
