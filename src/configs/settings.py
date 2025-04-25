# settings.py
import cv2
import logging
import os
import pickle
from src.configs.config import Config

logger = logging.getLogger(__name__)

class Settings:
    def __init__(self):
        self._camera_index = 0
        self._alert_volume = 50
        self._alert_sound_file = None  
        self.config = Config()
        self.sound_dir = self.config.SOUND_DIR
        self.settings_file = self.config.SETTINGS_FILE
        self.load() 

    @property
    def camera_index(self):
        return self._camera_index

    @camera_index.setter
    def camera_index(self, value):
        self._camera_index = value

    @property
    def alert_volume(self):
        return self._alert_volume

    @alert_volume.setter
    def alert_volume(self, value):
        self._alert_volume = max(0, min(100, value))

    @property
    def alert_sound_file(self):
        return self._alert_sound_file

    @alert_sound_file.setter
    def alert_sound_file(self, value):
        self._alert_sound_file = value

    def get_available_cameras(self):
        """Return a list of available camera indices."""
        index = 0
        cameras = []
        while True:
            cap = cv2.VideoCapture(index)
            if not cap.isOpened():
                break
            cameras.append(index)
            cap.release()
            index += 1
        return cameras

    def get_available_sounds(self):
        """Return a list of available sound files in the sounds directory."""
        os.makedirs(self.sound_dir, exist_ok=True)
        sound_files = ['Mặc định']  # Default sound option
        for file in os.listdir(self.sound_dir):
            if file.lower().endswith(('.wav', '.mp3')):
                sound_files.append(file)
        return sound_files

    def save(self):
        """Save settings to a file."""
        try:
            os.makedirs('data', exist_ok=True)
            with open(self.settings_file, 'wb') as f:
                pickle.dump({
                    'camera_index': self._camera_index,
                    'alert_volume': self._alert_volume,
                    'alert_sound_file': self._alert_sound_file
                }, f)
            logger.info("Settings saved successfully")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def load(self):
        """Load settings from a file."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'rb') as f:
                    data = pickle.load(f)
                    self._camera_index = data.get('camera_index', 0)
                    self._alert_volume = data.get('alert_volume', 50)
                    self._alert_sound_file = data.get('alert_sound_file', None)
                logger.info("Settings loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")