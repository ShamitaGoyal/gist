"use client";

import { ArrowUp, AtSign, FileText, MoreHorizontal, Plus, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { DeleteDialog } from "@/components/documents/DeleteDialog";
import { useWorkspace } from "@/hooks/useWorkspace";
import { answerBody, groundingLabel, sourceKey } from "@/lib/sources";
import type { ChatMessage, SourceCitation } from "@/lib/types";

export function ChatPanel() {
  const {
    selected,
    selectedDetail,
    messages,
    draft,
    setDraft,
    asking,
    ask,
    selectedSource,
    openSource,
    newChat,
    startNewChat,
  } = useWorkspace();
  const endRef = useRef<HTMLDivElement>(null);
  const finished = useRef(new Set<string>());
  const [, setTick] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const ready = selected?.ingestion_status === "success";
  const question = draft.trim();
  const canSend = Boolean(selected && ready && question && !asking && question.length <= 2000);
  const title = selected ? selected.filename.replace(/\.pdf$/i, "") : "New chat";

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, asking]);

  return (
    <section className="flex min-h-0 flex-1 flex-col bg-white">
      <header className="flex h-12 items-center gap-2 border-b border-line-subtle px-3">
        <FileText className="h-4 w-4 shrink-0 text-muted" strokeWidth={1.5} />
        <h2 className="min-w-0 flex-1 truncate text-sm text-ink">{title}</h2>
        <button
          type="button"
          aria-label="New chat"
          onClick={() => startNewChat()}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-secondary hover:bg-hover"
        >
          <Plus className="h-4 w-4" strokeWidth={1.5} />
        </button>
        <div className="relative">
          <button
            type="button"
            aria-label="Chat menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-secondary hover:bg-hover"
          >
            <MoreHorizontal className="h-4 w-4" strokeWidth={1.5} />
          </button>
          {menuOpen && selected ? (
            <button
              type="button"
              onClick={() => {
                setMenuOpen(false);
                setConfirmDelete(true);
              }}
              className="absolute right-0 top-9 z-10 whitespace-nowrap rounded-lg border border-line bg-white px-3 py-2 text-left text-sm text-ink hover:bg-hover"
            >
              Delete document
            </button>
          ) : null}
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-auto px-4 py-4 pb-6">
        {newChat && !selected ? (
          <p className="text-sm leading-6 text-secondary">Upload a PDF first to start this chat.</p>
        ) : null}
        {!newChat && !selected ? (
          <p className="text-sm leading-6 text-secondary">Choose a recent chat, or start a new one.</p>
        ) : null}
        {selected && !ready ? (
          <p className="text-sm leading-6 text-danger">
            {selectedDetail?.error || "Document ingestion has not completed successfully."}
          </p>
        ) : null}
        {selected && ready && messages.length === 0 ? (
          <p className="text-[15px] leading-7 text-secondary">
            Ask a question about this document. Answers stay attached to this chat.
          </p>
        ) : null}
        <div className="flex flex-col gap-5">
          {messages.map((message) => (
            <Message
              key={message.id}
              message={message}
              animate={Boolean(message.text) && !message.pending && !finished.current.has(message.id)}
              onRevealDone={() => {
                finished.current.add(message.id);
                setTick((value) => value + 1);
              }}
              selectedSource={selectedSource}
              onOpenSource={openSource}
            />
          ))}
        </div>
        <div ref={endRef} />
      </div>

      <div className="shrink-0 px-3 pb-3">
        {selected ? (
          <div className="mb-2 flex items-center gap-2">
            <span className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-line bg-white py-1 pl-2 pr-1 text-xs text-secondary">
              <AtSign className="h-3.5 w-3.5 shrink-0" strokeWidth={1.5} />
              <span className="truncate">{title}</span>
              <button
                type="button"
                aria-label="Clear document context"
                onClick={() => startNewChat()}
                className="flex h-5 w-5 items-center justify-center rounded-full hover:bg-hover"
              >
                <X className="h-3 w-3" strokeWidth={1.5} />
              </button>
            </span>
          </div>
        ) : null}
        <form
          className="rounded-2xl border border-line bg-white px-3 py-2"
          onSubmit={(event) => {
            event.preventDefault();
            if (canSend) void ask();
          }}
        >
          <label className="sr-only" htmlFor="gist-question">
            Question
          </label>
          <textarea
            id="gist-question"
            value={draft}
            rows={1}
            maxLength={2000}
            disabled={!selected || !ready}
            placeholder={selected && ready ? "Ask this context a question..." : "Upload a PDF first"}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                if (canSend) void ask();
              }
            }}
            className="max-h-32 w-full resize-none border-0 bg-transparent py-1 text-sm leading-6 text-ink outline-none placeholder:text-muted disabled:text-disabled"
          />
          <div className="flex items-center justify-between">
            <span className="px-1 text-xs text-muted">Gist</span>
            <button
              type="submit"
              aria-label="Send question"
              disabled={!canSend}
              className="flex h-8 w-8 items-center justify-center rounded-full bg-ink text-white disabled:bg-[#f0f0f0] disabled:text-disabled"
            >
              <ArrowUp className="h-4 w-4" strokeWidth={1.75} />
            </button>
          </div>
        </form>
      </div>
      {confirmDelete && selected ? (
        <DeleteDialog document={selected} onClose={() => setConfirmDelete(false)} />
      ) : null}
    </section>
  );
}

function Message({
  message,
  animate,
  onRevealDone,
  selectedSource,
  onOpenSource,
}: {
  message: ChatMessage;
  animate: boolean;
  onRevealDone: () => void;
  selectedSource: { chunkId: string; documentId: string } | null;
  onOpenSource: (source: SourceCitation) => void;
}) {
  if (message.role === "user") {
    return (
      <p className="ml-auto max-w-[85%] whitespace-pre-wrap rounded-2xl bg-user px-3.5 py-2 text-sm leading-6 text-ink">
        {message.text}
      </p>
    );
  }
  if (message.pending) {
    return (
      <p className="gist-gleam w-fit text-sm font-medium">Thinking</p>
    );
  }
  if (message.error) {
    return <p className="text-sm leading-6 text-danger">{message.error}</p>;
  }
  const body = answerBody(message.text);
  return (
    <article>
      {animate ? <RevealText text={body} onDone={onRevealDone} /> : <p className="whitespace-pre-wrap text-[15px] leading-7 text-ink">{body}</p>}
      {!animate && message.sources && message.sources.length > 0 ? (
        <SourceRow message={message} selectedSource={selectedSource} onOpenSource={onOpenSource} />
      ) : null}
      {!animate && message.groundingStatus ? (
        <p className="mt-2 text-xs text-muted">{groundingLabel(message.groundingStatus)}</p>
      ) : null}
    </article>
  );
}

function RevealText({ text, onDone }: { text: string; onDone: () => void }) {
  const [count, setCount] = useState(0);
  const doneRef = useRef(onDone);
  doneRef.current = onDone;

  useEffect(() => {
    let current = 0;
    const timer = window.setInterval(() => {
      current = Math.min(text.length, current + 2);
      setCount(current);
      if (current >= text.length) {
        window.clearInterval(timer);
        doneRef.current();
      }
    }, 28);
    return () => window.clearInterval(timer);
  }, [text]);

  return (
    <p className="whitespace-pre-wrap text-[15px] leading-7 text-ink">
      {text.slice(0, count)}
      {count < text.length ? <span className="gist-caret" /> : null}
    </p>
  );
}

function SourceRow({
  message,
  selectedSource,
  onOpenSource,
}: {
  message: ChatMessage;
  selectedSource: { chunkId: string; documentId: string } | null;
  onOpenSource: (source: SourceCitation) => void;
}) {
  const pages = new Map<number, SourceCitation>();
  const unlabeled: SourceCitation[] = [];
  for (const source of message.sources ?? []) {
    if (source.page_number && source.page_number > 0) {
      if (!pages.has(source.page_number)) pages.set(source.page_number, source);
    } else {
      unlabeled.push(source);
    }
  }
  const ordered = [...pages.entries()].sort((a, b) => a[0] - b[0]);
  const label = ordered.length === 1 ? "Page" : "Pages";

  return (
    <div className="mt-3 flex flex-wrap items-center gap-1">
      {ordered.length > 0 ? <span className="mr-1 text-xs text-muted">{label}</span> : null}
      {ordered.map(([page, source]) => {
        const selected =
          selectedSource?.documentId === source.document_id && selectedSource.chunkId === source.chunk_id;
        return (
          <button
            key={page}
            type="button"
            aria-label={`Go to page ${page}`}
            aria-pressed={selected}
            onClick={() => onOpenSource(source)}
            className={`inline-flex h-6 min-w-6 items-center justify-center rounded-md px-1.5 text-xs tabular-nums ${selected ? "bg-ink text-white" : "bg-hover text-ink hover:bg-selected"}`}
          >
            {page}
          </button>
        );
      })}
      {unlabeled.map((source) => {
        const selected =
          selectedSource?.documentId === source.document_id && selectedSource.chunkId === source.chunk_id;
        return (
          <button
            key={sourceKey(source)}
            type="button"
            aria-pressed={selected}
            onClick={() => onOpenSource(source)}
            className={`inline-flex h-6 items-center rounded-md px-1.5 text-xs ${selected ? "bg-ink text-white" : "bg-hover text-secondary hover:bg-selected"}`}
          >
            Source
          </button>
        );
      })}
    </div>
  );
}
