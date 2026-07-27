"""Maya-side tools for the USD asset pipeline.

Artists publish the current selection as a USD asset (each publish is a new
version), approve a version for others, and import approved or pinned
versions. Talks to the central server over HTTP; dialogs use PySide6.
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
# edit this line. Include the scheme (http/https) and no trailing slash.
SERVER = os.environ.get(
    "PIPELINE_SERVER", "https://usd-asset-pipeline.onrender.com"
).rstrip("/")

_logged_in = False
_current_user: Optional[str] = None


def _connect():
    """Open an HTTP or HTTPS connection based on SERVER's scheme."""
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
        urllib.request.urlopen(f"{SERVER}/", timeout=30)
        return True
    except Exception:
        QMessageBox.critical(None, "Error", "Server is not reachable")
        return False


def _ask(title: str, label: str) -> Optional[str]:
    """Prompt for a line of text. Returns None if cancelled or empty."""
    text, ok = QInputDialog.getText(None, title, label)
    text = text.strip()
    return text if (ok and text) else None


def _load_usd_plugin() -> None:
    """Make sure Maya's USD plugin is available."""
    if not cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
        cmds.loadPlugin("mayaUsdPlugin")


def _export_usd(path: str, nodes: list) -> None:
    """Export the given nodes (or the whole scene) to a USD file."""
    _load_usd_plugin()
    if nodes:
        cmds.select(nodes, replace=True)
        cmds.file(path, force=True, exportSelected=True, type="USD Export")
    else:
        cmds.file(path, force=True, exportAll=True, type="USD Export")


def _multipart_upload(filepath: str) -> tuple[int, dict]:
    """Upload a USD file to the server as a new version."""
    filename = os.path.basename(filepath)
    boundary = "----MayaPipelineBoundary"
    with open(filepath, "rb") as usd_file:
        file_data = usd_file.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

    uploader = _current_user or "unknown"
    url = f"/api/assets/upload?source_tool=Maya&uploaded_by={uploader}"
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


def _upload_thumbnail(name: str, view: str, version: int, filepath: str) -> None:
    """Upload one viewport screenshot for a specific version."""
    boundary = "----ThumbBoundary"
    with open(filepath, "rb") as image_file:
        image_data = image_file.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; '
        f'filename="{os.path.basename(filepath)}"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode() + image_data + f"\r\n--{boundary}--\r\n".encode()

    connection = _connect()
    connection.request(
        "POST",
        f"/api/assets/{name}/thumbnail/{view}?version={version}",
        body=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
    )
    response = connection.getresponse()
    connection.close()
    print(f"{view} thumb {'ok' if response.status == 200 else 'failed'}")


def _take_thumbnails(name: str, version: int, nodes: list) -> None:
    """Playblast front and top screenshots of the nodes and upload them."""
    if not nodes:
        print("nothing to thumbnail, skipping")
        return

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

        out = os.path.join(temp_dir, f"{name}_{view}.jpg")
        cmds.playblast(
            startTime=cmds.currentTime(query=True),
            endTime=cmds.currentTime(query=True),
            format="image",
            completeFilename=out,
            compression="jpg",
            widthHeight=[512, 512],
            percent=100,
            viewer=False,
            forceOverwrite=True,
        )
        _upload_thumbnail(name, view, version, out)

    cmds.setFocus(panel)
    mel.eval(f"lookThru {panel} persp")


def publish() -> None:
    """Export the current selection as USD and publish it as a new version."""
    if not _server_up() or not _check_login():
        return
    name = _ask("Publish Asset", "Asset name:")
    if not name:
        return

    nodes = cmds.ls(selection=True, long=True) or []
    temp_path = os.path.join(tempfile.gettempdir(), f"{name}.usd")
    try:
        _export_usd(temp_path, nodes)
    except Exception as exc:
        QMessageBox.critical(None, "Export failed", str(exc))
        return

    status, data = _multipart_upload(temp_path)
    if status != 200:
        QMessageBox.critical(None, "Error", str(data))
        return

    version = data.get("version")
    thumb_nodes = nodes or cmds.ls(geometry=True, long=True)
    _take_thumbnails(name, version, thumb_nodes)
    cmds.select(clear=True)
    QMessageBox.information(None, "Published", f"{name} published as v{version}")


def get_ready() -> list:
    """Show which assets have an approved version ready to import."""
    if not _server_up() or not _check_login():
        return []
    assets = json.loads(urllib.request.urlopen(f"{SERVER}/api/assets/ready").read())
    if not assets:
        QMessageBox.information(None, "Pipeline", "No assets ready")
        return []
    lines = "\n".join(
        f"  - {a['name']}  (v{a['approved_version']})" for a in assets
    )
    QMessageBox.information(None, "Ready Assets", f"{len(assets)} ready:\n\n{lines}")
    return assets


def _import_usd(name: str, url: str) -> None:
    """Download a USD file from the server and import it into the scene."""
    _load_usd_plugin()
    temp_path = os.path.join(tempfile.gettempdir(), f"{name}.usd")
    urllib.request.urlretrieve(url, temp_path)
    cmds.file(temp_path, i=True, type="USD Import", ignoreVersion=True)
    print(f"imported {name}")


def import_all_ready() -> None:
    """Import the approved version of every ready asset."""
    if not _server_up() or not _check_login():
        return
    assets = get_ready()
    if not assets:
        return
    for asset in assets:
        try:
            _import_usd(asset["name"], f"{SERVER}/api/assets/download/{asset['name']}")
        except Exception as exc:
            print(f"failed to import {asset['name']}: {exc}")
    QMessageBox.information(None, "Done", f"Imported {len(assets)} asset(s)")


def import_version() -> None:
    """Pick an asset and a specific version, and import that exact version."""
    if not _server_up() or not _check_login():
        return
    name = _ask("Import Version", "Asset name:")
    if not name:
        return
    try:
        info = json.loads(
            urllib.request.urlopen(f"{SERVER}/api/assets/{name}/versions").read()
        )
    except Exception:
        QMessageBox.critical(None, "Error", f"could not find {name}")
        return

    lines = "\n".join(
        f"  v{v['version']} - by {v['uploaded_by']}" for v in info["versions"]
    )
    msg = (
        f"{name}\nlatest: v{info['latest_version']}   "
        f"approved: v{info['approved_version']}\n\n{lines}"
    )
    QMessageBox.information(None, "Version History", msg)

    picked = _ask("Import Version", "Version number to import:")
    if not picked:
        return
    _import_usd(name, f"{SERVER}/api/assets/download/{name}?version={picked}")
    QMessageBox.information(None, "Done", f"Imported {name} v{picked}")


def _set_approval(endpoint: str, title: str, done_message: str) -> None:
    """Shared logic for approving / unapproving an asset (latest version)."""
    if not _server_up() or not _check_login():
        return
    name = _ask(title, "Asset name:")
    if not name:
        return
    connection = _connect()
    connection.request("PATCH", f"/api/assets/{name}/{endpoint}")
    response = connection.getresponse()
    connection.close()
    if response.status == 200:
        QMessageBox.information(None, "Done", done_message.format(name))
    else:
        QMessageBox.critical(None, "Error", f"could not find {name}")


def approve() -> None:
    """Approve the latest version of an asset for others to use."""
    _set_approval("approve", "Approve", "{} approved (latest version)")


def unapprove() -> None:
    """Take an asset out of the approved pool."""
    _set_approval("unapprove", "Unapprove", "{} unapproved")


def setup_shelf() -> None:
    """Create (or recreate) the OBJPipeline shelf with all tool buttons."""
    shelf = "OBJPipeline"
    if cmds.shelfLayout(shelf, exists=True):
        cmds.deleteUI(shelf)
    cmds.shelfLayout(shelf, parent="ShelfLayout")

    pipeline_dir = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
    base = f"import sys\nsys.path.append(r'{pipeline_dir}')\nimport pipeline\n"

    cmds.shelfButton(label="PUB", annotation="Publish selection as a USD version",
                     imageOverlayLabel="PUB", image="commandButton.png",
                     parent=shelf, command=base + "pipeline.publish()")

    cmds.shelfButton(label="IMP", annotation="Import all approved assets",
                     imageOverlayLabel="IMP", image="commandButton.png",
                     parent=shelf, command=base + "pipeline.import_all_ready()")

    cmds.shelfButton(label="CHK", annotation="Check what's approved on the server",
                     imageOverlayLabel="CHK", image="commandButton.png",
                     parent=shelf, command=base + "pipeline.get_ready()")

    cmds.shelfButton(label="VER", annotation="Version history / import a version",
                     imageOverlayLabel="VER", image="commandButton.png",
                     parent=shelf, command=base + "pipeline.import_version()")

    cmds.shelfButton(label="OK", annotation="Approve the latest version",
                     imageOverlayLabel="OK", image="commandButton.png",
                     parent=shelf, command=base + "pipeline.approve()")

    cmds.shelfButton(label="NO", annotation="Unapprove an asset",
                     imageOverlayLabel="NO", image="commandButton.png",
                     parent=shelf, command=base + "pipeline.unapprove()")

    print("shelf ready")
