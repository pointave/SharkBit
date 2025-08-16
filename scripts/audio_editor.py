from __future__ import annotations
import os
from typing import Optional, Tuple

from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

# Optional heavy deps
try:
    import numpy as np  # type: ignore
except Exception:
    np = None  # type: ignore

# Try pyqtgraph for fast waveform rendering
try:
    import pyqtgraph as pg  # type: ignore
except Exception:
    pg = None  # type: ignore


class AudioEditor(QWidget):
    """
    Lightweight audio editor panel with waveform, draggable trim markers, and playhead.
    - load(path): loads audio and renders waveform (best-effort; supports many formats if librosa available)
    - set_playhead_ms(ms): updates playhead position
    - set_trim_points(start_ms, end_ms): sets markers
    Signals:
      trimChanged(start_ms: int, end_ms: int)
    """

    trimChanged = pyqtSignal(int, int)
    playheadSeekRequested = pyqtSignal(int)  # ms

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._audio_path: Optional[str] = None
        self._duration_ms: int = 0
        self._sr: Optional[int] = None
        self._samples: Optional["np.ndarray"] = None  # mono float32 [-1,1]
        self._start_ms: Optional[int] = None
        self._end_ms: Optional[int] = None
        
        # Enable key events
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        if pg is None or np is None:
            self.info_label = QLabel("Waveform preview requires numpy and pyqtgraph. Install them to enable.")
            self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.info_label)
            self.plot_widget = None
            self.start_line = None
            self.end_line = None
            self.playhead_line = None
            return

        # Professional waveform display with grid and axis
        pg.setConfigOptions(antialias=True, useNumba=True, useOpenGL=True)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1e1e1e')  # Dark background like professional DAWs
        
        self.plot_item = self.plot_widget.getPlotItem()
        self.plot_item.setMouseEnabled(x=True, y=False)
        
        # Configure axes
        self.plot_item.showAxis('bottom', show=True)
        self.plot_item.showAxis('left', show=True)
        self.plot_item.getAxis('bottom').setPen(pg.mkPen('#888888'))
        self.plot_item.getAxis('left').setPen(pg.mkPen('#888888'))
        self.plot_item.setLabel('bottom', 'Time', 's')
        self.plot_item.setLabel('left', 'Amplitude')
        
        # Add grid
        self.plot_item.showGrid(x=True, y=True, alpha=0.2)
        
        # Create two curves for positive and negative parts (like Audacity)
        self.curve_positive = self.plot_item.plot(pen=pg.mkPen('#4e9ef4', width=1.2))  # Light blue for positive
        self.curve_negative = self.plot_item.plot(pen=pg.mkPen('#4e9ef4', width=1.2))  # Same color for now
        self.curve_zero = self.plot_item.plot(pen=pg.mkPen('#555555', width=0.5))  # Center line

        # Markers with better visibility
        self.start_line = pg.InfiniteLine(
            angle=90, 
            movable=True, 
            pen=pg.mkPen('#00FF88', width=2),
            hoverPen=pg.mkPen('#00FF88', width=3),
            bounds=[0, None]
        )
        self.end_line = pg.InfiniteLine(
            angle=90, 
            movable=True, 
            pen=pg.mkPen('#FF3366', width=2),
            hoverPen=pg.mkPen('#FF3366', width=3),
            bounds=[0, None]
        )
        self.playhead_line = pg.InfiniteLine(
            angle=90, 
            movable=False, 
            pen=pg.mkPen('#FFCC00', width=1.5, style=Qt.PenStyle.DashLine),
            hoverPen=pg.mkPen('#FFEE00', width=2, style=Qt.PenStyle.DashLine)
        )
        
        # Add markers to plot
        for line in [self.start_line, self.end_line, self.playhead_line]:
            self.plot_item.addItem(line)
            line.hide()
            
        # Add zoom/pan controls
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.setDownsampling(auto=True, mode='peak')
        self.plot_widget.setClipToView(True)
        self.plot_widget.setLimits(xMin=0, minXRange=0.1)
        
        # Context menu for zoom controls
        self.plot_widget.scene().contextMenu = []  # Remove default context menu

        # Marker moved handlers
        self.start_line.sigPositionChanged.connect(self._on_marker_moved)
        self.end_line.sigPositionChanged.connect(self._on_marker_moved)

        # Click-to-seek
        try:
            self.plot_widget.scene().sigMouseClicked.connect(self._on_plot_clicked)
        except Exception:
            pass

        layout.addWidget(self.plot_widget, 1)

    # Public API
    # ----------
    def load(self, path: str) -> None:
        self._audio_path = path
        self._samples, self._sr, self._duration_ms = self._load_samples(path)
        if self._samples is None or self.plot_widget is None or self._sr is None:
            return
            
        x = self._samples
        if x is None or len(x) == 0:
            return
            
        # Calculate time points for x-axis
        duration_sec = self._duration_ms / 1000.0
        time_points = np.linspace(0, duration_sec, len(x))
        
        # Create envelope for better visualization (top half only)
        # Take absolute value to get full waveform in positive space
        x_abs = np.abs(x)
        
        # Downsample intelligently for performance
        target_points = min(5000, len(x))  # Target number of points
        if len(x) > target_points * 2:
            # Use peak detection for better downsampling
            step = len(x) // target_points
            x_abs = self._downsample_peaks(x_abs, step)
            time_points = time_points[::step][:len(x_abs)]
        
        # Update the plot with new data (only positive half)
        self.curve_positive.setData(time_points, x_abs, pen=pg.mkPen('#4e9ef4', width=1.2))
        # Hide the negative curve since we're only showing top half
        self.curve_negative.setData([], [])  # Empty data to hide
        # Update zero line to be at the bottom
        self.curve_zero.setData([0, duration_sec], [0, 0], pen=pg.mkPen('#555555', width=0.5))
        
        # Set view to show full waveform with some padding (only positive Y)
        self.plot_item.setXRange(0, duration_sec, padding=0.02)
        self.plot_item.setYRange(0, 1.1, padding=0.1)  # Only show positive Y
        
        # Initialize playhead and markers
        self.playhead_line.setValue(0)
        self.playhead_line.show()
        
        # Default trim to full length
        self._start_ms, self._end_ms = 0, self._duration_ms
        self._update_marker_positions()
        self.start_line.show()
        self.end_line.show()
        
        # Update axis labels with time format
        self.plot_item.getAxis('bottom').setLabel(text='Time', units='s')
        
        # Enable auto-range buttons
        self.plot_item.getViewBox().enableAutoRange(enable=True)
        
    def _downsample_peaks(self, x: np.ndarray, step: int) -> np.ndarray:
        """Downsample using peak detection for better waveform visualization."""
        n = len(x) // step
        result = np.zeros(n)
        for i in range(n):
            start = i * step
            end = min((i + 1) * step, len(x))
            if start >= end:
                continue
            # Get min and max in the window
            window = x[start:end]
            if np.all(np.isnan(window)):
                result[i] = 0
            else:
                # For positive part, get max; for negative, get min
                if np.any(window > 0):
                    result[i] = np.nanmax(window)
                else:
                    result[i] = np.nanmin(window)
        return result

    def set_playhead_ms(self, ms: int) -> None:
        if self._duration_ms <= 0 or self.playhead_line is None:
            return
        # Convert ms to seconds for x-axis
        x_pos = ms / 1000.0
        self.playhead_line.setValue(x_pos)
        self.playhead_line.show()
        
        # Auto-scroll to keep playhead visible if needed
        if self.plot_item and self.plot_item.getViewBox():
            view = self.plot_item.getViewBox()
            view_range = view.viewRange()
            view_width = view_range[0][1] - view_range[0][0]
            
            # If playhead is near the right edge, scroll right
            if x_pos > view_range[0][1] - view_width * 0.2:  # 20% from right edge
                view.setXRange(x_pos - view_width * 0.8, x_pos + view_width * 0.2, padding=0)

    def set_trim_points(self, start_ms: int, end_ms: int) -> None:
        self._start_ms, self._end_ms = max(0, start_ms), max(start_ms, end_ms)
        self._update_marker_positions()

    def get_trim_points(self) -> Tuple[int, int]:
        s = 0 if self._start_ms is None else int(self._start_ms)
        e = self._duration_ms if self._end_ms is None else int(self._end_ms)
        return s, e

    # Internal helpers
    # ----------------
    def _on_marker_moved(self):
        if self._duration_ms <= 0:
            return
        # Convert marker x positions back to ms
        s_idx = int(self.start_line.value()) if self.start_line else 0
        e_idx = int(self.end_line.value()) if self.end_line else 0
        s_ms = self._sample_index_to_ms(s_idx)
        e_ms = self._sample_index_to_ms(e_idx)
        if e_ms < s_ms:
            s_ms, e_ms = e_ms, s_ms
        self._start_ms, self._end_ms = s_ms, e_ms
        self.trimChanged.emit(int(s_ms), int(e_ms))

    def _update_marker_positions(self):
        if self._duration_ms <= 0 or self.start_line is None or self.end_line is None:
            return
            
        # Convert ms to seconds for x-axis
        s_sec = (self._start_ms or 0) / 1000.0
        e_sec = (self._end_ms or self._duration_ms) / 1000.0
        
        self.start_line.blockSignals(True)
        self.end_line.blockSignals(True)
        
        # Update marker positions
        self.start_line.setValue(s_sec)
        self.end_line.setValue(e_sec)
        
        # Update marker bounds to prevent overlap and going out of range
        self.start_line.setBounds([0, e_sec])
        self.end_line.setBounds([s_sec, self._duration_ms / 1000.0])
        
        # Update marker labels if they exist (position at top of waveform)
        if hasattr(self, 'start_label'):
            self.start_label.setPos(s_sec, 1.0)
        if hasattr(self, 'end_label'):
            self.end_label.setPos(e_sec, 1.0)
            
        self.start_line.blockSignals(False)
        self.end_line.blockSignals(False)
        
        # Update the highlighted region between markers
        self._update_highlight_region()

    def _ms_to_sample_index(self, ms: int) -> int:
        if self._sr is None or self._duration_ms <= 0 or self._samples is None:
            return 0
        total_samples = self._samples.shape[0]
        ratio = float(ms) / float(self._duration_ms)
        return int(max(0, min(total_samples - 1, ratio * total_samples)))
        
    def _update_highlight_region(self):
        """No longer using highlight region to avoid interference with dragging."""
        # Remove highlight region if it exists
        if hasattr(self, 'highlight_region'):
            if self.plot_item and hasattr(self.plot_item, 'removeItem'):
                self.plot_item.removeItem(self.highlight_region)
            delattr(self, 'highlight_region')
            
    def _zoom_to_selection(self):
        """Zoom to the current selection between markers."""
        if self._start_ms is not None and self._end_ms is not None:
            start_sec = self._start_ms / 1000.0
            end_sec = self._end_ms / 1000.0
            if end_sec > start_sec:
                self.plot_item.setXRange(start_sec, end_sec, padding=0.02)
                
    def wheelEvent(self, event):
        """Handle mouse wheel events for zooming."""
        if not self.plot_widget or not self.plot_item:
            return
            
        # Get the current view range
        vb = self.plot_item.getViewBox()
        if not vb:
            return
            
        # Get mouse position in view coordinates
        pos = self.plot_widget.mapFromGlobal(event.globalPosition().toPoint())
        pos = self.plot_widget.plotItem.vb.mapSceneToView(pos)
        
        # Calculate zoom factor (15% per wheel step)
        zoom_factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        
        # Apply zoom centered on mouse position
        vb.setRange(xRange=vb.viewRange()[0], padding=0)
        vb.scaleBy((1/zoom_factor, 1), pos=pos)
        
        event.accept()

    def _sample_index_to_ms(self, idx: int) -> int:
        if self._samples is None or self._duration_ms <= 0:
            return 0
        total = max(1, self._samples.shape[0] - 1)
        ratio = max(0.0, min(1.0, float(idx) / float(total)))
        return int(ratio * self._duration_ms)

    def _on_plot_clicked(self, ev):
        if self.plot_item is None or self._duration_ms <= 0 or self._samples is None:
            return
            
        # Only process left mouse button clicks
        if ev.button() != Qt.MouseButton.LeftButton:
            return
            
        try:
            vb = self.plot_item.getViewBox()
            if not vb:
                return
                
            # Get the click position in the view coordinates
            mouse_point = vb.mapSceneToView(ev.scenePos())
            click_sec = max(0, min(self._duration_ms / 1000.0, mouse_point.x()))
            click_ms = int(click_sec * 1000)
            
            # If shift is held, set the nearest marker
            modifiers = ev.modifiers()
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                # Find which marker is closer to the click
                start_dist = abs((self._start_ms or 0) - click_ms)
                end_dist = abs((self._end_ms or self._duration_ms) - click_ms)
                
                if start_dist < end_dist:
                    self._start_ms = click_ms
                else:
                    self._end_ms = click_ms
                self._update_marker_positions()
                self.trimChanged.emit(int(self._start_ms or 0), int(self._end_ms or self._duration_ms))
            else:
                # Normal click - seek to position
                self.playheadSeekRequested.emit(click_ms)
                
            # If double click, zoom to selection
            if ev.double():
                self._zoom_to_selection()
                
        except Exception as e:
            import traceback
            print(f"Error handling plot click: {e}\n{traceback.format_exc()}")

    def keyPressEvent(self, event):
        # Handle mute toggle with CAPSLOCK or ] key
        if event.key() in [Qt.Key.Key_CapsLock, Qt.Key.Key_BracketRight] and not event.isAutoRepeat():
            if hasattr(self.parent(), 'audio_output'):
                audio_output = self.parent().audio_output
                current_volume = audio_output.volume()
                if current_volume > 0:
                    is_muted = not audio_output.isMuted()
                    audio_output.setMuted(is_muted)
                    if hasattr(self.parent(), 'update_status'):
                        self.parent().update_status(f"Audio {'muted' if is_muted else 'unmuted'}")
                else:
                    # If volume is 0, unmute and set to 50%
                    audio_output.setVolume(0.5)
                    audio_output.setMuted(False)
                    if hasattr(self.parent(), 'update_status'):
                        self.parent().update_status("Audio unmuted (50% volume)")
            event.accept()
            return
        super().keyPressEvent(event)

    def _load_samples(self, path: str):
        """Return (mono_samples_float32, sr, duration_ms). Best effort without hard deps.
        Prefers librosa if available, else tries wave for .wav files.
        """
        # Try librosa first for broad codec support
        try:
            import librosa  # type: ignore
            y, sr = librosa.load(path, sr=None, mono=True)
            if np is None:
                return None, None, 0
            y = y.astype(np.float32, copy=False)
            duration_ms = int(round((y.shape[0] / float(sr)) * 1000))
            return y, int(sr), duration_ms
        except Exception:
            pass
        # Fallback: wave module for WAV files only
        try:
            import wave, audioop
            if not path.lower().endswith('.wav'):
                return None, None, 0
            with wave.open(path, 'rb') as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                raw = wf.readframes(n_frames)
            # Convert to mono 16-bit
            if n_channels > 1:
                raw = audioop.tomono(raw, sampwidth, 0.5, 0.5)
            if sampwidth != 2:
                raw = audioop.lin2lin(raw, sampwidth, 2)
            # Bytes to numpy float32 in [-1,1]
            if np is None:
                return None, None, 0
            data = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
            data /= 32768.0
            duration_ms = int(round((data.shape[0] / float(framerate)) * 1000))
            return data, int(framerate), duration_ms
        except Exception:
            return None, None, 0
