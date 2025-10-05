#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest
import json
import os
import sys
from unittest.mock import Mock, patch, mock_open, MagicMock
from minio import Minio
from minio.error import S3Error

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from create_buckets import minio_login, create_bucket


@pytest.mark.unit
class TestMinioLogin:
    """Unit tests for the minio_login function"""
    
    @patch('create_buckets.Minio')
    def test_minio_login_creates_client_with_correct_parameters(self, mock_minio):
        """Test that minio_login creates a Minio client with the correct parameters"""
        # Arrange
        server = "localhost"
        port = 9000
        access_key = "test_access_key"
        secret_key = "test_secret_key"
        
        mock_client = Mock(spec=Minio)
        mock_minio.return_value = mock_client
        
        # Act
        result = minio_login(server, port, access_key, secret_key)
        
        # Assert
        mock_minio.assert_called_once_with(
            "localhost:9000",
            access_key="test_access_key",
            secret_key="test_secret_key",
            secure=False
        )
        assert result == mock_client
    
    @patch('create_buckets.Minio')
    def test_minio_login_with_different_port(self, mock_minio):
        """Test minio_login with a different port number"""
        # Arrange
        server = "minio.example.com"
        port = 9001
        access_key = "admin"
        secret_key = "password123"
        
        mock_client = Mock(spec=Minio)
        mock_minio.return_value = mock_client
        
        # Act
        result = minio_login(server, port, access_key, secret_key)
        
        # Assert
        mock_minio.assert_called_once_with(
            "minio.example.com:9001",
            access_key="admin",
            secret_key="password123",
            secure=False
        )
        assert result == mock_client
    
    @patch('create_buckets.Minio')
    def test_minio_login_returns_minio_instance(self, mock_minio):
        """Test that minio_login returns a Minio instance"""
        # Arrange
        mock_client = Mock(spec=Minio)
        mock_minio.return_value = mock_client
        
        # Act
        result = minio_login("localhost", 9000, "key", "secret")
        
        # Assert
        assert isinstance(result, type(mock_client))


@pytest.mark.unit
class TestCreateBucket:
    """Unit tests for the create_bucket function"""
    
    def test_create_bucket_when_bucket_exists(self, caplog):
        """Test create_bucket behavior when bucket already exists"""
        # Arrange
        mock_client = Mock(spec=Minio)
        mock_client.bucket_exists.return_value = True
        bucket_name = "existing-bucket"
        
        # Act
        create_bucket(mock_client, bucket_name)
        
        # Assert
        mock_client.bucket_exists.assert_called_once_with(bucket_name)
        mock_client.make_bucket.assert_not_called()
        assert "Bucket 'existing-bucket' exists." in caplog.text
    
    def test_create_bucket_when_bucket_does_not_exist(self, caplog):
        """Test create_bucket behavior when bucket doesn't exist"""
        # Arrange
        mock_client = Mock(spec=Minio)
        mock_client.bucket_exists.return_value = False
        bucket_name = "new-bucket"
        
        # Act
        create_bucket(mock_client, bucket_name)
        
        # Assert
        mock_client.bucket_exists.assert_called_once_with(bucket_name)
        mock_client.make_bucket.assert_called_once_with(bucket_name)
        assert "Creating bucket: new-bucket" in caplog.text
    
    def test_create_bucket_with_special_characters(self, caplog):
        """Test create_bucket with bucket name containing special characters"""
        # Arrange
        mock_client = Mock(spec=Minio)
        mock_client.bucket_exists.return_value = False
        bucket_name = "test-bucket-with-dashes_and_underscores"
        
        # Act
        create_bucket(mock_client, bucket_name)
        
        # Assert
        mock_client.bucket_exists.assert_called_once_with(bucket_name)
        mock_client.make_bucket.assert_called_once_with(bucket_name)
    
    def test_create_bucket_handles_s3_error(self):
        """Test create_bucket handles S3Error exceptions properly"""
        # Arrange
        mock_client = Mock(spec=Minio)
        mock_client.bucket_exists.return_value = False
        mock_client.make_bucket.side_effect = S3Error(
            "BucketAlreadyExists",
            "The requested bucket name is not available",
            "bucket-name",
            "request-id",
            "host-id",
            "response"
        )
        bucket_name = "problematic-bucket"
        
        # Act & Assert
        with pytest.raises(S3Error):
            create_bucket(mock_client, bucket_name)
        
        mock_client.bucket_exists.assert_called_once_with(bucket_name)
        mock_client.make_bucket.assert_called_once_with(bucket_name)