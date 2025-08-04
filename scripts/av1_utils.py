import os
import ffmpeg
import shutil

def is_av1_video(filepath):
    """Return True if the given video file is AV1 video, else False."""
    try:
        probe = ffmpeg.probe(filepath)
        for stream in probe.get('streams', []):
            if stream.get('codec_type') == 'video' and stream.get('codec_name', '').lower() == 'av1':
                return True
    except Exception:
        pass
    return False


def move_av1_videos(folder, subfolder_name="AV1"):
    """Scan the folder for AV1 videos and move them to a subfolder."""
    if not os.path.isdir(folder):
        raise ValueError(f"Not a directory: {folder}")
    av1_dir = os.path.join(folder, subfolder_name)
    os.makedirs(av1_dir, exist_ok=True)
    moved = []
    for entry in os.scandir(folder):
        if entry.is_file() and entry.name.lower().endswith((".mp4", ".mkv", ".avi", ".mov", ".wmv")):
            full_path = entry.path
            if is_av1_video(full_path):
                dest_path = os.path.join(av1_dir, entry.name)
                shutil.move(full_path, dest_path)
                moved.append(entry.name)
    return moved
