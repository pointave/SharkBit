import sys, os, cv2, ffmpeg, json, numpy as np
from scripts.custom_graphics_view import CustomGraphicsView
from PyQt6.QtWidgets import (
    QApplication, QWidget, QFileDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QListWidget, QSlider, QGraphicsPixmapItem, QLineEdit, QSpinBox,
    QSizePolicy, QCheckBox, QListWidgetItem, QComboBox, QMessageBox,
    QTreeWidget, QTreeWidgetItem, QGridLayout, QSizePolicy, QFrame, QScrollArea
)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QIcon, QMouseEvent
from PyQt6.QtCore import Qt, QTimer, QUrl
import shutil
import datetime
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

# Custom scene (modified to use the new crop region)
from scripts.custom_graphics_scene import CustomGraphicsScene

# Import helper modules
from scripts.video_loader import VideoLoader
from scripts.video_editor import VideoEditor
from scripts.video_exporter import VideoExporter

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
    def __init__(self, parent=None, grid_index=None, click_callback=None, loop_enabled=True, auto_advance_enabled=False, next_file_callback=None):
        super().__init__(parent)
        self.grid_index = grid_index
        self.click_callback = click_callback
        self.loop_enabled = loop_enabled
        self.auto_advance_enabled = auto_advance_enabled
        self.next_file_callback = next_file_callback
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.video_widget = QVideoWidget(self)
        self.player.setVideoOutput(self.video_widget)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.video_widget)
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 90)
        # Remove max size so cells can expand
        # self.setMaximumSize(640, 360)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
    def mousePressEvent(self, event):
        if self.click_callback:
            self.click_callback(self.grid_index)
        super().mousePressEvent(event)
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
        from PyQt6.QtMultimedia import QMediaPlayer
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.loop_enabled:
                self.player.setPosition(0)
                self.player.play()
            elif self.auto_advance_enabled and self.next_file_callback:
                self.next_file_callback(self.grid_index)

class VideoCropper(QWidget):
    def open_yt_folder(self):
        import os
        yt_folder = r"M:\video\yt"
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

    def toggle_auto_advance(self):
        self.auto_advance_enabled = self.auto_advance_button.isChecked()
        # Auto-advance disables looping in multi mode
        if self.auto_advance_enabled:
            self.multi_loop = False
        else:
            self.multi_loop = True
        self.auto_advance_button.setText(
            "Auto-Advance to Next File (ON)" if self.auto_advance_enabled else "Auto-Advance to Next File"
        )
        if self.multi_mode:
            self.status_label.setText(
                f"Multi mode: playing {len(self.multi_video_widgets)} videos (Auto-Advance {'ON' if self.auto_advance_enabled else 'OFF'})"
            )
            # Update all cells' loop/auto-advance state
            for cell in getattr(self, 'multi_video_widgets', []):
                cell.set_loop(not self.auto_advance_enabled)
                cell.set_auto_advance(self.auto_advance_enabled)

    export_in_progress = False  # Class-level flag to prevent duplicate exports
    def __init__(self):
        print("VideoCropper __init__ starting")  # DEBUG
        super().__init__()
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
            "3:2 (Classic Photo)": 3/2,
            "21:9 (Ultrawide)": 21/9
        }
        
        # Create helper modules and pass self.
        self.loader = VideoLoader(self)
        self.editor = VideoEditor(self)
        self.exporter = VideoExporter(self)
        self.export_in_progress = False  # Instance-level flag

        # Initialize favorite folder settings (fixed)
        #self.favorite_folder = r"C:\Users\CHANGE ME\"
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

    def on_sort_changed(self, idx):
        if hasattr(self, 'loader') and hasattr(self.loader, 'sort_videos'):
            self.loader.sort_videos(self.sort_dropdown.currentText())


    
    def eventFilter(self, source, event):
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
                cell.setStyleSheet("border: 2px solid #FF8800; background-color: rgba(255, 200, 100, 40);")
            else:
                cell.setStyleSheet("border: 2px solid transparent; background: none;")

    def _clear_multi_highlights(self):
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            item.setBackground(Qt.GlobalColor.transparent)

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
                loop_enabled=not getattr(self, 'auto_advance_enabled', False),
                auto_advance_enabled=getattr(self, 'auto_advance_enabled', False),
                next_file_callback=next_file_for_cell
            )
            cell.load(entry["original_path"])
            cell.play()
            self.multi_video_widgets.append(cell)
        cols = 2
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
        self.status_label.setText(
            f"Multi mode: playing {len(self.multi_video_widgets)} videos (QMediaPlayer grid)"
        )
        self._highlight_multi_videos()

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
            self.deleted_clips_stack.append({"entry": entry, "backup_path": backup_path})
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
        """Update the folder tree view with the current path and its siblings"""
        import os
        self.folder_tree.clear()
        parent_path = os.path.dirname(current_path)
        # Add parent folder (..)
        if parent_path and parent_path != current_path:
            parent_item = QTreeWidgetItem(['..'])
            parent_item.setData(0, Qt.ItemDataRole.UserRole, parent_path)
            self.folder_tree.addTopLevelItem(parent_item)
        # Add current folder
        root_item = QTreeWidgetItem([os.path.basename(current_path)])
        root_item.setData(0, Qt.ItemDataRole.UserRole, current_path)
        self.folder_tree.addTopLevelItem(root_item)
        self.folder_tree.setCurrentItem(root_item)
        # Populate tree with subfolders
        for entry in os.scandir(current_path):
            if entry.is_dir():
                child_item = QTreeWidgetItem([entry.name])
                child_item.setData(0, Qt.ItemDataRole.UserRole, entry.path)
                root_item.addChild(child_item)
        root_item.setExpanded(True)

    def on_folder_tree_clicked(self, item, column):
        """Handle folder selection from the tree view"""
        folder_path = item.data(0, Qt.ItemDataRole.UserRole)
        if folder_path and os.path.exists(folder_path) and os.path.isdir(folder_path):
            self.folder_path = folder_path
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

# --- Patch: Import shortcut handler and assign to VideoCropper ---
from scripts.shortcut_elements import keyPressEvent as shortcut_keyPressEvent

def multi_mode_keyPressEvent(self, event):
    if getattr(self, 'multi_mode', False) and getattr(self, 'multi_video_widgets', None):
        key = event.key()
        focused = getattr(self, 'multi_focused_grid', 0)
        if focused >= len(self.multi_video_widgets):
            focused = 0
        cell = self.multi_video_widgets[focused]
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
        elif key == Qt.Key.Key_Y:
            # Exit multi mode
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
