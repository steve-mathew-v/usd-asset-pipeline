import os
import sys
import subprocess
import requests
import getpass
from requests.auth import HTTPDigestAuth
from dotenv import load_dotenv

load_dotenv()

PUBLIC_KEY = os.getenv("ATLAS_PUBLIC_KEY")
PRIVATE_KEY = os.getenv("ATLAS_PRIVATE_KEY")
PROJECT_ID = os.getenv("ATLAS_PROJECT_ID")

BASE_URL = f"https://cloud.mongodb.com/api/atlas/v1.0/groups/{PROJECT_ID}"


def login():
    print("\n--- Root Admin Login ---")
    username = input("Username: ")
    password = getpass.getpass("Password: ")

    root_user = os.getenv("ROOT_USER")
    root_pass = os.getenv("ROOT_PASS")

    if username == root_user and password == root_pass:
        print(f"Logged in as {username}")
        return True
    else:
        print("Invalid credentials")
        return False


def create_user():
    print("\n--- Create New User ---")
    username = input("New username: ")
    password = getpass.getpass("New password: ")
    print("Roles: read, readWrite, dbAdmin, atlasAdmin")
    role = input("Role (default: readWrite): ").strip() or "readWrite"

    url = f"{BASE_URL}/databaseUsers"
    payload = {
        "databaseName": "admin",
        "username": username,
        "password": password,
        "roles": [
            {
                "roleName": role,
                "databaseName": "obj_pipeline"
            }
        ]
    }

    response = requests.post(
        url,
        auth=HTTPDigestAuth(PUBLIC_KEY, PRIVATE_KEY),
        json=payload
    )

    if response.status_code == 201:
        print(f"User '{username}' created with role '{role}'")
    else:
        print(f"Failed to create user: {response.json()}")


def list_users():
    url = f"{BASE_URL}/databaseUsers"
    response = requests.get(url, auth=HTTPDigestAuth(PUBLIC_KEY, PRIVATE_KEY))
    if response.status_code == 200:
        users = response.json().get("results", [])
        print(f"\n{len(users)} user(s):")
        for u in users:
            roles = [r["roleName"] for r in u.get("roles", [])]
            print(f"  - {u['username']} -> {', '.join(roles)}")
    else:
        print("Failed to list users")


def start_server():
    print("\nStarting server...")
    subprocess.Popen(
        ["uvicorn", "main:app", "--reload", "--port", "8000"],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    print("Server started at http://localhost:8000")


def menu():
    while True:
        print("\n=== OBJ Pipeline ===")
        print("1. Start server")
        print("2. Create new user")
        print("3. List users")
        print("4. Exit")

        choice = input("\nChoice: ").strip()

        if choice == "1":
            start_server()
        elif choice == "2":
            create_user()
        elif choice == "3":
            list_users()
        elif choice == "4":
            print("Bye!")
            sys.exit(0)
        else:
            print("Invalid choice")


if __name__ == "__main__":
    if login():
        menu()
    else:
        sys.exit(1)
