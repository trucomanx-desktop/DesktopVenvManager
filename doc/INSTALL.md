# virtual-env-manager

A local Linux desktop application for creating, importing, inspecting, and managing Python `venv` environments.


## Install from PYPI

The homepage in pipy is https://pypi.org/project/virtual_env_manager/

```bash
pip install --upgrade virtual_env_manager
```

or (recommended for desktop applications)

```bash
pipx install virtual_env_manager
```


Using:

```bash
virtual-env-manager
```

If you would like the program to initialize at the start of the Linux session, use `virtual-env-manager --autostart`.

## Install from source
Installing `virtual-env-manager` program

```bash
git clone https://github.com/trucomanx-desktop/VirtualEnvManager.git
cd VirtualEnvManager
pip install -r requirements.txt
cd src
python -m build
pip install dist/virtual_env_manager-*.tar.gz
```
Using:

```bash
virtual-env-manager
```

## Uninstall

```bash
pip uninstall virtual_env_manager
```
