"""Maya-side tools for the OBJ pipeline.

Gives artists shelf buttons to upload .obj files to the central server,
check and import ready assets, and mark assets as ready. Dialogs use
PySide6 (which ships with Maya 2025).
"""

import http.client
import json
import os
import tempfile
import urllib.request
from typing import Optional
from urllib.parse import urlparse

import maya.cmds as cmds
import maya.mel as mel

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

# Server address. Override with the PIPELINE_SERVER environment variable, or
# edit this line to point at your server. Include the scheme (http/https) and
# no trailing slash. Examples:
#   "http://localhost:8000"             - running on your own machine
#   "https://abc123.trycloudflare.com"  - a Cloudflare tunnel
#   "https://my-pipeline.onrender.com"  - a cloud deployment
SERVER = os.environ.get("PIPELINE_SERVER", "http://localhost:8000").rstrip("/")

_logged_in = False
_current_user: Optional[str] = None


def _connect():
    """Open an HTTP or HTTPS connection to the server based on SERVER's scheme."""
    parsed = urlparse(SERVER)
    if parsed.scheme == "https":
        return http.client.HTTPSConnection(parsed.netloc)
    return http.client.HTTPConnection(parsed.netloc)


class LoginDialog(QDialog):
    """Small username/password dialog shown on the first pipeline action."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Pipeline Login")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form.addRow("Username:", self.username_input)
        form.addRow("Password:", self.password_input)
        layout.addLayout(form)

        self.message_label = QLabel("")
        self.message_label.setStyleSheet("color: red;")
        layout.addWidget(self.message_label)

        login_button = QPushButton("Login")
        login_button.clicked.connect(self.try_login)
        self.password_input.returnPressed.connect(self.try_login)
        layout.addWidget(login_button)

    def try_login(self) -> None:
        """Send the entered credentials to the server's login endpoint."""
        global _current_user

        username = self.username_input.text().strip()
        password = self.password_input.text()

        try:
            body = json.dumps({"username": username, "password": password}).encode()
            connection = _connect()
            connection.request(
                "POST",
                "/api/auth/login",
                body=body,
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            connection.close()
            if response.status == 200:
                _current_user = username
                self.accept()
            else:
                self.message_label.setText("Wrong username or password")
                self.password_input.clear()
        except Exception as exc:
            self.message_label.setText(f"Could not reach server: {exc}")


def _check_login() -> bool:
    """Show the login dialog if the artist has not logged in yet."""
    global _logged_in
    if not _logged_in:
        _logged_in = LoginDialog().exec() == QDialog.Accepted
    return _logged_in


def _server_up() -> bool:
    """Ping the server, with a popup if it is not reachable."""
    try:
        urllib.request.urlopen(f"{SERVER}/", timeout=2)
        return True
    except Exception:
        QMessageBox.critical(None, "Error", "Server is not running")
        return False


def _ask_asset_name(title: str) -> Optional[str]:
    """Prompt the artist for an asset name. Returns None if cancelled."""
    name, ok = QInputDialog.getText(None, title, "Asset name:")
    name = name.strip()
    if not ok or not name:
        return None
    return name


def _multipart_upload(
    filepath: str, source_tool: str = "Maya", ready: bool = False
) -> tuple[int, dict]:
    """Upload a .obj file to the server as multipart form data.

    Built by hand because Maya's Python does not ship with requests.
    """
    filename = os.path.basename(filepath)
    boundary = "----MayaPipelineBoundary"

    with open(filepath, "rb") as obj_file:
        file_data = obj_file.read()

    body = (
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode()
        + file_data
        + f"\r\n--{boundary}--\r\n".encode()
    )

    uploader = _current_user or "unknown"
    url = (
        f"/api/assets/upload?source_tool={source_tool}"
        f"&ready={str(ready).lower()}&uploaded_by={uploader}"
    )
    connection = _connect()
    connection.request(
        "POST",
        url,
        body=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
    )
    response = connection.getresponse()
    data = json.loads(response.read())
    connection.close()
    return response.status, data


def _upload_thumbnail(name: str, view: str, filepath: str) -> None:
    """Upload one viewport screenshot to the server."""
    boundary = "----ThumbBoundary"
    with open(filepath, "rb") as image_file:
        image_data = image_file.read()

    body = (
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; '
            f'filename="{os.path.basename(filepath)}"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        ).encode()
        + image_data
        + f"\r\n--{boundary}--\r\n".encode()
    )

    connection = _connect()
    connection.request(
        "POST",
        f"/api/assets/{name}/thumbnail/{view}",
        body=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
    )
    response = connection.getresponse()
    connection.close()
    print(f"{view} thumb {'ok' if response.status == 200 else 'failed'}")


def _take_thumbnails(name: str, nodes: list[str]) -> None:
    """Playblast front and top screenshots of the given nodes and upload them."""
    temp_dir = tempfile.gettempdir()

    panel = None
    for visible_panel in cmds.getPanel(visiblePanels=True) or []:
        if cmds.getPanel(typeOf=visible_panel) == "modelPanel":
            panel = visible_panel
            break

    if not panel:
        print("no viewport, skipping thumbnails")
        return

    for view in ("front", "top"):
        cmds.select(nodes)
        cmds.setFocus(panel)
        mel.eval(f"lookThru {panel} {view}")
        cmds.viewFit(fitFactor=0.9)
        cmds.refresh(force=True)

        output_path = os.path.join(temp_dir, f"{name}_{view}.jpg")
        cmds.playblast(
            startTime=cmds.currentTime(query=True),
            endTime=cmds.currentTime(query=True),
            format="image",
            completeFilename=output_path,
            compression="jpg",
            widthHeight=[512, 512],
            percent=100,
            viewer=False,
            forceOverwrite=True,
        )
        _upload_thumbnail(name, view, output_path)

    cmds.setFocus(panel)
    mel.eval(f"lookThru {panel} persp")


def upload() -> None:
    """Pick a .obj file, upload it, and capture thumbnails for it.

    The file is imported temporarily so the thumbnails can be taken,
    then the imported nodes are deleted again.
    """
    if not _server_up() or not _check_login():
        return
    path = cmds.fileDialog2(fileFilter="OBJ Files (*.obj)", dialogStyle=2, fm=1)
    if not path:
        return
    path = path[0]

    status, data = _multipart_upload(path)
    if status != 200:
        QMessageBox.critical(None, "Error", str(data))
        return

    name = os.path.basename(path).replace(".obj", "")
    nodes_before = set(cmds.ls(dag=True, long=True))
    cmds.file(
        path,
        i=True,
        type="OBJ",
        ignoreVersion=True,
        mergeNamespacesOnClash=True,
        namespace=":",
    )
    new_nodes = list(set(cmds.ls(dag=True, long=True)) - nodes_before)

    if new_nodes:
        _take_thumbnails(name, new_nodes)
        cmds.delete(new_nodes)
    else:
        print("nothing imported, skipping thumbnails")

    cmds.select(clear=True)
    QMessageBox.information(None, "Done", f"Uploaded: {os.path.basename(path)}")


def get_ready() -> list[dict]:
    """Show which assets are marked ready on the server."""
    if not _server_up() or not _check_login():
        return []
    assets = json.loads(urllib.request.urlopen(f"{SERVER}/api/assets/ready").read())
    if not assets:
        QMessageBox.information(None, "Pipeline", "No assets ready")
        return []
    message = f"{len(assets)} asset(s) ready:\n\n" + "\n".join(
        f"  - {asset['name']}" for asset in assets
    )
    QMessageBox.information(None, "Ready Assets", message)
    return assets


def import_asset(name: str) -> None:
    """Download one asset from the server and import it into the scene."""
    temp_path = os.path.join(tempfile.gettempdir(), f"{name}.obj")
    urllib.request.urlretrieve(f"{SERVER}/api/assets/download/{name}", temp_path)
    cmds.file(
        temp_path,
        i=True,
        type="OBJ",
        ignoreVersion=True,
        mergeNamespacesOnClash=True,
        namespace=":",
    )
    print(f"imported {name}")


def import_all_ready() -> None:
    """Import every ready asset into the current scene."""
    if not _server_up() or not _check_login():
        return
    assets = get_ready()
    if not assets:
        return
    for asset in assets:
        try:
            import_asset(asset["name"])
        except Exception as exc:
            print(f"failed to import {asset['name']}: {exc}")
    QMessageBox.information(None, "Done", f"Imported {len(assets)} asset(s)")


def _set_ready_state(endpoint: str, title: str, done_message: str) -> None:
    """Shared logic for marking/unmarking an asset as ready."""
    if not _server_up() or not _check_login():
        return
    asset_name = _ask_asset_name(title)
    if not asset_name:
        return
    connection = _connect()
    connection.request("PATCH", f"/api/assets/{asset_name}/{endpoint}")
    response = connection.getresponse()
    connection.close()
    if response.status == 200:
        QMessageBox.information(None, "Done", done_message.format(asset_name))
    else:
        QMessageBox.critical(None, "Error", f"could not find {asset_name}")


def mark_ready() -> None:
    """Mark an asset on the server as ready."""
    _set_ready_state("ready", "Mark Ready", "{} marked as ready")


def unmark_ready() -> None:
    """Take an asset on the server out of the ready pool."""
    _set_ready_state("unready", "Unmark Ready", "{} unmarked")


def setup_shelf() -> None:
    """Create (or recreate) the OBJPipeline shelf with all tool buttons."""
    shelf = "OBJPipeline"
    if cmds.shelfLayout(shelf, exists=True):
        cmds.deleteUI(shelf)
    cmds.shelfLayout(shelf, parent="ShelfLayout")

    pipeline_dir = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
    base = f"import sys\nsys.path.append(r'{pipeline_dir}')\nimport pipeline\n"

    cmds.shelfButton(
        label="UPL",
        annotation="Upload .obj to pipeline",
        imageOverlayLabel="UPL",
        image="commandButton.png",
        parent=shelf,
        command=base + "pipeline.upload()",
    )

    cmds.shelfButton(
        label="IMP",
        annotation="Import all ready assets",
        imageOverlayLabel="IMP",
        image="commandButton.png",
        parent=shelf,
        command=base + "pipeline.import_all_ready()",
    )

    cmds.shelfButton(
        label="CHK",
        annotation="Check whats ready on server",
        imageOverlayLabel="CHK",
        image="commandButton.png",
        parent=shelf,
        command=base + "pipeline.get_ready()",
    )

    cmds.shelfButton(
        label="RDY",
        annotation="Mark an asset as ready",
        imageOverlayLabel="RDY",
        image="commandButton.png",
        parent=shelf,
        command=base + "pipeline.mark_ready()",
    )

    cmds.shelfButton(
        label="URDY",
        annotation="Unmark an asset as ready",
        imageOverlayLabel="URDY",
        image="commandButton.png",
        parent=shelf,
        command=base + "pipeline.unmark_ready()",
    )

    print("shelf ready")
