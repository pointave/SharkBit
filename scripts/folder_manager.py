import os
import json
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import QStandardPaths

class FolderManager:
    def __init__(self, main_app):
        self.main_app = main_app
        self.config_file = "folder_settings.json"
        self.audio_folders = []
        self.video_folders = []
        self.favorite_audio_folders = []
        self.favorite_video_folders = []
        self.default_audio_folder = ""
        self.default_video_folder = ""
        self.load_settings()
        
    def load_settings(self):
        """Load folder settings from JSON file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.audio_folders = data.get('audio_folders', [])
                    self.video_folders = data.get('video_folders', [])
                    self.favorite_audio_folders = data.get('favorite_audio_folders', [])
                    self.favorite_video_folders = data.get('favorite_video_folders', [])
                    self.default_audio_folder = data.get('default_audio_folder', '')
                    self.default_video_folder = data.get('default_video_folder', '')
            except Exception as e:
                print(f"Error loading folder settings: {e}")
        
        # Set default system folders if not configured
        if not self.default_audio_folder:
            self.default_audio_folder = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.MusicLocation)
        if not self.default_video_folder:
            self.default_video_folder = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.MoviesLocation)
    
    def save_settings(self):
        """Save folder settings to JSON file"""
        data = {
            'audio_folders': self.audio_folders,
            'video_folders': self.video_folders,
            'favorite_audio_folders': self.favorite_audio_folders,
            'favorite_video_folders': self.favorite_video_folders,
            'default_audio_folder': self.default_audio_folder,
            'default_video_folder': self.default_video_folder
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving folder settings: {e}")
    
    def get_system_folders(self):
        """Get standard system folders"""
        return {
            "Music": QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MusicLocation),
            "Videos": QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MoviesLocation),
            "Pictures": QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation),
            "Documents": QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation),
            "Downloads": QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        }
    
    def add_folder(self, folder_type, path, is_favorite=False):
        """Add a folder to the specified type (audio/video)"""
        if not path or not os.path.isdir(path):
            return False
            
        path = os.path.normpath(path)
        
        if folder_type == 'audio':
            if path not in self.audio_folders:
                self.audio_folders.append(path)
            if is_favorite and path not in self.favorite_audio_folders:
                self.favorite_audio_folders.append(path)
        else:  # video
            if path not in self.video_folders:
                self.video_folders.append(path)
            if is_favorite and path not in self.favorite_video_folders:
                self.favorite_video_folders.append(path)
                
        self.save_settings()
        return True
    
    def remove_folder(self, folder_type, path):
        """Remove a folder from the specified type (audio/video)"""
        path = os.path.normpath(path)
        
        if folder_type == 'audio':
            if path in self.audio_folders:
                self.audio_folders.remove(path)
            if path in self.favorite_audio_folders:
                self.favorite_audio_folders.remove(path)
            if self.default_audio_folder == path:
                self.default_audio_folder = ""
        else:  # video
            if path in self.video_folders:
                self.video_folders.remove(path)
            if path in self.favorite_video_folders:
                self.favorite_video_folders.remove(path)
            if self.default_video_folder == path:
                self.default_video_folder = ""
                
        self.save_settings()
    
    def toggle_favorite(self, folder_type, path):
        """Toggle favorite status for a folder"""
        path = os.path.normpath(path)
        
        if folder_type == 'audio':
            if path in self.favorite_audio_folders:
                self.favorite_audio_folders.remove(path)
            else:
                if path not in self.audio_folders:
                    self.audio_folders.append(path)
                self.favorite_audio_folders.append(path)
        else:  # video
            if path in self.favorite_video_folders:
                self.favorite_video_folders.remove(path)
            else:
                if path not in self.video_folders:
                    self.video_folders.append(path)
                self.favorite_video_folders.append(path)
                
        self.save_settings()
    
    def set_default_folder(self, folder_type, path):
        """Set the default folder for audio or video"""
        path = os.path.normpath(path)
        
        if folder_type == 'audio':
            if path not in self.audio_folders:
                self.audio_folders.append(path)
            self.default_audio_folder = path
        else:  # video
            if path not in self.video_folders:
                self.video_folders.append(path)
            self.default_video_folder = path
            
        self.save_settings()
    
    def get_current_folders(self, audio_mode=False):
        """Get the appropriate folders based on current mode"""
        if audio_mode:
            return {
                'current': self.main_app.folder_path if hasattr(self.main_app, 'folder_path') else "",
                'default': self.default_audio_folder,
                'favorites': self.favorite_audio_folders,
                'recent': [f for f in self.audio_folders if f not in self.favorite_audio_folders]
            }
        else:
            return {
                'current': self.main_app.folder_path if hasattr(self.main_app, 'folder_path') else "",
                'default': self.default_video_folder,
                'favorites': self.favorite_video_folders,
                'recent': [f for f in self.video_folders if f not in self.favorite_video_folders]
            }
