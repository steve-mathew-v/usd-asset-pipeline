"""Terminal menu for managing the server and Atlas database users."""

import getpass
import os
import subprocess
import sys

import requests
from dotenv import load_dotenv
from requests.auth import HTTPDigestAuth

load_dotenv()

ATLAS_PUBLIC_KEY = os.getenv("ATLAS_PUBLIC_KEY")
ATLAS_PRIVATE_KEY = os.getenv("ATLAS_PRIVATE_KEY")
ATLAS_PROJECT_ID = os.getenv("ATLAS_PROJECT_ID")
ATLAS_URL = f"https://cloud.mongodb.com/api/atlas/v1.0/groups/{ATLAS_PROJECT_ID}"


def login() -> bool:
    """Ask for root credentials and check them against the .env file."""
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    if username == os.getenv("ROOT_USER") and password == os.getenv("ROOT_PASS"):
        print(f"logged in as {username}")
        return True
    print("wrong credentials")
    return False


def create_user() -> None:
    """Create a new database user through the Atlas Admin API."""
    username = input("username: ")
    password = getpass.getpass("password: ")
    role = input("role (readWrite): ").strip() or "readWrite"

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
        print(f"created {username}")
    else:
        print(f"failed: {response.json()}")


def list_users() -> None:
    """Print every database user and their roles."""
    response = requests.get(
        f"{ATLAS_URL}/databaseUsers",
        auth=HTTPDigestAuth(ATLAS_PUBLIC_KEY, ATLAS_PRIVATE_KEY),
    )
    if response.status_code == 200:
        for user in response.json().get("results", []):
            roles = [role["roleName"] for role in user.get("roles", [])]
            print(f"  {user['username']} -> {', '.join(roles)}")
    else:
        print("failed to get users")


def delete_user() -> None:
    """Delete a database user through the Atlas Admin API."""
    username = input("username to delete: ").strip()
    response = requests.delete(
        f"{ATLAS_URL}/databaseUsers/admin/{username}",
        auth=HTTPDigestAuth(ATLAS_PUBLIC_KEY, ATLAS_PRIVATE_KEY),
    )
    if response.status_code == 204:
        print(f"deleted {username}")
    else:
        print(f"failed: {response.json()}")


def start_server() -> None:
    """Launch uvicorn in its own console window."""
    subprocess.Popen(
        ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    print("server up at http://localhost:8000")


def menu() -> None:
    """Main menu loop."""
    while True:
        print("\n1. start server\n2. create user\n3. list users\n4. delete user\n5. exit")
        choice = input("choice: ").strip()

        if choice == "1":
            start_server()
        elif choice == "2":
            create_user()
        elif choice == "3":
            list_users()
        elif choice == "4":
            delete_user()
        elif choice == "5":
            sys.exit(0)
        else:
            print("invalid")


if __name__ == "__main__":
    if login():
        menu()
    else:
        sys.exit(1)
