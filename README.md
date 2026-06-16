# OBJ Pipeline

![CI](https://github.com/steve-mathew-v/usd-asset-pipeline/actions/workflows/ci.yml/badge.svg)

A simple asset pipeline for sharing .obj files between DCC tools using a central server and MongoDB Atlas.

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

This builds the image, starts the server on `http://localhost:8000`, and keeps the `uploads/` and `thumbnails/` folders on the host so files survive restarts. Only the server is containerised — the GUI and Maya tools run on the artist's own machine.

## Maya setup

The Maya tools use the modules that ship with Maya 2025 (PySide6 included), so nothing extra needs to be installed into Maya.

Open Maya's Script Editor (Python tab) and run the installer once:

```python
import sys
sys.path.append(r"path/to/obj-pipeline/maya")
import install
install.run()
```

This adds the pipeline to your `userSetup.py` and creates an **OBJPipeline** shelf with these buttons:

| Button | What it does |
|--------|-------------|
| UPL | Upload a .obj file to the server |
| IMP | Import all ready assets into the scene |
| CHK | Check what assets are ready |
| RDY | Mark an asset as ready |
| URDY | Unmark an asset |

The first time you click any button you'll be asked to log in. Any Atlas database user (created from the Users tab or `startup.py`) can log in.

## Managing users

Use the **Users** tab in the GUI, or run the terminal version:

```bash
uv run startup.py
```

## Asset thumbnails

When you upload a .obj from Maya, the pipeline automatically takes a front and top viewport screenshot and uploads them to the server. These show up in the GUI's **Assets** tab.

## Project structure

```
obj-pipeline/
├── main.py            # FastAPI app entry point
├── routes.py          # API endpoints
├── database.py        # MongoDB connection
├── models.py          # Asset data model
├── gui.py             # Management GUI
├── startup.py         # Terminal management script
├── pyproject.toml     # Project metadata and dependencies
├── Dockerfile         # Server container image
├── docker-compose.yml # One-command server startup
├── .github/workflows/ # CI: runs the tests on every push
├── maya/
│   ├── install.py     # One-time Maya installer
│   └── pipeline.py    # Maya shelf and pipeline tools
├── tests/             # pytest suite (runs offline, no Atlas needed)
├── uploads/           # Stored .obj files (created at runtime)
└── thumbnails/        # Auto-generated asset thumbnails (created at runtime)
```
