import sys
import os
import time
from PyQt6.QtWidgets import QApplication
from scripts.video_cropper import VideoCropper

# Set high DPI environment variables before creating QApplication
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

# Create the application
app = QApplication(sys.argv)

if __name__ == "__main__":
    start = time.time()
    
    # Load the retro arcade stylesheet from a file
    with open("styles/minimal/pure_dark.css", "r") as file:
        retro_stylesheet = file.read()
    app.setStyleSheet(retro_stylesheet)
    
    try:
        window = VideoCropper()
        window.show()
        print("App created in", time.time() - start, "seconds")
        sys.exit(app.exec())
    except Exception as e:
        print(f"An error occurred: {e}")
        input("Press Enter to exit...")  # Keep the terminal open
        sys.exit(1)