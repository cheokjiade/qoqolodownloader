import os
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

# Import downloader functions - support both package install and direct run
try:
    from qoqolodownloader.downloader import (
        load_config, save_config, setup_directories,
        create_driver, do_login,
        download_checkin_photos, download_activity_photos,
    )
except ImportError:
    from downloader import (
        load_config, save_config, setup_directories,
        create_driver, do_login,
        download_checkin_photos, download_activity_photos,
    )

# Resolve paths for both development and PyInstaller bundled mode
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).parent
else:
    SCRIPT_DIR = Path(__file__).parent


def find_config_path():
    """Find config.properties in script dir or CWD."""
    candidates = [
        SCRIPT_DIR / "config.properties",
        Path.cwd() / "config.properties",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return str(candidates[0])  # default to script dir even if not found


class QoqoloDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Qoqolo Downloader")
        self.geometry("720x750")
        self.minsize(600, 600)

        self.cancel_event = threading.Event()
        self.download_thread = None
        self.config_path = find_config_path()
        self.advanced_visible = False

        # Store widget references
        self.entries = {}
        self.check_vars = {}

        self._build_ui()
        self._load_config()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main scrollable frame
        self.main_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        self.main_frame.grid_columnconfigure(0, weight=1)

        row = 0
        row = self._build_credentials_section(self.main_frame, row)
        row = self._build_child_section(self.main_frame, row)
        row = self._build_download_options_section(self.main_frame, row)
        row = self._build_output_section(self.main_frame, row)
        row = self._build_advanced_section(self.main_frame, row)
        row = self._build_action_buttons(self.main_frame, row)
        row = self._build_progress_section(self.main_frame, row)
        row = self._build_log_section(self.main_frame, row)

    # ── Section builders ─────────────────────────────────

    def _build_credentials_section(self, parent, row):
        label = ctk.CTkLabel(parent, text="Credentials", font=ctk.CTkFont(size=14, weight="bold"))
        label.grid(row=row, column=0, sticky="w", pady=(5, 2))
        row += 1

        cred_frame = ctk.CTkFrame(parent, fg_color="transparent")
        cred_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        cred_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(cred_frame, text="Username:").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=2)
        self.entries["username"] = ctk.CTkEntry(cred_frame, placeholder_text="your@email.com")
        self.entries["username"].grid(row=0, column=1, sticky="ew", pady=2)

        ctk.CTkLabel(cred_frame, text="Password:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=2)
        pw_frame = ctk.CTkFrame(cred_frame, fg_color="transparent")
        pw_frame.grid(row=1, column=1, sticky="ew", pady=2)
        pw_frame.grid_columnconfigure(0, weight=1)

        self.entries["password"] = ctk.CTkEntry(pw_frame, show="*", placeholder_text="password")
        self.entries["password"].grid(row=0, column=0, sticky="ew")
        self.show_pw_btn = ctk.CTkButton(pw_frame, text="Show", width=50, command=self._toggle_password)
        self.show_pw_btn.grid(row=0, column=1, padx=(5, 0))

        row += 1
        return row

    def _build_child_section(self, parent, row):
        label = ctk.CTkLabel(parent, text="Child", font=ctk.CTkFont(size=14, weight="bold"))
        label.grid(row=row, column=0, sticky="w", pady=(10, 2))
        row += 1

        child_frame = ctk.CTkFrame(parent, fg_color="transparent")
        child_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        child_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(child_frame, text="Child Name:").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=2)
        self.entries["childname"] = ctk.CTkEntry(child_frame, placeholder_text="CHILD NAME")
        self.entries["childname"].grid(row=0, column=1, sticky="ew", pady=2)

        hint = ctk.CTkLabel(child_frame, text="Enter the full name in CAPS, exactly as it appears on the Qoqolo website",
                            font=ctk.CTkFont(size=11), text_color="gray")
        hint.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 2))

        row += 1
        return row

    def _build_download_options_section(self, parent, row):
        label = ctk.CTkLabel(parent, text="Download Options", font=ctk.CTkFont(size=14, weight="bold"))
        label.grid(row=row, column=0, sticky="w", pady=(10, 2))
        row += 1

        opts_frame = ctk.CTkFrame(parent, fg_color="transparent")
        opts_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        opts_frame.grid_columnconfigure((0, 1), weight=1)

        # Checkboxes
        self.check_vars["download_checkin"] = ctk.StringVar(value="yes")
        cb1 = ctk.CTkCheckBox(opts_frame, text="Download Check-in/out",
                              variable=self.check_vars["download_checkin"],
                              onvalue="yes", offvalue="no")
        cb1.grid(row=0, column=0, sticky="w", pady=2)

        self.check_vars["download_activities"] = ctk.StringVar(value="yes")
        cb2 = ctk.CTkCheckBox(opts_frame, text="Download Activities",
                              variable=self.check_vars["download_activities"],
                              onvalue="yes", offvalue="no")
        cb2.grid(row=0, column=1, sticky="w", pady=2)

        # Months and Year
        fields_frame = ctk.CTkFrame(parent, fg_color="transparent")
        fields_frame.grid(row=row + 1, column=0, sticky="ew", pady=(0, 5))
        fields_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(fields_frame, text="Months:").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=2)
        self.entries["signin_months_to_download"] = ctk.CTkEntry(fields_frame, placeholder_text="1,2,3,4,5,6,7,8,9,10,11,12")
        self.entries["signin_months_to_download"].grid(row=0, column=1, sticky="ew", pady=2)

        ctk.CTkLabel(fields_frame, text="Year:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=2)
        self.entries["signin_year_to_download"] = ctk.CTkEntry(fields_frame, placeholder_text="2025")
        self.entries["signin_year_to_download"].grid(row=1, column=1, sticky="ew", pady=2)

        # Scroll times and sleep time on same row
        tuning_frame = ctk.CTkFrame(parent, fg_color="transparent")
        tuning_frame.grid(row=row + 2, column=0, sticky="ew", pady=(0, 5))
        tuning_frame.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(tuning_frame, text="Scroll Times:").grid(row=0, column=0, sticky="w", padx=(0, 5), pady=2)
        self.entries["activities_scroll_times"] = ctk.CTkEntry(tuning_frame, width=60)
        self.entries["activities_scroll_times"].insert(0, "7")
        self.entries["activities_scroll_times"].grid(row=0, column=1, sticky="w", pady=2)

        ctk.CTkLabel(tuning_frame, text="Sleep Time (s):").grid(row=0, column=2, sticky="w", padx=(20, 5), pady=2)
        self.entries["default_sleep_time"] = ctk.CTkEntry(tuning_frame, width=60)
        self.entries["default_sleep_time"].insert(0, "3")
        self.entries["default_sleep_time"].grid(row=0, column=3, sticky="w", pady=2)

        tuning_hint = ctk.CTkLabel(parent, text="Leave defaults unless downloads are failing. Increase Sleep Time if pages load slowly, Scroll Times for older activity posts.",
                                   font=ctk.CTkFont(size=11), text_color="gray", wraplength=650, justify="left")
        tuning_hint.grid(row=row + 3, column=0, sticky="w", pady=(0, 5))

        row += 4
        return row

    def _build_output_section(self, parent, row):
        label = ctk.CTkLabel(parent, text="Output Directory", font=ctk.CTkFont(size=14, weight="bold"))
        label.grid(row=row, column=0, sticky="w", pady=(10, 2))
        row += 1

        out_frame = ctk.CTkFrame(parent, fg_color="transparent")
        out_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        out_frame.grid_columnconfigure(0, weight=1)

        self.output_dir_entry = ctk.CTkEntry(out_frame, placeholder_text="Select output directory...")
        self.output_dir_entry.grid(row=0, column=0, sticky="ew")
        # Default to the directory containing config.properties
        default_dir = str(SCRIPT_DIR)
        self.output_dir_entry.insert(0, default_dir)

        browse_btn = ctk.CTkButton(out_frame, text="Browse...", width=80, command=self._browse_output_dir)
        browse_btn.grid(row=0, column=1, padx=(5, 0))

        row += 1
        return row

    def _build_advanced_section(self, parent, row):
        self.advanced_toggle_btn = ctk.CTkButton(
            parent, text="> Advanced Settings", anchor="w",
            fg_color="transparent", text_color=("gray10", "gray90"),
            hover_color=("gray80", "gray30"),
            command=self._toggle_advanced
        )
        self.advanced_toggle_btn.grid(row=row, column=0, sticky="ew", pady=(10, 2))
        row += 1

        self.advanced_frame = ctk.CTkFrame(parent)
        self.advanced_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        self.advanced_frame.grid_columnconfigure(1, weight=1)
        self.advanced_frame.grid_remove()  # hidden by default

        advanced_fields = [
            ("page_login", "Login URL:"),
            ("page_checkin", "Check-in URL:"),
            ("page_activities", "Activities URL:"),
            ("xpath_signin_table", "XPath Signin Table:"),
            ("xpath_activity_posts", "XPath Activity Posts:"),
            ("xpath_activity_post_images", "XPath Post Images:"),
            ("xpath_photo_carousel_close", "XPath Carousel Close:"),
        ]
        for i, (key, label_text) in enumerate(advanced_fields):
            ctk.CTkLabel(self.advanced_frame, text=label_text).grid(
                row=i, column=0, sticky="w", padx=(10, 10), pady=2
            )
            self.entries[key] = ctk.CTkEntry(self.advanced_frame)
            self.entries[key].grid(row=i, column=1, sticky="ew", padx=(0, 10), pady=2)

        row += 1
        return row

    def _build_action_buttons(self, parent, row):
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.grid(row=row, column=0, sticky="ew", pady=(10, 5))
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.start_btn = ctk.CTkButton(btn_frame, text="Start Download",
                                       fg_color="green", hover_color="darkgreen",
                                       command=self._start_download)
        self.start_btn.grid(row=0, column=0, padx=5, sticky="ew")

        self.cancel_btn = ctk.CTkButton(btn_frame, text="Cancel",
                                        fg_color="red", hover_color="darkred",
                                        state="disabled", command=self._cancel_download)
        self.cancel_btn.grid(row=0, column=1, padx=5, sticky="ew")

        self.save_btn = ctk.CTkButton(btn_frame, text="Save Config", command=self._save_config)
        self.save_btn.grid(row=0, column=2, padx=5, sticky="ew")

        row += 1
        return row

    def _build_progress_section(self, parent, row):
        prog_frame = ctk.CTkFrame(parent, fg_color="transparent")
        prog_frame.grid(row=row, column=0, sticky="ew", pady=(5, 2))
        prog_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(prog_frame)
        self.progress_bar.grid(row=0, column=0, sticky="ew")
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(prog_frame, text="0%", width=120)
        self.progress_label.grid(row=0, column=1, padx=(10, 0))

        row += 1
        return row

    def _build_log_section(self, parent, row):
        label = ctk.CTkLabel(parent, text="Log Output", font=ctk.CTkFont(size=14, weight="bold"))
        label.grid(row=row, column=0, sticky="w", pady=(10, 2))
        row += 1

        self.log_textbox = ctk.CTkTextbox(parent, height=200, state="disabled")
        self.log_textbox.grid(row=row, column=0, sticky="ew", pady=(0, 10))

        row += 1
        return row

    # ── Config management ────────────────────────────────

    def _load_config(self):
        """Load config from file and populate all GUI fields."""
        try:
            config = load_config(self.config_path)
            self._populate_fields(config)
            self._log(f"Config loaded from {self.config_path}")
        except FileNotFoundError:
            self._log(f"Config file not found at {self.config_path}. Using defaults.")
        except Exception as e:
            self._log(f"Error loading config: {e}")

    def _populate_fields(self, config):
        """Set all entry/checkbox values from config dict."""
        for key, entry in self.entries.items():
            if key in config:
                entry.delete(0, "end")
                entry.insert(0, config[key])

        for key, var in self.check_vars.items():
            if key in config:
                var.set(config[key])

        # Set output directory if stored in config
        if "output_base_dir" in config and config["output_base_dir"]:
            self.output_dir_entry.delete(0, "end")
            self.output_dir_entry.insert(0, config["output_base_dir"])

    def _collect_config(self):
        """Read all entry/checkbox values into a config dict."""
        config = {}
        for key, entry in self.entries.items():
            config[key] = entry.get()
        for key, var in self.check_vars.items():
            config[key] = var.get()
        return config

    def _save_config(self):
        """Persist current GUI fields to config.properties."""
        try:
            config = self._collect_config()
            # Also save the output directory
            config["output_base_dir"] = self.output_dir_entry.get()
            save_config(self.config_path, config)
            self._log(f"Config saved to {self.config_path}")
        except Exception as e:
            self._log(f"Error saving config: {e}")

    # ── UI actions ───────────────────────────────────────

    def _toggle_password(self):
        current = self.entries["password"].cget("show")
        if current == "*":
            self.entries["password"].configure(show="")
            self.show_pw_btn.configure(text="Hide")
        else:
            self.entries["password"].configure(show="*")
            self.show_pw_btn.configure(text="Show")

    def _toggle_advanced(self):
        if self.advanced_visible:
            self.advanced_frame.grid_remove()
            self.advanced_toggle_btn.configure(text="> Advanced Settings")
        else:
            self.advanced_frame.grid()
            self.advanced_toggle_btn.configure(text="v Advanced Settings")
        self.advanced_visible = not self.advanced_visible

    def _browse_output_dir(self):
        directory = filedialog.askdirectory(
            initialdir=self.output_dir_entry.get() or str(SCRIPT_DIR)
        )
        if directory:
            self.output_dir_entry.delete(0, "end")
            self.output_dir_entry.insert(0, directory)

    # ── Logging and progress (thread-safe) ───────────────

    def _log(self, message):
        """Append a timestamped message to the log textbox. Thread-safe."""
        def _append():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", f"{timestamp} - {message}\n")
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
        self.after(0, _append)

    def _update_progress(self, current, total, phase=""):
        """Update progress bar. Thread-safe."""
        def _update():
            fraction = current / total if total > 0 else 0
            self.progress_bar.set(fraction)
            pct = f"{int(fraction * 100)}%"
            label = f"{phase} {pct}" if phase else pct
            self.progress_label.configure(text=label)
        self.after(0, _update)

    # ── Download orchestration ───────────────────────────

    def _start_download(self):
        """Collect config, validate, start download in background thread."""
        config = self._collect_config()

        # Validation
        if not config.get("username"):
            self._log("Error: Username is required.")
            return
        if not config.get("password"):
            self._log("Error: Password is required.")
            return
        try:
            int(config.get("default_sleep_time", "3"))
        except ValueError:
            self._log("Error: Sleep Time must be a number.")
            return
        try:
            int(config.get("activities_scroll_times", "7"))
        except ValueError:
            self._log("Error: Scroll Times must be a number.")
            return
        months_str = config.get("signin_months_to_download", "")
        if months_str:
            try:
                [int(m.strip()) for m in months_str.split(",")]
            except ValueError:
                self._log("Error: Months must be comma-separated numbers (e.g. 1,2,3).")
                return

        # Reset UI state
        self.cancel_event.clear()
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.save_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")

        # Clear log
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("0.0", "end")
        self.log_textbox.configure(state="disabled")

        base_dir = self.output_dir_entry.get() or str(SCRIPT_DIR)

        self.download_thread = threading.Thread(
            target=self._download_worker,
            args=(config, base_dir),
            daemon=True,
        )
        self.download_thread.start()

    def _download_worker(self, config, base_dir):
        """Runs in background thread. Calls refactored downloader functions."""
        try:
            self._log("Setting up output directories...")
            checkinout_dir, activities_dir = setup_directories(config, base_dir)

            self._log("Launching Chrome browser...")
            driver = create_driver()

            try:
                self._log("Logging in...")
                do_login(driver, config, log_fn=self._log)

                if config.get("download_checkin") == "yes" and not self.cancel_event.is_set():
                    self._log("--- Starting check-in/out photo download ---")
                    self._update_progress(0, 1, phase="[Check-in]")
                    checkin_progress = lambda c, t: self._update_progress(c, t, phase="[Check-in]")
                    download_checkin_photos(
                        driver, config, checkinout_dir,
                        log_fn=self._log,
                        progress_fn=checkin_progress,
                        cancel_event=self.cancel_event,
                    )

                if config.get("download_activities") == "yes" and not self.cancel_event.is_set():
                    self._log("--- Starting activities photo download ---")
                    self._update_progress(0, 1, phase="[Activities]")
                    activity_progress = lambda c, t: self._update_progress(c, t, phase="[Activities]")
                    download_activity_photos(
                        driver, config, activities_dir,
                        log_fn=self._log,
                        progress_fn=activity_progress,
                        cancel_event=self.cancel_event,
                    )

                if self.cancel_event.is_set():
                    self._log("Download cancelled by user.")
                else:
                    self._log("All downloads complete!")
                    self._update_progress(1, 1)
            finally:
                driver.quit()
                self._log("Browser closed.")

        except Exception as e:
            self._log(f"Error: {e}")
            traceback.print_exc()
        finally:
            self.after(0, self._download_finished)

    def _download_finished(self):
        """Re-enable UI after download completes or fails."""
        self.start_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.save_btn.configure(state="normal")

    def _cancel_download(self):
        """Set cancel event. Download loops check this between iterations."""
        self.cancel_event.set()
        self._log("Cancellation requested... will stop after current operation.")

    def _on_close(self):
        """Handle window close: cancel download, wait briefly for cleanup, then destroy."""
        self.cancel_event.set()
        if self.download_thread and self.download_thread.is_alive():
            # Give the download thread a moment to quit the browser
            self.download_thread.join(timeout=3)
        self.destroy()


def main():
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = QoqoloDownloaderApp()
    app.protocol("WM_DELETE_WINDOW", app._on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
