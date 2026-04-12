"""
storage.py — Abstração de armazenamento de arquivos.

Em produção (S3_BUCKET definido): usa Amazon S3 via boto3.
Em desenvolvimento / sem S3_BUCKET: usa sistema de arquivos local.

Uso:
    from services.storage import storage

    key = storage.save(content_bytes, "prefixo/nome.xlsx")
    data = storage.load(key)
    storage.delete(key)
"""

from __future__ import annotations

import io
import os


class _LocalStorage:
    """Armazenamento local em disco (desenvolvimento)."""

    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def _path(self, key: str) -> str:
        # Evita path traversal: só permite o nome base
        filename = os.path.basename(key)
        return os.path.join(self.base_dir, filename)

    def save(self, data: bytes, key: str) -> str:
        path = self._path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return key

    def load(self, key: str) -> bytes:
        path = self._path(key)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Arquivo não encontrado: {key}")
        with open(path, "rb") as f:
            return f.read()

    def exists(self, key: str) -> bool:
        return os.path.exists(self._path(key))

    def delete(self, key: str) -> None:
        path = self._path(key)
        if os.path.exists(path):
            os.remove(path)

    def local_path(self, key: str) -> str | None:
        """Retorna o caminho local do arquivo (apenas para LocalStorage)."""
        return self._path(key)


class _S3Storage:
    """Armazenamento no Amazon S3 (produção)."""

    def __init__(self, bucket: str, prefix: str = "") -> None:
        import boto3  # type: ignore[import-untyped]
        self.bucket = bucket
        self.prefix = prefix.rstrip("/")
        self.client = boto3.client(
            "s3",
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
        )

    def _s3_key(self, key: str) -> str:
        filename = os.path.basename(key)
        return f"{self.prefix}/{filename}" if self.prefix else filename

    def save(self, data: bytes, key: str) -> str:
        s3_key = self._s3_key(key)
        self.client.put_object(
            Bucket=self.bucket,
            Key=s3_key,
            Body=data,
            ServerSideEncryption="AES256",
        )
        return key

    def load(self, key: str) -> bytes:
        s3_key = self._s3_key(key)
        obj = self.client.get_object(Bucket=self.bucket, Key=s3_key)
        return obj["Body"].read()

    def exists(self, key: str) -> bool:
        import botocore.exceptions  # type: ignore[import-untyped]
        s3_key = self._s3_key(key)
        try:
            self.client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except botocore.exceptions.ClientError:
            return False

    def delete(self, key: str) -> None:
        s3_key = self._s3_key(key)
        self.client.delete_object(Bucket=self.bucket, Key=s3_key)

    def local_path(self, key: str) -> str | None:
        """S3 não tem caminho local — retorna None."""
        return None

    def download_to_temp(self, key: str) -> str:
        """Baixa o objeto S3 para um arquivo temporário e retorna o caminho."""
        import tempfile
        data = self.load(key)
        suffix = os.path.splitext(key)[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            return tmp.name


def _build_storage() -> _LocalStorage | _S3Storage:
    bucket = os.environ.get("S3_BUCKET", "")
    if bucket:
        prefix = os.environ.get("S3_PREFIX", "controllo")
        print(f"[CONTROLLO] Storage: S3 bucket='{bucket}' prefix='{prefix}'")
        return _S3Storage(bucket=bucket, prefix=prefix)
    print("[CONTROLLO] Storage: sistema de arquivos local.")
    return _LocalStorage(base_dir="outputs")


# Instância global — use `from services.storage import storage`
storage: _LocalStorage | _S3Storage = _build_storage()
