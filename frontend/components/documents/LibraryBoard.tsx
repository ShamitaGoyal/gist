"use client";

import { FileText, Highlighter, Pencil, Search, StickyNote } from "lucide-react";
import { useMemo, useRef, useState, type ReactNode } from "react";

import { useWorkspace } from "@/hooks/useWorkspace";
import { formatAddedDate } from "@/lib/format";
import type { DocumentSummary } from "@/lib/types";

type LibraryTab = "sources" | "notes" | "annotations";

export function LibraryBoard() {
  const {
    documents,
    documentsStatus,
    documentsError,
    refreshDocuments,
    selectDocument,
    renameDocument,
    setSection,
    setPanel,
    setChatOpen,
  } = useWorkspace();
  const [tab, setTab] = useState<LibraryTab>("sources");
  const [query, setQuery] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftName, setDraftName] = useState("");
  const [renameError, setRenameError] = useState<string | null>(null);

  const items = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return [...documents]
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
      .filter((document) => !needle || document.filename.toLowerCase().includes(needle));
  }, [documents, query]);

  function openDocument(documentId: string) {
    selectDocument(documentId);
    setPanel("chat");
    setChatOpen(true);
  }

  function beginRename(document: DocumentSummary) {
    setEditingId(document.document_id);
    setDraftName(document.filename.replace(/\.pdf$/i, ""));
    setRenameError(null);
  }

  async function saveRename(documentId: string) {
    const next = draftName.trim();
    if (!next) {
      setRenameError("Enter a document name.");
      return;
    }
    try {
      await renameDocument(documentId, next);
      setEditingId(null);
      setRenameError(null);
    } catch (error) {
      setRenameError(error instanceof Error ? error.message : "The name could not be saved.");
    }
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col bg-white">
      <div className="px-8 pt-6">
        <p className="text-sm text-muted">
          <button type="button" onClick={() => setSection("home")} className="hover:text-ink">
            Home
          </button>
          <span className="px-1.5">/</span>
          <span className="text-secondary">Library</span>
        </p>
        <h1 className="mt-3 text-[28px] font-normal tracking-[-0.03em] text-ink">Library</h1>
      </div>

      <div className="mt-5 flex items-end justify-between gap-4 border-b border-line-subtle px-8">
        <div className="flex items-center gap-6">
          <TabButton active={tab === "sources"} onClick={() => setTab("sources")} icon={<FileText className="h-4 w-4" strokeWidth={1.5} />} label="Sources" />
          <TabButton active={tab === "notes"} onClick={() => setTab("notes")} icon={<StickyNote className="h-4 w-4" strokeWidth={1.5} />} label="Notes" />
          <TabButton active={tab === "annotations"} onClick={() => setTab("annotations")} icon={<Highlighter className="h-4 w-4" strokeWidth={1.5} />} label="Annotations" />
        </div>
        <label className="mb-2 flex h-9 w-full max-w-xs items-center gap-2 rounded-full border border-line bg-white px-3 text-muted">
          <Search className="h-4 w-4 shrink-0" strokeWidth={1.5} />
          <span className="sr-only">Search library</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search"
            className="w-full border-0 bg-transparent text-sm text-ink outline-none placeholder:text-muted"
          />
        </label>
      </div>

      <div className="min-h-0 flex-1 overflow-auto px-6 py-2">
        {tab === "sources" ? (
          <Sources
            items={items}
            status={documentsStatus}
            error={documentsError}
            query={query}
            editingId={editingId}
            draftName={draftName}
            renameError={renameError}
            onRetry={() => refreshDocuments().catch(() => undefined)}
            onOpen={openDocument}
            onBeginRename={beginRename}
            onDraftName={setDraftName}
            onSave={saveRename}
            onCancel={() => {
              setEditingId(null);
              setRenameError(null);
            }}
          />
        ) : null}
        {tab === "notes" ? (
          <EmptyCopy>Notes you write about a document will show up here.</EmptyCopy>
        ) : null}
        {tab === "annotations" ? (
          <EmptyCopy>Annotations you add on a document will show up here.</EmptyCopy>
        ) : null}
      </div>
    </section>
  );
}

function Sources({
  items,
  status,
  error,
  query,
  editingId,
  draftName,
  renameError,
  onRetry,
  onOpen,
  onBeginRename,
  onDraftName,
  onSave,
  onCancel,
}: {
  items: DocumentSummary[];
  status: string;
  error: string | null;
  query: string;
  editingId: string | null;
  draftName: string;
  renameError: string | null;
  onRetry: () => void;
  onOpen: (documentId: string) => void;
  onBeginRename: (document: DocumentSummary) => void;
  onDraftName: (value: string) => void;
  onSave: (documentId: string) => void;
  onCancel: () => void;
}) {
  const skipSave = useRef(false);
  if (status === "loading") return <p className="px-2 py-6 text-sm text-muted">Loading documents…</p>;
  if (status === "error") {
    return (
      <div className="px-2 py-6">
        <p className="text-sm text-danger">{error}</p>
        <button type="button" onClick={onRetry} className="mt-3 text-sm text-ink">
          Retry
        </button>
      </div>
    );
  }
  if (items.length === 0) {
    return (
      <p className="px-2 py-6 text-sm leading-6 text-secondary">
        {query.trim() ? "No documents match that search." : "Your library is empty. Start a new chat and upload a PDF."}
      </p>
    );
  }
  return (
    <ul>
      {items.map((document) => {
        const editing = editingId === document.document_id;
        return (
          <li key={document.document_id} className="group border-b border-line-subtle last:border-b-0">
            <div className="flex items-center gap-3 rounded-lg px-2 py-3 hover:bg-hover">
              <button
                type="button"
                onClick={() => onOpen(document.document_id)}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#f3f6f8] text-[#6d7f90]"
                aria-label={`Open ${document.filename}`}
              >
                <FileText className="h-4 w-4" strokeWidth={1.5} />
              </button>
              <div className="min-w-0 flex-1">
                {editing ? (
                  <form
                    onSubmit={(event) => {
                      event.preventDefault();
                      onSave(document.document_id);
                    }}
                  >
                    <input
                      aria-label={`Rename ${document.filename}`}
                      value={draftName}
                      autoFocus
                      onChange={(event) => onDraftName(event.target.value)}
                      onBlur={() => {
                        if (skipSave.current) {
                          skipSave.current = false;
                          return;
                        }
                        onSave(document.document_id);
                      }}
                      onKeyDown={(event) => {
                        if (event.key === "Escape") {
                          event.preventDefault();
                          skipSave.current = true;
                          onCancel();
                        }
                      }}
                      className="h-8 w-full rounded-md border border-line bg-white px-2 text-sm text-ink outline-none"
                    />
                  </form>
                ) : (
                  <button type="button" onClick={() => onOpen(document.document_id)} className="block max-w-full truncate text-left text-sm font-medium text-ink">
                    {document.filename}
                  </button>
                )}
                <p className="mt-0.5 text-xs text-muted">
                  Added {formatAddedDate(document.created_at)}
                  {document.ingestion_status === "failed" ? <span className="text-danger"> · Ingestion failed</span> : null}
                </p>
                {editing && renameError ? <p className="mt-1 text-xs text-danger">{renameError}</p> : null}
              </div>
              {editing ? null : (
                <button
                  type="button"
                  aria-label={`Rename ${document.filename}`}
                  onClick={() => onBeginRename(document)}
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted hover:bg-white hover:text-ink"
                >
                  <Pencil className="h-3.5 w-3.5" strokeWidth={1.5} />
                </button>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`-mb-px flex h-10 items-center gap-2 border-b-2 text-sm ${active ? "border-ink text-ink" : "border-transparent text-muted hover:text-ink"}`}
    >
      {icon}
      {label}
    </button>
  );
}

function EmptyCopy({ children }: { children: string }) {
  return <p className="px-2 py-6 text-sm leading-6 text-secondary">{children}</p>;
}
