"""Face recognition embedding extraction.

Supports two backends (auto-detected from model input shape):
- SFace (OpenCV Zoo): Apache 2.0, 99.4% LFW, MobileFaceNet architecture (default)
- ArcFace (InsightFace): higher accuracy but non-commercial license (legacy)

Both produce L2-normalized embeddings compatible with cosine similarity.
"""

import cv2
import numpy as np

from openbiometrics.runtime.session import OnnxModelSession


class FaceRecognizer:
    """Face embedding extractor supporting SFace and ArcFace models."""

    def __init__(self, model_path: str, ctx_id: int = 0):
        """
        Args:
            model_path: Path to .onnx recognition model
            ctx_id: GPU device ID (-1 for CPU)
        """
        self._model = OnnxModelSession(model_path, ctx_id=ctx_id)
        self.session = self._model.session
        self.input_name = self._model.input_name
        self.input_shape = self._model.input_shape  # e.g. [1, 3, 112, 112]

        # Auto-detect: SFace outputs 2 tensors (features + ?), ArcFace outputs 1
        output_count = len(self.session.get_outputs())
        self._is_sface = output_count >= 2

    def get_embedding(self, aligned_face: np.ndarray) -> np.ndarray:
        """Extract normalized embedding from a 112x112 aligned face.

        Args:
            aligned_face: BGR 112x112 aligned face image

        Returns:
            Normalized float32 embedding vector
        """
        blob = _preprocess(aligned_face)
        outputs = self._model.run(blob)

        # SFace: first output is the embedding
        embedding = outputs[0][0]

        # L2 normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding.astype(np.float32)

    def get_embeddings_batch(self, aligned_faces: list[np.ndarray]) -> list[np.ndarray]:
        """Extract embeddings for a batch of aligned faces."""
        if not aligned_faces:
            return []
        batch = np.concatenate([_preprocess(f) for f in aligned_faces], axis=0)
        embeddings = self._model.run(batch)[0]
        # L2 normalize each
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-10)
        embeddings = embeddings / norms
        return [e.astype(np.float32) for e in embeddings]

    @staticmethod
    def compare(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Cosine similarity between two embeddings. Returns [-1, 1]."""
        return float(np.dot(embedding1, embedding2))

    @staticmethod
    def compare_to_threshold(similarity: float, threshold: float = 0.4) -> bool:
        """Check if similarity exceeds verification threshold.

        Default threshold 0.4 works for both SFace and ArcFace models.
        Adjust based on your security requirements.
        """
        return similarity >= threshold


def _preprocess(aligned_face: np.ndarray) -> np.ndarray:
    """Preprocess aligned face for inference.

    Args:
        aligned_face: BGR uint8 [112, 112, 3]

    Returns:
        Float32 blob [1, 3, 112, 112], normalized to [-1, 1]
    """
    img = aligned_face.astype(np.float32)
    # Normalize to [-1, 1]
    img = (img - 127.5) / 127.5
    # HWC -> CHW -> NCHW
    img = img.transpose(2, 0, 1)[np.newaxis, ...]
    return img
