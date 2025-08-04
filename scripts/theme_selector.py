from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, 
    QPushButton, QLabel, QScrollArea, QWidget, QFrame, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor
import os

class ThemeSelector(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Theme Selector - SharkBit")
        self.setModal(True)
        self.resize(600, 500)
        
        # Theme categories and descriptions
        self.theme_categories = {
            "Premium Themes": [
                ("premium/stellar_nebula.css", "🌌 Stellar Nebula", "Deep space nebula with ethereal purples and glowing effects"),
                ("premium/amber_twilight.css", "🌅 Amber Twilight", "Warm dusk aesthetic with oranges, purples, and golden highlights"),
                ("premium/abyssal_blue.css", "🌊 Abyssal Blue", "Mysterious deep sea with teals, blues, and coral accents"),
                ("premium/retro_arcade.css", "🎮 Retro Arcade", "80s arcade aesthetic with neon pinks and electric blues"),
                ("premium/brass_steam.css", "⚙️ Brass & Steam", "Victorian industrial aesthetic with brass and mechanical elements"),
                ("premium/quantum_hologram.css", "💎 Quantum Hologram", "Futuristic iridescent theme with glass-like effects"),
                ("premium/cyber_neon.css", "🌿 Cyber Neon", "Elegant neon theme with sophisticated aesthetics"),
                ("premium/clean_slate.css", "☀️ Clean Slate", "Clean light theme with modern design")
            ],
            "Professional Themes": [
                ("professional/corporate_night.css", "🌙 Corporate Night", "Professional dark theme with excellent contrast"),
                ("professional/arctic_frost.css", "❄️ Arctic Frost", "Arctic frost crystal theme"),
                ("professional/urban_neon.css", "🌃 Urban Neon", "Japanese cyberpunk urban theme"),
                ("classic/gothic_horror.css", "🧛 Gothic Horror", "Gothic horror lair with blood red accents"),
                ("professional/elegant_dark.css", "🌙 Elegant Dark", "Sophisticated elegant theme"),
                ("professional/soft_night.css", "🌆 Soft Night", "Dreamy ethereal aesthetic")
            ],
            "Classic Themes": [
                ("classic/classic_mac.css", "🖥️ Classic Mac", "Classic Mac aesthetic with better readability"),
                ("classic/wooden_desk.css", "🪵 Wooden Desk", "Natural wood textures"),
                ("classic/deep_ocean.css", "🐠 Deep Ocean", "Deep ocean colors"),
                ("classic/glass_terminal.css", "💻 Glass Terminal", "Glass terminal aesthetic"),
                ("classic/sunset_glow.css", "📺 Sunset Glow", "Warm elegant browns and golds"),
                ("classic/8bit_dreams.css", "👾 8-Bit Dreams", "Retro pixel art style"),
                ("classic/study_notes.css", "📄 Study Notes", "Paper notebook inspired"),
                ("classic/paper_art.css", "📄 Paper Art", "Paper folding inspired"),
                ("classic/frozen_crystal.css", "🧊 Frozen Crystal", "Cool ice and crystal colors"),
                ("classic/code_light.css", "🐙 Code Light", "GitHub-inspired light theme")
            ],
            "Animated Themes": [
                ("animated/pulsing_neon.css", "💫 Pulsing Neon", "Animated neon aesthetic with better readability"),
                ("animated/bubblegum_pop.css", "🍬 Bubblegum Pop", "Sweet bubblegum colors"),
                ("animated/lava_lamp.css", "🌋 Lava Lamp", "Colorful gradient theme")
            ],
            "Minimal Themes": [
                ("minimal/pure_minimal.css", "📝 Pure Minimal", "Clean and simple design"),
                ("minimal/ocean_breeze.css", "🎨 Ocean Breeze", "Cool blue tones and refreshing design"),
                ("minimal/pastel_dreams.css", "🌸 Pastel Dreams", "Soft pastel colors"),
                ("minimal/pure_dark.css", "🌑 Pure Dark", "Classic dark theme"),
                ("minimal/material_blue.css", "🌊 Material Blue", "Material design ocean theme"),
                ("minimal/solarized_dark.css", "☀️ Solarized Dark", "Eye-friendly dark theme")
            ]
        }
        
        self.setup_ui()
        self.load_themes()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
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
        self.theme_list.itemClicked.connect(self.apply_theme)
        layout.addWidget(self.theme_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.apply_button = QPushButton("Apply Selected Theme")
        self.apply_button.clicked.connect(self.apply_selected_theme)
        button_layout.addWidget(self.apply_button)
        
        self.cycle_button = QPushButton("Cycle Next Theme")
        self.cycle_button.clicked.connect(self.cycle_theme)
        button_layout.addWidget(self.cycle_button)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
    def load_themes(self):
        self.theme_list.clear()
        
        for category, themes in self.theme_categories.items():
            # Add category header
            category_item = QListWidgetItem(f"━━━ {category} ━━━")
            category_item.setFlags(Qt.ItemFlag.NoItemFlags)  # Make it non-selectable
            category_item.setBackground(QColor(200, 200, 200))
            category_item.setForeground(QColor(50, 50, 50))
            font = QFont()
            font.setBold(True)
            category_item.setFont(font)
            self.theme_list.addItem(category_item)
            
            # Add themes in this category
            for filename, name, description in themes:
                theme_path = f"styles/{filename}"
                if os.path.exists(theme_path):
                    item = QListWidgetItem(f"{name}\n   {description}")
                    item.setData(Qt.ItemDataRole.UserRole, theme_path)
                    self.theme_list.addItem(item)
                    
        # Add system default option
        default_item = QListWidgetItem("🖥️ System Default\n   Use your system's default appearance")
        default_item.setData(Qt.ItemDataRole.UserRole, None)
        self.theme_list.addItem(default_item)
        
    def apply_theme(self, item):
        theme_path = item.data(Qt.ItemDataRole.UserRole)
        
        # Preserve parent window size and position
        if self.parent:
            current_size = self.parent.size()
            current_pos = self.parent.pos()
        
        if theme_path and os.path.exists(theme_path):
            with open(theme_path, 'r') as f:
                QApplication.instance().setStyleSheet(f.read())
            theme_name = os.path.basename(theme_path).replace('.css', '').replace('_', ' ').title()
            if hasattr(self.parent, 'update_status'):
                self.parent.update_status(f"Theme applied: {theme_name}")
        elif theme_path is None:  # System default
            QApplication.instance().setStyleSheet("")
            if hasattr(self.parent, 'update_status'):
                self.parent.update_status("Theme applied: System Default")
        
        # Restore parent window size and position to prevent resizing
        if self.parent:
            self.parent.resize(current_size)
            self.parent.move(current_pos)
                
    def apply_selected_theme(self):
        current_item = self.theme_list.currentItem()
        if current_item:
            self.apply_theme(current_item)
            
    def cycle_theme(self):
        if hasattr(self.parent, 'cycle_theme'):
            self.parent.cycle_theme() 