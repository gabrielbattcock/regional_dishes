import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_recipes():
    response = client.get("/api/recipes/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_recipe_by_id():
    response = client.get("/api/recipes/cornish-pasty")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "cornish-pasty"
    assert "ingredients" in data
    assert "steps" in data


def test_recipe_not_found():
    response = client.get("/api/recipes/nonexistent")
    assert response.status_code == 404


def test_list_regions():
    response = client.get("/api/regions/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
