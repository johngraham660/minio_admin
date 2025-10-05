#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from minio import Minio
from minio.error import S3Error, InvalidResponseError, ServerError

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from create_buckets import minio_login, create_bucket


@pytest.mark.unit
class TestMinioLoginEdgeCases:
    """Edge case tests for minio_login function"""
    
    @patch('create_buckets.Minio')
    def test_minio_login_with_empty_strings(self, mock_minio):
        """Test minio_login with empty string parameters"""
        # Arrange
        mock_client = Mock(spec=Minio)
        mock_minio.return_value = mock_client
        
        # Act
        result = minio_login("", 0, "", "")
        
        # Assert
        mock_minio.assert_called_once_with(
            ":0",
            access_key="",
            secret_key="",
            secure=False
        )
        assert result == mock_client
    
    @patch('create_buckets.Minio')
    def test_minio_login_with_very_long_strings(self, mock_minio):
        """Test minio_login with very long string parameters"""
        # Arrange
        long_server = "a" * 1000
        long_access_key = "b" * 1000
        long_secret_key = "c" * 1000
        mock_client = Mock(spec=Minio)
        mock_minio.return_value = mock_client
        
        # Act
        result = minio_login(long_server, 9000, long_access_key, long_secret_key)
        
        # Assert
        mock_minio.assert_called_once_with(
            f"{long_server}:9000",
            access_key=long_access_key,
            secret_key=long_secret_key,
            secure=False
        )
        assert result == mock_client
    
    @patch('create_buckets.Minio', side_effect=Exception("Connection failed"))
    def test_minio_login_connection_failure(self, mock_minio):
        """Test minio_login when Minio constructor raises an exception"""
        # Act & Assert
        with pytest.raises(Exception, match="Connection failed"):
            minio_login("localhost", 9000, "key", "secret")


@pytest.mark.unit
class TestCreateBucketEdgeCases:
    """Edge case tests for create_bucket function"""
    
    def test_create_bucket_with_empty_bucket_name(self, mock_minio_client):
        """Test create_bucket with empty bucket name"""
        # Arrange
        mock_minio_client.bucket_exists.return_value = False
        
        # Act
        create_bucket(mock_minio_client, "")
        
        # Assert
        mock_minio_client.bucket_exists.assert_called_once_with("")
        mock_minio_client.make_bucket.assert_called_once_with("")
    
    def test_create_bucket_with_very_long_bucket_name(self, mock_minio_client):
        """Test create_bucket with very long bucket name"""
        # Arrange
        long_bucket_name = "very-long-bucket-name-" + "x" * 100
        mock_minio_client.bucket_exists.return_value = False
        
        # Act
        create_bucket(mock_minio_client, long_bucket_name)
        
        # Assert
        mock_minio_client.bucket_exists.assert_called_once_with(long_bucket_name)
        mock_minio_client.make_bucket.assert_called_once_with(long_bucket_name)
    
    def test_create_bucket_bucket_exists_check_fails(self, mock_minio_client):
        """Test create_bucket when bucket_exists check raises an exception"""
        # Arrange
        mock_minio_client.bucket_exists.side_effect = S3Error(
            "AccessDenied",
            "Access Denied",
            "bucket-name",
            "request-id",
            "host-id",
            "response"
        )
        
        # Act & Assert
        with pytest.raises(S3Error):
            create_bucket(mock_minio_client, "test-bucket")
        
        mock_minio_client.bucket_exists.assert_called_once_with("test-bucket")
        mock_minio_client.make_bucket.assert_not_called()
    
    def test_create_bucket_multiple_error_types(self, mock_minio_client):
        """Test create_bucket with different types of MinIO errors"""
        # Test with InvalidResponseError (with correct constructor parameters)
        mock_minio_client.bucket_exists.return_value = False
        mock_minio_client.make_bucket.side_effect = InvalidResponseError(
            "Invalid response", "application/json", b'{}'
        )
        
        with pytest.raises(InvalidResponseError):
            create_bucket(mock_minio_client, "test-bucket")
        
        # Reset mocks
        mock_minio_client.reset_mock()
        
        # Test with ServerError (with correct constructor)
        mock_minio_client.bucket_exists.return_value = False
        mock_minio_client.make_bucket.side_effect = ServerError("Server error", 500)
        
        with pytest.raises(ServerError):
            create_bucket(mock_minio_client, "test-bucket")


@pytest.mark.unit
class TestParameterValidation:
    """Tests for parameter validation and type handling"""
    
    @patch('create_buckets.Minio')
    def test_minio_login_with_numeric_strings(self, mock_minio):
        """Test minio_login with numeric values as strings"""
        # Arrange
        mock_client = Mock(spec=Minio)
        mock_minio.return_value = mock_client
        
        # Act - port should be converted properly
        result = minio_login("192.168.1.100", 9000, "123456", "789012")
        
        # Assert
        mock_minio.assert_called_once_with(
            "192.168.1.100:9000",
            access_key="123456",
            secret_key="789012",
            secure=False
        )
        assert result == mock_client
    
    def test_create_bucket_with_none_client(self):
        """Test create_bucket with None client - should fail"""
        # Act & Assert
        with pytest.raises(AttributeError):
            create_bucket(None, "test-bucket")
    
    def test_create_bucket_with_none_bucket_name(self, mock_minio_client):
        """Test create_bucket with None bucket name"""
        # Arrange
        mock_minio_client.bucket_exists.return_value = False
        
        # Act
        create_bucket(mock_minio_client, None)
        
        # Assert
        mock_minio_client.bucket_exists.assert_called_once_with(None)
        mock_minio_client.make_bucket.assert_called_once_with(None)


@pytest.mark.unit
class TestLoggingBehavior:
    """Tests for logging behavior"""
    
    def test_create_bucket_logging_bucket_exists(self, mock_minio_client, caplog):
        """Test logging when bucket already exists"""
        # Arrange
        mock_minio_client.bucket_exists.return_value = True
        bucket_name = "existing-bucket"
        
        # Act
        create_bucket(mock_minio_client, bucket_name)
        
        # Assert
        assert f"Bucket '{bucket_name}' exists." in caplog.text
        assert "Creating bucket:" not in caplog.text
    
    def test_create_bucket_logging_bucket_creation(self, mock_minio_client, caplog):
        """Test logging when creating a new bucket"""
        # Arrange
        mock_minio_client.bucket_exists.return_value = False
        bucket_name = "new-bucket"
        
        # Act
        create_bucket(mock_minio_client, bucket_name)
        
        # Assert
        assert f"Creating bucket: {bucket_name}" in caplog.text
        assert "exists." not in caplog.text


@pytest.mark.unit
class TestFunctionBehaviorConsistency:
    """Tests to ensure consistent behavior across different scenarios"""
    
    def test_create_bucket_idempotent_behavior(self, mock_minio_client):
        """Test that create_bucket is idempotent when bucket exists"""
        # Arrange
        mock_minio_client.bucket_exists.return_value = True
        bucket_name = "test-bucket"
        
        # Act - call multiple times
        create_bucket(mock_minio_client, bucket_name)
        create_bucket(mock_minio_client, bucket_name)
        create_bucket(mock_minio_client, bucket_name)
        
        # Assert
        assert mock_minio_client.bucket_exists.call_count == 3
        mock_minio_client.make_bucket.assert_not_called()
    
    def test_create_bucket_multiple_different_buckets(self, mock_minio_client):
        """Test creating multiple different buckets"""
        # Arrange
        mock_minio_client.bucket_exists.return_value = False
        buckets = ["bucket1", "bucket2", "bucket3"]
        
        # Act
        for bucket in buckets:
            create_bucket(mock_minio_client, bucket)
        
        # Assert
        assert mock_minio_client.bucket_exists.call_count == 3
        assert mock_minio_client.make_bucket.call_count == 3
        
        for bucket in buckets:
            mock_minio_client.bucket_exists.assert_any_call(bucket)
            mock_minio_client.make_bucket.assert_any_call(bucket)


@pytest.mark.unit 
class TestMinioClientReassignment:
    """Test the client reassignment behavior in create_bucket function"""
    
    def test_create_bucket_client_reassignment(self, mock_minio_client):
        """Test that the client reassignment in create_bucket doesn't affect functionality"""
        # Note: The current implementation has "client = client" which is redundant
        # but we test that it doesn't break anything
        
        # Arrange
        original_client = mock_minio_client
        mock_minio_client.bucket_exists.return_value = False
        
        # Act
        create_bucket(mock_minio_client, "test-bucket")
        
        # Assert
        # The client should still be functional after the reassignment
        mock_minio_client.bucket_exists.assert_called_once_with("test-bucket")
        mock_minio_client.make_bucket.assert_called_once_with("test-bucket")
        assert mock_minio_client is original_client