#!/usr/bin/env python3
"""Virtual Env Manager: a local graphical manager for Python virtual environments."""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PyQt5.QtCore import Qt, QProcess
from PyQt5.QtGui import QColor, QIcon, QDesktopServices
from PyQt5.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QSizePolicy, QAction, QWidget, QProgressBar,
)

import virtual_env_manager.about as about
import virtual_env_manager.modules.configure as configure 
from virtual_env_manager.modules.resources import resource_path

from virtual_env_manager.modules.wabout    import show_about_window

CONFIG = {
    "toolbar_configure": "Configure",
    "toolbar_configure_tooltip": "Open the configure Json file of program GUI",
    "toolbar_about": "About",
    "toolbar_about_tooltip": "About the program",
    "toolbar_coffee": "Coffee",
    "toolbar_coffee_tooltip": "Buy me a coffee (TrucomanX)",
    "window_width": 1024,
    "window_height": 800,
    "app_subtitle": "Manage local Python virtual environments",
    "btn_new_text": "Create New",
    "btn_new_tooltip": "Create a virtual environment using the selected Python interpreter.",
    "btn_import_text": "Import Existing",
    "btn_import_tooltip": "Add an existing virtual environment from disk after validating its structure.",
    "btn_refresh_text": "Refresh",
    "btn_refresh_tooltip": "Recheck registered folders and update their Python versions and disk usage.",
    "refresh_progress_tooltip": "Shows how many saved environments have been checked during refresh.",
    "btn_terminal_text": "Open Terminal",
    "btn_terminal_tooltip": "Open a terminal at the selected environment folder with its activation command ready.",
    "btn_remove_text": "Remove from List",
    "btn_remove_tooltip": "Confirm removal of the selected environment and deletion of its folder from disk.",
    "column_name": "Name",
    "column_description": "Description",
    "column_python": "Python Version",
    "column_size": "Disk Usage",
    "column_status": "Status",
    "column_name_tooltip": "The display name assigned to this virtual environment.",
    "column_description_tooltip": "A short note describing the purpose of this environment.",
    "column_python_tooltip": "The Python interpreter version used by this environment.",
    "column_size_tooltip": "Total size of files currently stored inside the environment folder.",
    "column_status_tooltip": "Whether this folder currently contains a valid virtual environment.",
    "status_valid": "Valid",
    "status_missing": "Invalid / Missing",
    "details_title": "Environment Details",
    "detail_name": "Name",
    "detail_description": "Description",
    "detail_path": "Full Path",
    "detail_python": "Python Version",
    "detail_size": "Disk Usage",
    "detail_activate": "Activation Command",
    "detail_name_tooltip": "The saved display name for the selected environment.",
    "detail_description_tooltip": "The saved description for the selected environment.",
    "detail_path_tooltip": "The absolute filesystem path to this environment.",
    "detail_python_tooltip": "The interpreter version detected inside this environment.",
    "detail_size_tooltip": "The current total size of the environment folder.",
    "detail_activate_tooltip": "Copy or run this command in a compatible shell to activate the environment.",
    "total_space_template": "Total disk space used by all environments: {size}",
    "no_selection": "Select an environment to see its details.",
    "dialog_new_title": "Create Virtual Environment",
    "dialog_import_title": "Import Virtual Environment",
    "field_name": "Name",
    "field_name_tooltip": "A short, recognizable name for this environment.",
    "field_description": "Description",
    "field_description_tooltip": "Optional notes about what this environment is used for.",
    "field_path": "Location",
    "field_path_tooltip": "The folder where the virtual environment will be created or which will be imported.",
    "field_python": "Python Version",
    "field_python_tooltip": "Choose the installed Python interpreter used to create this environment.",
    "browse_text": "Browse…",
    "browse_tooltip": "Choose a folder on disk.",
    "create_text": "Create",
    "import_text": "Import",
    "cancel_text": "Cancel",
    "confirm_yes_text": "Delete Environment",
    "error_title": "Error",
    "warning_title": "Warning",
    "confirm_title": "Confirm Deletion",
    "confirm_delete_template": "Permanently delete the environment folder below and remove its record?\n\n{path}\n\nThis cannot be undone.",
    "error_name_required": "Enter a name for the environment.",
    "error_path_required": "Choose a folder path.",
    "error_path_exists": "The selected location already exists. Choose a new folder.",
    "error_duplicate_path": "This environment path is already in the list.",
    "error_no_python": "No supported Python 3 interpreter was found on this system.",
    "error_creation_template": "Could not create the virtual environment:\n{error}",
    "error_invalid_venv": "The selected folder does not contain a valid virtual environment.",
    "error_delete_template": "Could not delete the environment folder:\n{error}",
    "error_unsafe_delete": "For safety, this folder cannot be deleted because it is not a valid environment directory.",
    "terminal_error_template": "Could not open a terminal:\n{error}",
    "browse_create_title": "Choose Environment Parent Folder",
    "browse_import_title": "Choose Virtual Environment Folder",
    "file_dialog_directory": "Select Folder",
    "python_unknown": "Unknown",
    "size_zero": "0 B",
    "terminal_command": "bash",
    "terminal_working_directory": "Open terminal in the environment folder",
    "table_tooltip": "Registered virtual environments. Select a row to view its details below.",
    "no_terminal_error": "No terminal command is available.",
}

CONFIG_DIR = Path.home() / ".config" / "virtual_env_manager"
CONFIG_FILE = CONFIG_DIR / "config.json"


def is_venv(path):
    """Return true if path has the standard Linux venv activation and interpreter files."""
    path = Path(path).expanduser()
    return path.is_dir() and (path / "bin" / "activate").is_file() and any(
        (path / "bin" / name).is_file() for name in ("python", "python3")
    )


def detect_python_version(path):
    candidates = [Path(path) / "bin" / "python", Path(path) / "bin" / "python3"]
    for executable in candidates:
        if executable.is_file():
            try:
                result = subprocess.run(
                    [str(executable), "--version"], capture_output=True, text=True,
                    timeout=5, check=False,
                )
                output = (result.stdout or result.stderr).strip()
                match = re.search(r"Python\s+(\d+(?:\.\d+){1,2})", output)
                if match:
                    return match.group(1)
            except (OSError, subprocess.TimeoutExpired):
                pass
    return CONFIG["python_unknown"]


def available_pythons():
    names = {"python3"}
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        try:
            for name in os.listdir(directory or "."):
                if re.fullmatch(r"python3(?:\.\d+)+", name):
                    names.add(name)
        except OSError:
            continue
    found = {}
    for name in names:
        executable = shutil.which(name)
        if not executable:
            continue
        try:
            result = subprocess.run([executable, "--version"], capture_output=True,
                                    text=True, timeout=5, check=False)
            output = (result.stdout or result.stderr).strip()
            match = re.search(r"Python\s+(\d+(?:\.\d+){1,2})", output)
            if match and match.group(1).split(".")[0] == "3":
                found[(tuple(int(part) for part in match.group(1).split(".")), name)] = (name, match.group(1))
        except (OSError, subprocess.TimeoutExpired):
            continue
    return sorted(found.values(), key=lambda item: (tuple(map(int, item[1].split("."))), item[0]))


def folder_size(path):
    total = 0
    try:
        for root, dirs, files in os.walk(path, followlinks=False):
            dirs[:] = [d for d in dirs if not (Path(root) / d).is_symlink()]
            for filename in files:
                item = Path(root) / filename
                try:
                    if not item.is_symlink():
                        total += item.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def format_size(size):
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


class EnvironmentDialog(QDialog):
    def __init__(self, parent, importing=False):
        super().__init__(parent)
        self.importing = importing
        self.setWindowTitle(CONFIG["dialog_import_title"] if importing else CONFIG["dialog_new_title"])
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setToolTip(CONFIG["field_name_tooltip"])
        self.description_edit = QLineEdit()
        self.description_edit.setToolTip(CONFIG["field_description_tooltip"])
        self.path_edit = QLineEdit()
        self.path_edit.setToolTip(CONFIG["field_path_tooltip"])
        self.browse_button = QPushButton(CONFIG["browse_text"])
        self.browse_button.setIcon(QIcon.fromTheme("folder-open"))
        self.browse_button.setToolTip(CONFIG["browse_tooltip"])
        path_row = QWidget()
        path_layout = QHBoxLayout(path_row)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.addWidget(self.path_edit, 1)
        path_layout.addWidget(self.browse_button)
        form.addRow(self._label(CONFIG["field_name"], CONFIG["field_name_tooltip"]), self.name_edit)
        form.addRow(self._label(CONFIG["field_description"], CONFIG["field_description_tooltip"]), self.description_edit)
        form.addRow(self._label(CONFIG["field_path"], CONFIG["field_path_tooltip"]), path_row)
        self.python_combo = QComboBox()
        self.python_combo.setToolTip(CONFIG["field_python_tooltip"])
        self.python_versions = available_pythons()
        for command, version in self.python_versions:
            self.python_combo.addItem(f"Python {version} ({command})", command)
        self.python_row = self._label(CONFIG["field_python"], CONFIG["field_python_tooltip"])
        if not importing:
            form.addRow(self.python_row, self.python_combo)
        else:
            self.python_combo.setVisible(False)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Cancel).setText(CONFIG["cancel_text"])
        self.accept_button = buttons.addButton(CONFIG["import_text"] if importing else CONFIG["create_text"], QDialogButtonBox.AcceptRole)
        self.accept_button.setIcon(QIcon.fromTheme("list-add" if importing else "document-new"))
        self.accept_button.setToolTip(CONFIG["btn_import_tooltip"] if importing else CONFIG["btn_new_tooltip"])
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        self.browse_button.clicked.connect(self.browse)
        if not importing and not self.python_versions:
            self.accept_button.setEnabled(False)
            self.python_combo.setToolTip(CONFIG["error_no_python"])

    @staticmethod
    def _label(text, tooltip):
        label = QLabel(text)
        label.setToolTip(tooltip)
        return label

    def browse(self):
        title = CONFIG["browse_import_title"] if self.importing else CONFIG["browse_create_title"]
        path = QFileDialog.getExistingDirectory(self, title, str(Path.home()))
        if path:
            self.path_edit.setText(path)
            if self.importing and not self.name_edit.text().strip():
                self.name_edit.setText(Path(path).name)


class SortableItem(QTableWidgetItem):
    def __lt__(self, other):
        left = self.data(Qt.UserRole + 1)
        right = other.data(Qt.UserRole + 1)
        if left is not None and right is not None:
            return left < right
        return super().__lt__(other)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle(about.__program_name__)
        self.resize(CONFIG["window_width"], CONFIG["window_height"])
        
        ## Icon
        # Get base directory for icons
        self.icon_path = resource_path("icons", "logo.png")
        self.setWindowIcon(QIcon(self.icon_path)) 
        
        self.environments = []
        self._load()
        
        self._create_toolbar()
        self._create_status_bar()
        
        # Gnerate GUI
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        subtitle = QLabel(CONFIG["app_subtitle"])
        subtitle.setStyleSheet("color: palette(mid); margin-bottom: 8px;")
        layout.addWidget(subtitle)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([CONFIG[key] for key in ("column_name", "column_description", "column_python", "column_size", "column_status")])
        for column, tooltip_key in enumerate(("column_name_tooltip", "column_description_tooltip", "column_python_tooltip", "column_size_tooltip", "column_status_tooltip")):
            self.table.horizontalHeaderItem(column).setToolTip(CONFIG[tooltip_key])
        self.table.setToolTip(CONFIG["table_tooltip"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.table, 1)
        self.details_title = QLabel(CONFIG["details_title"])
        self.details_title.setStyleSheet("font-size: 16px; font-weight: 600; margin-top: 8px;")
        layout.addWidget(self.details_title)
        self.details = {}
        details_form = QFormLayout()
        fields = (("name", "detail_name", "detail_name_tooltip"), ("description", "detail_description", "detail_description_tooltip"),
                  ("path", "detail_path", "detail_path_tooltip"), ("python", "detail_python", "detail_python_tooltip"),
                  ("size", "detail_size", "detail_size_tooltip"), ("activate", "detail_activate", "detail_activate_tooltip"))
        for key, label_key, tip_key in fields:
            label = QLabel(CONFIG[label_key])
            label.setToolTip(CONFIG[tip_key])
            value = QLineEdit()
            value.setReadOnly(True)
            value.setToolTip(CONFIG[tip_key])
            details_form.addRow(label, value)
            self.details[key] = value
        layout.addLayout(details_form)
        buttons_row = QHBoxLayout()
        self.terminal_button = self._button("btn_terminal_text", "btn_terminal_tooltip", "utilities-terminal")
        self.remove_button = self._button("btn_remove_text", "btn_remove_tooltip", "edit-delete")
        self.terminal_button.setEnabled(False)
        self.remove_button.setEnabled(False)
        buttons_row.addWidget(self.terminal_button)
        buttons_row.addWidget(self.remove_button)
        buttons_row.addStretch(1)
        layout.addLayout(buttons_row)
        self.total_label = QLabel()
        self.total_label.setToolTip("The combined disk usage of all registered environment folders.")
        self.total_label.setStyleSheet("font-weight: 600; padding: 8px 0;")
        layout.addWidget(self.total_label)
        self.terminal_button.clicked.connect(self.open_terminal)
        self.remove_button.clicked.connect(self.remove_environment)
        self.table.itemSelectionChanged.connect(self.update_details)
        self.refresh()

    def _create_toolbar(self):
        self.toolbar = self.addToolBar("Main")
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        # Primary environment actions
        self.new_action = QAction(QIcon.fromTheme("list-add"), CONFIG["btn_new_text"], self)
        self.new_action.setToolTip(CONFIG["btn_new_tooltip"])
        self.new_action.triggered.connect(self.create_environment)
        self.toolbar.addAction(self.new_action)
        self.import_action = QAction(QIcon.fromTheme("folder-open"), CONFIG["btn_import_text"], self)
        self.import_action.setToolTip(CONFIG["btn_import_tooltip"])
        self.import_action.triggered.connect(self.import_environment)
        self.toolbar.addAction(self.import_action)
        self.refresh_action = QAction(QIcon.fromTheme("view-refresh"), CONFIG["btn_refresh_text"], self)
        self.refresh_action.setToolTip(CONFIG["btn_refresh_tooltip"])
        self.refresh_action.triggered.connect(self.refresh)
        self.toolbar.addAction(self.refresh_action)
        
        # Adicionar o espaçador
        self.toolbar_spacer = QWidget()
        self.toolbar_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.toolbar.addWidget(self.toolbar_spacer)
        
        #
        self.configure_action = QAction(QIcon.fromTheme("document-properties"), 
                                        CONFIG["toolbar_configure"], 
                                        self)
        self.configure_action.setToolTip(CONFIG["toolbar_configure_tooltip"])
        self.configure_action.triggered.connect(self.open_configure_editor)
        self.toolbar.addAction(self.configure_action)
        
        #
        self.about_action = QAction(QIcon.fromTheme("help-about"), 
                                    CONFIG["toolbar_about"], 
                                    self)
        self.about_action.setToolTip(CONFIG["toolbar_about_tooltip"])
        self.about_action.triggered.connect(self.open_about)
        self.toolbar.addAction(self.about_action)
        
        # Coffee
        self.coffee_action = QAction(   QIcon.fromTheme("emblem-favorite"), 
                                        CONFIG["toolbar_coffee"], 
                                        self)
        self.coffee_action.setToolTip(CONFIG["toolbar_coffee_tooltip"])
        self.coffee_action.triggered.connect(self.on_coffee_action_click)
        self.toolbar.addAction(self.coffee_action)

        # Conectar ao sinal de mudança de orientação
        self.toolbar.orientationChanged.connect(self.on_update_spacer_policy)
        self.on_update_spacer_policy()

    def _create_status_bar(self):
        self.refresh_progress_bar = QProgressBar()
        self.refresh_progress_bar.setToolTip(CONFIG["refresh_progress_tooltip"])
        self.refresh_progress_bar.setRange(0, 100)
        self.refresh_progress_bar.setValue(100)
        self.refresh_progress_bar.setFixedWidth(180)
        self.refresh_progress_bar.setTextVisible(True)
        self.statusBar().addPermanentWidget(self.refresh_progress_bar)

    def on_update_spacer_policy(self):
        """Atualiza a política do espaçador baseado na orientação da toolbar"""
        if self.toolbar.orientation() == Qt.Horizontal:
            # Horizontal: expande na largura
            self.toolbar_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        else:
            # Vertical: expande na altura
            self.toolbar_spacer.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

    def _open_file_in_text_editor(self, filepath):
        if os.name == 'nt':  # Windows
            os.startfile(filepath)
        elif os.name == 'posix':  # Linux/macOS
            subprocess.run(['xdg-open', filepath])
    
    def open_configure_editor(self):
        self._open_file_in_text_editor(CONFIG_FILE.as_posix())

    def open_about(self):
        data={
            "version": about.__version__,
            "package": about.__package__,
            "program_name": about.__program_name__,
            "author": about.__author__,
            "email": about.__email__,
            "description": about.__description__,
            "url_source": about.__url_source__,
            "url_doc": about.__url_doc__,
            "url_funding": about.__url_funding__,
            "url_bugs": about.__url_bugs__
        }
        show_about_window(data,self.icon_path)

    def on_coffee_action_click(self):
        QDesktopServices.openUrl(QUrl("https://ko-fi.com/trucomanx"))

    def _button(self, text_key, tip_key, icon_name):
        button = QPushButton(CONFIG[text_key])
        button.setIcon(QIcon.fromTheme(icon_name))
        button.setToolTip(CONFIG[tip_key])
        return button

    def _load(self):
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self.environments = [item for item in data if isinstance(item, dict) and item.get("path")]
        except (OSError, json.JSONDecodeError):
            self.environments = []

    def _save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        temporary = CONFIG_FILE.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(self.environments, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(CONFIG_FILE)

    def refresh(self):
        total = len(self.environments)
        self.refresh_action.setEnabled(False)
        self.refresh_progress_bar.setRange(0, 100)
        self.refresh_progress_bar.setValue(0)
        try:
            for index, env in enumerate(self.environments, start=1):
                path = Path(env["path"]).expanduser()
                env["valid"] = is_venv(path)
                if env["valid"]:
                    env["python_version"] = detect_python_version(path)
                    env["size_bytes"] = folder_size(path)
                else:
                    env["python_version"] = env.get("python_version") or CONFIG["python_unknown"]
                    env["size_bytes"] = 0
                progress = int(index * 100 / total) if total else 100
                self.refresh_progress_bar.setValue(progress)
                QApplication.processEvents()
            self._save()
            self.populate_table()
            self.update_details()
            self.total_label.setText(CONFIG["total_space_template"].format(size=format_size(sum(env.get("size_bytes", 0) for env in self.environments))))
            self.refresh_progress_bar.setValue(100)
        finally:
            self.refresh_action.setEnabled(True)

    def populate_table(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.environments))
        for row, env in enumerate(self.environments):
            values = (env.get("name", Path(env["path"]).name), env.get("description", ""),
                      env.get("python_version", CONFIG["python_unknown"]), format_size(env.get("size_bytes", 0)),
                      CONFIG["status_valid"] if env.get("valid") else CONFIG["status_missing"])
            for col, value in enumerate(values):
                item = SortableItem(value)
                item.setToolTip((CONFIG[("column_name_tooltip", "column_description_tooltip", "column_python_tooltip", "column_size_tooltip", "column_status_tooltip")[col]]))
                if col == 3:
                    item.setData(Qt.UserRole, env.get("size_bytes", 0))
                    item.setData(Qt.UserRole + 1, env.get("size_bytes", 0))
                elif col == 2:
                    try:
                        item.setData(Qt.UserRole + 1, tuple(int(part) for part in value.split(".")))
                    except ValueError:
                        item.setData(Qt.UserRole + 1, (0,))
                if not env.get("valid"):
                    item.setForeground(QColor("#c62828"))
                self.table.setItem(row, col, item)
            self.table.item(row, 0).setData(Qt.UserRole, row)
        self.table.setSortingEnabled(True)

    def selected_environment(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        index = item.data(Qt.UserRole) if item else None
        if not isinstance(index, int) or index >= len(self.environments):
            # Sorting changes visual row order; identify the record by its unique path.
            name = item.text() if item else None
            matches = [env for env in self.environments if env.get("name") == name]
            return matches[0] if matches else None
        return self.environments[index]

    def update_details(self):
        env = self.selected_environment()
        enabled = env is not None
        self.terminal_button.setEnabled(bool(env and env.get("valid")))
        self.remove_button.setEnabled(enabled)
        if not env:
            for value in self.details.values():
                value.clear()
            self.details["name"].setPlaceholderText(CONFIG["no_selection"])
            return
        path = str(Path(env["path"]).expanduser())
        data = {"name": env.get("name", ""), "description": env.get("description", ""), "path": path,
                "python": env.get("python_version", CONFIG["python_unknown"]), "size": format_size(env.get("size_bytes", 0)),
                "activate": f"source {shlex_quote(str(Path(path) / 'bin' / 'activate'))}" if env.get("valid") else ""}
        for key, value in data.items():
            self.details[key].setText(value)

    def create_environment(self):
        dialog = EnvironmentDialog(self)
        if not dialog.exec_():
            return
        name = dialog.name_edit.text().strip()
        raw_parent = dialog.path_edit.text().strip()
        parent = Path(raw_parent).expanduser()
        if not name:
            QMessageBox.warning(self, CONFIG["warning_title"], CONFIG["error_name_required"])
            return
        if not raw_parent:
            QMessageBox.warning(self, CONFIG["warning_title"], CONFIG["error_path_required"])
            return
        full_path = parent / name
        if full_path.exists():
            QMessageBox.warning(self, CONFIG["warning_title"], CONFIG["error_path_exists"])
            return
        if self._is_duplicate(full_path):
            QMessageBox.warning(self, CONFIG["warning_title"], CONFIG["error_duplicate_path"])
            return
        command = dialog.python_combo.currentData()
        try:
            subprocess.run([shutil.which(command) or command, "-m", "venv", str(full_path)], check=True, capture_output=True, text=True)
        except (OSError, subprocess.CalledProcessError) as error:
            detail = error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) and error.stderr else str(error)
            QMessageBox.critical(self, CONFIG["error_title"], CONFIG["error_creation_template"].format(error=detail))
            return
        version = next((version for cmd, version in dialog.python_versions if cmd == command), CONFIG["python_unknown"])
        self.environments.append({"name": name, "description": dialog.description_edit.text().strip(),
                                  "path": str(full_path.resolve()), "python_version": version, "valid": True})
        self.refresh()

    def import_environment(self):
        dialog = EnvironmentDialog(self, importing=True)
        if not dialog.exec_():
            return
        raw_path = dialog.path_edit.text().strip()
        path = Path(raw_path).expanduser()
        if not raw_path:
            QMessageBox.warning(self, CONFIG["warning_title"], CONFIG["error_path_required"])
            return
        if not is_venv(path):
            QMessageBox.warning(self, CONFIG["warning_title"], CONFIG["error_invalid_venv"])
            return
        if self._is_duplicate(path):
            QMessageBox.warning(self, CONFIG["warning_title"], CONFIG["error_duplicate_path"])
            return
        self.environments.append({"name": dialog.name_edit.text().strip() or path.name,
                                  "description": dialog.description_edit.text().strip(),
                                  "path": str(path.resolve()), "python_version": detect_python_version(path), "valid": True})
        self.refresh()

    def _is_duplicate(self, path):
        normalized = os.path.realpath(path)
        return any(os.path.realpath(env["path"]) == normalized for env in self.environments)

    def open_terminal(self):
        env = self.selected_environment()
        if not env or not env.get("valid"):
            return
        folder = str(Path(env["path"]).expanduser().resolve())
        activation = str(Path(folder) / "bin" / "activate")
        shell = CONFIG["terminal_command"]
        terminal = shutil.which(shell) if Path(shell).name != "bash" else None
        terminal = terminal or shutil.which("x-terminal-emulator") or shutil.which("gnome-terminal") or shutil.which("konsole") or shutil.which("xterm")
        try:
            command = f"cd {shlex_quote(folder)} && source {shlex_quote(activation)} && exec bash -i"
            if terminal and Path(terminal).name in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm"):
                args = ["-e", "bash", "-lc", command] if Path(terminal).name != "gnome-terminal" else ["--", "bash", "-lc", command]
                QProcess.startDetached(terminal, args, folder)
            elif terminal and Path(shell).name != "bash":
                QProcess.startDetached(terminal, ["-lc", command], folder)
            elif shutil.which("bash"):
                QProcess.startDetached(shutil.which("bash"), ["-lc", command], folder)
            else:
                raise OSError(CONFIG["no_terminal_error"])
        except OSError as error:
            QMessageBox.critical(self, CONFIG["error_title"], CONFIG["terminal_error_template"].format(error=error))

    def remove_environment(self):
        env = self.selected_environment()
        if not env:
            return
        path = Path(env["path"]).expanduser()
        confirm = QMessageBox(self)
        confirm.setWindowTitle(CONFIG["confirm_title"])
        confirm.setText(CONFIG["confirm_delete_template"].format(path=path))
        delete_button = confirm.addButton(CONFIG["confirm_yes_text"], QMessageBox.DestructiveRole)
        cancel_button = confirm.addButton(CONFIG["cancel_text"], QMessageBox.RejectRole)
        confirm.setDefaultButton(cancel_button)
        confirm.exec_()
        if confirm.clickedButton() != delete_button:
            return
        try:
            if path.exists():
                resolved = path.resolve()
                if resolved in (Path("/").resolve(), Path.home().resolve(), CONFIG_DIR.resolve()):
                    QMessageBox.warning(self, CONFIG["warning_title"], CONFIG["error_unsafe_delete"])
                    return
                if path.is_symlink():
                    path.unlink()
                else:
                    shutil.rmtree(path)
            self.environments.remove(env)
            self.refresh()
        except OSError as error:
            QMessageBox.critical(self, CONFIG["error_title"], CONFIG["error_delete_template"].format(error=error))


def shlex_quote(value):
    # Quote shell arguments without introducing another dependency.
    import shlex
    return shlex.quote(value)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(about.__program_name__)
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
