"""
Windows Native PC Status Sensor & Telemetry Reporter for WinVE.
Leverages ctypes and lightweight subprocess queries to retrieve system health
without heavy dependencies (like psutil).
"""
import ctypes
import os
import subprocess
import json
import time

class Win32_MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedPhys", ctypes.c_ulonglong),
    ]

class PCStatusReporter:
    """Retrieves local PC diagnostic state using Windows APIs and sends metrics."""
    
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        
    def get_ram_usage(self):
        """Returns RAM usage percentage, total, and available bytes using Kernel32 GlobalMemoryStatusEx."""
        stat = Win32_MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(stat)
        if self.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return {
                "percent_used": stat.dwMemoryLoad,
                "total_gb": round(stat.ullTotalPhys / (1024**3), 2),
                "available_gb": round(stat.ullAvailPhys / (1024**3), 2)
            }
        return {"percent_used": 0, "total_gb": 0, "available_gb": 0}

    def get_cpu_usage(self):
        """Gets CPU load average via native wmic command to avoid dependencies."""
        try:
            # Runs quick wmic query
            output = subprocess.check_output(
                "wmic cpu get loadpercentage /value", 
                shell=True, 
                stderr=subprocess.DEVNULL
            ).decode('utf-8')
            for line in output.splitlines():
                if "LoadPercentage=" in line:
                    return int(line.split("=")[1].strip())
        except Exception:
            # Fallback to powershell query if wmic is disabled/missing
            try:
                ps_cmd = "Get-WmiObject Win32_Processor | Select-Object -ExpandProperty LoadPercentage"
                output = subprocess.check_output(
                    f"powershell -Command \"{ps_cmd}\"", 
                    shell=True
                ).decode('utf-8').strip()
                return int(output)
            except Exception:
                pass
        return 0

    def is_workstation_locked(self):
        """Checks if Windows session is locked using User32 OpenInputDesktop."""
        # OpenInputDesktop will fail (return 0) if the workstation is locked or switch-user screen is active
        h_desk = self.user32.OpenInputDesktop(0, False, 0x0100) # DESKTOP_SWITCHDESKTOP access right
        if h_desk:
            self.user32.CloseDesktop(h_desk)
            return False
        return True

    def get_active_window_title(self):
        """Retrieves title text of the currently active window using User32."""
        hwnd = self.user32.GetForegroundWindow()
        if not hwnd:
            return "None/Lockscreen"
            
        length = self.user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return "Unknown"
            
        buf = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value

    def get_battery_status(self):
        """Queries battery charge/power status from Windows registry or wmic."""
        try:
            output = subprocess.check_output(
                "wmic path Win32_Battery get EstimatedChargeRemaining,BatteryStatus /value",
                shell=True,
                stderr=subprocess.DEVNULL
            ).decode('utf-8')
            metrics = {}
            for line in output.splitlines():
                if "=" in line:
                    k, v = line.split("=")
                    metrics[k.strip()] = int(v.strip())
            return {
                "percent": metrics.get("EstimatedChargeRemaining", 100),
                "charging": metrics.get("BatteryStatus", 1) == 2 # 2 means charging
            }
        except Exception:
            return {"percent": 100, "charging": True} # Fallback/Desktop PC

    def compile_telemetry(self):
        """Bundles all telemetry data together."""
        return {
            "timestamp": time.time(),
            "cpu_load_percent": self.get_cpu_usage(),
            "ram_status": self.get_ram_usage(),
            "locked": self.is_workstation_locked(),
            "focused_application": self.get_active_window_title(),
            "power": self.get_battery_status()
        }

    def start_reporting_loop(self, interval_seconds=30):
        """Continuously prints or sends telemetry metrics."""
        print(f"🖥️ PC Status Telemetry active. Reporting every {interval_seconds}s...")
        try:
            while True:
                telemetry = self.compile_telemetry()
                print(f"\n[Telemetry Update] {time.strftime('%H:%M:%S')}")
                print(json.dumps(telemetry, indent=2))
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("🖥️ Telemetry reporting stopped.")

if __name__ == "__main__":
    reporter = PCStatusReporter()
    # Read once immediately
    data = reporter.compile_telemetry()
    print("Initial diagnostic report:")
    print(json.dumps(data, indent=2))
    
    # Run short loop
    print("\nRunning demonstration loop (Ctrl+C to stop)...")
    reporter.start_reporting_loop(interval_seconds=5)
