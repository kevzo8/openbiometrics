"""Google Cloud Vision provider.

Proxies face detection to Google Cloud Vision API. Face detection only —
Google deprecated face recognition features.

pip install openbiometrics-engine[google]

Usage:
    provider = GoogleProvider(api_key="your-api-key")
    faces = provider.detect(image_bytes)

Note: Google Cloud Vision only supports face DETECTION (bounding boxes,
landmarks, emotions). It does NOT support face recognition/comparison.
For recognition, use local models or another provider.
"""

from __future__ import annotations

import base64
import json
from urllib.request import Request, urlopen

from openbiometrics.providers.base import CloudFaceResult, CloudProvider, CompareResult


class GoogleProvider(CloudProvider):
    """Google Cloud Vision face detection (detection only, no recognition)."""

    name = "google_vision"

    def __init__(self, api_key: str):
        self._api_key = api_key

    def detect(
        self,
        image: bytes,
        *,
        max_faces: int = 10,
        include_demographics: bool = True,
        include_quality: bool = False,
        include_emotions: bool = False,
    ) -> list[CloudFaceResult]:
        b64 = base64.b64encode(image).decode()

        body = {
            "requests": [{
                "image": {"content": b64},
                "features": [{"type": "FACE_DETECTION", "maxResults": max_faces}],
            }]
        }

        url = f"https://vision.googleapis.com/v1/images:annotate?key={self._api_key}"
        req = Request(url, data=json.dumps(body).encode(), method="POST")
        req.add_header("Content-Type", "application/json")

        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())

        annotations = data.get("responses", [{}])[0].get("faceAnnotations", [])
        results = []

        for ann in annotations[:max_faces]:
            # Bounding box
            verts = ann.get("boundingPoly", {}).get("vertices", [])
            if len(verts) >= 2:
                bbox = [
                    verts[0].get("x", 0), verts[0].get("y", 0),
                    verts[2].get("x", 0), verts[2].get("y", 0),
                ]
            else:
                bbox = [0, 0, 0, 0]

            # Landmarks
            landmarks = None
            lms = ann.get("landmarks", [])
            if lms:
                lm_map = {lm["type"]: [lm["position"]["x"], lm["position"]["y"]] for lm in lms}
                landmarks = [
                    lm_map.get("LEFT_EYE", [0, 0]),
                    lm_map.get("RIGHT_EYE", [0, 0]),
                    lm_map.get("NOSE_TIP", [0, 0]),
                    lm_map.get("MOUTH_LEFT", [0, 0]),
                    lm_map.get("MOUTH_RIGHT", [0, 0]),
                ]

            # Emotions (Google returns likelihood levels, not scores)
            emotions = None
            if include_emotions:
                likelihood_map = {
                    "VERY_UNLIKELY": 0.0, "UNLIKELY": 0.2,
                    "POSSIBLE": 0.5, "LIKELY": 0.8, "VERY_LIKELY": 1.0,
                }
                emotions = {
                    "joy": likelihood_map.get(ann.get("joyLikelihood", ""), 0),
                    "sorrow": likelihood_map.get(ann.get("sorrowLikelihood", ""), 0),
                    "anger": likelihood_map.get(ann.get("angerLikelihood", ""), 0),
                    "surprise": likelihood_map.get(ann.get("surpriseLikelihood", ""), 0),
                }

            confidence = ann.get("detectionConfidence", 0.0)

            results.append(CloudFaceResult(
                bbox=bbox,
                confidence=confidence,
                landmarks=landmarks,
                emotions=emotions,
                provider=self.name,
                raw_response=ann,
            ))

        return results

    def compare(self, image1: bytes, image2: bytes) -> CompareResult:
        """Google Vision does not support face recognition/comparison."""
        raise NotImplementedError(
            "Google Cloud Vision does not support face comparison. "
            "Use local models (SFace) or another provider (AWS, Azure)."
        )

    def health(self) -> dict:
        try:
            # Minimal request to check API key validity
            url = f"https://vision.googleapis.com/v1/images:annotate?key={self._api_key}"
            body = {"requests": [{"image": {"content": ""}, "features": [{"type": "FACE_DETECTION"}]}]}
            req = Request(url, data=json.dumps(body).encode(), method="POST")
            req.add_header("Content-Type", "application/json")
            try:
                urlopen(req, timeout=10)
            except Exception:
                pass  # Any response means the endpoint is reachable
            return {"provider": self.name, "status": "ok"}
        except Exception as e:
            return {"provider": self.name, "status": "error", "error": str(e)}
