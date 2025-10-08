#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

import sys
import os
import logging
import json
from os import getenv
from minio import Minio
from minio import MinioAdmin
from minio.credentials.providers import StaticProvider
from dotenv import load_dotenv
from vault_client import get_vault_client, VaultClient

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def substitute_env_vars_in_config(config_data):
    """
    Substitute environment variables in configuration data for usernames

    This allows keeping sensitive service usernames in environment variables
    instead of committing them to the repository.

    Args:
        config_data: Dictionary containing configuration data

    Returns:
        Dictionary with environment variables substituted
    """
    # Mapping of placeholder usernames to environment variable names
    username_mappings = {
        "MINIO_USER_CONCOURSE": os.getenv("MINIO_USER_CONCOURSE", "user1"),
        "MINIO_USER_JENKINS": os.getenv("MINIO_USER_JENKINS", "user2"),
        "MINIO_USER_K8S": os.getenv("MINIO_USER_K8S", "user3")
    }

    # Create a deep copy to avoid modifying the original
    import copy
    config_copy = copy.deepcopy(config_data)

    # Substitute usernames in user configurations
    if 'users' in config_copy:
        for user_config in config_copy['users']:
            username = user_config.get('username', '')
            # Check if username is a placeholder that should be substituted
            for env_var, actual_username in username_mappings.items():
                if username == f"${{{env_var}}}" or username == env_var:
                    user_config['username'] = actual_username
                    logger.debug(f"Substituted {env_var} -> {actual_username}")
                    break

    return config_copy


def connect() -> Minio:
    """
    Establish a connection to the MinIO server using environment variables

    Returns:
        Minio: A MinIO client instance that can be used to interact with the server.
    """
    # Get connection parameters from environment variables
    minio_server = getenv("MINIO_SERVER", "localhost")
    minio_port_str = getenv("MINIO_PORT")
    minio_secure_str = getenv("MINIO_SECURE", "False")
    bucketcreator_access_key = getenv("BUCKET_CREATOR_ACCESS_KEY", "xyz")
    bucketcreator_secret_key = getenv("BUCKET_CREATOR_SECRET_KEY", "abc")

    # Validate and convert port
    if minio_port_str is None:
        minio_port: int = 9000
    else:
        try:
            minio_port = int(minio_port_str)
        except ValueError:
            logging.error(
                f"MINIO_PORT environment variable {minio_port_str} is not a valid integer")
            sys.exit(1)

    # Convert secure flag
    minio_secure: bool = minio_secure_str.lower() == "true"

    # Log connection details
    logging.info(f"MINIO_SERVER = {minio_server}")
    logging.info(f"MINIO_PORT = {minio_port}")
    logging.info(f"MINIO_SECURE = {minio_secure}")

    # Create and return the client
    client = Minio(
        f"{minio_server}:{minio_port}",
        access_key=bucketcreator_access_key,
        secret_key=bucketcreator_secret_key,
        secure=minio_secure
    )

    return client


def connect_admin() -> MinioAdmin:
    """
    Establish an admin connection to the MinIO server using environment variables

    Returns:
        MinioAdmin: A MinIO admin client instance for administrative operations.
    """
    # Get connection parameters from environment variables
    minio_server = getenv("MINIO_SERVER", "localhost")
    minio_port_str = getenv("MINIO_PORT")
    minio_secure_str = getenv("MINIO_SECURE", "False")
    admin_access_key = getenv("MINIO_ADMIN_ACCESS_KEY", "accesskey_placeholder")
    admin_secret_key = getenv("MINIO_ADMIN_SECRET_KEY", "secretkey_placeholder")

    # Validate and convert port
    if minio_port_str is None:
        minio_port: int = 9000
    else:
        try:
            minio_port = int(minio_port_str)
        except ValueError:
            logging.error(
                f"MINIO_PORT environment variable {minio_port_str} is not a valid integer")
            sys.exit(1)

    # Convert secure flag
    minio_secure: bool = minio_secure_str.lower() == "true"

    # Log connection details
    logging.info(f"MINIO_ADMIN_SERVER = {minio_server}")
    logging.info(f"MINIO_ADMIN_PORT = {minio_port}")
    logging.info(f"MINIO_ADMIN_SECURE = {minio_secure}")

    # Create credentials provider
    credentials = StaticProvider(
        access_key=admin_access_key,
        secret_key=admin_secret_key
    )

    # Create and return the admin client
    admin_client = MinioAdmin(
        endpoint=f"{minio_server}:{minio_port}",
        credentials=credentials,
        secure=minio_secure
    )

    return admin_client


def create_bucket(client: Minio, bucket: str) -> None:
    """
    Create one or more buckets on the MinIO server.

    Args:
        client (Minio)  : The Minio connection instance
        bucket (str)    : The name of the bucket to create.

    Returns:
        None: This function does not return anything
    """
    # Initialize the MinIO client
    client = client

    # Check if the specified bucket exists, if not create it.
    if client.bucket_exists(bucket):
        logging.info(f"Bucket '{bucket}' exists.")
    else:
        # Create the bucket
        logging.info(f"Creating bucket: {bucket}")
        client.make_bucket(bucket)


def load_policy(policy_name: str) -> str:
    """
    Load a JSON policy from a file

    Args:
        policy_name (str): The name of the policy to load

    Returns:
        str: The content of the policy file as a JSON string.
    """
    policy_path = os.path.join(os.path.dirname(__file__), "..", "policies", policy_name)
    with open(policy_path, "r") as f:
        return f.read()


def apply_policy(admin_client: MinioAdmin, policy_name: str, policy_text: str) -> None:
    """
    Create or update a policy in MinIO

    Args:
        admin_client (MinioAdmin): The MinioAdmin connection instance
        policy_name (str): The name of the policy to create/update
        policy_text (str): The policy content as a JSON string

    Returns:
        None: This function does not return anything

    Raises:
        Exception: If policy creation/update fails
    """
    logging.info(f"Applying policy {policy_name}")
    try:
        # Parse the JSON string into a dictionary
        policy_dict = json.loads(policy_text)

        # Use the policy_add method with the parsed policy dictionary
        result = admin_client.policy_add(policy_name, policy=policy_dict)
        logging.info(f"Policy {policy_name} applied successfully: {result}")
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in policy {policy_name}: {e}")
        raise
    except Exception as e:
        logging.error(f"Failed to apply policy {policy_name}: {e}")
        raise


def create_user_with_vault_password(
        admin_client: MinioAdmin,
        username: str,
        vault_client: VaultClient,
        vault_path: str) -> None:
    """
    Create a MinIO user account with password retrieved from Vault

    Args:
        admin_client (MinioAdmin): The MinioAdmin connection instance
        username (str): The username for the new user account
        vault_client (VaultClient): Authenticated Vault client
        vault_path (str): Path to the secrets in Vault

    Returns:
        None: This function does not return anything

    Raises:
        Exception: If user creation fails for reasons other than user already exists
    """
    logging.info(f"Creating User: {username} (password from Vault)")
    try:
        # Get password from Vault
        password = vault_client.get_user_password(username, vault_path)

        # Create the user with access_key (username) and secret_key (password)
        result = admin_client.user_add(username, password)
        logging.info(f"User {username} created successfully: {result}")

    except Exception as e:
        error_str = str(e)
        if "already exists" in error_str.lower():
            logging.info(f"User {username} already exists, skipping creation")
        else:
            logging.error(f"Failed to create user {username}: {e}")
            raise


def create_user(admin_client: MinioAdmin, username: str, password: str) -> None:
    """
    Create a MinIO user account

    Args:
        admin_client (MinioAdmin): The MinioAdmin connection instance
        username (str): The username for the new user account
        password (str): The password for the new user account

    Returns:
        None: This function does not return anything

    Raises:
        Exception: If user creation fails for reasons other than user already exists
    """
    logging.info(f"Creating User: {username}")
    try:
        # Create the user with access_key (username) and secret_key (password)
        result = admin_client.user_add(username, password)
        logging.info(f"User {username} created successfully: {result}")

    except Exception as e:
        error_str = str(e)
        if "already exists" in error_str.lower():
            logging.info(f"User {username} already exists, skipping creation")
        else:
            logging.error(f"Failed to create user {username}: {e}")
            raise


def apply_policy_to_user(admin_client: MinioAdmin, username: str, policy_name: str) -> None:
    """
    Apply a policy to a specific MinIO user

    Args:
        admin_client (MinioAdmin): The MinioAdmin connection instance
        username (str): The username to apply the policy to
        policy_name (str): The name of the policy to apply

    Returns:
        None: This function does not return anything

    Raises:
        Exception: If policy application fails
    """
    logging.info(f"Applying policy {policy_name} to user {username}")
    try:
        # Apply the policy to the user
        policy_result = admin_client.policy_set(policy_name, user=username)
        logging.info(f"Policy {policy_name} applied to user {username}: {policy_result}")

    except Exception as e:
        logging.error(f"Failed to apply policy {policy_name} to user {username}: {e}")
        raise


if __name__ == '__main__':
    # =================================================================
    # Establish a connection to the MinIO Server, using least privilege
    # =================================================================
    connection = connect()
    admin_connection = connect_admin()

    # =================================================================
    # Initialize Vault client for password retrieval
    # =================================================================
    vault_client = None
    try:
        vault_client = get_vault_client()
        print("✅ Successfully connected to HashiCorp Vault")
    except Exception as e:
        print(f"❌ Failed to connect to Vault: {e}")
        print("🔄 Falling back to configuration file passwords")
        # Continue without Vault - will fail if config doesn't have passwords

    # Get the configuration from JSON file
    script_dir = os.path.dirname(__file__)
    config_file = os.path.join(script_dir, '..', 'config', 'minio_server_config.json')

    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)

        # Substitute environment variables for usernames
        config_data = substitute_env_vars_in_config(config_data)

        # =================================================================
        # Create buckets defined in the JSON file
        # =================================================================
        buckets = config_data.get('buckets', [])
        if buckets:
            print("Creating MinIO Buckets:")
            for bucket_name in buckets:
                create_bucket(connection, bucket_name)
        else:
            print("No buckets found in configuration file")

        # =================================================================
        # Create policies and users defined in the JSON file
        # =================================================================
        users = config_data.get('users', [])
        if users:
            print("\nCreating MinIO Users and Policies:")

            # Track which policies we've already created to avoid duplicates
            created_policies = set()

            for user_config in users:
                username = user_config.get('username')
                password = user_config.get('password')  # Legacy support
                vault_path = user_config.get('vault_path', 'secret/data/minio/users')
                policy_file = user_config.get('policy')

                if not all([username, policy_file]):
                    logging.warning(
                        f"Incomplete user configuration (missing username or policy): "
                        f"{user_config}")
                    continue

                # Check if we have Vault client and vault_path, otherwise require password
                if not vault_client and not password:
                    logging.error(
                        f"No Vault connection and no password in config for user "
                        f"'{username}' - skipping")
                    continue

                try:
                    # Extract policy name from filename (remove .json extension)
                    policy_name = os.path.splitext(policy_file)[0]

                    # Create policy if we haven't already
                    if policy_name not in created_policies:
                        policy_text = load_policy(policy_file)
                        apply_policy(admin_connection, policy_name, policy_text)
                        created_policies.add(policy_name)

                    # Create user - prefer Vault over config password
                    if vault_client:
                        create_user_with_vault_password(
                            admin_connection, username, vault_client, vault_path)
                    else:
                        create_user(admin_connection, username, password)

                    # Apply policy to user
                    apply_policy_to_user(admin_connection, username, policy_name)

                    print(f"✅ User '{username}' created with policy '{policy_name}'")

                except Exception as e:
                    print(f"❌ Failed to create user '{username}': {e}")
                    logging.error(f"Error creating user {username}: {e}")

        else:
            print("No users found in configuration file")

    except FileNotFoundError:
        logging.error(f"The configuration file {config_file} was not found.")
        print(f"❌ Configuration file not found: {config_file}")
    except json.JSONDecodeError:
        logging.error(f"Could not decode JSON from {config_file}.")
        print(f"❌ Invalid JSON in configuration file: {config_file}")
    except Exception as e:
        logging.error(f"An unexpected error was encountered: {e}")
        print(f"❌ Unexpected error: {e}")
    finally:
        # Clean up Vault token
        if vault_client:
            try:
                vault_client.revoke_token()
                logger.info("Vault token revoked")
            except Exception as e:
                logger.warning(f"Error revoking Vault token: {e}")

    print("\n🎯 MinIO server setup completed!")
