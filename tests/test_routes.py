"""Tests for the asset API endpoints."""

import os


def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "running"}


def test_login_with_root_credentials(client):
    response = client.post("/api/auth/login", json={
        "username": os.environ["ROOT_USER"],
        "password": os.environ["ROOT_PASS"],
    })
    assert response.status_code == 200
    assert response.json() == {"success": True}


def test_login_with_wrong_credentials(client):
    response = client.post("/api/auth/login", json={
        "username": "nobody",
        "password": "wrong",
    })
    assert response.status_code == 401


def test_upload_rejects_non_obj_files(client):
    response = client.post(
        "/api/assets/upload",
        files={"file": ("model.fbx", b"not an obj", "application/octet-stream")},
    )
    assert response.status_code == 400


def test_upload_and_list_asset(client, fake_collection, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("uploads", exist_ok=True)

    response = client.post(
        "/api/assets/upload?uploaded_by=tester",
        files={"file": ("cube.obj", b"v 0 0 0\n", "application/octet-stream")},
    )
    assert response.status_code == 200

    response = client.get("/api/assets")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) == 1
    assert assets[0]["name"] == "cube"
    assert assets[0]["uploaded_by"] == "tester"
    assert assets[0]["ready"] is False


def test_reupload_replaces_existing_asset(client, fake_collection, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("uploads", exist_ok=True)

    for _ in range(2):
        client.post(
            "/api/assets/upload",
            files={"file": ("cube.obj", b"v 0 0 0\n", "application/octet-stream")},
        )

    assets = client.get("/api/assets").json()
    assert len(assets) == 1


def test_mark_and_unmark_ready(client, fake_collection):
    fake_collection.documents.append(
        {"_id": "id0", "name": "cube", "file_path": "uploads/cube.obj", "ready": False}
    )

    response = client.patch("/api/assets/cube/ready")
    assert response.status_code == 200
    assert client.get("/api/assets/ready").json()[0]["name"] == "cube"

    response = client.patch("/api/assets/cube/unready")
    assert response.status_code == 200
    assert client.get("/api/assets/ready").json() == []


def test_mark_ready_unknown_asset(client):
    response = client.patch("/api/assets/doesnotexist/ready")
    assert response.status_code == 404


def test_download_unknown_asset(client):
    response = client.get("/api/assets/download/doesnotexist")
    assert response.status_code == 404


def test_thumbnail_rejects_bad_view(client):
    response = client.post(
        "/api/assets/cube/thumbnail/side",
        files={"file": ("cube_side.jpg", b"jpegdata", "image/jpeg")},
    )
    assert response.status_code == 400


def test_delete_unknown_asset(client):
    response = client.delete("/api/assets/doesnotexist")
    assert response.status_code == 404


def test_delete_asset_removes_entry(client, fake_collection):
    fake_collection.documents.append(
        {"_id": "id0", "name": "cube", "file_path": "uploads/missing.obj", "ready": False}
    )

    response = client.delete("/api/assets/cube")
    assert response.status_code == 200
    assert client.get("/api/assets").json() == []
