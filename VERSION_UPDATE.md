# Version Update Guide

## How to Update Version

To update the project version, you only need to change **ONE FILE**:

```
src/extended_memory_mcp/__init__.py
```

Change the line:
```python
__version__ = "0.9.0"  # ← Change this
```

## What Gets Updated Automatically

- ✅ **setup.py** - imports version from `__init__.py`
- ✅ **pip package** - uses version from setup.py

## What Needs Manual Update (if needed)

- ⚠️ **GitHub Workflow default** (`.github/workflows/release.yml`) - optional, for manual releases
- ⚠️ **Git tags** - create with `git tag v0.10.0`

## Release Process

1. Update version in `src/extended_memory_mcp/__init__.py`
2. Commit and push changes
3. Create git tag: `git tag v0.10.0 && git push origin v0.10.0`
4. Publish to PyPI: `python3 -m build && python3 -m twine upload dist/*`

That's it! No more hunting for version numbers across files.
