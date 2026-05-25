"""
Unit tests for settings configuration import and export utility.
"""
import os
import json
import pytest
from unittest.mock import Mock, patch
from config_import_export import ConfigImportExportManager

@pytest.mark.unit
def test_config_export_success(tmp_path):
    # Setup mock env file
    mock_env = tmp_path / ".env"
    mock_env.write_text("HA_HOST=localhost:8123\nHA_TOKEN=test_token\nDEBUG=true\n", encoding="utf-8")
    
    # Setup optional config files
    triggers_file = tmp_path / "script_triggers.json"
    triggers_file.write_text(json.dumps({"test trigger": "run script"}), encoding="utf-8")
    
    spells_file = tmp_path / "spells_config.json"
    spells_file.write_text(json.dumps({"lumos": "light on"}), encoding="utf-8")
    
    manager = ConfigImportExportManager(env_path=str(mock_env))
    dest_backup = tmp_path / "winve_backup.json"
    
    # Run export
    success, msg = manager.export_config(str(dest_backup))
    assert success is True
    assert dest_backup.exists()
    
    # Read backup
    with open(dest_backup, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert data["metadata"]["application"] == "WinVE"
    assert data["settings"]["HA_HOST"] == "localhost:8123"
    assert data["settings"]["HA_TOKEN"] == "test_token"
    assert data["settings"]["DEBUG"] == "true"
    assert data["script_triggers"]["test trigger"] == "run script"
    assert data["spells"]["lumos"] == "light on"

@pytest.mark.unit
def test_config_import_validation_failures(tmp_path):
    mock_env = tmp_path / ".env"
    manager = ConfigImportExportManager(env_path=str(mock_env))
    
    # 1. Non-existent file
    success, msg = manager.import_config(str(tmp_path / "does_not_exist.json"))
    assert success is False
    assert "does not exist" in msg
    
    # 2. Invalid schema (missing settings)
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text(json.dumps({"metadata": {}}), encoding="utf-8")
    success, msg = manager.import_config(str(invalid_file))
    assert success is False
    assert "settings" in msg

@pytest.mark.unit
def test_config_import_success(tmp_path):
    mock_env = tmp_path / ".env"
    mock_env.write_text("HA_HOST=old_host\n", encoding="utf-8")
    
    backup_payload = {
        "metadata": {
            "application": "WinVE",
            "version": "1.0.0"
        },
        "settings": {
            "HA_HOST": "new_host",
            "HA_TOKEN": "new_token",
            "HA_SUPPRESS_FULLSCREEN": "true"
        },
        "script_triggers": {
            "rebuild": "build.bat"
        }
    }
    
    src_file = tmp_path / "backup.json"
    src_file.write_text(json.dumps(backup_payload), encoding="utf-8")
    
    manager = ConfigImportExportManager(env_path=str(mock_env))
    
    # Run import (verify that no .env.bak_* backup files are created)
    success, msg = manager.import_config(str(src_file), create_backup=True)
    assert success is True
    
    # Verify no .env.bak_* files were created
    import os
    bak_files = [f for f in os.listdir(tmp_path) if f.startswith(".env.bak_")]
    assert len(bak_files) == 0
    
    # Check env changes
    env_content = mock_env.read_text(encoding="utf-8")
    assert "HA_HOST=new_host" in env_content
    assert "HA_TOKEN=new_token" in env_content
    assert "HA_SUPPRESS_FULLSCREEN=true" in env_content
    
    # Check script triggers file was written
    triggers_file = tmp_path / "script_triggers.json"
    assert triggers_file.exists()
    with open(triggers_file, "r") as f:
        data = json.load(f)
    assert data["rebuild"] == "build.bat"
