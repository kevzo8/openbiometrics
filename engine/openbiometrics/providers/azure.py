"""Microsoft Azure Face API provider.

Proxies face operations to Azure Cognitive Services Face API.

pip install openbiometrics-engine[azure]

Usage:
    provider = AzureProvider(
        endpoint="https://your-resource.cognitiveservices.azure.com",
        api_key="your-api-key",
    )
    faces = provider.detect(image_bytes)
    result = provider.compare(image1, image2)

Pricing (2026):
    - Free: 30,000 tx/month
    - Standard: tiered per 1,000 transactions
    - Liveness: separate pricing tier
"""

from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from openbiometrics.providers.base import CloudFaceResult, CloudProvider, CompareResult


class AzureProvider(CloudProvider):
    """Microsoft Azure Face API processing."""

    name = "azure_face"

    def __init__(
        self,
        endpoint: str,
        api_key: str,
    ):
        self._endpoint = endpoint.rstrip("/")
        self._api_key = api_key

    def _request(self, path: str, data: bytes | dict, content_type: str = "application/octet-stream") -> dict:
        """Make a request to Azure Face API."""
        url = f"{self._endpoint}/face/v1.0{path}"
        headers = {"Ocp-Apim-Subscription-Key": self._api_key}

        if isinstance(data, dict):
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
        else:
            body = data
            headers["Content-Type"] = content_type

        req = Request(url, data=body, headers=headers, method="POST")
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())

    def detect(
        self,
        image: bytes,
        *,
        max_faces: int = 10,
        include_demographics: bool = True,
        include_quality: bool = False,
        include_emotions: bool = False,
    ) -> list[CloudFaceResult]:
        params = ["returnFaceId=true"]
        attrs = []
        if include_demographics:
            attrs.extend(["age", "gender"])
        if include_emotions:
            attrs.append("emotion")
        if include_quality:
            attrs.extend(["blur", "exposure", "noise"])
        if attrs:
            params.append(f"returnFaceAttributes={','.join(attrs)}")
        params.append("returnFaceLandmarks=true")

        path = f"/detect?{'&'.join(params)}"

        url = f"{self._endpoint}/face/v1.0{path}"
        headers = {
            "Ocp-Apim-Subscription-Key": self._api_key,
            "Content-Type": "application/octet-stream",
        }
        req = Request(url, data=image, headers=headers, method="POST")
        with urlopen(req, timeout=30) as resp:
            faces = json.loads(resp.read())

        results = []
        for face in faces[:max_faces]:
            rect = face["faceRectangle"]
            # Azure returns absolute pixel coords — we normalize to 0-1 later
            bbox = [
                rect["left"],
                rect["top"],
                rect["left"] + rect["width"],
                rect["top"] + rect["height"],
            ]

            # Landmarks
            landmarks = None
            lm = face.get("faceLandmarks", {})
            if lm:
                landmarks = [
                    [lm.get("pupilLeft", {}).get("x", 0), lm.get("pupilLeft", {}).get("y", 0)],
                    [lm.get("pupilRight", {}).get("x", 0), lm.get("pupilRight", {}).get("y", 0)],
                    [lm.get("noseTip", {}).get("x", 0), lm.get("noseTip", {}).get("y", 0)],
                    [lm.get("mouthLeft", {}).get("x", 0), lm.get("mouthLeft", {}).get("y", 0)],
                    [lm.get("mouthRight", {}).get("x", 0), lm.get("mouthRight", {}).get("y", 0)],
                ]

            # Demographics
            age = None
            gender = None
            emotions = None
            quality_score = None
            fa = face.get("faceAttributes", {})
            if include_demographics:
                age = int(fa.get("age", 0)) if "age" in fa else None
                g = fa.get("gender", "")
                gender = "M" if g == "male" else "F" if g == "female" else None

            if include_emotions and "emotion" in fa:
                emotions = {k: v for k, v in fa["emotion"].items()}

            if include_quality:
                blur = fa.get("blur", {}).get("value", 1.0)
                exposure = fa.get("exposure", {}).get("value", 0.5)
                quality_score = max(0, 1.0 - blur) * min(1.0, exposure * 2)

            results.append(CloudFaceResult(
                bbox=bbox,
                confidence=1.0,  # Azure doesn't return detection confidence
                landmarks=landmarks,
                age=age,
                gender=gender,
                quality_score=quality_score,
                emotions=emotions,
                provider=self.name,
                raw_response=face,
            ))

        return results

    def compare(self, image1: bytes, image2: bytes) -> CompareResult:
        # Azure requires detecting faces first to get faceIds
        faces1 = self.detect(image1, include_demographics=False, max_faces=1)
        faces2 = self.detect(image2, include_demographics=False, max_faces=1)

        if not faces1 or not faces2:
            return CompareResult(is_match=False, similarity=0.0, provider=self.name)

        fid1 = faces1[0].raw_response.get("faceId")
        fid2 = faces2[0].raw_response.get("faceId")

        if not fid1 or not fid2:
            return CompareResult(is_match=False, similarity=0.0, provider=self.name)

        result = self._request("/verify", {"faceId1": fid1, "faceId2": fid2})

        return CompareResult(
            is_match=result.get("isIdentical", False),
            similarity=result.get("confidence", 0.0),
            provider=self.name,
        )

    def check_liveness(self, image: bytes) -> tuple[bool, float]:
        """Azure supports liveness detection via Face Liveness API."""
        # Azure liveness requires a session-based flow (not single-image)
        raise NotImplementedError(
            "Azure liveness requires interactive session flow. "
            "Use OpenBiometrics active liveness presets instead."
        )

    def health(self) -> dict:
        try:
            url = f"{self._endpoint}/face/v1.0/detect?returnFaceId=false"
            headers = {
                "Ocp-Apim-Subscription-Key": self._api_key,
                "Content-Type": "application/json",
            }
            # Minimal request to check connectivity
            req = Request(url, data=b'{"url":"https://example.com/x.jpg"}', headers=headers, method="POST")
            try:
                urlopen(req, timeout=10)
            except HTTPError as e:
                # 400 = API is reachable but image is invalid — that's OK
                if e.code == 400:
                    return {"provider": self.name, "status": "ok", "endpoint": self._endpoint}
                return {"provider": self.name, "status": "error", "error": str(e)}
            return {"provider": self.name, "status": "ok", "endpoint": self._endpoint}
        except Exception as e:
            return {"provider": self.name, "status": "error", "error": str(e)}
