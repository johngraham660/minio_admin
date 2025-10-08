#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Vault Setup Helper Script

This script helps you set up the required secrets in HashiCorp Vault
for the MinIO admin application. It will store the MinIO user passwords
in Vault under the specified path.

Usage:
    python scripts/setup_vault_secrets.py

Environment Variables Required:
    VAULT_ADDR - URL of your Vault server
    VAULT_ROLE_ID - AppRole role ID
    VAULT_SECRET_ID - AppRole secret ID
"""

import os
import sys
import logging
from pathlib import Path

# Add the src directory to the path
script_dir = Path(__file__).parent
src_dir = script_dir.parent / 'src'
sys.path.insert(0, str(src_dir))

from vault_client import get_vault_client  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_minio_user_secrets():
    """
    Set up MinIO user secrets in Vault

    This function will:
    1. Connect to Vault using AppRole authentication
    2. Store passwords for MinIO service users
    3. Verify the secrets were stored correctly
    """

    print("🔧 Setting up MinIO user secrets in HashiCorp Vault")
    print("=" * 60)

    try:
        # Connect to Vault
        print("🔗 Connecting to Vault...")
        vault_client = get_vault_client()
        print(f"✅ Successfully connected to Vault at {vault_client.vault_url}")

        # Define the user passwords
        # Read usernames from environment variables for security
        concourse_user = os.getenv('MINIO_USER_CONCOURSE', 'user1')
        jenkins_user = os.getenv('MINIO_USER_JENKINS', 'user2')
        k8s_user = os.getenv('MINIO_USER_K8S', 'user3')

        # In production, these should be generated securely or entered interactively
        user_passwords = {
            concourse_user: input(f"Enter password for {concourse_user}: ").strip(),
            jenkins_user: input(f"Enter password for {jenkins_user}: ").strip(),
            k8s_user: input(f"Enter password for {k8s_user}: ").strip()
        }

        # Validate passwords
        for username, password in user_passwords.items():
            if not password:
                print(f"❌ Error: Empty password provided for {username}")
                return False

        # Store secrets in Vault
        secret_path = "secret/data/minio/users"
        vault_path = "minio/users"  # Path for KV v2 engine (without secret/data prefix)
        print(f"\n📝 Storing secrets at path: {secret_path}")

        try:
            # Verify client is properly initialized
            if not vault_client.client or not vault_client.is_authenticated():
                raise Exception("Vault client is not properly authenticated")

            # For KV v2, we need to use the secrets.kv.v2 interface
            # Type: ignore is safe here because we've verified client is authenticated above
            vault_client.client.secrets.kv.v2.create_or_update_secret(  # type: ignore
                path=vault_path,
                secret=user_passwords
            )
            print("✅ Secrets stored successfully!")

        except Exception as e:
            print(f"❌ Error storing secrets: {e}")
            return False

        # Verify secrets were stored correctly
        print("\n🔍 Verifying stored secrets...")
        try:
            for username in user_passwords.keys():
                retrieved_password = vault_client.get_user_password(username, secret_path)
                if retrieved_password == user_passwords[username]:
                    print(f"✅ {username}: Password verified")
                else:
                    print(f"❌ {username}: Password verification failed")
                    return False

        except Exception as e:
            print(f"❌ Error verifying secrets: {e}")
            return False

        print("\n🎉 All MinIO user secrets have been successfully set up in Vault!")
        print("\nNext steps:")
        print("1. Ensure your .env file has the correct Vault configuration")
        print("2. Run 'python src/manage_minio.py' to create MinIO users with Vault passwords")

        # Clean up
        vault_client.revoke_token()
        return True

    except Exception as e:
        print(f"❌ Error setting up Vault secrets: {e}")
        return False


def verify_vault_connection():
    """
    Verify that we can connect to Vault with current configuration
    """
    print("🔍 Verifying Vault connection...")

    # Check environment variables
    required_vars = ['VAULT_ADDR', 'VAULT_ROLE_ID', 'VAULT_SECRET_ID']
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please set these variables in your .env file or environment")
        return False

    try:
        vault_client = get_vault_client()
        print(f"✅ Successfully connected to Vault at {vault_client.vault_url}")
        vault_client.revoke_token()
        return True

    except Exception as e:
        print(f"❌ Failed to connect to Vault: {e}")
        return False


def main():
    """Main function"""
    print("HashiCorp Vault Setup Helper for MinIO Admin")
    print("=" * 50)

    # Verify connection first
    if not verify_vault_connection():
        print("\n💡 Tips:")
        print("- Ensure Vault is running and accessible")
        print("- Check your VAULT_ADDR, VAULT_ROLE_ID, and VAULT_SECRET_ID")
        print("- Verify AppRole authentication is enabled in Vault")
        sys.exit(1)

    # Set up secrets
    if setup_minio_user_secrets():
        print("\n✅ Setup completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Setup failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
