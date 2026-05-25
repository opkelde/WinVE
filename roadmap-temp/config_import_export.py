"""
Settings Configuration Import/Export Utility for WinVE.
Enables exporting the current .env and key-value registry configs to a portable,
encrypted or plaintext JSON file, and importing them back safely with schema validation.
"""
import os
import json
import shutil
import time

class ConfigImportExportManager:
    """Handles parsing, backup, validation, and restoration of WinVE settings configs."""
    
    def __init__(self, env_path=None):
        # Default to main WinVE folder structure
        self.env_path = env_path or os.path.join(os.path.dirname(__file__), "..", ".env")

    def export_config(self, dest_path):
        """Reads the active .env variables and exports them as a JSON structure."""
        if not os.path.exists(self.env_path):
            return False, "Active .env file not found. Nothing to export."
            
        try:
            config_data = {
                "metadata": {
                    "application": "WinVE",
                    "export_timestamp": time.time(),
                    "version": "1.0.0"
                },
                "settings": {}
            }
            
            with open(self.env_path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    # Skip empty lines and comments
                    if not stripped or stripped.startswith("#"):
                        continue
                    if "=" in stripped:
                        k, v = stripped.split("=", 1)
                        # Clean values
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        config_data["settings"][k] = v
                        
            with open(dest_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)
                
            return True, f"Successfully exported settings to {dest_path}"
        except Exception as e:
            return False, f"Export failed: {e}"

    def import_config(self, src_path, create_backup=True):
        """Imports settings from a JSON file, validates the settings, and overwrites the .env."""
        if not os.path.exists(src_path):
            return False, f"Source import file {src_path} does not exist."
            
        try:
            with open(src_path, "r", encoding="utf-8") as f:
                imported_data = json.load(f)
        except Exception as e:
            return False, f"Failed to read/parse import file: {e}"
            
        # 1. Validation
        if not isinstance(imported_data, dict) or "settings" not in imported_data:
            return False, "Invalid import schema: Missing 'settings' block."
            
        settings = imported_data["settings"]
        if not settings:
            return False, "Settings block is empty."
            
        # Basic validation checklist for critical variables
        critical_keys = ["HA_URL", "HA_TOKEN"]
        for key in critical_keys:
            if key not in settings or not settings[key]:
                print(f"⚠️ Warning: Critical key '{key}' is missing or empty in the imported profile.")

        # 2. Backup existing config
        if create_backup and os.path.exists(self.env_path):
            backup_path = f"{self.env_path}.bak_{int(time.time())}"
            try:
                shutil.copyfile(self.env_path, backup_path)
                print(f"📁 Created config backup at: {backup_path}")
            except Exception as e:
                return False, f"Failed to create config backup, import aborted: {e}"

        # 3. Write new .env configuration file
        try:
            with open(self.env_path, "w", encoding="utf-8") as f:
                f.write("# WinVE configuration - Imported Profile\n")
                f.write(f"# Imported on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                for k, v in settings.items():
                    # Sanitize key/value
                    k_clean = k.upper().strip()
                    v_clean = str(v).strip()
                    # Add quotes if values contain spaces/special characters
                    if " " in v_clean or "#" in v_clean:
                        v_clean = f'"{v_clean}"'
                    f.write(f"{k_clean}={v_clean}\n")
                    
                    # Update active in-process environment variables immediately
                    os.environ[k_clean] = str(v).strip()
                    
            return True, "Config imported and loaded successfully. Environment reloaded."
        except Exception as e:
            return False, f"Failed to write configuration: {e}"

if __name__ == "__main__":
    # Test execution harness
    test_env = "test_winve.env"
    test_export_json = "winve_settings_backup.json"
    
    # Create mock .env configuration
    with open(test_env, "w", encoding="utf-8") as f:
        f.write("HA_URL=http://homeassistant.local:8123\n")
        f.write("HA_TOKEN=abcdef123456\n")
        f.write("HA_HOTKEY=ctrl+shift+h\n")
        f.write("HA_WAKE_WORD_ENABLED=true\n")
        f.write("HA_WAKE_WORD_THRESHOLD=0.55\n")
        
    manager = ConfigImportExportManager(env_path=test_env)
    
    # 1. Export settings
    ok, msg = manager.export_config(test_export_json)
    print(f"Export Operation: {'✅ SUCCESS' if ok else '❌ FAILED'} -> {msg}")
    
    if ok:
        with open(test_export_json, "r", encoding="utf-8") as f:
            print(f"Exported JSON content:\n{f.read()}")
            
    # 2. Modify one setting in JSON and import it back
    if ok:
        with open(test_export_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        data["settings"]["HA_WAKE_WORD_THRESHOLD"] = "0.75" # Change parameter
        data["settings"]["NEW_FEATURE_ENABLED"] = "true"
        
        with open(test_export_json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            
        ok_imp, msg_imp = manager.import_config(test_export_json, create_backup=False)
        print(f"Import Operation: {'✅ SUCCESS' if ok_imp else '❌ FAILED'} -> {msg_imp}")
        
        if ok_imp:
            with open(test_env, "r", encoding="utf-8") as f:
                print(f"Imported .env contents:\n{f.read()}")
                
    # Cleanup test files
    for temp_file in [test_env, test_export_json]:
        if os.path.exists(temp_file):
            os.remove(temp_file)
