"""Bounded private evidence storage with mandatory malware scanning before acceptance."""

import hashlib
import socket
import struct

import boto3
from botocore.config import Config

from .domain import RuleError, require

MAX_EVIDENCE_BYTES = 10 * 1024 * 1024


def capability(cfg):
    """Configuration permits an attempt; it never certifies an engine or file."""
    scanner = bool(cfg.clamav_host)
    private_storage = all((cfg.s3_endpoint, cfg.s3_access_key, cfg.s3_secret_key, cfg.s3_bucket))
    return {
        "upload_attempt_permitted": scanner and private_storage,
        "state": "EXCLUDED_SCANNER_UNAVAILABLE" if not scanner else
                 "EXCLUDED_PRIVATE_STORAGE_UNAVAILABLE" if not private_storage else
                 "CONFIGURED_EACH_FILE_REQUIRES_SCAN",
        "file_dependent_affiliation": "REQUIRES_CURRENT_ACCEPTED_SCANNED_EVIDENCE",
        "scanner_qualification": "NOT_INFERRED_FROM_CONFIGURATION",
        "scan_bypass_permitted": False,
    }


def client(cfg):
    require(
        all((cfg.s3_endpoint, cfg.s3_access_key, cfg.s3_secret_key, cfg.s3_bucket)),
        "AUTHORITY_UNAVAILABLE",
        "Private evidence storage is not configured",
        503,
    )
    return boto3.client(
        "s3",
        endpoint_url=cfg.s3_endpoint,
        aws_access_key_id=cfg.s3_access_key,
        aws_secret_access_key=cfg.s3_secret_key,
        region_name="auto",
        config=Config(connect_timeout=10, read_timeout=30, retries={"max_attempts": 2}),
    )


def scan(cfg, content: bytes):
    require(
        bool(cfg.clamav_host),
        "AUTHORITY_UNAVAILABLE",
        "Evidence malware scanning must be configured before uploads can be accepted",
        503,
    )
    try:
        with socket.create_connection((cfg.clamav_host, cfg.clamav_port), timeout=30) as connection:
            connection.sendall(b"zINSTREAM\0")
            for offset in range(0, len(content), 65536):
                chunk = content[offset : offset + 65536]
                connection.sendall(struct.pack("!I", len(chunk)) + chunk)
            connection.sendall(struct.pack("!I", 0))
            result = b""
            while b"\0" not in result and len(result) < 4096:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                result += chunk
    except OSError as exc:
        raise RuleError(
            "AUTHORITY_UNAVAILABLE",
            "Evidence scanning is unavailable; upload was not accepted",
            503,
        ) from exc
    require(
        result.rstrip(b"\0\n") == b"stream: OK",
        "VALIDATION_FAILED",
        "The evidence did not pass its security scan",
        422,
    )


def store(cfg, key: str, content: bytes, media_type: str):
    signatures = {
        "application/pdf": b"%PDF-",
        "image/png": b"\x89PNG\r\n\x1a\n",
        "image/jpeg": b"\xff\xd8\xff",
    }
    require(
        media_type in signatures and content.startswith(signatures[media_type]),
        "VALIDATION_FAILED",
        "Upload a PDF, PNG or JPEG matching its declared media type",
        422,
    )
    scan(cfg, content)
    storage = client(cfg)
    storage.put_object(
        Bucket=cfg.s3_bucket, Key=key, Body=content, ContentType="application/octet-stream"
    )
    return hashlib.sha256(content).hexdigest()


def read(cfg, key):
    result = client(cfg).get_object(Bucket=cfg.s3_bucket, Key=key)
    try:
        return result["Body"].read(MAX_EVIDENCE_BYTES + 1)
    finally:
        result["Body"].close()
