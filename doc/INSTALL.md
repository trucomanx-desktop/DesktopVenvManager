# desktop-venv-manager

A local Linux desktop application for creating, importing, inspecting, and managing Python `venv` environments.


## Install from PYPI

The homepage in pipy is https://pypi.org/project/desktop_venv_manager/

```bash
pip install --upgrade desktop_venv_manager
```

or (recommended for desktop applications)

```bash
pipx install desktop_venv_manager
```


Using:

```bash
desktop-venv-manager
```

If you would like the program to initialize at the start of the Linux session, use `desktop-venv-manager --autostart`.

## Install from source
Installing `desktop-venv-manager` program

```bash
git clone https://github.com/trucomanx-desktop/DesktopVenvManager.git
cd DesktopVenvManager
pip install -r requirements.txt
cd src
python -m build
pip install dist/desktop_venv_manager-*.tar.gz
```
Using:

```bash
desktop-venv-manager
```

## Uninstall

```bash
pip uninstall desktop_venv_manager
```
