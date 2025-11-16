from PyQt6.QtCore import Qt, QMimeData, QUrl
from PyQt6.QtGui import QDrag, QPixmap
import os


class DragDropHelper:
    """Helper class to manage drag and drop operations for video files"""
    
    @staticmethod
    def create_drag_for_file(source_widget, file_path, event_pos=None, pixmap=None):
        """
        Create and execute a drag operation for a file.
        
        Args:
            source_widget: The QWidget initiating the drag
            file_path: Path to the file to drag
            event_pos: The position of the drag start (for hot spot)
            pixmap: Optional pixmap to use as drag image
            
        Returns:
            The result of the drag operation (Qt.DropAction enum)
        """
        if not os.path.exists(file_path):
            return Qt.DropAction.IgnoreAction
            
        # Create drag object
        drag = QDrag(source_widget)
        
        # Create mime data with file URL
        mime_data = QMimeData()
        
        # Add the file URL so external programs can accept it
        file_url = QUrl.fromLocalFile(os.path.abspath(file_path))
        mime_data.setUrls([file_url])
        
        # Also add text fallback for some applications
        mime_data.setText(os.path.abspath(file_path))
        
        drag.setMimeData(mime_data)
        
        # Set drag image (pixmap or default)
        if pixmap:
            drag.setPixmap(pixmap)
        else:
            # Create a simple default drag image
            default_pixmap = QPixmap(100, 100)
            default_pixmap.fill(Qt.GlobalColor.black)
            drag.setPixmap(default_pixmap)
        
        # Set hot spot if position provided
        if event_pos:
            drag.setHotSpot(event_pos)
        
        # Execute drag with copy action (most compatible with external apps)
        result = drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)
        return result
    
    @staticmethod
    def create_drag_for_files(source_widget, file_paths, event_pos=None, pixmap=None):
        """
        Create and execute a drag operation for multiple files.
        
        Args:
            source_widget: The QWidget initiating the drag
            file_paths: List of file paths to drag
            event_pos: The position of the drag start (for hot spot)
            pixmap: Optional pixmap to use as drag image
            
        Returns:
            The result of the drag operation (Qt.DropAction enum)
        """
        if not file_paths:
            return Qt.DropAction.IgnoreAction
        
        # Filter to valid files only
        valid_paths = [p for p in file_paths if os.path.exists(p)]
        
        if not valid_paths:
            return Qt.DropAction.IgnoreAction
        
        # Create drag object
        drag = QDrag(source_widget)
        
        # Create mime data with file URLs
        mime_data = QMimeData()
        
        # Add all file URLs
        file_urls = [QUrl.fromLocalFile(os.path.abspath(p)) for p in valid_paths]
        mime_data.setUrls(file_urls)
        
        # Also add text fallback (newline-separated paths)
        mime_data.setText('\n'.join([os.path.abspath(p) for p in valid_paths]))
        
        drag.setMimeData(mime_data)
        
        # Set drag image
        if pixmap:
            drag.setPixmap(pixmap)
        else:
            # Create a simple default drag image
            default_pixmap = QPixmap(100, 100)
            default_pixmap.fill(Qt.GlobalColor.darkGray)
            drag.setPixmap(default_pixmap)
        
        # Set hot spot if position provided
        if event_pos:
            drag.setHotSpot(event_pos)
        
        # Execute drag with copy action (most compatible with external apps)
        result = drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)
        return result


class DragDropMixin:
    """Mixin class to add drag support to QListWidget or similar widgets"""
    
    def setup_drag_support(self, file_getter_func=None):
        """
        Set up drag support for this widget.
        
        Args:
            file_getter_func: Optional function that takes (item) and returns file path.
                            If not provided, item.text() will be used as filename.
        """
        self.file_getter_func = file_getter_func or (lambda item: item.text())
    
    def start_drag(self, event, item):
        """
        Start a drag operation for an item.
        
        Args:
            event: The QMouseEvent containing position
            item: The item being dragged
        """
        if not hasattr(self, 'file_getter_func'):
            return
        
        file_path = self.file_getter_func(item)
        if file_path:
            # Try to get a preview pixmap from the widget
            pixmap = None
            try:
                pixmap = self.grab(self.visualRect(self.indexFromItem(item)))
            except:
                pass
            
            DragDropHelper.create_drag_for_file(
                self,
                file_path,
                event_pos=event.pos(),
                pixmap=pixmap
            )
