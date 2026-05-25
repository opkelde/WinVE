"""
One-Click Application Updater for WinVE.
Queries the GitHub Releases API for the latest version tag, downloads the compiled 
Windows setup binary, and launches the installer to upgrade the running application.
"""
import urllib.request
import json
import os
import subprocess
import sys
import tempfile
import threading

class WinVEUpdater:
    """Manages version check, background download, and installation wrapper."""
    
    def __init__(self, current_version="1.0.0"):
        self.current_version = current_version
        self.repo_url = "https://api.github.com/repos/opkelde/WinVE/releases/latest"
        self.download_progress = 0.0
        self.is_downloading = False
        self.latest_release_info = None

    def check_for_updates(self):
        """Fetches latest release info from GitHub API and compares versions."""
        try:
            # Setup request with User-Agent to avoid API blocks
            req = urllib.request.Request(
                self.repo_url, 
                headers={'User-Agent': 'WinVE-Updater'}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                self.latest_release_info = json.loads(response.read().decode('utf-8'))
                
            tag_name = self.latest_release_info.get("tag_name", "v1.0.0").strip("v")
            
            # Simple version comparison (e.g., "1.1.0" > "1.0.0")
            has_update = self._compare_versions(tag_name, self.current_version)
            
            # Find the Windows installer asset (typically named setup.exe or containing setup/win)
            download_url = None
            for asset in self.latest_release_info.get("assets", []):
                name = asset.get("name", "").lower()
                if "setup" in name or name.endswith(".exe"):
                    download_url = asset.get("browser_download_url")
                    break
                    
            return {
                "update_available": has_update,
                "latest_version": tag_name,
                "download_url": download_url,
                "release_notes": self.latest_release_info.get("body", "")
            }
            
        except Exception as e:
            print(f"Error checking for updates: {e}")
            return {"update_available": False, "error": str(e)}

    def start_upgrade(self, download_url):
        """Starts background thread to download and execute update installer."""
        if self.is_downloading:
            return False
            
        self.is_downloading = True
        self.download_progress = 0.0
        
        thread = threading.Thread(target=self._download_and_run, args=(download_url,), daemon=True)
        thread.start()
        return True

    def _compare_versions(self, version_latest, version_current):
        """Compares dot-separated version strings."""
        try:
            v_l = [int(x) for x in version_latest.split(".")]
            v_c = [int(x) for x in version_current.split(".")]
            return v_l > v_c
        except ValueError:
            return version_latest != version_current

    def _download_and_run(self, url):
        """Downloads setup executable in chunks and executes it."""
        try:
            temp_dir = tempfile.gettempdir()
            installer_path = os.path.join(temp_dir, "WinVE-Setup-Update.exe")
            
            req = urllib.request.Request(url, headers={'User-Agent': 'WinVE-Updater'})
            with urllib.request.urlopen(req) as response:
                total_size = int(response.info().get('Content-Length', 0))
                bytes_downloaded = 0
                
                with open(installer_path, "wb") as out_file:
                    chunk_size = 1024 * 64
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        out_file.write(chunk)
                        bytes_downloaded += len(chunk)
                        
                        if total_size > 0:
                            self.download_progress = bytes_downloaded / total_size
                            print(f"Downloading Update: {self.download_progress * 100:.1f}%")
                            
            print("Download finished. Launching installer and shutting down WinVE...")
            
            # Launch setup in a detached process
            # /SP- disables the "This will install... Do you want to continue?" prompt (Silent/semi-silent Inno Setup)
            # /SILENT runs the installer without showing wizard but showing progress bar
            subprocess.Popen([installer_path, "/SILENT"], shell=True)
            
            # Clean exit of python runtime so files can be overwritten
            sys.exit(0)
            
        except Exception as e:
            self.is_downloading = False
            print(f"Upgrade failed: {e}")

if __name__ == "__main__":
    # Test execution harness
    updater = WinVEUpdater(current_version="1.0.0")
    
    print("Checking for updates from GitHub...")
    result = updater.check_for_updates()
    
    if result.get("update_available"):
        print(f"\n📢 Update Available!")
        print(f"Latest Version: v{result['latest_version']} (Current: v{updater.current_version})")
        print(f"Download URL: {result['download_url']}")
        print(f"Release Notes:\n{result['release_notes']}")
        
        # Simulate trigger
        # updater.start_upgrade(result['download_url'])
    else:
        print(f"\n✅ WinVE is up to date (Version v{updater.current_version}).")
        if "error" in result:
            print(f"Error: {result['error']}")
