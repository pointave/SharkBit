import os
print("ui_elements.py imported")  # DEBUG

from PyQt6.QtWidgets import (
    QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QListWidget,
    QCheckBox, QSpinBox, QSlider, QTreeWidget, QTreeWidgetItem, QWidget, QGridLayout,
    QSizePolicy, QGraphicsPixmapItem, QApplication
)
from PyQt6.QtGui import QPixmap, QPainter, QIcon, QImage
from PyQt6.QtCore import Qt, QTimer, QSize
from scripts.custom_graphics_view import CustomGraphicsView
from scripts.custom_graphics_scene import CustomGraphicsScene


def initUI(self):
    print("initUI called")  # DEBUG

    main_layout = QHBoxLayout(self)
    
    # LEFT PANEL
    left_panel = QVBoxLayout()
    self.icon_label = QLabel(self)
    icon_pixmap = QPixmap("icons/folder_icon.png")
    self.icon_label.setPixmap(icon_pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio))
    self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.icon_label.setCursor(Qt.CursorShape.PointingHandCursor)
    left_panel.addWidget(self.icon_label)
    # Make icon clickable for theme cycling
    def icon_click_event(event):
        self.cycle_theme()
    self.icon_label.mousePressEvent = icon_click_event
    
    self.folder_button = QPushButton("Select Folder")
    self.folder_button.clicked.connect(self.loader.load_folder)
    # Remove any theme cycle button from the UI (if it exists)
    if hasattr(self, 'theme_button'):
        self.theme_button.hide()
        self.theme_button.deleteLater()
    
    # Folder selection + refresh
    folder_nav_layout = QHBoxLayout()
    # Buttons stacked vertically
    button_layout = QVBoxLayout()
    button_layout.addWidget(self.folder_button)
    self.refresh_button = QPushButton("Refresh Folder")
    self.refresh_button.clicked.connect(self.loader.load_folder_contents)
    button_layout.addWidget(self.refresh_button)
    # --- Favorite Folder Toggle Button (new) ---
    self.favorite_button = QPushButton("★ Favorite Folder")
    self.favorite_button.setCheckable(True)
    self.favorite_button.setChecked(False)
    self.favorite_button.clicked.connect(self.toggle_favorite_folder)
    button_layout.addWidget(self.favorite_button)
    # --- End Favorite Folder Toggle ---
    folder_nav_layout.addLayout(button_layout)

    # Folder tree to the right of buttons
    self.folder_tree = QTreeWidget()
    self.folder_tree.setHeaderHidden(True)
    self.folder_tree.setMaximumHeight(150)
    self.folder_tree.itemClicked.connect(self.on_folder_tree_clicked)
    folder_nav_layout.addWidget(self.folder_tree)

    left_panel.addLayout(folder_nav_layout)

    # Search bar
    self.search_bar = QLineEdit()
    self.search_bar.setPlaceholderText("Search videos...")
    self.search_bar.textChanged.connect(lambda text: self.loader.search_videos(text))
    left_panel.addWidget(self.search_bar)

    # Sorting dropdown
    self.sort_dropdown = QComboBox()
    self.sort_dropdown.addItems([
        "Date (new first)",
        "Date (old first)",
        "Alphabetical",
        "Size (large first)",
        "Size (small first)",
        "Random"
    ])
    self.sort_dropdown.setCurrentIndex(0)  # Default to Date (new first)

    self.sort_dropdown.currentIndexChanged.connect(self.on_sort_changed)
    left_panel.addWidget(self.sort_dropdown)
    
    self.video_list.itemClicked.connect(self.loader.load_video)
    self.video_list.itemChanged.connect(self.loader.update_list_item_color)
    left_panel.addWidget(self.video_list, 1)
    # Install event filter so key events in the file list go to main window
    self.video_list.installEventFilter(self)

    # --- Add file counter label ---
    self.file_count_label = QLabel("Files: 0")
    left_panel.addWidget(self.file_count_label)

    self.clear_crop_button = QPushButton("Clear Crop")
    self.clear_crop_button.clicked.connect(self.loader.clear_crop_region)
    left_panel.addWidget(self.clear_crop_button)
    
    # Auto-advance button: disables looping and plays next file automatically
    self.auto_advance_enabled = False
    self.auto_advance_button = QPushButton("Auto-Advance to Next File")
    self.auto_advance_button.setCheckable(True)
    self.auto_advance_button.setChecked(False)
    self.auto_advance_button.clicked.connect(self.toggle_auto_advance)
    left_panel.addWidget(self.auto_advance_button)

    # --- YouTube URL Section ---
    yt_layout = QHBoxLayout()
    self.youtube_url_input = QLineEdit()
    self.youtube_url_input.setPlaceholderText("Paste YouTube URL...")
    yt_layout.addWidget(self.youtube_url_input)
    self.youtube_load_button = QPushButton("Load YouTube")
    self.youtube_load_button.clicked.connect(self.load_youtube_url)
    yt_layout.addWidget(self.youtube_load_button)
    self.youtube_folder_button = QPushButton("Open YT Folder")
    self.youtube_folder_button.clicked.connect(self.open_yt_folder)
    yt_layout.addWidget(self.youtube_folder_button)
    left_panel.addLayout(yt_layout)

    # Always autoplay on video change
    self.auto_play_on_change = True

    # --- Optional Settings (moved from right to left) ---
    self.resolution_input = QLineEdit()
    self.resolution_input.setPlaceholderText("Set longest edge (default 1024)")
    self.resolution_input.textChanged.connect(self.set_longest_edge)
    left_panel.addWidget(self.resolution_input)

    self.prefix_input = QLineEdit()
    self.prefix_input.setPlaceholderText("Filename Replacement (Optional)")
    self.prefix_input.textChanged.connect(lambda text: setattr(self, "export_prefix", text))
    left_panel.addWidget(self.prefix_input)

    self.caption_input = QLineEdit()
    self.caption_input.setPlaceholderText("Simple caption (Optional)")
    self.caption_input.textChanged.connect(lambda text: setattr(self, "simple_caption", text))
    left_panel.addWidget(self.caption_input)
    # --- Move aspect ratio box here ---
    aspect_ratio_layout = QHBoxLayout()
    self.aspect_ratio_combo = QComboBox()
    for ratio_name in self.aspect_ratios.keys():
        self.aspect_ratio_combo.addItem(ratio_name)
    self.aspect_ratio_combo.currentTextChanged.connect(self.set_aspect_ratio)
    aspect_ratio_layout.addWidget(self.aspect_ratio_combo)
    left_panel.addLayout(aspect_ratio_layout)
    # --- End move ---

    # Remove play/pause button from left panel (old)
    # self.play_pause_button = QPushButton("Play/Pause")
    # self.play_pause_button.clicked.connect(self.editor.toggle_play_forward)
    # left_panel.addWidget(self.play_pause_button)
    
    self.clip_length_label = QLabel("Clip Length: 0")
    left_panel.addWidget(self.clip_length_label)
    self.trim_point_label = QLabel("Trim Point: 0")
    left_panel.addWidget(self.trim_point_label)
    
    trim_layout = QHBoxLayout()
    trim_layout.addWidget(QLabel("Trim Length (frames):"))
    self.trim_spin = QSpinBox()
    self.trim_spin.setMaximum(9999)
    self.trim_spin.setValue(113)
    self.trim_spin.valueChanged.connect(lambda v: setattr(self, 'trim_length', v))
    trim_layout.addWidget(self.trim_spin)
    left_panel.addLayout(trim_layout)
    

    self.export_image_checkbox = QCheckBox("Export Image at Trim Point")
    self.export_image_checkbox.setChecked(False)
    left_panel.addWidget(self.export_image_checkbox)
    
    main_layout.addLayout(left_panel, 1)

    self.video_list.setStyleSheet("QListWidget::item:selected { background-color: #3A4F7A; }")
    
    # RIGHT PANEL
    self.right_panel_layout = QVBoxLayout()
    right_panel = self.right_panel_layout
    # Monitoring label (replaces old shortcut info)
    # Place clock and monitoring label on the same horizontal line
    clock_monitor_layout = QHBoxLayout()
    self.monitoring_label = QLabel("Loading system status...")
    self.monitoring_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    self.monitoring_label.setStyleSheet("font-size: 12px; color: #ECEFF4;")
    clock_monitor_layout.addWidget(self.monitoring_label, stretch=2)
    self.clock_label = QLabel()
    self.clock_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    self.clock_label.setStyleSheet("font-size: 18px; color: #FFD700; padding-left: 12px;")
    clock_monitor_layout.addWidget(self.clock_label, stretch=1)
    right_panel.addLayout(clock_monitor_layout)
    def update_clock():
        from datetime import datetime
        now = datetime.now().strftime('%H:%M')
        self.clock_label.setText(now)
    self.clock_timer = QTimer()
    self.clock_timer.timeout.connect(update_clock)
    self.clock_timer.start(30000)  # Update every 10 seconds
    update_clock()


    # Periodically update system status
    def update_monitoring():
        try:
            import importlib.util
            import sys
            import os
            script_dir = os.path.dirname(os.path.abspath(__file__))
            module_path = os.path.join(script_dir, 'monitoring_status.py')
            spec = importlib.util.spec_from_file_location('monitoring_status', module_path)
            monitoring_status = importlib.util.module_from_spec(spec)
            sys.modules['monitoring_status'] = monitoring_status
            spec.loader.exec_module(monitoring_status)
            status = monitoring_status.get_monitoring_status()
            self.monitoring_label.setText(status)
        except Exception as e:
            self.monitoring_label.setText(f"Monitor error: {e}")
    self.monitoring_timer = QTimer()
    self.monitoring_timer.timeout.connect(update_monitoring)
    self.monitoring_timer.start(2000)  # Update every 2 seconds
    update_monitoring()
    
    # Moved slider above the video display
    self.slider = QSlider(Qt.Orientation.Horizontal)
    self.slider.setEnabled(False)
    self.slider.sliderMoved.connect(self.editor.scrub_video)
    right_panel.addWidget(self.slider)
    
    self.graphics_view = CustomGraphicsView()
    self.graphics_view.setRenderHint(QPainter.RenderHint.Antialiasing)
    self.graphics_view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    self.graphics_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    self.scene = CustomGraphicsScene(self)
    self.graphics_view.setScene(self.scene)
    self.pixmap_item = QGraphicsPixmapItem()
    self.scene.addItem(self.pixmap_item)
    self.graphics_view.setMouseTracking(True)
    # Install event filter so arrow keys work globally
    self.graphics_view.installEventFilter(self)
    right_panel.addWidget(self.graphics_view, 1)
    
    self.thumbnail_label = QWidget(self)
    self.thumbnail_label.setWindowFlags(Qt.WindowType.ToolTip)
    self.thumbnail_label.setStyleSheet("background-color: black; border: 1px solid white;")
    self.thumbnail_label.hide()
    right_panel.addWidget(self.thumbnail_label)
    self.thumbnail_image_label = QLabel(self.thumbnail_label)
    self.thumbnail_image_label.setGeometry(0, 0, 160, 90)
    
    self.slider.installEventFilter(self)
    

    # --- Move Play/Pause button here ---
    button_row = QHBoxLayout()
    self.play_pause_button = QPushButton("Play/Pause")
    self.play_pause_button.clicked.connect(self.editor.toggle_play_forward)
    button_row.addWidget(self.play_pause_button)
    self.submit_button = QPushButton("Export Cropped Videos")
    self.submit_button.clicked.connect(self.exporter.export_videos)
    button_row.addWidget(self.submit_button)
    right_panel.addLayout(button_row)
    # --- End Move ---
    
    self.status_label = QLabel("Ready")
    right_panel.addWidget(self.status_label)
    
    main_layout.addLayout(right_panel, 3)
    
    # Disconnect existing connections
    try:
        self.video_list.itemClicked.disconnect()
    except Exception:
        pass
    self.video_list.currentRowChanged.connect(self.on_video_selected)
    self.video_list.itemPressed.connect(self.on_video_list_pressed)
    
    self.video_list.setViewMode(QListWidget.ViewMode.ListMode)
    self.video_list.keyboardSearch = lambda x: None

    # --- Multi-video grid widget (hidden by default) ---
    self.multi_grid_widget = QWidget()
    self.multi_grid_layout = QGridLayout(self.multi_grid_widget)
    self.multi_grid_widget.setVisible(False)
    # Insert the multi grid above the graphics_view in the right panel
    self.right_panel_layout.insertWidget(1, self.multi_grid_widget)
    
def set_aspect_ratio(self, ratio_name):
    ratio_value = self.aspect_ratios.get(ratio_name)
    self.scene.set_aspect_ratio(ratio_value)

def set_longest_edge(self):
    try:
        self.longest_edge = int(self.resolution_input.text())
    except ValueError:
        self.longest_edge = 1080

def clear_crop_region_controller(self):
    """
    Remove all interactive crop region items from the scene.
    This ensures that when loading a new clip or creating a new crop region,
    only one crop region is visible.
    """
    from scripts.interactive_crop_region import InteractiveCropRegion
    # Collect all items that are instances of InteractiveCropRegion.
    items_to_remove = [item for item in self.scene.items() if isinstance(item, InteractiveCropRegion)]
    for item in items_to_remove:
        self.scene.removeItem(item)
    self.current_rect = None

def crop_rect_updating(self, rect):
    """
    Callback invoked during crop region adjustment.
    You can use this to update a preview or status label.
    """
    print(f"Crop region updating: {rect}")

def crop_rect_finalized(self, rect):
    """
    Callback invoked when the crop region is finalized (on mouse release or after a wheel event).
    This saves the crop region relative to the original clip dimensions.
    """
    if not self.current_video:
        return
    pixmap = self.pixmap_item.pixmap()
    if pixmap is None or pixmap.width() == 0:
        return
    scale_w = self.original_width / pixmap.width()
    scale_h = self.original_height / pixmap.height()
    x = int(rect.x() * scale_w)
    y = int(rect.y() * scale_h)
    w = int(rect.width() * scale_w)
    h = int(rect.height() * scale_h)
    self.crop_regions[self.current_video] = (x, y, w, h)
    self.check_current_video_item()
    

def cycle_theme(self):
        # Simple theme cycling: dark, light, none
        if not hasattr(self, '_theme_index'):
            self._theme_index = 0
        themes = [
            None,
            'styles/minimalist.css',
            'styles/retro_terminal.css',
            'styles/cyberpunk.css',
            'styles/high_contrast.css',
            'styles/playful.css',
            'styles/vintage_mac.css',
            'styles/music_daw.css',
            'styles/hacker_matrix.css',
            'styles/pastel_bliss.css',
            'styles/animated_rainbow.css',
            'styles/animated_neon.css',
            'styles/animated_bubblegum.css',
            'styles/cartoon_pop.css',
            'styles/space_aurora.css',
            'styles/vaporwave_sunset.css',
            'styles/underwater_deep.css',
            'styles/lava_lamp.css',
            'styles/origami_fold.css',
            'styles/pixel_art.css',
            'styles/wooden_desk.css',
            'styles/ice_cave.css',
            'styles/terminal_glass.css',
        ]
        self._theme_index = (self._theme_index + 1) % len(themes)
        theme = themes[self._theme_index]
        if theme and os.path.exists(theme):
            with open(theme, 'r') as f:
                QApplication.instance().setStyleSheet(f.read())
        else:
            QApplication.instance().setStyleSheet("")

def toggle_fullscreen(self):
        if not hasattr(self, '_is_fullscreen'):
            self._is_fullscreen = False
        if self._is_fullscreen:
            self.showNormal()
            self._is_fullscreen = False
        else:
            self.showFullScreen()
            self._is_fullscreen = True

def toggle_favorite_folder(self):
    # New method for toggling favorite folder
    if not self.favorite_active:
        self.last_non_favorite_folder = self.folder_path
        self.folder_path = self.favorite_folder
        self.favorite_active = True
        self.favorite_button.setChecked(True)
        self.favorite_button.setText("★ Favorite Folder (Active)")
        self.loader.load_folder_contents()
        self.update_folder_tree(self.folder_path)
    else:
        if self.last_non_favorite_folder and os.path.exists(self.last_non_favorite_folder):
            self.folder_path = self.last_non_favorite_folder
            self.loader.load_folder_contents()
            self.update_folder_tree(self.folder_path)
        self.favorite_active = False
        self.favorite_button.setChecked(False)
        self.favorite_button.setText("★ Favorite Folder")

def _youtube_download_worker(self, url):
        import subprocess, os, glob
        yt_folder = r"M:\video\yt"
        before = set(glob.glob(os.path.join(yt_folder, "**", "*.*"), recursive=True))
        try:
            cmd = f'yt-dlp -o "%(uploader)s/%(title)s.%(ext)s" "{url}" --cookies-from-browser firefox'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=yt_folder, timeout=1200)
            if res.returncode != 0 and "already been downloaded" not in (res.stderr or ""):
                raise RuntimeError(res.stderr or "download failed")
            after = set(glob.glob(os.path.join(yt_folder, "**", "*.*"), recursive=True))
            new = after - before
            downloaded = max(new, key=os.path.getctime) if new else None
            if not downloaded:
                name_cmd = f'yt-dlp --get-filename -o "%(uploader)s/%(title)s.%(ext)s" "{url}" --cookies-from-browser firefox'
                name_res = subprocess.run(name_cmd, shell=True, capture_output=True, text=True, cwd=yt_folder, timeout=120)
                candidate = name_res.stdout.strip()
                path = os.path.join(yt_folder, candidate) if candidate else None
                downloaded = path if path and os.path.exists(path) else None
            if not downloaded:
                raise RuntimeError("Downloaded file not found")
        except Exception as e:
            QTimer.singleShot(0, lambda: QMessageBox.critical(self, "YouTube Error", str(e)))
            QTimer.singleShot(0, lambda: self.youtube_url_input.setEnabled(True))
            return
        QTimer.singleShot(0, lambda: self._on_download_complete(downloaded))

def _on_download_complete(self, downloaded_file):
        display = os.path.basename(downloaded_file)
        entry = {"original_path": downloaded_file, "display_name": display, "copy_number": 0}
        self.video_files.append(entry)
        self.loader.add_video_item(display)
        self.video_list.setCurrentRow(self.video_list.count() - 1)
        item = self.video_list.currentItem()
        self.loader.load_video(item)
        self.update_status(f"Loaded YouTube video: {display}")
        self.youtube_url_input.setEnabled(True)

def update_file_count(self):
        count = self.video_list.count()
        self.file_count_label.setText(f"Files: {count}")

def take_screenshot(self):
        # Find the current video entry (dict) by display name
        entry = next((e for e in self.video_files if e["display_name"] == self.current_video), None)
        if not entry or self.pixmap_item.pixmap().isNull():
            self.update_status("No video loaded.")
            return

        from scripts.screenshot_helper import save_video_screenshot
        result = save_video_screenshot(
            entry=entry,
            pixmap=self.pixmap_item.pixmap(),
            crop_regions=self.crop_regions,
            original_width=self.original_width,
            original_height=self.original_height,
            current_video=self.current_video,
            folder_path=self.folder_path
        )
        if result:
            self.update_status("Screenshot saved")
        else:
            self.update_status("Failed to save screenshot.")
    

def check_current_video_item(self):
    # Find the list item corresponding to the current video and mark it checked.
    for i in range(self.video_list.count()):
        item = self.video_list.item(i)
        if item.text() == self.current_video:
            if item.checkState() != Qt.CheckState.Checked:
                item.setCheckState(Qt.CheckState.Checked)
            break