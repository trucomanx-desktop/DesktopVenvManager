# desktop-venv-manager

A local Linux desktop application for creating, importing, inspecting, and managing Python `venv` environments.

## Upload to PYPI

```bash
pip install --upgrade pkginfo twine packaging build

cd src
python -m build
twine upload dist/*
```
