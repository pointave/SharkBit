# video_editor.py
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
        self.playback_timer.timeout.connect(self._playback_tick)
        self._playback_mode = None  # 'forward' or 'loop' or None

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
            return
        ret, frame = self.main_app.cap.read()
        if not ret:
            # Read error: treat as end of video
            next_action = True
        else:
            # Display frame and update slider
            self.display_frame(frame)
            current_pos = int(self.main_app.cap.get(cv2.CAP_PROP_POS_FRAMES))
            self.main_app.slider.setValue(current_pos)
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
            current_frame = int(self.main_app.cap.get(cv2.CAP_PROP_POS_FRAMES))
            if current_frame < start or current_frame >= end:
                self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, start)
                self.main_app.slider.setValue(start)
                current_frame = start
            ret, frame = self.main_app.cap.read()
            if ret:
                self.display_frame(frame)
                frame_after = int(self.main_app.cap.get(cv2.CAP_PROP_POS_FRAMES))
                # If after reading we are out of bounds, reset
                if frame_after < start or frame_after >= end:
                    self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, start)
                    self.main_app.slider.setValue(start)
            else:
                self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, start)
                self.main_app.slider.setValue(start)
        else:
            self._stop_timer()

    def load_video(self, video_entry):
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
        delay = max(15, min(delay, 100))  # min 15ms (max ~66fps), max 100ms (min ~10fps)
        self.main_app.video_delay = delay
        # Always start at the beginning (frame 0) when loading a video
        self.main_app.trim_points[self.main_app.current_video] = 0
        self.main_app.slider.setMaximum(self.main_app.frame_count - 1)
        self.main_app.slider.setEnabled(True)
        self.main_app.slider.setValue(0)
                # Show both total frames and total seconds
        fps = getattr(self.main_app, 'video_fps', 30)
        total_seconds = self.main_app.frame_count / fps if fps else 0
        self.main_app.clip_length_label.setText(f"Clip Length: {self.main_app.frame_count} ({total_seconds:.2f}s)")
        self.update_trim_label()
        self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = self.main_app.cap.read()
        if ret:
            self.display_frame(frame)
        else:
            print("Error: Could not read first frame.")

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
        scaled_pixmap = pixmap.scaled(
            self.main_app.graphics_view.width() - 20,
            self.main_app.graphics_view.height() - 20,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.main_app.pixmap_item.setPixmap(scaled_pixmap)
        self.main_app.graphics_view.fitInView(self.main_app.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        # Set the scene boundaries to match the pixmap's bounding rectangle.
        self.main_app.scene.setSceneRect(self.main_app.pixmap_item.boundingRect())
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
                self.main_app.trim_point_label.setText(f"Current Frame: {current_frame} ({second:.2f}s, {percent:.1f}%)")

    def scrub_video(self, position):
        if self.main_app.cap:
            self.main_app.trim_points[self.main_app.current_video] = int(position)
            self.main_app.trim_modified = True
            self.update_trim_label()
            self.main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, int(position))
            ret, frame = self.main_app.cap.read()
            if ret:
                self.display_frame(frame)

    def update_trim_label(self):
        val = self.main_app.slider.value()
                # Show both frame and second count
        fps = getattr(self.main_app, 'video_fps', 30)
        second = val / fps if fps else 0
                # Show frame, second, and percent
        fps = getattr(self.main_app, 'video_fps', 30)
        total_frames = getattr(self.main_app, 'frame_count', 1)
        second = val / fps if fps else 0
        percent = (val / total_frames * 100) if total_frames else 0
        self.main_app.trim_point_label.setText(f"Trim Point: {val} ({second:.2f}s, {percent:.1f}%)")
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


    def stop_playback(self):
        self._stop_timer()
        self.main_app.is_playing = False
        self.main_app.loop_playback = False
        # Do not seek to trim point or any frame when pausing; just stop playback.

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
