# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-01-07

### Added
- Added tenacity library for robust retry handling with exponential backoff
- Added centralized constants for timeouts and configuration values
- Added version consistency across all package files

### Changed
- Updated all hardcoded version strings to use `__version__` from `__init__.py`
- Centralized magic numbers (timeouts, rate limits) into named constants
- Improved DRY compliance by eliminating duplicate API key error messages
- Made `correct_hallucinations` and `eval_factual_consistency` tools fully self-contained

### Improved
- **Code Quality**: Reduced code duplication and improved maintainability
- **Reliability**: Replaced custom retry logic with proven library used by major projects
- **Consistency**: Unified error handling and validation patterns across all MCP tools
- **Configuration**: Centralized timeout and limit configurations for easier tuning

### Fixed
- Fixed version inconsistencies between `__init__.py`, `pyproject.toml`, `setup.py`, and hardcoded strings
- Synchronized missing dependencies between `requirements.txt`, `pyproject.toml`, and `setup.py`
- Resolved "Event loop is closed" issues in async retry contexts

### Technical Details
- Retry logic now uses `AsyncRetrying` with configurable stop conditions and wait strategies
- All timeout values now reference named constants (e.g., `DEFAULT_TOTAL_TIMEOUT = 30`)
- Rate limiting parameters now use constants (`DEFAULT_MAX_REQUESTS = 100`)
- Version information now sourced from single source of truth (`__version__`)

## [0.1.5] - Previous Release
- Basic MCP server functionality
- Vectara RAG integration