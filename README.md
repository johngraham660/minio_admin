# MinIO Admin Project

A Python project for managing MinIO buckets and policies with comprehensive testing.

## Project Structure

```
.
├── Makefile                    # Build automation with testing targets
├── pytest.ini                 # Pytest configuration
├── requirements.txt            # Python dependencies
├── config/
│   └── minio_buckets.json     # Bucket configuration
├── policies/
│   ├── bucketcreator-policy.json
│   └── virtua-devops-policy.json
├── src/
│   ├── create_buckets.py      # Main bucket creation script
│   └── policy_manager.py      # Policy management script
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

2. **Configure environment variables (create a .env file):**
   ```bash
   MINIO_SERVER=localhost
   MINIO_PORT=9000
   MINIO_SECURE=false
   BUCKET_CREATOR_ACCESS_KEY=your_access_key
   BUCKET_CREATOR_SECRET_KEY=your_secret_key
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

### Creating Buckets

1. Configure your bucket list in `config/minio_buckets.json`
2. Set up environment variables
3. Run the script:
   ```bash
   python src/create_buckets.py
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
- `pytest`: Testing framework
- `pytest-cov`: Coverage reporting
- `pytest-mock`: Mocking utilities
- `flake8`: Code quality checking