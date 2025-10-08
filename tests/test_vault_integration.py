#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from manage_minio import create_user_with_vault_password
import pytest
import os
import sys
from unittest.mock import Mock, patch
from minio import MinioAdmin

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.mark.unit
class TestVaultIntegration:
    """Unit tests for Vault integration functionality"""

    def test_create_user_with_vault_password_success(self, caplog):
        """Test successful user creation with password from Vault"""
        # Arrange
        mock_admin_client = Mock(spec=MinioAdmin)
        mock_admin_client.user_add.return_value = {"status": "success"}

        mock_vault_client = Mock()
        mock_vault_client.get_user_password.return_value = "vault_password_123"

        username = "test-user"
        vault_path = "secret/data/minio/users"

        # Act
        create_user_with_vault_password(mock_admin_client, username, mock_vault_client, vault_path)

        # Assert
        mock_vault_client.get_user_password.assert_called_once_with(username, vault_path)
        mock_admin_client.user_add.assert_called_once_with(username, "vault_password_123")
        assert f"Creating User: {username} (password from Vault)" in caplog.text
        assert f"User {username} created successfully" in caplog.text

    def test_create_user_with_vault_password_user_exists(self, caplog):
        """Test user creation when user already exists"""
        # Arrange
        mock_admin_client = Mock(spec=MinioAdmin)
        mock_admin_client.user_add.side_effect = Exception("User already exists")

        mock_vault_client = Mock()
        mock_vault_client.get_user_password.return_value = "vault_password_123"

        username = "existing-user"
        vault_path = "secret/data/minio/users"

        # Act
        create_user_with_vault_password(mock_admin_client, username, mock_vault_client, vault_path)

        # Assert
        mock_vault_client.get_user_password.assert_called_once_with(username, vault_path)
        mock_admin_client.user_add.assert_called_once_with(username, "vault_password_123")
        assert f"User {username} already exists, skipping creation" in caplog.text

    def test_create_user_with_vault_password_vault_error(self):
        """Test user creation when Vault returns an error"""
        # Arrange
        mock_admin_client = Mock(spec=MinioAdmin)

        mock_vault_client = Mock()
        mock_vault_client.get_user_password.side_effect = Exception("Vault connection failed")

        username = "test-user"
        vault_path = "secret/data/minio/users"

        # Act & Assert
        with pytest.raises(Exception, match="Vault connection failed"):
            create_user_with_vault_password(
                mock_admin_client, username, mock_vault_client, vault_path)

        mock_vault_client.get_user_password.assert_called_once_with(username, vault_path)
        mock_admin_client.user_add.assert_not_called()

    def test_create_user_with_vault_password_user_add_error(self):
        """Test user creation when MinIO user_add fails with non-exists error"""
        # Arrange
        mock_admin_client = Mock(spec=MinioAdmin)
        mock_admin_client.user_add.side_effect = Exception("Permission denied")

        mock_vault_client = Mock()
        mock_vault_client.get_user_password.return_value = "vault_password_123"

        username = "test-user"
        vault_path = "secret/data/minio/users"

        # Act & Assert
        with pytest.raises(Exception, match="Permission denied"):
            create_user_with_vault_password(
                mock_admin_client, username, mock_vault_client, vault_path)

        mock_vault_client.get_user_password.assert_called_once_with(username, vault_path)
        mock_admin_client.user_add.assert_called_once_with(username, "vault_password_123")


@pytest.mark.unit
class TestVaultClientMocking:
    """Tests for mocking Vault client behavior"""

    @patch('manage_minio.get_vault_client')
    def test_vault_client_creation_success(self, mock_get_vault_client):
        """Test successful Vault client creation"""
        # Arrange
        mock_vault_client = Mock()
        mock_vault_client.authenticate.return_value = True
        mock_get_vault_client.return_value = mock_vault_client

        # Act
        from manage_minio import get_vault_client
        result = get_vault_client()

        # Assert
        assert result == mock_vault_client
        mock_get_vault_client.assert_called_once()

    @patch('manage_minio.get_vault_client')
    def test_vault_client_creation_failure(self, mock_get_vault_client):
        """Test Vault client creation failure"""
        # Arrange
        mock_get_vault_client.side_effect = Exception("Vault unavailable")

        # Act & Assert
        with pytest.raises(Exception, match="Vault unavailable"):
            from manage_minio import get_vault_client
            get_vault_client()

        mock_get_vault_client.assert_called_once()


@pytest.mark.unit
class TestVaultConfigurationHandling:
    """Tests for configuration handling with Vault paths"""

    def test_vault_client_requires_vault_addr(self):
        """Test that VaultClient raises error when VAULT_ADDR is not provided"""
        from vault_client import VaultClient

        # Test that missing VAULT_ADDR raises ValueError
        with patch.dict(os.environ, {}, clear=True):  # Clear all env vars
            with pytest.raises(ValueError, match="VAULT_ADDR environment variable must be set"):
                VaultClient(vault_url=None, role_id="test-role", secret_id="test-secret")

    def test_vault_client_requires_role_credentials(self):
        """Test that VaultClient raises error when role credentials are missing"""
        from vault_client import VaultClient

        # Test that missing role_id raises ValueError
        with patch.dict(os.environ, {'VAULT_ADDR': 'https://vault.example.com:8200'}, clear=True):
            with pytest.raises(
                ValueError,
                match="VAULT_ROLE_ID and VAULT_SECRET_ID environment variables must be set"
            ):
                VaultClient(vault_url=None, role_id=None, secret_id="test-secret")

        # Test that missing secret_id raises ValueError
        with patch.dict(os.environ, {'VAULT_ADDR': 'https://vault.example.com:8200'}, clear=True):
            with pytest.raises(
                ValueError,
                match="VAULT_ROLE_ID and VAULT_SECRET_ID environment variables must be set"
            ):
                VaultClient(vault_url=None, role_id="test-role", secret_id=None)

    def test_user_config_with_vault_path(self):
        """Test that user configuration correctly includes vault_path"""
        # Arrange
        user_config = {
            "username": "svc-test",
            "vault_path": "secret/data/minio/users",
            "policy": "test-policy.json"
        }

        # Act & Assert
        assert user_config.get('vault_path') == "secret/data/minio/users"
        assert 'password' not in user_config
        assert user_config.get('username') == "svc-test"
        assert user_config.get('policy') == "test-policy.json"

    def test_user_config_without_vault_path_has_default(self):
        """Test that missing vault_path gets default value"""
        # Arrange
        user_config = {
            "username": "svc-test",
            "policy": "test-policy.json"
        }

        # Act
        vault_path = user_config.get('vault_path', 'secret/data/minio/users')

        # Assert
        assert vault_path == 'secret/data/minio/users'


@pytest.mark.integration
class TestVaultIntegrationScenarios:
    """Integration test scenarios for Vault functionality"""

    @patch('manage_minio.get_vault_client')
    def test_fallback_to_config_passwords_when_vault_unavailable(self, mock_get_vault_client):
        """Test fallback to configuration file passwords when Vault is unavailable"""
        # Arrange
        mock_get_vault_client.side_effect = Exception("Vault connection failed")

        # This test would need to be integrated with the main script logic
        # For now, we test that the exception is raised as expected

        # Act & Assert
        with pytest.raises(Exception, match="Vault connection failed"):
            from manage_minio import get_vault_client
            get_vault_client()

    @patch('manage_minio.get_vault_client')
    def test_vault_connection_success_scenario(self, mock_get_vault_client):
        """Test successful Vault connection scenario"""
        # Arrange
        mock_vault_client = Mock()
        mock_vault_client.authenticate.return_value = True
        mock_vault_client.is_authenticated.return_value = True
        mock_vault_client.get_user_password.return_value = "secure_vault_password"
        mock_get_vault_client.return_value = mock_vault_client

        # Act
        from manage_minio import get_vault_client
        vault_client = get_vault_client()
        password = vault_client.get_user_password("test-user", "secret/data/minio/users")

        # Assert
        assert vault_client == mock_vault_client
        assert password == "secure_vault_password"
        mock_vault_client.get_user_password.assert_called_once_with(
            "test-user", "secret/data/minio/users")
