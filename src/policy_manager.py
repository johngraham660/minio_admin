import os
from minio import Minio
from minio import MinioAdmin
from minio.commonconfig import REPLACE
from minio.error import S3Error
from dotenv import load_dotenv
import json
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def connect_admin():
    """Connect to MinIO as an admin using credentials from environment variables."""
    endpoint = os.getenv("MINIO_ENDPOINT")
    access_key = os.getenv("MINIO_ACCESS_KEY")
    secret_key = os.getenv("MINIO_SECRET_KEY")
    secure = os.getenv("MINIO_SECURE", "False").lower() == "true"

    logging.info(f"Connecting to server at http://{endpoint}")
    logging.info(f"Using MINIO_ACCESS_KEY={access_key}")
    logging.info(f"Using MINIO_SECRET_KEY={secret_key}")
    logging.info(f"Using sercure http access: {secure}")
    

    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


def load_policy(policy_name: str) -> str:
    """Load a JSON policy file as a string."""
    policy_path = os.path.join(os.path.dirname(__file__), "..", "policies", policy_name)
    with open(policy_path, "r") as f:
        return f.read()


def apply_policy(admin_client, policy_name: str, policy_text: str):
    """Upload (create or update) a policy in MinIO."""
    print(f"🛠️ Applying policy: {policy_name}")
    admin_client.policy_add(policy_name, policy_text, "json")


def create_user(admin_client, username: str, password: str, policy_name: str):
    """Create a user and attach a policy."""
    print(f"👤 Creating user: {username}")
    try:
        admin_client.user_add(username, password, policy_name)
    except S3Error as e:
        if "already exists" in str(e):
            print(f"⚠️ User {username} already exists, updating policy...")
            admin_client.user_policy_set(username, policy_name)
        else:
            raise


def main():
    admin_client = connect_admin()

    users = [
        {"username": "admin_user", "password": "AdminPass123!", "policy": "virtua-admin-policy.json"},
        {"username": "ci_cd_bot", "password": "CiCdPass123!", "policy": "virtua-devops-policy.json"},
        {"username": "dev_john", "password": "DevPass123!", "policy": "virtua-developer-policy.json"},
        {"username": "audit_claire", "password": "AuditPass123!", "policy": "virtua-auditor-policy.json"},
    ]

    for user in users:
        policy_text = load_policy(user["policy"])
        policy_name = os.path.splitext(user["policy"])[0]

        apply_policy(admin_client, policy_name, policy_text)
        create_user(admin_client, user["username"], user["password"], policy_name)

    print("\n✅ All users and policies applied successfully!")


if __name__ == "__main__":
    main()

