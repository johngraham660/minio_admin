# MinIO Admin Project

A Python project for managing MinIO buckets, policies, and users with HashiCorp Vault integration and comprehensive testing.

## Features

- ✅ **MinIO Bucket Management**: Automated bucket creation
- ✅ **User & Policy Management**: Create users and assign policies
- 🔐 **HashiCorp Vault Integration**: Secure password retrieval using AppRole authentication
- 🔧 **Interactive Setup Helper**: Guided Vault secrets configuration with validation
- 📋 **Configuration-Driven**: Users and policies defined in JSON config, no hardcoded values
- 🛡️ **Robust Error Handling**: Graceful fallbacks and clear user guidance
- 🧪 **Comprehensive Testing**: Unit, integration, and edge case tests
- 🚀 **CI/CD Ready**: GitHub Actions workflow included

## Project Structure

```
.
├── Makefile                    # Build automation with testing targets
├── pytest.ini                 # Pytest configuration
├── requirements.txt            # Python dependencies (includes hvac for Vault)
├── .env.example               # Environment variables template
├── config/
│   └── minio_server_config.json # Server configuration (passwords removed)
├── policies/
│   ├── bucketcreator-policy.json
│   ├── concourse-pipeline-artifacts-policy.json
│   ├── jenkins-pipeline-artifacts-policy.json
│   └── k8s-etcdbackup-policy.json
├── scripts/
│   └── setup_vault_secrets.py # Interactive Vault secrets setup helper
├── src/
│   ├── manage_minio.py        # Main MinIO management script
│   └── vault_client.py        # HashiCorp Vault client module
└── tests/
    ├── conftest.py            # Shared test fixtures
    ├── test_create_buckets.py # Unit tests
    ├── test_edge_cases.py     # Edge case tests
    └── test_integration.py    # Integration tests
```

## Setup

### Prerequisites
- Python 3.13 or higher
- Access to a MinIO server

### Environment Setup

1. **Setup virtual environment and install dependencies:**
   ```bash
   make dev
   ```

   Or manually:
   ```bash
   make setup-venv
   make install
   ```

2. **Configure environment variables:**
   
   Copy the example environment file and configure your settings:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your configuration:
   ```bash
   # MinIO Server Configuration
   MINIO_SERVER=localhost
   MINIO_PORT=9000
   MINIO_SECURE=false
   
   # MinIO Credentials
   BUCKET_CREATOR_ACCESS_KEY=your_bucket_creator_access_key
   BUCKET_CREATOR_SECRET_KEY=your_bucket_creator_secret_key
   MINIO_ADMIN_ACCESS_KEY=your_admin_access_key
   MINIO_ADMIN_SECRET_KEY=your_admin_secret_key
   
   # MinIO Service User Names (configure for your environment)
   MINIO_USER_CONCOURSE=your_concourse_user
   MINIO_USER_JENKINS=your_jenkins_user
   MINIO_USER_K8S=your_k8s_user
   
   # HashiCorp Vault Configuration
   VAULT_ADDR=https://vault.example.com:8200
   VAULT_ROLE_ID=your_role_id
   VAULT_SECRET_ID=your_secret_id
   ```

   **Security Note**: Service usernames are configurable via environment variables and the application uses a configuration-driven approach instead of hardcoded values. This prevents exposing internal service naming conventions in your repository while providing robust fallback handling for incomplete configurations.

3. **Set up HashiCorp Vault secrets:**
   
   Use the interactive setup helper to store MinIO user passwords in Vault:
   ```bash
   python scripts/setup_vault_secrets.py
   ```
   
   This script will:
   - Verify your Vault connection and credentials
   - Load user configuration from `config/minio_server_config.json`
   - Warn you if environment variables are missing (with fallback options)
   - Interactively prompt for passwords for each configured user
   - Store the passwords securely in Vault at `secret/data/minio/users`
   - Verify the secrets were stored correctly
   
   **Manual Vault setup (alternative):**
   ```bash
   # Using Vault CLI:
   vault kv put secret/minio/users \
     your_concourse_user=secure_password_1 \
     your_jenkins_user=secure_password_2 \
     your_k8s_user=secure_password_3
   
   # Using curl with Vault HTTP API:
   # First, authenticate and get a token
   VAULT_TOKEN=$(curl -s -X POST $VAULT_ADDR/v1/auth/approle/login \
     -d '{"role_id":"'$VAULT_ROLE_ID'","secret_id":"'$VAULT_SECRET_ID'"}' \
     | jq -r '.auth.client_token')
   
   # Then store the secrets
   curl -X POST $VAULT_ADDR/v1/secret/data/minio/users \
     -H "X-Vault-Token: $VAULT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "data": {
         "your_concourse_user": "secure_password_1",
         "your_jenkins_user": "secure_password_2", 
         "your_k8s_user": "secure_password_3"
       }
     }'
   ```

## Available Make Targets

| Target | Description |
|--------|-------------|
| `make help` | Show all available targets |
| `make setup-venv` | Create Python virtual environment |
| `make install` | Install project dependencies |
| `make test` | Run all tests |
| `make test-unit` | Run unit tests only |
| `make test-integration` | Run integration tests only |
| `make test-coverage` | Run tests with coverage reporting |
| `make test-dev` | Run tests and coverage with non-blocking lint (developer-friendly) |
| `make test-all` | Run tests, coverage, and linting (strict - fails on lint errors) |
| `make lint` | Run code quality checks (flake8) |
| `make clean` | Clean up generated files and cache |
| `make quick` | Quick test run (unit tests only) |
| `make ci` | Continuous integration workflow |
| `make dev` | Full development setup (uses test-dev) |

## Testing

### Running Tests

**Quick unit tests:**
```bash
make test-unit
```

**All tests with coverage:**
```bash
make test-coverage
```

**Developer-friendly test suite (non-blocking lint):**
```bash
make test-dev
```

**Complete test suite (strict mode - fails on lint errors):**
```bash
make test-all
```

### Test Modes

**Developer Mode (`test-dev`)**:
- Runs all tests with coverage
- Shows linting issues but doesn't fail the build
- Perfect for active development
- Used by `make dev`

**Strict Mode (`test-all`)**:
- Runs all tests with coverage  
- Fails if any linting issues are found
- Ideal for CI/CD and pre-commit validation
- Used by `make ci`

### Test Categories

- **Unit Tests**: Test individual functions with mocking
- **Integration Tests**: Test end-to-end workflows
- **Edge Cases**: Test error conditions and boundary cases

### Test Coverage

After running `make test-coverage`, view the coverage report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Code Quality

Run linting checks:
```bash
make lint
```

## Usage

### HashiCorp Vault Integration

The application now retrieves MinIO user passwords from HashiCorp Vault instead of storing them in configuration files. This provides better security and secret management.

**Vault Setup Requirements:**
- Vault server accessible at the configured URL
- AppRole authentication method enabled
- Secrets stored under `secret/data/minio/users` path

**Fallback Behavior:**
If Vault is unavailable, the application will attempt to fall back to passwords in the configuration file (for backward compatibility during transition).

### Creating Buckets and Users

1. Configure your buckets and users in `config/minio_server_config.json` (passwords are now retrieved from Vault)
2. Set up environment variables (including Vault credentials and service usernames)
3. Store user passwords in Vault using the setup helper:
   ```bash
   python scripts/setup_vault_secrets.py
   ```
4. Run the main script to create buckets, users, and policies:
   ```bash
   python src/manage_minio.py
   ```

### Configuration Validation

The setup script includes intelligent configuration validation:

- **Automatic fallback handling**: If service usernames aren't configured in `.env`, the script uses meaningful defaults (`user1`, `user2`, `user3`) with clear warnings
- **Interactive confirmation**: You'll be prompted before proceeding with fallback usernames
- **Configuration guidance**: Clear instructions on how to configure proper service names
- **Error prevention**: Validates configuration before making any changes to Vault

### Testing Vault Connection

Test your Vault connection:
```bash
python src/vault_client.py
```

Or use the setup script which includes connection verification:
```bash
python scripts/setup_vault_secrets.py
```

### Testing the Scripts

The test suite provides comprehensive coverage including:
- Function-level unit testing
- Error handling scenarios
- Environment configuration testing
- Real configuration file validation

## CI/CD

The project includes a CI target for automated testing:
```bash
make ci
```

This runs:
1. Environment setup
2. Dependency installation
3. Full test suite with coverage
4. Code quality checks

## Development Workflow

1. **Setup development environment:**
   ```bash
   make dev
   ```

2. **Make your changes**

3. **Run tests:**
   ```bash
   make test-unit  # Quick feedback
   make test-all   # Complete validation
   ```

4. **Clean up:**
   ```bash
   make clean
   ```

## Dependencies

See `requirements.txt` for the complete list. Key dependencies:
- `minio`: MinIO Python SDK
- `python-dotenv`: Environment variable management
- `hvac`: HashiCorp Vault client library
- `pytest`: Testing framework
- `pytest-cov`: Coverage reporting
- `pytest-mock`: Mocking utilities
- `flake8`: Code quality checking