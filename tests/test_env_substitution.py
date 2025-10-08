#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest
import os
import sys
from unittest.mock import patch

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from manage_minio import substitute_env_vars_in_config  # noqa: E402


@pytest.mark.unit
class TestEnvironmentVariableSubstitution:
    """Tests for environment variable substitution in configuration"""

    def test_substitute_env_vars_with_all_variables_set(self):
        """Test substitution when all environment variables are set"""
        # Arrange
        test_config = {
            "users": [
                {"username": "${MINIO_USER_CONCOURSE}", "policy": "test1.json"},
                {"username": "${MINIO_USER_JENKINS}", "policy": "test2.json"},
                {"username": "${MINIO_USER_K8S}", "policy": "test3.json"}
            ]
        }

        env_vars = {
            'MINIO_USER_CONCOURSE': 'my-concourse-svc',
            'MINIO_USER_JENKINS': 'my-jenkins-svc',
            'MINIO_USER_K8S': 'my-k8s-svc'
        }

        # Act
        with patch.dict(os.environ, env_vars, clear=False):
            result = substitute_env_vars_in_config(test_config)

        # Assert
        assert len(result['users']) == 3
        assert result['users'][0]['username'] == 'my-concourse-svc'
        assert result['users'][1]['username'] == 'my-jenkins-svc'
        assert result['users'][2]['username'] == 'my-k8s-svc'
        # Ensure other fields are preserved
        assert result['users'][0]['policy'] == 'test1.json'

    def test_substitute_env_vars_with_fallback_defaults(self):
        """Test substitution falls back to defaults when env vars not set"""
        # Arrange
        test_config = {
            "users": [
                {"username": "${MINIO_USER_CONCOURSE}", "policy": "test1.json"},
                {"username": "${MINIO_USER_JENKINS}", "policy": "test2.json"},
                {"username": "${MINIO_USER_K8S}", "policy": "test3.json"}
            ]
        }

        # Act - clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            result = substitute_env_vars_in_config(test_config)

        # Assert - should use default values
        assert result['users'][0]['username'] == 'user1'
        assert result['users'][1]['username'] == 'user2'
        assert result['users'][2]['username'] == 'user3'

    def test_substitute_env_vars_no_modification_needed(self):
        """Test that config without placeholders is unchanged"""
        # Arrange
        test_config = {
            "users": [
                {"username": "regular-user", "policy": "test.json"},
                {"username": "another-user", "policy": "test2.json"}
            ],
            "buckets": ["bucket1", "bucket2"]
        }

        # Act
        result = substitute_env_vars_in_config(test_config)

        # Assert - should be unchanged
        assert result == test_config
        assert result['users'][0]['username'] == 'regular-user'
        assert result['users'][1]['username'] == 'another-user'
        assert result['buckets'] == ["bucket1", "bucket2"]

    def test_substitute_env_vars_mixed_placeholders(self):
        """Test substitution with mix of placeholders and regular usernames"""
        # Arrange
        test_config = {
            "users": [
                {"username": "${MINIO_USER_CONCOURSE}", "policy": "test1.json"},
                {"username": "regular-user", "policy": "test2.json"},
                {"username": "${MINIO_USER_JENKINS}", "policy": "test3.json"}
            ]
        }

        env_vars = {
            'MINIO_USER_CONCOURSE': 'env-concourse',
            'MINIO_USER_JENKINS': 'env-jenkins'
        }

        # Act
        with patch.dict(os.environ, env_vars, clear=False):
            result = substitute_env_vars_in_config(test_config)

        # Assert
        assert result['users'][0]['username'] == 'env-concourse'  # substituted
        assert result['users'][1]['username'] == 'regular-user'  # unchanged
        assert result['users'][2]['username'] == 'env-jenkins'   # substituted

    def test_substitute_env_vars_does_not_modify_original(self):
        """Test that the original config is not modified"""
        # Arrange
        original_config = {
            "users": [
                {"username": "${MINIO_USER_CONCOURSE}", "policy": "test.json"}
            ]
        }
        original_username = original_config['users'][0]['username']

        env_vars = {'MINIO_USER_CONCOURSE': 'modified-username'}

        # Act
        with patch.dict(os.environ, env_vars, clear=False):
            result = substitute_env_vars_in_config(original_config)

        # Assert
        assert original_config['users'][0]['username'] == original_username  # unchanged
        assert result['users'][0]['username'] == 'modified-username'        # modified in copy

    def test_substitute_env_vars_empty_config(self):
        """Test substitution with empty or minimal config"""
        # Arrange & Act
        result1 = substitute_env_vars_in_config({})
        result2 = substitute_env_vars_in_config({"buckets": ["test"]})
        result3 = substitute_env_vars_in_config({"users": []})

        # Assert
        assert result1 == {}
        assert result2 == {"buckets": ["test"]}
        assert result3 == {"users": []}

    def test_substitute_env_vars_alternative_placeholder_format(self):
        """Test substitution with environment variable name without ${} wrapper"""
        # Arrange
        test_config = {
            "users": [
                {"username": "MINIO_USER_CONCOURSE", "policy": "test.json"}
            ]
        }

        env_vars = {'MINIO_USER_CONCOURSE': 'alt-format-user'}

        # Act
        with patch.dict(os.environ, env_vars, clear=False):
            result = substitute_env_vars_in_config(test_config)

        # Assert
        assert result['users'][0]['username'] == 'alt-format-user'
