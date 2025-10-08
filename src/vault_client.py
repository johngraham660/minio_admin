#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
from typing import Optional, Dict, Any
import hvac
from hvac.exceptions import VaultError, InvalidPath, Forbidden, Unauthorized

logger = logging.getLogger(__name__)


class VaultClient:
    """
    HashiCorp Vault client for managing secrets using AppRole authentication
    """
    
    def __init__(self, 
                 vault_url: Optional[str] = None, 
                 role_id: Optional[str] = None, 
                 secret_id: Optional[str] = None):
        """
        Initialize the Vault client
        
        Args:
            vault_url: Vault server URL (defaults to VAULT_URL env var)
            role_id: AppRole role ID (defaults to VAULT_ROLE_ID env var)
            secret_id: AppRole secret ID (defaults to VAULT_SECRET_ID env var)
        """
        self.vault_url = vault_url or os.getenv('VAULT_ADDR', 'http://vault.virtua.home:8200')
        self.role_id = role_id or os.getenv('VAULT_ROLE_ID')
        self.secret_id = secret_id or os.getenv('VAULT_SECRET_ID')
        
        if not self.role_id or not self.secret_id:
            raise ValueError("VAULT_ROLE_ID and VAULT_SECRET_ID environment variables must be set")
        
        self.client = None
        self.token = None
        
        logger.info(f"Initializing Vault client for {self.vault_url}")
    
    def authenticate(self) -> bool:
        """
        Authenticate with Vault using AppRole
        
        Returns:
            bool: True if authentication successful, False otherwise
        
        Raises:
            VaultError: If authentication fails
        """
        try:
            # Initialize the hvac client
            self.client = hvac.Client(url=self.vault_url)
            
            # Check if Vault is available
            if not self.client.sys.is_initialized():
                raise VaultError("Vault is not initialized")
            
            if self.client.sys.is_sealed():
                raise VaultError("Vault is sealed")
            
            # Authenticate using AppRole
            logger.info("Authenticating with Vault using AppRole")
            auth_response = self.client.auth.approle.login(
                role_id=self.role_id,
                secret_id=self.secret_id
            )
            
            # Extract token from response
            self.token = auth_response['auth']['client_token']
            self.client.token = self.token
            
            logger.info("Successfully authenticated with Vault")
            return True
            
        except (VaultError, Unauthorized, Forbidden) as e:
            logger.error(f"Vault authentication failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Vault authentication: {e}")
            raise VaultError(f"Authentication failed: {e}")
    
    def get_secret(self, path: str, key: Optional[str] = None) -> Any:
        """
        Retrieve a secret from Vault
        
        Args:
            path: Path to the secret (e.g., 'minio/users' for KV v2 engine)
            key: Specific key within the secret (optional)
        
        Returns:
            The secret value or dictionary of secret values
        
        Raises:
            VaultError: If secret retrieval fails
            InvalidPath: If the secret path doesn't exist
        """
        if not self.client or not self.token:
            raise VaultError("Client not authenticated. Call authenticate() first.")
        
        try:
            logger.debug(f"Retrieving secret from path: {path}")
            
            # For KV v2, remove 'secret/data/' prefix if present since hvac adds it automatically
            clean_path = path
            if path.startswith('secret/data/'):
                clean_path = path[12:]  # Remove 'secret/data/' prefix
            
            # Read secret from Vault
            response = self.client.secrets.kv.v2.read_secret_version(path=clean_path)
            secret_data = response['data']['data']
            
            if key:
                if key not in secret_data:
                    raise InvalidPath(f"Key '{key}' not found in secret at path '{path}'")
                return secret_data[key]
            else:
                return secret_data
                
        except InvalidPath:
            logger.error(f"Secret not found at path: {path}")
            raise
        except Forbidden:
            logger.error(f"Access denied to secret at path: {path}")
            raise
        except Exception as e:
            logger.error(f"Error retrieving secret from {path}: {e}")
            raise VaultError(f"Failed to retrieve secret: {e}")
    
    def get_user_password(self, username: str, secret_path: str = "secret/data/minio/users") -> str:
        """
        Get a specific user's password from Vault
        
        Args:
            username: The username to get the password for
            secret_path: Path to the secrets in Vault
        
        Returns:
            str: The user's password
        
        Raises:
            VaultError: If password retrieval fails
        """
        try:
            password = self.get_secret(secret_path, username)
            if not password:
                raise VaultError(f"Password for user '{username}' is empty or not found")
            
            logger.debug(f"Successfully retrieved password for user: {username}")
            return password
            
        except Exception as e:
            logger.error(f"Failed to get password for user '{username}': {e}")
            raise
    
    def is_authenticated(self) -> bool:
        """
        Check if the client is authenticated
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        try:
            if not self.client or not self.token:
                return False
            
            # Try to read token info to verify it's still valid
            self.client.auth.token.lookup_self()
            return True
            
        except Exception:
            return False
    
    def revoke_token(self) -> None:
        """
        Revoke the current authentication token
        """
        try:
            if self.client and self.token:
                logger.info("Revoking Vault token")
                self.client.auth.token.revoke_self()
                self.token = None
                
        except Exception as e:
            logger.warning(f"Error revoking token: {e}")


def get_vault_client(vault_url: Optional[str] = None,
                     role_id: Optional[str] = None,
                     secret_id: Optional[str] = None) -> VaultClient:
    """
    Factory function to create and authenticate a Vault client
    
    Args:
        vault_url: Vault server URL (optional, uses env var if not provided)
        role_id: AppRole role ID (optional, uses env var if not provided)
        secret_id: AppRole secret ID (optional, uses env var if not provided)
    
    Returns:
        VaultClient: Authenticated Vault client instance
    
    Raises:
        VaultError: If client creation or authentication fails
    """
    try:
        client = VaultClient(vault_url=vault_url, role_id=role_id, secret_id=secret_id)
        client.authenticate()
        return client
        
    except Exception as e:
        logger.error(f"Failed to create authenticated Vault client: {e}")
        raise


if __name__ == '__main__':
    # Example usage and testing
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    try:
        # Create and authenticate client
        vault = get_vault_client()
        
        # Test retrieving a secret
        print("✅ Vault client authenticated successfully")
        print(f"🔗 Connected to: {vault.vault_url}")
        
        # Example of getting all users from vault
        try:
            users_secrets = vault.get_secret("secret/data/minio/users")
            print(f"📋 Found secrets for users: {list(users_secrets.keys())}")
        except Exception as e:
            print(f"⚠️  Could not retrieve user secrets: {e}")
        
        # Clean up
        vault.revoke_token()
        print("🔒 Token revoked")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)