"""
Prototype Implementation: Local Audio Caching System
Stored in roadmap-temp/ for reference and future integration.
"""
import os
import requests
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_audio_cache")

class LocalAudioCacheManager:
    """Caches TTS voice output files and dynamic media streams locally to decrease latency and allow offline playback."""
    
    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            self.cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache", "audio")
        else:
            self.cache_dir = cache_dir
            
        os.makedirs(self.cache_dir, exist_ok=True)
        self.max_cache_size_bytes = 100 * 1024 * 1024 # 100 MB max size
        
    def get_cached_file(self, url: str) -> str:
        """Downloads audio file from URL, caches it locally, and returns the path."""
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        # Resolve extension (usually .mp3 or .wav)
        ext = os.path.splitext(url.split("?")[0])[1] or ".mp3"
        cached_filepath = os.path.join(self.cache_dir, f"{url_hash}{ext}")
        
        # Check if already cached
        if os.path.exists(cached_filepath):
            logger.info(f"Audio cache hit: {cached_filepath}")
            # Update access time for LRU eviction calculation
            os.utime(cached_filepath, None)
            return cached_filepath
            
        # Download and cache
        logger.info(f"Audio cache miss. Downloading from: {url}")
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                with open(cached_filepath, "wb") as f:
                    f.write(response.content)
                logger.info(f"Saved audio file to cache: {cached_filepath}")
                
                # Perform clean up if cache exceeded size limit
                self._prune_cache()
                return cached_filepath
        except Exception as e:
            logger.error(f"Failed to cache remote audio file: {e}")
            
        return ""

    def cache_tts_text(self, text: str, audio_bytes: bytes) -> str:
        """Caches raw TTS bytes generated from a text sentence."""
        text_hash = hashlib.md5(text.lower().strip().encode("utf-8")).hexdigest()
        cached_filepath = os.path.join(self.cache_dir, f"tts_{text_hash}.wav")
        
        try:
            with open(cached_filepath, "wb") as f:
                f.write(audio_bytes)
            logger.info(f"Saved TTS output to local cache: {cached_filepath}")
            self._prune_cache()
            return cached_filepath
        except Exception as e:
            logger.error(f"Failed to write TTS cache: {e}")
            return ""

    def _prune_cache(self):
        """Least Recently Used (LRU) cache pruning logic."""
        files = []
        total_size = 0
        
        for name in os.listdir(self.cache_dir):
            filepath = os.path.join(self.cache_dir, name)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append((filepath, stat.st_atime, stat.st_size))
                total_size += stat.st_size
                
        if total_size <= self.max_cache_size_bytes:
            return
            
        logger.info("Cache size exceeded. Pruning least recently used audio files...")
        # Sort by access time ascending (oldest first)
        files.sort(key=lambda x: x[1])
        
        for filepath, _, size in files:
            if total_size <= self.max_cache_size_bytes:
                break
            try:
                os.remove(filepath)
                total_size -= size
                logger.info(f"Evicted from cache: {filepath}")
            except Exception as e:
                logger.error(f"Failed to delete cached file: {e}")

    def clear_cache(self):
        """Clears all cached audio files."""
        for name in os.listdir(self.cache_dir):
            filepath = os.path.join(self.cache_dir, name)
            if os.path.isfile(filepath):
                try:
                    os.remove(filepath)
                except Exception as e:
                    logger.error(f"Failed to delete cached file: {e}")
        logger.info("Audio cache cleared.")
