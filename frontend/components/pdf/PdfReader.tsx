"use client";

import { ChevronLeft, ChevronRight, Minus, Plus, UnfoldHorizontal } from "lucide-react";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

import { UploadPrompt } from "@/components/documents/UploadPrompt";
import { useWorkspace } from "@/hooks/useWorkspace";
import { fetchDocumentFile } from "@/lib/api";

const PdfViewer = dynamic(
  () => import("@/components/pdf/PdfViewer").then((mod) => mod.PdfViewer),
  { ssr: false },
);

export function PdfReader() {
  const {
    selected,
    page,
    pdfPageCount,
    setPdfPageCount,
    scrollToken,
    goToPage,
    noteVisiblePage,
    showPreviousPage,
    showNextPage,
    selectedSource,
    newChat,
  } = useWorkspace();
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [phase, setPhase] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [fitWidth, setFitWidth] = useState(true);
  const [scale, setScale] = useState(1);
  const [pageDraft, setPageDraft] = useState("1");

  useEffect(() => {
    setPageDraft(String(page));
  }, [page]);

  useEffect(() => {
    if (!selected) {
      setFileUrl(null);
      setPhase("idle");
      setError(null);
      return;
    }
    const controller = new AbortController();
    let cancelled = false;
    let objectUrl = "";
    setPhase("loading");
    setError(null);
    setFileUrl(null);
    fetchDocumentFile(selected.document_id, controller.signal)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setFileUrl(objectUrl);
        setPhase("ready");
      })
      .catch((caught: unknown) => {
        if (cancelled || controller.signal.aborted) return;
        setPhase("error");
        setError(caught instanceof Error ? caught.message : "The PDF could not be opened.");
      });
    return () => {
      cancelled = true;
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [selected]);

  const highlightedPage =
    selectedSource && selectedSource.documentId === selected?.document_id
      ? selectedSource.pageNumber
      : null;

  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col bg-white">
      <div className="flex h-11 shrink-0 items-center gap-2 border-b border-line-subtle px-3">
        <p className="min-w-0 flex-1 truncate text-sm text-ink">
          {selected ? selected.filename : "No document selected"}
        </p>
        <button
          type="button"
          aria-label="Previous page"
          onClick={showPreviousPage}
          disabled={!selected || page <= 1}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-secondary hover:bg-hover disabled:text-disabled"
        >
          <ChevronLeft className="h-4 w-4" strokeWidth={1.5} />
        </button>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const next = Number(pageDraft);
            if (Number.isInteger(next) && next >= 1 && (pdfPageCount === 0 || next <= pdfPageCount)) {
              goToPage(next);
            } else {
              setPageDraft(String(page));
            }
          }}
        >
          <input
            aria-label="Page number"
            value={pageDraft}
            onChange={(event) => setPageDraft(event.target.value)}
            className="h-8 w-12 rounded-lg border border-line bg-surface text-center text-sm"
          />
        </form>
        <span className="text-xs text-muted" data-current-page={page} data-page-count={pdfPageCount}>
          / {pdfPageCount || "–"}
        </span>
        <button
          type="button"
          aria-label="Next page"
          onClick={showNextPage}
          disabled={!selected || (pdfPageCount > 0 && page >= pdfPageCount)}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-secondary hover:bg-hover disabled:text-disabled"
        >
          <ChevronRight className="h-4 w-4" strokeWidth={1.5} />
        </button>
        <span className="mx-1 h-4 w-px bg-line" />
        <button
          type="button"
          aria-label="Zoom out"
          onClick={() => {
            setFitWidth(false);
            setScale((current) => Math.max(0.6, Number((current - 0.15).toFixed(2))));
          }}
          disabled={!selected}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-secondary hover:bg-hover disabled:text-disabled"
        >
          <Minus className="h-4 w-4" strokeWidth={1.5} />
        </button>
        <span className="w-12 text-center text-xs text-muted">{fitWidth ? "Fit" : `${Math.round(scale * 100)}%`}</span>
        <button
          type="button"
          aria-label="Zoom in"
          onClick={() => {
            setFitWidth(false);
            setScale((current) => Math.min(2.5, Number((current + 0.15).toFixed(2))));
          }}
          disabled={!selected}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-secondary hover:bg-hover disabled:text-disabled"
        >
          <Plus className="h-4 w-4" strokeWidth={1.5} />
        </button>
        <button
          type="button"
          aria-label="Fit to width"
          aria-pressed={fitWidth}
          onClick={() => setFitWidth(true)}
          disabled={!selected}
          className={`flex h-8 w-8 items-center justify-center rounded-lg hover:bg-hover disabled:text-disabled ${fitWidth ? "bg-selected text-ink" : "text-secondary"}`}
        >
          <UnfoldHorizontal className="h-4 w-4" strokeWidth={1.5} />
        </button>
      </div>
      {selectedSource && selectedSource.documentId === selected?.document_id ? (
        <p className="truncate border-b border-line-subtle px-3 py-1.5 text-xs text-secondary">
          Source <span className="font-mono text-ink">{selectedSource.chunkId}</span>
          {selectedSource.pageNumber ? ` · Page ${selectedSource.pageNumber}` : ""}
          {selectedSource.sourceType === "ocr_figure" ? " · Figure OCR" : ""}
        </p>
      ) : null}
      {!selected && newChat ? <UploadPrompt /> : null}
      {!selected && !newChat ? (
        <div className="flex flex-1 items-center justify-center px-6">
          <p className="max-w-sm text-center text-sm leading-6 text-secondary">
            Choose a recent chat, or press + to start a new one.
          </p>
        </div>
      ) : null}
      {phase === "loading" ? <p className="px-6 py-6 text-sm text-muted">Opening document…</p> : null}
      {error ? <p className="px-6 py-3 text-sm text-danger">{error}</p> : null}
      {phase === "ready" && fileUrl ? (
        <PdfViewer
          fileUrl={fileUrl}
          page={page}
          scrollToken={scrollToken}
          fitWidth={fitWidth}
          scale={scale}
          highlightedPage={highlightedPage}
          onVisiblePage={noteVisiblePage}
          onPageCount={setPdfPageCount}
          onError={setError}
        />
      ) : null}
    </section>
  );
}
