# tk_ui.py
# --- Imports Section ---
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from core_dump import *
from mini_mode import MiniWindow
import threading
import os
import subprocess
import sys
import logging
import json
import re
from pathlib import Path
from datetime import datetime
import zipfile
import platform
try:
    import winreg
except ImportError:
    winreg = None
try:
    import py7zr # type: ignore
except ImportError:
    py7zr = None
# --- Tooltip Class Section ---
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
    def show_tooltip(self, event=None):
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip, text=self.text, background="yellow", relief="solid", borderwidth=1, padx=5, pady=2)
        label.pack()
    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
# --- Profile Dialog Class Section ---
class ProfileDialog(tk.Toplevel):
    def __init__(self, parent, app, profile_name="", extensions="", include_patterns="", exclude="", config_files=""):
        super().__init__(parent)
        self.app = app
        self.title("New Profile" if not profile_name else "Edit Profile")
        self.geometry("400x300")
        self.resizable(False, False)
        self.transient(parent)
        self.profile_name_var = tk.StringVar(value=profile_name)
        ttk.Label(self, text="Profile Name:").grid(row=0, column=0, sticky="w", pady=2, padx=5)
        name_entry = ttk.Entry(self, textvariable=self.profile_name_var, width=40)
        name_entry.grid(row=0, column=1, sticky="ew", pady=2, padx=5)
        ttk.Label(self, text="Extensions (; separated):").grid(row=1, column=0, sticky="w", pady=2, padx=5)
        self.extensions_text = tk.Text(self, height=3, width=50, undo=True)
        self.extensions_text.insert("1.0", extensions)
        self.extensions_text.grid(row=1, column=1, sticky="ew", pady=2, padx=5)
        ttk.Label(self, text="Include Patterns (; separated):").grid(row=2, column=0, sticky="w", pady=2, padx=5)
        self.include_text = tk.Text(self, height=3, width=50, undo=True)
        self.include_text.insert("1.0", include_patterns)
        self.include_text.grid(row=2, column=1, sticky="ew", pady=2, padx=5)
        ttk.Label(self, text="Exclude Patterns (; separated):").grid(row=3, column=0, sticky="w", pady=2, padx=5)
        self.exclude_text = tk.Text(self, height=3, width=50, undo=True)
        self.exclude_text.insert("1.0", exclude)
        self.exclude_text.grid(row=3, column=1, sticky="ew", pady=2, padx=5)
        ttk.Label(self, text="Config Files (; separated):").grid(row=4, column=0, sticky="w", pady=2, padx=5)
        self.config_text = tk.Text(self, height=3, width=50, undo=True)
        self.config_text.insert("1.0", config_files)
        self.config_text.grid(row=4, column=1, sticky="ew", pady=2, padx=5)
        button_frame = ttk.Frame(self)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Save", command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)
        self.columnconfigure(1, weight=1)
        if self.app.is_dark_mode():
            self.set_dark_theme()
    def set_dark_theme(self):
        style = ttk.Style()
        style.theme_use('clam')
        dark_bg = '#2e2e2e'
        dark_fg = '#ffffff'
        dark_entry_bg = '#3e3e3e'
        dark_button_bg = '#4e4e4e'
        style.configure('.', background=dark_bg, foreground=dark_fg)
        style.configure('TLabel', background=dark_bg, foreground=dark_fg)
        style.configure('TEntry', fieldbackground=dark_entry_bg, foreground=dark_fg)
        style.configure('TButton', background=dark_button_bg, foreground=dark_fg)
        style.configure('TCheckbutton', background=dark_bg, foreground=dark_fg)
        style.configure('TCombobox', fieldbackground=dark_entry_bg, foreground=dark_fg, arrowcolor=dark_fg)
        style.configure('TNotebook', background=dark_bg)
        style.configure('TNotebook.Tab', background=dark_button_bg, foreground=dark_fg)
        style.configure('TFrame', background=dark_bg)
        style.configure('TLabelFrame', background=dark_bg, foreground=dark_fg)
        style.configure('TLabelFrame.Label', background=dark_bg, foreground=dark_fg)
        style.configure('Horizontal.TProgressbar', troughcolor=dark_bg, background='green')
        self.config(bg=dark_bg)
        for widget in [self.extensions_text, self.include_text, self.exclude_text, self.config_text]:
            widget.config(bg=dark_entry_bg, fg=dark_fg)
    def save(self):
        name = self.profile_name_var.get().strip()
        if re.search(r'[/;]', name):
            messagebox.showerror("Invalid Name", "Profile name cannot contain / or ;")
            return
        self.result = {
            "name": name,
            "extensions": self.extensions_text.get("1.0", tk.END).strip(),
            "include": self.include_text.get("1.0", tk.END).strip(),
            "exclude": self.exclude_text.get("1.0", tk.END).strip(),
            "config": self.config_text.get("1.0", tk.END).strip()
        }
        self.destroy()
# --- Preset Dialog Class Section ---
class PresetDialog(tk.Toplevel):
    def __init__(self, parent, app, preset_name="", files_list=[]):
        super().__init__(parent)
        self.app = app
        self.title("New Preset" if not preset_name else "Edit Preset")
        self.geometry("400x400")
        self.resizable(False, False)
        self.transient(parent)
        self.preset_name_var = tk.StringVar(value=preset_name)
        ttk.Label(self, text="Preset Name:").grid(row=0, column=0, sticky="w", pady=2, padx=5)
        name_entry = ttk.Entry(self, textvariable=self.preset_name_var, width=40)
        name_entry.grid(row=0, column=1, sticky="ew", pady=2, padx=5)
        ttk.Label(self, text="Files (; separated):").grid(row=1, column=0, sticky="w", pady=2, padx=5)
        self.files_text = tk.Text(self, height=15, width=50)
        self.files_text.insert("1.0", "; ".join(files_list))
        self.files_text.grid(row=1, column=1, sticky="ew", pady=2, padx=5)
        button_frame = ttk.Frame(self)
        button_frame.grid(row=2, column=1, sticky="ew", pady=2)
        ttk.Button(button_frame, text="Add Files", command=self.add_files).pack(side=tk.LEFT, padx=5)
        save_frame = ttk.Frame(self)
        save_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(save_frame, text="Save", command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(save_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)
        self.columnconfigure(1, weight=1)
        if self.app.is_dark_mode():
            self.set_dark_theme()
    def set_dark_theme(self):
        style = ttk.Style()
        style.theme_use('clam')
        dark_bg = '#2e2e2e'
        dark_fg = '#ffffff'
        dark_entry_bg = '#3e3e3e'
        dark_button_bg = '#4e4e4e'
        style.configure('.', background=dark_bg, foreground=dark_fg)
        style.configure('TLabel', background=dark_bg, foreground=dark_fg)
        style.configure('TEntry', fieldbackground=dark_entry_bg, foreground=dark_fg)
        style.configure('TButton', background=dark_button_bg, foreground=dark_fg)
        style.configure('TCheckbutton', background=dark_bg, foreground=dark_fg)
        style.configure('TCombobox', fieldbackground=dark_entry_bg, foreground=dark_fg, arrowcolor=dark_fg)
        style.configure('TNotebook', background=dark_bg)
        style.configure('TNotebook.Tab', background=dark_button_bg, foreground=dark_fg)
        style.configure('TFrame', background=dark_bg)
        style.configure('TLabelFrame', background=dark_bg, foreground=dark_fg)
        style.configure('TLabelFrame.Label', background=dark_bg, foreground=dark_fg)
        style.configure('Horizontal.TProgressbar', troughcolor=dark_bg, background='green')
        self.config(bg=dark_bg)
        self.files_text.config(bg=dark_entry_bg, fg=dark_fg)
    def add_files(self):
        project_dir = self.app.get_project_dir()
        files = filedialog.askopenfilenames(initialdir=project_dir, title="Select Files")
        current_files = self.parse_files_text()
        for full_path in files:
            rel_path = os.path.relpath(full_path, project_dir).replace('\\', '/')
            if rel_path not in current_files:
                current_files.append(rel_path)
        self.files_text.delete("1.0", tk.END)
        self.files_text.insert("1.0", "; ".join(current_files))
        self.lift()
    def parse_files_text(self):
        content = self.files_text.get("1.0", tk.END).strip()
        return [item.strip() for item in content.split(';') if item.strip()]
    def save(self):
        name = self.preset_name_var.get().strip()
        if re.search(r'[/;]', name):
            messagebox.showerror("Invalid Name", "Preset name cannot contain / or ;")
            return
        self.result = {
            "name": name,
            "files": self.parse_files_text()
        }
        self.destroy()
# --- DumpApp Class Section ---
class DumpApp:
    # --- Initialization and Setup Section ---
    def __init__(self, root):
        self.root = root
        self.root.title("Project Dump Configuration")
        self.root.geometry(f"{default_form_width}x{default_form_height}+{default_form_x}+{default_form_y}")
        self.root.minsize(550, 500)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.profiles = custom_config.get("Profiles", default_profiles)
        self.presets = {}
        self.start_dir_var = tk.StringVar(value=default_start_dir)
        self.output_dir_var = tk.StringVar(value=default_start_dir)
        self.output_base_var = tk.StringVar(value=default_output_base)
        self.minify_var = tk.BooleanVar(value=default_minify)
        self.include_hashes_var = tk.BooleanVar(value=default_include_hashes)
        self.max_part_size_var = tk.StringVar(value=str(default_max_part_size))
        self.save_as_txt_var = tk.BooleanVar(value=(default_format == "txt"))
        self.split_large_var = tk.BooleanVar(value=default_split_large_files)
        self.single_limit_var = tk.StringVar(value=str(default_single_file_limit))
        self.profile_var = tk.StringVar(value=default_profile)
        self.preset_var = tk.StringVar(value="None")
        self.exclude_cmake_var = tk.BooleanVar(value=custom_config.get("LastExcludeCMake", True))
        self.exclude_vscode_var = tk.BooleanVar(value=custom_config.get("LastExcludeVSCode", True))
        self.is_exclude_dynamic_var = tk.BooleanVar(value=default_is_exclude_dynamic)
        self.input_type_var = tk.StringVar(value=default_input_type)
        self.use_placeholders_var = tk.BooleanVar(value=default_use_placeholders)
        self.include_tree_var = tk.BooleanVar(value=default_include_tree)
        self.parse_git_var = tk.BooleanVar(value=default_parse_git)
        self.timestamp_var = tk.BooleanVar(value=default_timestamp)
        self.max_output_parts_var = tk.StringVar(value=str(default_max_output_parts))
        self.use_default_backup_path_var = tk.BooleanVar(value=default_use_default_backup_path)
        self.full_backup_var = tk.BooleanVar(value=custom_config.get("LastFullBackup", False))
        self.include_binary_var = tk.BooleanVar(value=custom_config.get("LastIncludeBinary", False))
        self.auto_save_interval_var = tk.StringVar(value=str(custom_config.get("AutoSaveIntervalMinutes", 5)))
        self.backup_interval_var = tk.StringVar(value=str(custom_config.get("BackupIntervalHours", 1)))
        self.backup_interval = int(self.backup_interval_var.get()) * 3600
        self.remaining_time = self.backup_interval
        self.auto_save_timer = None
        self.backup_timer = None
        self.dirty = False
        self.last_progress = custom_config.get("LastProgressMessage", "")
        self.recent_paths = custom_config.get("RecentPaths", [])
        self.create_widgets()
        self.setup_traces()
        self.load_profile()
        if "DynamicPatterns" in custom_config:
            self.dynamic_text.delete("1.0", tk.END)
            self.dynamic_text.insert("1.0", "; ".join(custom_config["DynamicPatterns"]))
        self.is_exclude_dynamic_var.set(default_is_exclude_dynamic)
        self.mini_win = None
        self.icon = None
        self.load_merged_config()
        self.on_start_dir_change()
        self.start_auto_save()
        self.start_backup_timer()
        self.update_progress("", "black")
        if self.is_dark_mode():
            self.set_dark_theme()
        self.configure_error_tags()
        self.update_generate_bat_state()
    # --- Validation and Theme Section ---
    def validate_numeric(self, event):
        entry = event.widget
        text = entry.get().strip()
        if text and not text.isdigit():
            entry.config(fieldbackground="red")
        else:
            entry.config(fieldbackground="white")
    def configure_error_tags(self):
        for widget in [self.extensions_text, self.include_text, self.exclude_text, self.dynamic_text, self.project_exclude_text]:
            widget.tag_configure("error", background="red", foreground="white")
    def is_dark_mode(self):
        system = platform.system()
        if system == 'Darwin':
            return self.is_dark_mode_macos()
        elif system == 'Windows':
            return self.is_dark_mode_windows()
        elif system == 'Linux':
            return self.is_dark_mode_linux()
        return False
    def is_dark_mode_macos(self):
        try:
            cmd = 'defaults read -g AppleInterfaceStyle'
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            output, _ = p.communicate()
            return 'Dark' in output.decode('utf-8')
        except:
            return False
    def is_dark_mode_windows(self):
        if not winreg:
            return False
        try:
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            reg_keypath = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize'
            reg_key = winreg.OpenKey(registry, reg_keypath)
            for i in range(1024):
                try:
                    value_name, value, _ = winreg.EnumValue(reg_key, i)
                    if value_name == 'AppsUseLightTheme':
                        return value == 0
                except OSError:
                    break
        except:
            pass
        return False
    def is_dark_mode_linux(self):
        try:
            # GNOME
            get_args = ['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme']
            current_theme = subprocess.run(get_args, capture_output=True).stdout.decode("utf-8").strip().strip("'")
            if current_theme.endswith('-dark'):
                return True
        except:
            pass
        try:
            # KDE
            get_args = ['kreadconfig5', '--file', 'kdeglobals', '--group', 'General', '--key', 'ColorScheme']
            current_scheme = subprocess.run(get_args, capture_output=True).stdout.decode("utf-8").strip()
            if 'dark' in current_scheme.lower():
                return True
        except:
            pass
        # XFCE or others, assume light
        return False
    def set_dark_theme(self):
        style = ttk.Style()
        style.theme_use('clam')
        dark_bg = '#2e2e2e'
        dark_fg = '#ffffff'
        dark_entry_bg = '#3e3e3e'
        dark_button_bg = '#4e4e4e'
        style.configure('.', background=dark_bg, foreground=dark_fg)
        style.configure('TLabel', background=dark_bg, foreground=dark_fg)
        style.configure('TEntry', fieldbackground=dark_entry_bg, foreground=dark_fg)
        style.configure('TButton', background=dark_button_bg, foreground=dark_fg)
        style.configure('TCheckbutton', background=dark_bg, foreground=dark_fg)
        style.configure('TCombobox', fieldbackground=dark_entry_bg, foreground=dark_fg, arrowcolor=dark_fg)
        style.configure('TNotebook', background=dark_bg)
        style.configure('TNotebook.Tab', background=dark_button_bg, foreground=dark_fg)
        style.configure('TFrame', background=dark_bg)
        style.configure('TLabelFrame', background=dark_bg, foreground=dark_fg)
        style.configure('TLabelFrame.Label', background=dark_bg, foreground=dark_fg)
        style.configure('Horizontal.TProgressbar', troughcolor=dark_bg, background='green')
        self.root.config(bg=dark_bg)
        self.progress_text.config(bg=dark_entry_bg, fg=dark_fg)
        for widget in [self.extensions_text, self.include_text, self.exclude_text, self.dynamic_text, self.project_exclude_text, self.preset_files_text]:
            widget.config(bg=dark_entry_bg, fg=dark_fg)
        self.pattern_status.config(background=dark_bg)
    # --- Change Detection and Auto-Save Section ---
    def setup_traces(self):
        vars_to_trace = [
            self.start_dir_var, self.output_dir_var, self.output_base_var, self.minify_var, self.include_hashes_var,
            self.max_part_size_var, self.save_as_txt_var, self.split_large_var, self.single_limit_var, self.profile_var, self.preset_var,
            self.exclude_cmake_var, self.exclude_vscode_var, self.is_exclude_dynamic_var, self.input_type_var,
            self.use_placeholders_var, self.include_tree_var, self.parse_git_var, self.timestamp_var,
            self.max_output_parts_var, self.use_default_backup_path_var, self.full_backup_var, self.include_binary_var, self.auto_save_interval_var,
            self.backup_interval_var
        ]
        for var in vars_to_trace:
            var.trace("w", self.on_var_change)
        text_widgets = [self.extensions_text, self.include_text, self.exclude_text, self.dynamic_text, self.project_exclude_text]
        for widget in text_widgets:
            widget.bind("<KeyRelease>", self.on_text_change)
        self.start_dir_var.trace("w", self.on_start_dir_change)
        self.preset_var.trace("w", self.on_preset_change)
    def on_var_change(self, *args):
        self.dirty = True
    def on_text_change(self, event):
        self.dirty = True
    def on_start_dir_change(self, *args):
        self.load_merged_config()
        project_dir = self.get_project_dir()
        self.output_base_var.set(os.path.basename(project_dir))
    def start_auto_save(self):
        self.auto_save()
        interval_ms = int(self.auto_save_interval_var.get()) * 60000
        self.auto_save_timer = self.root.after(interval_ms, self.start_auto_save)
    def auto_save(self):
        if self.dirty:
            try:
                self.save_settings(quiet=True)
                self.dirty = False
                logging.info("Auto-save completed")
            except Exception as e:
                logging.error(f"Auto-save failed: {e}")
    # --- Backup Scheduling Section ---
    def start_backup_timer(self):
        self.update_backup_display()
        self.backup_timer = self.root.after(1000, self.start_backup_timer)
    def update_backup_display(self):
        if self.remaining_time > 0:
            self.remaining_time -= 1
            mins, secs = divmod(self.remaining_time, 60)
            hours, mins = divmod(mins, 60)
            time_str = f"{hours:02d}:{mins:02d}:{secs:02d}"
            self.backup_label.config(text=f"Next Backup: {time_str}")
        else:
            self.do_backup()
            self.remaining_time = self.backup_interval
    def do_backup(self):
        self.backup()
    # --- Closing and Recent Paths Section ---
    def on_closing(self):
        if self.auto_save_timer:
            self.root.after_cancel(self.auto_save_timer)
        if self.backup_timer:
            self.root.after_cancel(self.backup_timer)
        self.save_settings(quiet=True)
        self.root.destroy()
    def add_to_recent(self, path):
        if path not in self.recent_paths:
            self.recent_paths.insert(0, path)
            self.recent_paths = self.recent_paths[:5]
            self.recent_combo['values'] = self.recent_paths
            custom_config["RecentPaths"] = self.recent_paths
            save_config(custom_config)
    def on_recent_select(self, event):
        path = self.recent_combo.get()
        self.start_dir_var.set(path)
        self.output_dir_var.set(path if os.path.isdir(path) else os.path.dirname(path))
        self.load_merged_config()
    # --- GUI Creation Section ---
    def create_widgets(self):
        self.notebook = ttk.Notebook(self.root, padding="10")
        self.notebook.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        # Settings Tab (merged Basic and Advanced)
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="Settings")
        settings_frame.columnconfigure(1, weight=1)
        row = 0
        self.input_type_label = ttk.Label(settings_frame, text="Input Type:")
        self.input_type_label.grid(row=row, column=0, sticky="w", pady=2)
        self.type_combo = ttk.Combobox(settings_frame, textvariable=self.input_type_var, values=["Local", "GitHub"], state="readonly", width=17)
        self.type_combo.grid(row=row, column=1, sticky="w", pady=2)
        Tooltip(self.type_combo, "Local for directory/file, GitHub for repo URL")
        row += 1
        self.start_dir_label = ttk.Label(settings_frame, text="Start Directory/URL:")
        self.start_dir_label.grid(row=row, column=0, sticky="w", pady=2)
        self.start_dir_entry = ttk.Entry(settings_frame, textvariable=self.start_dir_var, width=50)
        self.start_dir_entry.grid(row=row, column=1, sticky="ew", pady=2)
        self.browse_start_button = ttk.Button(settings_frame, text="Browse", command=self.browse_start, width=7)
        self.browse_start_button.grid(row=row, column=2, padx=(5,0), pady=2)
        Tooltip(self.start_dir_entry, "Project directory or GitHub URL")
        row += 1
        ttk.Label(settings_frame, text="Recent Projects:").grid(row=row, column=0, sticky="w", pady=2)
        self.recent_combo = ttk.Combobox(settings_frame, values=self.recent_paths, state="readonly")
        self.recent_combo.grid(row=row, column=1, sticky="ew", pady=2)
        self.recent_combo.bind("<<ComboboxSelected>>", self.on_recent_select)
        row += 1
        self.output_dir_label = ttk.Label(settings_frame, text="Output Directory:")
        self.output_dir_label.grid(row=row, column=0, sticky="w", pady=2)
        self.output_dir_entry = ttk.Entry(settings_frame, textvariable=self.output_dir_var, width=30)
        self.output_dir_entry.grid(row=row, column=1, sticky="w", pady=2)
        self.browse_output_button = ttk.Button(settings_frame, text="...", command=self.browse_output, width=3)
        self.browse_output_button.grid(row=row, column=1, padx=(210,0), pady=2, sticky="e")
        Tooltip(self.output_dir_entry, "Directory for output files")
        row += 1
        self.output_base_label = ttk.Label(settings_frame, text="Output File Base:")
        self.output_base_label.grid(row=row, column=0, sticky="w", pady=2)
        self.output_base_entry = ttk.Entry(settings_frame, textvariable=self.output_base_var, width=30)
        self.output_base_entry.grid(row=row, column=1, sticky="w", pady=2)
        Tooltip(self.output_base_entry, "Base name for dump files")
        row += 1
        # Grouped checkboxes with LabelFrames
        features_lf = ttk.LabelFrame(settings_frame, text="Features")
        features_lf.grid(row=row, column=0, sticky="w", pady=2)
        self.minify_check = ttk.Checkbutton(features_lf, text="Minify JS/TS", variable=self.minify_var)
        self.minify_check.pack(side=tk.LEFT, padx=(0,10))
        Tooltip(self.minify_check, "Minify JS/TS files")
        self.hashes_check = ttk.Checkbutton(features_lf, text="Include File Hashes", variable=self.include_hashes_var)
        self.hashes_check.pack(side=tk.LEFT, padx=(0,10))
        Tooltip(self.hashes_check, "Add SHA256 hashes")
        self.full_backup_check = ttk.Checkbutton(features_lf, text="Full Backup", variable=self.full_backup_var)
        self.full_backup_check.pack(side=tk.LEFT, padx=(0,10))
        Tooltip(self.full_backup_check, "Backup all files without filtering")
        self.binary_check = ttk.Checkbutton(features_lf, text="Include Binary", variable=self.include_binary_var)
        self.binary_check.pack(side=tk.LEFT, padx=(0,10))
        Tooltip(self.binary_check, "Include binary files as base64")
        excludes_lf = ttk.LabelFrame(settings_frame, text="Excludes")
        excludes_lf.grid(row=row, column=1, sticky="w", pady=2)
        self.exc_cmake_check = ttk.Checkbutton(excludes_lf, text="Exc CMake", variable=self.exclude_cmake_var)
        self.exc_cmake_check.pack(side=tk.LEFT, padx=(0,10))
        Tooltip(self.exc_cmake_check, "Exclude CMake")
        self.exc_vscode_check = ttk.Checkbutton(excludes_lf, text="Exc VSCode", variable=self.exclude_vscode_var)
        self.exc_vscode_check.pack(side=tk.LEFT)
        Tooltip(self.exc_vscode_check, "Exclude VSCode")
        row += 1
        dump_options_lf = ttk.LabelFrame(settings_frame, text="Dump Options")
        dump_options_lf.grid(row=row, column=0, columnspan=2, sticky="w", pady=2)
        self.parse_git_check = ttk.Checkbutton(dump_options_lf, text="Parse .gitignore", variable=self.parse_git_var)
        self.parse_git_check.pack(side=tk.LEFT, padx=(0,10))
        Tooltip(self.parse_git_check, "Use .gitignore excludes")
        self.timestamp_check = ttk.Checkbutton(dump_options_lf, text="Add Timestamp", variable=self.timestamp_var)
        self.timestamp_check.pack(side=tk.LEFT, padx=(0,10))
        Tooltip(self.timestamp_check, "Timestamp output files")
        self.include_tree_check = ttk.Checkbutton(dump_options_lf, text="Include Project Tree", variable=self.include_tree_var)
        self.include_tree_check.pack(side=tk.LEFT, padx=(0,10))
        Tooltip(self.include_tree_check, "Add project tree")
        self.split_large_check = ttk.Checkbutton(dump_options_lf, text="Split Large Files", variable=self.split_large_var)
        self.split_large_check.pack(side=tk.LEFT, padx=(0,10))
        Tooltip(self.split_large_check, "Split large files")
        self.use_placeholders_check = ttk.Checkbutton(dump_options_lf, text="Use Placeholders for Large Files", variable=self.use_placeholders_var)
        self.use_placeholders_check.pack(side=tk.LEFT, padx=(0,10))
        Tooltip(self.use_placeholders_check, "Placeholders for large files")
        self.use_default_backup_path_check = ttk.Checkbutton(dump_options_lf, text="Use Default Backup Path", variable=self.use_default_backup_path_var)
        self.use_default_backup_path_check.pack(side=tk.LEFT, padx=(0,10))
        Tooltip(self.use_default_backup_path_check, "Use ~/Dev_backup")
        row += 1
        self.max_part_size_label = ttk.Label(settings_frame, text="Max Part Size:")
        self.max_part_size_label.grid(row=row, column=0, sticky="w", pady=2)
        self.max_part_size_entry = ttk.Entry(settings_frame, textvariable=self.max_part_size_var, width=10)
        self.max_part_size_entry.grid(row=row, column=1, sticky="w", pady=2)
        self.max_part_size_entry.bind("<KeyRelease>", self.validate_numeric)
        Tooltip(self.max_part_size_entry, "Max characters per part")
        row += 1
        self.single_limit_label = ttk.Label(settings_frame, text="Single File Limit:")
        self.single_limit_label.grid(row=row, column=0, sticky="w", pady=2)
        self.single_limit_entry = ttk.Entry(settings_frame, textvariable=self.single_limit_var, width=10)
        self.single_limit_entry.grid(row=row, column=1, sticky="w", pady=2)
        self.single_limit_entry.bind("<KeyRelease>", self.validate_numeric)
        Tooltip(self.single_limit_entry, "Limit for single file")
        row += 1
        self.save_as_txt_label = ttk.Label(settings_frame, text="Save as TXT:")
        self.save_as_txt_label.grid(row=row, column=0, sticky="w", pady=2)
        self.save_as_txt_check = ttk.Checkbutton(settings_frame, variable=self.save_as_txt_var)
        self.save_as_txt_check.grid(row=row, column=1, sticky="w", pady=2)
        Tooltip(self.save_as_txt_check, "Save output as .txt (checked) or .md (unchecked)")
        row += 1
        self.max_output_parts_label = ttk.Label(settings_frame, text="Max Output Parts (0 for no limit):")
        self.max_output_parts_label.grid(row=row, column=0, sticky="w", pady=2)
        self.max_output_parts_entry = ttk.Entry(settings_frame, textvariable=self.max_output_parts_var, width=10)
        self.max_output_parts_entry.grid(row=row, column=1, sticky="w", pady=2)
        self.max_output_parts_entry.bind("<KeyRelease>", self.validate_numeric)
        Tooltip(self.max_output_parts_entry, "Max parts, 0 unlimited")
        row += 1
        # Scheduling
        scheduling_lf = ttk.LabelFrame(settings_frame, text="Scheduling")
        scheduling_lf.grid(row=row, column=0, columnspan=2, sticky="w", pady=2)
        ttk.Label(scheduling_lf, text="Auto Save Interval (minutes):").pack(side=tk.LEFT, padx=(0,10))
        self.auto_save_interval_entry = ttk.Entry(scheduling_lf, textvariable=self.auto_save_interval_var, width=10)
        self.auto_save_interval_entry.pack(side=tk.LEFT, padx=(0,10))
        self.auto_save_interval_entry.bind("<KeyRelease>", self.validate_numeric)
        Tooltip(self.auto_save_interval_entry, "Auto save interval in minutes")
        ttk.Label(scheduling_lf, text="Backup Interval (hours):").pack(side=tk.LEFT, padx=(0,10))
        self.backup_interval_entry = ttk.Entry(scheduling_lf, textvariable=self.backup_interval_var, width=10)
        self.backup_interval_entry.pack(side=tk.LEFT, padx=(0,10))
        self.backup_interval_entry.bind("<KeyRelease>", self.validate_numeric)
        Tooltip(self.backup_interval_entry, "Backup interval in hours")
        self.backup_label = ttk.Label(scheduling_lf, text="Next Backup: 00:00:00")
        self.backup_label.pack(side=tk.LEFT, padx=(0,10))
        row += 1
        # Patterns Tab (merged with Profiles)
        patterns_frame = ttk.Frame(self.notebook)
        self.notebook.add(patterns_frame, text="Patterns & Profiles")
        patterns_frame.columnconfigure(1, weight=1)
        row = 0
        self.profile_label = ttk.Label(patterns_frame, text="Profile:")
        self.profile_label.grid(row=row, column=0, sticky="w", pady=2)
        self.profile_combo = ttk.Combobox(patterns_frame, textvariable=self.profile_var, values=list(self.profiles.keys()), state="readonly", width=47)
        self.profile_combo.grid(row=row, column=1, columnspan=2, sticky="ew", pady=2)
        self.profile_combo.bind("<<ComboboxSelected>>", self.on_profile_change)
        Tooltip(self.profile_combo, "Select profile")
        row += 1
        self.profile_mgmt_frame = ttk.Frame(patterns_frame)
        self.profile_mgmt_frame.grid(row=row, column=0, columnspan=3, pady=2)
        ttk.Button(self.profile_mgmt_frame, text="New Profile", command=self.new_profile).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.profile_mgmt_frame, text="Save Profile", command=self.save_profile).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.profile_mgmt_frame, text="Delete Profile", command=self.delete_profile).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.profile_mgmt_frame, text="Import Profiles", command=self.import_profiles).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.profile_mgmt_frame, text="Export Profiles", command=self.export_profiles).pack(side=tk.LEFT, padx=5)
        row += 1
        self.extensions_label = ttk.Label(patterns_frame, text="Extensions (; separated):")
        self.extensions_label.grid(row=row, column=0, sticky="w", pady=2)
        self.extensions_text = tk.Text(patterns_frame, height=2, width=50, wrap=tk.WORD, undo=True)
        self.extensions_text.grid(row=row, column=1, columnspan=2, sticky="ew", pady=2)
        self.extensions_text.bind("<KeyRelease>", self.validate_patterns)
        Tooltip(self.extensions_text, "Extensions to include")
        row += 1
        self.include_label = ttk.Label(patterns_frame, text="Include Patterns (; separated):")
        self.include_label.grid(row=row, column=0, sticky="w", pady=2)
        self.include_text = tk.Text(patterns_frame, height=2, width=50, wrap=tk.WORD, undo=True)
        self.include_text.grid(row=row, column=1, columnspan=2, sticky="ew", pady=2)
        self.include_text.bind("<KeyRelease>", self.validate_patterns)
        Tooltip(self.include_text, "Include patterns")
        row += 1
        self.exclude_label = ttk.Label(patterns_frame, text="Exclude Patterns (; separated):")
        self.exclude_label.grid(row=row, column=0, sticky="w", pady=2)
        self.exclude_text = tk.Text(patterns_frame, height=3, width=50, wrap=tk.WORD, undo=True)
        self.exclude_text.grid(row=row, column=1, columnspan=2, sticky="ew", pady=2)
        self.exclude_text.bind("<KeyRelease>", self.validate_patterns)
        Tooltip(self.exclude_text, "Exclude patterns")
        row += 1
        self.dynamic_frame = ttk.Frame(patterns_frame)
        self.dynamic_frame.grid(row=row, column=0, columnspan=3, sticky="w", pady=2)
        ttk.Label(self.dynamic_frame, text="Dynamic Patterns (; separated):").pack(side=tk.LEFT, padx=(0,10))
        ttk.Checkbutton(self.dynamic_frame, text="Treat as Exclude", variable=self.is_exclude_dynamic_var).pack(side=tk.LEFT)
        row += 1
        self.dynamic_text = tk.Text(patterns_frame, height=3, width=50, wrap=tk.WORD, undo=True)
        self.dynamic_text.grid(row=row, column=1, columnspan=2, sticky="ew", pady=2)
        self.dynamic_text.bind("<KeyRelease>", self.validate_patterns)
        Tooltip(self.dynamic_text, "Dynamic patterns")
        row += 1
        self.project_exclude_label = ttk.Label(patterns_frame, text="Project Excludes (; separated):")
        self.project_exclude_label.grid(row=row, column=0, sticky="w", pady=2)
        self.project_exclude_text = tk.Text(patterns_frame, height=2, width=50, wrap=tk.WORD, undo=True)
        self.project_exclude_text.grid(row=row, column=1, columnspan=2, sticky="ew", pady=2)
        self.project_exclude_text.bind("<KeyRelease>", self.validate_patterns)
        Tooltip(self.project_exclude_text, "Project-specific excludes")
        row += 1
        self.presets_mgmt_frame = ttk.Frame(patterns_frame)
        self.presets_mgmt_frame.grid(row=row, column=0, columnspan=3, pady=2)
        ttk.Label(self.presets_mgmt_frame, text="Preset:").pack(side=tk.LEFT, padx=5)
        self.preset_combo = ttk.Combobox(self.presets_mgmt_frame, textvariable=self.preset_var, state="readonly", width=20)
        self.preset_combo.pack(side=tk.LEFT, padx=5)
        self.preset_combo.bind("<<ComboboxSelected>>", self.on_preset_change)
        ttk.Button(self.presets_mgmt_frame, text="New Preset", command=self.new_preset).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.presets_mgmt_frame, text="Edit Preset", command=self.edit_preset).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.presets_mgmt_frame, text="Delete Preset", command=self.delete_preset).pack(side=tk.LEFT, padx=5)
        self.generate_bat_button = ttk.Button(self.presets_mgmt_frame, text="Generate BATs", command=self.generate_bats)
        self.generate_bat_button.pack(side=tk.LEFT, padx=5)
        row += 1
        self.preset_files_text = tk.Text(patterns_frame, height=5, width=50, undo=True)
        self.preset_files_text.grid(row=row, column=1, columnspan=2, sticky="ew", pady=2)
        self.preset_files_text.config(state=tk.DISABLED)
        Tooltip(self.preset_files_text, "Files in selected preset")
        row += 1
        self.pattern_status = ttk.Label(patterns_frame, text="Patterns OK", foreground="green")
        self.pattern_status.grid(row=row, column=0, columnspan=3, sticky="w", pady=2)
        row += 1
        # Bottom components
        self.progress_bar = ttk.Progressbar(self.root, mode='indeterminate', length=300)
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=5)
        self.progress_text = tk.Text(self.root, height=3, width=70, state=tk.DISABLED, wrap=tk.WORD, bg="lightgray")
        self.progress_text.grid(row=2, column=0, sticky="ew", pady=5)
        button_frame = ttk.Frame(self.root)
        button_frame.grid(row=3, column=0, pady=10)
        self.test_filter_button = ttk.Button(button_frame, text="Test Filter", command=self.test_filter)
        self.test_filter_button.pack(side=tk.LEFT, padx=5)
        self.run_dump_button = ttk.Button(button_frame, text="Run Dump", command=self.do_run_dump)
        self.run_dump_button.pack(side=tk.LEFT, padx=5)
        self.save_settings_button = ttk.Button(button_frame, text="Save Settings", command=self.save_settings)
        self.save_settings_button.pack(side=tk.LEFT, padx=5)
        self.save_project_button = ttk.Button(button_frame, text="Save Project Config", command=self.save_project_config)
        self.save_project_button.pack(side=tk.LEFT, padx=5)
        self.backup_button = ttk.Button(button_frame, text="Backup", command=self.backup)
        self.backup_button.pack(side=tk.LEFT, padx=5)
        self.restore_button = ttk.Button(button_frame, text="Restore", command=self.restore)
        self.restore_button.pack(side=tk.LEFT, padx=5)
        self.dry_restore_button = ttk.Button(button_frame, text="Dry Restore", command=self.dry_restore)
        self.dry_restore_button.pack(side=tk.LEFT, padx=5)
        self.mini_mode_button = ttk.Button(button_frame, text="Mini Mode", command=self.toggle_mini_mode)
        self.mini_mode_button.pack(side=tk.LEFT, padx=5)
        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self.root.quit)
        self.cancel_button.pack(side=tk.LEFT, padx=5)
        self.tray_mode_button = ttk.Button(button_frame, text="Tray Mode", command=self.toggle_tray_mode)
        self.tray_mode_button.pack(side=tk.LEFT, padx=5)
    # --- Mode Toggling Section ---
    def toggle_mini_mode(self):
        if self.mini_win:
            # Save mini window geometry
            custom_config["MiniFormWidth"] = self.mini_win.winfo_width()
            custom_config["MiniFormHeight"] = self.mini_win.winfo_height()
            custom_config["MiniFormX"] = self.mini_win.winfo_x()
            custom_config["MiniFormY"] = self.mini_win.winfo_y()
            save_config(custom_config)
            self.mini_win.destroy()
            self.mini_win = None
            self.root.deiconify()
            self.mini_mode_button.config(text="Mini Mode")
        else:
            self.root.withdraw()
            self.mini_win = MiniWindow(self.root, self)
            self.mini_mode_button.config(text="Full Mode")
    def toggle_tray_mode(self):
        if self.icon:
            self.icon.stop()
            self.icon = None
            self.root.deiconify()
            self.tray_mode_button.config(text="Tray Mode")
        else:
            pystray = None
            Image = None
            try:
                import pystray # type: ignore
                from PIL import Image # type: ignore
            except ImportError:
                if messagebox.askyesno("Install Required Packages", "pystray and Pillow are required for tray mode. Do you want to install them?"):
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", "pystray", "pillow"])
                        import pystray # type: ignore
                        from PIL import Image # type: ignore
                    except Exception as e:
                        messagebox.showerror("Installation Failed", f"Failed to install pystray and Pillow: {e}")
                        return
                else:
                    return
            self.root.withdraw()
            self.icon_thread = threading.Thread(target=self.run_tray_icon)
            self.icon_thread.daemon = True
            self.icon_thread.start()
            self.tray_mode_button.config(text="Exit Tray")
    def run_tray_icon(self):
        import pystray # type: ignore
        from PIL import Image # type: ignore
        menu = pystray.Menu(
            pystray.MenuItem("Backup", self.backup),
            pystray.MenuItem("Restore", self.restore),
            pystray.MenuItem("Show GUI", self.show_gui_from_tray),
            pystray.MenuItem("Exit", self.exit_tray)
        )
        icon_image = Image.new('RGB', (64, 64), color = (73, 109, 137))
        self.icon = pystray.Icon('project_dump', icon_image, "Project Dump", menu)
        self.icon.run()
    def show_gui_from_tray(self):
        self.icon.stop()
        self.icon = None
        self.root.deiconify()
        self.tray_mode_button.config(text="Tray Mode")
    def exit_tray(self):
        self.icon.stop()
        self.root.quit()
    # --- Helper Methods Section ---
    def get_project_dir(self):
        start_dir = self.start_dir_var.get()
        return os.path.dirname(start_dir) if os.path.isfile(start_dir) else start_dir
    def get_dump_config(self, project_dir):
        extensions = self.parse_extensions()
        include_patterns = self.parse_list(self.include_text)
        exclude = self.parse_list(self.exclude_text)
        exclude = apply_additional_excludes(exclude, self.exclude_cmake_var.get(), self.exclude_vscode_var.get())
        include_patterns, exclude = apply_dynamic_patterns(include_patterns, exclude, self.parse_list(self.dynamic_text), self.is_exclude_dynamic_var.get())
        project_excludes, _ = load_project_config(project_dir)
        exclude.extend([p for p in project_excludes if p not in exclude])
        if self.parse_git_var.get():
            git_path = os.path.join(project_dir, '.gitignore')
            if os.path.exists(git_path):
                git_excludes = parse_gitignore(git_path)
                exclude.extend([p for p in git_excludes if p not in exclude])
        return {"Extensions": extensions, "IncludePatterns": include_patterns, "Exclude": exclude}
    def collect_files(self, dump_config, project_dir):
        all_files = []
        if self.full_backup_var.get():
            for root, dirs, files in os.walk(project_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    all_files.append(file_path)
        else:
            for root, dirs, files in os.walk(project_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if should_include_file(file_path, dump_config, project_dir):
                        all_files.append(file_path)
        return all_files
    # --- Backup and Restore Actions Section ---
    def backup(self):
        if self.input_type_var.get() == "GitHub":
            self.update_progress("Backup not supported for GitHub input.", "red")
            return
        try:
            project_dir = self.get_project_dir()
            dump_config = self.get_dump_config(project_dir)
            message, color = do_backup(project_dir, dump_config, self.full_backup_var.get(), self.use_default_backup_path_var.get(), self.parse_git_var.get())
            self.update_progress(message, color)
        except Exception as e:
            self.update_progress(f"Backup error: {e}", "red")
    def get_backup_dir(self, project_dir):
        if self.use_default_backup_path_var.get():
            return Path.home() / "Dev_backup"
        else:
            return Path(project_dir) / ".backup"
    def restore(self):
        if self.input_type_var.get() == "GitHub":
            self.update_progress("Restore not supported for GitHub input.", "red")
            return
        try:
            project_dir = self.get_project_dir()
            backup_dir = self.get_backup_dir(project_dir)
            if not backup_dir.exists():
                self.update_progress("No backup directory found.", "red")
                return
            backups = list(backup_dir.glob("*.7z")) + list(backup_dir.glob("*.zip"))
            if not backups:
                self.update_progress("No backups found.", "red")
                return
            backup_file = filedialog.askopenfilename(initialdir=backup_dir, title="Select Backup", filetypes=[("7Z/ZIP Files", "*.7z *.zip")])
            if not backup_file:
                self.update_progress("Restore cancelled.", "black")
                return
            if messagebox.askyesno("Confirm Restore", f"Extract backup to {project_dir}?\nThis may overwrite existing files."):
                if backup_file.endswith(".7z"):
                    if py7zr is None:
                        raise ImportError("py7zr not installed for .7z restore")
                    with py7zr.SevenZipFile(backup_file, 'r') as z:
                        z.extractall(project_dir)
                else:
                    with zipfile.ZipFile(backup_file, 'r') as zipf:
                        zipf.extractall(project_dir)
                self.update_progress(f"Restored from {backup_file} to {project_dir}", "green")
            else:
                self.update_progress("Restore cancelled.", "black")
        except Exception as e:
            self.update_progress(f"Restore error: {e}", "red")
    def dry_restore(self):
        try:
            project_dir = self.get_project_dir()
            backup_dir = self.get_backup_dir(project_dir)
            if not backup_dir.exists():
                self.update_progress("No backup directory found.", "red")
                return
            backups = list(backup_dir.glob("*.7z")) + list(backup_dir.glob("*.zip"))
            if not backups:
                self.update_progress("No backups found.", "red")
                return
            backup_file = filedialog.askopenfilename(initialdir=backup_dir, title="Select Backup for Dry Run", filetypes=[("7Z/ZIP Files", "*.7z *.zip")])
            if not backup_file:
                return
            if backup_file.endswith(".7z"):
                if py7zr is None:
                    raise ImportError("py7zr not installed for .7z dry restore")
                with py7zr.SevenZipFile(backup_file, 'r') as z:
                    files = z.getnames()
            else:
                with zipfile.ZipFile(backup_file, 'r') as zipf:
                    files = zipf.namelist()
            overwritten = [f for f in files if os.path.exists(os.path.join(project_dir, f))]
            msg = f"Would overwrite {len(overwritten)} files:\n" + "\n".join(overwritten[:10]) + ("\n..." if len(overwritten) > 10 else "")
            messagebox.showinfo("Dry Run Restore", msg)
        except Exception as e:
            self.update_progress(f"Dry restore error: {e}", "red")
    # --- Project Config Management Section ---
    def save_project_config(self):
        project_excludes = self.parse_list(self.project_exclude_text)
        start_dir = self.start_dir_var.get()
        project_dir = os.path.dirname(start_dir) if os.path.isfile(start_dir) else start_dir
        project_config_path = Path(project_dir) / ".dump-project.json"
        if os.path.exists(project_config_path):
            if not messagebox.askyesno("Overwrite", "Overwrite existing project config?"):
                return
        project_config = {
            "Exclude": project_excludes,
            "UseDefaultBackupPath": self.use_default_backup_path_var.get(),
            "FullBackup": self.full_backup_var.get(),
            "IncludeBinary": self.include_binary_var.get(),
            "Profile": self.profile_var.get(),
            "Minify": self.minify_var.get(),
            "IncludeHashes": self.include_hashes_var.get(),
            "MaxPartSize": int(self.max_part_size_var.get()),
            "Format": "txt" if self.save_as_txt_var.get() else "md",
            "SplitLargeFiles": self.split_large_var.get(),
            "SingleFileLimit": int(self.single_limit_var.get()),
            "ExcludeCMake": self.exclude_cmake_var.get(),
            "ExcludeVSCode": self.exclude_vscode_var.get(),
            "DynamicPatterns": self.parse_list(self.dynamic_text),
            "IsExcludeDynamic": self.is_exclude_dynamic_var.get(),
            "UsePlaceholders": self.use_placeholders_var.get(),
            "IncludeTree": self.include_tree_var.get(),
            "ParseGit": self.parse_git_var.get(),
            "Timestamp": self.timestamp_var.get(),
            "MaxOutputParts": int(self.max_output_parts_var.get()),
            "Extensions": self.parse_extensions(),
            "IncludePatterns": self.parse_list(self.include_text),
            "ExcludePatterns": self.parse_list(self.exclude_text),
            "Presets": self.presets
        }
        with open(project_config_path, "w", encoding="utf-8") as f:
            json.dump(project_config, f, indent=4)
        self.update_progress("Project config saved.", "green")
    def load_merged_config(self):
        start_dir = self.start_dir_var.get()
        project_dir = os.path.dirname(start_dir) if os.path.isfile(start_dir) else start_dir
        merged = load_all_project_configs(project_dir)
        if merged:
            try:
                if "Profile" in merged:
                    self.profile_var.set(merged["Profile"])
                    self.load_profile()
                if "Minify" in merged:
                    self.minify_var.set(merged["Minify"])
                if "IncludeHashes" in merged:
                    self.include_hashes_var.set(merged["IncludeHashes"])
                if "MaxPartSize" in merged:
                    self.max_part_size_var.set(str(merged["MaxPartSize"]))
                if "Format" in merged:
                    self.save_as_txt_var.set(merged["Format"] == "txt")
                if "SplitLargeFiles" in merged:
                    self.split_large_var.set(merged["SplitLargeFiles"])
                if "SingleFileLimit" in merged:
                    self.single_limit_var.set(str(merged["SingleFileLimit"]))
                if "ExcludeCMake" in merged:
                    self.exclude_cmake_var.set(merged["ExcludeCMake"])
                if "ExcludeVSCode" in merged:
                    self.exclude_vscode_var.set(merged["ExcludeVSCode"])
                if "DynamicPatterns" in merged:
                    self.dynamic_text.delete("1.0", tk.END)
                    self.dynamic_text.insert("1.0", "; ".join(merged["DynamicPatterns"]))
                if "IsExcludeDynamic" in merged:
                    self.is_exclude_dynamic_var.set(merged["IsExcludeDynamic"])
                if "UsePlaceholders" in merged:
                    self.use_placeholders_var.set(merged["UsePlaceholders"])
                if "IncludeTree" in merged:
                    self.include_tree_var.set(merged["IncludeTree"])
                if "ParseGit" in merged:
                    self.parse_git_var.set(merged["ParseGit"])
                if "Timestamp" in merged:
                    self.timestamp_var.set(merged["Timestamp"])
                if "MaxOutputParts" in merged:
                    self.max_output_parts_var.set(str(merged["MaxOutputParts"]))
                if "Extensions" in merged:
                    ext_content = "; ".join(ext.lstrip('.') for ext in merged["Extensions"])
                    self.extensions_text.delete("1.0", tk.END)
                    self.extensions_text.insert("1.0", ext_content)
                if "IncludePatterns" in merged:
                    inc_content = "; ".join(merged["IncludePatterns"])
                    self.include_text.delete("1.0", tk.END)
                    self.include_text.insert("1.0", inc_content)
                if "ExcludePatterns" in merged:
                    exc_content = "; ".join(merged["ExcludePatterns"])
                    self.exclude_text.delete("1.0", tk.END)
                    self.exclude_text.insert("1.0", exc_content)
                if "Exclude" in merged:
                    self.project_exclude_text.delete("1.0", tk.END)
                    self.project_exclude_text.insert("1.0", "; ".join(merged["Exclude"]))
                if "UseDefaultBackupPath" in merged:
                    self.use_default_backup_path_var.set(merged["UseDefaultBackupPath"])
                if "FullBackup" in merged:
                    self.full_backup_var.set(merged["FullBackup"])
                if "IncludeBinary" in merged:
                    self.include_binary_var.set(merged["IncludeBinary"])
                if "Presets" in merged:
                    self.presets = merged["Presets"]
                    self.preset_combo['values'] = ["None"] + list(self.presets.keys())
                    self.preset_var.set("None")
                    self.on_preset_change()
            except Exception as e:
                logging.error(f"Failed to load merged project config: {e}")
                self.load_global_config_fallback()
        else:
            self.load_global_config_fallback()
        self.update_generate_bat_state()
    def load_global_config_fallback(self):
        self.minify_var.set(default_minify)
        self.include_hashes_var.set(default_include_hashes)
        self.max_part_size_var.set(str(default_max_part_size))
        self.save_as_txt_var.set(default_format == "txt")
        self.split_large_var.set(default_split_large_files)
        self.single_limit_var.set(str(default_single_file_limit))
        self.exclude_cmake_var.set(True)
        self.exclude_vscode_var.set(True)
        self.is_exclude_dynamic_var.set(default_is_exclude_dynamic)
        self.use_placeholders_var.set(default_use_placeholders)
        self.include_tree_var.set(default_include_tree)
        self.parse_git_var.set(default_parse_git)
        self.timestamp_var.set(default_timestamp)
        self.max_output_parts_var.set(str(default_max_output_parts))
        self.dynamic_text.delete("1.0", tk.END)
        self.dynamic_text.insert("1.0", "")
        self.extensions_text.delete("1.0", tk.END)
        self.include_text.delete("1.0", tk.END)
        self.exclude_text.delete("1.0", tk.END)
        self.project_exclude_text.delete("1.0", tk.END)
        self.use_default_backup_path_var.set(default_use_default_backup_path)
        self.full_backup_var.set(False)
        self.include_binary_var.set(False)
        self.presets = {}
        self.preset_combo['values'] = ["None"]
        self.preset_var.set("None")
        self.on_preset_change()
        self.load_profile()
    # --- Profile Management Section ---
    def new_profile(self):
        dialog = ProfileDialog(self.root, self)
        self.root.wait_window(dialog)
        if hasattr(dialog, 'result') and dialog.result['name']:
            name = dialog.result['name']
            if name in self.profiles:
                messagebox.showerror("Error", "Profile name already exists.")
                return
            self.profiles[name] = {
                "Extensions": parse_extensions(dialog.result['extensions']),
                "IncludePatterns": parse_list(dialog.result['include']),
                "Exclude": parse_list(dialog.result['exclude']),
                "ConfigFiles": parse_list(dialog.result['config'])
            }
            custom_config["Profiles"] = self.profiles
            self.profile_combo['values'] = list(self.profiles.keys())
            self.profile_var.set(name)
            self.load_profile()
            save_config(custom_config)
    def save_profile(self):
        name = self.profile_var.get()
        if name not in self.profiles:
            return
        if name in default_profiles.keys():
            messagebox.showerror("Error", "Cannot edit default profiles.")
            return
        self.profiles[name] = {
            "Extensions": self.parse_extensions(),
            "IncludePatterns": self.parse_list(self.include_text),
            "Exclude": self.parse_list(self.exclude_text),
            "ConfigFiles": self.parse_list(self.dynamic_text)
        }
        custom_config["Profiles"] = self.profiles
        save_config(custom_config)
        messagebox.showinfo("Saved", f"Profile {name} updated.")
    def delete_profile(self):
        name = self.profile_var.get()
        if name not in self.profiles or name in default_profiles:
            messagebox.showerror("Error", "Cannot delete default or non-existent profile.")
            return
        if messagebox.askyesno("Confirm", f"Delete profile {name}?"):
            del self.profiles[name]
            custom_config["Profiles"] = self.profiles
            self.profile_combo['values'] = list(self.profiles.keys())
            self.profile_var.set("Custom")
            self.load_profile()
            save_config(custom_config)
    def load_profile(self):
        profile = self.profile_var.get()
        if profile in self.profiles:
            prof = self.profiles[profile]
            ext_content = "; ".join(ext.lstrip('.') for ext in prof["Extensions"])
            self.extensions_text.delete("1.0", tk.END)
            self.extensions_text.insert("1.0", ext_content)
            inc_content = "; ".join(prof["IncludePatterns"])
            self.include_text.delete("1.0", tk.END)
            self.include_text.insert("1.0", inc_content)
            exc_content = "; ".join(prof["Exclude"])
            self.exclude_text.delete("1.0", tk.END)
            self.exclude_text.insert("1.0", exc_content)
            # For dynamic, add profile's ConfigFiles
            dynamic_content = "; ".join(prof["ConfigFiles"])
            self.dynamic_text.delete("1.0", tk.END)
            self.dynamic_text.insert("1.0", dynamic_content)
        self.validate_patterns()
    def on_profile_change(self, *args):
        self.load_profile()
    def import_profiles(self):
        file_path = filedialog.askopenfilename(title="Import Profiles", filetypes=[("JSON Files", "*.json")])
        if file_path:
            try:
                with open(file_path, "r") as f:
                    imported_profiles = json.load(f)
                self.profiles.update(imported_profiles)
                custom_config["Profiles"] = self.profiles
                save_config(custom_config)
                self.profile_combo['values'] = list(self.profiles.keys())
                messagebox.showinfo("Import Successful", "Profiles imported successfully.")
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import profiles: {e}")
    def export_profiles(self):
        file_path = filedialog.asksaveasfilename(title="Export Profiles", defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if file_path:
            try:
                with open(file_path, "w") as f:
                    json.dump(self.profiles, f, indent=4)
                messagebox.showinfo("Export Successful", "Profiles exported successfully.")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export profiles: {e}")
    # --- Preset Management Section ---
    def new_preset(self):
        dialog = PresetDialog(self.root, self)
        self.root.wait_window(dialog)
        if hasattr(dialog, 'result') and dialog.result['name']:
            name = dialog.result['name']
            if name in self.presets:
                messagebox.showerror("Error", "Preset name already exists.")
                return
            self.presets[name] = dialog.result['files']
            self.preset_combo['values'] = ["None"] + list(self.presets.keys())
            self.preset_var.set(name)
            self.on_preset_change()
            self.save_project_config()
            self.update_generate_bat_state()
    def edit_preset(self):
        name = self.preset_var.get()
        if name == "None":
            messagebox.showerror("Error", "Select a preset to edit.")
            return
        dialog = PresetDialog(self.root, self, name, self.presets[name])
        self.root.wait_window(dialog)
        if hasattr(dialog, 'result'):
            self.presets[name] = dialog.result['files']
            self.on_preset_change()
            self.save_project_config()
            self.update_generate_bat_state()
    def delete_preset(self):
        name = self.preset_var.get()
        if name == "None":
            messagebox.showerror("Error", "Select a preset to delete.")
            return
        if messagebox.askyesno("Confirm", f"Delete preset {name}?"):
            del self.presets[name]
            self.preset_combo['values'] = ["None"] + list(self.presets.keys())
            self.preset_var.set("None")
            self.on_preset_change()
            self.save_project_config()
            self.update_generate_bat_state()
    def on_preset_change(self, *args):
        preset = self.preset_var.get()
        self.preset_files_text.config(state=tk.NORMAL)
        self.preset_files_text.delete("1.0", tk.END)
        if preset != "None":
            files = self.presets.get(preset, [])
            self.preset_files_text.insert("1.0", "; ".join(files))
        self.preset_files_text.config(state=tk.DISABLED)
        self.update_generate_bat_state()
    def update_generate_bat_state(self):
        if len(self.presets) > 0:
            self.generate_bat_button.config(state=tk.NORMAL)
        else:
            self.generate_bat_button.config(state=tk.DISABLED)
    def generate_bats(self):
        project_dir = self.get_project_dir()
        if getattr(sys, 'frozen', False):
            app_path = sys.executable
        else:
            app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dump_project.py")
            app_path = f'python "{app_path}"'
        project_name = os.path.basename(project_dir)
        # Generate for presets
        for preset in self.presets.keys():
            bat_path = os.path.join(project_dir, f"dump_{preset}.bat")
            if os.path.exists(bat_path):
                if not messagebox.askyesno("Overwrite", f"Overwrite {bat_path}?"):
                    continue
            args_str = self.get_args_str()
            content = f"""@echo off
setlocal
set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
{app_path} "%PROJECT_DIR%" --preset "{preset}" --output "%PROJECT_DIR%" --output-base "{project_name}-{preset}"{args_str}
endlocal
"""
            try:
                with open(bat_path, "w") as f:
                    f.write(content)
                self.update_progress(f"BAT generated at {bat_path}", "green")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to generate BAT for {preset}: {e}")
        # Generate for whole project
        bat_path = os.path.join(project_dir, "dump_project.bat")
        if os.path.exists(bat_path):
            if not messagebox.askyesno("Overwrite", f"Overwrite {bat_path}?"):
                return
        args_str = self.get_args_str()
        content = f"""@echo off
setlocal
set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
{app_path} "%PROJECT_DIR%" --output "%PROJECT_DIR%" --output-base "{project_name}"{args_str}
endlocal
"""
        try:
            with open(bat_path, "w") as f:
                f.write(content)
            self.update_progress(f"BAT generated at {bat_path}", "green")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate BAT for whole project: {e}")
        # Generate for backup
        bat_path = os.path.join(project_dir, "backup_project.bat")
        if os.path.exists(bat_path):
            if not messagebox.askyesno("Overwrite", f"Overwrite {bat_path}?"):
                return
        args_str = self.get_args_str()
        content = f"""@echo off
setlocal
set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
{app_path} "%PROJECT_DIR%" --backup --full-backup --input-type Local
endlocal
"""
        try:
            with open(bat_path, "w") as f:
                f.write(content)
            self.update_progress(f"BAT generated at {bat_path}", "green")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate BAT for backup: {e}")
    def get_args_str(self):
        args_str = ""
        if self.minify_var.get():
            args_str += " --minify"
        if self.include_hashes_var.get():
            args_str += " --hashes"
        args_str += f" --max-part-size {self.max_part_size_var.get()}"
        args_str += f" --format {'txt' if self.save_as_txt_var.get() else 'md'}"
        if not self.split_large_var.get():
            args_str += " --no-split"
        args_str += f" --single-file-limit {self.single_limit_var.get()}"
        if self.use_placeholders_var.get():
            args_str += " --use-placeholders"
        if not self.include_tree_var.get():
            args_str += " --no-include-tree"
        if not self.parse_git_var.get():
            args_str += " --no-parse-git"
        if self.timestamp_var.get():
            args_str += " --timestamp"
        args_str += f" --max-output-parts {self.max_output_parts_var.get()}"
        if self.include_binary_var.get():
            args_str += " --include-binary"
        args_str += f" --input-type {self.input_type_var.get()}"
        return args_str
    # --- File Browsing Section ---
    def browse_start(self):
        input_type = self.input_type_var.get()
        if input_type == "Local":
            initial = self.start_dir_var.get() or os.getcwd()
            if os.path.isdir(initial):
                dir_path = filedialog.askdirectory(initialdir=initial)
                if dir_path:
                    self.start_dir_var.set(dir_path)
                    self.output_dir_var.set(dir_path) # Sync output dir
                    self.add_to_recent(dir_path)
            else:
                file_path = filedialog.askopenfilename(initialdir=os.path.dirname(initial) if initial else os.getcwd())
                if file_path:
                    self.start_dir_var.set(file_path)
                    self.output_dir_var.set(os.path.dirname(file_path))
                    self.add_to_recent(file_path)
        else: # GitHub
            url = simpledialog.askstring("GitHub Repo", "Enter GitHub repository URL (e.g., https://github.com/user/repo):", initialvalue=self.start_dir_var.get())
            if url:
                self.start_dir_var.set(url)
                self.output_dir_var.set(os.getcwd()) # For GitHub, default to cwd
    def browse_output(self):
        dir_path = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if dir_path:
            self.output_dir_var.set(dir_path)
    # --- Pattern Parsing and Validation Section ---
    def get_text_content(self, text_widget):
        return text_widget.get("1.0", tk.END).strip()
    def parse_list(self, text_widget):
        content = self.get_text_content(text_widget)
        if not content:
            return []
        return [item.strip() for item in content.split(';') if item.strip()]
    def parse_extensions(self):
        exts = self.parse_list(self.extensions_text)
        return [f".{e}" if not e.startswith('.') else e for e in exts]
    def validate_patterns(self, event=None):
        invalid = False
        widgets = {
            'include': self.include_text,
            'exclude': self.exclude_text,
            'dynamic': self.dynamic_text,
            'project_exclude': self.project_exclude_text
        }
        for name, widget in widgets.items():
            widget.tag_remove("error", "1.0", tk.END)
            content = self.get_text_content(widget)
            if not content:
                continue
            # Assume no newlines for simplicity; users should not insert newlines in patterns
            parts = [p.strip() for p in content.split(';') if p.strip()]
            col = 0
            for part in parts:
                start = f"1.{col}"
                end = f"1.{col + len(part)}"
                try:
                    re.compile(glob_to_regex(part))
                except re.error:
                    widget.tag_add("error", start, end)
                    invalid = True
                col += len(part) + 1 # for ;
        if invalid:
            self.pattern_status.config(text="Invalid patterns highlighted", foreground="red")
        else:
            self.pattern_status.config(text="Patterns OK", foreground="green")
    # --- Testing and Validation Section ---
    def test_filter(self):
        try:
            start_dir = self.start_dir_var.get().rstrip('\\').rstrip('/')
            if not start_dir:
                raise ValueError("Start directory cannot be empty.")
            start_full = os.path.abspath(start_dir) if self.input_type_var.get() == "Local" else start_dir
            output_dir = self.output_dir_var.get().rstrip('\\').rstrip('/')
            if not output_dir:
                raise ValueError("Output directory cannot be empty.")
            output_full = os.path.abspath(output_dir)
            extensions = self.parse_extensions()
            include_patterns = self.parse_list(self.include_text)
            exclude = self.parse_list(self.exclude_text)
            message, color = test_filter(start_full, output_full, extensions, include_patterns, exclude,
                                         self.exclude_cmake_var.get(), self.exclude_vscode_var.get(), self.input_type_var.get())
            self.update_progress(message, color)
        except Exception as e:
            self.update_progress(f"Test error: {e}", "red")
    def validate_inputs(self):
        start_dir = self.start_dir_var.get().rstrip('\\').rstrip('/')
        if not start_dir:
            raise ValueError("Start directory cannot be empty.")
        if self.input_type_var.get() == "GitHub":
            if not re.match(r'https://github\.com/[^\s/]+/[^\s/]+', start_dir):
                raise ValueError("Invalid GitHub URL format. Use https://github.com/user/repo")
        start_full = os.path.abspath(start_dir) if self.input_type_var.get() == "Local" else start_dir
        output_dir = self.output_dir_var.get().rstrip('\\').rstrip('/')
        if not output_dir:
            raise ValueError("Output directory cannot be empty.")
        output_full = os.path.abspath(output_dir)
        if os.path.exists(output_full) and os.path.isfile(output_full):
            raise ValueError("Output path exists and is a file. It must be a directory.")
        output_base = self.output_base_var.get().strip()
        if not output_base:
            raise ValueError("Output file base cannot be empty.")
        try:
            max_part_size = int(self.max_part_size_var.get())
            if max_part_size <= 0:
                raise ValueError("Max part size must be positive.")
            single_file_limit = int(self.single_limit_var.get())
            if single_file_limit <= 0:
                raise ValueError("Single file limit must be positive.")
            max_output_parts = int(self.max_output_parts_var.get())
            if max_output_parts < 0:
                raise ValueError("Max output parts cannot be negative.")
        except ValueError:
            raise ValueError("Max part size, single file limit, and max output parts must be non-negative integers.")
        extensions = self.parse_extensions()
        if not extensions:
            raise ValueError("At least one extension must be specified.")
        return {
            "start_dir": start_full,
            "output_dir": output_full,
            "output_base": output_base,
            "minify": self.minify_var.get(),
            "include_hashes": self.include_hashes_var.get(),
            "max_part_size": max_part_size,
            "format_out": "txt" if self.save_as_txt_var.get() else "md",
            "split_large_files": self.split_large_var.get(),
            "single_file_limit": single_file_limit,
            "extensions": extensions,
            "include_patterns": self.parse_list(self.include_text),
            "exclude": self.parse_list(self.exclude_text),
            "exclude_cmake": self.exclude_cmake_var.get(),
            "exclude_vscode": self.exclude_vscode_var.get(),
            "dynamic_patterns": self.parse_list(self.dynamic_text),
            "is_exclude_dynamic": self.is_exclude_dynamic_var.get(),
            "input_type": self.input_type_var.get(),
            "use_placeholders": self.use_placeholders_var.get(),
            "include_tree": self.include_tree_var.get(),
            "parse_git": self.parse_git_var.get(),
            "timestamp": self.timestamp_var.get(),
            "max_output_parts": max_output_parts,
            "include_binary": self.include_binary_var.get(),
            "preset_files": None,
            "full_backup": self.full_backup_var.get()
        }
    # --- Dump Execution Section ---
    def do_run_dump(self):
        try:
            params = self.validate_inputs()
            preset_name = self.preset_var.get()
            if preset_name != "None":
                project_dir = self.get_project_dir()
                params["preset_files"] = [os.path.join(project_dir, rel.replace('/', os.sep)) for rel in self.presets[preset_name]]
            if not self.mini_win:
                self.progress_bar.start()
            self.update_progress("Running dump...", "black")
            def progress_cb(msg, color="black"):
                self.root.after(0, lambda: self.update_progress(msg, color))
            params["progress_callback"] = progress_cb
            def do_run():
                message, color = run_dump(**params)
                self.root.after(0, lambda: self.finish_run(message, color))
            thread = threading.Thread(target=do_run, daemon=True)
            thread.start()
        except Exception as e:
            if not self.mini_win:
                self.progress_bar.stop()
            self.update_progress(f"Validation error: {e}", "red")
    def finish_run(self, message, color):
        if not self.mini_win:
            self.progress_bar.stop()
        self.update_progress(message, color)
    # --- Settings Management Section ---
    def save_settings(self, quiet=False):
        if not quiet:
            if not messagebox.askyesno("Save", "Save global settings?"):
                return
        try:
            params = self.validate_inputs()
            custom_config.update({
                "LastOutputBase": params["output_base"],
                "LastMinify": params["minify"],
                "LastIncludeHashes": params["include_hashes"],
                "LastMaxPartSize": params["max_part_size"],
                "LastFormat": params["format_out"],
                "LastSplitLargeFiles": params["split_large_files"],
                "LastSingleFileLimit": params["single_file_limit"],
                "LastProfile": self.profile_var.get(),
                "LastExcludeCMake": self.exclude_cmake_var.get(),
                "LastExcludeVSCode": self.exclude_vscode_var.get(),
                "IsExcludeDynamic": params["is_exclude_dynamic"],
                "LastInputType": self.input_type_var.get(),
                "LastUsePlaceholders": params["use_placeholders"],
                "LastIncludeTree": self.include_tree_var.get(),
                "LastParseGit": self.parse_git_var.get(),
                "LastTimestamp": self.timestamp_var.get(),
                "LastFormWidth": self.root.winfo_width(),
                "LastFormHeight": self.root.winfo_height(),
                "LastFormX": self.root.winfo_x(),
                "LastFormY": self.root.winfo_y(),
                "LastMaxOutputParts": params["max_output_parts"],
                "UseDefaultBackupPath": self.use_default_backup_path_var.get(),
                "LastFullBackup": self.full_backup_var.get(),
                "LastIncludeBinary": self.include_binary_var.get(),
                "DynamicPatterns": params["dynamic_patterns"],
                "AutoSaveIntervalMinutes": int(self.auto_save_interval_var.get()),
                "BackupIntervalHours": int(self.backup_interval_var.get())
            })
            save_config(custom_config)
            self.backup_interval = int(self.backup_interval_var.get()) * 3600
            self.remaining_time = self.backup_interval
            if not quiet:
                self.update_progress("Settings saved successfully.", "green")
        except Exception as e:
            if not quiet:
                self.update_progress(f"Save error: {e}", "red")
            else:
                logging.error(f"Save settings failed: {e}")
    # --- Utility Methods Section ---
    def update_progress(self, message, color):
        if self.mini_win:
            self.mini_win.update_progress(message, color)
        else:
            self.progress_text.config(state=tk.NORMAL)
            self.progress_text.delete("1.0", tk.END)
            self.progress_text.insert("1.0", message)
            self.progress_text.config(state=tk.DISABLED, fg=color)
            self.root.update()
        custom_config["LastProgressMessage"] = message
        save_config(custom_config)
# TODO (Major Enhancement): Add support for more input types like local Git repos or zip archives.
# TODO (Major Enhancement): Add CLI support for GitHub input (--input-type github URL).
# TODO (Major Enhancement): Support custom minification plugins or scripts.
# TODO (Major Enhancement): Allow overriding default profile deletion with confirmation for advanced users.
# TODO (Major Enhancement): Load profiles from external files for easier sharing/updates.