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
def mock_vault_client():
    """Fixture that provides a mock Vault client"""
    mock_vault = Mock()
    mock_vault.authenticate.return_value = True
    mock_vault.is_authenticated.return_value = True
    mock_vault.get_user_password.return_value = "secure_password_from_vault"

    # Use environment variables for usernames with fallbacks
    concourse_user = os.getenv('MINIO_USER_CONCOURSE', 'user1')
    jenkins_user = os.getenv('MINIO_USER_JENKINS', 'user2')
    k8s_user = os.getenv('MINIO_USER_K8S', 'user3')

    mock_vault.get_secret.return_value = {
        concourse_user: "vault_password_1",
        jenkins_user: "vault_password_2",
        k8s_user: "vault_password_3"
    }
    mock_vault.revoke_token.return_value = None
    return mock_vault


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
def sample_user_config_with_vault():
    """Fixture that provides sample user configuration with Vault paths"""
    # Use environment variables for usernames with fallbacks
    concourse_user = os.getenv('MINIO_USER_CONCOURSE', 'user1')
    jenkins_user = os.getenv('MINIO_USER_JENKINS', 'user2')
    k8s_user = os.getenv('MINIO_USER_K8S', 'user3')

    return {
        "users": [
            {
                "username": concourse_user,
                "vault_path": "secret/data/minio/users",
                "policy": "concourse-pipeline-artifacts-policy.json"
            },
            {
                "username": jenkins_user,
                "vault_path": "secret/data/minio/users",
                "policy": "jenkins-pipeline-artifacts-policy.json"
            },
            {
                "username": k8s_user,
                "vault_path": "secret/data/minio/users",
                "policy": "k8s-etcdbackup-policy.json"
            }
        ]
    }


@pytest.fixture
def sample_user_config_legacy():
    """Fixture that provides sample user configuration with legacy passwords"""
    return {
        "users": [
            {
                "username": "legacy-user1",
                "password": "legacy_password_1",
                "policy": "concourse-pipeline-artifacts-policy.json"
            },
            {
                "username": "legacy-user2",
                "password": "legacy_password_2",
                "policy": "jenkins-pipeline-artifacts-policy.json"
            }
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
        'BUCKET_CREATOR_SECRET_KEY': 'test_secret_key',
        'VAULT_ADDR': 'http://test-vault:8200',
        'VAULT_ROLE_ID': 'test-role-id',
        'VAULT_SECRET_ID': 'test-secret-id',
        'MINIO_USER_CONCOURSE': 'test-user1',
        'MINIO_USER_JENKINS': 'test-user2',
        'MINIO_USER_K8S': 'test-user3'
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
def temp_vault_config_file(sample_user_config_with_vault, sample_bucket_config):
    """Fixture that creates a temporary config file with Vault configuration"""
    config_data = {**sample_bucket_config, **sample_user_config_with_vault}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
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
    # Use relative path from the test directory to make it portable across environments
    test_dir = os.path.dirname(__file__)
    config_path = os.path.join(test_dir, '..', 'config', 'minio_server_config.json')
    # Return the normalized absolute path to ensure it works regardless of cwd
    return os.path.normpath(config_path)


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
