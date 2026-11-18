"use client";

import { FileUp } from "lucide-react";
import { useRef, useState } from "react";

import { uploadDocument } from "@/lib/api";
import { formatBytes } from "@/lib/format";
import { useWorkspace } from "@/hooks/useWorkspace";

type PendingFile = {
  file: File;
  error: string | null;
  uploading: boolean;
};

export function UploadControl() {
  const inputRef = useRef<HTMLInputElement>(null);
  const { refreshDocuments, selectDocument } = useWorkspace();
  const [pending, setPending] = useState<PendingFile | null>(null);

  function chooseFile(file: File | null) {
    if (!file) return;
    const looksLikePdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    if (!looksLikePdf) {
      setPending({ file, error: "Only PDF files can be uploaded.", uploading: false });
      return;
    }
    if (file.size === 0) {
      setPending({ file, error: "The uploaded file is empty.", uploading: false });
      return;
    }
    setPending({ file, error: null, uploading: false });
  }

  async function startUpload() {
    if (!pending || pending.error || pending.uploading) return;
    setPending({ ...pending, uploading: true, error: null });
    try {
      const uploaded = await uploadDocument(pending.file);
      await refreshDocuments();
      selectDocument(uploaded.document_id);
      setPending(null);
      if (inputRef.current) inputRef.current.value = "";
    } catch (error) {
      setPending({
        ...pending,
        uploading: false,
        error: error instanceof Error ? error.message : "Ingestion failed.",
      });
    }
  }

  return (
    <div className="px-3">
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        className="sr-only"
        aria-label="Choose a PDF"
        onChange={(event) => chooseFile(event.target.files?.[0] ?? null)}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        className="flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-ink text-sm font-medium text-on-ink hover:bg-ink-hover"
      >
        <FileUp className="h-4 w-4" strokeWidth={1.5} />
        Upload PDF
      </button>
      {pending ? (
        <div className="mt-3 rounded-lg border border-line bg-surface p-3">
          <p className="truncate text-sm text-ink">{pending.file.name}</p>
          <p className="mt-1 text-xs text-muted">{formatBytes(pending.file.size)}</p>
          {pending.error ? <p className="mt-2 text-sm text-danger">{pending.error}</p> : null}
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={startUpload}
              disabled={Boolean(pending.error) || pending.uploading}
              className="h-8 rounded-lg bg-ink px-3 text-sm font-medium text-on-ink disabled:bg-selected disabled:text-disabled"
            >
              {pending.uploading ? "Ingesting…" : "Upload"}
            </button>
            <button
              type="button"
              onClick={() => {
                setPending(null);
                if (inputRef.current) inputRef.current.value = "";
              }}
              disabled={pending.uploading}
              className="h-8 rounded-lg border border-line bg-surface px-3 text-sm text-ink disabled:text-disabled"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
