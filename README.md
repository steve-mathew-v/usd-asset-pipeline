# USD Asset Pipeline

![CI](https://github.com/steve-mathew-v/usd-asset-pipeline/actions/workflows/ci.yml/badge.svg)

A pipeline for sharing versioned **USD** assets between DCC tools (Maya and Houdini) through a central server, with files and version history stored in MongoDB Atlas. Every publish is kept as a new version; a chosen version is approved for others to import.

## What it does

Artists can upload .obj files from Maya to a shared server. Once an asset is marked as ready, other artists can pull it straight into their Maya scene without having to manually share files.

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A free MongoDB Atlas account
- Maya 2025 (for the artist tools)

## Setup

### 1. Install dependencies

With uv (recommended — creates an isolated .venv automatically):

```bash
uv sync
```

Or with pip:

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Set up MongoDB Atlas

1. Create a free account at [mongodb.com/atlas](https://www.mongodb.com/atlas) and create a cluster (the free M0 tier is fine).
2. In **Database Access**, create a database user and note the username/password.
3. In **Network Access**, allow access from your IP (or 0.0.0.0/0 for testing).
4. Click **Connect** on your cluster and copy the connection string — it looks like `mongodb+srv://user:pass@cluster0.xxxxx.mongodb.net/`. This is your `MONGO_URI`.
5. For the user management features you also need an Atlas API key: go to **Project Settings > Access Manager > API Keys**, create a key with the *Project Owner* role, and note the public and private key. Your `ATLAS_PROJECT_ID` is in **Project Settings > General**.

### 3. Create the .env file

Create a file called `.env` in the project root:

```
# from step 4 above
MONGO_URI=mongodb+srv://user:pass@cluster0.xxxxx.mongodb.net/
DB_NAME=obj_pipeline

# from step 5 above (only needed for the user management tab)
ATLAS_PUBLIC_KEY=your_atlas_public_key
ATLAS_PRIVATE_KEY=your_atlas_private_key
ATLAS_PROJECT_ID=your_atlas_project_id

# pick your own admin login for the GUI
ROOT_USER=admin
ROOT_PASS=pick_a_password
```

## Running the server

Through the management GUI:

```bash
uv run gui.py          # or: python gui.py
```

Log in with your `ROOT_USER`/`ROOT_PASS`, then click **Start Server**. The server runs on `http://localhost:8000` and the interactive API docs are at `http://localhost:8000/docs`.

Or straight from the terminal:

```bash
uv run uvicorn main:app --reload --port 8000
```

## Running the tests

```bash
uv run pytest          # or: python -m pytest
```

The tests use an in-memory fake database, so they run without an Atlas connection.

The same test suite runs automatically on every push via GitHub Actions (see `.github/workflows/ci.yml`).

## Running with Docker

The server can be run in a container so it works the same on any machine without installing Python or the dependencies by hand. You still need a `.env` file (see above).

```bash
docker compose up --build
```

This builds the image and starts the server on `http://localhost:8000`. Uploaded files and thumbnails are stored in MongoDB (via GridFS), so the server keeps nothing on its own disk and can run on an ephemeral cloud host without losing assets. Only the server is containerised — the GUI and Maya tools run on the artist's own machine.

## Letting other people connect

By default everything points at `http://localhost:8000`, which only works on the same machine as the server. To let someone on another machine connect, point their client at the server's address with the `PIPELINE_SERVER` environment variable (or by editing the `SERVER` line at the top of `maya/pipeline.py`). Include the scheme and no trailing slash:

```
PIPELINE_SERVER=https://my-pipeline.onrender.com
```

There are two common ways to make the server reachable:

- **Same network (LAN):** the server already binds to `0.0.0.0`, so others on the same Wi-Fi can use `http://<your-local-ip>:8000` (allow port 8000 through your firewall).
- **Over the internet:** either run a tunnel from your machine (e.g. `cloudflared tunnel --url http://localhost:8000`, which prints a public `https://…trycloudflare.com` URL) or deploy the server to a cloud host. A [render.com](https://render.com) blueprint is included (`render.yaml`) — it builds from the Dockerfile; set `MONGO_URI`, `DB_NAME`, `ROOT_USER`, `ROOT_PASS` in the Render dashboard. When deploying to Atlas, allow access from anywhere (`0.0.0.0/0`) under Network Access, since cloud hosts use dynamic IPs.

Either way, create the person an account (Users tab or `startup.py`), give them the server URL, and they log in with those credentials.

## Maya setup

The Maya tools use the modules that ship with Maya 2025 (PySide6 included), so nothing extra needs to be installed into Maya.

Open Maya's Script Editor (Python tab) and run the installer once:

```python
import sys
sys.path.append(r"path/to/obj-pipeline/maya")
import install
install.run()
```

This creates an **OBJPipeline** shelf with these buttons:

| Button | What it does |
|--------|-------------|
| PUB | Publish the current selection as USD (a new version) |
| IMP | Import all approved assets into the scene |
| CHK | Check what's approved on the server |
| VER | Show an asset's version history / import a specific version |
| OK | Approve the latest version of an asset |
| NO | Unapprove an asset |

The first time you click any button you'll be asked to log in. Any Atlas database user (created from the Users tab or `startup.py`) can log in.

## Houdini setup

The Houdini tools use `hou` and Houdini's built-in dialogs, so nothing extra needs installing. Open Houdini's **Python Source Editor** (Windows > Python Source Editor) and run the installer once:

```python
import sys
sys.path.append(r"path/to/obj-pipeline/houdini")
import install
install.run()
```

This creates an **OBJ Pipeline** shelf with the same PUB / IMP / CHK / VER / OK / NO tools. Select geometry and click **PUB** to publish it as USD; **IMP** brings approved assets in through a File SOP.

## Managing users

Use the **Users** tab in the GUI, or run the terminal version:

```bash
uv run startup.py
```

## Versioning

Re-publishing an asset with the same name does **not** overwrite it — it creates the next version (v1, v2, v3…). The full history is kept. You then **approve** a specific version (the latest by default, or a pinned one), and that's what other artists import. This gives real version tracking and lets you roll back or pin an exact version.

## Asset thumbnails

When you publish from Maya, the pipeline automatically takes a front and top viewport screenshot of that version and uploads them. They show up in the GUI's **Assets** tab. (Houdini publishing skips thumbnails for now.)

## Where files are stored

USD files and thumbnails are stored **inside MongoDB using GridFS**, not on the server's local disk. This keeps the server stateless, so it can be deployed to a cloud host (where the disk is wiped on every restart) without losing any assets. The trade-off is the database's storage limit (512 MB on the Atlas free tier), which suits modest assets.

## Project structure

```
obj-pipeline/
├── main.py            # FastAPI app entry point
├── routes.py          # API endpoints
├── database.py        # MongoDB connection
├── models.py          # Versioned asset data model
├── storage.py         # File storage in MongoDB GridFS
├── database.py        # MongoDB connection (files + records both live here)
├── gui.py             # Management GUI
├── startup.py         # Terminal management script
├── pyproject.toml     # Project metadata and dependencies
├── Dockerfile         # Server container image
├── docker-compose.yml # One-command server startup
├── render.yaml        # Render.com cloud deploy blueprint
├── .github/workflows/ # CI: runs the tests on every push
├── maya/
│   ├── install.py     # One-time Maya installer
│   └── pipeline.py    # Maya shelf and pipeline tools
├── houdini/
│   ├── install.py     # One-time Houdini installer
│   └── pipeline.py    # Houdini shelf and pipeline tools
└── tests/             # pytest suite (runs offline, no Atlas needed)
```
