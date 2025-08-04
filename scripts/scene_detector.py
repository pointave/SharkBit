import os
import cv2
import numpy as np
import json
import hashlib
from typing import List, Tuple, Optional
import threading
from PyQt6.QtCore import QObject, pyqtSignal

class SceneDetector(QObject):
    """Scene detection using content-based analysis"""
    
    # Signals for progress updates
    progress_updated = pyqtSignal(int)  # Progress percentage
    scenes_detected = pyqtSignal(list)  # List of scene frame positions
    detection_finished = pyqtSignal()   # Detection completed
    
    def __init__(self, threshold=40.0, min_scene_len=30, sample_fps=.1, target_megapixels=0.5):
        super().__init__()
        self.threshold = threshold
        self.min_scene_len = min_scene_len
        self.sample_fps = sample_fps  # FPS to sample at for scene detection
        self.target_megapixels = target_megapixels  # Target resolution in megapixels (0.5 = 500,000 pixels)
        self.scenes = []  # List of (start_frame, end_frame) tuples
        self.stop_detection = False  # Flag to stop detection
        
    def detect_scenes(self, video_path: str) -> List[Tuple[int, int]]:
        """
        Detect scenes in a video file using content-based analysis.
        Returns a list of (start_frame, end_frame) tuples.
        """
        if not os.path.exists(video_path):
            print(f"Video file not found: {video_path}")
            return []
            
        # Try to load from cache first
        cached_scenes = self.load_scenes_from_cache(video_path)
        if cached_scenes is not None:
            self.scenes = cached_scenes
            # Emit signals for cached scenes
            self.scenes_detected.emit(cached_scenes)
            self.detection_finished.emit()
            return cached_scenes
            
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Could not open video: {video_path}")
            return []
            
        try:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            if total_frames <= 0:
                print("Invalid frame count")
                return []
                
            # Calculate frame sampling interval
            if fps > 0:
                sample_interval = int(fps / self.sample_fps)
            else:
                sample_interval = 15  # Default to every 15 frames if FPS is unknown
                
            # Calculate minimum frame difference based on min_scene_len
            min_frame_diff = int(self.min_scene_len * self.sample_fps) if self.sample_fps > 0 else 15
            
            scenes = []
            prev_frame = None
            scene_start = 0
            frame_count = 0
            sampled_frame_count = 0
            
            # Get original frame dimensions
            original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Calculate target dimensions - only resize if original is 0.7MP or larger
            target_pixels = int(self.target_megapixels * 1000000)  # Convert to pixels (0.5MP)
            resize_threshold = 700000  # 0.7 megapixels
            original_pixels = original_width * original_height
            
            if original_pixels >= resize_threshold:
                # Calculate scale factor to reach target megapixels
                scale_factor = (target_pixels / original_pixels) ** 0.5
                target_width = int(original_width * scale_factor)
                target_height = int(original_height * scale_factor)
            else:
                # If original is smaller than 0.7MP, use original size
                target_width = original_width
                target_height = original_height
            
            print(f"Detecting scenes in {video_path}")
            print(f"Total frames: {total_frames}, Video FPS: {fps}, Sampling at {self.sample_fps} FPS (every {sample_interval} frames)")
            print(f"Original resolution: {original_width}x{original_height} ({original_pixels/1000000:.1f}MP), Processing at: {target_width}x{target_height} ({target_width*target_height/1000000:.1f}MP)")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # Only process every Nth frame based on sample_fps
                if frame_count % sample_interval == 0:
                    # Resize frame for faster processing
                    if target_width != original_width or target_height != original_height:
                        frame = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)
                    
                    # Convert to grayscale for comparison
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    
                    if prev_frame is not None:
                        # Calculate frame difference
                        diff = cv2.absdiff(gray, prev_frame)
                        mean_diff = np.mean(diff)
                        
                        # Check if this is a scene change
                        if mean_diff > self.threshold:
                            # Ensure minimum scene length
                            if sampled_frame_count - scene_start >= min_frame_diff:
                                # Convert sampled frame position back to actual frame position
                                actual_start_frame = scene_start * sample_interval
                                actual_end_frame = sampled_frame_count * sample_interval
                                scenes.append((actual_start_frame, actual_end_frame))
                                scene_start = sampled_frame_count
                                
                    prev_frame = gray
                    sampled_frame_count += 1
                    
                    # Check if we should stop
                    if self.stop_detection:
                        print("Scene detection stopped by user")
                        cap.release()
                        self.detection_finished.emit()
                        return []
                        
                    # Emit progress updates
                    if sampled_frame_count % 10 == 0:  # Update every 10 sampled frames
                        progress = int((frame_count / total_frames) * 100)
                        self.progress_updated.emit(progress)
                        
                frame_count += 1
                    
            # Add the last scene
            if sampled_frame_count - scene_start >= min_frame_diff:
                # Convert sampled frame position back to actual frame position
                actual_start_frame = scene_start * sample_interval
                actual_end_frame = frame_count  # Use the actual end frame
                scenes.append((actual_start_frame, actual_end_frame))
                
            # If no scenes detected, create one scene for the entire video
            if not scenes:
                scenes = [(0, frame_count)]
                
            self.scenes = scenes
            print(f"Detected {len(scenes)} scenes")
            
            # Save to cache
            self.save_scenes_to_cache(video_path, scenes)
            
            # Emit final signals
            self.scenes_detected.emit(scenes)
            self.detection_finished.emit()
            
            return scenes
            
        finally:
            cap.release()
    
    def detect_scenes_async(self, video_path: str):
        """Run scene detection in a background thread"""
        self.stop_detection = False  # Reset stop flag when starting new detection
        thread = threading.Thread(target=self.detect_scenes, args=(video_path,), daemon=True)
        thread.start()
        return thread
    
    def get_scene_at_frame(self, frame_number: int) -> Optional[int]:
        """Get the scene index for a given frame number"""
        for i, (start, end) in enumerate(self.scenes):
            if start <= frame_number < end:
                return i
        return None
    
    def get_scene_start_frame(self, scene_index: int) -> Optional[int]:
        """Get the start frame of a scene by index"""
        if 0 <= scene_index < len(self.scenes):
            return self.scenes[scene_index][0]
        return None
    
    def get_scene_end_frame(self, scene_index: int) -> Optional[int]:
        """Get the end frame of a scene by index"""
        if 0 <= scene_index < len(self.scenes):
            return self.scenes[scene_index][1]
        return None
    
    def get_scene_count(self) -> int:
        """Get the total number of detected scenes"""
        return len(self.scenes)
    
    def clear_scenes(self):
        """Clear the detected scenes"""
        self.scenes = []
        
    def _get_video_hash(self, video_path: str) -> str:
        """Generate a hash for the video file based on path, size, and modification time"""
        try:
            stat = os.stat(video_path)
            # Use path, size, and modification time for hash
            hash_data = f"{video_path}_{stat.st_size}_{stat.st_mtime}"
            return hashlib.md5(hash_data.encode()).hexdigest()
        except:
            return hashlib.md5(video_path.encode()).hexdigest()
            
    def _get_cache_file_path(self, video_path: str) -> str:
        """Get the cache file path for a video"""
        video_dir = os.path.dirname(video_path)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        return os.path.join(video_dir, f".scene_cache_{video_name}.json")
        
    def load_scenes_from_cache(self, video_path: str) -> Optional[List[Tuple[int, int]]]:
        """Load scenes from cache if available and valid"""
        cache_path = self._get_cache_file_path(video_path)
        if not os.path.exists(cache_path):
            return None
            
        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
                
            # Check if the video hash matches
            current_hash = self._get_video_hash(video_path)
            if cache_data.get('video_hash') != current_hash:
                print(f"Video changed, cache invalid for {video_path}")
                return None
                
            # Check if detection parameters match
            if (cache_data.get('threshold') != self.threshold or
                cache_data.get('min_scene_len') != self.min_scene_len or
                cache_data.get('sample_fps') != self.sample_fps or
                cache_data.get('target_megapixels') != self.target_megapixels):
                print(f"Detection parameters changed, cache invalid for {video_path}")
                return None
                
            scenes = cache_data.get('scenes', [])
            print(f"Loaded {len(scenes)} scenes from cache for {video_path}")
            return scenes
            
        except Exception as e:
            print(f"Error loading scene cache: {e}")
            return None
            
    def save_scenes_to_cache(self, video_path: str, scenes: List[Tuple[int, int]]):
        """Save scenes to cache file"""
        cache_path = self._get_cache_file_path(video_path)
        try:
            cache_data = {
                'video_hash': self._get_video_hash(video_path),
                'threshold': self.threshold,
                'min_scene_len': self.min_scene_len,
                'sample_fps': self.sample_fps,
                'target_megapixels': self.target_megapixels,
                'scenes': scenes
            }
            
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
            print(f"Saved {len(scenes)} scenes to cache: {cache_path}")
            
        except Exception as e:
            print(f"Error saving scene cache: {e}") 