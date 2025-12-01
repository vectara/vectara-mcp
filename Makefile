.PHONY: test lint install install-dev clean

# Run all tests
test:
	python -m pytest tests/ -v

# Run tests with coverage
test-cov:
	python -m pytest tests/ -v --cov=vectara_mcp --cov-report=term-missing

# Run integration tests only
test-integration:
	python -m pytest tests/test_integration.py -v -s

# Run unit tests only (excludes integration tests)
test-unit:
	python -m pytest tests/test_server.py tests/test_api_key_management.py tests/test_health_checks.py tests/test_connection_manager.py -v

# Run linting
lint:
	python -m pylint vectara_mcp/ --disable=C0114,C0115,C0116

# Run linting with all checks (stricter)
lint-strict:
	python -m pylint vectara_mcp/

# Install package in development mode
install:
	pip install -e .

# Install with test dependencies
install-dev:
	pip install -e ".[test]"
	pip install pylint

# Clean up build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
