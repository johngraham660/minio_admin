#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest
import os
import sys
import json
import tempfile
from unittest.mock import Mock, patch
from minio import Minio

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def mock_minio_client():
    """Fixture that provides a mock Minio client"""
    mock_client = Mock(spec=Minio)
    mock_client.bucket_exists.return_value = False
    mock_client.make_bucket.return_value = None
    return mock_client


@pytest.fixture
def sample_bucket_config():
    """Fixture that provides sample bucket configuration data"""
    return {
        "buckets": [
            "test-bucket-1",
            "test-bucket-2", 
            "test-bucket-3",
            "development-bucket",
            "production-bucket"
        ]
    }


@pytest.fixture
def empty_bucket_config():
    """Fixture that provides empty bucket configuration"""
    return {"buckets": []}


@pytest.fixture
def invalid_bucket_config():
    """Fixture that provides invalid bucket configuration (missing buckets key)"""
    return {"other_key": ["bucket1", "bucket2"]}


@pytest.fixture
def test_environment_variables():
    """Fixture that provides test environment variables"""
    return {
        'MINIO_SERVER': 'localhost',
        'MINIO_PORT': '9000',
        'MINIO_SECURE': 'false',
        'BUCKET_CREATOR_ACCESS_KEY': 'test_access_key',
        'BUCKET_CREATOR_SECRET_KEY': 'test_secret_key'
    }


@pytest.fixture
def temp_config_file(sample_bucket_config):
    """Fixture that creates a temporary config file with sample data"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_bucket_config, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def temp_empty_config_file(empty_bucket_config):
    """Fixture that creates a temporary config file with empty bucket list"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(empty_bucket_config, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def temp_invalid_config_file():
    """Fixture that creates a temporary config file with invalid JSON"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{ invalid json content')
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def minio_connection_params():
    """Fixture that provides standard Minio connection parameters"""
    return {
        'server': 'localhost',
        'port': 9000,
        'access_key': 'test_access_key',
        'secret_key': 'test_secret_key'
    }


@pytest.fixture
def real_config_path():
    """Fixture that provides the path to the real config file"""
    return '/home/johngr/Projects/git/python/minio_admin/config/minio_buckets.json'


@pytest.fixture
def patch_environment(test_environment_variables):
    """Fixture that patches environment variables for testing"""
    with patch.dict(os.environ, test_environment_variables, clear=True):
        yield test_environment_variables


@pytest.fixture(autouse=True)
def reset_logging():
    """Fixture to reset logging configuration between tests"""
    import logging
    # Clear any existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Reset to basic config
    logging.basicConfig(level=logging.INFO, force=True)
    
    yield
    
    # Clean up after test
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)