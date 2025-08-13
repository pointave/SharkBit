# video_editor.py
import os
import cv2
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QPen
from PyQt6.QtCore import Qt, QTimer, QRectF
from scripts.interactive_crop_region import InteractiveCropRegion  # New interactive crop region

class VideoEditor:
    def __init__(self, main_app):
        self.main_app = main_app
        from PyQt6.QtCore import QTimer
        self.playback_timer = QTimer()
        self.playback_timer.setSingleShot(False)
        # Use a more precise timer to reduce jitter at higher FPS
        try:
            from PyQt6.QtCore import Qt
            self.playback_timer.setTimerType(Qt.TimerType.PreciseTimer)
        except Exception:
            pass
        self.playback_timer.timeout.connect(self._playback_tick)
        self._playback_mode = None  # 'forward' or 'loop' or None
        # Track last shown frame index to avoid redundant redraws
        self._last_shown_frame = -1
        # Adaptive sync correction tracking
        self._corrections_in_window = 0
        self._window_start_ts = 0.0
        # Cache to avoid heavy scene/layout updates every frame
        self._last_pixmap_size = None

    def _reset_correction_window(self):
        self._corrections_in_window = 0
        self._window_start_ts = 0.0

    def _note_correction(self):
        """Record a drift correction and auto-switch to video-master if too many."""
        try:
            from time import monotonic
            now = monotonic()
            window = 2.0  # seconds
            if self._window_start_ts == 0.0 or (now - self._window_start_ts) > window:
                self._window_start_ts = now
                self._corrections_in_window = 1
            else:
                self._corrections_in_window += 1
            # If too many corrections in window, switch to video-master for this clip
            if self._corrections_in_window >= 6 and getattr(self.main_app, '_audio_master', True):
                self.main_app._audio_master = False
                if hasattr(self.main_app, 'update_status'):
                    self.main_app.update_status('Sync mode: video-master (auto)')
        except Exception:
            pass

    def _stop_timer(self):
        if self.playback_timer.isActive():
            self.playback_timer.stop()
        self._playback_mode = None

    def _playback_tick(self):
        # Called by QTimer: always use correct tick for mode
        if self._playback_mode == 'loop':
            self._loop_playback_tick()
        elif self._playback_mode == 'forward':
            self._play_forward_tick()

    def _play_forward_tick(self):
        if not self.main_app.is_playing or not self.main_app.cap:
            self._stop_timer()
            # Ensure audio pauses when playback stops
            if hasattr(self.main_app, '_pause_audio'):
                self.main_app._pause_audio()
            return
        # If audio is enabled, occasionally correct drift by seeking; otherwise read next frame
        use_audio_clock = (
            getattr(self.main_app, 'audio_enabled', False)
            and getattr(self.main_app, '_audio_master', True)
            and hasattr(self.main_app, 'audio_player')
        )
        if use_audio_clock and getattr(self.main_app, 'video_fps', 0):
            fps = self.main_app.video_fps if self.main_app.video_fps else 30
            audio_ms = self.main_app.audio_player.position()
            target_frame = int(audio_ms * fps / 1000)
            cur_frame = int(self.main_app.cap.get(cv2.CAP_PROP_POS_FRAMES)) if self.main_app.cap else 0
            # If target frame hasn't advanced, skip heavy work this tick
            if target_frame == self._last_shown_frame:
                return
            # Only seek if we are significantly behind/ahead (> 6 frames)
            if abs(target_frame - cur_frame) > 6:
                if target_frame < 0:
                    target_frame = 0
                elif target_frame >= self.main_app.frame_count:
                    target_frame = self.main_app.frame_count - 1
                self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                self._note_correction()
        ret, frame = self.main_app.cap.read()
        current_pos = int(self.main_app.cap.get(cv2.CAP_PROP_POS_FRAMES)) if self.main_app.cap else 0
        if not ret:
            # Read error: treat as end of video
            next_action = True
        else:
            # Display frame and update slider
            self.display_frame(frame)
            self.main_app.slider.setValue(current_pos)
            self._last_shown_frame = current_pos
            # Keep audio in sync with video only when audio is NOT master
            if not getattr(self.main_app, 'audio_enabled', False):
                if hasattr(self.main_app, '_sync_audio_position'):
                    self.main_app._sync_audio_position()
            # Determine if at last frame
            next_action = (current_pos >= self.main_app.frame_count - 1)
        if next_action:
            mode = self.main_app.sort_dropdown.currentText()
            if getattr(self.main_app, 'auto_advance_enabled', False):
                # Advance to next file
                self._stop_timer()
                self.main_app.is_playing = False
                self.main_app.play_next_file()
            else:
                # Loop trimmed region or whole video, even in Random mode
                self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.main_app.slider.setValue(0)
                # Continue playback from start
                # Don't stop timer or set is_playing = False
        return

    def _loop_playback_tick(self):
        # Always loop ONLY the highlighted region: [start, start+trim_length)
        if self.main_app.cap:
            start = self.main_app.trim_points.get(self.main_app.current_video, 0)
            trim_length = self.main_app.trim_length
            end = start + trim_length
            # If audio is enabled, keep audio position within loop window
            if getattr(self.main_app, 'audio_enabled', False) and hasattr(self.main_app, 'audio_player') and getattr(self.main_app, 'video_fps', 0):
                fps = self.main_app.video_fps if self.main_app.video_fps else 30
                start_ms = int(start * 1000 / fps)
                end_ms = int(end * 1000 / fps)
                pos = self.main_app.audio_player.position()
                if pos < start_ms or pos >= end_ms:
                    self.main_app.audio_player.setPosition(start_ms)
            # Determine the frame to show; only seek when drift is large
            target = int(self.main_app.cap.get(cv2.CAP_PROP_POS_FRAMES))
            use_audio_clock = (
                getattr(self.main_app, 'audio_enabled', False)
                and getattr(self.main_app, '_audio_master', True)
                and hasattr(self.main_app, 'audio_player')
            )
            if use_audio_clock and getattr(self.main_app, 'video_fps', 0):
                fps = self.main_app.video_fps if self.main_app.video_fps else 30
                audio_ms = self.main_app.audio_player.position()
                audio_frame = int(audio_ms * fps / 1000)
                # Constrain to loop bounds
                if audio_frame < start or audio_frame >= end:
                    audio_frame = start
                # If target hasn't advanced, skip work this tick
                if audio_frame == self._last_shown_frame:
                    return
                if abs(audio_frame - target) > 6:
                    target = audio_frame
                    self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, target)
                    self._note_correction()
            grabbed = self.main_app.cap.grab()
            if grabbed:
                ret, frame = self.main_app.cap.retrieve()
            else:
                ret, frame = False, None
            if ret:
                self.display_frame(frame)
                frame_after = target
                # If after reading we are out of bounds, reset
                if frame_after < start or frame_after >= end:
                    self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, start)
                    self.main_app.slider.setValue(start)
                # Sync audio to current frame in loop only when audio is NOT master
                if not getattr(self.main_app, 'audio_enabled', False):
                    if hasattr(self.main_app, '_sync_audio_position'):
                        self.main_app._sync_audio_position()
                self._last_shown_frame = frame_after
            else:
                self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, start)
                self.main_app.slider.setValue(start)
        else:
            self._stop_timer()

    def load_video(self, video_entry):
        # Before opening a new video, release any previous handles to avoid file locks (WinError 32)
        try:
            if getattr(self.main_app, 'cap', None) is not None:
                try:
                    self.main_app.cap.release()
                except Exception:
                    pass
                self.main_app.cap = None
            # Detach audio source so OS handle is released
            if hasattr(self.main_app, 'audio_player'):
                try:
                    self.main_app.audio_player.stop()
                    from PyQt6.QtCore import QUrl
                    self.main_app.audio_player.setSource(QUrl())
                except Exception:
                    pass
        except Exception:
            pass
        video_path = video_entry["original_path"]
        self.main_app.cap = cv2.VideoCapture(video_path)
        if not self.main_app.cap.isOpened():
            print("Error: Could not open video file.")
            return
        self.main_app.frame_count = int(self.main_app.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.main_app.original_width = int(self.main_app.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.main_app.original_height = int(self.main_app.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.main_app.clip_aspect_ratio = self.main_app.original_width / self.main_app.original_height
        # Get FPS for correct playback speed
        fps = self.main_app.cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps < 1:
            fps = 30  # fallback default
        self.main_app.video_fps = fps
        # Clamp delay to avoid too slow or too fast playback
        delay = int(1000 / fps)
        # Allow smaller intervals for high-FPS clips; keep a sane upper bound
        delay = max(5, min(delay, 100))  # min 5ms (~200fps), max 100ms (~10fps)
        self.main_app.video_delay = delay
        # Always start at the beginning (frame 0) when loading a video
        self.main_app.trim_points[self.main_app.current_video] = 0
        self.main_app.slider.setMaximum(self.main_app.frame_count - 1)
        self.main_app.slider.setEnabled(True)
        self.main_app.slider.setValue(0)
                # Show both total frames and total seconds
        fps = getattr(self.main_app, 'video_fps', 30)
        total_seconds = self.main_app.frame_count / fps if fps else 0
        # Format large numbers with commas for better readability (e.g., 1,234,567)
        frame_count_str = f"{self.main_app.frame_count:,}"
        self.main_app.clip_length_label.setText(f"{frame_count_str} ({total_seconds:.1f}s)")
        # Update FPS display with just the number
        self.main_app.fps_label.setText(f"{fps:.1f}")
        
        # Update file size
        try:
            file_size = os.path.getsize(video_path) / (1024 * 1024)  # Convert to MB
            self.main_app.file_size_label.setText(f"{file_size:.1f} MB")
        except Exception as e:
            print(f"Error getting file size: {e}")
            self.main_app.file_size_label.setText("N/A")
            
        self.update_trim_label()
        self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = self.main_app.cap.read()
        if ret:
            self.display_frame(frame)
        else:
            # If failed to read first frame, keep UI consistent
            pass
        # Set audio source for single-video audio pipeline
        if hasattr(self.main_app, '_set_audio_source'):
            self.main_app._set_audio_source(video_path)
            # Ensure audio is paused initially and positioned at start
            if hasattr(self.main_app, '_pause_audio'):
                self.main_app._pause_audio()
        # Reset last shown frame tracker
        self._last_shown_frame = -1
        # Reset correction tracking and prefer audio-master initially
        self._reset_correction_window()
        # Check if there is a crop region saved for this video.
        crop = self.main_app.crop_regions.get(self.main_app.current_video)
        if crop:
            # Scale the saved crop region to the displayed image dimensions.
            scale_w = self.main_app.pixmap_item.pixmap().width() / self.main_app.original_width
            scale_h = self.main_app.pixmap_item.pixmap().height() / self.main_app.original_height
            x = crop[0] * scale_w
            y = crop[1] * scale_h
            w = crop[2] * scale_w
            h = crop[3] * scale_h
            self.draw_crop_rectangle(x, y, w, h)
        else:
            # Remove any lingering interactive crop region items from the scene.
            items_to_remove = [item for item in self.main_app.scene.items() 
                               if isinstance(item, InteractiveCropRegion)]
            for item in items_to_remove:
                self.main_app.scene.removeItem(item)
            self.main_app.current_rect = None

        # Auto-play if enabled
        if getattr(self.main_app, 'auto_play_on_change', False):
            self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.main_app.slider.setValue(0)
            self.main_app.is_playing = False
            self.main_app.play_pause_button.setText("Play")
            self.toggle_play_forward()
        else:
            # Ensure playback is paused at trim point
            self.main_app.is_playing = False
            self.main_app.play_pause_button.setText("Play")

    def display_frame(self, frame):
        # Limit visible resolution to 1920x1080 for smoother playback
        max_w, max_h = 1920, 1080
        h, w = frame.shape[:2]
        if w > max_w or h > max_h:
            scale = min(max_w / w, max_h / h)
            new_w, new_h = int(w * scale), int(h * scale)
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        # Scale to current view size, prefer speed to minimize stutter
        target_w = max(1, self.main_app.graphics_view.width() - 20)
        target_h = max(1, self.main_app.graphics_view.height() - 20)
        scaled_pixmap = pixmap.scaled(
            target_w,
            target_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        self.main_app.pixmap_item.setPixmap(scaled_pixmap)
        # Only update scene rect (and avoid fitInView) when size changes to reduce layout work
        if self._last_pixmap_size != scaled_pixmap.size():
            self.main_app.scene.setSceneRect(self.main_app.pixmap_item.boundingRect())
            self._last_pixmap_size = scaled_pixmap.size()
        # --- Update slider to match current frame ---
        if self.main_app.cap:
            current_frame = int(self.main_app.cap.get(cv2.CAP_PROP_POS_FRAMES))
            # Avoid feedback loop if user is scrubbing
            if not self.main_app.slider.isSliderDown():
                self.main_app.slider.setValue(current_frame)
            # Update trim point indicator to show current frame
            if hasattr(self.main_app, 'trim_point_label'):
                                # Show both frame and second count
                fps = getattr(self.main_app, 'video_fps', 30)
                second = current_frame / fps if fps else 0
                                # Show frame, second, and percent
                fps = getattr(self.main_app, 'video_fps', 30)
                total_frames = getattr(self.main_app, 'frame_count', 1)
                second = current_frame / fps if fps else 0
                percent = (current_frame / total_frames * 100) if total_frames else 0
                self.main_app.trim_point_label.setText(f"{current_frame} ({second:.1f}s, {percent:.0f}%)")

    def scrub_video(self, position):
        if self.main_app.cap:
            self.main_app.trim_points[self.main_app.current_video] = int(position)
            self.main_app.trim_modified = True
            self.update_trim_label()
            self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, int(position))
            ret, frame = self.main_app.cap.read()
            if ret:
                self.display_frame(frame)
                # Sync audio to current frame
                if hasattr(self.main_app, '_sync_audio_position'):
                    self.main_app._sync_audio_position()

    def update_trim_label(self):
        val = self.main_app.slider.value()
        # Show frame, second, and percent
        fps = getattr(self.main_app, 'video_fps', 30)
        total_frames = getattr(self.main_app, 'frame_count', 1)
        second = val / fps if fps else 0
        percent = (val / total_frames * 100) if total_frames else 0
        self.main_app.trim_point_label.setText(f"{val} ({second:.1f}s, {percent:.0f}%)")
        self.main_app.trim_points[self.main_app.current_video] = val
        if self.main_app.trim_modified:
            self.main_app.check_current_video_item()
            self.main_app.trim_modified = False

    def start_selection(self, event):
        pos = self.main_app.graphics_view.mapToScene(event.pos())
        self.main_app.start_x = pos.x()
        self.main_app.start_y = pos.y()

    def end_selection(self, event):
        pos = self.main_app.graphics_view.mapToScene(event.pos())
        self.main_app.end_x = pos.x()
        self.main_app.end_y = pos.y()
        if None not in (self.main_app.start_x, self.main_app.start_y, 
                        self.main_app.end_x, self.main_app.end_y):
            x1 = max(0, min(self.main_app.start_x, self.main_app.end_x))
            y1 = max(0, min(self.main_app.start_y, self.main_app.end_y))
            x2 = min(self.main_app.pixmap_item.pixmap().width(), max(self.main_app.start_x, self.main_app.end_x))
            y2 = min(self.main_app.pixmap_item.pixmap().height(), max(self.main_app.start_y, self.main_app.end_y))
            w = max(0, x2 - x1)
            h = max(0, y2 - y1)
            if w < 10 or h < 10:
                print("Crop region is too small.")
                return
            scale_w = self.main_app.original_width / self.main_app.pixmap_item.pixmap().width()
            scale_h = self.main_app.original_height / self.main_app.pixmap_item.pixmap().height()
            self.main_app.crop_regions[self.main_app.current_video] = (
                int(x1 * scale_w), int(y1 * scale_h), int(w * scale_w), int(h * scale_h)
            )
            self.draw_crop_rectangle(x1, y1, w, h)
            self.main_app.check_current_video_item()

    def draw_crop_rectangle(self, x, y, w, h):
        from scripts.interactive_crop_region import InteractiveCropRegion
        # Remove any existing crop region.
        if self.main_app.current_rect:
            self.main_app.scene.removeItem(self.main_app.current_rect)
        # Create a new interactive crop region.
        rect = QRectF(x, y, w, h)
        aspect = self.main_app.scene.aspect_ratio if hasattr(self.main_app.scene, "aspect_ratio") else None
        self.main_app.current_rect = InteractiveCropRegion(rect, aspect_ratio=aspect)
        self.main_app.scene.addItem(self.main_app.current_rect)
        # Set the scene's crop_item pointer to the current region.
        self.main_app.scene.crop_item = self.main_app.current_rect

    def move_trim_to_click_position(self, event):
        if not self.main_app.cap:
            return
        pos = event.position().toPoint()
        slider_width = self.main_app.slider.width()
        frame_pos = int((pos.x() / slider_width) * self.main_app.frame_count)
        frame_pos = max(0, min(frame_pos, self.main_app.frame_count - 1))
        self.main_app.slider.setValue(frame_pos)
        self.main_app.trim_modified = True
        self.update_trim_label()
        self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
        ret, frame = self.main_app.cap.read()
        if ret:
            self.display_frame(frame)
            # Sync audio to current frame
            if hasattr(self.main_app, '_sync_audio_position'):
                self.main_app._sync_audio_position()

    def show_thumbnail(self, event):
        if not self.main_app.cap:
            return
        pos = event.position().toPoint()
        slider_width = self.main_app.slider.width()
        frame_pos = int((pos.x() / slider_width) * self.main_app.frame_count)
        frame_pos = max(0, min(frame_pos, self.main_app.frame_count - 1))
        self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
        ret, frame = self.main_app.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            thumbnail_height = 300
            thumbnail_width = int(thumbnail_height * self.main_app.clip_aspect_ratio)
            self.main_app.thumbnail_label.setFixedSize(thumbnail_width, thumbnail_height)
            self.main_app.thumbnail_image_label.setGeometry(0, 0, thumbnail_width, thumbnail_height)
            scaled_pixmap = pixmap.scaled(thumbnail_width, thumbnail_height, Qt.AspectRatioMode.KeepAspectRatio)
            self.main_app.thumbnail_image_label.setPixmap(scaled_pixmap)
            global_pos = self.main_app.slider.mapToGlobal(event.position().toPoint())
            self.main_app.thumbnail_label.move(global_pos.x() - thumbnail_width // 2, 
                                                 global_pos.y() - thumbnail_height - 10)
            self.main_app.thumbnail_label.show()

    def toggle_loop_playback(self):
        self.main_app.loop_playback = not self.main_app.loop_playback
        if self.main_app.loop_playback:
            # Always reset to start of loop
            start = self.main_app.trim_points.get(self.main_app.current_video, 0)
            self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, start)
            self.main_app.slider.setValue(start)
            self.start_loop_playback()
            end = start + self.main_app.trim_length
            self.main_app.update_status(f'HIGHLIGHT LOOP: {start}-{end}')
        else:
            self.stop_playback()
            self.main_app.update_status('LOOP OFF')

    def start_loop_playback(self):
        # Stop any existing playback timer
        self._stop_timer()
        if self.main_app.cap and self.main_app.loop_playback:
            start = self.main_app.trim_points.get(self.main_app.current_video, 0)
            self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, start)
            self.main_app.slider.setValue(start)
            self._playback_mode = 'loop'
            self.playback_timer.start(self.main_app.video_delay)

    def toggle_play_forward(self):
        self.main_app.is_playing = not self.main_app.is_playing
        # Update button text based on state
        self.main_app.play_pause_button.setText("Pause" if self.main_app.is_playing else "Play")
        if self.main_app.is_playing:
            # Starting playback: clear last-shown marker
            self._last_shown_frame = -1
            # If in Highlight Loop mode, ensure current frame is within loop
            if getattr(self.main_app, 'loop_playback', False):
                start = self.main_app.trim_points.get(self.main_app.current_video, 0)
                trim_length = getattr(self.main_app, 'trim_length', 1)
                end = start + trim_length
                current_frame = int(self.main_app.cap.get(cv2.CAP_PROP_POS_FRAMES)) if self.main_app.cap else start
                if current_frame < start or current_frame >= end:
                    if self.main_app.cap:
                        self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, start)
                    self.main_app.slider.setValue(start)
            self.play_forward()
            # Start audio if needed
            if hasattr(self.main_app, '_play_audio_if_needed'):
                self.main_app._play_audio_if_needed()
        else:
            self.stop_playback()

    def play_forward(self):
        # Start playing video frames forward
        def play_loop():
            if not self.main_app.is_playing or not self.main_app.cap:
                return
            ret, frame = self.main_app.cap.read()
            if ret:
                current_frame = int(self.main_app.cap.get(cv2.CAP_PROP_POS_FRAMES))
                self.display_frame(frame)
                # Check for end of video
                if current_frame >= self.main_app.frame_count:
                    mode = self.main_app.sort_dropdown.currentText()
                    if getattr(self.main_app, 'auto_advance_enabled', False) or mode == "Random":
                        # Auto-advance to next file
                        self.main_app.is_playing = False
                        self.main_app.play_next_file()
                        return
                    else:
                        # Repeat from beginning
                        self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        self.main_app.slider.setValue(0)
                        QTimer.singleShot(self.main_app.video_delay, play_loop)
                        return
                QTimer.singleShot(self.main_app.video_delay, play_loop)
            else:
                # End of video or error: treat Random like auto-advance
                mode = self.main_app.sort_dropdown.currentText()
                if getattr(self.main_app, 'auto_advance_enabled', False) or mode == "Random":
                    self.main_app.is_playing = False
                    self.main_app.play_next_file()
                    return
                else:
                    # Repeat from beginning
                    self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.main_app.slider.setValue(0)
                    QTimer.singleShot(self.main_app.video_delay, play_loop)
                    return
        play_loop()

    def play_forward(self):
        # Stop any existing playback timer
        self._stop_timer()
        if self.main_app.is_playing and self.main_app.cap:
            self._playback_mode = 'forward'
            self.playback_timer.start(self.main_app.video_delay)
            # Ensure audio starts if enabled
            if hasattr(self.main_app, '_play_audio_if_needed'):
                self.main_app._play_audio_if_needed()

    def stop_playback(self):
        self._stop_timer()
        self.main_app.is_playing = False
        self.main_app.loop_playback = False
        # Do not seek to trim point or any frame when pausing; just stop playback.
        # Pause audio as well
        if hasattr(self.main_app, '_pause_audio'):
            self.main_app._pause_audio()
        # Reset last shown frame tracker
        self._last_shown_frame = -1
        self._reset_correction_window()

    def next_clip(self):
        # Stop playback before switching video
        self.stop_playback()
        current_idx = self.main_app.video_list.currentRow()
        new_idx = min(len(self.main_app.video_files) - 1, current_idx + 1)
        self.main_app.video_list.setCurrentRow(new_idx)
        # Do NOT call loader.load_video here; let on_video_selected handle it.

    def prev_clip(self):
        # Stop playback before switching video
        self.stop_playback()
        current_idx = self.main_app.video_list.currentRow()
        new_idx = max(0, current_idx - 1)
        self.main_app.video_list.setCurrentRow(new_idx)
        # Do NOT call loader.load_video here; let on_video_selected handle it.

    def move_trim(self, step):
        # Always clamp to valid frame range
        current_val = self.main_app.slider.value()
        new_val = current_val + step
        if new_val < 0:
            new_val = 0
        elif new_val > self.main_app.slider.maximum():
            new_val = self.main_app.slider.maximum()
        if new_val == current_val:
            return  # No change
        self.main_app.slider.setValue(new_val)
        self.update_trim_label()
        if self.main_app.cap:
            # Set to new_val, grab/retrieve frame, and always set slider to new_val
            self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, new_val)
            grabbed = self.main_app.cap.grab()
            if grabbed:
                ret, frame = self.main_app.cap.retrieve()
                if ret:
                    self.display_frame(frame)
            # Always set slider and label to new_val (not OpenCV's pointer)
            if self.main_app.slider.value() != new_val:
                self.main_app.slider.setValue(new_val)
                self.update_trim_label()


    def navigate_clip(self, direction):
        # Placeholder for additional navigation between clips if needed
        pass
