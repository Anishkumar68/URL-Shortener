from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_shorten_url():
    response = client.post("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 200
    data = response.json()
    assert "short_url" in data


def test_redirect_and_stats():
    # Shorten a URL first
    response = client.post("/shorten", json={"url": "https://example.com"})
    short_url = response.json()["short_url"]
    short_code = short_url.split("/")[-1]

    # Simulate visiting the short URL
    redirect_response = client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_response.status_code in (307, 302)  # Redirect

    # Get stats
    stats_response = client.get(f"/stats/{short_code}")
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["visit_count"] >= 1
    assert len(stats["visitors"]) >= 1
