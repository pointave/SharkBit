import sys
import time
from PyQt6.QtWidgets import QApplication
from scripts.video_cropper import VideoCropper

if __name__ == "__main__":
    start = time.time()
    app = QApplication(sys.argv)
    
    # Load the dark mode stylesheet from a file
    with open("styles/one_dark.css", "r") as file:
        dark_stylesheet = file.read()
    app.setStyleSheet(dark_stylesheet)
    
    try:
        window = VideoCropper()
        window.show()
        print("App created in", time.time() - start, "seconds")
        sys.exit(app.exec())
    except Exception as e:
        print(f"An error occurred: {e}")
        input("Press Enter to exit...")  # Keep the terminal open
        sys.exit(1)