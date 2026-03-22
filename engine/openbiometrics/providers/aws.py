"""Amazon Rekognition provider.

Proxies face operations to AWS Rekognition. Requires boto3 and AWS credentials.

pip install openbiometrics-engine[aws]

Usage:
    provider = AWSProvider(region="us-east-1")
    faces = provider.detect(image_bytes)
    result = provider.compare(image1, image2)

Pricing (2026):
    - $0.001/image (first 1M)
    - $0.0008/image (1-5M)
    - $0.0006/image (5-35M)
    - Face storage: $0.00001/face/month
"""

from __future__ import annotations

from openbiometrics.providers.base import CloudFaceResult, CloudProvider, CompareResult


class AWSProvider(CloudProvider):
    """Amazon Rekognition face processing."""

    name = "aws_rekognition"

    def __init__(
        self,
        region: str = "us-east-1",
        access_key: str | None = None,
        secret_key: str | None = None,
        collection_id: str | None = None,
    ):
        try:
            import boto3
        except ImportError:
            raise ImportError(
                "AWS provider requires boto3. Install with: "
                "pip install openbiometrics-engine[aws]"
            )

        kwargs = {"region_name": region}
        if access_key and secret_key:
            kwargs["aws_access_key_id"] = access_key
            kwargs["aws_secret_access_key"] = secret_key

        self._client = boto3.client("rekognition", **kwargs)
        self._collection_id = collection_id
        self._region = region

    def detect(
        self,
        image: bytes,
        *,
        max_faces: int = 10,
        include_demographics: bool = True,
        include_quality: bool = False,
        include_emotions: bool = False,
    ) -> list[CloudFaceResult]:
        attributes = ["DEFAULT"]
        if include_demographics or include_emotions:
            attributes = ["ALL"]

        resp = self._client.detect_faces(
            Image={"Bytes": image},
            Attributes=attributes,
        )

        results = []
        for detail in resp.get("FaceDetails", [])[:max_faces]:
            bb = detail["BoundingBox"]
            bbox = [
                bb["Left"],
                bb["Top"],
                bb["Left"] + bb["Width"],
                bb["Top"] + bb["Height"],
            ]

            # Landmarks
            landmarks = None
            if detail.get("Landmarks"):
                lm_map = {lm["Type"]: [lm["X"], lm["Y"]] for lm in detail["Landmarks"]}
                landmarks = [
                    lm_map.get("eyeLeft", [0, 0]),
                    lm_map.get("eyeRight", [0, 0]),
                    lm_map.get("nose", [0, 0]),
                    lm_map.get("mouthLeft", [0, 0]),
                    lm_map.get("mouthRight", [0, 0]),
                ]

            # Demographics
            age = None
            gender = None
            if include_demographics:
                age_range = detail.get("AgeRange", {})
                if age_range:
                    age = (age_range.get("Low", 0) + age_range.get("High", 0)) // 2
                gender_info = detail.get("Gender", {})
                if gender_info:
                    gender = "M" if gender_info.get("Value") == "Male" else "F"

            # Emotions
            emotions = None
            if include_emotions and detail.get("Emotions"):
                emotions = {
                    e["Type"].lower(): e["Confidence"] / 100.0
                    for e in detail["Emotions"]
                }

            # Quality
            quality_score = None
            if include_quality and detail.get("Quality"):
                q = detail["Quality"]
                quality_score = min(q.get("Sharpness", 0), q.get("Brightness", 0)) / 100.0

            results.append(CloudFaceResult(
                bbox=bbox,
                confidence=detail.get("Confidence", 0) / 100.0,
                landmarks=landmarks,
                age=age,
                gender=gender,
                quality_score=quality_score,
                emotions=emotions,
                provider=self.name,
                raw_response=detail,
            ))

        return results

    def compare(self, image1: bytes, image2: bytes) -> CompareResult:
        resp = self._client.compare_faces(
            SourceImage={"Bytes": image1},
            TargetImage={"Bytes": image2},
            SimilarityThreshold=0.0,  # Return all, let caller decide
        )

        matches = resp.get("FaceMatches", [])
        if not matches:
            return CompareResult(is_match=False, similarity=0.0, provider=self.name)

        best = max(matches, key=lambda m: m["Similarity"])
        similarity = best["Similarity"] / 100.0

        return CompareResult(
            is_match=similarity >= 0.8,
            similarity=similarity,
            provider=self.name,
        )

    def health(self) -> dict:
        try:
            self._client.describe_collection(CollectionId="__health_check__")
        except self._client.exceptions.ResourceNotFoundException:
            return {"provider": self.name, "status": "ok", "region": self._region}
        except Exception as e:
            error_name = type(e).__name__
            if "AccessDenied" in error_name or "ResourceNotFound" in error_name:
                return {"provider": self.name, "status": "ok", "region": self._region}
            return {"provider": self.name, "status": "error", "error": str(e)}
        return {"provider": self.name, "status": "ok", "region": self._region}
