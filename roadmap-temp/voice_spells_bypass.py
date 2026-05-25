"""
Voice Spells Bypass System for WinVE.
Allows defining specific key phrases ("spells" like "Lumos" or "Nox") that bypass
the standard wake-word-first pipeline and execute custom local actions or 
Home Assistant service calls directly. Includes dynamic add/remove/toggle settings APIs.
"""
import json
import os
import re

class VoiceSpellsManager:
    """Manages creation, state toggling, deletion, and parsing of bypass 'spells'."""
    
    def __init__(self, config_path=None):
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), "..", "spells_config.json")
        self.spells = {}
        self.load_spells()
        
    def load_spells(self):
        """Loads spells from the local configuration file or initializes default ones."""
        if not os.path.exists(self.config_path):
            # Create default spells
            self.spells = {
                "lumos": {
                    "action": "ha_service_call",
                    "target": "light.turn_on",
                    "enabled": True,
                    "description": "Turn on all primary room lights"
                },
                "nox": {
                    "action": "ha_service_call",
                    "target": "light.turn_off",
                    "enabled": True,
                    "description": "Turn off all primary room lights"
                },
                "system lock": {
                    "action": "shell_command",
                    "target": "rundll32.exe user32.dll,LockWorkStation",
                    "enabled": True,
                    "description": "Bypass wake word to lock Windows immediately"
                }
            }
            self.save_spells()
        else:
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.spells = json.load(f)
            except Exception as e:
                print(f"Error loading spells configuration: {e}")
                self.spells = {}

    def save_spells(self):
        """Saves current spells back to the configuration file."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.spells, f, indent=4)
        except Exception as e:
            print(f"Error saving spells configuration: {e}")

    def add_spell(self, phrase, action_type, target, description="", enabled=True):
        """Adds a new spell or overwrites an existing one."""
        phrase_key = phrase.lower().strip()
        if not phrase_key:
            return False, "Spell phrase cannot be empty"
            
        self.spells[phrase_key] = {
            "action": action_type,
            "target": target,
            "enabled": enabled,
            "description": description
        }
        self.save_spells()
        return True, f"Spell '{phrase_key}' registered successfully."

    def remove_spell(self, phrase):
        """Deletes a spell by its trigger phrase."""
        phrase_key = phrase.lower().strip()
        if phrase_key in self.spells:
            del self.spells[phrase_key]
            self.save_spells()
            return True, f"Spell '{phrase_key}' removed."
        return False, "Spell not found"

    def toggle_spell(self, phrase, enabled=None):
        """Enables or disables a spell."""
        phrase_key = phrase.lower().strip()
        if phrase_key in self.spells:
            if enabled is None:
                # Toggle
                self.spells[phrase_key]["enabled"] = not self.spells[phrase_key]["enabled"]
            else:
                self.spells[phrase_key]["enabled"] = bool(enabled)
            self.save_spells()
            status = "enabled" if self.spells[phrase_key]["enabled"] else "disabled"
            return True, f"Spell '{phrase_key}' is now {status}."
        return False, "Spell not found"

    def evaluate_audio_transcript(self, transcript_text):
        """
        Parses transcripts from local speech recognition (e.g. continuous whispered/VAD streams)
        to identify active spells. Bypasses normal wake-word validation.
        """
        cleaned_text = transcript_text.lower().strip()
        
        for spell_phrase, info in self.spells.items():
            if not info.get("enabled", False):
                continue
                
            # Direct match check or regex word boundary check
            pattern = rf"\b{re.escape(spell_phrase)}\b"
            if re.search(pattern, cleaned_text):
                print(f"🪄 Spell Triggered! Phrase matched: '{spell_phrase}'")
                return {
                    "matched": True,
                    "phrase": spell_phrase,
                    "action": info["action"],
                    "target": info["target"]
                }
                
        return {"matched": False}

    def execute_spell_action(self, spell_data):
        """Executes the action associated with the triggered spell."""
        action_type = spell_data.get("action")
        target = spell_data.get("target")
        
        if action_type == "shell_command":
            import subprocess
            try:
                subprocess.Popen(target, shell=True)
                return True, f"Executed command: {target}"
            except Exception as e:
                return False, f"Command execution error: {e}"
                
        elif action_type == "ha_service_call":
            # Mock or invoke Home Assistant WebSocket service calls
            # Real code will push this payload to HomeAssistantClient
            print(f"Sending service call {target} to Home Assistant...")
            return True, f"Mocked Home Assistant service call for {target}"
            
        return False, f"Unknown action type: {action_type}"

if __name__ == "__main__":
    manager = VoiceSpellsManager(config_path="spells_demo_config.json")
    
    # 1. Show loaded default spells
    print("Initial spells list:")
    print(json.dumps(manager.spells, indent=2))
    
    # 2. Add custom spell
    manager.add_spell("alohomora", "shell_command", "explorer.exe", "Unlock and open explorer folder")
    print("\nAfter adding 'alohomora':")
    print(json.dumps(manager.spells, indent=2))
    
    # 3. Simulate continuous audio transcript evaluations
    transcripts = [
        "is anyone home?",
        "lumos maximo",
        "lumos",
        "please open explorer using alohomora"
    ]
    
    print("\n--- Simulating Voice Spell Audits ---")
    for phrase in transcripts:
        result = manager.evaluate_audio_transcript(phrase)
        if result["matched"]:
            ok, msg = manager.execute_spell_action(result)
            print(f"Transcript: '{phrase}' -> MATCHED! -> Action result: {msg}")
        else:
            print(f"Transcript: '{phrase}' -> No spell matches")
            
    # Cleanup demo files
    if os.path.exists("spells_demo_config.json"):
        os.remove("spells_demo_config.json")
