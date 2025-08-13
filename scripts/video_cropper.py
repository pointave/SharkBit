import sys, os, cv2, ffmpeg, json, numpy as np, re
from scripts.custom_graphics_view import CustomGraphicsView
from PyQt6.QtWidgets import (
    QApplication, QWidget, QFileDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QListWidget, QSlider, QGraphicsPixmapItem, QLineEdit, QSpinBox,
    QSizePolicy, QCheckBox, QListWidgetItem, QComboBox, QMessageBox,
    QTreeWidget, QTreeWidgetItem, QGridLayout, QFrame, QScrollArea, QTabWidget
)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QIcon, QMouseEvent, QDrag
from PyQt6.QtCore import Qt, QTimer, QUrl, QMimeData
from PyQt6.QtGui import QTextOption, QTextCursor
import shutil
import datetime
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import QTextEdit, QDialog, QVBoxLayout, QPushButton
import cv2
import json
import subprocess
from datetime import datetime

# Custom scene (modified to use the new crop region)
from scripts.custom_graphics_scene import CustomGraphicsScene

# Import helper modules
from scripts.video_loader import VideoLoader
from scripts.video_editor import VideoEditor
from scripts.video_exporter import VideoExporter
from scripts.scene_detector import SceneDetector

# Import UI methods from ui_elements.py
from scripts.ui_elements import (
    initUI,
    set_aspect_ratio,
    set_longest_edge,
    clear_crop_region_controller,
    crop_rect_updating,
    crop_rect_finalized,
    check_current_video_item,
    toggle_favorite_folder,
    cycle_theme,
    update_file_count,
    toggle_fullscreen,
    open_theme_selector,
    on_move_av1_clicked,
)

class ClickableLabel(QLabel):
    def __init__(self, parent=None, grid_index=None, click_callback=None):
        super().__init__(parent)
        self.grid_index = grid_index  # index in the multi_selected_indices
        self.click_callback = click_callback
    def mousePressEvent(self, event):
        if self.click_callback:
            self.click_callback(self.grid_index)
        super().mousePressEvent(event)

class MultiVideoCell(QWidget):
    def __init__(self, parent=None, grid_index=None, click_callback=None, loop_enabled=True, auto_advance_enabled=False, next_file_callback=None, drag_drop_callback=None, hover_callback=None):
        super().__init__(parent)
        self.grid_index = grid_index
        self.click_callback = click_callback
        self.drag_drop_callback = drag_drop_callback
        self.hover_callback = hover_callback  # New callback for hover events
        self.loop_enabled = loop_enabled
        self.auto_advance_enabled = auto_advance_enabled
        self.next_file_callback = next_file_callback
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        # Mute audio for multi-video mode to prevent multiple videos playing audio simultaneously
        self.audio_output.setMuted(True)
        self.player.setAudioOutput(self.audio_output)
        self.video_widget = QVideoWidget(self)
        self.player.setVideoOutput(self.video_widget)
        
        # Create a frame to hold the video widget with border styling
        self.frame = QFrame(self)
        self.frame.setFrameStyle(QFrame.Shape.Box)
        self.frame.setLineWidth(2)
        self.frame.setStyleSheet("QFrame { border: 2px solid #666; background-color: #333; }")
        
        # Create layout for the frame
        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(2, 2, 2, 2)
        frame_layout.addWidget(self.video_widget)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.frame)
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 90)
        
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        
        # Enable drag and drop on ALL widgets in the hierarchy
        self.setAcceptDrops(True)
        self.frame.setAcceptDrops(True)
        self.video_widget.setAcceptDrops(True)
        
        # Make video widget transparent to mouse events so drag events go to parent
        self.video_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        # Install event filters to ensure drag events are handled
        self.frame.installEventFilter(self)
        self.video_widget.installEventFilter(self)
        
        # Drag state
        self.is_dragging = False
        self.drag_start_pos = None
        
        # Enable mouse tracking for hover detection
        self.setMouseTracking(True)
        self.frame.setMouseTracking(True)
        
    def eventFilter(self, obj, event):
        """Event filter to handle drag events on child widgets"""
        if obj in [self.frame, self.video_widget]:
            if event.type() == event.Type.DragEnter:
                self.dragEnterEvent(event)
                return True
            elif event.type() == event.Type.DragLeave:
                self.dragLeaveEvent(event)
                return True
            elif event.type() == event.Type.DragMove:
                self.dragMoveEvent(event)
                return True
            elif event.type() == event.Type.Drop:
                self.dropEvent(event)
                return True
        return super().eventFilter(obj, event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
            self.is_dragging = False
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        # Handle hover callback
        if self.hover_callback:
            self.hover_callback(self.grid_index)
            
        if (self.drag_start_pos is not None and 
            (event.pos() - self.drag_start_pos).manhattanLength() > 10):
            self.is_dragging = True
            
            # Create drag object
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(str(self.grid_index))
            drag.setMimeData(mime_data)
            
            # Set drag pixmap (screenshot of current widget)
            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.pos())
            
            # Start drag
            result = drag.exec(Qt.DropAction.MoveAction)
            
            # Clear drag state and restore normal styling
            self.is_dragging = False
            self.drag_start_pos = None
            self.set_highlighted(False)  # Restore normal styling
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.is_dragging:
            # This was a click, not a drag
            if self.click_callback:
                self.click_callback(self.grid_index)
        self.is_dragging = False
        self.drag_start_pos = None
        super().mouseReleaseEvent(event)
        
    def wheelEvent(self, event):
        """Handle mouse wheel events for frame adjustment"""
        # Get the main app instance to access trim_length
        main_app = self.parent()
        while main_app and not hasattr(main_app, 'trim_length'):
            main_app = main_app.parent()
        
        if not main_app:
            super().wheelEvent(event)
            return
            
        modifiers = event.modifiers()
        delta = event.angleDelta().y()
        
        # Determine seek direction and amount based on modifiers
        if delta > 0:  # Scroll up - seek backward (like D key)
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                # Shift + wheel up = seek backward by trim_length * 4
                seek_amount = -main_app.trim_length * 4
                seek_type = "Shift+Wheel"
            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                # Ctrl + wheel up = seek backward by trim_length * 2
                seek_amount = -main_app.trim_length * 2
                seek_type = "Ctrl+Wheel"
            else:
                # Plain wheel up = seek backward by trim_length
                seek_amount = -main_app.trim_length
                seek_type = "Wheel"
        else:  # Scroll down - seek forward (like F key)
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                # Shift + wheel down = seek forward by trim_length * 4
                seek_amount = main_app.trim_length * 4
                seek_type = "Shift+Wheel"
            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                # Ctrl + wheel down = seek forward by trim_length * 2
                seek_amount = main_app.trim_length * 2
                seek_type = "Ctrl+Wheel"
            else:
                # Plain wheel down = seek forward by trim_length
                seek_amount = main_app.trim_length
                seek_type = "Wheel"
        
        # Apply seeking to the current video
        current_pos = self.player.position()
        duration = self.player.duration()
        
        # Calculate frame duration based on video duration and frame count
        # For QMediaPlayer, we need to estimate the frame duration
        # Assuming 30 FPS as default, but we can try to get actual FPS from the video
        fps = 30  # Default FPS
        frame_duration_ms = 1000 / fps  # milliseconds per frame
        
        # Calculate new position in milliseconds
        seek_duration_ms = seek_amount * frame_duration_ms
        new_pos = max(0, min(current_pos + seek_duration_ms, duration))
        self.player.setPosition(int(new_pos))
        
        # Update status if we can find the main app
        if hasattr(main_app, 'update_status'):
            main_app.update_status(f"Grid {self.grid_index+1}: {seek_type} {abs(seek_amount)} frames")
        
        event.accept()
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            
    def dragLeaveEvent(self, event):
        # No visual change needed
        pass
        
    def dropEvent(self, event):
        try:
            source_index = int(event.mimeData().text())
            target_index = self.grid_index
            
            if source_index != target_index and self.drag_drop_callback:
                self.drag_drop_callback(source_index, target_index)
                
            event.acceptProposedAction()
        except Exception as e:
            print(f"Error in dropEvent: {e}")
        
    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            
    def set_highlighted(self, highlighted):
        """Set visual highlight for this cell"""
        if highlighted:
            self.frame.setStyleSheet("QFrame { border: 3px solid #007acc; background-color: #333; }")
        else:
            self.frame.setStyleSheet("QFrame { border: 2px solid #666; background-color: #333; }")
            
    def show_swap_menu(self, pos):
        """Show context menu for swapping with other videos"""
        from PyQt6.QtWidgets import QMenu
        
        menu = QMenu(self)
        menu.setTitle(f"Swap Grid {self.grid_index + 1}")
        
        # Get parent widget to access other cells
        parent = self.parent()
        if parent and hasattr(parent, 'multi_video_widgets'):
            for i, cell in enumerate(parent.multi_video_widgets):
                if i != self.grid_index:
                    action = menu.addAction(f"Swap with Grid {i + 1}")
                    action.triggered.connect(lambda checked, target=i: self._swap_with_grid(target))
        
        if menu.actions():
            menu.exec(pos)
        
    def _swap_with_grid(self, target_index):
        """Swap this cell with another grid cell"""
        if self.drag_drop_callback:
            self.drag_drop_callback(self.grid_index, target_index)
            
    def load(self, path):
        self.player.setSource(QUrl.fromLocalFile(path))
    def play(self):
        self.player.play()
    def pause(self):
        self.player.pause()
    def stop(self):
        self.player.stop()
    def set_position(self, pos):
        self.player.setPosition(pos)
    def set_loop(self, loop):
        self.loop_enabled = loop
    def set_auto_advance(self, enabled):
        self.auto_advance_enabled = enabled
    def set_next_file_callback(self, callback):
        self.next_file_callback = callback
    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.loop_enabled:
                self.player.setPosition(0)
                self.player.play()
            elif self.auto_advance_enabled and self.next_file_callback:
                self.next_file_callback(self.grid_index)

    def toggle_audio(self):
        """Toggle audio on/off"""
        self.audio_enabled = not self.audio_enabled
        self.audio_output.setMuted(not self.audio_enabled)
        self.audio_button.setText("🔊 Audio On" if self.audio_enabled else "🔇 Audio Off")
        self.audio_button.setChecked(self.audio_enabled)

class VideoCropper(QWidget):
    def open_yt_folder(self):
        import os
        #yt_folder = r"----CUSTOM PATH HERE----"
        yt_folder = os.path.join(os.environ["USERPROFILE"], "Videos")
        if not os.path.exists(yt_folder):
            QMessageBox.critical(self, "YT Folder Not Found", f"{yt_folder} does not exist.")
            return
        try:
            os.startfile(yt_folder)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open folder: {e}")

    def load_youtube_url(self):
        url = self.youtube_url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "No URL", "Please enter a YouTube URL.")
            return
        # Run download in background thread to keep UI responsive
        import threading
        self.youtube_url_input.setEnabled(False)
        threading.Thread(target=self._youtube_download_worker, args=(url,), daemon=True).start()
        
    def _youtube_download_worker(self, url):
        """Worker function to handle YouTube downloads in a background thread."""
        try:
            import yt_dlp
            import tempfile
            import os
            
            self.update_status(f"Downloading YouTube video: {url}")
            
            # Set up yt-dlp options
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': os.path.join(tempfile.gettempdir(), '%(title)s.%(ext)s'),
                'quiet': False,
                'no_warnings': True,
                'progress_hooks': [self._youtube_download_progress_hook],
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get video info first to show title
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', 'video')
                self.update_status(f"Downloading: {video_title}")
                
                # Start the download
                ydl.download([url])
                
                # Get the downloaded file path
                filename = ydl.prepare_filename(info)
                
                # Move the file to the current folder
                if os.path.exists(filename):
                    import shutil
                    dest_path = os.path.join(self.folder_path, os.path.basename(filename))
                    shutil.move(filename, dest_path)
                    self.update_status(f"Download complete: {os.path.basename(dest_path)}")
                    # Refresh the file list
                    self.loader.load_folder_contents()
                
        except Exception as e:
            self.update_status(f"Error downloading video: {str(e)}")
            QMessageBox.critical(self, "Download Error", f"Failed to download video: {str(e)}")
        finally:
            # Re-enable the input field
            self.youtube_url_input.setEnabled(True)
    
    def _youtube_download_progress_hook(self, d):
        """Progress hook for YouTube downloads."""
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%')
            speed = d.get('_speed_str', 'N/A')
            self.update_status(f"Downloading: {percent} at {speed}")
        elif d['status'] == 'finished':
            self.update_status("Processing video...")

    def toggle_audio(self):
        """Toggle audio on/off"""
        # Only allow audio in single-video mode
        if self.multi_mode:
            self.audio_enabled = False
            self.audio_button.setChecked(False)
            self.audio_button.setText("🔇 Audio Off")
            self.update_status("Audio disabled in multi-video mode")
            return
            
        self.audio_enabled = not self.audio_enabled
        self.audio_button.setText("🔊 Audio On" if self.audio_enabled else "🔇 Audio Off")
        
        # Update audio state for the current video player
        if hasattr(self, 'player') and hasattr(self.player, 'audio_output'):
            self.player.audio_output.setMuted(not self.audio_enabled)
            
        self.update_status(f"Audio {'enabled' if self.audio_enabled else 'disabled'}")
        
    def toggle_auto_advance(self):
        """Toggle auto-advance to next video after trim"""
        self.auto_advance_enabled = not getattr(self, 'auto_advance_enabled', False)
        if hasattr(self, 'auto_advance_button'):
            self.auto_advance_button.setChecked(self.auto_advance_enabled)
        self.update_status(
            f"Auto-advance {'enabled' if self.auto_advance_enabled else 'disabled'}"
        )
        # Update all cells' loop/auto-advance state
        for cell in getattr(self, 'multi_video_widgets', []):
            if hasattr(cell, 'set_loop'):
                cell.set_loop(not self.auto_advance_enabled)
            if hasattr(cell, 'set_auto_advance'):
                cell.set_auto_advance(self.auto_advance_enabled)
                
        # If enabling auto-advance, make sure audio is off in multi-video mode
        if self.multi_mode and self.audio_enabled:
            self.audio_enabled = False
            self.audio_button.setChecked(False)
            self.audio_button.setText("🔇 Audio Off")

    def take_screenshot(self):
        """Take a screenshot of the current video frame with crop regions."""
        if not hasattr(self, 'current_video') or not self.current_video:
            self.update_status("No video loaded.")
            return
            
        # Get the current video entry
        entry = next((e for e in self.video_files if e["display_name"] == self.current_video), None)
        if not entry:
            self.update_status("Could not find current video entry.")
            return
            
        # Check if we have a valid pixmap
        if not hasattr(self, 'pixmap_item') or not hasattr(self.pixmap_item, 'pixmap') or self.pixmap_item.pixmap().isNull():
            self.update_status("No video frame available.")
            return
            
        try:
            from scripts.screenshot_helper import save_video_screenshot
            
            # Save the screenshot
            result = save_video_screenshot(
                entry=entry,
                pixmap=self.pixmap_item.pixmap(),
                crop_regions=getattr(self, 'crop_regions', {}),
                original_width=getattr(self, 'original_width', 0),
                original_height=getattr(self, 'original_height', 0),
                current_video=self.current_video,
                folder_path=self.folder_path if hasattr(self, 'folder_path') else os.getcwd()
            )
            
            if result:
                self.update_status("Screenshot saved")
            else:
                self.update_status("Failed to save screenshot.")
                
        except Exception as e:
            self.update_status(f"Error saving screenshot: {str(e)}")
            import traceback
            print(f"Screenshot error: {traceback.format_exc()}")

    export_in_progress = False  # Class-level flag to prevent duplicate exports
    def __init__(self):
        print("VideoCropper __init__ starting")  # DEBUG
        super().__init__()
        # ... (rest of the code remains the same)
        self.loop_playback = False  # Always define this to prevent AttributeError
        self.setWindowTitle("SharkBit")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon("icons/shark_icon.svg"))
        # Ensure the widget gets key events immediately.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Core state
        self.folder_path = ""
        self.video_files = []  # List of video dicts
        self.current_video = None
        # Add this new property:
        self.current_video_index = 0
        self.crop_regions = {}  # Dict to store crop region data per video
        self.current_rect = None  # Reference to the active crop region item
        self.longest_edge = 1024
        self.cap = None
        self.frame_count = 0
        self.original_width = 0
        self.original_height = 0
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.clip_aspect_ratio = 1.0  # Default
        
        # Audio state
        self.audio_enabled = False
        
        # Trimming properties
        self.trim_length = 113
        self.trim_points = {}
        self.is_playing = False
        self.auto_play_on_change = False  # New: controls auto-play on video change
        
        # Export properties
        self.export_uncropped = False
        self.export_image = False
        self.trim_modified = False
        
        # Session file
        self.folder_sessions = {}
        self.session_file = "session_data.json"
        
        # New property for simple caption text.
        self.simple_caption = ""
        
        # Add video state tracking like gui-videotrim
        self.current_video_index = -1  # Start at -1 like gui-videotrim
        self.video_files = []
        self.playing = False
        
        # UI widgets
        self.video_list = QListWidget()
        
        # Aspect ratio options (for crop constraint)
        self.aspect_ratios = {
            "Free-form": None,
            "1:1 (Square)": 1.0,
            "4:3 (Standard)": 4/3,
            "16:9 (Widescreen)": 16/9,
            "9:16 (Vertical Video)": 9/16,
            "2:1 (Cinematic)": 2.0,
            "2:3 (Classic Photo)": 2/3,
            "21:9 (Ultrawide)": 21/9
        }
        
        # Create helper modules and pass self.
        self.loader = VideoLoader(self)
        self.editor = VideoEditor(self)
        self.exporter = VideoExporter(self)
        self.export_in_progress = False  # Instance-level flag

        # Initialize favorite folder settings (fixed)
        #self.favorite_folder = r"--PUT YOUR PATH HERE__"
        self.favorite_folder = os.path.join(os.environ["USERPROFILE"], "Videos")
        self.last_non_favorite_folder = ""
        self.favorite_active = False


        # --- Multi-video mode state (must be initialized before UI setup) ---
        self.multi_mode = False
        self.multi_selected_indices = []
        self.multi_video_widgets = []
        self.multi_caps = []
        self.multi_frame_counts = []
        self.multi_timer = QTimer()
        self.multi_timer.timeout.connect(self._multi_next_frame)
        self.multi_frame_pos = 0
        self.multi_loop = True
        self.multi_focused_grid = 0  # Index of focused grid video in multi mode
        self.multi_playing = []      # Per-grid play state
        
        # Grid layout mode: 'auto' (smart), 'vertical' (2 cols), 'horizontal' (3 cols)
        self.grid_layout_mode = 'auto'
        
        # Drag and drop system for grid rearrangement

        # Load previous session.
        self.loader.load_session()
        # --- Patch: If folder_path is missing or invalid, use favorite_folder ---
        if not self.folder_path or not os.path.exists(self.folder_path) or not os.path.isdir(self.folder_path):
            self.folder_path = self.favorite_folder
            self.favorite_active = True
        # Always reset trim_length to default on startup
        self.trim_length = 113
        if hasattr(self, 'trim_spin'):
            self.trim_spin.setValue(113)
        print("Restored folder_path:", self.folder_path)  # Debug print

        # If a folder was remembered, load its contents now.
        if self.folder_path:
            self.loader.load_folder_contents()
        self.initUI()
        print("After initUI")  # DEBUG
        self.deleted_clips_stack = []  # Initialize an empty stack for deleted videos
        # Ensure default sort is 'Date (new first)' on startup (after UI is built)
        self.sort_dropdown.setCurrentIndex(0)
        if self.video_files:
            self.loader.sort_videos('Date (new first)')
        # Removed folder history dropdown; no longer used
        # Auto-highlight and expand the starting folder in the folder tree
        if self.folder_path:
            self.update_folder_tree(self.folder_path)
            def select_folder_item(tree, target_path):
                def recurse(item):
                    if item.data(0, Qt.ItemDataRole.UserRole) == target_path:
                        tree.setCurrentItem(item)
                        item.setSelected(True)
                        parent = item.parent()
                        while parent:
                            parent.setExpanded(True)
                            parent = parent.parent()
                        return True
                    for i in range(item.childCount()):
                        if recurse(item.child(i)):
                            return True
                for i in range(tree.topLevelItemCount()):
                    if recurse(tree.topLevelItem(i)):
                        break
            select_folder_item(self.folder_tree, self.folder_path)

        # New multi-video mode attributes
        self.multi_target_fps = 16
        self.multi_skip_frames = 1

        # Additional UI widgets
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(5, 30)
        self.fps_spin.setValue(self.multi_target_fps)
        self.fps_spin.valueChanged.connect(lambda v: self.adjust_multi_performance(target_fps=v, skip_frames=self.multi_skip_frames))

        self.skip_spin = QSpinBox()
        self.skip_spin.setRange(1, 10)
        self.skip_spin.setValue(self.multi_skip_frames)
        self.skip_spin.valueChanged.connect(lambda v: self.adjust_multi_performance(target_fps=self.multi_target_fps, skip_frames=v))

        # Now it's safe to update the file count label
        if self.folder_path:
            self.update_file_count()
            
        # Initialize scene detection
        self.scene_detector = SceneDetector()
        self.scene_detector.progress_updated.connect(self.on_scene_detection_progress)
        self.scene_detector.scenes_detected.connect(self.on_scenes_detected)
        self.scene_detector.detection_finished.connect(self.on_scene_detection_finished)
        self.current_scenes = []  # Store scenes for current video
        self.scene_detection_in_progress = False  # Track if detection is running
        self.scene_detection_stop_requested = False  # Track if stop was requested
        
        # Initialize metadata dialog
        self.metadata_dialog = None

    def on_sort_changed(self, idx):
        if hasattr(self, 'loader') and hasattr(self.loader, 'sort_videos'):
            self.loader.sort_videos(self.sort_dropdown.currentText())

    def open_theme_selector(self):
        """Open the theme selector dialog"""
        from scripts.theme_selector import ThemeSelector
        dialog = ThemeSelector(self)
        dialog.exec()


    
    def eventFilter(self, source, event):
        # Simplified event filter - just handle the original functionality
        
        # Redirect key events from video_list and graphics_view to main window for global shortcuts
        from PyQt6.QtCore import QEvent
        # Only redirect key events from video_list or graphics_view, not from search_bar
        from PyQt6.QtCore import QEvent
        # Only redirect key events from graphics_view for up/down, but only if graphics_view exists
        if hasattr(self, 'graphics_view') and source is self.graphics_view and event.type() == QEvent.Type.KeyPress:
            # Prevent double navigation in preview mode: let preview window handle Up/Down
            if hasattr(self, '_preview_mode') and self._preview_mode:
                return False
            key = event.key()
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                self.keyPressEvent(event)
                return True  # Block further processing (prevent double-step)
            self.keyPressEvent(event)
            return True
        # For video_list, let QListWidget handle up/down arrows natively
        if source is self.video_list and event.type() == QEvent.Type.KeyPress:
            if self.search_bar.hasFocus():
                return False
            # Only redirect non-up/down keys
            key = event.key()
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                return False  # Let QListWidget handle up/down
            self.keyPressEvent(event)
            return True
        # This event filter is only used for the slider.
        if hasattr(self, 'slider') and source is self.slider:
            if event.type() == QMouseEvent.Type.MouseButtonPress:
                self.editor.move_trim_to_click_position(event)
            elif event.type() == QMouseEvent.Type.HoverMove:
                self.editor.show_thumbnail(event)
            elif event.type() == QMouseEvent.Type.Leave:
                self.thumbnail_label.hide()
        return False

    def closeEvent(self, event):
        self.loader.save_session()
        event.accept()

    def update_status(self, message):
        self.status_label.setText(message)

    def export_finished_callback(self):
        self.export_in_progress = False
        self.update_status("Export ready.")

    def showEvent(self, event):
        super().showEvent(event)
        self.setFocus()  # Ensure VideoCropper has focus when shown.

    def on_video_list_pressed(self, item):
        """Handle ctrl+click for multi mode, or normal click for single mode."""
        modifiers = QApplication.keyboardModifiers()
        idx = self.video_list.row(item)
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            # Multi mode: add/remove selection
            if idx not in self.multi_selected_indices:
                self.multi_selected_indices.append(idx)
            else:
                self.multi_selected_indices.remove(idx)
            self._update_multi_selection()
        else:
            # Normal click: reset to single mode
            self.multi_mode = False
            self.multi_selected_indices = []
            self._teardown_multi_mode()
            self.on_video_selected(idx)

    def _update_multi_selection(self):
        if len(self.multi_selected_indices) > 1:
            # Disable audio when entering multi-video mode
            if self.audio_enabled:
                self.audio_enabled = False
                if hasattr(self, 'audio_button'):
                    self.audio_button.setChecked(False)
                    self.audio_button.setText("🔇 Audio Off")
                if hasattr(self, 'player') and hasattr(self.player, 'audio_output'):
                    self.player.audio_output.setMuted(True)
            self.multi_mode = True
            self._setup_multi_mode()
        elif len(self.multi_selected_indices) == 1:
            self.multi_mode = False
            self._teardown_multi_mode()
            self.on_video_selected(self.multi_selected_indices[0])
        else:
            self.multi_mode = False
            self._teardown_multi_mode()

    MULTI_COLORS = [
        "#FFB3B3",  # Light Red
        "#B3FFB3",  # Light Green
        "#B3B3FF",  # Light Blue
        "#FFF7B3",  # Light Yellow
        "#FFB3FF",  # Light Magenta
        "#B3FFFF",  # Light Cyan
        "#FFD9B3",  # Light Orange
        "#D9B3FF",  # Light Purple
    ]

    def _highlight_multi_videos(self):
        for i, cell in enumerate(getattr(self, "multi_video_widgets", [])):
            if i == getattr(self, "multi_focused_grid", 0):
                cell.set_highlighted(True)
            else:
                cell.set_highlighted(False)

    def _clear_multi_highlights(self):
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            item.setBackground(Qt.GlobalColor.transparent)

    def _calculate_grid_columns(self, num_videos):
        """Calculate optimal number of columns based on layout mode and number of videos"""
        if self.grid_layout_mode == 'vertical':
            # Always use 2 columns for vertical layout
            return 2
        elif self.grid_layout_mode == 'horizontal':
            # Use 3 columns for horizontal layout when possible
            if num_videos <= 3:
                return num_videos  # 1, 2, or 3 columns based on video count
            else:
                return 3  # Max 3 columns for horizontal layout
        else:  # 'auto' mode - smart layout
            if num_videos <= 2:
                return 2  # 2x1 or 1x2
            elif num_videos <= 4:
                return 2  # 2x2
            elif num_videos <= 6:
                return 3  # 3x2
            elif num_videos <= 9:
                return 3  # 3x3
            else:
                return 4  # 4xN for larger numbers

    def _restore_multi_mode_layout(self):
        """Properly restore multi-mode layout after preview window is closed"""
        # Clear the existing grid layout
        while self.multi_grid_layout.count():
            item = self.multi_grid_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        # Re-add all video cells to the grid with proper layout
        cols = self._calculate_grid_columns(len(self.multi_video_widgets))
        for i, w in enumerate(self.multi_video_widgets):
            row = i // cols
            col = i % cols
            self.multi_grid_layout.addWidget(w, row, col)
        
        # Ensure the scroll area is properly set up
        if not hasattr(self, 'multi_grid_scroll_area'):
            self.multi_grid_scroll_area = QScrollArea()
            self.multi_grid_scroll_area.setWidgetResizable(True)
            self.multi_grid_scroll_area.setWidget(self.multi_grid_widget)
        
        # Insert the scroll area back into the right panel layout
        # First, remove any existing scroll area
        for i in range(self.right_panel_layout.count()):
            item = self.right_panel_layout.itemAt(i)
            if item and item.widget() == self.multi_grid_scroll_area:
                self.right_panel_layout.removeItem(item)
                break
        
        # Insert at the correct position (index 1, after the graphics view)
        self.right_panel_layout.insertWidget(1, self.multi_grid_scroll_area)
        
        # Set proper size policies and visibility
        self.multi_grid_widget.setMinimumSize(0, 0)
        self.multi_grid_widget.setMaximumSize(16777215, 16777215)
        self.multi_grid_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.multi_grid_scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.multi_grid_scroll_area.setMinimumSize(0, 0)
        self.multi_grid_scroll_area.setMaximumSize(16777215, 16777215)
        
        # Update geometry and ensure visibility
        self.multi_grid_widget.updateGeometry()
        self.multi_grid_scroll_area.setVisible(True)
        self.multi_grid_widget.setVisible(True)
        
        # Ensure graphics view and slider remain hidden in multi mode
        self.graphics_view.setVisible(False)
        self.slider.setVisible(False)
        
        # Update status
        layout_names = {'auto': 'Auto', 'vertical': 'Vertical (2 cols)', 'horizontal': 'Horizontal (3 cols)'}
        layout_name = layout_names.get(self.grid_layout_mode, 'Auto')
        self.status_label.setText(
            f"Multi mode: playing {len(self.multi_video_widgets)} videos - Layout: {layout_name}"
        )
        
        # Re-highlight the focused grid
        self._highlight_multi_videos()

    def _setup_multi_mode(self):
        self.is_playing = False
        self.editor._stop_timer()
        for w in getattr(self, 'multi_video_widgets', []):
            self.multi_grid_layout.removeWidget(w)
            w.deleteLater()
        self.multi_video_widgets = []
        def on_grid_cell_clicked(grid_idx):
            self.multi_focused_grid = grid_idx
            self._highlight_multi_videos()
        def on_grid_cell_hover(grid_idx):
            # Update focused grid on hover
            self.multi_focused_grid = grid_idx
            self._highlight_multi_videos()
        def next_file_for_cell(grid_idx):
            # Called when a cell needs to auto-advance
            current_idx = self.multi_selected_indices[grid_idx]
            next_idx = (current_idx + 1) % len(self.video_files)
            self.multi_selected_indices[grid_idx] = next_idx
            entry = self.video_files[next_idx]
            cell = self.multi_video_widgets[grid_idx]
            cell.load(entry["original_path"])
            cell.player.play()
            cell.setToolTip(entry["display_name"])
            self.status_label.setText(f"Grid {grid_idx+1}: {entry['display_name']}")
            self._highlight_multi_videos()
        for slot, idx in enumerate(self.multi_selected_indices):
            entry = self.video_files[idx]
            cell = MultiVideoCell(
                grid_index=slot,
                click_callback=on_grid_cell_clicked,
                hover_callback=on_grid_cell_hover,
                loop_enabled=not getattr(self, 'auto_advance_enabled', False),
                auto_advance_enabled=getattr(self, 'auto_advance_enabled', False),
                next_file_callback=next_file_for_cell,
                drag_drop_callback=self._on_video_drag_drop
            )
            cell.load(entry["original_path"])
            cell.play()
            self.multi_video_widgets.append(cell)
        
        # Calculate optimal number of columns based on layout mode and video count
        cols = self._calculate_grid_columns(len(self.multi_video_widgets))
        
        for i, w in enumerate(self.multi_video_widgets):
            row = i // cols
            col = i % cols
            self.multi_grid_layout.addWidget(w, row, col)
        if not hasattr(self, 'multi_grid_scroll_area'):
            self.multi_grid_scroll_area = QScrollArea()
            self.multi_grid_scroll_area.setWidgetResizable(True)
            self.multi_grid_scroll_area.setWidget(self.multi_grid_widget)
            self.right_panel_layout.insertWidget(1, self.multi_grid_scroll_area)
        self.multi_grid_widget.setMinimumSize(0, 0)
        self.multi_grid_widget.setMaximumSize(16777215, 16777215)
        self.multi_grid_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.multi_grid_scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.multi_grid_scroll_area.setMinimumSize(0, 0)
        self.multi_grid_scroll_area.setMaximumSize(16777215, 16777215)
        self.multi_grid_widget.updateGeometry()
        self.multi_grid_scroll_area.setVisible(True)
        self.multi_grid_widget.setVisible(True)
        self.graphics_view.setVisible(False)
        self.slider.setVisible(False)
        # Add wheel event handling to multi grid widget
        def multi_grid_wheel_event(event):
            """Handle wheel events in multi grid widget"""
            # Find which cell the mouse is over
            mouse_pos = event.position()
            for cell in self.multi_video_widgets:
                if cell.geometry().contains(mouse_pos.toPoint()):
                    # Directly call the cell's wheelEvent method
                    cell.wheelEvent(event)
                    event.accept()
                    return
            event.ignore()
        
        self.multi_grid_widget.wheelEvent = multi_grid_wheel_event
        
        # Show current layout mode in status
        layout_names = {'auto': 'Auto', 'vertical': 'Vertical (2 cols)', 'horizontal': 'Horizontal (3 cols)'}
        layout_name = layout_names.get(self.grid_layout_mode, 'Auto')
        self.status_label.setText(
            f"Multi mode: playing {len(self.multi_video_widgets)} videos - Layout: {layout_name} | Drag to rearrange | Ctrl+Arrow keys to swap | F/D/Wheel to adjust frames"
        )
        self._highlight_multi_videos()
        
        # Drag-and-drop should work now

    def _on_video_drag_drop(self, source_index, target_index):
        """Handle drag and drop to swap video positions"""
        if source_index == target_index:
            return
            
        # Swap the video indices in multi_selected_indices
        self.multi_selected_indices[source_index], self.multi_selected_indices[target_index] = \
            self.multi_selected_indices[target_index], self.multi_selected_indices[source_index]
            
        # Update the grid_index of the cells to match their new positions
        self.multi_video_widgets[source_index].grid_index = target_index
        self.multi_video_widgets[target_index].grid_index = source_index
        
        # Swap the cells in the widgets list
        self.multi_video_widgets[source_index], self.multi_video_widgets[target_index] = \
            self.multi_video_widgets[target_index], self.multi_video_widgets[source_index]
            
        # Check if we're in preview mode and restore layout
        if hasattr(self, '_preview_mode') and self._preview_mode:
            # We're in preview mode - trigger Shift+Y twice to restore the window
            if hasattr(self, '_preview_window') and self._preview_window:
                # Simulate pressing Shift+Y twice to restore the window
                QTimer.singleShot(100, lambda: self._trigger_shift_y_twice())
        else:
            # Normal mode - update the grid layout positions
            cols = self._calculate_grid_columns(len(self.multi_video_widgets))
            
            # Remove widgets from layout
            for widget in self.multi_video_widgets:
                self.multi_grid_layout.removeWidget(widget)
                
            # Re-add widgets in new positions
            for i, w in enumerate(self.multi_video_widgets):
                row = i // cols
                col = i % cols
                self.multi_grid_layout.addWidget(w, row, col)
            
        # Update status
        self.status_label.setText(f"Videos rearranged: Grid {source_index+1} ↔ Grid {target_index+1}")
        
        # Re-highlight the focused grid
        self._highlight_multi_videos()
        
    def _trigger_shift_y_twice(self):
        """Simulate pressing Shift+Y twice to restore the preview window"""
        if hasattr(self, '_preview_mode') and self._preview_mode:
            # First Shift+Y - close preview window
            self._preview_mode = False
            if hasattr(self, '_preview_window') and self._preview_window:
                self._preview_window.close()
                
            # Restore all video cells back to the multi grid widget
            for cell in self.multi_video_widgets:
                cell.setParent(self.multi_grid_widget)
            
            # Properly restore multi mode layout
            self._restore_multi_mode_layout()
            
            self.showNormal()
            if hasattr(self, '_prev_geometry'):
                self.setGeometry(self._prev_geometry)
            if hasattr(self, '_prev_window_state'):
                self.setWindowState(self._prev_window_state)
            self.show()
            
            # Second Shift+Y - reopen preview window
            QTimer.singleShot(50, lambda: self._trigger_shift_y_second())
            
    def _trigger_shift_y_second(self):
        """Second part of Shift+Y - reopen the preview window"""
        if not hasattr(self, '_preview_mode'):
            self._preview_mode = False
        self._preview_mode = True
        
        # Hide main window
        self._prev_geometry = self.geometry()
        self._prev_window_state = self.windowState()
        self.hide()
        
        # Create preview window with custom responsive layout
        self._preview_window = QWidget()
        self._preview_window.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self._preview_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        # Create a custom container widget that will handle the responsive layout
        self._preview_container = QWidget(self._preview_window)
        self._preview_container.setStyleSheet("background-color: black;")
        
        # Add a custom resize event handler to the container
        def container_resizeEvent(ev):
            try:
                # Trigger the window resize handler
                if hasattr(self, '_preview_window') and self._preview_window.resizeEvent:
                    self._preview_window.resizeEvent(ev)
            except Exception as e:
                print(f"Error in container resize handler: {e}")
            QWidget.resizeEvent(self._preview_container, ev)
        
        self._preview_container.resizeEvent = container_resizeEvent
        
        # Move all video cells to the preview container
        for cell in self.multi_video_widgets:
            cell.setParent(self._preview_container)
        
        layout = QVBoxLayout(self._preview_window)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self._preview_container)
        
        # Set proper size policies for responsive layout
        self.multi_grid_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        for cell in self.multi_video_widgets:
            if hasattr(cell, 'setSizePolicy'):
                cell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            if hasattr(cell, 'video_widget') and hasattr(cell.video_widget, 'setSizePolicy'):
                cell.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Set a larger initial size that can be bigger than the main UI
        num_videos = len(self.multi_video_widgets)
        if num_videos <= 2:
            initial_width = 1200
            initial_height = 600
        elif num_videos <= 4:
            initial_width = 1200
            initial_height = 800
        elif num_videos <= 6:
            initial_width = 1400
            initial_height = 900
        else:
            initial_width = 1600
            initial_height = 1000
        
        # Set up initial video positioning in the preview container
        cols = self._calculate_grid_columns(num_videos)
        
        rows = (num_videos + cols - 1) // cols
        cell_width = initial_width // cols
        cell_height = initial_height // rows
        
        # Position all videos in the preview container
        for i, cell in enumerate(self.multi_video_widgets):
            row = i // cols
            col = i % cols
            x = col * cell_width
            y = row * cell_height
            cell.setGeometry(x, y, cell_width, cell_height)
            if hasattr(cell, 'video_widget'):
                cell.video_widget.setGeometry(0, 0, cell_width, cell_height)
        
        # Now resize the window after layout is set up
        self._preview_window.resize(initial_width, initial_height)
        
        # Force layout update to ensure all videos fit properly
        self.multi_grid_widget.updateGeometry()
        # Center preview window on screen
        screen = QApplication.primaryScreen().geometry()
        x = screen.center().x() - initial_width // 2
        y = screen.center().y() - initial_height // 2
        self._preview_window.move(x, y)
        self._preview_window.show()
        self._preview_window.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._preview_window.setFocus()
        self._preview_window.raise_()
        
        # Trigger initial resize to ensure proper layout
        QTimer.singleShot(100, lambda: self._preview_window.resizeEvent(None))
        
        def esc_close(event):
            # --- Minimize preview window on Backspace ---
            if event.key() == Qt.Key.Key_Backspace:
                self._preview_window.showMinimized()
                return
            if event.key() == Qt.Key.Key_Q:
                QApplication.quit()
                return
            if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Y):
                self._preview_mode = False
                self._preview_window.close()
                
                # Restore all video cells back to the multi grid widget
                for cell in self.multi_video_widgets:
                    cell.setParent(self.multi_grid_widget)
                
                # Properly restore multi mode layout
                self._restore_multi_mode_layout()
                
                self.showNormal()
                self.setGeometry(self._prev_geometry)
                self.setWindowState(self._prev_window_state)
                self.show()
                event.accept()
                return
            self.keyPressEvent(event)
        self._preview_window.keyPressEvent = esc_close
        self.multi_grid_widget.keyPressEvent = esc_close
        self.multi_grid_widget.setMinimumSize(200, 150)
        
        # --- Add resize handler that actually scales videos to fit ---
        def preview_resizeEvent(ev):
            try:
                # Get the available space in the preview container
                container_width = self._preview_container.width()
                container_height = self._preview_container.height()
                
                if container_width < 50 or container_height < 50:
                    QWidget.resizeEvent(self._preview_window, ev)
                    return
                
                num_videos = len(self.multi_video_widgets)
                if num_videos == 0:
                    QWidget.resizeEvent(self._preview_window, ev)
                    return
                
                # Calculate optimal grid layout using the same logic as main grid
                cols = self._calculate_grid_columns(num_videos)
                
                rows = (num_videos + cols - 1) // cols
                
                # Calculate cell dimensions to fit ALL videos in the available space
                cell_width = container_width // cols
                cell_height = container_height // rows
                
                # Position and size each video cell
                for i, cell in enumerate(self.multi_video_widgets):
                    row = i // cols
                    col = i % cols
                    
                    # Calculate position
                    x = col * cell_width
                    y = row * cell_height
                    
                    # Set the cell to exactly fit in its grid position
                    cell.setGeometry(x, y, cell_width, cell_height)
                    
                    # Ensure the video widget fills the cell
                    if hasattr(cell, 'video_widget'):
                        cell.video_widget.setGeometry(0, 0, cell_width, cell_height)
                
                # Force update
                self._preview_container.update()
                
            except Exception as e:
                print(f"Error in preview resize handler: {e}")
                import traceback
                traceback.print_exc()
            
            QWidget.resizeEvent(self._preview_window, ev)
        
        # Store the original resizeEvent method
        self._preview_window.resizeEvent = preview_resizeEvent


    def _teardown_multi_mode(self):
        for w in getattr(self, 'multi_video_widgets', []):
            w.player.stop()
            self.multi_grid_layout.removeWidget(w)
            w.deleteLater()
        self.multi_video_widgets = []
        if hasattr(self, 'multi_grid_scroll_area'):
            self.multi_grid_scroll_area.setVisible(False)
        self.multi_grid_widget.setVisible(False)
        self.graphics_view.setVisible(True)
        self.slider.setVisible(True)
        self.status_label.setText("Ready")

    def _multi_next_frame(self):
        if not self.multi_mode or not self.multi_caps:
            self.multi_timer.stop()
            return
        # Only update/redraw changed slots
        for i in range(len(self.multi_caps)):
            if self.multi_finished[i]:
                continue
            # Only advance frame if playing
            if not self.multi_playing[i]:
                continue
            pos = self.multi_frame_positions[i]
            if pos % self.multi_skip_frames != 0:
                self.multi_frame_positions[i] += 1
                continue
            cap = self.multi_caps[i]
            frame_count = self.multi_frame_counts[i]
            label = self.multi_video_widgets[i]
            cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            ret, frame = cap.read()
            if not ret or pos >= frame_count:
                if self.multi_loop:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                    pos = 0
                    if not ret:
                        self.multi_finished[i] = True
                        label.clear()
                        continue
                    self.multi_frame_positions[i] = 1
                elif getattr(self, "auto_advance_enabled", False):
                    # Move to next file in folder
                    current_idx = self.multi_indices[i]
                    next_idx = (current_idx + 1) % len(self.video_files)
                    if next_idx == current_idx:
                        self.multi_finished[i] = True
                        label.clear()
                        continue
                    self.multi_caps[i].release()
                    entry = self.video_files[next_idx]
                    cap = cv2.VideoCapture(entry["original_path"])
                    if not cap.isOpened():
                        self.multi_finished[i] = True
                        label.clear()
                        continue
                    self.multi_caps[i] = cap
                    self.multi_frame_counts[i] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    self.multi_frame_positions[i] = 0
                    self.multi_finished[i] = False
                    self.multi_indices[i] = next_idx
                    label.setToolTip(entry["display_name"])
                    self._highlight_multi_videos()
                    continue
                else:
                    self.multi_finished[i] = True
                    label.clear()
                    continue
            else:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                bytes_per_line = ch * w
                qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                pix = QPixmap.fromImage(qimg)
                label.setPixmap(pix.scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                self.multi_frame_positions[i] = pos + 1

        # If all slots are finished and not looping/auto-advancing, teardown multi mode
        if all(self.multi_finished) and not self.multi_loop and not getattr(self, "auto_advance_enabled", False):
            self.multi_timer.stop()
            self._teardown_multi_mode()
            return

    def on_video_selected(self, index):
        """Handle video selection using index-based navigation"""
        if self.multi_mode:
            return  # Ignore single selection if in multi mode
        if 0 <= index < len(self.video_files):
            self.current_video_index = index
            self.video_list.setCurrentRow(index)  # move selector
            item = self.video_list.item(index)
            if item:
                # Clear scene markers when switching videos
                if hasattr(self, 'slider') and hasattr(self.slider, 'clear_scene_markers'):
                    self.slider.clear_scene_markers()
                self.current_scenes = []
                
                self.loader.load_video(item)
                if not self.is_playing:
                    self.editor.toggle_play_forward()  # Auto-play like gui-videotrim

    def play_next_file(self):
        # Advance to next video, wrapping to top at end
        if not self.video_files:
            return
        next_index = (self.current_video_index + 1) % len(self.video_files)
        self.on_video_selected(next_index)


    def delete_selected_video(self):
        selected_row = self.video_list.currentRow()
        selected_item = self.video_list.currentItem()
        if not selected_item:
            return
        video_name = selected_item.text()
        # Find the matching entry in video_files based on display name.
        entry = next((e for e in self.video_files if e["display_name"] == video_name), None)
        if not entry:
            return
        original_path = entry["original_path"]
        base_folder = self.folder_path if self.folder_path else os.getcwd()
        backup_folder = os.path.join(base_folder, "trash_backup")
        os.makedirs(backup_folder, exist_ok=True)
        backup_path = os.path.join(backup_folder, os.path.basename(original_path))
        try:
            # If the video is currently open, release the capture.
            if self.cap is not None and self.current_video == video_name:
                self.cap.release()
                self.cap = None
            shutil.move(original_path, backup_path)
            self.deleted_clips_stack.append({
                "entry": entry, 
                "backup_path": backup_path,
                "original_path": original_path,
                "index": selected_row
            })
            self.video_files.remove(entry)
            self.video_list.takeItem(selected_row)
            self.update_file_count()
            print(f"Deleted {video_name} and moved to backup.")

            # --- Fix: Select and preview the correct next item after deletion ---
            count = self.video_list.count()
            if count > 0:
                # If we deleted the last item, move selection up, else stay at same index
                next_row = min(selected_row, count - 1)
                self.video_list.setCurrentRow(next_row)
                # Force load the video at the new row
                item = self.video_list.item(next_row)
                if item:
                    self.loader.load_video(item)
                    self.current_video_index = next_row
            else:
                self.current_video = None  # No videos left
        except Exception as e:
            print(f"Error deleting file: {e}")
            
    def undo_delete_video(self):
        """Restore the most recently deleted video from trash_backup"""
        if not self.deleted_clips_stack:
            print("No deleted videos to restore")
            return
            
        deleted_info = self.deleted_clips_stack.pop()
        backup_path = deleted_info["backup_path"]
        original_path = deleted_info["original_path"]
        original_index = deleted_info["index"]
        entry = deleted_info["entry"]
        
        try:
            # Restore the file from backup
            if os.path.exists(backup_path):
                # Make sure the directory exists
                os.makedirs(os.path.dirname(original_path), exist_ok=True)
                shutil.move(backup_path, original_path)
                
                # Re-add to video_files and video_list
                self.video_files.insert(original_index, entry)
                self.video_list.insertItem(original_index, entry["display_name"])
                self.update_file_count()
                
                # Select and load the restored video
                self.video_list.setCurrentRow(original_index)
                self.loader.load_video(self.video_list.item(original_index))
                print(f"Restored {os.path.basename(original_path)} from trash")
            else:
                print(f"Backup file not found: {backup_path}")
                
        except Exception as e:
            print(f"Error restoring video: {e}")
            # Add back to stack if restore failed
            self.deleted_clips_stack.append(deleted_info)

    def undo_delete_video(self):
        if not self.deleted_clips_stack:
            return
        last_deleted = self.deleted_clips_stack.pop()
        entry = last_deleted["entry"]
        backup_path = last_deleted["backup_path"]
        original_path = entry["original_path"]
        try:
            shutil.move(backup_path, original_path)
            self.video_files.append(entry)
            self.add_video_item(entry["display_name"])
            self.update_file_count()
            print(f"Restored {entry['display_name']} from backup.")
        except Exception as e:
            print(f"Error restoring file: {e}")

    def update_folder_tree(self, current_path):
        """Update the folder tree view to show parent, siblings, current, and subfolders.
        The current folder is shown inline with its siblings, with its subfolders as children."""
        import os
        from PyQt6.QtWidgets import QTreeWidgetItem
        self.folder_tree.clear()
        parent_path = os.path.dirname(current_path)
        current_basename = os.path.basename(current_path)

        # If we're at root level, just show current directory and its subfolders
        if not parent_path or parent_path == current_path:
            root_item = QTreeWidgetItem([current_basename])
            root_item.setData(0, Qt.ItemDataRole.UserRole, current_path)
            self.folder_tree.addTopLevelItem(root_item)
            self.folder_tree.setCurrentItem(root_item)
            
            # Add subfolders
            try:
                for entry in os.scandir(current_path):
                    if entry.is_dir():
                        child_item = QTreeWidgetItem([entry.name])
                        child_item.setData(0, Qt.ItemDataRole.UserRole, entry.path)
                        root_item.addChild(child_item)
            except Exception as e:
                print(f"Error listing subfolders: {e}")
            root_item.setExpanded(True)
            return

        # For non-root directories, show parent with all siblings (including current)
        parent_item = QTreeWidgetItem(['..'])
        parent_item.setData(0, Qt.ItemDataRole.UserRole, parent_path)
        
        # Add all sibling folders (including current) as children of parent
        current_item = None
        try:
            # First pass: add all items
            for entry in os.scandir(parent_path):
                if entry.is_dir():
                    sibling_item = QTreeWidgetItem([entry.name])
                    sibling_item.setData(0, Qt.ItemDataRole.UserRole, entry.path)
                    
                    # If this is the current folder, add its subfolders and store reference
                    if entry.path == current_path:
                        current_item = sibling_item
                        try:
                            for sub_entry in os.scandir(entry.path):
                                if sub_entry.is_dir():
                                    child_item = QTreeWidgetItem([sub_entry.name])
                                    child_item.setData(0, Qt.ItemDataRole.UserRole, sub_entry.path)
                                    sibling_item.addChild(child_item)
                        except Exception as e:
                            print(f"Error listing subfolders: {e}")
                    
                    parent_item.addChild(sibling_item)
        except Exception as e:
            print(f"Error listing siblings: {e}")
        
        self.folder_tree.addTopLevelItem(parent_item)
        
        # Expand parent and current folder, and ensure current folder is selected and visible
        parent_item.setExpanded(True)
        if current_item:
            current_item.setExpanded(True)  # Ensure current folder is expanded
            self.folder_tree.setCurrentItem(current_item)
            self.folder_tree.scrollToItem(current_item)
            
            # Force update the tree widget to ensure expansion is visible
            self.folder_tree.update()
            QApplication.processEvents()


    def on_folder_tree_clicked(self, item, column):
        """Handle folder selection from the tree view"""
        folder_path = item.data(0, Qt.ItemDataRole.UserRole)
        if folder_path and os.path.exists(folder_path):
            self.folder_path = folder_path
            self.loader.folder_path = folder_path
            # If this is not the parent directory (..), expand it to show subfolders
            if os.path.basename(folder_path) != '..':
                item.setExpanded(True)
            self.loader.load_folder_contents()
            self.update_folder_tree(folder_path)
            self.update_file_count()
        elif folder_path:
            QMessageBox.warning(self, "Invalid Folder", "The selected folder no longer exists.")

    def adjust_multi_performance(self, target_fps=15, skip_frames=2):
        """Adjust multi-mode playback performance settings."""
        self.multi_target_fps = target_fps
        self.multi_skip_frames = skip_frames
        if hasattr(self, 'multi_timer'):
            self.multi_timer.setInterval(1000 // self.multi_target_fps)
            
    def detect_scenes_for_current_video(self):
        """Start or stop scene detection for the current video"""
        # If detection is in progress, stop it
        if self.scene_detection_in_progress:
            self.stop_scene_detection()
            return
            
        if not self.current_video or not self.video_files:
            return
            
        # Find the current video entry
        current_entry = None
        for entry in self.video_files:
            if entry["display_name"] == self.current_video:
                current_entry = entry
                break
                
        if not current_entry:
            return
            
        video_path = current_entry["original_path"]
        
        # Show progress UI
        self.scene_progress_label.setVisible(True)
        self.scene_progress_bar.setVisible(True)
        self.scene_progress_bar.setValue(0)
        self.detect_scenes_button.setEnabled(True)
        self.detect_scenes_button.setText("Stop Detection")
        
        # Reset flags and start detection
        self.scene_detection_in_progress = True
        self.scene_detection_stop_requested = False
        
        # Start scene detection in background
        self.scene_detection_thread = self.scene_detector.detect_scenes_async(video_path)
        
    def on_scene_detection_progress(self, progress):
        """Update progress bar during scene detection"""
        self.scene_progress_bar.setValue(progress)
        
    def on_scenes_detected(self, scenes):
        """Handle detected scenes"""
        self.current_scenes = scenes
        print(f"Detected {len(scenes)} scenes")
        
        # Extract start frames for scene markers
        scene_start_frames = [scene[0] for scene in scenes]
        
        # Update the slider with scene markers
        if hasattr(self, 'slider') and hasattr(self.slider, 'set_scene_markers'):
            self.slider.set_scene_markers(scene_start_frames)
            
        # Update status
        self.status_label.setText(f"Detected {len(scenes)} scenes - Use ` or 0 for start, Ctrl+0 for scene 11, Ctrl+1-9 for scenes 2-10, Ctrl+-/= for scenes 13-14, Ctrl+Q-\\ for scenes 15-27")
        
    def stop_scene_detection(self):
        """Stop the running scene detection"""
        if self.scene_detection_in_progress:
            self.scene_detection_stop_requested = True
            self.scene_detector.stop_detection = True
            self.scene_detection_in_progress = False
            self.detect_scenes_button.setEnabled(False)
            self.detect_scenes_button.setText("Stopping...")
    
    def on_scene_detection_finished(self):
        """Handle scene detection completion"""
        # Update UI based on whether we stopped or finished
        if self.scene_detection_stop_requested:
            self.status_label.setText("Scene detection stopped")
        
        # Hide progress UI
        self.scene_progress_label.setVisible(False)
        self.scene_progress_bar.setVisible(False)
        self.detect_scenes_button.setEnabled(True)
        self.detect_scenes_button.setText("Detect Scenes")
        self.scene_detection_in_progress = False
        self.scene_detection_stop_requested = False
        
    def on_scene_marker_clicked(self, scene_index):
        """Handle clicking on a scene marker"""
        self.jump_to_scene_by_index(scene_index)



    def _clear_layout(self, layout):
        """Recursively clear all widgets and layouts."""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self._clear_layout(item.layout())
            QWidget().setLayout(layout)
    
    def display_video_metadata(self, video_entry):
        """Display or toggle detailed metadata for a video file."""
        # If dialog exists and is visible, hide it and return
        if hasattr(self, 'metadata_dialog') and self.metadata_dialog:
            if self.metadata_dialog.isVisible():
                self.metadata_dialog.hide()
                return
            # Clean up the existing dialog
            try:
                self.metadata_dialog.deleteLater()
            except RuntimeError:
                pass  # Widget already deleted
        
        # Create a new dialog
        try:
            self.metadata_dialog = QDialog(self)
            self.metadata_dialog.setWindowTitle("Video Metadata")
            self.metadata_dialog.resize(800, 600)
            self.metadata_dialog.setWindowFlags(self.metadata_dialog.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
            
            # Handle key events for the dialog
            def dialog_key_press(event):
                if event.key() == Qt.Key.Key_Escape or (event.key() == Qt.Key.Key_I and event.modifiers() == Qt.KeyboardModifier.NoModifier):
                    self.metadata_dialog.hide()
                    return
                super(type(self.metadata_dialog), self.metadata_dialog).keyPressEvent(event)
            
            self.metadata_dialog.keyPressEvent = dialog_key_press
            
            # Set a style sheet to ensure proper background and text colors
            self.metadata_dialog.setStyleSheet("""
                QDialog {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QTextEdit {
                    background-color: #3a3a3a;
                    color: #ffffff;
                    border: 1px solid #555555;
                    border-radius: 3px;
                    padding: 5px;
                }
            """)
        except Exception as e:
            print(f"Error creating metadata dialog: {e}")
            return
            
        if not video_entry or "original_path" not in video_entry:
            print("Error: Invalid video entry")
            return
            
        video_path = video_entry["original_path"]
        metadata = {
            "File": os.path.basename(video_path),
            "Path": video_path,
            "Size": f"{os.path.getsize(video_path) / (1024*1024):.2f} MB",
            "Created": datetime.fromtimestamp(os.path.getctime(video_path)).strftime('%Y-%m-%d %H:%M:%S'),
            "Modified": datetime.fromtimestamp(os.path.getmtime(video_path)).strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        # Get video properties using OpenCV
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            metadata.update({
                "Resolution": f"{int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}",
                "FPS": f"{cap.get(cv2.CAP_PROP_FPS):.2f}",
                "Frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                "Duration (s)": f"{int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / max(1, cap.get(cv2.CAP_PROP_FPS)):.2f}",
            })
            cap.release()
        
        # Try to get metadata using ffprobe if available
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', video_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode == 0:
                ffprobe_data = json.loads(result.stdout)
                
                # Extract format metadata
                if 'format' in ffprobe_data:
                    fmt = ffprobe_data['format']
                    metadata.update({
                        'Format': fmt.get('format_name', 'N/A'),
                        'Bitrate': f"{int(fmt.get('bit_rate', 0)) / 1000:.1f} kb/s" if 'bit_rate' in fmt else 'N/A',
                    })
                    
                    # Look for prompt/workflow in format tags
                    if 'tags' in fmt:
                        tags = fmt['tags']
                        for key in ['comment', 'description', 'title', 'purl', 'purl:comment', 'purl:description']:
                            if key in tags and tags[key].strip():
                                metadata['Comment'] = tags[key].strip()
                                break
                
                # Extract video stream metadata
                if 'streams' in ffprobe_data:
                    for stream in ffprobe_data['streams']:
                        if stream['codec_type'] == 'video':
                            metadata.update({
                                'Video Codec': stream.get('codec_long_name', stream.get('codec_name', 'N/A')),
                                'Bit Depth': f"{stream.get('bits_per_raw_sample', stream.get('bits_per_sample', 'N/A'))} bits",
                                'Color Space': stream.get('color_space', 'N/A'),
                                'Color Range': stream.get('color_range', 'N/A'),
                                'Color Primaries': stream.get('color_primaries', 'N/A'),
                                'Color Transfer': stream.get('color_transfer', 'N/A')
                            })
                            break
        except Exception as e:
            print(f"Error getting ffprobe metadata: {e}")
        
        # Create or reuse metadata dialog
        if not hasattr(self, 'metadata_dialog') or not self.metadata_dialog:
            self.metadata_dialog = QDialog(self)
            self.metadata_dialog.setWindowTitle("Video Metadata")
            self.metadata_dialog.resize(800, 600)  # Increased width for better prompt display
            self.metadata_dialog.setWindowFlags(self.metadata_dialog.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
            
            # Handle key events for the dialog
            def dialog_key_press(event):
                if event.key() == Qt.Key.Key_Escape or (event.key() == Qt.Key.Key_I and event.modifiers() == Qt.KeyboardModifier.NoModifier):
                    self.metadata_dialog.hide()
                    return
                super(type(self.metadata_dialog), self.metadata_dialog).keyPressEvent(event)
            
            self.metadata_dialog.keyPressEvent = dialog_key_press
            
            # Set a style sheet to ensure proper background and text colors
            self.metadata_dialog.setStyleSheet("""
                QDialog {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QTextEdit {
                    background-color: #3a3a3a;
                    color: #ffffff;
                    border: 1px solid #555555;
                    border-radius: 3px;
                    padding: 5px;
                }
            """)
        
        # Clear previous content and create new layout
        layout = QVBoxLayout()
        
        # Clear any existing layout and widgets
        if self.metadata_dialog.layout():
            old_layout = self.metadata_dialog.layout()
            self._clear_layout(old_layout)
            
        # Set the new layout
        self.metadata_dialog.setLayout(layout)
        
        # Always show basic metadata
        basic_metadata = QTextEdit()
        basic_metadata.setReadOnly(True)
        basic_metadata.setFontFamily("Courier New")
        basic_metadata.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        
        # Format basic metadata
        metadata_text = ""
        for key, value in metadata.items():
            if key != 'Comment':  # We'll handle comment separately
                metadata_text += f"<b>{key}:</b> {value}<br>"
        
        basic_metadata.setHtml(metadata_text)
        layout.addWidget(QLabel("<h3>Basic Information</h3>"))
        layout.addWidget(basic_metadata)
        
        # Show prompt section if available
        if 'Comment' in metadata and 'prompt' in metadata['Comment']:
            try:
                # Extract the JSON part from the comment
                comment = metadata['Comment']
                # Find the first { and last } to get the JSON object
                start = comment.find('{')
                end = comment.rfind('}') + 1
                if start != -1 and end != -1:
                    json_str = comment[start:end]
                    # Parse the JSON
                    prompt_data = json.loads(json_str)
                    
                    # Extract all text from ShowText nodes
                    comment_str = json.dumps(prompt_data)
                    text_entries = []
                    
                    # Look for all ShowText nodes and extract their text
                    pattern = r'"Node name for S&R": "ShowText\|[^"]+", "widget_ue_connectable": {}}, "widgets_values": \[\["([^\]]+)\]\]'
                    matches = re.findall(pattern, comment_str)
                    
                    if matches:
                        # Clean up each match (remove any extra quotes or brackets)
                        for match in matches:
                            # Remove any trailing quotes or brackets
                            clean_text = match.split('"')[0].strip()
                            if clean_text:
                                text_entries.append(clean_text)
                    
                    # If we found text entries, create a scrollable list with copy buttons
                    if text_entries:
                        scroll = QScrollArea()
                        scroll_widget = QWidget()
                        scroll_layout = QVBoxLayout(scroll_widget)
                        
                        for i, text in enumerate(text_entries):
                            entry_widget = QWidget()
                            entry_layout = QHBoxLayout(entry_widget)
                            entry_layout.setContentsMargins(0, 0, 0, 5)
                            
                            # Create a text edit for better wrapping
                            text_edit = QTextEdit(f"{i+1}. {text}")
                            text_edit.setReadOnly(True)
                            text_edit.setFrameStyle(QFrame.Shape.NoFrame)
                            text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)  # Show scrollbar when needed
                            text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                            text_edit.setStyleSheet("""
                                QTextEdit {
                                    padding: 8px;
                                    border: 1px solid #444;
                                    border-radius: 3px;
                                    background-color: #2a2a2a;
                                    color: white;
                                    font-size: 11pt;
                                    line-height: 1.4;
                                }
                                QTextEdit:hover {
                                    background-color: #3a3a3a;
                                    border: 1px solid #666;
                                }
                                QScrollBar:vertical {
                                    width: 10px;
                                    margin: 0px;
                                }
                            """)
                            text_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                            
                            # Set a reasonable fixed height that shows more text by default
                            text_edit.setMinimumHeight(80)  # Increased minimum height
                            text_edit.setMaximumHeight(300)  # Increased maximum height
                            
                            # Add a copy button
                            copy_btn = QPushButton("Copy")
                            copy_btn.setFixedWidth(60)
                            copy_btn.setProperty("text_to_copy", text)  # Store the clean text
                            copy_btn.clicked.connect(lambda checked, t=text: QApplication.clipboard().setText(t))
                            
                            # Make the label clickable to copy
                            def on_label_clicked(event, t=text):
                                QApplication.clipboard().setText(t)
                                
                            text_edit.mousePressEvent = on_label_clicked
                            
                            entry_layout.addWidget(text_edit, 1)  # Text takes available space
                            entry_layout.addWidget(copy_btn)       # Button stays right-aligned
                            scroll_layout.addWidget(entry_widget)
                        
                        # Add stretch to push everything to the top
                        scroll_layout.addStretch()
                        
                        # Set up the scroll area
                        scroll.setWidgetResizable(True)
                        scroll.setWidget(scroll_widget)
                        
                        # Add the scroll area to the main layout
                        layout.addWidget(scroll)
                        
                        # Add buttons at the bottom
                        button_layout = QHBoxLayout()
                        
                        # Copy All button
                        copy_all_btn = QPushButton("Copy All")
                        copy_all_btn.clicked.connect(lambda: QApplication.clipboard().setText('\n'.join(text_entries)))
                        
                        # Close button
                        close_btn = QPushButton("Close")
                        close_btn.clicked.connect(self.metadata_dialog.hide)
                        
                        button_layout.addWidget(copy_all_btn)
                        button_layout.addStretch()
                        button_layout.addWidget(close_btn)
                        
                        layout.addLayout(button_layout)
                        
                        # Set the layout and show the dialog
                        self.metadata_dialog.setLayout(layout)
                        self.metadata_dialog.show()
                        self.metadata_dialog.raise_()
                        self.metadata_dialog.activateWindow()
                        # Ensure the dialog is properly closed when the main window is closed
                        self.metadata_dialog.finished.connect(lambda: setattr(self.metadata_dialog, 'is_visible', False))
                        return
                    
                    # Fallback to old method if no matches found
                    elif isinstance(prompt_data, dict) and "widgets_values" in prompt_data:
                        widgets_values = prompt_data["widgets_values"]
                        if widgets_values and isinstance(widgets_values, list) and len(widgets_values) > 0:
                            first_value = widgets_values[0]
                            if isinstance(first_value, list) and len(first_value) > 0:
                                display_text = first_value[0]
                            else:
                                display_text = str(first_value)
                    
                    # If still no text, show the full JSON
                    if not display_text:
                        display_text = json.dumps(prompt_data, indent=2)
                    
                    # Create prompt display for non-matching format
                    prompt_text = QTextEdit()
                    prompt_text.setReadOnly(True)
                    prompt_text.setFontFamily("Courier New")
                    prompt_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
                    prompt_text.setWordWrapMode(QTextOption.WrapMode.WordWrap)
                    prompt_text.setPlainText(display_text)
                    
                    # Add buttons at the bottom
                    button_layout = QHBoxLayout()
                    
                    # Copy button
                    copy_btn = QPushButton("Copy to Clipboard")
                    copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(display_text))
                    
                    # Close button
                    close_btn = QPushButton("Close")
                    close_btn.clicked.connect(self.metadata_dialog.hide)
                    
                    # Add widgets to the main layout
                    layout.addWidget(prompt_text)
                    button_layout.addStretch()
                    button_layout.addWidget(copy_btn)
                    button_layout.addWidget(close_btn)
                    layout.addLayout(button_layout)
                    
            except json.JSONDecodeError as e:
                print(f"Error parsing prompt JSON: {e}")
                # Fall back to showing raw comment if JSON parsing fails
                if 'Comment' in metadata:
                    prompt_text = QTextEdit()
                    prompt_text.setReadOnly(True)
                    prompt_text.setFontFamily("Courier New")
                    prompt_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
                    prompt_text.setWordWrapMode(QTextOption.WrapMode.WordWrap)
                    prompt_text.setPlainText(metadata['Comment'])
                    
                    # Add buttons at the bottom
                    button_layout = QHBoxLayout()
                    
                    # Copy button
                    copy_btn = QPushButton("Copy to Clipboard")
                    copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(metadata['Comment']))
                    
                    # Close button
                    close_btn = QPushButton("Close")
                    close_btn.clicked.connect(self.metadata_dialog.hide)
                    
                    # Add widgets to the main layout
                    layout.addWidget(prompt_text)
                    button_layout.addStretch()
                    button_layout.addWidget(copy_btn)
                    button_layout.addWidget(close_btn)
                    layout.addLayout(button_layout)
        
        # Set the layout and show the dialog
        self.metadata_dialog.setLayout(layout)
        
        # Force update the window title with the current video name
        if 'File' in metadata:
            self.metadata_dialog.setWindowTitle(f"Metadata - {metadata['File']}")
        else:
            self.metadata_dialog.setWindowTitle("Video Metadata")
            
        # Always show and raise the dialog to ensure it's visible
        self.metadata_dialog.show()
        self.metadata_dialog.raise_()
        self.metadata_dialog.activateWindow()
        
        # Ensure the dialog gets focus
        self.metadata_dialog.setFocus()

    def jump_to_scene_by_index(self, scene_index):
        """Jump to a specific scene by index (0-based)"""
        if not hasattr(self, 'current_scenes') or not self.current_scenes:
            return
            
        if 0 <= scene_index < len(self.current_scenes):
            frame_pos = self.current_scenes[scene_index]
            if hasattr(self, 'cap') and self.cap is not None:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
                ret, frame = self.cap.read()
                if ret:
                    self.editor.display_frame(frame)
                    self.slider.setValue(int(frame_pos))
                    self.current_frame_pos = int(frame_pos)
                    self.status_label.setText(f"Jumped to Scene {scene_index + 1}")
                    print(f"Successfully jumped to scene {scene_index + 1} at frame {frame_pos}")
            else:
                self.status_label.setText(f"Scene {scene_index + 1} not found")
                print(f"Scene {scene_index + 1} not found (total scenes: {len(self.current_scenes)})")

# --- Patch: Import shortcut handler and assign to VideoCropper ---
from scripts.shortcut_elements import keyPressEvent as shortcut_keyPressEvent

def multi_mode_keyPressEvent(self, event):
    if getattr(self, 'multi_mode', False) and getattr(self, 'multi_video_widgets', None):
        key = event.key()
        modifiers = event.modifiers()
        
        # --- Grid Rearrangement Shortcuts ---
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_Left:
                # Swap focused grid with the one to its left
                focused = getattr(self, 'multi_focused_grid', 0)
                if focused > 0:
                    self._on_video_drag_drop(focused, focused - 1)
                    self.multi_focused_grid = focused - 1
                    self._highlight_multi_videos()
                    self.update_status(f"Swapped Grid {focused + 1} ↔ Grid {focused}")
                    return
            elif key == Qt.Key.Key_Right:
                # Swap focused grid with the one to its right
                focused = getattr(self, 'multi_focused_grid', 0)
                if focused < len(self.multi_video_widgets) - 1:
                    self._on_video_drag_drop(focused, focused + 1)
                    self.multi_focused_grid = focused + 1
                    self._highlight_multi_videos()
                    self.update_status(f"Swapped Grid {focused + 1} ↔ Grid {focused + 2}")
                    return
            elif key == Qt.Key.Key_Up:
                # Swap focused grid with the one above it
                focused = getattr(self, 'multi_focused_grid', 0)
                cols = self._calculate_grid_columns(len(self.multi_video_widgets))
                if focused >= cols:  # Not in the top row
                    target = focused - cols
                    self._on_video_drag_drop(focused, target)
                    self.multi_focused_grid = target
                    self._highlight_multi_videos()
                    self.update_status(f"Swapped Grid {focused + 1} ↔ Grid {target + 1}")
                    return
            elif key == Qt.Key.Key_Down:
                # Swap focused grid with the one below it
                focused = getattr(self, 'multi_focused_grid', 0)
                cols = self._calculate_grid_columns(len(self.multi_video_widgets))
                if focused + cols < len(self.multi_video_widgets):  # Not in the bottom row
                    target = focused + cols
                    self._on_video_drag_drop(focused, target)
                    self.multi_focused_grid = target
                    self._highlight_multi_videos()
                    self.update_status(f"Swapped Grid {focused + 1} ↔ Grid {target + 1}")
                    return
        
        # --- Multi-Video Preview Mode Toggle (Shift+Y) - MUST BE FIRST ---
        if key == Qt.Key.Key_Y and modifiers == Qt.KeyboardModifier.ShiftModifier:
            print(f"DEBUG: Shift+Y pressed in multi-mode - key: {key}, modifiers: {modifiers}")
            if not hasattr(self, '_preview_mode'):
                self._preview_mode = False
            self._preview_mode = not self._preview_mode
            if self._preview_mode:
                try:
                    # Hide main window
                    self._prev_geometry = self.geometry()
                    self._prev_window_state = self.windowState()
                    self.hide()
                    # Create preview window with custom responsive layout
                    self._preview_window = QWidget()
                    self._preview_window.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
                    self._preview_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
                    
                    # Create a custom container widget that will handle the responsive layout
                    self._preview_container = QWidget(self._preview_window)
                    self._preview_container.setStyleSheet("background-color: black;")
                    
                    # Add a custom resize event handler to the container
                    def container_resizeEvent(ev):
                        try:
                            print(f"DEBUG: Container resize event - size: {ev.size().width()}x{ev.size().height()}")
                            # Trigger the window resize handler
                            if hasattr(self, '_preview_window') and self._preview_window.resizeEvent:
                                self._preview_window.resizeEvent(ev)
                        except Exception as e:
                            print(f"Error in container resize handler: {e}")
                        QWidget.resizeEvent(self._preview_container, ev)
                    
                    self._preview_container.resizeEvent = container_resizeEvent
                    
                    # Move all video cells to the preview container
                    for cell in self.multi_video_widgets:
                        cell.setParent(self._preview_container)
                    
                    layout = QVBoxLayout(self._preview_window)
                    layout.setContentsMargins(0,0,0,0)
                    layout.setSpacing(0)
                    layout.addWidget(self._preview_container)
                    
                    # Set proper size policies for responsive layout
                    self.multi_grid_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                    for cell in self.multi_video_widgets:
                        if hasattr(cell, 'setSizePolicy'):
                            cell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                        if hasattr(cell, 'video_widget') and hasattr(cell.video_widget, 'setSizePolicy'):
                            cell.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                    
                    # Set a larger initial size that can be bigger than the main UI
                    num_videos = len(self.multi_video_widgets)
                    if num_videos <= 2:
                        initial_width = 1200
                        initial_height = 600
                    elif num_videos <= 4:
                        initial_width = 1200
                        initial_height = 800
                    elif num_videos <= 6:
                        initial_width = 1400
                        initial_height = 900
                    else:
                        initial_width = 1600
                        initial_height = 1000
                    
                    # Set up initial video positioning in the preview container
                    cols = self._calculate_grid_columns(num_videos)
                    
                    rows = (num_videos + cols - 1) // cols
                    cell_width = initial_width // cols
                    cell_height = initial_height // rows
                    
                    # Position all videos in the preview container
                    for i, cell in enumerate(self.multi_video_widgets):
                        row = i // cols
                        col = i % cols
                        x = col * cell_width
                        y = row * cell_height
                        cell.setGeometry(x, y, cell_width, cell_height)
                        if hasattr(cell, 'video_widget'):
                            cell.video_widget.setGeometry(0, 0, cell_width, cell_height)
                    
                    # Now resize the window after layout is set up
                    self._preview_window.resize(initial_width, initial_height)
                    
                    # Force layout update to ensure all videos fit properly
                    self.multi_grid_widget.updateGeometry()
                    # Center preview window on screen
                    screen = QApplication.primaryScreen().geometry()
                    x = screen.center().x() - initial_width // 2
                    y = screen.center().y() - initial_height // 2
                    self._preview_window.move(x, y)
                    self._preview_window.show()
                    self._preview_window.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                    self._preview_window.setFocus()
                    self._preview_window.raise_()
                    
                    # Trigger initial resize to ensure proper layout
                    QTimer.singleShot(100, lambda: preview_resizeEvent(None))
                    def esc_close(event):
                        # --- Minimize preview window on Backspace ---
                        if event.key() == Qt.Key.Key_Backspace:
                            self._preview_window.showMinimized()
                            return
                        if event.key() == Qt.Key.Key_Q:
                            QApplication.quit()
                            return
                        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Y):
                            self._preview_mode = False
                            self._preview_window.close()
                            
                            # Restore all video cells back to the multi grid widget
                            for cell in self.multi_video_widgets:
                                cell.setParent(self.multi_grid_widget)
                            
                            # Properly restore multi mode layout
                            self._restore_multi_mode_layout()
                            
                            self.showNormal()
                            self.setGeometry(self._prev_geometry)
                            self.setWindowState(self._prev_window_state)
                            self.show()
                            event.accept()
                            return
                        self.keyPressEvent(event)
                    
                    def preview_wheel_event(event):
                        """Handle wheel events in preview window"""
                        # Find which cell the mouse is over
                        mouse_pos = event.position()
                        for cell in self.multi_video_widgets:
                            if cell.geometry().contains(mouse_pos.toPoint()):
                                # Directly call the cell's wheelEvent method
                                cell.wheelEvent(event)
                                event.accept()
                                return
                        event.ignore()
                    
                    self._preview_window.keyPressEvent = esc_close
                    self._preview_window.wheelEvent = preview_wheel_event
                    self.multi_grid_widget.keyPressEvent = esc_close
                    self.multi_grid_widget.setMinimumSize(200, 150)
                    # --- Add resize handler that actually scales videos to fit ---
                    def preview_resizeEvent(ev):
                        try:
                            # Handle None event case
                            if ev is None:
                                # Use current window size
                                window_size = self._preview_window.size()
                                print(f"DEBUG: Preview window resize event triggered - size: {window_size.width()}x{window_size.height()}")
                            else:
                                print(f"DEBUG: Preview window resize event triggered - size: {ev.size().width()}x{ev.size().height()}")
                            
                            # Get the available space in the preview container
                            container_width = self._preview_container.width()
                            container_height = self._preview_container.height()
                            
                            print(f"DEBUG: Container size: {container_width}x{container_height}")
                            
                            if container_width < 50 or container_height < 50:
                                print("DEBUG: Container too small, skipping resize")
                                if ev is not None:
                                    QWidget.resizeEvent(self._preview_window, ev)
                                return
                            
                            num_videos = len(self.multi_video_widgets)
                            if num_videos == 0:
                                print("DEBUG: No videos to resize")
                                if ev is not None:
                                    QWidget.resizeEvent(self._preview_window, ev)
                                return
                            
                            # Calculate optimal grid layout using the same logic as main grid
                            cols = self._calculate_grid_columns(num_videos)
                            
                            rows = (num_videos + cols - 1) // cols
                            
                            # Calculate cell dimensions to fit ALL videos in the available space
                            cell_width = container_width // cols
                            cell_height = container_height // rows
                            
                            print(f"DEBUG: Grid layout: {cols}x{rows}, Cell size: {cell_width}x{cell_height}")
                            
                            # Position and size each video cell
                            for i, cell in enumerate(self.multi_video_widgets):
                                row = i // cols
                                col = i % cols
                                
                                # Calculate position
                                x = col * cell_width
                                y = row * cell_height
                                
                                print(f"DEBUG: Positioning cell {i} at ({x}, {y}) with size {cell_width}x{cell_height}")
                                
                                # Set the cell to exactly fit in its grid position
                                cell.setGeometry(x, y, cell_width, cell_height)
                                
                                # Ensure the video widget fills the cell
                                if hasattr(cell, 'video_widget'):
                                    cell.video_widget.setGeometry(0, 0, cell_width, cell_height)
                            
                            # Force update
                            self._preview_container.update()
                            
                        except Exception as e:
                            print(f"Error in preview resize handler: {e}")
                            import traceback
                            traceback.print_exc()
                        
                        if ev is not None:
                            QWidget.resizeEvent(self._preview_window, ev)
                    
                    # Store the original resizeEvent method
                    original_resizeEvent = self._preview_window.resizeEvent
                    self._preview_window.resizeEvent = preview_resizeEvent
                    
                    # Also add a timer to handle resize events that might be missed
                    resize_timer = QTimer()
                    resize_timer.setSingleShot(True)
                    resize_timer.setInterval(100)  # 100ms delay
                    
                    def delayed_resize():
                        if hasattr(self, '_preview_window') and self._preview_window.isVisible():
                            preview_resizeEvent(None)
                    
                    resize_timer.timeout.connect(delayed_resize)
                    
                    # Connect the timer to window resize events
                    def on_window_resize():
                        resize_timer.start()
                    
                    self._preview_window.resizeEvent = lambda ev: (preview_resizeEvent(ev), on_window_resize())
                except Exception as e:
                    # If anything goes wrong, restore the main window
                    print(f"Error in Shift+Y preview mode: {e}")
                    self._preview_mode = False
                    if hasattr(self, '_preview_window'):
                        self._preview_window.close()
                    self.showNormal()
                    self.setGeometry(self._prev_geometry)
                    self.setWindowState(self._prev_window_state)
                    self.show()
                    QMessageBox.warning(self, "Preview Error", f"Failed to open preview window: {e}")
            else:
                # --- Restore from Preview Mode ---
                if hasattr(self, '_preview_window'):
                    self._preview_window.close()
                    # Restore correct widget to main window
                    if hasattr(self, 'multi_grid_widget'):
                        self.multi_grid_widget.setParent(None)
                        # Properly restore multi mode layout
                        self._restore_multi_mode_layout()
                    self.showNormal()
                    self.setGeometry(self._prev_geometry)
                    self.setWindowState(self._prev_window_state)
                    self.show()
            return
        
        focused = getattr(self, 'multi_focused_grid', 0)
        if focused >= len(self.multi_video_widgets):
            focused = 0
        cell = self.multi_video_widgets[focused]
        
        # --- Frame Adjustment Shortcuts for Highlighted Grid ---
        # Handle F/D keys for frame adjustment (like in single mode)
        if modifiers == Qt.KeyboardModifier.NoModifier:
            if key in (Qt.Key.Key_F, Qt.Key.Key_Right):
                # Move forward by trim_length
                current_pos = cell.player.position()
                duration = cell.player.duration()
                # Calculate frame duration (assuming 30 FPS)
                fps = 30
                frame_duration_ms = 1000 / fps
                new_pos = min(current_pos + (self.trim_length * frame_duration_ms), duration)
                cell.player.setPosition(int(new_pos))
                self.update_status(f"Grid {focused+1}: Forward {self.trim_length} frames")
                return
            elif key in (Qt.Key.Key_D, Qt.Key.Key_Left):
                # Move backward by trim_length
                current_pos = cell.player.position()
                # Calculate frame duration (assuming 30 FPS)
                fps = 30
                frame_duration_ms = 1000 / fps
                new_pos = max(current_pos - (self.trim_length * frame_duration_ms), 0)
                cell.player.setPosition(int(new_pos))
                self.update_status(f"Grid {focused+1}: Backward {self.trim_length} frames")
                return
        elif modifiers == Qt.KeyboardModifier.ShiftModifier:
            if key in (Qt.Key.Key_F, Qt.Key.Key_Right):
                # Move forward by trim_length * 4
                current_pos = cell.player.position()
                duration = cell.player.duration()
                # Calculate frame duration (assuming 30 FPS)
                fps = 30
                frame_duration_ms = 1000 / fps
                new_pos = min(current_pos + (self.trim_length * 4 * frame_duration_ms), duration)
                cell.player.setPosition(int(new_pos))
                self.update_status(f"Grid {focused+1}: Forward {self.trim_length * 4} frames")
                return
            elif key in (Qt.Key.Key_D, Qt.Key.Key_Left):
                # Move backward by trim_length * 4
                current_pos = cell.player.position()
                # Calculate frame duration (assuming 30 FPS)
                fps = 30
                frame_duration_ms = 1000 / fps
                new_pos = max(current_pos - (self.trim_length * 4 * frame_duration_ms), 0)
                cell.player.setPosition(int(new_pos))
                self.update_status(f"Grid {focused+1}: Backward {self.trim_length * 4} frames")
                return
        elif modifiers == Qt.KeyboardModifier.ControlModifier:
            if key in (Qt.Key.Key_F, Qt.Key.Key_Right):
                # Move forward by trim_length * 2
                current_pos = cell.player.position()
                duration = cell.player.duration()
                # Calculate frame duration (assuming 30 FPS)
                fps = 30
                frame_duration_ms = 1000 / fps
                new_pos = min(current_pos + (self.trim_length * 2 * frame_duration_ms), duration)
                cell.player.setPosition(int(new_pos))
                self.update_status(f"Grid {focused+1}: Forward {self.trim_length * 2} frames")
                return
            elif key in (Qt.Key.Key_D, Qt.Key.Key_Left):
                # Move backward by trim_length * 2
                current_pos = cell.player.position()
                # Calculate frame duration (assuming 30 FPS)
                fps = 30
                frame_duration_ms = 1000 / fps
                new_pos = max(current_pos - (self.trim_length * 2 * frame_duration_ms), 0)
                cell.player.setPosition(int(new_pos))
                self.update_status(f"Grid {focused+1}: Backward {self.trim_length * 2} frames")
                return
        
        # Play/pause for focused grid
        if key == Qt.Key.Key_V:
            if cell.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                cell.player.pause()
            else:
                cell.player.play()
            return
        # Next video for focused grid
        elif key == Qt.Key.Key_R or key == Qt.Key.Key_Down:
            current_idx = self.multi_selected_indices[focused]
            next_idx = (current_idx + 1) % len(self.video_files)
            self.multi_selected_indices[focused] = next_idx
            entry = self.video_files[next_idx]
            cell.load(entry["original_path"])
            cell.player.play()
            cell.setToolTip(entry["display_name"])
            self.status_label.setText(f"Grid {focused+1}: {entry['display_name']}")
            self._highlight_multi_videos()
            return
        # Previous video for focused grid
        elif key == Qt.Key.Key_E or key == Qt.Key.Key_Up:
            current_idx = self.multi_selected_indices[focused]
            prev_idx = (current_idx - 1) % len(self.video_files)
            self.multi_selected_indices[focused] = prev_idx
            entry = self.video_files[prev_idx]
            cell.load(entry["original_path"])
            cell.player.play()
            cell.setToolTip(entry["display_name"])
            self.status_label.setText(f"Grid {focused+1}: {entry['display_name']}")
            self._highlight_multi_videos()
            return
        elif key == Qt.Key.Key_PageDown:
            self.multi_focused_grid = (focused + 1) % len(self.multi_video_widgets)
            self._highlight_multi_videos()
            return
        elif key == Qt.Key.Key_PageUp:
            self.multi_focused_grid = (focused - 1) % len(self.multi_video_widgets)
            self._highlight_multi_videos()
            return
        elif key == Qt.Key.Key_L and modifiers == Qt.KeyboardModifier.NoModifier:
            # Cycle through grid layout modes: auto -> vertical -> horizontal -> auto
            if self.grid_layout_mode == 'auto':
                self.grid_layout_mode = 'vertical'
                self.status_label.setText("Grid layout: Vertical (2 columns)")
            elif self.grid_layout_mode == 'vertical':
                self.grid_layout_mode = 'horizontal'
                self.status_label.setText("Grid layout: Horizontal (3 columns)")
            else:  # horizontal
                self.grid_layout_mode = 'auto'
                self.status_label.setText("Grid layout: Auto (smart)")
            
            # Re-setup multi mode with new layout
            if self.multi_mode:
                self._setup_multi_mode()
            return
        elif key == Qt.Key.Key_Y and modifiers == Qt.KeyboardModifier.NoModifier:
            # Exit multi mode (regular Y, no modifiers)
            self.multi_mode = False
            self.multi_selected_indices = []
            self._teardown_multi_mode()
            # Restore the main video area and select the last focused video
            if self.current_video_index >= 0:
                self.on_video_selected(self.current_video_index)
            return
        else:
            return shortcut_keyPressEvent(self, event)
    return shortcut_keyPressEvent(self, event)

VideoCropper.keyPressEvent = multi_mode_keyPressEvent

if __name__ == "__main__":
    import sys
    import traceback
    from PyQt6.QtWidgets import QApplication
    print("Starting QApplication")  # DEBUG
    try:
        app = QApplication(sys.argv)
        print("QApplication created")  # DEBUG
        win = VideoCropper()
        print("VideoCropper created")  # DEBUG
        win.show()
        print("Window shown")  # DEBUG
        sys.exit(app.exec())
    except Exception as e:
        print("Exception occurred:", e)
        traceback.print_exc()
        input("Press Enter to exit...")

VideoCropper.initUI = initUI
VideoCropper.set_aspect_ratio = set_aspect_ratio
VideoCropper.set_longest_edge = set_longest_edge
VideoCropper.clear_crop_region_controller = clear_crop_region_controller
VideoCropper.crop_rect_updating = crop_rect_updating
VideoCropper.crop_rect_finalized = crop_rect_finalized
VideoCropper.check_current_video_item = check_current_video_item
VideoCropper.toggle_favorite_folder = toggle_favorite_folder
VideoCropper.cycle_theme = cycle_theme
VideoCropper.update_file_count = update_file_count
VideoCropper.toggle_fullscreen = toggle_fullscreen
VideoCropper.open_theme_selector = open_theme_selector
VideoCropper.on_move_av1_clicked = on_move_av1_clicked
