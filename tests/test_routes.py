"""Tests for the versioned USD asset API."""

import os


def _upload(client, data=b"#usda 1.0\n", name="cube.usd", by="steve"):
    return client.post(
        f"/api/assets/upload?uploaded_by={by}",
        files={"file": (name, data, "application/octet-stream")},
    )


def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "running"}


def test_login_with_root_credentials(client):
    response = client.post(
        "/api/auth/login",
        json={
            "username": os.environ["ROOT_USER"],
            "password": os.environ["ROOT_PASS"],
        },
    )
    assert response.status_code == 200
    assert response.json() == {"success": True}


def test_login_with_wrong_credentials(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "nobody", "password": "wrong"},
    )
    assert response.status_code == 401


def test_upload_rejects_non_usd(client):
    response = client.post(
        "/api/assets/upload",
        files={"file": ("model.obj", b"v 0 0 0", "application/octet-stream")},
    )
    assert response.status_code == 400


def test_upload_creates_versions(client):
    assert _upload(client).json()["version"] == 1
    assert _upload(client).json()["version"] == 2

    assets = client.get("/api/assets").json()
    assert len(assets) == 1
    asset = assets[0]
    assert asset["name"] == "cube"
    assert asset["latest_version"] == 2
    assert len(asset["versions"]) == 2
    assert asset["approved_version"] is None


def test_download_requires_approval(client):
    _upload(client)
    assert client.get("/api/assets/download/cube").status_code == 404


def test_approve_latest_and_download(client):
    _upload(client, b"v1")
    _upload(client, b"v2")

    assert client.patch("/api/assets/cube/approve").status_code == 200
    download = client.get("/api/assets/download/cube")
    assert download.status_code == 200
    assert download.content == b"v2"


def test_approve_specific_version(client):
    _upload(client, b"v1")
    _upload(client, b"v2")

    client.patch("/api/assets/cube/approve?version=1")
    assert client.get("/api/assets/download/cube").content == b"v1"


def test_download_pinned_version(client):
    _upload(client, b"v1")
    _upload(client, b"v2")
    client.patch("/api/assets/cube/approve")  # approves v2

    assert client.get("/api/assets/download/cube?version=1").content == b"v1"


def test_versions_endpoint(client):
    _upload(client, b"v1")
    _upload(client, b"v2")
    client.patch("/api/assets/cube/approve?version=1")

    history = client.get("/api/assets/cube/versions").json()
    assert history["latest_version"] == 2
    assert history["approved_version"] == 1
    assert len(history["versions"]) == 2


def test_ready_list_and_unapprove(client):
    _upload(client)
    client.patch("/api/assets/cube/approve")
    assert client.get("/api/assets/ready").json()[0]["name"] == "cube"

    client.patch("/api/assets/cube/unapprove")
    assert client.get("/api/assets/ready").json() == []
    assert client.get("/api/assets/download/cube").status_code == 404


def test_thumbnail_round_trip(client):
    _upload(client)
    client.post(
        "/api/assets/cube/thumbnail/front?version=1",
        files={"file": ("cube_front.jpg", b"jpegbytes", "image/jpeg")},
    )
    response = client.get("/api/assets/cube/thumbnail/front?version=1")
    assert response.status_code == 200
    assert response.content == b"jpegbytes"


def test_thumbnail_rejects_bad_view(client):
    response = client.post(
        "/api/assets/cube/thumbnail/side?version=1",
        files={"file": ("cube_side.jpg", b"jpegdata", "image/jpeg")},
    )
    assert response.status_code == 400


def test_delete_removes_asset(client):
    _upload(client)
    assert client.delete("/api/assets/cube").status_code == 200
    assert client.get("/api/assets").json() == []


def test_unknown_asset_404s(client):
    assert client.get("/api/assets/nope/versions").status_code == 404
    assert client.patch("/api/assets/nope/approve").status_code == 404
    assert client.get("/api/assets/download/nope").status_code == 404
    assert client.delete("/api/assets/nope").status_code == 404
