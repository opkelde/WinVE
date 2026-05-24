"""
Tests for wake_word_detector module.
"""
import pytest
import os
import tempfile
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import wake_word_detector


class TestWakeWordDetector:
    """Test cases for WakeWordDetector class."""
    
    @patch.dict('os.environ', {
        'HA_WAKE_WORD_ENABLED': 'true',
        'HA_WAKE_WORD_MODELS': 'alexa,jarvis',
        'HA_WAKE_WORD_THRESHOLD': '0.6'
    })
    def test_init_enabled(self):
        """Test WakeWordDetector initialization when enabled."""
        callback = Mock()
        
        with patch('wake_word_detector.WakeWordDetector._init_openwakeword'):
            detector = wake_word_detector.WakeWordDetector(callback)
            
            assert detector.enabled is True
            assert detector.detection_callback == callback
            assert detector.detection_threshold == 0.6
            assert detector.selected_models == ['alexa', 'jarvis']
            assert detector.sample_rate == 16000
    
    @patch.dict('os.environ', {
        'HA_WAKE_WORD_ENABLED': 'false'
    })
    def test_init_disabled(self):
        """Test WakeWordDetector initialization when disabled."""
        detector = wake_word_detector.WakeWordDetector()
        
        assert detector.enabled is False
        assert detector.model is None
        assert detector.is_running is False
    
    @patch.dict('os.environ', {
        'HA_WAKE_WORD_ENABLED': '1',  # Test different true value
        'HA_WAKE_WORD_MODELS': 'alexa'
    })
    def test_init_boolean_parsing(self):
        """Test boolean parsing for different string values."""
        with patch('wake_word_detector.WakeWordDetector._init_openwakeword'):
            detector = wake_word_detector.WakeWordDetector()
            assert detector.enabled is True
    
    def test_get_selected_models_string(self):
        """Test getting selected models from string."""
        with patch.dict('os.environ', {
            'HA_WAKE_WORD_MODELS': 'alexa, jarvis, hal'
        }):
            detector = wake_word_detector.WakeWordDetector()
            models = detector._get_selected_models()
            assert models == ['alexa', 'jarvis', 'hal']
    
    def test_get_selected_models_default(self):
        """Test getting selected models with default."""
        with patch.dict('os.environ', {}, clear=True):
            detector = wake_word_detector.WakeWordDetector()
            models = detector._get_selected_models()
            assert models == ['computer_v2']
    
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_ensure_models_directory_creates(self, mock_exists, mock_makedirs):
        """Test models directory creation."""
        mock_exists.return_value = False
        
        detector = wake_word_detector.WakeWordDetector()
        
        # When creating detector, it calls _ensure_models_directory inside __init__
        mock_makedirs.assert_called_once()
    
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_ensure_models_directory_exists(self, mock_exists, mock_makedirs):
        """Test when models directory already exists."""
        mock_exists.return_value = True
        
        detector = wake_word_detector.WakeWordDetector()
        detector._ensure_models_directory()
        
        mock_makedirs.assert_not_called()
    
    @patch('openwakeword.model.Model')
    @patch('wake_word_detector.check_wake_word_noise_suppression')
    def test_init_openwakeword_success(self, mock_check_noise, mock_model):
        """Test successful OpenWakeWord initialization."""
        mock_check_noise.return_value = True
        mock_model_instance = Mock()
        mock_model.return_value = mock_model_instance
        
        with patch.dict('os.environ', {
            'HA_WAKE_WORD_ENABLED': 'true',
            'HA_WAKE_WORD_NOISE_SUPPRESSION': 'true'
        }):
            detector = wake_word_detector.WakeWordDetector()
            
            assert detector.model == mock_model_instance
            mock_model.assert_called_once()
    
    @patch('openwakeword.model.Model')
    def test_init_openwakeword_import_error(self, mock_model):
        """Test OpenWakeWord initialization with import error."""
        mock_model.side_effect = ImportError("OpenWakeWord not installed")
        
        with patch.dict('os.environ', {'HA_WAKE_WORD_ENABLED': 'true'}):
            detector = wake_word_detector.WakeWordDetector()
            
            assert detector.model is None
            assert detector.enabled is False
    
    @patch('os.path.exists')
    def test_get_model_paths_success(self, mock_exists):
        """Test getting model paths successfully."""
        def side_effect(path):
            if path.endswith(('alexa.onnx', 'jarvis.tflite', 'models')):
                return True
            return False
        mock_exists.side_effect = side_effect
        
        detector = wake_word_detector.WakeWordDetector()
        detector.selected_models = ['alexa', 'jarvis']
        
        paths = detector._get_model_paths()
        
        assert len(paths) == 2
        assert any('alexa.onnx' in path for path in paths)
        assert any('jarvis.tflite' in path for path in paths)
    
    @patch('os.path.exists')
    def test_get_model_paths_missing_models(self, mock_exists):
        """Test getting model paths with missing models."""
        def side_effect(path):
            if path.endswith(('alexa.onnx', 'models')):
                return True
            return False
        mock_exists.side_effect = side_effect
        
        detector = wake_word_detector.WakeWordDetector()
        detector.selected_models = ['alexa', 'nonexistent']
        
        paths = detector._get_model_paths()
        
        assert len(paths) == 1
        assert 'alexa.onnx' in paths[0]
    
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_get_model_paths_no_directory(self, mock_exists, mock_makedirs):
        """Test getting model paths when directory doesn't exist."""
        mock_exists.return_value = False
        
        detector = wake_word_detector.WakeWordDetector()
        detector.selected_models = ['custom_nonexistent_model']
        
        paths = detector._get_model_paths()
        
        assert paths == []
    
    @patch('pyaudio.PyAudio')
    def test_start_detection_success(self, mock_pyaudio):
        """Test successful wake word detection start."""
        mock_audio = Mock()
        mock_pyaudio.return_value = mock_audio
        mock_stream = Mock()
        mock_audio.open.return_value = mock_stream
        
        detector = wake_word_detector.WakeWordDetector()
        detector.enabled = True
        detector.model = Mock()
        
        with patch.object(detector, '_find_microphone', return_value=0):
            result = detector.start_detection()
            
            assert result is True
            assert detector.is_running is True
            assert detector.audio == mock_audio
            assert detector.stream == mock_stream
    
    def test_start_detection_disabled(self):
        """Test starting detection when disabled."""
        detector = wake_word_detector.WakeWordDetector()
        detector.enabled = False
        
        result = detector.start_detection()
        
        assert result is False
        assert detector.is_running is False
    
    def test_start_detection_no_model(self):
        """Test starting detection without model."""
        detector = wake_word_detector.WakeWordDetector()
        detector.enabled = True
        detector.model = None
        
        result = detector.start_detection()
        
        assert result is False
        assert detector.is_running is False
    
    @patch('pyaudio.PyAudio')
    def test_start_detection_already_running(self, mock_pyaudio):
        """Test starting detection when already running."""
        detector = wake_word_detector.WakeWordDetector()
        detector.enabled = True
        detector.model = Mock()
        detector.is_running = True
        
        result = detector.start_detection()
        
        assert result is True
        mock_pyaudio.assert_not_called()
    
    @patch('pyaudio.PyAudio')
    def test_start_detection_audio_error(self, mock_pyaudio):
        """Test starting detection with audio error."""
        mock_pyaudio.side_effect = Exception("Audio error")
        
        detector = wake_word_detector.WakeWordDetector()
        detector.enabled = True
        detector.model = Mock()
        
        result = detector.start_detection()
        
        assert result is False
        assert detector.is_running is False
    
    def test_stop_detection_success(self):
        """Test successful detection stop."""
        detector = wake_word_detector.WakeWordDetector()
        detector.is_running = True
        mock_stream = Mock()
        mock_audio = Mock()
        detector.stream = mock_stream
        detector.audio = mock_audio
        
        detector.stop_detection()
        
        assert detector.is_running is False
        mock_stream.stop_stream.assert_called_once()
        mock_stream.close.assert_called_once()
        mock_audio.terminate.assert_called_once()
    
    def test_stop_detection_not_running(self):
        """Test stopping detection when not running."""
        detector = wake_word_detector.WakeWordDetector()
        detector.is_running = False
        
        # Should not raise exception
        detector.stop_detection()
        
        assert detector.is_running is False
    
    def test_stop_detection_with_errors(self):
        """Test stopping detection with cleanup errors."""
        detector = wake_word_detector.WakeWordDetector()
        detector.is_running = True
        detector.stream = Mock()
        detector.audio = Mock()
        
        # Mock exceptions during cleanup
        detector.stream.stop_stream.side_effect = Exception("Stream error")
        detector.audio.terminate.side_effect = Exception("Audio error")
        
        # Should not raise exceptions
        detector.stop_detection()
        
        assert detector.is_running is False
    
    def test_process_predictions_wake_word_detected(self):
        """Test predictions processing with wake word detection."""
        callback = Mock()
        detector = wake_word_detector.WakeWordDetector(callback)
        detector.detection_threshold = 0.5
        detector.selected_models = ['alexa', 'jarvis']
        
        predictions = {'alexa': 0.7, 'jarvis': 0.3}
        detector._process_predictions(predictions)
        
        callback.assert_called_once_with('alexa', 0.7)
    
    def test_process_predictions_no_detection(self):
        """Test predictions processing without wake word detection."""
        callback = Mock()
        detector = wake_word_detector.WakeWordDetector(callback)
        detector.detection_threshold = 0.5
        detector.selected_models = ['alexa', 'jarvis']
        
        predictions = {'alexa': 0.3, 'jarvis': 0.2}
        detector._process_predictions(predictions)
        
        callback.assert_not_called()
    
    def test_process_predictions_callback_exception(self):
        """Test predictions processing when callback raises an exception."""
        callback = Mock(side_effect=Exception("Callback error"))
        detector = wake_word_detector.WakeWordDetector(callback)
        detector.detection_threshold = 0.5
        detector.selected_models = ['alexa']
        
        # Should not raise exception
        detector._process_predictions({'alexa': 0.7})
    
    def test_get_model_info_enabled(self):
        """Test getting model info when enabled."""
        detector = wake_word_detector.WakeWordDetector()
        detector.enabled = True
        detector.is_running = True
        detector.selected_models = ['alexa', 'jarvis']
        detector.detection_threshold = 0.5
        detector.vad_threshold = 0.3
        detector.noise_suppression = True
        
        with patch.object(detector, '_get_available_models', return_value=['alexa', 'jarvis', 'hal']):
            info = detector.get_model_info()
            
            assert info['enabled'] is True
            assert info['is_running'] is True
            assert info['selected_models'] == ['alexa', 'jarvis']
            assert info['detection_threshold'] == 0.5
            assert info['vad_threshold'] == 0.3
            assert info['noise_suppression'] is True
            assert info['available_models'] == ['alexa', 'jarvis', 'hal']
    
    def test_get_model_info_disabled(self):
        """Test getting model info when disabled."""
        detector = wake_word_detector.WakeWordDetector()
        detector.enabled = False
        
        info = detector.get_model_info()
        
        assert info['enabled'] is False
        assert info['is_running'] is False
        assert info['selected_models'] == []
    
    @patch('os.listdir')
    @patch('os.path.exists')
    def test_get_available_models(self, mock_exists, mock_listdir):
        """Test getting available models."""
        mock_exists.return_value = True
        mock_listdir.return_value = [
            'alexa.onnx', 'alexa.tflite', 
            'jarvis.onnx', 'jarvis.tflite',
            'hal.onnx', 'other.txt'
        ]
        
        detector = wake_word_detector.WakeWordDetector()
        models = detector._get_available_models()
        
        assert 'alexa' in models
        assert 'jarvis' in models
        assert 'hal' in models
        assert 'other' not in models  # Should not include .txt files
    
    @patch('wake_word_detector.utils.get_env')
    @patch('wake_word_detector.WakeWordDetector._init_openwakeword')
    def test_reload_models_success(self, mock_init, mock_get_env):
        """Test successful model reloading."""
        mock_get_env.return_value = True
        detector = wake_word_detector.WakeWordDetector()
        detector.enabled = True
        detector.is_running = True
        detector.model = Mock()
        
        mock_init.reset_mock()
        with patch.object(detector, 'stop_detection'), \
             patch.object(detector, 'start_detection', return_value=True):
            
            result = detector.reload_models()
            
            assert result is True
            mock_init.assert_called_once()
    
    @patch('wake_word_detector.utils.get_env')
    @patch('wake_word_detector.WakeWordDetector._init_openwakeword')
    def test_reload_models_disabled(self, mock_init, mock_get_env):
        """Test model reloading when disabled."""
        mock_get_env.return_value = False
        detector = wake_word_detector.WakeWordDetector()
        detector.enabled = False
        
        mock_init.reset_mock()
        result = detector.reload_models()
        
        assert result is False
        mock_init.assert_not_called()
    
    @patch('wake_word_detector.utils.get_env')
    @patch('wake_word_detector.WakeWordDetector._init_openwakeword')
    def test_reload_models_start_failure(self, mock_init, mock_get_env):
        """Test model reloading with start failure."""
        mock_get_env.return_value = True
        detector = wake_word_detector.WakeWordDetector()
        detector.enabled = True
        detector.is_running = True
        detector.model = Mock()
        
        with patch.object(detector, 'stop_detection'), \
             patch.object(detector, 'start_detection', return_value=False):
            
            result = detector.reload_models()
            
            assert result is False

    def test_get_clean_model_name(self):
        """Test cleaning of model names."""
        from wake_word_detector import get_clean_model_name
        assert get_clean_model_name("alexa") == "alexa"
        assert get_clean_model_name("alexa.onnx") == "alexa"
        assert get_clean_model_name("hey_jarvis.tflite") == "hey_jarvis"
        assert get_clean_model_name("c:\\path\\to\\models\\alexa.onnx") == "alexa"
        assert get_clean_model_name("/path/to/models/hey_mycroft.tflite") == "hey_mycroft"

    @patch('os.makedirs')
    @patch('os.path.exists', return_value=False)
    def test_get_model_paths_default_model_fallback(self, mock_exists, mock_makedirs):
        """Test fallback to default models when not found locally."""
        detector = wake_word_detector.WakeWordDetector()
        detector.selected_models = ['alexa', 'hey jarvis', 'custom_nonexistent']
        
        paths = detector._get_model_paths()
        
        # 'alexa' and 'hey jarvis' (normalized to 'hey_jarvis') are default models,
        # 'custom_nonexistent' is not.
        assert len(paths) == 2
        assert 'alexa' in paths
        assert 'hey_jarvis' in paths




def test_validate_wake_word_config():
    """Test wake word configuration validation."""
    with patch.dict('os.environ', {
        'HA_WAKE_WORD_ENABLED': 'true',
        'HA_WAKE_WORD_MODELS': 'alexa,jarvis',
        'HA_WAKE_WORD_THRESHOLD': '0.5'
    }):
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=['alexa.onnx', 'jarvis.tflite']):
            
            issues = wake_word_detector.validate_wake_word_config()
            
            assert len(issues) == 0

def test_validate_wake_word_config_disabled():
    """Test wake word configuration validation when disabled."""
    with patch.dict('os.environ', {
        'HA_WAKE_WORD_ENABLED': 'false'
    }):
        issues = wake_word_detector.validate_wake_word_config()
        
        assert len(issues) == 0

def test_validate_wake_word_config_missing_models():
    """Test wake word configuration validation with missing models."""
    with patch.dict('os.environ', {
        'HA_WAKE_WORD_ENABLED': 'true',
        'HA_WAKE_WORD_MODELS': 'alexa,nonexistent'
    }):
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=['alexa.onnx']):
            
            issues = wake_word_detector.validate_wake_word_config()
            
            assert len(issues) > 0
            assert any('nonexistent' in issue for issue in issues)

def test_validate_wake_word_config_invalid_threshold():
    """Test wake word configuration validation with invalid threshold."""
    with patch.dict('os.environ', {
        'HA_WAKE_WORD_ENABLED': 'true',
        'HA_WAKE_WORD_THRESHOLD': '1.5'  # Invalid threshold > 1.0
    }):
        issues = wake_word_detector.validate_wake_word_config()
        
        assert len(issues) > 0
        assert any('threshold' in issue.lower() for issue in issues)