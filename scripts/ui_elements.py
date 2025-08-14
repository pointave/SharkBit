import os
print("ui_elements.py imported")  # DEBUG

from PyQt6.QtWidgets import (
    QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QListWidget,
    QCheckBox, QSpinBox, QSlider, QTreeWidget, QTreeWidgetItem, QWidget, QGridLayout,
    QSizePolicy, QGraphicsPixmapItem, QApplication, QProgressBar
)
from PyQt6.QtGui import QPixmap, QPainter, QIcon, QImage
from PyQt6.QtCore import Qt, QTimer, QSize
from scripts.custom_graphics_view import CustomGraphicsView
from scripts.custom_graphics_scene import CustomGraphicsScene
from scripts.audio_editor import AudioEditor


def initUI(self):
    print("initUI called")  # DEBUG

    main_layout = QHBoxLayout(self)
    # App mode: 'video' or 'audio'
    if not hasattr(self, 'audio_mode'):
        self.audio_mode = False
    
    # LEFT PANEL
    left_panel = QVBoxLayout()
    self.icon_label = QLabel(self)
    icon_pixmap = QPixmap("icons/folder_icon.png")
    self.icon_label.setPixmap(icon_pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio))
    self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.icon_label.setCursor(Qt.CursorShape.PointingHandCursor)
    left_panel.addWidget(self.icon_label)
    # Make icon clickable to toggle Audio/Video mode for now
    def icon_click_event(event):
        try:
            was_audio_mode = getattr(self, 'audio_mode', False)
            self.audio_mode = not was_audio_mode
            
            # Update UI hints
            self.search_bar.setPlaceholderText("Search audio..." if self.audio_mode else "Search videos...")
            # Update status and reload folder listing with appropriate extensions
            self.update_status("Audio Mode" if self.audio_mode else "Video Mode")
            
            # Swap main view widgets
            try:
                if hasattr(self, 'graphics_view') and self.graphics_view is not None:
                    self.graphics_view.setVisible(not self.audio_mode)
                if hasattr(self, 'audio_editor') and self.audio_editor is not None:
                    self.audio_editor.setVisible(self.audio_mode)
            except Exception:
                pass
                
            # Auto-unmute when switching to audio tab
            if self.audio_mode and hasattr(self, 'audio_output'):
                if self.audio_output.isMuted() or self.audio_output.volume() == 0:
                    self.audio_output.setVolume(0.5)
                    self.audio_output.setMuted(False)
                    self.update_status("Audio unmuted (50% volume)")
                    
            if hasattr(self, 'loader'):
                self.loader.load_folder_contents()
        except Exception as e:
            print(f"Error toggling mode: {e}")
    self.icon_label.mousePressEvent = icon_click_event
    
    self.folder_button = QPushButton("Select Folder")
    self.folder_button.clicked.connect(self.loader.load_folder)
    
    # Add theme selector button
    self.theme_button = QPushButton("🎨 Themes")
    self.theme_button.clicked.connect(self.open_theme_selector)
    self.theme_button.setToolTip("Open theme selector (or press T to cycle)")
    
    # Remove any old theme cycle button from the UI (if it exists)
    if hasattr(self, 'old_theme_button'):
        self.old_theme_button.hide()
        self.old_theme_button.deleteLater()
    
    # Folder selection + refresh
    folder_nav_layout = QHBoxLayout()
    # Buttons stacked vertically
    button_layout = QVBoxLayout()
    button_layout.addWidget(self.folder_button)
    self.refresh_button = QPushButton("Refresh Folder")
    self.refresh_button.clicked.connect(self.loader.load_folder_contents)
    button_layout.addWidget(self.refresh_button)
    button_layout.addWidget(self.theme_button)  # Add theme button
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
    self.search_bar.setPlaceholderText("Search audio..." if getattr(self, 'audio_mode', False) else "Search videos...")
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


    # --- Clear Crop and Aspect Ratio buttons side by side ---
    crop_aspect_layout = QHBoxLayout()
    self.clear_crop_button = QPushButton("Clear Crop")
    self.clear_crop_button.clicked.connect(self.loader.clear_crop_region)
    crop_aspect_layout.addWidget(self.clear_crop_button)
    
    self.aspect_ratio_combo = QComboBox()
    for ratio_name in self.aspect_ratios.keys():
        self.aspect_ratio_combo.addItem(ratio_name)
    self.aspect_ratio_combo.currentTextChanged.connect(self.set_aspect_ratio)
    crop_aspect_layout.addWidget(self.aspect_ratio_combo)
    left_panel.addLayout(crop_aspect_layout)
    
    # Loop and AV1 buttons side by side
    self.auto_advance_enabled = False
    loop_av1_layout = QHBoxLayout()
    self.auto_advance_button = QPushButton("Loop")
    self.auto_advance_button.setCheckable(True)
    self.auto_advance_button.setChecked(False)
    self.auto_advance_button.clicked.connect(self.toggle_auto_advance)
    loop_av1_layout.addWidget(self.auto_advance_button)
    self.move_av1_button = QPushButton("AV1")
    self.move_av1_button.setToolTip("Scan current folder and move all AV1 videos to an 'AV1' subfolder.")
    self.move_av1_button.clicked.connect(self.on_move_av1_clicked)
    loop_av1_layout.addWidget(self.move_av1_button)
    left_panel.addLayout(loop_av1_layout)

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

    # Remove play/pause button from left panel (old)
    # self.play_pause_button = QPushButton("Play/Pause")
    # self.play_pause_button.clicked.connect(self.editor.toggle_play_forward)
    # left_panel.addWidget(self.play_pause_button)
    
    # Video info grid layout - compact version
    video_info_layout = QGridLayout()
    video_info_layout.setContentsMargins(2, 2, 2, 2)  # Reduce margins
    
    # Create a small font for compact display
    small_font = self.font()
    small_font.setPointSize(small_font.pointSize() - 2)  # Slightly smaller font
    
    # Row 0: Clip length and File size
    self.clip_length_label = QLabel("0")
    self.clip_length_label.setFont(small_font)
    video_info_layout.addWidget(QLabel("Clip:"), 0, 0)
    video_info_layout.addWidget(self.clip_length_label, 0, 1)
    
    self.file_size_label = QLabel("0 MB")
    self.file_size_label.setFont(small_font)
    video_info_layout.addWidget(QLabel("Size:"), 0, 2)
    video_info_layout.addWidget(self.file_size_label, 0, 3)
    
    # Row 1: Current position and FPS
    self.trim_point_label = QLabel("0")
    self.trim_point_label.setFont(small_font)
    video_info_layout.addWidget(QLabel("Pos:"), 1, 0)
    video_info_layout.addWidget(self.trim_point_label, 1, 1)
    
    self.fps_label = QLabel("0")
    self.fps_label.setFont(small_font)
    video_info_layout.addWidget(QLabel("FPS:"), 1, 2)
    video_info_layout.addWidget(self.fps_label, 1, 3)
    
    # Adjust spacing and alignment
    video_info_layout.setHorizontalSpacing(3)
    video_info_layout.setVerticalSpacing(1)
    video_info_layout.setColumnStretch(1, 2)  # Give more space to values
    video_info_layout.setColumnStretch(3, 2)  # Give more space to values
    
    # Add the grid to the left panel
    left_panel.addLayout(video_info_layout)
    
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

    # Set size constraints to prevent UI resizing when themes change
    self.setMinimumSize(400, 400)  # Minimum window size
    self.resize(1400, 800)  # Default window size
    
    # Set fixed heights for key UI elements to prevent resizing
    self.folder_button.setFixedHeight(35)
    self.refresh_button.setFixedHeight(35)
    self.theme_button.setFixedHeight(35)
    self.favorite_button.setFixedHeight(35)
    self.search_bar.setFixedHeight(30)
    self.sort_dropdown.setFixedHeight(30)
    self.clear_crop_button.setFixedHeight(35)
    self.auto_advance_button.setFixedHeight(35)
    self.youtube_url_input.setFixedHeight(30)
    self.youtube_load_button.setFixedHeight(30)
    self.youtube_folder_button.setFixedHeight(30)
    self.resolution_input.setFixedHeight(30)
    self.prefix_input.setFixedHeight(30)
    self.caption_input.setFixedHeight(30)
    self.aspect_ratio_combo.setFixedHeight(30)
    self.trim_spin.setFixedHeight(30)
    
    # Set fixed widths for consistent layout
    self.folder_button.setFixedWidth(120)
    self.refresh_button.setFixedWidth(120)
    self.theme_button.setFixedWidth(120)
    self.favorite_button.setFixedWidth(120)
    self.clear_crop_button.setFixedWidth(120)
    self.auto_advance_button.setFixedWidth(180)
    self.youtube_load_button.setFixedWidth(100)
    self.youtube_folder_button.setFixedWidth(100)
    self.aspect_ratio_combo.setFixedWidth(150)

    # self.video_list.setStyleSheet("QListWidget::item:selected { background-color: #3A4F7A; }")
    
    # RIGHT PANEL
    self.right_panel_layout = QVBoxLayout()
    right_panel = self.right_panel_layout
    # Monitoring label (replaces old shortcut info)
    # Place clock and monitoring label on the same horizontal line
    clock_monitor_layout = QHBoxLayout()
    self.monitoring_label = QLabel("Loading system status...")
    self.monitoring_label.setObjectName("monitoring_label")
    self.monitoring_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    # self.monitoring_label.setStyleSheet("font-size: 12px; color: #ECEFF4;")
    clock_monitor_layout.addWidget(self.monitoring_label, stretch=2)
    self.clock_label = QLabel()
    self.clock_label.setObjectName("clock_label")
    self.clock_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    # self.clock_label.setStyleSheet("font-size: 18px; color: #FFD700; padding-left: 12px;")
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
    from scripts.scene_slider import SceneSlider
    self.slider = SceneSlider(Qt.Orientation.Horizontal)
    self.slider.setEnabled(False)
    self.slider.sliderMoved.connect(self.editor.scrub_video)
    self.slider.scene_clicked.connect(self.on_scene_marker_clicked)
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

    # Audio editor panel (hidden by default, appears in Audio Mode)
    try:
        self.audio_editor = AudioEditor(self)
    except Exception:
        self.audio_editor = None
    if self.audio_editor is not None:
        self.audio_editor.setVisible(bool(getattr(self, 'audio_mode', False)))
        right_panel.addWidget(self.audio_editor, 1)
        # Ensure video view visibility is opposite
        try:
            self.graphics_view.setVisible(not getattr(self, 'audio_mode', False))
        except Exception:
            pass
        # Click-to-seek wiring
        try:
            if hasattr(self, 'audio_player') and self.audio_player is not None:
                self.audio_editor.playheadSeekRequested.connect(lambda ms: self.audio_player.setPosition(int(ms)))
        except Exception:
            pass
    
    self.thumbnail_label = QWidget(self)
    self.thumbnail_label.setObjectName("thumbnail_label")
    self.thumbnail_label.setWindowFlags(Qt.WindowType.ToolTip)
    # self.thumbnail_label.setStyleSheet("background-color: black; border: 1px solid white;")
    self.thumbnail_label.hide()
    right_panel.addWidget(self.thumbnail_label)
    self.thumbnail_image_label = QLabel(self.thumbnail_label)
    self.thumbnail_image_label.setGeometry(0, 0, 160, 90)
    
    self.slider.installEventFilter(self)
    

    # --- Control Buttons Row ---
    button_row = QHBoxLayout()
    
    # Play/Pause button
    self.play_pause_button = QPushButton("Play/Pause")
    self.play_pause_button.clicked.connect(self.editor.toggle_play_forward)
    button_row.addWidget(self.play_pause_button)
    
    # Audio Toggle button
    self.audio_button = QPushButton("🔇 Audio Off")
    self.audio_button.setCheckable(True)
    self.audio_button.setChecked(False)
    self.audio_button.clicked.connect(self.toggle_audio)
    # Make the audio button act as a volume rocker via mouse wheel
    self.audio_button.setToolTip("Audio: click to toggle, wheel to change volume (Shift=fine, Ctrl=coarse)")
    self.audio_button.setMouseTracking(True)
    self.audio_button.installEventFilter(self)
    # Initialize label with current volume if helper exists
    if hasattr(self, '_update_audio_button_label'):
        try:
            self._update_audio_button_label()
        except Exception:
            pass
    button_row.addWidget(self.audio_button)
    
    # Export button
    self.submit_button = QPushButton("Export Cropped Videos")
    self.submit_button.clicked.connect(self.exporter.export_videos)
    button_row.addWidget(self.submit_button)
    
    # Scene detection button
    self.detect_scenes_button = QPushButton("Detect Scenes")
    self.detect_scenes_button.clicked.connect(self.detect_scenes_for_current_video)
    button_row.addWidget(self.detect_scenes_button)
    
    right_panel.addLayout(button_row)
    # --- End Move ---
    
    # Add scene detection progress bar
    self.scene_progress_label = QLabel("Scene Detection Progress:")
    self.scene_progress_label.setVisible(False)
    right_panel.addWidget(self.scene_progress_label)
    
    self.scene_progress_bar = QProgressBar()
    self.scene_progress_bar.setVisible(False)
    right_panel.addWidget(self.scene_progress_bar)
    
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
    # Enable drag and drop on the grid widget itself
    self.multi_grid_widget.setAcceptDrops(True)
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
    # Safety check: ensure scene exists
    if not hasattr(self, 'scene') or self.scene is None:
        return
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
    

def open_theme_selector(self):
        """Open the theme selector dialog"""
        from scripts.theme_selector import ThemeSelector
        dialog = ThemeSelector(self)
        dialog.exec()

def cycle_theme(self):
        # Enhanced theme cycling with organized themes
        if not hasattr(self, '_theme_index'):
            self._theme_index = 0
        themes = [
            None,  # Default system theme
            # Premium Themes
            'styles/premium/stellar_nebula.css',
            'styles/premium/amber_twilight.css',
            'styles/premium/abyssal_blue.css',
            'styles/premium/retro_arcade.css',
            'styles/premium/brass_steam.css',
            'styles/premium/quantum_hologram.css',
            'styles/premium/cyber_neon.css',
            'styles/premium/clean_slate.css',
            # Professional Themes
            'styles/professional/corporate_night.css',
            'styles/professional/arctic_frost.css',
            'styles/professional/urban_neon.css',
            'styles/classic/gothic_horror.css',
            'styles/professional/elegant_dark.css',
            'styles/professional/soft_night.css',
            # Classic Themes
            'styles/classic/classic_mac.css',
            'styles/classic/wooden_desk.css',
            'styles/classic/deep_ocean.css',
            'styles/classic/glass_terminal.css',
            'styles/classic/sunset_glow.css',
            'styles/classic/8bit_dreams.css',
            'styles/classic/study_notes.css',
            'styles/classic/paper_art.css',
            'styles/classic/frozen_crystal.css',
            'styles/classic/code_light.css',
            # Animated Themes
            'styles/animated/pulsing_neon.css',
            'styles/animated/bubblegum_pop.css',
            'styles/animated/lava_lamp.css',
            # Minimal Themes
            'styles/minimal/pure_minimal.css',
            'styles/minimal/ocean_breeze.css',
            'styles/minimal/studio_dark.css',
            'styles/minimal/pastel_dreams.css',
            'styles/minimal/aurora_borealis.css',
            'styles/minimal/vapor_sunset.css',
            'styles/minimal/pure_dark.css',
            'styles/minimal/material_blue.css',
            'styles/minimal/solarized_dark.css',
        ]
        self._theme_index = (self._theme_index + 1) % len(themes)
        theme = themes[self._theme_index]
        
        # Preserve current window size and position
        current_size = self.size()
        current_pos = self.pos()
        
        # Get theme name for display
        if theme:
            theme_name = os.path.basename(theme).replace('.css', '').replace('_', ' ').title()
        else:
            theme_name = "System Default"
        
        if theme and os.path.exists(theme):
            with open(theme, 'r') as f:
                QApplication.instance().setStyleSheet(f.read())
            # Update status to show current theme
            if hasattr(self, 'update_status'):
                self.update_status(f"Theme: {theme_name}")
        else:
            QApplication.instance().setStyleSheet("")
            if hasattr(self, 'update_status'):
                self.update_status(f"Theme: {theme_name}")
        
        # Restore window size and position to prevent resizing
        self.resize(current_size)
        self.move(current_pos)

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
    """Toggle between favorite and non-favorite folders using FolderManager"""
    if not hasattr(self, 'folder_manager'):
        print("Error: FolderManager not initialized")
        return
    
    # Initialize last_non_favorite_folders if it doesn't exist
    if not hasattr(self, 'last_non_favorite_folders'):
        self.last_non_favorite_folders = {'audio': None, 'video': None}
    
    current_mode = 'audio' if self.audio_mode else 'video'
    
    if not self.favorite_active:
        # Save current folder as last non-favorite
        if self.folder_path and os.path.exists(self.folder_path):
            self.last_non_favorite_folders[current_mode] = self.folder_path
            # Also add to recent folders for persistence
            self.folder_manager.add_folder(current_mode, self.folder_path, is_favorite=False)
        
        # Switch to default favorite folder for current mode
        default_folder = (self.folder_manager.default_audio_folder if self.audio_mode 
                         else self.folder_manager.default_video_folder)
        
        if default_folder and os.path.exists(default_folder):
            self.folder_path = default_folder
            self.favorite_active = True
            self.favorite_button.setChecked(True)
            self.favorite_button.setText("★ Favorite (Active)")
            self.loader.folder_path = self.folder_path
            self.loader.load_folder_contents()
            if hasattr(self, 'update_folder_tree'):
                self.update_folder_tree(self.folder_path)
    else:
        # Switch back to the last non-favorite folder for this mode
        target_folder = self.last_non_favorite_folders.get(current_mode)
        
        # Fallback to the most recent non-favorite folder if no last folder is set
        if not target_folder or not os.path.exists(target_folder):
            recent_folders = self.folder_manager.get_current_folders(self.audio_mode)['recent']
            target_folder = recent_folders[0] if recent_folders else None
        
        if target_folder and os.path.exists(target_folder):
            self.folder_path = target_folder
            self.loader.folder_path = self.folder_path
            self.loader.load_folder_contents()
            if hasattr(self, 'update_folder_tree'):
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
    

def on_move_av1_clicked(self):
    from PyQt6.QtWidgets import QMessageBox
    import os
    try:
        from scripts.av1_utils import move_av1_videos
        folder = self.folder_path
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, "No Folder", "No valid folder selected.")
            return
        moved = move_av1_videos(folder)
        if moved:
            msg = f"Moved {len(moved)} AV1 videos to 'AV1' subfolder:\n" + "\n".join(moved)
        else:
            msg = "No AV1 videos found."
        QMessageBox.information(self, "AV1 Move Complete", msg)
        self.loader.load_folder_contents()  # Refresh UI
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to move AV1 videos:\n{e}")

def check_current_video_item(self):
    # Find the list item corresponding to the current video and mark it checked.
    for i in range(self.video_list.count()):
        item = self.video_list.item(i)
        if item.text() == self.current_video:
            if item.checkState() != Qt.CheckState.Checked:
                item.setCheckState(Qt.CheckState.Checked)
            break