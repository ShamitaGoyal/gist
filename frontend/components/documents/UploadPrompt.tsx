"use client";

import { FileUp } from "lucide-react";
import { useRef } from "react";

import { IngestProgress } from "@/components/documents/IngestProgress";
import { useWorkspace } from "@/hooks/useWorkspace";

export function UploadPrompt() {
  const inputRef = useRef<HTMLInputElement>(null);
  const { ingest, uploadPdf, clearIngest, groups, activeGroupId } = useWorkspace();
  const busy = Boolean(ingest?.active);
  const groupName = groups.find((group) => group.id === activeGroupId)?.name;

  return (
    <div className="flex flex-1 items-center justify-center px-8">
      <div className="w-full max-w-md text-center">
        <h2 className="text-2xl font-normal tracking-[-0.02em] text-ink">Upload a PDF to start this chat</h2>
        <p className="mx-auto mt-3 max-w-sm text-sm leading-6 text-secondary">
          {groupName
            ? `This chat will be saved in ${groupName}. Choose a PDF and Gist will ingest it before you ask a question.`
            : "A new chat reads one document. Choose a PDF and Gist will ingest it before you ask a question."}
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          className="sr-only"
          aria-label="Choose a PDF"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void uploadPdf(file);
            event.target.value = "";
          }}
        />
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={busy}
          className="mx-auto mt-6 flex h-10 items-center gap-2 rounded-full bg-ink px-4 text-sm font-medium text-on-ink hover:bg-ink-hover disabled:bg-selected disabled:text-disabled"
        >
          <FileUp className="h-4 w-4" strokeWidth={1.5} />
          Choose PDF
        </button>
        {ingest ? (
          <div className="mt-8 text-left">
            <IngestProgress ingest={ingest} />
            {ingest.error ? (
              <button type="button" onClick={clearIngest} className="mt-3 text-sm text-secondary hover:text-ink">
                Dismiss
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
