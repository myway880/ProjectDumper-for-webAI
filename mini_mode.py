# mini_mode.py
# --- Imports Section ---
import tkinter as tk
from tkinter import ttk
from core_dump import custom_config
# --- MiniWindow Class Section ---
class MiniWindow(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("Mini Mode")
        default_mini_width = custom_config.get("MiniFormWidth", 300)
        default_mini_height = custom_config.get("MiniFormHeight", 120)
        default_mini_x = custom_config.get("MiniFormX", 100)
        default_mini_y = custom_config.get("MiniFormY", 100)
        self.geometry(f"{default_mini_width}x{default_mini_height}+{default_mini_x}+{default_mini_y}")
        self.attributes('-topmost', True)
        self.showing_message = False
        self.remaining_time = self.app.backup_interval
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=5)
        ttk.Button(button_frame, text="Run Dump", command=self.app.do_run_dump).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Backup", command=self.app.backup).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Restore", command=self.app.restore).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Full Mode", command=self.toggle_full).pack(side=tk.LEFT, padx=5)
        self.status_text = tk.Text(self, height=3, width=35, state=tk.DISABLED, wrap=tk.WORD, bg="lightgray")
        self.status_text.pack(pady=5)
        mins, secs = divmod(self.remaining_time, 60)
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert("1.0", f"Next backup in {mins}:{secs:02d}")
        self.status_text.config(state=tk.DISABLED)
        self.after(1000, self.update_timer)
    def update_timer(self):
        self.remaining_time -= 1
        if self.remaining_time <= 0:
            self.app.backup()
            self.remaining_time = self.app.backup_interval
        if not self.showing_message:
            mins, secs = divmod(self.remaining_time, 60)
            self.status_text.config(state=tk.NORMAL)
            self.status_text.delete("1.0", tk.END)
            self.status_text.insert("1.0", f"Next backup in {mins}:{secs:02d}")
            self.status_text.config(state=tk.DISABLED, fg="black")
        self.after(1000, self.update_timer)
    def update_progress(self, message, color):
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete("1.0", tk.END)
        self.status_text.insert("1.0", message)
        self.status_text.config(state=tk.DISABLED, fg=color)
        self.showing_message = True
        self.after(10000, lambda: setattr(self, 'showing_message', False))
    def toggle_full(self):
        self.app.toggle_mini_mode()
# TODO (Enhancement): Add progress bar to mini mode for long operations.
# TODO (Design Improvement): Make mini mode resizable with saved geometry.