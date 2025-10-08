#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from manage_minio import connect, create_bucket
import pytest
import os
import sys
from unittest.mock import Mock, patch
from minio import Minio
from minio.error import S3Error

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.mark.unit
class TestConnect:
    """Unit tests for the connect function"""

    @patch('manage_minio.Minio')
    @patch.dict(os.environ, {
        'MINIO_SERVER': 'localhost',
        'MINIO_PORT': '9000',
        'MINIO_SECURE': 'false',
        'BUCKET_CREATOR_ACCESS_KEY': 'test_access_key',
        'BUCKET_CREATOR_SECRET_KEY': 'test_secret_key'
    })
    def test_connect_creates_client_with_correct_parameters(self, mock_minio):
        """Test that connect creates a Minio client with the correct parameters"""
        # Arrange
        mock_client = Mock(spec=Minio)
        mock_minio.return_value = mock_client

        # Act
        result = connect()

        # Assert
        mock_minio.assert_called_once_with(
            "localhost:9000",
            access_key="test_access_key",
            secret_key="test_secret_key",
            secure=False
        )
        assert result == mock_client

    @patch('manage_minio.Minio')
    @patch.dict(os.environ, {
        'MINIO_SERVER': 'minio.example.com',
        'MINIO_PORT': '9001',
        'MINIO_SECURE': 'false',
        'BUCKET_CREATOR_ACCESS_KEY': 'admin',
        'BUCKET_CREATOR_SECRET_KEY': 'password123'
    })
    def test_connect_with_different_port(self, mock_minio):
        """Test connect with a different port number"""
        # Arrange
        mock_client = Mock(spec=Minio)
        mock_minio.return_value = mock_client

        # Act
        result = connect()

        # Assert
        mock_minio.assert_called_once_with(
            "minio.example.com:9001",
            access_key="admin",
            secret_key="password123",
            secure=False
        )
        assert result == mock_client

    @patch('manage_minio.Minio')
    @patch.dict(os.environ, {
        'MINIO_SERVER': 'localhost',
        'MINIO_PORT': '9000',
        'MINIO_SECURE': 'false',
        'BUCKET_CREATOR_ACCESS_KEY': 'key',
        'BUCKET_CREATOR_SECRET_KEY': 'secret'
    })
    def test_connect_returns_minio_instance(self, mock_minio):
        """Test that connect returns a Minio instance"""
        # Arrange
        mock_client = Mock(spec=Minio)
        mock_minio.return_value = mock_client

        # Act
        result = connect()

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

        # Create a mock response object for S3Error
        mock_response = Mock()
        mock_response.status = 409
        mock_response.reason = "Conflict"
        mock_response.data = b'{"error": "BucketAlreadyExists"}'

        # Create S3Error with proper constructor parameters
        mock_client.make_bucket.side_effect = S3Error(
            response=mock_response,
            code="BucketAlreadyExists",
            message="The requested bucket name is not available",
            resource="bucket-name",
            request_id="request-id",
            host_id="host-id"
        )
        bucket_name = "problematic-bucket"

        # Act & Assert
        with pytest.raises(S3Error):
            create_bucket(mock_client, bucket_name)

        mock_client.bucket_exists.assert_called_once_with(bucket_name)
        mock_client.make_bucket.assert_called_once_with(bucket_name)
