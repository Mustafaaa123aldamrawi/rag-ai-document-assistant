from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any


def _safe(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "")).strip("._")
    return value or "file"


class LocalArtifactStore:
    mode = "local"

    def __init__(self, root: str | os.PathLike[str] = "data/artifacts"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, *, key: str, payload: bytes, content_type: str) -> dict:
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        return {
            "mode": self.mode,
            "key": key,
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "content_type": content_type,
        }


class S3ArtifactStore:
    mode = "s3"

    def __init__(self, *, bucket: str, region: str | None = None, endpoint_url: str | None = None):
        import boto3

        self.bucket = bucket
        self.client = boto3.client("s3", region_name=region or None, endpoint_url=endpoint_url or None)

    def put_bytes(self, *, key: str, payload: bytes, content_type: str) -> dict:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=payload,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )
        return {
            "mode": self.mode,
            "bucket": self.bucket,
            "key": key,
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "content_type": content_type,
        }


def create_artifact_store():
    mode = os.getenv("AVIA_STORAGE_MODE", "local").strip().lower()
    if mode == "s3":
        bucket = os.getenv("AVIA_STORAGE_BUCKET", "").strip()
        if not bucket:
            raise RuntimeError("AVIA_STORAGE_BUCKET is required when AVIA_STORAGE_MODE=s3.")
        return S3ArtifactStore(
            bucket=bucket,
            region=os.getenv("AVIA_STORAGE_REGION", "").strip() or None,
            endpoint_url=os.getenv("AVIA_STORAGE_ENDPOINT", "").strip() or None,
        )
    return LocalArtifactStore(os.getenv("AVIA_STORAGE_PATH", "data/artifacts"))


def drawing_artifact_key(owner_id: str, project_id: str, filename: str, digest: str) -> str:
    return f"users/{_safe(owner_id)}/projects/{_safe(project_id)}/drawings/{digest[:16]}-{_safe(filename)}"


def report_artifact_key(owner_id: str, project_id: str, period: str, filename: str) -> str:
    return f"users/{_safe(owner_id)}/projects/{_safe(project_id)}/reports/{_safe(period)}/{_safe(filename)}"
