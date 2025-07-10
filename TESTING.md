# Testing

## Setup
```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Or install with Redis support
pip install -e ".[redis,dev]"
```

## Run tests
```bash
PYTHONPATH=src python3 -m pytest tests/
```

## Development workflow
1. Install dev dependencies: `pip install -e ".[dev]"`
2. Run all tests: `PYTHONPATH=src python3 -m pytest tests/`
3. Run specific test: `PYTHONPATH=src python3 -m pytest tests/test_config_utils.py -v`
4. Run with coverage: `PYTHONPATH=src python3 -m pytest tests/ --cov=extended_memory_mcp`

## Dependencies
All dependencies are managed through setup.py:
- **install_requires**: Core dependencies (aiosqlite, pyyaml, jinja2, platformdirs)
- **extras_require[redis]**: Redis support (redis[hiredis])
- **extras_require[dev]**: Development tools (pytest, pytest-asyncio)
