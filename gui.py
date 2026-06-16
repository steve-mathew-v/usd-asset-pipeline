"""PySide6 management GUI for the OBJ pipeline server."""

import os
import subprocess
import sys

import requests
from dotenv import load_dotenv
from requests.auth import HTTPDigestAuth

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFormLayout, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QTabWidget,
    QVBoxLayout, QWidget,
)

load_dotenv()

ATLAS_PUBLIC_KEY = os.getenv("ATLAS_PUBLIC_KEY")
ATLAS_PRIVATE_KEY = os.getenv("ATLAS_PRIVATE_KEY")
ATLAS_PROJECT_ID = os.getenv("ATLAS_PROJECT_ID")
ROOT_USER = os.getenv("ROOT_USER")
ROOT_PASS = os.getenv("ROOT_PASS")

ATLAS_URL = f"https://cloud.mongodb.com/api/atlas/v1.0/groups/{ATLAS_PROJECT_ID}"
# Address the GUI talks to. Defaults to the local server; override with
# PIPELINE_SERVER to point the Assets tab at a remote/cloud server.
SERVER_URL = os.environ.get("PIPELINE_SERVER", "http://localhost:8000").rstrip("/")

server_process = None


class ServerThread(QThread):
    """Starts the uvicorn server in its own console without freezing the GUI."""

    done = Signal()
    err = Signal(str)

    def run(self) -> None:
        global server_process
        try:
            server_process = subprocess.Popen(
                ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            self.done.emit()
        except Exception as exc:
            self.err.emit(str(exc))


class LoginWindow(QDialog):
    """Root login dialog shown before the main window opens."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OBJ Pipeline - Login")
        self.setMinimumSize(380, 260)
        self.resize(420, 280)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 32, 32, 32)

        title = QLabel("OBJ Pipeline")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setMinimumHeight(36)
        self.username_input.setFont(QFont("Arial", 11))

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(36)
        self.password_input.setFont(QFont("Arial", 11))

        username_label = QLabel("User:")
        username_label.setFont(QFont("Arial", 11))
        password_label = QLabel("Pass:")
        password_label.setFont(QFont("Arial", 11))

        form.addRow(username_label, self.username_input)
        form.addRow(password_label, self.password_input)
        layout.addLayout(form)

        login_button = QPushButton("Login")
        login_button.setMinimumHeight(38)
        login_button.setFont(QFont("Arial", 11))
        login_button.clicked.connect(self.try_login)
        self.password_input.returnPressed.connect(self.try_login)
        layout.addWidget(login_button)

        self.message_label = QLabel("")
        self.message_label.setStyleSheet("color: red;")
        self.message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.message_label)

    def try_login(self) -> None:
        """Check the entered credentials against the root account."""
        if (self.username_input.text().strip() == ROOT_USER
                and self.password_input.text() == ROOT_PASS):
            self.accept()
        else:
            self.message_label.setText("Invalid credentials")
            self.password_input.clear()


class ServerTab(QWidget):
    """Tab for starting and stopping the FastAPI server."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Status:"))
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: red; font-size: 18px;")
        self.status_label = QLabel("Stopped")
        status_row.addWidget(self.status_dot)
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        layout.addLayout(status_row)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        self.url_label = QLabel("URL: -")
        self.url_label.setStyleSheet("color: grey;")
        layout.addWidget(self.url_label)

        self.docs_label = QLabel("Docs: -")
        self.docs_label.setStyleSheet("color: grey;")
        layout.addWidget(self.docs_label)

        layout.addStretch()

        button_row = QHBoxLayout()
        self.start_button = QPushButton("Start Server")
        self.start_button.setFixedHeight(36)
        self.start_button.clicked.connect(self.start)

        self.stop_button = QPushButton("Stop Server")
        self.stop_button.setFixedHeight(36)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop)

        button_row.addWidget(self.start_button)
        button_row.addWidget(self.stop_button)
        layout.addLayout(button_row)

    def start(self) -> None:
        """Kick off the server thread."""
        self.start_button.setEnabled(False)
        self.status_label.setText("Starting...")
        self.thread = ServerThread()
        self.thread.done.connect(self.on_start)
        self.thread.err.connect(self.on_error)
        self.thread.start()

    def on_start(self) -> None:
        """Update the tab once the server process is running."""
        self.status_dot.setStyleSheet("color: green; font-size: 18px;")
        self.status_label.setText("Running")
        self.url_label.setText(f"URL: {SERVER_URL}")
        self.url_label.setStyleSheet("color: green;")
        self.docs_label.setText(f"Docs: {SERVER_URL}/docs")
        self.docs_label.setStyleSheet("color: green;")
        self.stop_button.setEnabled(True)

    def on_error(self, error: str) -> None:
        """Show an error popup if the server failed to start."""
        self.status_label.setText("Failed")
        self.start_button.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Could not start server:\n{error}")

    def stop(self) -> None:
        """Kill the whole server process tree (uvicorn --reload spawns children)."""
        global server_process
        if server_process:
            subprocess.call(
                ["taskkill", "/F", "/T", "/PID", str(server_process.pid)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            server_process = None
        self.status_dot.setStyleSheet("color: red; font-size: 18px;")
        self.status_label.setText("Stopped")
        self.url_label.setText("URL: -")
        self.url_label.setStyleSheet("color: grey;")
        self.docs_label.setText("Docs: -")
        self.docs_label.setStyleSheet("color: grey;")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)


class UsersTab(QWidget):
    """Tab for creating and listing Atlas database users."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addWidget(QLabel("Create New User"))

        form = QFormLayout()
        self.new_username_input = QLineEdit()
        self.new_username_input.setPlaceholderText("e.g. maya_tool")
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.Password)
        self.new_password_input.setPlaceholderText("Password")
        self.role_combo = QComboBox()
        self.role_combo.addItems(["readWrite", "read", "dbAdmin", "atlasAdmin"])
        form.addRow("Username:", self.new_username_input)
        form.addRow("Password:", self.new_password_input)
        form.addRow("Role:", self.role_combo)
        layout.addLayout(form)

        create_button = QPushButton("Create User")
        create_button.setFixedHeight(34)
        create_button.clicked.connect(self.create_user)
        layout.addWidget(create_button)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        layout.addWidget(QLabel("Users"))

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Username", "Roles"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.load_users)
        layout.addWidget(refresh_button)

        self.load_users()

    def create_user(self) -> None:
        """Create a new database user through the Atlas Admin API."""
        username = self.new_username_input.text().strip()
        password = self.new_password_input.text()
        role = self.role_combo.currentText()

        if not username or not password:
            QMessageBox.warning(self, "Missing fields", "Fill in username and password.")
            return

        try:
            response = requests.post(
                f"{ATLAS_URL}/databaseUsers",
                auth=HTTPDigestAuth(ATLAS_PUBLIC_KEY, ATLAS_PRIVATE_KEY),
                json={
                    "databaseName": "admin",
                    "username": username,
                    "password": password,
                    "roles": [{"roleName": role, "databaseName": "obj_pipeline"}],
                },
            )
            if response.status_code == 201:
                QMessageBox.information(self, "Done", f"User '{username}' created.")
                self.new_username_input.clear()
                self.new_password_input.clear()
                self.load_users()
            else:
                QMessageBox.critical(self, "Error", str(response.json()))
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))

    def load_users(self) -> None:
        """Fill the table with every database user and their roles."""
        self.table.setRowCount(0)
        try:
            response = requests.get(
                f"{ATLAS_URL}/databaseUsers",
                auth=HTTPDigestAuth(ATLAS_PUBLIC_KEY, ATLAS_PRIVATE_KEY),
            )
            if response.status_code == 200:
                for user in response.json().get("results", []):
                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QTableWidgetItem(user["username"]))
                    roles = ", ".join(r["roleName"] for r in user.get("roles", []))
                    self.table.setItem(row, 1, QTableWidgetItem(roles))
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))


class AssetCard(QFrame):
    """One asset in the assets grid: thumbnails, info and action buttons."""

    deleted = Signal(str)

    def __init__(self, asset: dict) -> None:
        super().__init__()
        self.name = asset["name"]
        self.ready = asset.get("ready", False)
        self.setFrameShape(QFrame.Box)
        self.setFixedWidth(260)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        thumb_row = QHBoxLayout()
        for view in ("front", "top"):
            thumb_label = QLabel()
            thumb_label.setFixedSize(110, 110)
            thumb_label.setAlignment(Qt.AlignCenter)
            thumb_label.setStyleSheet("background: #2a2a2a;")
            try:
                image_bytes = requests.get(
                    f"{SERVER_URL}/api/assets/{self.name}/thumbnail/{view}",
                    timeout=2,
                ).content
                pixmap = QPixmap()
                pixmap.loadFromData(image_bytes)
                thumb_label.setPixmap(
                    pixmap.scaled(110, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            except Exception:
                thumb_label.setText(view)
            thumb_row.addWidget(thumb_label)
        layout.addLayout(thumb_row)

        name_label = QLabel(self.name)
        name_label.setFont(QFont("Arial", 10, QFont.Bold))
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        info_row = QHBoxLayout()
        tool_label = QLabel(asset.get("source_tool") or "unknown")
        tool_label.setStyleSheet("color: grey; font-size: 10px;")
        info_row.addWidget(tool_label)
        info_row.addStretch()
        self.status_label = QLabel("ready" if self.ready else "not ready")
        self.status_label.setStyleSheet(
            f"color: {'green' if self.ready else 'red'}; font-size: 10px;"
        )
        info_row.addWidget(self.status_label)
        layout.addLayout(info_row)

        uploader_label = QLabel(f"uploaded by: {asset.get('uploaded_by') or 'unknown'}")
        uploader_label.setStyleSheet("color: grey; font-size: 10px;")
        layout.addWidget(uploader_label)

        self.ready_button = QPushButton("Unmark Ready" if self.ready else "Mark Ready")
        self.ready_button.setFixedHeight(28)
        self.ready_button.clicked.connect(self.toggle_ready)
        layout.addWidget(self.ready_button)

        delete_button = QPushButton("Delete")
        delete_button.setFixedHeight(28)
        delete_button.setStyleSheet("color: red;")
        delete_button.clicked.connect(self.delete_asset)
        layout.addWidget(delete_button)

    def toggle_ready(self) -> None:
        """Flip the asset's ready state on the server and update the card."""
        endpoint = "unready" if self.ready else "ready"
        try:
            response = requests.patch(f"{SERVER_URL}/api/assets/{self.name}/{endpoint}")
            if response.status_code == 200:
                self.ready = not self.ready
                self.status_label.setText("ready" if self.ready else "not ready")
                self.status_label.setStyleSheet(
                    f"color: {'green' if self.ready else 'red'}; font-size: 10px;"
                )
                self.ready_button.setText("Unmark Ready" if self.ready else "Mark Ready")
            else:
                QMessageBox.critical(self, "Error", str(response.json()))
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))

    def delete_asset(self) -> None:
        """Delete the asset from the server after confirmation."""
        confirm = QMessageBox.question(
            self, "Delete", f"Delete '{self.name}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            response = requests.delete(f"{SERVER_URL}/api/assets/{self.name}")
            if response.status_code == 200:
                self.deleted.emit(self.name)
            else:
                QMessageBox.critical(self, "Error", f"Failed to delete: {response.json()}")
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))


class AssetsTab(QWidget):
    """Tab showing every uploaded asset as a card grid."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("All Assets"))
        header_row.addStretch()
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.load_assets)
        header_row.addWidget(refresh_button)
        layout.addLayout(header_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setSpacing(12)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        scroll.setWidget(self.grid_widget)
        layout.addWidget(scroll)

        self.load_assets()

    def load_assets(self) -> None:
        """Clear the grid and rebuild it from the server's asset list."""
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            response = requests.get(f"{SERVER_URL}/api/assets", timeout=3)
            if response.status_code != 200:
                return
            assets = response.json()
            if not assets:
                empty_label = QLabel("No assets uploaded yet.")
                empty_label.setStyleSheet("color: grey;")
                self.grid.addWidget(empty_label, 0, 0)
                return
            for index, asset in enumerate(assets):
                card = AssetCard(asset)
                card.deleted.connect(self.load_assets)
                self.grid.addWidget(card, index // 3, index % 3)
        except Exception:
            offline_label = QLabel("Server is not running.")
            offline_label.setStyleSheet("color: red;")
            self.grid.addWidget(offline_label, 0, 0)


class MainWindow(QMainWindow):
    """Main window holding the server, users and assets tabs."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OBJ Pipeline")
        self.setMinimumSize(560, 480)

        tabs = QTabWidget()
        tabs.addTab(ServerTab(), "Server")
        tabs.addTab(UsersTab(), "Users")
        tabs.addTab(AssetsTab(), "Assets")
        self.setCentralWidget(tabs)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    login_window = LoginWindow()
    if login_window.exec() != QDialog.Accepted:
        sys.exit(0)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
