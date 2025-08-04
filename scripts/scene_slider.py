from PyQt6.QtWidgets import QSlider, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QMouseEvent
import math

class SceneSlider(QSlider):
    """Custom slider with scene markers"""
    
    scene_clicked = pyqtSignal(int)  # Emitted when a scene marker is clicked
    
    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.scene_markers = []  # List of frame positions for scene markers
        self.scene_colors = []   # List of colors for scene markers
        self.marker_height = 8   # Height of scene markers
        self.marker_width = 2    # Width of scene markers
        self.hovered_marker = -1 # Index of currently hovered marker
        self.setMouseTracking(True)
        
    def set_scene_markers(self, scene_frames):
        """Set scene markers from a list of frame positions"""
        self.scene_markers = scene_frames
        self.scene_colors = []
        
        # Generate colors for markers
        for i in range(len(scene_frames)):
            # Create a color gradient from blue to red
            hue = (i * 137.5) % 360  # Golden angle for good distribution
            self.scene_colors.append(QColor.fromHsv(int(hue), 200, 255))
            
        self.update()
        
    def clear_scene_markers(self):
        """Clear all scene markers"""
        self.scene_markers = []
        self.scene_colors = []
        self.hovered_marker = -1
        self.update()
        
    def paintEvent(self, event):
        """Custom paint event to draw scene markers"""
        super().paintEvent(event)
        
        if not self.scene_markers or not self.scene_colors:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get slider geometry
        slider_rect = self.geometry()
        slider_width = slider_rect.width()
        slider_height = slider_rect.height()
        
        # Calculate marker positions
        max_value = self.maximum()
        if max_value <= 0:
            return
            
        for i, frame_pos in enumerate(self.scene_markers):
            # Safety check for array bounds
            if i >= len(self.scene_colors):
                continue
                
            # Calculate x position based on frame position
            x = int((frame_pos / max_value) * slider_width)
            
            # Clamp x position to slider bounds
            x = max(0, min(x, slider_width - 1))
            
            # Determine marker color and size
            if i == self.hovered_marker:
                color = self.scene_colors[i].lighter(150)  # Lighter when hovered
                marker_width = self.marker_width * 2
                marker_height = self.marker_height * 1.5
            else:
                color = self.scene_colors[i]
                marker_width = self.marker_width
                marker_height = self.marker_height
                
            # Ensure minimum marker size
            marker_width = max(1, marker_width)
            marker_height = max(1, marker_height)
                
            # Draw marker
            painter.setPen(QPen(color, 1))
            painter.setBrush(QBrush(color))
            
            # Create triangle points with bounds checking
            top_y = max(0, slider_height - marker_height - 2)
            bottom_y = min(slider_height - 2, slider_height - 1)
            left_x = max(0, x - marker_width // 2)
            right_x = min(slider_width - 1, x + marker_width // 2)
            
            points = [
                QPoint(x, top_y),
                QPoint(left_x, bottom_y),
                QPoint(right_x, bottom_y)
            ]
            
            painter.drawPolygon(points)
            
            # Draw scene number if hovered
            if i == self.hovered_marker:
                painter.setPen(QPen(Qt.GlobalColor.white))
                painter.setBrush(QBrush(Qt.GlobalColor.black))
                text_rect = QRect(x - 15, top_y - 25, 30, 20)
                # Ensure text rect is within bounds
                if text_rect.top() >= 0 and text_rect.bottom() <= slider_height:
                    painter.drawRect(text_rect)
                    painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, str(i + 1))
                
    def mouseMoveEvent(self, event):
        """Handle mouse move to show hover effects"""
        if not self.scene_markers or self.maximum() <= 0:
            super().mouseMoveEvent(event)
            return
            
        # Check if mouse is over a scene marker
        slider_width = self.width()
        max_value = self.maximum()
        mouse_x = event.position().x()
        
        # Safety check for mouse position
        if mouse_x < 0 or mouse_x > slider_width:
            if self.hovered_marker != -1:
                self.hovered_marker = -1
                self.update()
            super().mouseMoveEvent(event)
            return
        
        old_hovered = self.hovered_marker
        self.hovered_marker = -1
        
        for i, frame_pos in enumerate(self.scene_markers):
            # Safety check for frame position
            if frame_pos < 0 or frame_pos > max_value:
                continue
            marker_x = int((frame_pos / max_value) * slider_width)
            if abs(mouse_x - marker_x) <= 10:  # 10 pixel tolerance
                self.hovered_marker = i
                break
                
        if old_hovered != self.hovered_marker:
            self.update()
            
        super().mouseMoveEvent(event)
        
    def mousePressEvent(self, event):
        """Handle mouse press to detect scene marker clicks"""
        if not self.scene_markers or self.maximum() <= 0:
            super().mousePressEvent(event)
            return
            
        # Check if clicking on a scene marker
        slider_width = self.width()
        max_value = self.maximum()
        mouse_x = event.position().x()
        
        # Safety check for mouse position
        if mouse_x < 0 or mouse_x > slider_width:
            super().mousePressEvent(event)
            return
        
        for i, frame_pos in enumerate(self.scene_markers):
            # Safety check for frame position
            if frame_pos < 0 or frame_pos > max_value:
                continue
            marker_x = int((frame_pos / max_value) * slider_width)
            if abs(mouse_x - marker_x) <= 10:  # 10 pixel tolerance
                self.scene_clicked.emit(i)
                return
                
        super().mousePressEvent(event)
        
    def leaveEvent(self, event):
        """Clear hover state when mouse leaves"""
        if self.hovered_marker != -1:
            self.hovered_marker = -1
            self.update()
        super().leaveEvent(event) 