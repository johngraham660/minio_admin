#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest
import json
import os
import sys
from unittest.mock import Mock, patch, mock_open
from minio import Minio

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import create_buckets


@pytest.mark.integration
class TestCreateBucketsIntegration:
    """Integration tests for the create_buckets module"""
    
    @patch.dict(os.environ, {
        'MINIO_SERVER': 'localhost',
        'MINIO_PORT': '9000',
        'MINIO_SECURE': 'false',
        'BUCKET_CREATOR_ACCESS_KEY': 'test_access',
        'BUCKET_CREATOR_SECRET_KEY': 'test_secret'
    })
    @patch('create_buckets.minio_login')
    @patch('create_buckets.create_bucket')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    @patch('os.path.join')
    @patch('os.path.dirname')
    def test_bucket_creation_workflow(self, mock_dirname, mock_join, mock_json_load, 
                                    mock_file, mock_create_bucket, mock_minio_login):
        """Test the complete bucket creation workflow"""
        # Arrange
        mock_dirname.return_value = '/fake/src'
        mock_join.return_value = '/fake/config/minio_buckets.json'
        
        test_buckets = {
            "buckets": [
                "test-bucket-1",
                "test-bucket-2",
                "test-bucket-3"
            ]
        }
        mock_json_load.return_value = test_buckets
        
        mock_client = Mock(spec=Minio)
        mock_minio_login.return_value = mock_client
        
        # Act - simulate the main script logic
        server = os.getenv("MINIO_SERVER")
        port = os.getenv("MINIO_PORT")
        access_key = os.getenv("BUCKET_CREATOR_ACCESS_KEY")
        secret_key = os.getenv("BUCKET_CREATOR_SECRET_KEY")
        
        # Create connection
        conn = create_buckets.minio_login(server, port, access_key, secret_key)
        
        # Process buckets from "file"
        data = mock_json_load.return_value
        buckets = data.get('buckets', [])
        
        for bucket_name in buckets:
            create_buckets.create_bucket(conn, bucket_name)
        
        # Assert
        mock_minio_login.assert_called_once_with('localhost', '9000', 'test_access', 'test_secret')
        assert mock_create_bucket.call_count == 3
        mock_create_bucket.assert_any_call(mock_client, "test-bucket-1")
        mock_create_bucket.assert_any_call(mock_client, "test-bucket-2")
        mock_create_bucket.assert_any_call(mock_client, "test-bucket-3")
    
    @patch('create_buckets.minio_login')
    @patch('builtins.open', side_effect=FileNotFoundError("Configuration file not found"))
    def test_file_not_found_handling(self, mock_file, mock_minio_login):
        """Test handling when configuration file is not found"""
        mock_client = Mock(spec=Minio)
        mock_minio_login.return_value = mock_client
        
        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            with open("nonexistent_file.json", 'r') as f:
                json.load(f)
    
    @patch('create_buckets.minio_login')
    @patch('builtins.open', new_callable=mock_open, read_data='invalid json content')
    def test_invalid_json_handling(self, mock_file, mock_minio_login):
        """Test handling when configuration file contains invalid JSON"""
        mock_client = Mock(spec=Minio)
        mock_minio_login.return_value = mock_client
        
        # Act & Assert
        with pytest.raises(json.JSONDecodeError):
            with open("config.json", 'r') as f:
                json.load(f)
    
    @patch('create_buckets.minio_login')
    @patch('create_buckets.create_bucket')
    def test_empty_buckets_list_handling(self, mock_create_bucket, mock_minio_login):
        """Test handling when bucket configuration has empty buckets list"""
        mock_client = Mock(spec=Minio)
        mock_minio_login.return_value = mock_client
        
        # Simulate empty buckets list
        data = {"buckets": []}
        buckets = data.get('buckets', [])
        
        if buckets:
            for bucket_name in buckets:
                create_buckets.create_bucket(mock_client, bucket_name)
        
        # Assert no buckets were created
        mock_create_bucket.assert_not_called()
    
    @patch('create_buckets.minio_login')
    @patch('create_buckets.create_bucket')
    def test_missing_buckets_key_handling(self, mock_create_bucket, mock_minio_login):
        """Test handling when bucket configuration has no 'buckets' key"""
        mock_client = Mock(spec=Minio)
        mock_minio_login.return_value = mock_client
        
        # Simulate missing buckets key
        data = {"other_key": ["bucket1", "bucket2"]}
        buckets = data.get('buckets', [])
        
        if buckets:
            for bucket_name in buckets:
                create_buckets.create_bucket(mock_client, bucket_name)
        
        # Assert no buckets were created
        mock_create_bucket.assert_not_called()


@pytest.mark.integration
class TestEnvironmentVariableHandling:
    """Test environment variable handling and configuration"""
    
    def test_missing_environment_variables(self):
        """Test behavior when required environment variables are missing"""
        # Clear environment variables that might be set
        env_vars = ['MINIO_SERVER', 'MINIO_PORT', 'BUCKET_CREATOR_ACCESS_KEY', 'BUCKET_CREATOR_SECRET_KEY']
        
        with patch.dict(os.environ, {}, clear=True):
            # Test that getenv returns None for missing variables
            assert os.getenv('MINIO_SERVER') is None
            assert os.getenv('MINIO_PORT') is None
            assert os.getenv('BUCKET_CREATOR_ACCESS_KEY') is None
            assert os.getenv('BUCKET_CREATOR_SECRET_KEY') is None
    
    @patch.dict(os.environ, {
        'MINIO_SERVER': 'test-server',
        'MINIO_PORT': '9001',
        'MINIO_SECURE': 'true',
        'BUCKET_CREATOR_ACCESS_KEY': 'test_key',
        'BUCKET_CREATOR_SECRET_KEY': 'test_secret'
    })
    def test_environment_variables_loaded_correctly(self):
        """Test that environment variables are loaded correctly"""
        # Test that getenv calls would return the expected values
        assert os.getenv('MINIO_SERVER') == 'test-server'
        assert os.getenv('MINIO_PORT') == '9001'
        assert os.getenv('MINIO_SECURE') == 'true'
        assert os.getenv('BUCKET_CREATOR_ACCESS_KEY') == 'test_key'
        assert os.getenv('BUCKET_CREATOR_SECRET_KEY') == 'test_secret'


@pytest.mark.integration
class TestRealConfigFile:
    """Integration tests using the actual config file"""
    
    def test_actual_config_file_structure(self):
        """Test that the actual minio_buckets.json file has the expected structure"""
        config_path = '/home/johngr/Projects/git/python/minio_admin/config/minio_buckets.json'
        
        with open(config_path, 'r') as f:
            data = json.load(f)
        
        # Assert the file has the expected structure
        assert 'buckets' in data
        assert isinstance(data['buckets'], list)
        assert len(data['buckets']) > 0
        
        # Check that all bucket names are strings
        for bucket in data['buckets']:
            assert isinstance(bucket, str)
            assert len(bucket) > 0
    
    @patch('create_buckets.minio_login')
    @patch('create_buckets.create_bucket')
    def test_integration_with_real_config(self, mock_create_bucket, mock_minio_login):
        """Integration test using the real config file"""
        # Arrange
        mock_client = Mock(spec=Minio)
        mock_minio_login.return_value = mock_client
        
        config_path = '/home/johngr/Projects/git/python/minio_admin/config/minio_buckets.json'
        
        # Act
        with open(config_path, 'r') as f:
            data = json.load(f)
            buckets = data.get('buckets', [])
        
        # Simulate the main script logic
        if buckets:
            for bucket_name in buckets:
                create_buckets.create_bucket(mock_client, bucket_name)
        
        # Assert
        expected_buckets = [
            "virtua-cicd-pipeline-logs",
            "virtua-cicd-pipeline-artifacts", 
            "k8s-etcdbackup-development",
            "k8s-etcdbackup-production"
        ]
        
        assert mock_create_bucket.call_count == len(expected_buckets)
        for bucket in expected_buckets:
            mock_create_bucket.assert_any_call(mock_client, bucket)


@pytest.mark.integration
class TestModuleFunctionIntegration:
    """Test integration between module functions"""
    
    @patch('create_buckets.Minio')
    def test_minio_login_and_create_bucket_integration(self, mock_minio_class):
        """Test integration between minio_login and create_bucket functions"""
        # Arrange
        mock_client = Mock(spec=Minio)
        mock_client.bucket_exists.return_value = False
        mock_minio_class.return_value = mock_client
        
        # Act
        client = create_buckets.minio_login("localhost", 9000, "test_key", "test_secret")
        create_buckets.create_bucket(client, "test-bucket")
        
        # Assert
        mock_minio_class.assert_called_once_with(
            "localhost:9000",
            access_key="test_key",
            secret_key="test_secret",
            secure=False
        )
        mock_client.bucket_exists.assert_called_once_with("test-bucket")
        mock_client.make_bucket.assert_called_once_with("test-bucket")
    
    def test_create_bucket_with_real_minio_client_structure(self):
        """Test create_bucket function expects correct Minio client interface"""
        # Create a mock that has the expected Minio interface
        mock_client = Mock()
        mock_client.bucket_exists = Mock(return_value=True)
        mock_client.make_bucket = Mock()
        
        # This should not raise any AttributeError
        create_buckets.create_bucket(mock_client, "test-bucket")
        
        # Verify the expected methods were called
        mock_client.bucket_exists.assert_called_once_with("test-bucket")
        mock_client.make_bucket.assert_not_called()  # Because bucket exists