"""
Prototype Implementation: Custom Wake Word Downloader
Stored in roadmap-temp/ for reference and future integration.
"""
import os
import requests
import logging
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_model_downloader")

class CustomModelDownloader:
    """Handles downloading custom openWakeWord .onnx files from GitHub or public URLs into the local models directory."""
    
    def __init__(self, models_dir: str = None):
        if models_dir is None:
            self.models_dir = os.path.join(os.path.dirname(__file__), "..", "models")
        else:
            self.models_dir = models_dir
            
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Predefined community model directories (e.g. from official openWakeWord repo or similar)
        self.community_base_url = "https://raw.githubusercontent.com/dscripka/openWakeWord/main/openwakeword/resources/models/"

    def download_model(self, model_name: str, custom_url: str = None, on_complete=None):
        """Dispatches model downloader thread."""
        threading.Thread(
            target=self._run_download,
            args=(model_name, custom_url, on_complete),
            daemon=True
        ).start()

    def _run_download(self, model_name: str, custom_url: str = None, on_complete=None):
        # Resolve target model filename
        if not model_name.endswith(".onnx"):
            model_filename = f"{model_name}.onnx"
        else:
            model_filename = model_name
            model_name = os.path.splitext(model_name)[0]
            
        target_path = os.path.join(self.models_dir, model_filename)
        
        # Resolve URL source
        if custom_url:
            url = custom_url
        else:
            # Fallback to fetching standard openWakeWord model
            url = f"{self.community_base_url}{model_filename}"
            
        logger.info(f"Downloading model '{model_name}' from: {url}")
        try:
            # Send GET stream to download file
            response = requests.get(url, stream=True, timeout=30)
            if response.status_code == 200:
                # Save chunks to model folder
                with open(target_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=4096):
                        if chunk:
                            f.write(chunk)
                logger.info(f"Custom model '{model_name}' downloaded successfully to: {target_path}")
                if on_complete:
                    on_complete(True, model_name)
            else:
                logger.error(f"Failed to download model. HTTP status code: {response.status_code}")
                if on_complete:
                    on_complete(False, f"HTTP Error {response.status_code}")
        except Exception as e:
            logger.error(f"Error downloading custom model: {e}")
            if on_complete:
                on_complete(False, str(e))

    def list_local_custom_models(self) -> list:
        """Scan models directory and return list of custom models."""
        if not os.path.exists(self.models_dir):
            return []
        
        # Standard openWakeWord default models we want to filter out if we only want custom ones
        defaults = {"alexa", "hey_jarvis", "hey_mycroft", "hey_rhasspy", "timers", "weather"}
        
        custom_models = []
        for name in os.listdir(self.models_dir):
            if name.endswith(".onnx"):
                base_name = os.path.splitext(name)[0]
                if base_name.lower() not in defaults:
                    custom_models.append(base_name)
        return sorted(custom_models)
