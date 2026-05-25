"""
Prototype Implementation: Custom Script Triggers
Stored in roadmap-temp/ for reference and future integration.
"""
import os
import json
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_script_triggers")

class ScriptTriggerManager:
    """Manages mapping of spoken phrases to local scripts or batch files."""
    
    def __init__(self, config_path=None):
        if config_path is None:
            # Save mapping config inside the user appdata or project root
            self.config_path = os.path.join(os.path.dirname(__file__), "script_triggers.json")
        else:
            self.config_path = config_path
            
        self.triggers = self._load_triggers()

    def _load_triggers(self) -> dict:
        """Load phrase-to-script mapping from configuration file."""
        if not os.path.exists(self.config_path):
            # Create a default configuration template
            default_config = {
                "run compilation": {
                    "script_path": "C:\\Projects\\Glass\\build.bat",
                    "args": [],
                    "description": "Rebuilds WinVE executable package"
                },
                "backup files": {
                    "script_path": "C:\\Scripts\\backup.py",
                    "args": ["--daily"],
                    "description": "Executes daily backup routine"
                }
            }
            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(default_config, f, indent=4)
                logger.info(f"Created default script trigger config at {self.config_path}")
                return default_config
            except Exception as e:
                logger.error(f"Failed to write default triggers: {e}")
                return {}
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading script trigger config: {e}")
            return {}

    def check_and_execute(self, command_text: str) -> bool:
        """Scan command text. If a script trigger phrase is found, run it."""
        cleaned_cmd = command_text.lower().strip()
        
        for phrase, info in self.triggers.items():
            if phrase in cleaned_cmd:
                script_path = info.get("script_path")
                args = info.get("args", [])
                
                logger.info(f"Custom Script Trigger Matched: '{phrase}'")
                if not os.path.exists(script_path):
                    logger.error(f"Script path does not exist: {script_path}")
                    return False
                
                self._run_script_async(script_path, args)
                return True
                
        return False

    def _run_script_async(self, path: str, args: list):
        """Execute script asynchronously to avoid blocking the voice assistant thread."""
        import threading
        
        def runner():
            try:
                logger.info(f"Running script: {path} with args: {args}")
                ext = os.path.splitext(path)[1].lower()
                
                # Choose shell runner based on extension
                if ext in (".bat", ".cmd"):
                    # Windows Batch files
                    result = subprocess.run([path] + args, capture_output=True, text=True, check=True)
                elif ext == ".ps1":
                    # PowerShell scripts
                    result = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", path] + args, 
                                            capture_output=True, text=True, check=True)
                elif ext == ".py":
                    # Python scripts
                    result = subprocess.run(["python", path] + args, capture_output=True, text=True, check=True)
                else:
                    # Generic executable or shell opening
                    result = subprocess.run([path] + args, capture_output=True, text=True, check=True)
                
                logger.info(f"Script execution finished. Stdout: {result.stdout.strip()}")
                
            except subprocess.CalledProcessError as err:
                logger.error(f"Script execution failed with exit code {err.returncode}")
                logger.error(f"Stderr: {err.stderr}")
            except Exception as ex:
                logger.error(f"Unexpected error running script: {ex}")

        # Run script in a separate thread so the UI/voice loop stays interactive
        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        
    def add_trigger(self, phrase: str, script_path: str, args: list = None, description: str = ""):
        """Add new voice trigger mapping and save config."""
        self.triggers[phrase] = {
            "script_path": script_path,
            "args": args or [],
            "description": description
        }
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.triggers, f, indent=4)
            logger.info(f"Added custom script trigger for '{phrase}' successfully.")
        except Exception as e:
            logger.error(f"Failed to save triggers: {e}")
