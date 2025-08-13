import os, json
from PyQt6.QtWidgets import QFileDialog, QListWidgetItem, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor  # Added import for QColor
import sys

class VideoLoader:
    def __init__(self, main_app):
        self.main_app = main_app
        self.session_file = "session_data.json"

    def load_folder(self):
        """Open folder dialog and load contents"""
        folder = QFileDialog.getExistingDirectory(
            self.main_app,  # Changed from self.parent to self.main_app
            "Select Folder",
            self.main_app.folder_path or os.path.expanduser("~")  # Changed here too
        )
        if folder:
            self.main_app.folder_path = folder
            self.main_app.update_folder_tree(folder)  # Add this line
            self.load_folder_contents()

    def load_folder_contents(self):
        if not self.main_app.folder_path:
            return
            
        self.main_app.video_list.clear()
        self.main_app.video_files = []
        
        video_extensions = ('.mp4', '.avi', '.mkv', '.mov', '.wmv')
        audio_extensions = ('.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg')
        
        # Use os.scandir for better performance
        try:
            with os.scandir(self.main_app.folder_path) as entries:
                for entry in entries:
                    if not entry.is_file():
                        continue
                    name = entry.name.lower()
                    if getattr(self.main_app, 'audio_mode', False):
                        if name.endswith(audio_extensions):
                            self.main_app.video_files.append({
                                "original_path": entry.path,
                                "display_name": entry.name,
                                "copy_number": 0
                            })
                    else:
                        if name.endswith(video_extensions):
                            self.main_app.video_files.append({
                                "original_path": entry.path,
                                "display_name": entry.name,
                                "copy_number": 0
                            })
            
            # Populate list by current sort mode
            if hasattr(self.main_app, 'sort_dropdown'):
                mode = self.main_app.sort_dropdown.currentText()
            else:
                mode = "Date (new first)"  # Default sort mode
            self.sort_videos(mode)
            
            # Select first video if available, but defer loading until UI is responsive
            if self.main_app.video_files:
                self.main_app.current_video_index = 0
                self.main_app.video_list.setCurrentRow(0)
                from PyQt6.QtCore import QTimer
                if getattr(self.main_app, 'audio_mode', False):
                    QTimer.singleShot(0, lambda: self.load_audio(self.main_app.video_list.item(0)))
                else:
                    QTimer.singleShot(0, lambda: self.load_video(self.main_app.video_list.item(0)))
        except Exception as e:
            print(f"Error loading folder contents: {e}")

    def add_video_item(self, display_name):
        item = QListWidgetItem(display_name)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        # Look up the saved export state.
        entry = next((e for e in self.main_app.video_files if e["display_name"] == display_name), None)
        if entry and entry.get("export_enabled", False):
            item.setCheckState(Qt.CheckState.Checked)
        else:
            item.setCheckState(Qt.CheckState.Unchecked)
        self.update_list_item_color(item)
        self.main_app.video_list.addItem(item)

    def sort_videos(self, mode):
        import random
        # Remember the currently playing video's display name
        current_display = getattr(self.main_app, 'current_video', None)
        if mode == "Date (old first)":
            self.main_app.video_files.sort(key=lambda x: os.path.getctime(x["original_path"]))
        elif mode == "Date (new first)":
            self.main_app.video_files.sort(key=lambda x: os.path.getctime(x["original_path"]), reverse=True)
        elif mode == "Alphabetical":
            self.main_app.video_files.sort(key=lambda x: x["display_name"].lower())
        elif mode == "Size (large first)":
            self.main_app.video_files.sort(key=lambda x: os.path.getsize(x["original_path"]), reverse=True)
        elif mode == "Size (small first)":
            self.main_app.video_files.sort(key=lambda x: os.path.getsize(x["original_path"]))
        elif mode == "Random":
            random.shuffle(self.main_app.video_files)
        # Repopulate the list
        self.main_app.video_list.clear()
        for video in self.main_app.video_files:
            self.add_video_item(video["display_name"])
        # After sorting, select the previously playing video if possible
        if current_display:
            idx = next((i for i, v in enumerate(self.main_app.video_files) if v["display_name"] == current_display), None)
            if idx is not None:
                self.main_app.current_video_index = idx
                self.main_app.video_list.setCurrentRow(idx)
                # Ensure the selected video is visible
                self.main_app.video_list.scrollToItem(self.main_app.video_list.item(idx))
                self.main_app.current_video = self.main_app.video_files[idx]["display_name"]
            else:
                # Fallback to first video
                self.main_app.current_video_index = 0
                self.main_app.video_list.setCurrentRow(0)
                if self.main_app.video_files:
                    self.main_app.current_video = self.main_app.video_files[0]["display_name"]
        elif self.main_app.video_files:
            self.main_app.current_video_index = 0
            self.main_app.video_list.setCurrentRow(0)
            self.main_app.current_video = self.main_app.video_files[0]["display_name"]
        else:
            self.main_app.current_video = None


    def search_videos(self, text):
        # Case-insensitive search in display_name or original_path
        text = text.strip().lower()
        self.main_app.video_list.clear()
        if not hasattr(self.main_app, 'filtered_video_files'):
            self.main_app.filtered_video_files = []
        if not text:
            # Show all
            self.main_app.filtered_video_files = list(self.main_app.video_files)
            for video in self.main_app.filtered_video_files:
                self.add_video_item(video["display_name"])
        else:
            self.main_app.filtered_video_files = [
                video for video in self.main_app.video_files
                if text in video["display_name"].lower() or text in video["original_path"].lower()
            ]
            for video in self.main_app.filtered_video_files:
                self.add_video_item(video["display_name"])
        # Optionally, select first result
        if self.main_app.video_list.count() > 0:
            self.main_app.video_list.setCurrentRow(0)

    def update_list_item_color(self, item):
        idx = self.main_app.video_list.row(item)
        if idx >= 0 and idx < len(self.main_app.video_files):
            # Update the export_enabled flag in the video_files entry.
            self.main_app.video_files[idx]["export_enabled"] = (item.checkState() == Qt.CheckState.Checked)
        if item.checkState() == Qt.CheckState.Checked:
            # Use a darker green.
            item.setBackground(QColor(0, 100, 0))
        else:
            item.setBackground(Qt.GlobalColor.transparent)

        # Save the session immediately after updating the state.
      #  self.save_session()

    def load_video(self, item):
        idx = self.main_app.video_list.row(item)
        filtered = getattr(self.main_app, 'filtered_video_files', None)
        video_list_source = filtered if filtered is not None and len(filtered) == self.main_app.video_list.count() else self.main_app.video_files
        if idx < 0 or idx >= len(video_list_source):
            return
        video_entry = video_list_source[idx]
        # If in audio mode, route to audio loader instead
        if getattr(self.main_app, 'audio_mode', False):
            self.load_audio(item)
            return
        self.main_app.current_video = video_entry["display_name"]
        if self.main_app.cap:
            self.main_app.cap.release()
        
        # Clear any existing crop region from the previous clip.
        self.main_app.clear_crop_region_controller()
        
        if self.main_app.current_video not in self.main_app.crop_regions:
            self.main_app.crop_regions[self.main_app.current_video] = None
        self.main_app.editor.load_video(video_entry)

    def load_audio(self, item):
        idx = self.main_app.video_list.row(item)
        filtered = getattr(self.main_app, 'filtered_video_files', None)
        src = filtered if filtered is not None and len(filtered) == self.main_app.video_list.count() else self.main_app.video_files
        if idx < 0 or idx >= len(src):
            return
        entry = src[idx]
        self.main_app.current_video = entry["display_name"]
        # Delegate to the main app's audio loader
        if hasattr(self.main_app, 'load_audio_entry'):
            self.main_app.load_audio_entry(entry)
        else:
            # Fallback: just update status
            try:
                self.main_app.update_status(f"Audio selected: {entry['display_name']}")
            except Exception:
                pass


    def duplicate_clip(self):
        current_item = self.main_app.video_list.currentItem()
        if not current_item:
            return
        current_idx = self.main_app.video_list.row(current_item)
        original_entry = self.main_app.video_files[current_idx]
        base_name, ext = os.path.splitext(original_entry["display_name"])
        # Start with the next copy number.
        new_copy = original_entry["copy_number"] + 1
        new_display = f"{base_name}_{new_copy}{ext}"
        # Check for name collisions.
        existing_names = [entry["display_name"] for entry in self.main_app.video_files]
        while new_display in existing_names:
            new_copy += 1
            new_display = f"{base_name}_{new_copy}{ext}"
        new_entry = {
            "original_path": original_entry["original_path"],
            "display_name": new_display,
            "copy_number": new_copy,
            "export_enabled": original_entry.get("export_enabled", False)
        }
        self.main_app.video_files.append(new_entry)
        self.add_video_item(new_display)
        self.main_app.crop_regions[new_display] = self.main_app.crop_regions.get(original_entry["display_name"], None)
        self.main_app.trim_points[new_display] = self.main_app.trim_points.get(original_entry["display_name"], 0)
        self.save_session()

    def clear_crop_region(self):
        if self.main_app.current_video and self.main_app.current_video in self.main_app.crop_regions:
            self.main_app.crop_regions[self.main_app.current_video] = None
            if self.main_app.current_rect:
                self.main_app.scene.removeItem(self.main_app.current_rect)
                self.main_app.current_rect = None

    def refresh_video_list(self):
        self.main_app.video_list.clear()
        for entry in self.main_app.video_files:
            self.add_video_item(entry["display_name"])

    def load_session(self):
        session_file = "session_data.json"
        if os.path.exists(session_file):
            try:
                with open(session_file, "r") as f:
                    session_data = json.load(f)
                self.main_app.folder_path = session_data.get("folder_path", "")
                self.main_app.video_files = session_data.get("video_files", [])
                self.main_app.folder_sessions = session_data.get("folder_sessions", {})
                self.main_app.crop_regions = session_data.get("crop_regions", {})
                self.main_app.trim_points = session_data.get("trim_points", {})
                self.main_app.longest_edge = session_data.get("longest_edge", 1024)
                self.main_app.trim_length = session_data.get("trim_length", 113)
                # Load grid layout mode preference
                self.main_app.grid_layout_mode = session_data.get("grid_layout_mode", "auto")
            except json.JSONDecodeError:
                print("Error: Session file is corrupted. Starting with an empty session.")
                self.main_app.folder_sessions = {}
        else:
            self.main_app.folder_sessions = {}

    def save_session(self):
        # Update the export_enabled flag from the UI before saving.
        for i in range(self.main_app.video_list.count()):
            item = self.main_app.video_list.item(i)
            self.main_app.video_files[i]["export_enabled"] = (item.checkState() == Qt.CheckState.Checked)
        # Update the mapping for the current folder.
        self.main_app.folder_sessions[self.main_app.folder_path] = self.main_app.video_files
        
        session_data = {
            "folder_path": self.main_app.folder_path,
            "video_files": self.main_app.video_files,
            "folder_sessions": self.main_app.folder_sessions,
            "crop_regions": self.main_app.crop_regions,
            "trim_points": self.main_app.trim_points,
            "longest_edge": self.main_app.longest_edge,
            "trim_length": self.main_app.trim_length,
            "grid_layout_mode": self.main_app.grid_layout_mode
        }
        with open(self.session_file, "w") as file:
            json.dump(session_data, file)

if __name__ == "__main__":
    from scripts.video_cropper import VideoCropper  # Local import to break circular dependency
    app = QApplication(sys.argv)
    window = VideoCropper()
    # Load the session (restores folder_path, video_files, etc.)
    window.loader.load_session()
    # If a folder was remembered, load its contents.
    if window.folder_path:
        window.loader.load_folder_contents()
    window.show()
    sys.exit(app.exec())
