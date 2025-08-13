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

        # Fast interactive plot
        pg.setConfigOptions(antialias=True)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('k')
        self.plot_widget.showGrid(x=False, y=True, alpha=0.2)
        self.plot_widget.setMouseEnabled(x=True, y=False)
        self.plot_item = self.plot_widget.getPlotItem()
        self.curve = self.plot_item.plot(pen=pg.mkPen('#55C3FF', width=1))

        # Markers
        self.start_line = pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen('#00FF88', width=2))
        self.end_line = pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen('#FF3366', width=2))
        self.playhead_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#FFFF00', width=1))
        self.plot_item.addItem(self.start_line)
        self.plot_item.addItem(self.end_line)
        self.plot_item.addItem(self.playhead_line)
        self.start_line.hide()
        self.end_line.hide()
        self.playhead_line.hide()

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
        if self._samples is None or self.plot_widget is None:
            return
        # Downsample for speed if very long
        x = self._samples
        max_points = 5000
        if x.shape[0] > max_points:
            # block reduce by max/abs for envelope
            factor = int(np.ceil(x.shape[0] / max_points))
            pad = (-x.shape[0]) % factor
            if pad:
                x = np.pad(x, (0, pad), mode='constant')
            x = x.reshape(-1, factor)
            x = x.mean(axis=1)
        self.curve.setData(x)
        self.plot_item.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)
        self.playhead_line.setValue(0)
        self.playhead_line.show()
        # Default trim to full length
        self._start_ms, self._end_ms = 0, self._duration_ms
        self._update_marker_positions()
        self.start_line.show()
        self.end_line.show()

    def set_playhead_ms(self, ms: int) -> None:
        if self._duration_ms <= 0 or self.playhead_line is None:
            return
        # Map ms to sample index domain used in curve (0..len(samples)-1 envelope)
        x_pos = self._ms_to_sample_index(ms)
        self.playhead_line.setValue(x_pos)
        self.playhead_line.show()

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
        s_idx = self._ms_to_sample_index(self._start_ms or 0)
        e_idx = self._ms_to_sample_index(self._end_ms or self._duration_ms)
        self.start_line.blockSignals(True)
        self.end_line.blockSignals(True)
        self.start_line.setValue(s_idx)
        self.end_line.setValue(e_idx)
        self.start_line.blockSignals(False)
        self.end_line.blockSignals(False)

    def _ms_to_sample_index(self, ms: int) -> int:
        if self._sr is None or self._duration_ms <= 0 or self._samples is None:
            return 0
        total_samples = self._samples.shape[0]
        ratio = float(ms) / float(self._duration_ms)
        return int(max(0, min(total_samples - 1, ratio * total_samples)))

    def _sample_index_to_ms(self, idx: int) -> int:
        if self._samples is None or self._duration_ms <= 0:
            return 0
        total = max(1, self._samples.shape[0] - 1)
        ratio = max(0.0, min(1.0, float(idx) / float(total)))
        return int(ratio * self._duration_ms)

    def _on_plot_clicked(self, ev):
        if self.plot_item is None or self._duration_ms <= 0 or self._samples is None:
            return
        try:
            vb = self.plot_item.getViewBox()
            mouse_point = vb.mapSceneToView(ev.scenePos())
            idx = int(max(0, min(self._samples.shape[0] - 1, mouse_point.x())))
            ms = self._sample_index_to_ms(idx)
            self.playheadSeekRequested.emit(int(ms))
        except Exception:
            pass

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
