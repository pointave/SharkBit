Easily cycle through videos and utilizes these shortcuts

Q =   Close program
W =   Open current folder
E R = Previous and Next file in list
T =   Fullscreen
Y =   Pull-out Window
A S = Down and up one frame
D F = Will jump 113 frames by default. (Can be modified with shift or ctrl to doube or quadruple frame jumping)  
G =   Random
H =   Remove crop selection
Z =   Toggle trim preview
X =   Auto-advance toggle
C =   Screenshot
V =   Play/Pause
B =   Save clip  (either cropped or uncropped)
/ =   Search
Backspace = Minimize

To have more videos playing at once you need to ctrl+click on two or more videos in the filelist.

![Screenshot 2025-07-04 115641](https://github.com/user-attachments/assets/07fc67da-8e1d-4623-9879-4fc1a0ced63a)

Installation

git clone https://github.com/pointave/SharkBit
cd sharkbit
conda create -n sharkbit python=3.12 -y
conda activate sharkbit
pip install -r requirements.txt
optionally add yt-dlp.exe to sharkbit folder

It will open to your Videos folder, but you can change default location by going to scripts/video_cropper.py    line 216  by uncommenting and commenting the line beneath it.

Credits
PyQt
Yt-DLP
