from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QSizePolicy, QMessageBox
from PyQt6.QtGui import QClipboard
import os
import cv2

def keyPressEvent(self, event):
        # Q quits the app, but not when Ctrl is pressed (for scene navigation)
        if event.key() == Qt.Key.Key_Q and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            QApplication.quit()
            return
        # --- Minimize window on Backspace ---
        elif event.key() == Qt.Key.Key_Backspace:
            # If in preview mode and preview window exists, minimize it
            if hasattr(self, '_preview_mode') and self._preview_mode and hasattr(self, '_preview_window'):
                self._preview_window.showMinimized()
            else:
                self.showMinimized()
            return
        # --- Trigger clear crop on H key ---
        elif event.key() == Qt.Key.Key_H and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            self.loader.clear_crop_region()
            self.update_status("Crop cleared")
            return
        # --- Trigger refresh on \ key ---
        elif event.key() == Qt.Key.Key_Backslash:
            if hasattr(self, 'loader'):
                self.loader.load_folder_contents()
                self.update_status("Folder refreshed")
            return
        # --- Cycle themes on T key ---
        elif event.key() == Qt.Key.Key_T and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            if hasattr(self, 'cycle_theme'):
                self.cycle_theme()
            return
        # --- Open theme selector on Ctrl+T ---
        elif event.key() == Qt.Key.Key_T and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if hasattr(self, 'open_theme_selector'):
                self.open_theme_selector()
            return
        # --- Undo delete with Ctrl+Z ---
        elif event.key() == Qt.Key.Key_Z and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if hasattr(self, 'undo_delete_video'):
                self.undo_delete_video()
                self.update_status("Undo: Restored last deleted video")
            return
            
        # --- Toggle mute with CAPSLOCK or ] key ---
        elif event.key() in [Qt.Key.Key_CapsLock, Qt.Key.Key_BracketRight] and not event.isAutoRepeat():
            if hasattr(self, 'audio_output'):
                current_volume = self.audio_output.volume()
                if current_volume > 0:
                    self.audio_output.setMuted(not self.audio_output.isMuted())
                    self.update_status(f"Audio {'muted' if self.audio_output.isMuted() else 'unmuted'}")
                else:
                    # If volume is 0, unmute and set to 50%
                    self.audio_output.setVolume(0.5)
                    self.audio_output.setMuted(False)
                    self.update_status("Audio unmuted (50% volume)")
            return
            
        # --- Copy filepath with Ctrl+Shift+C ---
        elif event.key() == Qt.Key.Key_C and event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
            if hasattr(self, 'video_list') and hasattr(self, 'video_files'):
                selected_item = self.video_list.currentItem()
                if selected_item:
                    video_name = selected_item.text()
                    # Find the matching entry in video_files based on display name
                    entry = next((e for e in self.video_files if e["display_name"] == video_name), None)
                    if entry and "original_path" in entry:
                        clipboard = QApplication.clipboard()
                        clipboard.setText(entry["original_path"])
                        self.update_status(f"Copied to clipboard: {os.path.basename(entry['original_path'])}")
                        return
                
        # --- Video swapping shortcuts (only in multi-mode) ---
        elif self.multi_mode and hasattr(self, 'multi_video_widgets'):
            # Ctrl+S to enter swap mode
            if event.key() == Qt.Key.Key_S and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                if not getattr(self, 'swap_mode', False):
                    self.swap_mode = True
                    self.swap_source = self.multi_focused_grid
                    self.update_status(f"Swap mode: Select target for Grid {self.multi_focused_grid + 1} (press number key 1-{len(self.multi_video_widgets)})")
                else:
                    self.swap_mode = False
                    self.swap_source = None
                    self.update_status("Swap mode cancelled")
                return
            # Number keys 1-9 to select target for swap
            elif getattr(self, 'swap_mode', False) and event.key() in [Qt.Key.Key_1, Qt.Key.Key_2, Qt.Key.Key_3, Qt.Key.Key_4, Qt.Key.Key_5, Qt.Key.Key_6, Qt.Key.Key_7, Qt.Key.Key_8, Qt.Key.Key_9]:
                target_index = event.key() - Qt.Key.Key_1  # Convert key to 0-based index
                if target_index < len(self.multi_video_widgets) and target_index != self.swap_source:
                    print(f"DEBUG: Keyboard swap from {self.swap_source} to {target_index}")
                    if hasattr(self, '_on_video_drag_drop'):
                        self._on_video_drag_drop(self.swap_source, target_index)
                    self.update_status(f"Swapped Grid {self.swap_source + 1} ↔ Grid {target_index + 1}")
                else:
                    self.update_status("Invalid swap target")
                self.swap_mode = False
                self.swap_source = None
                return
        # --- Multi-Video Preview Mode Toggle (Shift+Y) - MUST BE BEFORE REGULAR Y ---
        if event.key() == Qt.Key.Key_Y and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            print(f"DEBUG: Shift+Y pressed - key: {event.key()}, modifiers: {event.modifiers()}")
            print(f"DEBUG: multi_mode: {getattr(self, 'multi_mode', 'NOT SET')}")
            print(f"DEBUG: multi_grid_widget exists: {hasattr(self, 'multi_grid_widget')}")
            print(f"DEBUG: multi_video_widgets exists: {hasattr(self, 'multi_video_widgets')}")
            # Check if we're in multi-mode and have the required widgets
            if not hasattr(self, 'multi_mode') or not self.multi_mode:
                QMessageBox.information(self, "Multi-Video Preview", "Please select multiple videos first (Ctrl+click) to use Shift+Y preview mode.")
                return
                
            if not hasattr(self, 'multi_grid_widget') or not hasattr(self, 'multi_video_widgets'):
                QMessageBox.information(self, "Multi-Video Preview", "Multi-video mode not properly initialized. Please select multiple videos again.")
                return
                
            if not hasattr(self, '_preview_mode'):
                self._preview_mode = False
            self._preview_mode = not self._preview_mode
            if self._preview_mode:
                try:
                    # Hide main window
                    self._prev_geometry = self.geometry()
                    self._prev_window_state = self.windowState()
                    self.hide()
                    # Create preview window sized to grid
                    self._preview_window = QWidget()
                    self._preview_window.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
                    self._preview_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
                    layout = QVBoxLayout(self._preview_window)
                    layout.setContentsMargins(0,0,0,0)
                    layout.setSpacing(0)
                    self.multi_grid_widget.setParent(self._preview_window)
                    layout.addWidget(self.multi_grid_widget)
                    # --- Set Expanding policy for grid and cells in preview ---
                    self.multi_grid_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                    for cell in self.multi_video_widgets:
                        if hasattr(cell, 'setSizePolicy'):
                            cell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                        if hasattr(cell, 'video_widget') and hasattr(cell.video_widget, 'setSizePolicy'):
                            cell.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                    self._preview_window.resize(self.multi_grid_widget.size())
                    # Center preview window on screen
                    screen = QApplication.primaryScreen().geometry()
                    x = screen.center().x() - self.multi_grid_widget.width() // 2
                    y = screen.center().y() - self.multi_grid_widget.height() // 2
                    self._preview_window.move(x, y)
                    self._preview_window.show()
                    self._preview_window.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                    self._preview_window.setFocus()
                    self._preview_window.raise_()
                    def esc_close(event):
                        # --- Minimize preview window on Backspace ---
                        if event.key() == Qt.Key.Key_Backspace:
                            self._preview_window.showMinimized()
                            return
                        if event.key() == Qt.Key.Key_Q:
                            QApplication.quit()
                            return
                        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Y):
                            self._preview_mode = False
                            self._preview_window.close()
                            self.multi_grid_widget.setParent(None)
                            # Properly restore multi mode layout
                            if hasattr(self, '_restore_multi_mode_layout'):
                                self._restore_multi_mode_layout()
                            else:
                                # Fallback for older versions
                                self.right_panel_layout.insertWidget(1, self.multi_grid_widget)
                                self.multi_grid_widget.setVisible(True)
                                self.multi_grid_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                                for cell in self.multi_video_widgets:
                                    if hasattr(cell, 'setSizePolicy'):
                                        cell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                                    if hasattr(cell, 'video_widget') and hasattr(cell.video_widget, 'setSizePolicy'):
                                        cell.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                            self.showNormal()
                            self.setGeometry(self._prev_geometry)
                            self.setWindowState(self._prev_window_state)
                            self.show()
                            event.accept()
                            return
                        self.keyPressEvent(event)
                    self._preview_window.keyPressEvent = esc_close
                    self.multi_grid_widget.keyPressEvent = esc_close
                    self.multi_grid_widget.setMinimumSize(200, 150)
                    # --- Add resize handler ---
                    def preview_resizeEvent(ev):
                        self.multi_grid_widget.resize(self._preview_window.size())
                        for cell in self.multi_video_widgets:
                            if hasattr(cell, 'resize'):
                                cell.resize(cell.parent().size())
                            if hasattr(cell, 'video_widget') and hasattr(cell.video_widget, 'resize'):
                                cell.video_widget.resize(cell.size())
                        QWidget.resizeEvent(self._preview_window, ev)
                    self._preview_window.resizeEvent = preview_resizeEvent
                except Exception as e:
                    # If anything goes wrong, restore the main window
                    print(f"Error in Shift+Y preview mode: {e}")
                    self._preview_mode = False
                    if hasattr(self, '_preview_window'):
                        self._preview_window.close()
                    self.showNormal()
                    self.setGeometry(self._prev_geometry)
                    self.setWindowState(self._prev_window_state)
                    self.show()
                    QMessageBox.warning(self, "Preview Error", f"Failed to open preview window: {e}")
            else:
                # --- Restore from Preview Mode ---
                if hasattr(self, '_preview_window'):
                    self._preview_window.close()
                    # Restore correct widget to main window
                    if hasattr(self, 'multi_grid_widget'):
                        self.multi_grid_widget.setParent(None)
                        # Properly restore multi mode layout
                        if hasattr(self, '_restore_multi_mode_layout'):
                            self._restore_multi_mode_layout()
                        else:
                            # Fallback for older versions
                            self.right_panel_layout.insertWidget(1, self.multi_grid_widget)
                            self.multi_grid_widget.setVisible(True)
                    self.showNormal()
                    self.setGeometry(self._prev_geometry)
                    self.setWindowState(self._prev_window_state)
                    self.show()
            return
        # --- Preview Mode Toggle (Regular Y - no modifiers) ---
        if event.key() == Qt.Key.Key_Y and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            print(f"DEBUG: Regular Y pressed - key: {event.key()}, modifiers: {event.modifiers()}")
            if not hasattr(self, '_preview_mode'):
                self._preview_mode = False
            self._preview_mode = not self._preview_mode
            if self._preview_mode:
                import ctypes
                # --- Preview for multi-mode ---
                if self.multi_mode and self.multi_grid_widget.isVisible():
                    # Hide main window
                    self._prev_geometry = self.geometry()
                    self._prev_window_state = self.windowState()
                    self.hide()
                    # Create preview window sized to grid
                    self._preview_window = QWidget()
                    self._preview_window.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
                    self._preview_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
                    layout = QVBoxLayout(self._preview_window)
                    layout.setContentsMargins(0,0,0,0)
                    layout.setSpacing(0)
                    self.multi_grid_widget.setParent(self._preview_window)
                    layout.addWidget(self.multi_grid_widget)
                    # --- Set Expanding policy for grid and cells in preview ---
                    self.multi_grid_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                    for cell in getattr(self, 'multi_video_widgets', []):
                        cell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                        cell.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                    self._preview_window.resize(self.multi_grid_widget.size())
                    # Center preview window on screen
                    screen = QApplication.primaryScreen().geometry()
                    x = screen.center().x() - self.multi_grid_widget.width() // 2
                    y = screen.center().y() - self.multi_grid_widget.height() // 2
                    self._preview_window.move(x, y)
                    self._preview_window.show()
                    self._preview_window.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                    self._preview_window.setFocus()
                    self._preview_window.raise_()
                    def esc_close(event):
                        # --- Minimize preview window on Backspace ---
                        if event.key() == Qt.Key.Key_Backspace:
                            self._preview_window.showMinimized()
                            return
                        if event.key() == Qt.Key.Key_Q:
                            QApplication.quit()
                            return
                        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Y):
                            self._preview_mode = False
                            self._preview_window.close()
                            self.multi_grid_widget.setParent(None)
                            # Properly restore multi mode layout
                            if hasattr(self, '_restore_multi_mode_layout'):
                                self._restore_multi_mode_layout()
                            else:
                                # Fallback for older versions
                                self.right_panel_layout.insertWidget(1, self.multi_grid_widget)
                                self.multi_grid_widget.setVisible(True)
                                self.multi_grid_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                                for cell in getattr(self, 'multi_video_widgets', []):
                                    cell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                                    cell.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                            self.showNormal()
                            self.setGeometry(self._prev_geometry)
                            self.setWindowState(self._prev_window_state)
                            self.show()
                            event.accept()
                            return
                        self.keyPressEvent(event)
                    self._preview_window.keyPressEvent = esc_close
                    self.multi_grid_widget.keyPressEvent = esc_close
                    self.multi_grid_widget.setMinimumSize(200, 150)
                    # --- Add resize handler ---
                    def preview_resizeEvent(ev):
                        self.multi_grid_widget.resize(self._preview_window.size())
                        for cell in getattr(self, 'multi_video_widgets', []):
                            cell.resize(cell.parent().size())
                            cell.video_widget.resize(cell.size())
                        QWidget.resizeEvent(self._preview_window, ev)
                    self._preview_window.resizeEvent = preview_resizeEvent
                else:
                    # --- Single video preview mode (unchanged) ---
                    # Get video frame size
                    pixmap = self.pixmap_item.pixmap()
                    if not pixmap.isNull():
                        video_width = pixmap.width()
                        video_height = pixmap.height()
                    else:
                        video_width, video_height = 640, 480
                    # Hide main window
                    self._prev_geometry = self.geometry()
                    self._prev_window_state = self.windowState()
                    self.hide()
                    # Create preview window sized to video
                    self._preview_window = QWidget()
                    # Always-on-top preview window
                    self._preview_window.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
                    self._preview_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
                    layout = QVBoxLayout(self._preview_window)
                    layout.setContentsMargins(0,0,0,0)
                    layout.setSpacing(0)
                    self.graphics_view.setParent(self._preview_window)
                    layout.addWidget(self.graphics_view)
                    self._preview_window.resize(video_width, video_height)
                    # Center preview window on screen
                    screen = QApplication.primaryScreen().geometry()
                    x = screen.center().x() - video_width // 2
                    y = screen.center().y() - video_height // 2
                    self._preview_window.move(x, y)
                    self._preview_window.show()
                    # Ensure preview window receives key events
                    self._preview_window.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                    self._preview_window.setFocus()
                    self._preview_window.raise_()
                    # ESC closes preview
                    def esc_close(event):
                        # --- Minimize preview window on Backspace ---
                        if event.key() == Qt.Key.Key_Backspace:
                            self._preview_window.showMinimized()
                            return
                        # Q quits the entire application
                        if event.key() == Qt.Key.Key_Q:
                            QApplication.quit()
                            return
                        # Y or Esc exit preview mode
                        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Y):
                            self._preview_mode = False
                            self._preview_window.close()
                            self.graphics_view.setParent(None)
                            # Restore graphics_view to its original layout
                            for i in range(self.right_panel_layout.count()):
                                item = self.right_panel_layout.itemAt(i)
                                if item and item.widget() is self.graphics_view:
                                    self.right_panel_layout.removeWidget(self.graphics_view)
                                    break
                            self.right_panel_layout.insertWidget(3, self.graphics_view, 1)
                            self.showNormal()
                            self.setGeometry(self._prev_geometry)
                            self.setWindowState(self._prev_window_state)
                            self.show()
                            event.accept()
                            return
                        # Prevent double navigation: accept Up/Down so only one handler runs
                        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                            self.keyPressEvent(event)
                            event.accept()
                            return
                        self.keyPressEvent(event)
                    self._preview_window.keyPressEvent = esc_close
                    self.graphics_view.keyPressEvent = esc_close
                    # Ensure video scales with window
                    self.graphics_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                    self._preview_window.setMinimumSize(200, 150)
            else:
                # --- Restore from Preview Mode ---
                if hasattr(self, '_preview_window'):
                    self._preview_window.close()
                    # Restore correct widget to main window
                    if self.multi_mode and hasattr(self, 'multi_grid_widget'):
                        self.multi_grid_widget.setParent(None)
                        self.right_panel_layout.insertWidget(1, self.multi_grid_widget)
                        self.multi_grid_widget.setVisible(True)
                    else:
                        self.graphics_view.setParent(None)
                        for i in range(self.right_panel_layout.count()):
                            item = self.right_panel_layout.itemAt(i)
                            if item and item.widget() is self.graphics_view:
                                self.right_panel_layout.removeWidget(self.graphics_view)
                                break
                        self.right_panel_layout.insertWidget(3, self.graphics_view, 1)
                    self.showNormal()
                    self.setGeometry(self._prev_geometry)
                    self.setWindowState(self._prev_window_state)
                    self.show()
            return
        # --- End Preview Mode Toggle ---
        key = event.key()
        modifiers = event.modifiers()
        
        # Handle scene navigation shortcuts (must be before other shortcuts)
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            # Handle Ctrl+0 to jump to scene 10 (11th scene)
            if key == Qt.Key.Key_0:
                scene_index = 10  # Scene index 10 (the 11th scene)
                print(f"Ctrl+0: Attempting to jump to scene {scene_index}")
                if hasattr(self, 'jump_to_scene_by_index') and hasattr(self, 'current_scenes') and self.current_scenes:
                    self.jump_to_scene_by_index(scene_index)
                    return
                else:
                    print(f"No scenes detected or method not available")
                    return
                    
            # Handle Ctrl+number keys for scene navigation (Ctrl+1 = second scene, Ctrl+2 = third scene, etc.)
            elif Qt.Key.Key_1 <= key <= Qt.Key.Key_9:
                scene_index = key - Qt.Key.Key_0  # Convert to 0-based index (Ctrl+1 = scene 1, Ctrl+2 = scene 2, etc.)
                print(f"Ctrl+{key - Qt.Key.Key_0}: Attempting to jump to scene {scene_index}")
                if hasattr(self, 'jump_to_scene_by_index') and hasattr(self, 'current_scenes') and self.current_scenes:
                    self.jump_to_scene_by_index(scene_index)
                    return
                else:
                    print(f"No scenes detected or method not available")
                    return
                    
            # Handle Ctrl+- and Ctrl+= for scenes 13 and 14
            elif key == Qt.Key.Key_Minus:  # Ctrl+-
                scene_index = 12  # Scene 13 (0-based index)
                print(f"Ctrl+-: Attempting to jump to scene {scene_index}")
                if hasattr(self, 'jump_to_scene_by_index') and hasattr(self, 'current_scenes') and self.current_scenes:
                    self.jump_to_scene_by_index(scene_index)
                    return
            elif key == Qt.Key.Key_Equal:  # Ctrl+=
                scene_index = 13  # Scene 14 (0-based index)
                print(f"Ctrl+=: Attempting to jump to scene {scene_index}")
                if hasattr(self, 'jump_to_scene_by_index') and hasattr(self, 'current_scenes') and self.current_scenes:
                    self.jump_to_scene_by_index(scene_index)
                    return
                    
            # Handle Ctrl+Q through Ctrl+\ for scenes 15-30 (next row of keys)
            else:
                # Q=15, W=16, E=17, R=18, T=19, Y=20, U=21, I=22, O=23, P=24, [=25, ]=26, \=27
                scene_mapping = {
                    Qt.Key.Key_Q: 14,  # Scene 15
                    Qt.Key.Key_W: 15,  # Scene 16
                    Qt.Key.Key_E: 16,  # Scene 17
                    Qt.Key.Key_R: 17,  # Scene 18
                    Qt.Key.Key_T: 18,  # Scene 19
                    Qt.Key.Key_Y: 19,  # Scene 20
                    Qt.Key.Key_U: 20,  # Scene 21
                    Qt.Key.Key_I: 21,  # Scene 22
                    Qt.Key.Key_O: 22,  # Scene 23
                    Qt.Key.Key_P: 23,  # Scene 24
                    Qt.Key.Key_BracketLeft: 24,   # Scene 25
                    Qt.Key.Key_BracketRight: 25,  # Scene 26
                    Qt.Key.Key_Backslash: 26,     # Scene 27
                }
                
                if key in scene_mapping:
                    scene_index = scene_mapping[key]
                    print(f"Ctrl+{chr(key)}: Attempting to jump to scene {scene_index}")
                    if hasattr(self, 'jump_to_scene_by_index') and hasattr(self, 'current_scenes') and self.current_scenes:
                        self.jump_to_scene_by_index(scene_index)
                        return
        
        # Handle Shift + directional shortcuts for extended movement (skip by trim_length * 4)
        if modifiers == Qt.KeyboardModifier.ShiftModifier:
            if key in (Qt.Key.Key_Right, Qt.Key.Key_F):
                # Move highlight loop forward by trim_length*4
                if self.loop_playback:
                    old_start = self.trim_points.get(self.current_video, self.slider.value())
                    max_start = max(0, self.frame_count - self.trim_length)
                    new_start = min(old_start + self.trim_length * 4, max_start)
                else:
                    current_frame = self.slider.value() if hasattr(self, 'slider') else 0
                    max_start = max(0, self.frame_count - self.trim_length)
                    new_start = min(current_frame + self.trim_length * 4, max_start)
                self.trim_points[self.current_video] = new_start
                self.slider.setValue(new_start)
                if self.cap:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_start)
                    # Sync audio position to match video position
                    if hasattr(self, '_sync_audio_position'):
                        self._sync_audio_position()
                if self.loop_playback:
                    self.editor._stop_timer()
                    self.editor._playback_mode = 'loop'
                    self.editor.playback_timer.start(self.video_delay)
                    self.update_status(f'HIGHLIGHT LOOP: {new_start}-{new_start + self.trim_length}')
                else:
                    self.update_status(f'HIGHLIGHT ADJUST: {new_start}')
                return
            elif key in (Qt.Key.Key_Left, Qt.Key.Key_D):
                # Move highlight loop backward by trim_length*4
                if self.loop_playback:
                    old_start = self.trim_points.get(self.current_video, self.slider.value())
                    new_start = max(0, old_start - self.trim_length * 4)
                else:
                    current_frame = self.slider.value() if hasattr(self, 'slider') else 0
                    new_start = max(0, current_frame - self.trim_length * 4)
                self.trim_points[self.current_video] = new_start
                self.slider.setValue(new_start)
                if self.cap:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_start)
                    # Sync audio position to match video position
                    if hasattr(self, '_sync_audio_position'):
                        self._sync_audio_position()
                if self.loop_playback:
                    self.editor._stop_timer()
                    self.editor._playback_mode = 'loop'
                    self.editor.playback_timer.start(self.video_delay)
                    self.update_status(f'HIGHLIGHT LOOP: {new_start}-{new_start + self.trim_length}')
                else:
                    self.update_status(f'HIGHLIGHT ADJUST: {new_start}')
                return
        # Handle plain Right/Left Arrow and F/D for single trim movement
        if modifiers == Qt.KeyboardModifier.NoModifier:
            if key in (Qt.Key.Key_Right, Qt.Key.Key_F):
                # Move highlight loop forward
                if self.loop_playback:
                    old_start = self.trim_points.get(self.current_video, self.slider.value())
                    max_start = max(0, self.frame_count - self.trim_length)
                    new_start = min(old_start + self.trim_length, max_start)
                else:
                    # Use current frame for non-loop
                    current_frame = self.slider.value() if hasattr(self, 'slider') else 0
                    max_start = max(0, self.frame_count - self.trim_length)
                    new_start = min(current_frame + self.trim_length, max_start)
                self.trim_points[self.current_video] = new_start
                self.slider.setValue(new_start)
                if self.cap:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_start)
                    # Sync audio position to match video position
                    if hasattr(self, '_sync_audio_position'):
                        self._sync_audio_position()
                if self.loop_playback:
                    self.editor._stop_timer()
                    self.editor._playback_mode = 'loop'
                    self.editor.playback_timer.start(self.video_delay)
                    self.update_status(f'HIGHLIGHT LOOP: {new_start}-{new_start + self.trim_length}')
                else:
                    self.update_status(f'HIGHLIGHT ADJUST: {new_start}')
                return
            elif key in (Qt.Key.Key_Left, Qt.Key.Key_D):
                # Move highlight loop backward
                if self.loop_playback:
                    old_start = self.trim_points.get(self.current_video, self.slider.value())
                    new_start = max(0, old_start - self.trim_length)
                else:
                    current_frame = self.slider.value() if hasattr(self, 'slider') else 0
                    new_start = max(0, current_frame - self.trim_length)
                self.trim_points[self.current_video] = new_start
                self.slider.setValue(new_start)
                if self.cap:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_start)
                    # Sync audio position to match video position
                    if hasattr(self, '_sync_audio_position'):
                        self._sync_audio_position()
                if self.loop_playback:
                    self.editor._stop_timer()
                    self.editor._playback_mode = 'loop'
                    self.editor.playback_timer.start(self.video_delay)
                    self.update_status(f'HIGHLIGHT LOOP: {new_start}-{new_start + self.trim_length}')
                else:
                    self.update_status(f'HIGHLIGHT ADJUST: {new_start}')
                return
            elif key == Qt.Key.Key_S:
                # In highlight loop: nudge start up by 1 and restart loop
                if self.loop_playback:
                    old_start = self.trim_points.get(self.current_video, self.slider.value())
                    max_start = max(0, self.frame_count - self.trim_length)
                    new_start = min(old_start + 1, max_start)
                    self.trim_points[self.current_video] = new_start
                    self.slider.setValue(new_start)
                    if self.cap:
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_start)
                        # Sync audio position to match video position
                        if hasattr(self, '_sync_audio_position'):
                            self._sync_audio_position()
                        # Immediately display the new start frame
                        ret, frame = self.cap.read()
                        if ret:
                            self.editor.display_frame(frame)
                    self.editor._stop_timer()
                    self.editor._playback_mode = 'loop'
                    self.editor.playback_timer.start(self.video_delay)
                    self.update_status(f'HIGHLIGHT LOOP: {new_start}-{new_start + self.trim_length}')
                    return
                # If not in loop, keep existing behavior (if any)
        
        # Handle Ctrl + directional shortcuts for double trim length
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            if key in (Qt.Key.Key_F, Qt.Key.Key_Right):
                # Move highlight loop forward by trim_length*2
                if self.loop_playback:
                    old_start = self.trim_points.get(self.current_video, self.slider.value())
                    max_start = max(0, self.frame_count - self.trim_length)
                    new_start = min(old_start + self.trim_length * 2, max_start)
                else:
                    current_frame = self.slider.value() if hasattr(self, 'slider') else 0
                    max_start = max(0, self.frame_count - self.trim_length)
                    new_start = min(current_frame + self.trim_length * 2, max_start)
                self.trim_points[self.current_video] = new_start
                self.slider.setValue(new_start)
                if self.cap:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_start)
                    # Sync audio position to match video position
                    if hasattr(self, '_sync_audio_position'):
                        self._sync_audio_position()
                if self.loop_playback:
                    self.editor._stop_timer()
                    self.editor._playback_mode = 'loop'
                    self.editor.playback_timer.start(self.video_delay)
                    self.update_status(f'HIGHLIGHT LOOP: {new_start}-{new_start + self.trim_length}')
                else:
                    self.update_status(f'HIGHLIGHT ADJUST: {new_start}')
                return
            elif key in (Qt.Key.Key_D, Qt.Key.Key_Left):
                # Move highlight loop backward by trim_length*2
                if self.loop_playback:
                    old_start = self.trim_points.get(self.current_video, self.slider.value())
                    new_start = max(0, old_start - self.trim_length * 2)
                else:
                    current_frame = self.slider.value() if hasattr(self, 'slider') else 0
                    new_start = max(0, current_frame - self.trim_length * 2)
                self.trim_points[self.current_video] = new_start
                self.slider.setValue(new_start)
                if self.cap:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_start)
                    # Sync audio position to match video position
                    if hasattr(self, '_sync_audio_position'):
                        self._sync_audio_position()
                if self.loop_playback:
                    self.editor._stop_timer()
                    self.editor._playback_mode = 'loop'
                    self.editor.playback_timer.start(self.video_delay)
                    self.update_status(f'HIGHLIGHT LOOP: {new_start}-{new_start + self.trim_length}')
                else:
                    self.update_status(f'HIGHLIGHT ADJUST: {new_start}')
                return


                
        # Handle number keys and backtick for position jumping
        if key == Qt.Key.Key_QuoteLeft or key == Qt.Key.Key_0:  # Both ` and 0 jump to start
            if self.slider.isEnabled():
                position = 0
                self.slider.setValue(position)
                self.editor.scrub_video(position)
                return
        elif Qt.Key.Key_1 <= key <= Qt.Key.Key_9:
            if self.slider.isEnabled():
                percentage = (key - Qt.Key.Key_0) * 10
                position = int((percentage / 100.0) * self.slider.maximum())
                self.slider.setValue(position)
                self.editor.scrub_video(position)
                return

        # '/' focuses the search bar unless already focused
        if key == Qt.Key.Key_Slash and not self.search_bar.hasFocus():
            self.search_bar.setFocus()
            event.accept()
            return
        # Handle regular shortcuts
        if key == Qt.Key.Key_Z:
            # Classic Z: set trim point to current frame and toggle loop playback
            self.trim_points[self.current_video] = self.slider.value()
            self.editor.toggle_loop_playback()
            return
        elif key in (Qt.Key.Key_E, Qt.Key.Key_Up):  # Previous clip
            self.editor.prev_clip()
        elif key in (Qt.Key.Key_R, Qt.Key.Key_Down):  # Next clip
            self.editor.next_clip()
        elif key == Qt.Key.Key_V or key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.editor.toggle_play_forward()
            event.accept()
            return
        # elif key == Qt.Key.Key_T:
        #     self.toggle_fullscreen()
        #     event.accept()
        #     return
        elif key == Qt.Key.Key_A and modifiers == Qt.KeyboardModifier.NoModifier:
            if self.loop_playback:
                trim_length = self.trim_spin.value() if hasattr(self, 'trim_spin') else self.trim_length
                old_start = self.trim_points.get(self.current_video, self.slider.value())
                new_start = max(0, old_start - 1)
                self.trim_points[self.current_video] = new_start
                self.slider.setValue(new_start)
                if self.cap:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_start)
                    # Sync audio position to match video position
                    if hasattr(self, '_sync_audio_position'):
                        self._sync_audio_position()
                    ret, frame = self.cap.read()
                    if ret:
                        self.editor.display_frame(frame)
                self.loop_playback = True
                self.is_playing = True
                self.editor._stop_timer()
                self.editor._playback_mode = 'loop'
                self.editor.playback_timer.start(self.video_delay)
                self.update_status(f'HIGHLIGHT LOOP: {new_start}-{new_start + trim_length}')
            else:
                # Just decrement trim point, update frame and status, but do not start looping
                old_start = self.trim_points.get(self.current_video, self.slider.value())
                new_start = max(0, old_start - 1)
                self.trim_points[self.current_video] = new_start
                self.slider.setValue(new_start)
                if self.cap:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_start)
                    # Sync audio position to match video position
                    if hasattr(self, '_sync_audio_position'):
                        self._sync_audio_position()
                    ret, frame = self.cap.read()
                    if ret:
                        self.editor.display_frame(frame)
                self.update_status(f'HIGHLIGHT ADJUST: {new_start}')
            return
        elif key == Qt.Key.Key_S and modifiers == Qt.KeyboardModifier.NoModifier:
            if self.loop_playback:
                # Shift loop start forward by one frame (from current loop start, not slider)
                trim_len = self.trim_spin.value() if hasattr(self, 'trim_spin') else self.trim_length
                old_start = self.trim_points[self.current_video]
                max_start = max(0, self.frame_count - trim_len)
                new_start = min(old_start + 1, max_start)
                self.trim_points[self.current_video] = new_start
                self.slider.setValue(new_start)
                if self.cap:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_start)
                    # Sync audio position to match video position
                    if hasattr(self, '_sync_audio_position'):
                        self._sync_audio_position()
                    ret, frame = self.cap.read()
                    if ret:
                        self.editor.display_frame(frame)
                self.update_status(f'HIGHLIGHT LOOP: {new_start}-{new_start + trim_len}')
            else:
                self.editor.move_trim(1)
            return
        elif key in (Qt.Key.Key_D, Qt.Key.Key_Left):
            self.editor.move_trim(-self.trim_length)
        elif key in (Qt.Key.Key_F, Qt.Key.Key_Right):
            self.editor.move_trim(self.trim_length)
        elif key == Qt.Key.Key_W:  # Open folder
            if self.folder_path:
                os.startfile(self.folder_path)
            else:
                QMessageBox.warning(self, "No Folder", "No folder is currently selected.")
        elif key == Qt.Key.Key_Q and modifiers == Qt.KeyboardModifier.NoModifier:
            self.close()
            return
        elif key == Qt.Key.Key_G and modifiers == Qt.KeyboardModifier.NoModifier:
            # Toggle between 'Random' and 'Date (new first)' sorting
            if not hasattr(self, '_g_random_toggle'):
                self._g_random_toggle = False
            if not self._g_random_toggle:
                idx = self.sort_dropdown.findText("Random")
                if idx != -1:
                    self.sort_dropdown.setCurrentIndex(idx)
                self._g_random_toggle = True
            else:
                idx = self.sort_dropdown.findText("Date (new first)")
                if idx != -1:
                    self.sort_dropdown.setCurrentIndex(idx)
                self._g_random_toggle = False
            
            # In multi-video mode, also randomize the video positions
            if hasattr(self, 'multi_mode') and self.multi_mode and hasattr(self, 'multi_video_widgets') and self.multi_video_widgets:
                import random
                # Get all available video indices
                all_indices = list(range(len(self.video_files)))
                # Randomly select new indices for each grid position
                new_indices = random.sample(all_indices, len(self.multi_video_widgets))
                self.multi_selected_indices = new_indices
                
                # Update each grid cell with the new random video
                for i, (cell, new_idx) in enumerate(zip(self.multi_video_widgets, new_indices)):
                    entry = self.video_files[new_idx]
                    cell.load(entry["original_path"])
                    cell.player.play()
                    cell.setToolTip(entry["display_name"])
                
                self.update_status(f"Multi-video: Jumped to random positions ({len(self.multi_video_widgets)} videos)")
            
            return
        elif key == Qt.Key.Key_B and self.current_video:
            self.exporter.export_videos()
        elif key == Qt.Key.Key_Delete:
            self.delete_selected_video()
            return
        elif modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_Z:
            self.undo_delete_video()
            return
        elif key == Qt.Key.Key_X and modifiers == Qt.KeyboardModifier.NoModifier:
            self.auto_advance_button.toggle()
            self.toggle_auto_advance()
            return
        elif key == Qt.Key.Key_C and modifiers == Qt.KeyboardModifier.NoModifier:
            self.take_screenshot()
            event.accept()
            return
        elif key == Qt.Key.Key_I and modifiers == Qt.KeyboardModifier.NoModifier:
            # Show metadata when I key is pressed
            if hasattr(self, 'current_video') and self.current_video:
                # Get the current video entry
                entry = next((e for e in self.video_files if e["display_name"] == self.current_video), None)
                if entry:
                    # Call the display_video_metadata method to show detailed metadata
                    if hasattr(self, 'display_video_metadata'):
                        self.display_video_metadata(entry)
            return
        else:
            # super().keyPressEvent(event)
            QWidget.keyPressEvent(self, event)
        
        # Only handle up/down if focus is NOT on graphics_view (to prevent double navigation)
        if key == Qt.Key.Key_Up:
            if self.focusWidget() is not self.graphics_view:
                self.editor.prev_clip()
            return
        elif key == Qt.Key.Key_Down:
            if self.focusWidget() is not self.graphics_view:
                self.editor.next_clip()
            return
