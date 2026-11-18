"""Track ingested PDFs separately from the Chroma chunk index.

The project does not configure MongoDB. This registry is a JSON file so
document status can be listed without adding a database dependency. One
process should write it. A concurrent writer can overwrite the file.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path


class DocumentNotFound(KeyError):
    """No registry record exists for this document id."""


class DocumentRegistry:
    def __init__(self, path):
        self.path = Path(path)

    def list_documents(self):
        records = self._read()
        return [dict(records[document_id]) for document_id in sorted(records)]

    def get_document(self, document_id):
        records = self._read()
        if document_id not in records:
            raise DocumentNotFound(document_id)
        return dict(records[document_id])

    def remove_document(self, document_id):
        """Drop one registry record. The caller deletes the file and index."""

        records = self._read()
        if document_id not in records:
            raise DocumentNotFound(document_id)
        removed = records.pop(document_id)
        self._write(records)
        return dict(removed)

    def record_success(self, document_id, pdf_path, pages, chunks, embeddings):
        now = _now()
        records = self._read()
        created_at = records.get(document_id, {}).get("created_at", now)
        records[document_id] = {
            "document_id": document_id,
            "filename": Path(pdf_path).name,
            "file_path": str(pdf_path),
            "ingestion_status": "success",
            "total_pages": pages,
            "total_chunks": chunks,
            "total_embeddings": embeddings,
            "created_at": created_at,
            "last_ingestion_at": now,
            "error": None,
        }
        self._write(records)
        return dict(records[document_id])

    def record_failure(self, document_id, pdf_path, error):
        """Record an error without discarding a previous successful index.

        A failed repeat ingestion leaves the last successful status in place
        because the vector index is restored. The error is still saved.
        A document that has never succeeded is marked failed.
        """

        now = _now()
        records = self._read()
        existing = records.get(document_id)
        if existing and existing["ingestion_status"] == "success":
            existing["error"] = str(error)
            existing["last_ingestion_at"] = now
            records[document_id] = existing
        else:
            records[document_id] = {
                "document_id": document_id,
                "filename": Path(pdf_path).name if pdf_path else "",
                "file_path": str(pdf_path) if pdf_path else "",
                "ingestion_status": "failed",
                "total_pages": 0,
                "total_chunks": 0,
                "total_embeddings": 0,
                "created_at": existing["created_at"] if existing else now,
                "last_ingestion_at": now,
                "error": str(error),
            }
        self._write(records)
        return dict(records[document_id])

    def _read(self):
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, records):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(records, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.path)


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
