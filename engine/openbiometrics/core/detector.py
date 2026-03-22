"""Face detection with alignment.

Supports two backends (auto-detected by model file):
- YuNet (OpenCV Zoo): MIT license, 75K params, 1000+ FPS capable (default, recommended)
- SCRFD (InsightFace): higher accuracy but non-commercial license (legacy)

YuNet is loaded directly via OpenCV DNN — no InsightFace dependency needed.
"""

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class DetectedFace:
    """A detected face with bounding box, landmarks, and confidence."""

    bbox: np.ndarray  # [x1, y1, x2, y2]
    landmarks: np.ndarray  # 5-point landmarks (left_eye, right_eye, nose, left_mouth, right_mouth)
    confidence: float
    aligned: np.ndarray  # 112x112 aligned face crop
    embedding: np.ndarray | None = None  # 512-d embedding (filled by recognizer)
    age: int | None = None
    gender: str | None = None
    liveness_score: float | None = None
    quality_score: float | None = None

    @property
    def face_size(self) -> float:
        """Face size as defined by biometric standards:
        max(inter-eye distance, eye-center-to-mouth distance)."""
        left_eye = self.landmarks[0]
        right_eye = self.landmarks[1]
        mouth_center = (self.landmarks[3] + self.landmarks[4]) / 2
        eye_center = (left_eye + right_eye) / 2

        inter_eye = np.linalg.norm(right_eye - left_eye)
        eye_to_mouth = np.linalg.norm(mouth_center - eye_center)
        return float(max(inter_eye, eye_to_mouth))


class FaceDetector:
    """Face detector supporting YuNet (MIT) and SCRFD (legacy) backends.

    When model_path points to a YuNet ONNX file, uses OpenCV DNN directly.
    When model_name is provided, falls back to InsightFace FaceAnalysis (legacy).
    """

    def __init__(
        self,
        model_name: str = "buffalo_l",
        model_path: str | None = None,
        ctx_id: int = 0,
        det_thresh: float = 0.5,
        det_size: tuple[int, int] = (640, 640),
    ):
        self.det_thresh = det_thresh
        self.det_size = det_size
        self._yunet = None
        self._insightface_app = None

        # Prefer YuNet if model_path provided
        if model_path and Path(model_path).exists():
            self._yunet = cv2.FaceDetectorYN.create(
                model_path,
                "",
                det_size,
                det_thresh,
                0.3,  # NMS threshold
                5000,  # top_k
            )
        else:
            # Legacy: use InsightFace
            from insightface.app import FaceAnalysis

            self._insightface_app = FaceAnalysis(
                name=model_name,
                allowed_modules=["detection"],
                providers=_get_providers(ctx_id),
            )
            self._insightface_app.prepare(
                ctx_id=ctx_id, det_thresh=det_thresh, det_size=det_size
            )

    def detect(self, image: np.ndarray, max_faces: int = 0) -> list[DetectedFace]:
        """Detect faces in a BGR image.

        Args:
            image: BGR numpy array (OpenCV format)
            max_faces: Maximum faces to return (0 = unlimited)

        Returns:
            List of DetectedFace sorted by confidence descending.
        """
        if self._yunet is not None:
            return self._detect_yunet(image, max_faces)
        return self._detect_insightface(image, max_faces)

    def _detect_yunet(self, image: np.ndarray, max_faces: int) -> list[DetectedFace]:
        """YuNet detection via OpenCV DNN."""
        h, w = image.shape[:2]
        self._yunet.setInputSize((w, h))
        _, raw = self._yunet.detect(image)

        if raw is None:
            return []

        results = []
        for det in raw:
            # YuNet output: [x, y, w, h, right_eye_x, right_eye_y, left_eye_x, left_eye_y,
            #                 nose_x, nose_y, right_mouth_x, right_mouth_y,
            #                 left_mouth_x, left_mouth_y, confidence]
            x, y, bw, bh = det[0:4]
            confidence = float(det[14])

            bbox = np.array([x, y, x + bw, y + bh], dtype=np.float32)

            # YuNet landmark order: right_eye, left_eye, nose, right_mouth, left_mouth
            # Our order: left_eye, right_eye, nose, left_mouth, right_mouth
            landmarks = np.array(
                [
                    [det[6], det[7]],   # left_eye
                    [det[4], det[5]],   # right_eye
                    [det[8], det[9]],   # nose
                    [det[12], det[13]], # left_mouth
                    [det[10], det[11]], # right_mouth
                ],
                dtype=np.float32,
            )

            aligned = _align_face(image, landmarks)
            results.append(
                DetectedFace(
                    bbox=bbox,
                    landmarks=landmarks,
                    confidence=confidence,
                    aligned=aligned,
                )
            )

        results.sort(key=lambda f: f.confidence, reverse=True)
        if max_faces > 0:
            results = results[:max_faces]
        return results

    def _detect_insightface(self, image: np.ndarray, max_faces: int) -> list[DetectedFace]:
        """Legacy InsightFace SCRFD detection."""
        faces = self._insightface_app.get(image)

        if max_faces > 0:
            faces = sorted(faces, key=lambda f: f.det_score, reverse=True)[:max_faces]

        results = []
        for face in faces:
            aligned = _align_face(image, face.kps)
            results.append(
                DetectedFace(
                    bbox=face.bbox.astype(np.float32),
                    landmarks=face.kps.astype(np.float32),
                    confidence=float(face.det_score),
                    aligned=aligned,
                )
            )

        return sorted(results, key=lambda f: f.confidence, reverse=True)


def _align_face(
    image: np.ndarray, landmarks: np.ndarray, output_size: tuple[int, int] = (112, 112)
) -> np.ndarray:
    """Align face using 5-point landmarks via affine transform."""
    # Standard alignment targets for 112x112
    dst = np.array(
        [
            [38.2946, 51.6963],
            [73.5318, 51.5014],
            [56.0252, 71.7366],
            [41.5493, 92.3655],
            [70.7299, 92.2041],
        ],
        dtype=np.float32,
    )
    src = landmarks.astype(np.float32)
    M = cv2.estimateAffinePartial2D(src, dst)[0]
    if M is None:
        # Fallback: just crop and resize
        x1, y1 = landmarks.min(axis=0).astype(int)
        x2, y2 = landmarks.max(axis=0).astype(int)
        pad = int((x2 - x1) * 0.3)
        h, w = image.shape[:2]
        crop = image[max(0, y1 - pad) : min(h, y2 + pad), max(0, x1 - pad) : min(w, x2 + pad)]
        return cv2.resize(crop, output_size)
    return cv2.warpAffine(image, M, output_size, borderValue=0)


def _get_providers(ctx_id: int) -> list:
    """Select ONNX Runtime providers based on context."""
    if ctx_id >= 0:
        return [
            ("CUDAExecutionProvider", {"device_id": ctx_id}),
            "CPUExecutionProvider",
        ]
    return ["CPUExecutionProvider"]
