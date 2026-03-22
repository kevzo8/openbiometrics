"""Age and gender estimation from face images.

Supports two backends:
- ViT (Vision Transformer): 94.3% gender accuracy, 4.5yr age MAE (default, recommended)
- InsightFace genderage: lighter but less accurate (legacy)

The backend is auto-detected from the model's input shape.
"""

import cv2
import numpy as np

from openbiometrics.runtime.session import OnnxModelSession


class DemographicsEstimator:
    """Estimate age and gender from aligned face images."""

    def __init__(self, model_path: str, ctx_id: int = 0):
        self._model = OnnxModelSession(model_path, ctx_id=ctx_id)
        self.session = self._model.session
        self.input_name = self._model.input_name
        self.input_size = (self._model.input_shape[3], self._model.input_shape[2])  # (W, H)

        # Auto-detect backend from input shape: ViT uses 224x224, InsightFace uses 96x96
        self._is_vit = self.input_size[0] >= 224

    def estimate(self, aligned_face: np.ndarray) -> tuple[int, str]:
        """Estimate age and gender from an aligned face.

        Args:
            aligned_face: BGR aligned face (any size, will be resized)

        Returns:
            (age, gender) where gender is "M" or "F"
        """
        if self._is_vit:
            return self._estimate_vit(aligned_face)
        return self._estimate_insightface(aligned_face)

    def _estimate_vit(self, aligned_face: np.ndarray) -> tuple[int, str]:
        """ViT-base model: dual-head age regression + gender classification."""
        img = cv2.resize(aligned_face, self.input_size)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        blob = img.astype(np.float32) / 255.0
        # ImageNet normalization
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        blob = (blob - mean) / std
        blob = blob.transpose(2, 0, 1)[np.newaxis, ...]

        output = self._model.run(blob)[0][0]

        # ViT output: [age_logit, gender_logit]
        age = int(np.clip(np.round(output[0]), 0, 100))
        gender = "F" if output[1] >= 0.5 else "M"

        return age, gender

    def _estimate_insightface(self, aligned_face: np.ndarray) -> tuple[int, str]:
        """InsightFace genderage model (legacy)."""
        img = cv2.resize(aligned_face, self.input_size)
        blob = img.astype(np.float32)
        blob = (blob - 127.5) / 127.5
        blob = blob.transpose(2, 0, 1)[np.newaxis, ...]

        output = self._model.run(blob)[0][0]

        gender = "F" if output[0] > output[1] else "M"
        age = int(np.round(output[2] * 100))

        return age, gender
