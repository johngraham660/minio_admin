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
import json
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


def substitute_env_vars_in_config(config_data):
    """
    Substitute environment variables in configuration data for usernames
    
    This function looks for strings that match the pattern ${VAR_NAME} in usernames
    and replaces them with the actual environment variable values.
    
    Args:
        config_data (dict): The configuration dictionary
        
    Returns:
        dict: Configuration data with environment variables substituted
    """
    import copy
    import re
    
    config_copy = copy.deepcopy(config_data)
    
    # Get all environment variables that match MINIO_USER_* pattern with fallback defaults
    # This ensures compatibility when .env file is missing or incomplete
    username_mappings = {
        "MINIO_USER_CONCOURSE": os.getenv("MINIO_USER_CONCOURSE", "user1"),
        "MINIO_USER_JENKINS": os.getenv("MINIO_USER_JENKINS", "user2"),
        "MINIO_USER_K8S": os.getenv("MINIO_USER_K8S", "user3")
    }
    
    # Substitute usernames in the users section
    if 'users' in config_copy:
        for user_config in config_copy['users']:
            username = user_config.get('username', '')
            # Look for ${MINIO_USER_*} pattern and replace with env var value
            for env_var, actual_username in username_mappings.items():
                pattern = f'${{{env_var}}}'
                if pattern in username:
                    user_config['username'] = username.replace(pattern, actual_username)
                    break
                # Also handle direct env var name without ${} wrapper (alternative format)
                elif username == env_var:
                    user_config['username'] = actual_username
                    break
    
    return config_copy


def load_config():
    """
    Load and parse the MinIO server configuration file
    
    Returns:
        dict: Configuration data with environment variables substituted
        
    Raises:
        FileNotFoundError: If configuration file is not found
        json.JSONDecodeError: If configuration file is not valid JSON
    """
    config_file = script_dir.parent / 'config' / 'minio_server_config.json'
    
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # Substitute environment variables for usernames
        config_data = substitute_env_vars_in_config(config_data)
        
        return config_data
        
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON in configuration file: {e}")


def setup_minio_user_secrets():
    """
    Set up MinIO user secrets in Vault

    This function will:
    1. Load user configuration from minio_server_config.json
    2. Connect to Vault using AppRole authentication
    3. Prompt for passwords for all configured MinIO users
    4. Store passwords in Vault under the specified path
    5. Verify the secrets were stored correctly
    """

    print("🔧 Setting up MinIO user secrets in HashiCorp Vault")
    print("=" * 60)

    try:
        # Connect to Vault
        print("🔗 Connecting to Vault...")
        vault_client = get_vault_client()
        print(f"✅ Successfully connected to Vault at {vault_client.vault_url}")

        # Load configuration file
        print("📖 Loading user configuration...")
        try:
            config_data = load_config()
            users = config_data.get('users', [])
            
            if not users:
                print("❌ Error: No users found in configuration file")
                return False
                
            print(f"✅ Found {len(users)} users in configuration")
            
            # Check for users with fallback defaults and warn user
            fallback_users = []
            for user in users:
                username = user.get('username', '')
                if username in ['user1', 'user2', 'user3']:
                    fallback_users.append(username)
            
            if fallback_users:
                print(f"\n⚠️ WARNING: {len(fallback_users)} users are using fallback defaults:")
                for username in fallback_users:
                    print(f"  - {username}")
                print("💡 Consider setting MINIO_USER_* environment variables in your .env file")
                print("   for more meaningful usernames (see .env.example)")
                
                response = input("\nContinue with fallback usernames? (y/N): ").strip().lower()
                if response not in ['y', 'yes']:
                    print("Setup cancelled. Please configure your .env file and try again.")
                    return False
            
        except Exception as e:
            print(f"❌ Error loading configuration: {e}")
            return False

        # Collect passwords for all configured users
        user_passwords = {}
        print("\n🔐 Please enter passwords for the configured users:")
        
        for user_config in users:
            username = user_config.get('username')
            if not username:
                print(f"⚠️ Warning: Skipping user config with missing username: {user_config}")
                continue
                
            password = input(f"Enter password for {username}: ").strip()
            if not password:
                print(f"❌ Error: Empty password provided for {username}")
                return False
            user_passwords[username] = password

        # Store secrets in Vault
        # Use the vault_path from the first user config (all users share the same path)
        vault_path_full = users[0].get('vault_path', 'secret/data/minio/users')
        vault_path = vault_path_full.replace('secret/data/', '')  # Path for KV v2 engine
        print(f"\n📝 Storing secrets at path: {vault_path_full}")

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
                retrieved_password = vault_client.get_user_password(username, vault_path_full)
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
