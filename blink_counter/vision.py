"""Cross-platform camera capture and eye-landmark extraction backends.

Supports:
1. MediaPipe FaceMesh (`mp.solutions.face_mesh`) — instant offline landmark extraction.
2. MediaPipe Tasks `FaceLandmarker` — compatible with newer MediaPipe 0.10.20+ releases
   (downloads and caches `face_landmarker.task` automatically on first use).
3. OpenCV Haar Cascade fallback — lightweight fallback if MediaPipe is not installed.
"""

from __future__ import annotations

import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Tuple

from .config import default_cache_dir
from .detector import LEFT_EYE_INDICES, RIGHT_EYE_INDICES, Point2D

FACE_LANDMARKER_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
FACE_LANDMARKER_FILENAME = "face_landmarker.task"


@dataclass(frozen=True)
class EyeExtractionResult:
    """Extracted eye landmarks (pixel coordinates) for a single video frame."""

    face_detected: bool
    left_eye: Optional[List[Point2D]] = None
    right_eye: Optional[List[Point2D]] = None
    synthetic_ear: Optional[float] = None


def _camera_permission_hint() -> str:
    if sys.platform == "darwin":
        return (
            "On macOS, grant Camera access to your Terminal / IDE in "
            "System Settings -> Privacy & Security -> Camera."
        )
    if sys.platform == "win32":
        return (
            "On Windows, enable camera permissions in Settings -> Privacy & security -> Camera "
            "and ensure no other app is locking the webcam."
        )
    return (
        "On Linux, ensure your user is in the 'video' group (`sudo usermod -aG video $USER`) "
        "and that /dev/video0 is accessible."
    )


def open_video_capture(
    camera_index: int = 0,
    video_source: Optional[str] = None,
    width: int = 960,
    height: int = 540,
) -> Any:
    """Open a webcam or video file using OS-optimal OpenCV capture backends."""
    import cv2

    if video_source is not None:
        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video file: {video_source}")
        return cap

    backends: List[int] = []
    if sys.platform == "darwin" and hasattr(cv2, "CAP_AVFOUNDATION"):
        backends.append(cv2.CAP_AVFOUNDATION)
    elif sys.platform == "win32" and hasattr(cv2, "CAP_DSHOW"):
        backends.append(cv2.CAP_DSHOW)
    elif sys.platform.startswith("linux") and hasattr(cv2, "CAP_V4L2"):
        backends.append(cv2.CAP_V4L2)
    backends.append(cv2.CAP_ANY)

    cap = None
    for backend in backends:
        candidate = cv2.VideoCapture(camera_index, backend)
        if candidate.isOpened():
            cap = candidate
            break
        candidate.release()

    if cap is None:
        raise RuntimeError(
            f"Could not open camera index {camera_index}. {_camera_permission_hint()}"
        )

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    return cap


def ensure_face_landmarker_model(cache_dir: Optional[Path] = None) -> Path:
    """Ensure `face_landmarker.task` is downloaded into the local cache directory."""
    target_dir = cache_dir or default_cache_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    model_path = target_dir / FACE_LANDMARKER_FILENAME
    if model_path.exists() and model_path.stat().st_size > 100_000:
        return model_path

    tmp_path = model_path.with_suffix(".task.part")
    print(f"[blink-counter] Downloading MediaPipe FaceLandmarker model to {model_path}...")
    urllib.request.urlretrieve(FACE_LANDMARKER_MODEL_URL, tmp_path)
    tmp_path.replace(model_path)
    return model_path


class BaseEyeExtractor:
    """Common interface for eye landmark extraction backends."""

    backend_name: str = "base"

    def extract(self, bgr_frame: Any) -> EyeExtractionResult:
        raise NotImplementedError

    def close(self) -> None:
        pass


class MediaPipeFaceMeshExtractor(BaseEyeExtractor):
    """Offline MediaPipe FaceMesh extractor (`mp.solutions.face_mesh`)."""

    backend_name = "mediapipe-facemesh"

    def __init__(self) -> None:
        import mediapipe as mp

        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def extract(self, bgr_frame: Any) -> EyeExtractionResult:
        import cv2

        height, width = bgr_frame.shape[:2]
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._face_mesh.process(rgb)
        if not results.multi_face_landmarks:
            return EyeExtractionResult(face_detected=False)

        landmarks = results.multi_face_landmarks[0].landmark
        left_eye = [(landmarks[i].x * width, landmarks[i].y * height) for i in LEFT_EYE_INDICES]
        right_eye = [(landmarks[i].x * width, landmarks[i].y * height) for i in RIGHT_EYE_INDICES]
        return EyeExtractionResult(
            face_detected=True,
            left_eye=left_eye,
            right_eye=right_eye,
        )

    def close(self) -> None:
        self._face_mesh.close()


class MediaPipeTasksExtractor(BaseEyeExtractor):
    """MediaPipe Tasks FaceLandmarker extractor for MediaPipe 0.10.x+."""

    backend_name = "mediapipe-tasks"

    def __init__(self, model_path: Optional[Path] = None) -> None:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        resolved = model_path or ensure_face_landmarker_model()
        base_options = mp_python.BaseOptions(model_asset_path=str(resolved))
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._mp = mp
        self._landmarker = vision.FaceLandmarker.create_from_options(options)

    def extract(self, bgr_frame: Any) -> EyeExtractionResult:
        import cv2

        height, width = bgr_frame.shape[:2]
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect(mp_image)
        if not result.face_landmarks:
            return EyeExtractionResult(face_detected=False)

        landmarks = result.face_landmarks[0]
        left_eye = [(landmarks[i].x * width, landmarks[i].y * height) for i in LEFT_EYE_INDICES]
        right_eye = [(landmarks[i].x * width, landmarks[i].y * height) for i in RIGHT_EYE_INDICES]
        return EyeExtractionResult(
            face_detected=True,
            left_eye=left_eye,
            right_eye=right_eye,
        )

    def close(self) -> None:
        self._landmarker.close()


class OpenCVHaarExtractor(BaseEyeExtractor):
    """Lightweight OpenCV Haar Cascade fallback when MediaPipe is unavailable."""

    backend_name = "opencv-haar"

    def __init__(self) -> None:
        import cv2

        cascade_dir = Path(cv2.data.haarcascades)
        self._face_cascade = cv2.CascadeClassifier(
            str(cascade_dir / "haarcascade_frontalface_default.xml")
        )
        self._eye_cascade = cv2.CascadeClassifier(
            str(cascade_dir / "haarcascade_eye_tree_eyeglasses.xml")
        )
        if self._face_cascade.empty() or self._eye_cascade.empty():
            raise RuntimeError("OpenCV Haar cascade XML files could not be loaded.")

    def extract(self, bgr_frame: Any) -> EyeExtractionResult:
        import cv2

        gray = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = self._face_cascade.detectMultiScale(
            gray, scaleFactor=1.15, minNeighbors=5, minSize=(90, 90)
        )
        if len(faces) == 0:
            return EyeExtractionResult(face_detected=False)

        # Pick largest detected face
        x, y, w, h = max(faces, key=lambda rect: rect[2] * rect[3])
        upper_face = gray[y : y + int(h * 0.6), x : x + w]
        eyes = self._eye_cascade.detectMultiScale(
            upper_face, scaleFactor=1.1, minNeighbors=4, minSize=(20, 20)
        )
        # Synthesize EAR proxy: open eyes detected -> ~0.30, closed -> ~0.12
        synthetic_ear = 0.30 if len(eyes) >= 1 else 0.12
        return EyeExtractionResult(face_detected=True, synthetic_ear=synthetic_ear)


def create_eye_extractor(backend: str = "auto") -> BaseEyeExtractor:
    """Create the best available eye landmark extractor for this environment."""
    backend_norm = backend.strip().lower()
    if backend_norm == "haar":
        return OpenCVHaarExtractor()

    if backend_norm in ("auto", "mediapipe"):
        try:
            import mediapipe as mp

            # Prefer offline FaceMesh when available (zero download needed)
            if hasattr(mp, "solutions") and hasattr(mp.solutions, "face_mesh"):
                return MediaPipeFaceMeshExtractor()
            # Otherwise use modern MediaPipe Tasks FaceLandmarker
            return MediaPipeTasksExtractor()
        except Exception as exc:
            if backend_norm == "mediapipe":
                raise RuntimeError(f"Failed to initialize MediaPipe backend: {exc}") from exc
            print(
                f"[blink-counter] MediaPipe unavailable ({exc}); falling back to OpenCV Haar backend."
            )
            return OpenCVHaarExtractor()

    raise ValueError(f"Unknown vision backend: {backend!r}. Expected 'auto', 'mediapipe', or 'haar'.")
