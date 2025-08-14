from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, 
    QPushButton, QLabel, QScrollArea, QWidget, QFrame, QApplication,
    QTabWidget, QFileDialog, QMenu, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QPalette, QColor, QAction, QIcon
import os
import json
from PyQt6.QtCore import QStandardPaths

class ThemeSelector(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Theme & Folder Manager - SharkBit")
        self.setModal(True)
        self.resize(800, 600)
        
        # Initialize folder manager and current folders
        self.folder_manager = parent.folder_manager if hasattr(parent, 'folder_manager') else None
        self.current_audio_folder = ""
        self.current_video_folder = ""
        
        # Load current folders from parent if available
        if hasattr(parent, 'folder_path'):
            if hasattr(parent, 'audio_mode') and parent.audio_mode:
                self.current_audio_folder = parent.folder_path
            else:
                self.current_video_folder = parent.folder_path
        
        # Theme categories and descriptions
        self.theme_categories = {
            "Premium Themes": [
                ("premium/stellar_nebula.css", " Stellar Nebula", "Deep space nebula with ethereal purples and glowing effects"),
                ("premium/amber_twilight.css", " Amber Twilight", "Warm dusk aesthetic with oranges, purples, and golden highlights"),
                ("premium/abyssal_blue.css", " Abyssal Blue", "Mysterious deep sea with teals, blues, and coral accents"),
                ("premium/retro_arcade.css", " Retro Arcade", "80s arcade aesthetic with neon pinks and electric blues"),
                ("premium/brass_steam.css", " Brass & Steam", "Victorian industrial aesthetic with brass and mechanical elements"),
                ("premium/quantum_hologram.css", " Quantum Hologram", "Futuristic iridescent theme with glass-like effects"),
                ("premium/cyber_neon.css", " Cyber Neon", "Elegant neon theme with sophisticated aesthetics"),
                ("premium/clean_slate.css", " Clean Slate", "Clean light theme with modern design")
            ],
            "Professional Themes": [
                ("professional/corporate_night.css", " Corporate Night", "Professional dark theme with excellent contrast"),
                ("professional/arctic_frost.css", " Arctic Frost", "Arctic frost crystal theme"),
                ("professional/urban_neon.css", " Urban Neon", "Japanese cyberpunk urban theme"),
                ("classic/gothic_horror.css", " Gothic Horror", "Gothic horror lair with blood red accents"),
                ("professional/elegant_dark.css", " Elegant Dark", "Sophisticated elegant theme"),
                ("professional/soft_night.css", " Soft Night", "Dreamy ethereal aesthetic")
            ],
            "Classic Themes": [
                ("classic/classic_mac.css", " Classic Mac", "Classic Mac aesthetic with better readability"),
                ("classic/wooden_desk.css", " Wooden Desk", "Natural wood textures"),
                ("classic/deep_ocean.css", " Deep Ocean", "Deep ocean colors"),
                ("classic/glass_terminal.css", " Glass Terminal", "Glass terminal aesthetic"),
                ("classic/sunset_glow.css", " Sunset Glow", "Warm elegant browns and golds"),
                ("classic/8bit_dreams.css", " 8-Bit Dreams", "Retro pixel art style"),
                ("classic/study_notes.css", " Study Notes", "Paper notebook inspired"),
                ("classic/paper_art.css", " Paper Art", "Paper folding inspired"),
                ("classic/frozen_crystal.css", " Frozen Crystal", "Cool ice and crystal colors"),
                ("classic/code_light.css", " Code Light", "GitHub-inspired light theme")
            ],
            "Animated Themes": [
                ("animated/pulsing_neon.css", " Pulsing Neon", "Animated neon aesthetic with better readability"),
                ("animated/bubblegum_pop.css", " Bubblegum Pop", "Sweet bubblegum colors"),
                ("animated/lava_lamp.css", " Lava Lamp", "Colorful gradient theme")
            ],
            "Minimal Themes": [
                ("minimal/pure_minimal.css", " Pure Minimal", "Clean and simple design"),
                ("minimal/ocean_breeze.css", " Ocean Breeze", "Cool blue tones and refreshing design"),
                ("minimal/pastel_dreams.css", " Pastel Dreams", "Soft pastel colors"),
                ("minimal/pure_dark.css", " Pure Dark", "Classic dark theme"),
                ("minimal/material_blue.css", " Material Blue", "Material design ocean theme"),
                ("minimal/solarized_dark.css", " Solarized Dark", "Eye-friendly dark theme")
            ]
        }
        
        self.setup_ui()
        self.load_themes()
        
    def setup_ui(self):
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Theme tab
        self.setup_theme_tab()
        
        # Folder tab
        self.setup_folder_tab()
        
        # Add tabs to main layout
        main_layout.addWidget(self.tabs)
        
        # Close button at bottom
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        main_layout.addWidget(self.close_button, alignment=Qt.AlignmentFlag.AlignRight)
    
    def setup_theme_tab(self):
        """Set up the theme selection tab"""
        theme_tab = QWidget()
        layout = QVBoxLayout(theme_tab)
        
        # Title
        title = QLabel("Choose Your Theme")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel("Press 'T' to cycle themes quickly • Click a theme to apply it")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(instructions)
        
        # Theme list
        self.theme_list = QListWidget()
        self.theme_list.setAlternatingRowColors(True)
        self.theme_list.itemDoubleClicked.connect(self.apply_theme)
        self.theme_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.theme_list.customContextMenuRequested.connect(self.show_theme_context_menu)
        layout.addWidget(self.theme_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.apply_button = QPushButton("Apply Selected Theme")
        self.apply_button.clicked.connect(self.apply_selected_theme)
        button_layout.addWidget(self.apply_button)
        
        self.cycle_button = QPushButton("Cycle Next Theme")
        self.cycle_button.clicked.connect(self.cycle_theme)
        button_layout.addWidget(self.cycle_button)
        
        layout.addLayout(button_layout)
        
        # Add tab
        self.tabs.addTab(theme_tab, "Themes")
    
    def setup_folder_tab(self):
        """Set up the folder management tab"""
        if not self.folder_manager:
            return
            
        folder_tab = QWidget()
        layout = QVBoxLayout(folder_tab)
        
        # Title
        title = QLabel("Folder Management")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Mode selector
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Current Mode:")
        self.mode_selector = QListWidget()
        self.mode_selector.addItems(["Video Mode", "Audio Mode"])
        self.mode_selector.setMaximumHeight(80)
        self.mode_selector.currentRowChanged.connect(self.update_folder_display)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_selector)
        layout.addLayout(mode_layout)
        
        # Current folder
        current_layout = QHBoxLayout()
        self.current_folder_label = QLabel("Current: ")
        self.current_folder_label.setWordWrap(True)
        current_layout.addWidget(self.current_folder_label)
        
        # Default folder
        default_layout = QHBoxLayout()
        default_label = QLabel("Default:")
        self.default_folder_label = QLabel()
        self.default_folder_label.setWordWrap(True)
        set_default_btn = QPushButton("Set as Default")
        set_default_btn.clicked.connect(self.set_current_as_default)
        default_layout.addWidget(default_label)
        default_layout.addWidget(self.default_folder_label)
        default_layout.addWidget(set_default_btn)
        
        # Favorites section
        favorites_label = QLabel("Favorite Folders:")
        self.favorites_list = QListWidget()
        self.favorites_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.favorites_list.customContextMenuRequested.connect(self.show_folder_context_menu)
        self.favorites_list.itemDoubleClicked.connect(self.load_folder_from_list)
        
        # Recent folders
        recent_label = QLabel("Recent Folders:")
        self.recent_folders_list = QListWidget()
        self.recent_folders_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.recent_folders_list.customContextMenuRequested.connect(self.show_folder_context_menu)
        self.recent_folders_list.itemDoubleClicked.connect(self.load_folder_from_list)
        
        # System folders
        system_label = QLabel("System Folders:")
        self.system_folders_list = QListWidget()
        self.system_folders_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.system_folders_list.customContextMenuRequested.connect(self.show_system_folder_context_menu)
        self.system_folders_list.itemDoubleClicked.connect(self.load_system_folder)
        
        # Folder buttons
        folder_buttons = QHBoxLayout()
        
        # Set current folder button
        set_current_btn = QPushButton("Set Current Folder")
        set_current_btn.setToolTip("Set the selected folder as the current working directory")
        set_current_btn.clicked.connect(self.set_current_folder)
        folder_buttons.addWidget(set_current_btn)
        
        # Add to favorites button
        add_favorite_btn = QPushButton("Add to Favorites")
        add_favorite_btn.setToolTip("Add the selected folder to favorites")
        add_favorite_btn.clicked.connect(self.add_to_favorites)
        folder_buttons.addWidget(add_favorite_btn)
        
        # Set as default button
        set_default_btn = QPushButton("Set as Default")
        set_default_btn.setToolTip("Set the selected folder as default for this mode")
        set_default_btn.clicked.connect(self.set_current_as_default)
        folder_buttons.addWidget(set_default_btn)
        
        # Add widgets to layout
        layout.addLayout(current_layout)
        layout.addLayout(default_layout)
        layout.addWidget(favorites_label)
        layout.addWidget(self.favorites_list)
        layout.addWidget(recent_label)
        layout.addWidget(self.recent_folders_list)
        layout.addWidget(system_label)
        layout.addWidget(self.system_folders_list)
        layout.addLayout(folder_buttons)
        
        # Add tab
        self.tabs.addTab(folder_tab, "Folders")
        
        # Initial update - default to video mode (index 0)
        self.update_folder_display(0)
        
    def load_themes(self):
        """Load all available themes into the list"""
        self.theme_list.clear()
        
        for category, themes in self.theme_categories.items():
            # Add category header
            header = QListWidgetItem(f"--- {category} ---")
            header.setFlags(Qt.ItemFlag.NoItemFlags)  # Make it non-selectable
            header.setBackground(QColor(240, 240, 240))
            self.theme_list.addItem(header)
            
            # Add themes in this category
            for theme_file, theme_name, description in themes:
                item = QListWidgetItem(f"{theme_name} - {description}")
                item.setData(Qt.ItemDataRole.UserRole, theme_file)
                item.setToolTip(f"File: {theme_file}")
                self.theme_list.addItem(item)
                
        # Add system default option
        default_item = QListWidgetItem(" System Default\n   Use your system's default appearance")
        default_item.setData(Qt.ItemDataRole.UserRole, None)
        self.theme_list.addItem(default_item)
        
    def apply_theme(self, item):
        """Apply the selected theme"""
        if not isinstance(item, QListWidgetItem):
            item = self.theme_list.currentItem()
            if not item:
                return
        
        # Get the theme path and name from the item data
        theme_path = item.data(Qt.ItemDataRole.UserRole)
        theme_name = item.text().split(' - ')[0].strip()  # Clean up the theme name
        
        if theme_path is None:  # System default
            QApplication.instance().setStyleSheet("")
            if hasattr(self.parent, 'update_status'):
                self.parent.update_status("Theme applied: System Default")
            # Save the theme as None for system default
            if hasattr(self.parent, 'current_theme'):
                self.parent.current_theme = None
        else:
            # Apply the stylesheet
            try:
                # Handle both forward and backward slashes in theme paths
                theme_path = theme_path.replace('\\', '/')  # Normalize to forward slashes
                
                # First try the theme path as-is (relative to styles/)
                theme_file = os.path.join("styles", theme_path)
                
                # If not found, try with backslashes on Windows
                if not os.path.exists(theme_file):
                    theme_file = os.path.join("styles", theme_path.replace('/', '\\'))
                
                # If still not found, try in the root directory
                if not os.path.exists(theme_file):
                    theme_file = os.path.join(os.getcwd(), "styles", theme_path)
                    
                # If the file still doesn't exist, try one more time with backslashes
                if not os.path.exists(theme_file):
                    theme_file = os.path.join(os.getcwd(), "styles", theme_path.replace('/', '\\'))
                    
                if not os.path.exists(theme_file):
                    raise FileNotFoundError(f"Theme file not found: {os.path.join('styles', theme_path)}")
                
                # Convert to absolute path for better error messages
                theme_file = os.path.abspath(theme_file)
                
                with open(theme_file, "r") as f:
                    stylesheet = f.read()
                    QApplication.instance().setStyleSheet(stylesheet)
                    if hasattr(self.parent, 'update_status'):
                        self.parent.update_status(f"Theme applied: {theme_name}")
                    # Save the current theme
                    if hasattr(self.parent, 'current_theme'):
                        self.parent.current_theme = theme_path
            except Exception as e:
                print(f"Error loading theme: {e}")
                QMessageBox.warning(self, "Theme Error", f"Could not load theme: {theme_name}\nError: {str(e)}")
                return
        
        # Save the current theme to settings
        if hasattr(self, 'parent') and hasattr(self.parent, 'save_settings'):
            self.parent.save_settings()
                
    def apply_selected_theme(self):
        current_item = self.theme_list.currentItem()
        if current_item:
            self.apply_theme(current_item)
            
    def cycle_theme(self):
        # Get all theme items (skip category headers)
        all_themes = []
        for i in range(self.theme_list.count()):
            item = self.theme_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) is not None:  # Skip category headers
                all_themes.append(item)
        
        if not all_themes:
            return
            
        # Find current theme
        current_theme = getattr(self.parent, 'current_theme', None)
        current_index = 0
        
        if current_theme is not None:
            # Find the current theme in the list
            for i, item in enumerate(all_themes):
                if item.data(Qt.ItemDataRole.UserRole) == current_theme:
                    current_index = i
                    break
        
        # Get next theme (cycle to start if at end)
        next_index = (current_index + 1) % len(all_themes)
        next_theme_item = all_themes[next_index]
        
        # Apply the next theme
        self.theme_list.setCurrentItem(next_theme_item)
        self.apply_theme(next_theme_item)
        
    def show_theme_context_menu(self, position):
        """Show context menu for theme actions"""
        item = self.theme_list.itemAt(position)
        if not item:
            return
            
        menu = QMenu()
        
        # Add preview action
        preview_action = menu.addAction("Preview Theme")
        preview_action.triggered.connect(lambda: self.apply_theme(item))
        
        # Add set as default action
        set_default_action = menu.addAction("Set as Default Theme")
        set_default_action.triggered.connect(lambda: self.set_default_theme(item))
        
        # Show the menu
        menu.exec(self.theme_list.viewport().mapToGlobal(position))
    
    def set_default_theme(self, item):
        """Set the selected theme as the default theme"""
        theme_path = item.data(Qt.ItemDataRole.UserRole)
        if not theme_path:
            return
            
        # Here you would implement the logic to save this as the default theme
        # For example, to a config file or settings
        QMessageBox.information(self, "Default Theme Set", 
                              f"Default theme set to: {item.text().strip()}")
        
        # Update the theme immediately if needed
        self.apply_theme(item)
        
    def update_folder_display(self, mode_index):
        """Update the folder display based on the selected mode (Audio/Video)"""
        if not hasattr(self, 'folder_manager') or not self.folder_manager:
            return
            
        # Determine the current mode
        is_audio_mode = (mode_index == 1)  # 0 = Video, 1 = Audio
        self.current_mode = 'audio' if is_audio_mode else 'video'
        
        # Get the current folder for this mode
        if is_audio_mode:
            current_folder = self.current_audio_folder
        else:
            current_folder = self.current_video_folder
            
        # Get folders from the folder manager
        folders = self.folder_manager.get_current_folders(is_audio_mode)
            
        # Update current folder display
        self.current_folder_label.setText(f"Current: {current_folder or 'Not set'}")
        
        # Update default folder display
        default_folder = self.folder_manager.default_audio_folder if is_audio_mode else self.folder_manager.default_video_folder
        self.default_folder_label.setText(f"Default: {default_folder or 'Not set'}")
        
        # Update favorites list
        self.favorites_list.clear()
        favorites = folders.get('favorites', [])
        self.favorites_list.addItems(folders.get('favorites', []))
        
        # Update recent folders list
        self.recent_folders_list.clear()
        self.recent_folders_list.addItems(folders.get('recent', []))
        
        # Update system folders list
        self.system_folders_list.clear()
        system_folders = self.folder_manager.get_system_folders()
        self.system_folders_list.addItems(system_folders.values())
        
        # Update the current folder in our tracking
        if is_audio_mode:
            self.current_audio_folder = current_folder
        else:
            self.current_video_folder = current_folder
        
    def set_current_as_default(self):
        """Set the current folder as the default for the selected mode"""
        if not hasattr(self, 'folder_manager') or not self.folder_manager:
            QMessageBox.warning(self, "Error", "Folder manager is not available.")
            return
            
        if not hasattr(self, 'current_mode'):
            self.current_mode = 'video'  # Default to video mode if not set
            
        # Get the current folder for the selected mode
        is_audio_mode = (self.current_mode == 'audio')
        folders = self.folder_manager.get_current_folders(is_audio_mode)
        current_folder = folders.get('current', '')
        
        if not current_folder or not os.path.exists(current_folder):
            QMessageBox.warning(self, "Invalid Folder", "Current folder is not valid or accessible.")
            return
            
        try:
            # Set as default folder for the current mode
            if is_audio_mode:
                self.folder_manager.default_audio_folder = current_folder
            else:
                self.folder_manager.default_video_folder = current_folder
                
            # Save the updated settings
            self.folder_manager.save_settings()
            
            # Update the display
            self.update_folder_display(1 if is_audio_mode else 0)
            
            QMessageBox.information(self, "Default Folder Set", 
                                  f"Default {self.current_mode} folder set to:\n{current_folder}")
                                  
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to set default folder:\n{str(e)}")
            
    def show_folder_context_menu(self, position):
        """Show context menu for folder items (favorites and recent)"""
        # Determine which list was clicked
        list_widget = self.sender()
        if not list_widget:
            return
            
        item = list_widget.itemAt(position)
        if not item:
            return
            
        folder_path = item.text()
        if not folder_path or not os.path.exists(folder_path):
            return
            
        menu = QMenu()
        
        # Open in File Explorer
        open_action = menu.addAction("Open in File Explorer")
        open_action.triggered.connect(lambda: os.startfile(folder_path))
        
        # Set as Default
        set_default_action = menu.addAction("Set as Default Folder")
        set_default_action.triggered.connect(lambda: self.set_folder_as_default(folder_path))
        
        # Remove from List (only for favorites)
        if list_widget == self.favorites_list:
            remove_action = menu.addAction("Remove from Favorites")
            remove_action.triggered.connect(lambda: self.remove_folder_from_favorites(folder_path))
        
        # Show the menu
        menu.exec(list_widget.viewport().mapToGlobal(position))
    
    def set_folder_as_default(self, folder_path):
        """Set the specified folder as default for the current mode"""
        if not hasattr(self, 'folder_manager') or not self.folder_manager:
            return
            
        if not folder_path or not os.path.exists(folder_path):
            QMessageBox.warning(self, "Invalid Folder", "The specified folder is not valid or accessible.")
            return
            
        try:
            if self.current_mode == 'audio':
                self.folder_manager.default_audio_folder = folder_path
            else:
                self.folder_manager.default_video_folder = folder_path
                
            self.folder_manager.save_settings()
            self.update_folder_display(1 if self.current_mode == 'audio' else 0)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to set default folder:\n{str(e)}")
    
    def remove_folder_from_favorites(self, folder_path):
        """Remove a folder from favorites"""
        if not hasattr(self, 'folder_manager') or not self.folder_manager:
            return
            
        try:
            self.folder_manager.remove_folder(self.current_mode, folder_path, folder_type='favorites')
            self.update_folder_display(1 if self.current_mode == 'audio' else 0)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to remove folder from favorites:\n{str(e)}")
            
    def load_folder_from_list(self, item):
        """Load the selected folder from the favorites or recent list"""
        if not item:
            return
            
        folder_path = item.text()
        if not folder_path or not os.path.exists(folder_path):
            QMessageBox.warning(self, "Invalid Folder", "The selected folder no longer exists.")
            return
            
        try:
            # Get the current mode (audio or video)
            is_audio_mode = (self.current_mode == 'audio')
            
            # Add to recent folders if it's not a favorite selection
            # This ensures the folder appears in the recent folders list for toggling
            if self.sender() != self.favorites_list:
                self.folder_manager.add_folder(
                    self.current_mode,
                    folder_path,
                    is_favorite=False  # Just adding to recent, not marking as favorite
                )
            
            # Update our current folder tracking
            if is_audio_mode:
                self.current_audio_folder = folder_path
            else:
                self.current_video_folder = folder_path
                
            # Update the parent's folder path if the mode matches
            if hasattr(self.parent, 'audio_mode') and self.parent.audio_mode == is_audio_mode:
                # If we were in favorite mode, turn it off when selecting a new folder
                if hasattr(self.parent, 'favorite_active') and self.parent.favorite_active:
                    self.parent.favorite_active = False
                    if hasattr(self.parent, 'favorite_button'):
                        self.parent.favorite_button.setChecked(False)
                        self.parent.favorite_button.setText("★ Favorite Folder")
                
                self.parent.folder_path = folder_path
                if hasattr(self.parent, 'loader') and hasattr(self.parent.loader, 'load_folder_contents'):
                    self.parent.loader.load_folder_contents()
                if hasattr(self.parent, 'update_folder_tree'):
                    self.parent.update_folder_tree(folder_path)
        
            # Update the display
            self.update_folder_display(1 if is_audio_mode else 0)
            
            # Show success message
            QMessageBox.information(self, "Folder Loaded", 
                                 f"{self.current_mode.capitalize()} folder updated to:\n{folder_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load folder:\n{str(e)}")
            
    def show_system_folder_context_menu(self, position):
        """Show context menu for system folder items"""
        item = self.system_folders_list.itemAt(position)
        if not item:
            return
            
        folder_path = item.text()
        if not folder_path or not os.path.exists(folder_path):
            return
            
        menu = QMenu()
        
        # Open in File Explorer
        open_action = menu.addAction("Open in File Explorer")
        open_action.triggered.connect(lambda: os.startfile(folder_path))
        
        # Add to Favorites
        current_favorites = self.folder_manager.get_folders(self.current_mode)['favorites']
        if folder_path not in current_favorites:
            add_fav_action = menu.addAction("Add to Favorites")
            add_fav_action.triggered.connect(lambda: self.add_system_folder_to_favorites(folder_path))
        
        # Set as Default
        set_default_action = menu.addAction("Set as Default Folder")
        set_default_action.triggered.connect(lambda: self.set_folder_as_default(folder_path))
        
        # Show the menu
        menu.exec(self.system_folders_list.viewport().mapToGlobal(position))
    
    def add_system_folder_to_favorites(self, folder_path):
        """Add a system folder to favorites"""
        if not hasattr(self, 'folder_manager') or not self.folder_manager:
            return
            
        try:
            self.folder_manager.add_folder(self.current_mode, folder_path, folder_type='favorites')
            self.update_folder_display(1 if self.current_mode == 'audio' else 0)
            QMessageBox.information(self, "Added to Favorites", 
                                  f"Added folder to favorites:\n{folder_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                               f"Failed to add folder to favorites:\n{str(e)}")
                               
    def load_system_folder(self, item):
        """Load the selected system folder"""
        if not item:
            return
            
        folder_name = item.text()
        system_folders = self.folder_manager.get_system_folders()
        
        if folder_name not in system_folders or not os.path.exists(system_folders[folder_name]):
            QMessageBox.warning(self, "Invalid Folder", "The selected system folder is not accessible.")
            return
            
        folder_path = system_folders[folder_name]
        
        try:
            # Get the current mode (audio or video)
            is_audio_mode = (self.current_mode == 'audio')
            
            # Add to recent folders
            self.folder_manager.add_folder(
                                 f"{self.current_mode.capitalize()} folder updated to system folder:\n{folder_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load system folder:\n{str(e)}")
            
    def add_folder(self):
        """Open a dialog to add a new folder"""
        if not hasattr(self, 'folder_manager') or not self.folder_manager:
            return
            
        # Get the current mode
        if not hasattr(self, 'current_mode'):
            self.current_mode = 'video'  # Default to video mode if not set
            
        # Open folder dialog
        folder_path = QFileDialog.getExistingDirectory(
            self,
            f"Select {self.current_mode.capitalize()} Folder",
            os.path.expanduser("~"),  # Start at user's home directory
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        
        if not folder_path:  # User cancelled
            return
            
        if not os.path.exists(folder_path):
            QMessageBox.warning(self, "Invalid Folder", "The selected folder does not exist.")
            return
            
        try:
            # Add to favorites
            self.folder_manager.add_folder(self.current_mode, folder_path, folder_type='favorites')
            
            # Update the current folder
            if self.current_mode == 'audio':
                self.folder_manager.current_audio_folder = folder_path
            else:
                self.folder_manager.current_video_folder = folder_path
                
            # Update the parent's folder path if it exists
            if hasattr(self.parent, 'folder_path'):
                self.parent.folder_path = folder_path
                
            # Update the display
            self.update_folder_display(1 if self.current_mode == 'audio' else 0)
            
            # Show success message
            QMessageBox.information(self, "Folder Added", 
                                  f"Added folder to favorites and set as current:\n{folder_path}")
                                  
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                               f"Failed to add folder:\n{str(e)}")
                               
    def set_current_folder(self):
        """Set the selected folder as the current working directory"""
        # Check which list has focus
        current_list = None
        if self.favorites_list.hasFocus():
            current_item = self.favorites_list.currentItem()
            current_list = self.favorites_list
        elif self.recent_folders_list.hasFocus():
            current_item = self.recent_folders_list.currentItem()
            current_list = self.recent_folders_list
        elif self.system_folders_list.hasFocus():
            current_item = self.system_folders_list.currentItem()
            current_list = self.system_folders_list
            
        if not current_item:
            # If no item is selected, open folder dialog
            folder_path = QFileDialog.getExistingDirectory(
                self,
                "Select Folder",
                os.path.expanduser("~"),
                QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
            )
            if not folder_path:
                return
        else:
            folder_path = current_item.text()
            
        if not os.path.exists(folder_path):
            QMessageBox.warning(self, "Invalid Folder", "The selected folder does not exist.")
            return
            
        try:
            # Update the current folder in folder manager
            if hasattr(self.folder_manager, f'set_current_{self.current_mode}_folder'):
                getattr(self.folder_manager, f'set_current_{self.current_mode}_folder')(folder_path)
                
            # Update the parent's folder path if it exists and matches the current mode
            if hasattr(self.parent, 'folder_path') and hasattr(self.parent, 'audio_mode'):
                if self.parent.audio_mode == (self.current_mode == 'audio'):
                    self.parent.folder_path = folder_path
                    if hasattr(self.parent, 'loader') and hasattr(self.parent.loader, 'load_folder_contents'):
                        self.parent.loader.load_folder_contents()
                    if hasattr(self.parent, 'update_folder_tree'):
                        self.parent.update_folder_tree(folder_path)
            
            # Add to recent folders if not already there
            self.folder_manager.add_folder(self.current_mode, folder_path, is_favorite=False)
            
            # Update the display
            self.update_folder_display(1 if self.current_mode == 'audio' else 0)
            
            QMessageBox.information(self, "Folder Set", 
                                 f"Current {self.current_mode} folder set to:\n{folder_path}")
                                  
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                               f"Failed to set current folder:\n{str(e)}")
                               
    def add_to_favorites(self):
        """Add the selected folder to favorites"""
        # Check which list has focus
        current_item = None
        if self.recent_folders_list.hasFocus():
            current_item = self.recent_folders_list.currentItem()
        elif self.system_folders_list.hasFocus():
            current_item = self.system_folders_list.currentItem()
            
        if not current_item:
            # If no item is selected, open folder dialog
            folder_path = QFileDialog.getExistingDirectory(
                self,
                "Select Folder to Add to Favorites",
                os.path.expanduser("~"),
                QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
            )
            if not folder_path:
                return
        else:
            folder_path = current_item.text()
            
        if not os.path.exists(folder_path):
            QMessageBox.warning(self, "Invalid Folder", "The selected folder does not exist.")
            return
            
        try:
            # Add to favorites
            self.folder_manager.add_folder(self.current_mode, folder_path, is_favorite=True)
            
            # Update the display
            self.update_folder_display(1 if self.current_mode == 'audio' else 0)
            
            QMessageBox.information(self, "Favorite Added", 
                                 f"Added to {self.current_mode} favorites:\n{folder_path}")
                                  
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                               f"Failed to add to favorites:\n{str(e)}")