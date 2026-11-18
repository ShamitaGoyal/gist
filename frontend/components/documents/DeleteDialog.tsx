"use client";

import { useEffect, useRef, useState } from "react";

import { useWorkspace } from "@/hooks/useWorkspace";
import type { DocumentSummary } from "@/lib/types";

export function DeleteDialog({
  document,
  onClose,
}: {
  document: DocumentSummary;
  onClose: () => void;
}) {
  const { removeDocument } = useWorkspace();
  const cancelRef = useRef<HTMLButtonElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape" && !deleting) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [deleting, onClose]);

  async function confirm() {
    setDeleting(true);
    setError(null);
    try {
      await removeDocument(document.document_id);
      onClose();
    } catch (caught) {
      setDeleting(false);
      setError(caught instanceof Error ? caught.message : "Document deletion could not be completed.");
    }
  }

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-ink/10 px-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-document-title"
        className="w-full max-w-sm rounded-xl border border-line bg-surface p-4"
      >
        <h2 id="delete-document-title" className="text-base font-normal tracking-[-0.011em] text-ink">
          Delete this document?
        </h2>
        <p className="mt-2 text-sm leading-6 text-secondary">
          {document.filename} will be removed from the library, the reader, and the index.
        </p>
        {error ? <p className="mt-3 text-sm text-danger">{error}</p> : null}
        <div className="mt-4 flex justify-end gap-2">
          <button
            ref={cancelRef}
            type="button"
            onClick={onClose}
            disabled={deleting}
            className="h-8 rounded-lg border border-line bg-surface px-3 text-sm text-ink"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={confirm}
            disabled={deleting}
            className="h-8 rounded-lg bg-ink px-3 text-sm font-medium text-on-ink disabled:bg-selected disabled:text-disabled"
          >
            {deleting ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}
