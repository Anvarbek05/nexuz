from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root_redirects_to_a_language():
    r = client.get("/", follow_redirects=False, headers={"accept-language": "ru-RU,ru;q=0.9"})
    assert r.status_code == 302 and r.headers["location"] == "/ru/"
    r = client.get("/", follow_redirects=False, headers={"accept-language": "de"})
    assert r.headers["location"] == "/uz/"      # default language
