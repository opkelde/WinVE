"""
Settings Configuration Import/Export Utility for WinVE.
Enables exporting the current .env and JSON configurations to a portable JSON file,
and importing them back safely with schema validation.
"""
import os
import json
import shutil
import time
import logging
import utils

logger = logging.getLogger('haassist')

class ConfigImportExportManager:
    """Handles parsing, backup, validation, and restoration of WinVE settings profiles."""
    
    def __init__(self, env_path=None):
        self.env_path = env_path or utils.get_env_path()
        # Resolve the root app directory
        self.app_dir = os.path.dirname(self.env_path)

    def _get_json_config_path(self, filename):
        """Get the absolute path for a config file in the app directory."""
        return os.path.join(self.app_dir, filename)

    def export_config(self, dest_path) -> tuple:
        """
        Reads the active .env variables and optional JSON configurations and exports them.
        Returns a tuple: (success: bool, message: str)
        """
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
            
            # 1. Read .env file
            with open(self.env_path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    # Skip empty lines and comments
                    if not stripped or stripped.startswith("#"):
                        continue
                    if "=" in stripped:
                        k, v = stripped.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        config_data["settings"][k] = v
            
            # 2. Read optional script triggers config
            triggers_path = self._get_json_config_path("script_triggers.json")
            if os.path.exists(triggers_path):
                try:
                    with open(triggers_path, "r", encoding="utf-8") as f:
                        config_data["script_triggers"] = json.load(f)
                    logger.info("Export: bundled script_triggers.json")
                except Exception as e:
                    logger.warning(f"Export: failed to read script_triggers.json: {e}")

            # 3. Read optional spells config
            spells_path = self._get_json_config_path("spells_config.json")
            if os.path.exists(spells_path):
                try:
                    with open(spells_path, "r", encoding="utf-8") as f:
                        config_data["spells"] = json.load(f)
                    logger.info("Export: bundled spells_config.json")
                except Exception as e:
                    logger.warning(f"Export: failed to read spells_config.json: {e}")

            # Save export to destination
            with open(dest_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)
                
            return True, f"Successfully exported settings to {os.path.basename(dest_path)}"
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False, f"Export failed: {str(e)}"

    def import_config(self, src_path, create_backup=True) -> tuple:
        """
        Imports settings from a JSON file, validates the settings, and overwrites local config.
        Returns a tuple: (success: bool, message: str)
        """
        if not os.path.exists(src_path):
            return False, f"Source import file {src_path} does not exist."
            
        try:
            with open(src_path, "r", encoding="utf-8") as f:
                imported_data = json.load(f)
        except Exception as e:
            return False, f"Failed to parse import file: {str(e)}"
            
        # 1. Validation
        if not isinstance(imported_data, dict) or "settings" not in imported_data:
            return False, "Invalid import schema: Missing 'settings' block."
            
        settings = imported_data["settings"]
        if not settings:
            return False, "Settings block is empty."
            
        # 2. Backup existing config
        if create_backup and os.path.exists(self.env_path):
            backup_path = f"{self.env_path}.bak_{int(time.time())}"
            try:
                shutil.copyfile(self.env_path, backup_path)
                logger.info(f"Created config backup at: {backup_path}")
            except Exception as e:
                return False, f"Failed to create config backup: {str(e)}"

        # 3. Write imported .env configuration file
        try:
            # We recreate the env file with clear sections
            env_content = "# WinVE Desktop Settings - Imported Profile\n"
            env_content += f"# Imported on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            for k, v in settings.items():
                k_clean = k.upper().strip()
                v_clean = str(v).strip()
                if " " in v_clean or "#" in v_clean:
                    v_clean = f'"{v_clean}"'
                env_content += f"{k_clean}={v_clean}\n"
                
                # Update active in-process environment variables immediately
                os.environ[k_clean] = str(v).strip()
                
            with open(self.env_path, "w", encoding="utf-8") as f:
                f.write(env_content)
                
        except Exception as e:
            return False, f"Failed to write .env configuration: {str(e)}"

        # 4. Import optional script triggers config
        if "script_triggers" in imported_data:
            triggers_path = self._get_json_config_path("script_triggers.json")
            try:
                with open(triggers_path, "w", encoding="utf-8") as f:
                    json.dump(imported_data["script_triggers"], f, indent=4)
                logger.info("Import: restored script_triggers.json")
            except Exception as e:
                logger.error(f"Import: failed to write script_triggers.json: {e}")

        # 5. Import optional spells config
        if "spells" in imported_data:
            spells_path = self._get_json_config_path("spells_config.json")
            try:
                with open(spells_path, "w", encoding="utf-8") as f:
                    json.dump(imported_data["spells"], f, indent=4)
                logger.info("Import: restored spells_config.json")
            except Exception as e:
                logger.error(f"Import: failed to write spells_config.json: {e}")

        return True, "Profile imported and loaded successfully."
