# Contributing to Extended Memory MCP Server

We welcome contributions to the Extended Memory MCP Server project! This document provides guidelines for contributing.

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/ssmirnovpro/extended-memory-mcp.git
cd extended-memory-mcp
```

2. Install dependencies:
```bash
pip install -e ".[dev,redis]"
```

3. Run tests to verify setup:
```bash
PYTHONPATH=src python3 -m pytest tests/
```

## How to Contribute

### Reporting Issues
- Use GitHub Issues to report bugs or request features
- Search existing issues before creating new ones
- Provide clear descriptions and reproduction steps

### Code Contributions
1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass: `pytest`
6. Submit a pull request

## Code Standards

- Follow PEP 8 style guidelines
- Include docstrings for new functions and classes
- Add tests for new features
- Keep commits focused and descriptive

## Pull Request Process

1. Update documentation if needed
2. Ensure all tests pass
3. Add a clear description of changes
4. Reference related issues

## Questions?

Use GitHub Issues for project-related questions and discussions.

Thank you for contributing!
