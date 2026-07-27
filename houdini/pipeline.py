"""Houdini-side tools for the USD asset pipeline.

Mirrors the Maya tools: publish the selected geometry as a USD asset (each
publish is a new version), approve a version, and import approved or pinned
versions. Uses Houdini's built-in dialogs (hou.ui) so no Qt binding is needed.

NOTE: the HTTP parts match the tested Maya client. The Houdini-specific
export/import/shelf calls are best-effort and may need small adjustments for
your Houdini version.
"""

import http.client
import json
import os
import tempfile
import urllib.request
from typing import Optional
from urllib.parse import urlparse

import hou

# Server address. Override with the PIPELINE_SERVER environment variable.
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


def _show_login() -> bool:
    """Prompt for credentials and check them against the server."""
    global _current_user
    button, values = hou.ui.readMultiInput(
        "Pipeline Login",
        ("Username", "Password"),
        password_input_indices=(1,),
        buttons=("Login", "Cancel"),
        default_choice=0,
        close_choice=1,
        title="Pipeline Login",
    )
    if button != 0:
        return False
    username, password = values[0].strip(), values[1]
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
            return True
        hou.ui.displayMessage("Wrong username or password",
                              severity=hou.severityType.Warning)
        return False
    except Exception as exc:
        hou.ui.displayMessage(f"Could not reach server:\n{exc}",
                              severity=hou.severityType.Error)
        return False


def _check_login() -> bool:
    """Show the login dialog once per Houdini session."""
    global _logged_in
    if not _logged_in:
        _logged_in = _show_login()
    return _logged_in


def _server_up() -> bool:
    """Ping the server, with a popup if it is not reachable."""
    try:
        urllib.request.urlopen(f"{SERVER}/", timeout=30)
        return True
    except Exception:
        hou.ui.displayMessage("Server is not reachable",
                              severity=hou.severityType.Error)
        return False


def _ask(title: str, label: str) -> Optional[str]:
    """Prompt for a line of text. Returns None if cancelled or empty."""
    button, value = hou.ui.readInput(label, buttons=("OK", "Cancel"), title=title)
    value = value.strip()
    return value if (button == 0 and value) else None


def _selected_geometry():
    """Return the geometry of the selected SOP or object node."""
    selected = hou.selectedNodes()
    if not selected:
        raise RuntimeError("Select an object or SOP to publish")
    node = selected[0]
    if isinstance(node, hou.SopNode):
        return node.geometry()
    if isinstance(node, hou.ObjNode):
        display = node.displayNode()
        if display:
            return display.geometry()
    raise RuntimeError("Could not get geometry from the selection")


def _multipart_upload(filepath: str) -> tuple[int, dict]:
    """Upload a USD file to the server as a new version."""
    filename = os.path.basename(filepath)
    boundary = "----HoudiniPipelineBoundary"
    with open(filepath, "rb") as usd_file:
        file_data = usd_file.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

    uploader = _current_user or "unknown"
    url = f"/api/assets/upload?source_tool=Houdini&uploaded_by={uploader}"
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


def publish() -> None:
    """Export the selected geometry as USD and publish it as a new version."""
    if not _server_up() or not _check_login():
        return
    name = _ask("Publish Asset", "Asset name:")
    if not name:
        return
    try:
        geometry = _selected_geometry()
    except Exception as exc:
        hou.ui.displayMessage(str(exc), severity=hou.severityType.Error)
        return

    temp_path = os.path.join(tempfile.gettempdir(), f"{name}.usd")
    try:
        geometry.saveToFile(temp_path)
    except Exception as exc:
        hou.ui.displayMessage(f"USD export failed:\n{exc}",
                              severity=hou.severityType.Error)
        return

    status, data = _multipart_upload(temp_path)
    if status != 200:
        hou.ui.displayMessage(str(data), severity=hou.severityType.Error)
        return
    hou.ui.displayMessage(f"{name} published as v{data.get('version')}")


def get_ready() -> list:
    """Show which assets have an approved version ready to import."""
    if not _server_up() or not _check_login():
        return []
    assets = json.loads(urllib.request.urlopen(f"{SERVER}/api/assets/ready").read())
    if not assets:
        hou.ui.displayMessage("No assets ready")
        return []
    lines = "\n".join(f"  - {a['name']}  (v{a['approved_version']})" for a in assets)
    hou.ui.displayMessage(f"{len(assets)} ready:\n\n{lines}")
    return assets


def _import_usd(name: str, url: str) -> None:
    """Download a USD file and bring it into the scene via a File SOP."""
    temp_path = os.path.join(tempfile.gettempdir(), f"{name}.usd")
    urllib.request.urlretrieve(url, temp_path)
    geo = hou.node("/obj").createNode("geo", node_name=name)
    file_sop = geo.createNode("file")
    file_sop.parm("file").set(temp_path)
    file_sop.setDisplayFlag(True)
    file_sop.setRenderFlag(True)
    geo.layoutChildren()
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
    hou.ui.displayMessage(f"Imported {len(assets)} asset(s)")


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
        hou.ui.displayMessage(f"could not find {name}",
                              severity=hou.severityType.Error)
        return

    lines = "\n".join(
        f"  v{v['version']} - by {v['uploaded_by']}" for v in info["versions"]
    )
    hou.ui.displayMessage(
        f"{name}\nlatest: v{info['latest_version']}   "
        f"approved: v{info['approved_version']}\n\n{lines}"
    )

    picked = _ask("Import Version", "Version number to import:")
    if not picked:
        return
    _import_usd(name, f"{SERVER}/api/assets/download/{name}?version={picked}")
    hou.ui.displayMessage(f"Imported {name} v{picked}")


def _set_approval(endpoint: str, done_message: str) -> None:
    """Shared logic for approving / unapproving an asset (latest version)."""
    if not _server_up() or not _check_login():
        return
    name = _ask("Approval", "Asset name:")
    if not name:
        return
    connection = _connect()
    connection.request("PATCH", f"/api/assets/{name}/{endpoint}")
    response = connection.getresponse()
    connection.close()
    if response.status == 200:
        hou.ui.displayMessage(done_message.format(name))
    else:
        hou.ui.displayMessage(f"could not find {name}",
                              severity=hou.severityType.Error)


def approve() -> None:
    """Approve the latest version of an asset for others to use."""
    _set_approval("approve", "{} approved (latest version)")


def unapprove() -> None:
    """Take an asset out of the approved pool."""
    _set_approval("unapprove", "{} unapproved")
