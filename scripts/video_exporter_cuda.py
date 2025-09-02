from PyQt6.QtCore import QProcess
import os, ffmpeg, cv2, subprocess
from PyQt6.QtWidgets import QMessageBox

class VideoExporter:
    def __init__(self, main_app):
        self.main_app = main_app
        self.file_counter = 0  # Counter for incremental padding suffix
        self.cancel_requested = False
        self.has_nvidia_gpu = self._check_nvidia_gpu()
        
    def _check_nvidia_gpu(self):
        """Check if NVIDIA GPU is available for hardware acceleration."""
        try:
            # Check for NVIDIA GPU using nvidia-smi
            result = subprocess.run(['nvidia-smi'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE, 
                                 text=True)
            return result.returncode == 0 and 'NVIDIA' in result.stdout
        except (FileNotFoundError, Exception):
            return False

    def cancel_export(self):
        self.cancel_requested = True
        print("Export cancelled by user.")

    def get_unique_filename(self, file_path):
        base, ext = os.path.splitext(file_path)
        counter = 1
        unique_file = file_path
        while os.path.exists(unique_file):
            unique_file = f"{base}_{counter}{ext}"
            counter += 1
        return unique_file

    def write_caption(self, output_file):
        """
        If a simple caption was provided, write it into a .txt file with the same base name as output_file.
        """
        caption = getattr(self.main_app, 'simple_caption', '').strip()
        if caption:
            base, _ = os.path.splitext(output_file)
            txt_file = base + ".txt"
            with open(txt_file, "w") as f:
                f.write(caption)
            print(f"Exported caption for {output_file} to {txt_file}")

    def run_ffmpeg_async(self, cmd_list):
        self.main_app.update_status("Encoding video...")
        # Add fast seeking before input
        if cmd_list[0] == "ffmpeg" and "-i" in cmd_list:
            input_idx = cmd_list.index("-i")
            try:
                ss_idx = cmd_list.index("-ss")
                seek_time = float(cmd_list[ss_idx + 1])
                # Move the -ss parameter before input for faster seeking
                cmd_list.pop(ss_idx + 1)
                cmd_list.pop(ss_idx)
                cmd_list[input_idx:input_idx] = [
                    "-ss", str(seek_time),
                    "-noaccurate_seek"
                ]
            except (ValueError, IndexError):
                print("Warning: Could not find -ss parameter in command")
        
        print("Running FFmpeg command:", cmd_list)
        
        try:
            # Use subprocess.Popen instead of QProcess for better reliability
            process = subprocess.Popen(
                cmd_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW  # Prevents console window from appearing on Windows
            )
            
            # Start a thread to monitor the process
            import threading
            def monitor_process():
                stdout, stderr = process.communicate()
                if process.returncode == 0:
                    self.ffmpeg_finished(0, 0)
                else:
                    print(f"FFmpeg error: {stderr}")
                    self.ffmpeg_finished(process.returncode, 0)
            
            thread = threading.Thread(target=monitor_process, daemon=True)
            thread.start()
            
            self.main_app.update_status("FFmpeg process started in background")
            
        except Exception as e:
            print(f"Error starting FFmpeg process: {str(e)}")
            self.main_app.update_status(f"Error starting FFmpeg: {str(e)}")
            if hasattr(self.main_app, 'export_finished_callback'):
                self.main_app.export_finished_callback()

    def ffmpeg_finished(self, exitCode, exitStatus):
        if exitCode == 0:
            self.main_app.update_status("Export completed successfully")
            # Clean up uncropped file if it was only used as a temporary source
            if hasattr(self, 'temp_uncropped_path'):
                try:
                    import time
                    time.sleep(1)  # Small delay to ensure file is not in use
                    if os.path.exists(self.temp_uncropped_path):
                        os.remove(self.temp_uncropped_path)
                        print(f"Cleaned up temporary uncropped file: {self.temp_uncropped_path}")
                    delattr(self, 'temp_uncropped_path')  # Clean up the reference
                except Exception as e:
                    print(f"Could not remove temporary file {self.temp_uncropped_path}: {str(e)}")
        else:
            self.main_app.update_status(f"Export failed with code {exitCode}")
        self.ffmpeg_process = None
        if hasattr(self.main_app, 'export_finished_callback'):
            self.main_app.export_finished_callback()

    def export_videos(self):
        if not self.main_app.current_video:
            if hasattr(self.main_app, 'export_finished_callback'):
                self.main_app.export_finished_callback()
            return

        self.main_app.update_status("Preparing to export...")
        # Clear any previous cancel request.
        self.cancel_requested = False

        output_folder = os.path.join(self.main_app.folder_path, "cropped")
        os.makedirs(output_folder, exist_ok=True)
        uncropped_folder = os.path.join(self.main_app.folder_path, "uncropped")
        os.makedirs(uncropped_folder, exist_ok=True)
        
        # Reset file counter for each export session
        self.file_counter = 0

        # Only process the current video.
        current_video = self.main_app.current_video
        if not current_video:
            if self.main_app.video_files:
                current_video = self.main_app.video_files[0]["display_name"]
                self.main_app.current_video = current_video
                print("No current video selected; defaulting to first video:", current_video)
            else:
                print("No videos available.")
                if hasattr(self.main_app, 'export_finished_callback'):
                    self.main_app.export_finished_callback()
                return

        entry = next((e for e in self.main_app.video_files if e["display_name"] == current_video), None)
        if not entry:
            print(f"Current video entry {current_video} not found.")
            if hasattr(self.main_app, 'export_finished_callback'):
                self.main_app.export_finished_callback()
            return

        video_path = entry["original_path"]
        display_name = entry["display_name"]
        crop = self.main_app.crop_regions.get(display_name)
        prefix = getattr(self.main_app, 'export_prefix', '').strip()

        # Use the export_enabled flag from the entry.
        if not entry.get("export_enabled", False):
            if hasattr(self.main_app, 'export_finished_callback'):
                self.main_app.export_finished_callback()
            return

        cap = cv2.VideoCapture(video_path)
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        trim_start = self.main_app.trim_points.get(display_name, 0)
        duration = self.main_app.trim_length / fps

        if self.main_app.export_image_checkbox.isChecked():
            cap.set(cv2.CAP_PROP_POS_FRAMES, trim_start)
            ret, frame = cap.read()
            if ret:
                base_name = os.path.splitext(display_name)[0]
                # If neither export cropped nor uncropped are separately checked, export both.
                # Always export both cropped and uncropped images
                # Export cropped image if a valid crop exists.
                if crop:
                    x, y, w, h = crop
                    if x >= 0 and y >= 0 and w > 0 and h > 0 and (x + w) <= orig_w and (y + h) <= orig_h:
                        cropped_frame = frame[y:y+h, x:x+w]
                        if cropped_frame.size != 0:
                            if prefix:
                                self.file_counter += 1
                                cropped_image_name = f"{prefix}_{self.file_counter:05d}_cropped.png"
                            else:
                                cropped_image_name = f"{base_name}_cropped.png"
                            cropped_image_path = os.path.join(output_folder, cropped_image_name)
                            cropped_image_path = self.get_unique_filename(cropped_image_path)
                            cv2.imwrite(cropped_image_path, cropped_frame)
                            print(f"Exported cropped image for {display_name} to {cropped_image_path}")
                            self.write_caption(cropped_image_path)
                            if self.cancel_requested:
                                cap.release()
                                if hasattr(self.main_app, 'export_finished_callback'):
                                    self.main_app.export_finished_callback()
                                return
                # Always export the uncropped image
                if prefix:
                    self.file_counter += 1
                    uncropped_image_name = f"{prefix}_{self.file_counter:05d}.png"
                else:
                    uncropped_image_name = f"{base_name}.png"
                uncropped_image_path = os.path.join(uncropped_folder, uncropped_image_name)
                uncropped_image_path = self.get_unique_filename(uncropped_image_path)
                cv2.imwrite(uncropped_image_path, frame)
                print(f"Exported uncropped image for {display_name} to {uncropped_image_path}")
                self.write_caption(uncropped_image_path)
                if self.cancel_requested:
                    cap.release()
                    if hasattr(self.main_app, 'export_finished_callback'):
                        self.main_app.export_finished_callback()
                    return


        # First export uncropped version regardless of checkbox
        base_name, ext = os.path.splitext(display_name)
        if prefix:
            self.file_counter += 1
            uncropped_name = f"{prefix}_{self.file_counter:05d}{ext}"
        else:
            uncropped_name = f"{base_name}{ext}"
        
        uncropped_path = os.path.join(uncropped_folder, uncropped_name)
        uncropped_path = self.get_unique_filename(uncropped_path)
        seek_time = trim_start / fps
        
        # Export trimmed uncropped version first with HEVC if GPU is available
        if self.has_nvidia_gpu:
            # Use GPU-accelerated HEVC encoding
            (
                ffmpeg.input(video_path, ss=seek_time)
                .output(uncropped_path,
                        vf=f'trim=start_frame=0:end_frame={self.main_app.trim_length},setpts=PTS-STARTPTS',
                        vcodec='hevc_nvenc',  # NVIDIA HEVC encoder
                        preset='slow',
                        cq=23,  # Constant Quality mode (18-28 is a good range)
                        pix_fmt='yuv420p',
                        af='aresample=async=1',
                        t=duration,
                        map_metadata='-1')
                .overwrite_output()
                .run(quiet=True)
            )
        else:
            # Fall back to software encoding
            (
                ffmpeg.input(video_path, ss=seek_time)
                .output(uncropped_path,
                        vf=f'trim=start_frame=0:end_frame={self.main_app.trim_length},setpts=PTS-STARTPTS',
                        vcodec='libx265',  # Software HEVC encoder
                        preset='medium',
                        crf=23,  # Constant Rate Factor (lower = better quality, 18-28 is a good range)
                        pix_fmt='yuv420p',
                        af='aresample=async=1',
                        t=duration,
                        map_metadata='-1')
                .overwrite_output()
                .run(quiet=True)
            )
        
        # Store the uncropped path when creating it
        self.temp_uncropped_path = uncropped_path

        # Only save uncropped if checkbox is checked
        if True:
            print(f"Exported uncropped {display_name} to {uncropped_path}")
            self.write_caption(uncropped_path)
        
        # Now handle cropped version using the uncropped as source
        if crop:
            x, y, w, h = crop
            x = max(0, x)
            y = max(0, y)
            w = min(w, orig_w - x)
            h = min(h, orig_h - y)
            
            if w > 0 and h > 0:
                # Ensure width and height are even for encoding
                if self.main_app.longest_edge % 2 != 0:
                    self.main_app.longest_edge -= 1
                if h % 2 != 0:
                    h -= 1
                if w % 2 != 0:
                    w -= 1

                if prefix:
                    self.file_counter += 1
                    output_name = f"{prefix}_{self.file_counter:05d}_cropped{ext}"
                else:
                    output_name = f"{base_name}_cropped{ext}"

                output_path = os.path.join(output_folder, output_name)
                output_path = self.get_unique_filename(output_path)

                # Use the trimmed uncropped version as source with GPU acceleration if available
                if self.has_nvidia_gpu:
                    cmd = [
                        "ffmpeg",
                        "-y",  # Overwrite output files without asking
                        "-hwaccel", "cuda",
                        "-hwaccel_output_format", "cuda",
                        "-i", uncropped_path,
                        "-vf", f"crop={w}:{h}:{x}:{y},scale={self.main_app.longest_edge}:-2:format=yuv420p,hwupload_cuda",
                        "-c:v", "hevc_nvenc",  # NVIDIA HEVC encoder
                        "-preset", "slow",
                        "-cq", "23",  # Constant Quality mode
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-map", "0:v:0",
                        "-map", "0:a?",
                        "-map_metadata", "-1",
                        "-movflags", "+faststart",  # For web streaming
                        "-f", "mp4",  # Force output format
                        output_path
                    ]
                else:
                    # Fall back to software encoding
                    cmd = [
                        "ffmpeg",
                        "-y",  # Overwrite output files without asking
                        "-i", uncropped_path,
                        "-vf", f"crop={w}:{h}:{x}:{y},scale={self.main_app.longest_edge}:-2:format=yuv420p",
                        "-c:v", "libx265",  # Software HEVC encoder
                        "-preset", "medium",
                        "-crf", "23",  # Constant Rate Factor
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-map", "0:v:0",
                        "-map", "0:a?",
                        "-map_metadata", "-1",
                        "-movflags", "+faststart",  # For web streaming
                        "-f", "mp4",  # Force output format
                        output_path
                    ]
                self.run_ffmpeg_async(cmd)
                print(f"Exported cropped {display_name} to {output_path}")
                self.write_caption(output_path)
    # Use the trimmed uncropped version as source with GPU-accelerated H.265/HEVC encoding
                cmd = [
                    "ffmpeg",
                    "-hwaccel", "cuda",  # Enable CUDA hardware acceleration
                    "-hwaccel_output_format", "cuda",  # Keep frames in GPU memory
                    "-i", uncropped_path,
                    "-vf", f"crop={w}:{h}:{x}:{y},scale={self.main_app.longest_edge}:-2:format=yuv420p,hwupload_cuda",  # Process on GPU
                    "-c:v", "hevc_nvenc",  # Use NVIDIA's HEVC encoder
                    "-preset", "p7",  # P7 is the highest quality preset for NVENC
                    "-tune", "hq",  # High quality tuning
                    "-b:v", "15M",  # Bitrate (adjust as needed)
                    "-bufsize", "30M",  # Buffer size
                    "-maxrate", "20M",  # Maximum bitrate
                    "-c:a", "aac",  # Use AAC audio codec
                    "-b:a", "192k",  # Audio bitrate
                    "-map", "0:v:0",  # Map first video stream
                    "-map", "0:a?",  # Map audio if present
                    "-map_metadata", "-1",
                    "-y",  # Overwrite output file if it exists
                    output_path
                ]
                self.run_ffmpeg_async(cmd)
                print(f"Exported cropped {display_name} to {output_path}")
                self.write_caption(output_path)

                self.run_ffmpeg_async(cmd)
                print(f"Exported cropped {display_name} to {output_path}")
                self.write_caption(output_path)
