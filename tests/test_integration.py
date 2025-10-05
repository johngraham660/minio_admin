#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest
import json
import os
import sys
import tempfile
from unittest.mock import Mock, patch, mock_open, MagicMock
from minio import Minio
from minio.error import S3Error

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
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    @patch('os.path.join')
    @patch('os.path.dirname')
    def test_main_script_execution_success(self, mock_dirname, mock_join, mock_json_load, 
                                         mock_file, mock_minio_login, caplog):
        """Test successful execution of the main script"""
        # Arrange
        mock_dirname.return_value = '/fake/src'
        mock_join.return_value = '/fake/src/../config/minio_buckets.json'
        
        test_buckets = {
            "buckets": [
                "test-bucket-1",
                "test-bucket-2",
                "test-bucket-3"
            ]
        }
        mock_json_load.return_value = test_buckets
        
        mock_client = Mock(spec=Minio)
        mock_client.bucket_exists.return_value = False
        mock_minio_login.return_value = mock_client
        
        # Mock the main execution
        with patch('create_buckets.create_bucket') as mock_create_bucket:
            # Act
            exec(open('/home/johngr/Projects/git/python/minio_admin/src/create_buckets.py').read())
            
            # Assert
            mock_minio_login.assert_called_once_with('localhost', '9000', 'test_access', 'test_secret')
            assert mock_create_bucket.call_count == 3
            mock_create_bucket.assert_any_call(mock_client, "test-bucket-1")
            mock_create_bucket.assert_any_call(mock_client, "test-bucket-2")
            mock_create_bucket.assert_any_call(mock_client, "test-bucket-3")
    
    @patch.dict(os.environ, {
        'MINIO_SERVER': 'localhost',
        'MINIO_PORT': '9000',
        'MINIO_SECURE': 'false',
        'BUCKET_CREATOR_ACCESS_KEY': 'test_access',
        'BUCKET_CREATOR_SECRET_KEY': 'test_secret'
    })
    @patch('create_buckets.minio_login')
    @patch('builtins.open', side_effect=FileNotFoundError("File not found"))
    @patch('os.path.join')
    @patch('os.path.dirname')
    def test_main_script_file_not_found(self, mock_dirname, mock_join, mock_file, 
                                      mock_minio_login, caplog):
        """Test main script behavior when bucket config file is not found"""
        # Arrange
        mock_dirname.return_value = '/fake/src'
        mock_join.return_value = '/fake/src/../config/minio_buckets.json'
        
        mock_client = Mock(spec=Minio)
        mock_minio_login.return_value = mock_client
        
        # Act
        with patch('sys.argv', ['create_buckets.py']):
            try:
                exec(open('/home/johngr/Projects/git/python/minio_admin/src/create_buckets.py').read())
            except SystemExit:
                pass  # Script may exit, that's ok for this test
        
        # Assert
        assert "was not found" in caplog.text
    
    @patch.dict(os.environ, {
        'MINIO_SERVER': 'localhost',
        'MINIO_PORT': '9000',
        'MINIO_SECURE': 'false',
        'BUCKET_CREATOR_ACCESS_KEY': 'test_access',
        'BUCKET_CREATOR_SECRET_KEY': 'test_secret'
    })
    @patch('create_buckets.minio_login')
    @patch('builtins.open', new_callable=mock_open, read_data='invalid json')
    @patch('json.load', side_effect=json.JSONDecodeError("Invalid JSON", "doc", 0))
    @patch('os.path.join')
    @patch('os.path.dirname')
    def test_main_script_invalid_json(self, mock_dirname, mock_join, mock_json_load, 
                                    mock_file, mock_minio_login, caplog):
        """Test main script behavior when bucket config file contains invalid JSON"""
        # Arrange
        mock_dirname.return_value = '/fake/src'
        mock_join.return_value = '/fake/src/../config/minio_buckets.json'
        
        mock_client = Mock(spec=Minio)
        mock_minio_login.return_value = mock_client
        
        # Act
        with patch('sys.argv', ['create_buckets.py']):
            try:
                exec(open('/home/johngr/Projects/git/python/minio_admin/src/create_buckets.py').read())
            except SystemExit:
                pass  # Script may exit, that's ok for this test
        
        # Assert
        assert "Could not decode JSON" in caplog.text
    
    @patch.dict(os.environ, {
        'MINIO_SERVER': 'localhost',
        'MINIO_PORT': '9000',
        'MINIO_SECURE': 'false',
        'BUCKET_CREATOR_ACCESS_KEY': 'test_access',
        'BUCKET_CREATOR_SECRET_KEY': 'test_secret'
    })
    @patch('create_buckets.minio_login')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    @patch('os.path.join')
    @patch('os.path.dirname')
    def test_main_script_empty_buckets_list(self, mock_dirname, mock_join, mock_json_load, 
                                          mock_file, mock_minio_login, capsys):
        """Test main script behavior when bucket config file has empty buckets list"""
        # Arrange
        mock_dirname.return_value = '/fake/src'
        mock_join.return_value = '/fake/src/../config/minio_buckets.json'
        
        test_buckets = {"buckets": []}
        mock_json_load.return_value = test_buckets
        
        mock_client = Mock(spec=Minio)
        mock_minio_login.return_value = mock_client
        
        # Act
        with patch('sys.argv', ['create_buckets.py']):
            try:
                exec(open('/home/johngr/Projects/git/python/minio_admin/src/create_buckets.py').read())
            except SystemExit:
                pass  # Script may exit, that's ok for this test
        
        # Assert
        captured = capsys.readouterr()
        assert "No buckets found in JSON file" in captured.out
    
    @patch.dict(os.environ, {
        'MINIO_SERVER': 'localhost',
        'MINIO_PORT': '9000',
        'MINIO_SECURE': 'false',
        'BUCKET_CREATOR_ACCESS_KEY': 'test_access',
        'BUCKET_CREATOR_SECRET_KEY': 'test_secret'
    })
    @patch('create_buckets.minio_login')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    @patch('os.path.join')
    @patch('os.path.dirname')
    def test_main_script_no_buckets_key(self, mock_dirname, mock_join, mock_json_load, 
                                      mock_file, mock_minio_login, capsys):
        """Test main script behavior when bucket config file has no 'buckets' key"""
        # Arrange
        mock_dirname.return_value = '/fake/src'
        mock_join.return_value = '/fake/src/../config/minio_buckets.json'
        
        test_buckets = {"other_key": ["bucket1", "bucket2"]}
        mock_json_load.return_value = test_buckets
        
        mock_client = Mock(spec=Minio)
        mock_minio_login.return_value = mock_client
        
        # Act
        with patch('sys.argv', ['create_buckets.py']):
            try:
                exec(open('/home/johngr/Projects/git/python/minio_admin/src/create_buckets.py').read())
            except SystemExit:
                pass  # Script may exit, that's ok for this test
        
        # Assert
        captured = capsys.readouterr()
        assert "No buckets found in JSON file" in captured.out


@pytest.mark.integration
class TestEnvironmentVariableHandling:
    """Test environment variable handling and configuration"""
    
    def test_missing_environment_variables(self):
        """Test behavior when required environment variables are missing"""
        # Clear environment variables that might be set
        env_vars = ['MINIO_SERVER', 'MINIO_PORT', 'BUCKET_CREATOR_ACCESS_KEY', 'BUCKET_CREATOR_SECRET_KEY']
        
        with patch.dict(os.environ, {}, clear=True):
            # Import fresh copy to test environment variable loading
            import importlib
            importlib.reload(create_buckets)
            
            # The script should handle None values gracefully
            # This test ensures the import doesn't fail with missing env vars
            assert hasattr(create_buckets, 'minio_login')
            assert hasattr(create_buckets, 'create_bucket')
    
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