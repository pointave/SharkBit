import os
from datetime import datetime
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap
from PyQt6.QtCore import Qt

def save_video_screenshot(entry, pixmap, crop_regions, original_width, original_height, current_video, folder_path):
    """
    Save a screenshot of the current video frame with optional crop regions.
    
    Args:
        entry (dict): Video metadata dictionary
        pixmap (QPixmap): The pixmap to save
        crop_regions (dict): Dictionary of crop regions
        original_width (int): Original video width
        original_height (int): Original video height
        current_video (str): Current video filename
        folder_path (str): Folder to save the screenshot
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create screenshots directory if it doesn't exist
        screenshots_dir = os.path.join(folder_path, "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(os.path.basename(entry["original_path"]))[0]
        screenshot_path = os.path.join(screenshots_dir, f"{base_name}_{timestamp}.jpg")
        
        # Make a copy of the pixmap to draw on
        screenshot = pixmap.copy()
        
        # Draw crop regions if they exist
        if crop_regions and current_video in crop_regions and crop_regions[current_video]:
            region = crop_regions[current_video]
            painter = QPainter(screenshot)
            pen = QPen(QColor(255, 0, 0), 2)  # Red border
            painter.setPen(pen)
            
            # Calculate scale factors
            scale_x = screenshot.width() / original_width
            scale_y = screenshot.height() / original_height
            
            # Draw the crop region
            x = int(region[0] * scale_x)
            y = int(region[1] * scale_y)
            width = int((region[2] - region[0]) * scale_x)
            height = int((region[3] - region[1]) * scale_y)
            
            painter.drawRect(x, y, width, height)
            painter.end()
        
        # Save the screenshot as JPG with 95% quality
        success = screenshot.save(screenshot_path, "JPG", quality=95)
        return success
        
    except Exception as e:
        print(f"Error saving screenshot: {e}")
        return False
