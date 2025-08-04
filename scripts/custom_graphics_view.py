from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtGui import QMouseEvent, QWheelEvent
from PyQt6.QtCore import Qt
import cv2

class CustomGraphicsView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event: QMouseEvent):
        grabbed = self.scene().mouseGrabberItem()
        if grabbed:
            # Map the view's mouse position to scene coordinates.
            scene_pos = self.mapToScene(event.pos())
            # Then map the scene position to the grabbed item's local coordinates.
            local_pos = grabbed.mapFromScene(scene_pos)
            # Create a new fake QMouseEvent with the local coordinates.
            fake_event = QMouseEvent(
                event.type(),
                local_pos,
                event.globalPosition(),
                event.button(),
                event.buttons(),
                event.modifiers()
            )
            grabbed.mouseMoveEvent(fake_event)
            event.accept()
        else:
            super().mouseMoveEvent(event)
            
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel events for scene navigation and video seeking"""
        # Check if we have scenes and the main app has scene navigation capability
        if hasattr(self.scene(), 'parent_widget') and hasattr(self.scene().parent_widget, 'current_scenes') and self.scene().parent_widget.current_scenes:
            # Get current scene index
            current_frame = self.scene().parent_widget.slider.value()
            current_scene_index = None
            
            # Find which scene we're currently in
            for i, (start, end) in enumerate(self.scene().parent_widget.current_scenes):
                if start <= current_frame < end:
                    current_scene_index = i
                    break
                    
            if current_scene_index is not None:
                # Determine scroll direction
                delta = event.angleDelta().y()
                if delta > 0:  # Scroll up - go to previous scene
                    if current_scene_index > 0:
                        new_scene_index = current_scene_index - 1
                        start_frame = self.scene().parent_widget.current_scenes[new_scene_index][0]
                        self.scene().parent_widget.slider.setValue(start_frame)
                        self.scene().parent_widget.editor.scrub_video(start_frame)
                        self.scene().parent_widget.status_label.setText(f"Mouse wheel: Scene {new_scene_index + 1}")
                elif delta < 0:  # Scroll down - go to next scene
                    if current_scene_index < len(self.scene().parent_widget.current_scenes) - 1:
                        new_scene_index = current_scene_index + 1
                        start_frame = self.scene().parent_widget.current_scenes[new_scene_index][0]
                        self.scene().parent_widget.slider.setValue(start_frame)
                        self.scene().parent_widget.editor.scrub_video(start_frame)
                        self.scene().parent_widget.status_label.setText(f"Mouse wheel: Scene {new_scene_index + 1}")
                        
                event.accept()
                return
        
        # If no scenes or not in a scene, handle video seeking like F/D keys
        if hasattr(self.scene(), 'parent_widget'):
            main_app = self.scene().parent_widget
            modifiers = event.modifiers()
            delta = event.angleDelta().y()
            
            # Determine seek direction and amount based on modifiers
            if delta > 0:  # Scroll up - seek backward (like D key)
                if modifiers == Qt.KeyboardModifier.ShiftModifier:
                    # Shift + wheel up = seek backward by trim_length * 4 (like Shift+D)
                    seek_amount = -main_app.trim_length * 4
                    seek_type = "Shift+Wheel"
                elif modifiers == Qt.KeyboardModifier.ControlModifier:
                    # Ctrl + wheel up = seek backward by trim_length * 2 (like Ctrl+D)
                    seek_amount = -main_app.trim_length * 2
                    seek_type = "Ctrl+Wheel"
                else:
                    # Plain wheel up = seek backward by trim_length (like D)
                    seek_amount = -main_app.trim_length
                    seek_type = "Wheel"
            else:  # Scroll down - seek forward (like F key)
                if modifiers == Qt.KeyboardModifier.ShiftModifier:
                    # Shift + wheel down = seek forward by trim_length * 4 (like Shift+F)
                    seek_amount = main_app.trim_length * 4
                    seek_type = "Shift+Wheel"
                elif modifiers == Qt.KeyboardModifier.ControlModifier:
                    # Ctrl + wheel down = seek forward by trim_length * 2 (like Ctrl+F)
                    seek_amount = main_app.trim_length * 2
                    seek_type = "Ctrl+Wheel"
                else:
                    # Plain wheel down = seek forward by trim_length (like F)
                    seek_amount = main_app.trim_length
                    seek_type = "Wheel"
            
            # Apply seeking logic similar to F/D key handling
            if main_app.loop_playback:
                # In loop mode, move the loop start point
                old_start = main_app.trim_points.get(main_app.current_video, main_app.slider.value())
                max_start = max(0, main_app.frame_count - main_app.trim_length)
                new_start = max(0, min(old_start + seek_amount, max_start))
                main_app.trim_points[main_app.current_video] = new_start
                main_app.slider.setValue(new_start)
                if main_app.cap:
                    main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, new_start)
                main_app.editor._stop_timer()
                main_app.editor._playback_mode = 'loop'
                main_app.editor.playback_timer.start(main_app.video_delay)
                main_app.update_status(f'HIGHLIGHT LOOP: {new_start}-{new_start + main_app.trim_length} ({seek_type})')
            else:
                # In normal mode, move current frame
                current_frame = main_app.slider.value() if hasattr(main_app, 'slider') else 0
                max_start = max(0, main_app.frame_count - main_app.trim_length)
                new_start = max(0, min(current_frame + seek_amount, max_start))
                main_app.trim_points[main_app.current_video] = new_start
                main_app.slider.setValue(new_start)
                if main_app.cap:
                    main_app.cap.set(cv2.CAP_PROP_POS_FRAMES, new_start)
                main_app.update_status(f'HIGHLIGHT ADJUST: {new_start} ({seek_type})')
            
            event.accept()
            return
                
        # If no scenes or not in a scene, let the default wheel behavior happen
        super().wheelEvent(event)
