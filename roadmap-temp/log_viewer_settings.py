"""
Flet Log Viewer settings panel/popup for real-time diagnostic output.
Provides search/filtering and auto-scrolling log visualizers.
"""
import flet as ft
import os
import threading
import time

class RealtimeLogViewer(ft.UserControl):
    """Realtime log viewer widget using Flet UI."""
    def __init__(self, log_file_path=None):
        super().__init__()
        self.log_file_path = log_file_path or os.path.join(os.path.dirname(__file__), "..", "winve.log")
        self.log_list = ft.ListView(expand=True, spacing=4, auto_scroll=True)
        self.filter_input = ft.TextField(
            hint_text="Search logs...", 
            on_change=self._filter_logs, 
            expand=True,
            height=40,
            text_size=14
        )
        self.severity_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("ALL"),
                ft.dropdown.Option("INFO"),
                ft.dropdown.Option("WARNING"),
                ft.dropdown.Option("ERROR"),
            ],
            value="ALL",
            width=120,
            height=40,
            on_change=self._filter_logs
        )
        self.auto_scroll_checkbox = ft.Checkbox(label="Auto-scroll", value=True, on_change=self._toggle_autoscroll)
        self.all_log_lines = []
        self.running = False
        
    def build(self):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    self.filter_input,
                    self.severity_dropdown,
                    self.auto_scroll_checkbox,
                    ft.IconButton(icon=ft.icons.REFRESH, on_click=self.refresh_logs),
                    ft.IconButton(icon=ft.icons.DELETE_FOREVER, on_click=self.clear_logs)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                ft.Container(
                    content=self.log_list,
                    border=ft.border.all(1, ft.colors.OUTLINE),
                    border_radius=8,
                    bgcolor=ft.colors.BLACK87,
                    padding=10,
                    expand=True
                )
            ]),
            expand=True
        )

    def did_mount(self):
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_log_file, daemon=True)
        self.monitor_thread.start()

    def will_unmount(self):
        self.running = False

    def _toggle_autoscroll(self, e):
        self.log_list.auto_scroll = self.auto_scroll_checkbox.value
        self.log_list.update()

    def clear_logs(self, e):
        if os.path.exists(self.log_file_path):
            try:
                with open(self.log_file_path, "w", encoding="utf-8") as f:
                    f.truncate(0)
            except Exception as ex:
                print(f"Error clearing logs: {ex}")
        self.all_log_lines = []
        self.log_list.controls.clear()
        self.log_list.update()

    def refresh_logs(self, e=None):
        self._load_full_log()
        self._render_logs()

    def _load_full_log(self):
        if not os.path.exists(self.log_file_path):
            self.all_log_lines = ["[System] Log file does not exist yet."]
            return
            
        try:
            with open(self.log_file_path, "r", encoding="utf-8", errors="ignore") as f:
                self.all_log_lines = f.readlines()
        except Exception as ex:
            self.all_log_lines = [f"[Error reading log file] {ex}"]

    def _render_logs(self):
        self.log_list.controls.clear()
        filter_text = self.filter_input.value.lower() if self.filter_input.value else ""
        severity_filter = self.severity_dropdown.value
        
        for line in self.all_log_lines:
            line_str = line.strip()
            if not line_str:
                continue
            
            # Check search text filter
            if filter_text and filter_text not in line_str.lower():
                continue
                
            # Parse level
            level = "INFO"
            level_color = ft.colors.GREEN_400
            if "WARNING" in line_str or "WARN" in line_str:
                level = "WARNING"
                level_color = ft.colors.AMBER_400
            elif "ERROR" in line_str or "CRITICAL" in line_str or "EXCEPTION" in line_str:
                level = "ERROR"
                level_color = ft.colors.RED_400
                
            # Check severity level filter
            if severity_filter != "ALL" and level != severity_filter:
                continue
                
            self.log_list.controls.append(
                ft.Text(
                    line_str,
                    color=level_color if level != "INFO" else ft.colors.GREY_300,
                    font_family="Consolas",
                    size=12
                )
            )
        self.log_list.update()

    def _filter_logs(self, e):
        self._render_logs()

    def _monitor_log_file(self):
        last_size = 0
        if os.path.exists(self.log_file_path):
            last_size = os.path.getsize(self.log_file_path)
            self._load_full_log()
            self._render_logs()
            
        while self.running:
            try:
                if not os.path.exists(self.log_file_path):
                    time.sleep(1)
                    continue
                    
                current_size = os.path.getsize(self.log_file_path)
                if current_size < last_size:
                    # Log cleared or rotated
                    last_size = current_size
                    self._load_full_log()
                    self._render_logs()
                elif current_size > last_size:
                    # New lines added
                    with open(self.log_file_path, "r", encoding="utf-8", errors="ignore") as f:
                        f.seek(last_size)
                        new_lines = f.readlines()
                        self.all_log_lines.extend(new_lines)
                    last_size = current_size
                    self._render_logs()
            except Exception as e:
                print(f"[Log Monitor Error] {e}")
            time.sleep(0.5)

def main(page: ft.Page):
    page.title = "WinVE Diagnostic Log Viewer"
    page.window_width = 800
    page.window_height = 600
    page.theme_mode = ft.ThemeMode.DARK
    
    # Create a mock log file for demonstration
    log_path = "winve_mock.log"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("2026-05-24 23:00:01,234 INFO [main] Application initializing...\n")
        f.write("2026-05-24 23:00:02,456 INFO [wake_word] Wake word engine loaded (onnxruntime)\n")
        f.write("2026-05-24 23:00:03,892 WARNING [audio] High audio latency detected: 120ms\n")
        f.write("2026-05-24 23:00:05,102 ERROR [client] Connection failed to Home Assistant: Timeout\n")
        f.write("2026-05-24 23:00:06,120 INFO [client] Reconnecting to local satellite gateway...\n")
        
    viewer = RealtimeLogViewer(log_file_path=log_path)
    page.add(viewer)
    
    # Add a button to generate new logs dynamically
    def append_log(e):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"2026-05-24 23:00:{int(time.time())%60:02d},000 INFO [user] Simulated diagnostic event triggered.\n")
            
    page.add(ft.ElevatedButton("Simulate Log Event", on_click=append_log))

if __name__ == "__main__":
    ft.app(target=main)
