"use client";

import { ChevronDown, ChevronRight, GripVertical, Home, Library, Plus, Trash2 } from "lucide-react";
import type { PointerEvent as ReactPointerEvent, ReactNode } from "react";
import { useMemo, useRef, useState } from "react";

import { DeleteDialog } from "@/components/documents/DeleteDialog";
import { useWorkspace } from "@/hooks/useWorkspace";
import type { DocumentSummary } from "@/lib/types";

export function DocumentLibrary() {
  const {
    documents,
    documentsStatus,
    documentsError,
    refreshDocuments,
    selectedId,
    selectDocument,
    section,
    setSection,
    setPanel,
    newChat,
    groups,
    activeGroupId,
    createGroup,
    removeGroup,
    moveDocumentToGroup,
    startNewChat,
  } = useWorkspace();
  const [pendingDelete, setPendingDelete] = useState<DocumentSummary | null>(null);
  const [dropGroupId, setDropGroupId] = useState<string | null>(null);
  const [dragGhost, setDragGhost] = useState<{ name: string; x: number; y: number } | null>(null);
  const suppressClick = useRef(false);
  const namingLock = useRef(false);
  const [namingGroup, setNamingGroup] = useState(false);
  const [groupName, setGroupName] = useState("");
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});

  const documentsById = useMemo(
    () => new Map(documents.map((document) => [document.document_id, document])),
    [documents],
  );
  const groupedIds = useMemo(
    () => new Set(groups.flatMap((group) => group.documentIds)),
    [groups],
  );
  const ungrouped = useMemo(
    () => documents.filter((document) => !groupedIds.has(document.document_id))
      .sort((a, b) => b.created_at.localeCompare(a.created_at)),
    [documents, groupedIds],
  );

  function commitGroup() {
    if (namingLock.current) return;
    const id = createGroup(groupName);
    if (!id) {
      setNamingGroup(false);
      return;
    }
    namingLock.current = true;
    setGroupName("");
    setNamingGroup(false);
    setOpenGroups((current) => ({ ...current, [id]: true }));
  }

  function beginDrag(event: ReactPointerEvent, document: DocumentSummary) {
    if (event.button !== 0) return;
    const startX = event.clientX;
    const startY = event.clientY;
    const documentId = document.document_id;
    const name = document.filename.replace(/\.pdf$/i, "");
    let dragging = false;

    const groupAt = (x: number, y: number) => {
      const under = window.document.elementFromPoint(x, y);
      return under?.closest("[data-group-id]")?.getAttribute("data-group-id") ?? null;
    };
    const move = (pointer: PointerEvent) => {
      if (pointer.pointerId !== event.pointerId) return;
      if (!dragging && Math.hypot(pointer.clientX - startX, pointer.clientY - startY) < 6) return;
      dragging = true;
      setDragGhost({ name, x: pointer.clientX, y: pointer.clientY });
      setDropGroupId(groupAt(pointer.clientX, pointer.clientY));
    };
    const finish = (pointer: PointerEvent) => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", finish);
      window.removeEventListener("pointercancel", finish);
      if (pointer.pointerId !== event.pointerId) return;
      if (dragging) {
        suppressClick.current = true;
        const groupId = groupAt(pointer.clientX, pointer.clientY);
        if (groupId) {
          moveDocumentToGroup(documentId, groupId);
          setOpenGroups((current) => ({ ...current, [groupId]: true }));
        }
      }
      setDragGhost(null);
      setDropGroupId(null);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", finish);
    window.addEventListener("pointercancel", finish);
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-white">
      <div className="flex items-center gap-2 px-5 py-3">
        <h1 className="text-2xl tracking-[-0.011em] text-ink">Gist</h1>
      </div>
      <nav className="px-2">
        <NavButton
          icon={<Home className="h-4 w-4" strokeWidth={1.5} />}
          label="Home"
          active={section === "home"}
          onClick={() => {
            setSection("home");
            setPanel("reader");
          }}
        />
        <NavButton
          icon={<Library className="h-4 w-4" strokeWidth={1.5} />}
          label="Library"
          active={section === "library"}
          onClick={() => {
            setSection("library");
            setPanel("reader");
          }}
        />
      </nav>
      <div className="mt-4 flex items-center justify-between px-3">
        <p className="text-xs font-medium text-muted">Groups</p>
        <button
          type="button"
          aria-label="New group"
          onClick={() => {
            namingLock.current = false;
            setNamingGroup(true);
          }}
          className="flex h-6 w-6 items-center justify-center rounded-md text-secondary hover:bg-hover hover:text-ink"
        >
          <Plus className="h-4 w-4" strokeWidth={1.5} />
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-auto px-2 pb-3 pt-1">
        {namingGroup ? (
          <form
            className="px-1 pb-2"
            onSubmit={(event) => {
              event.preventDefault();
              commitGroup();
            }}
          >
            <input
              aria-label="Group name"
              autoFocus
              value={groupName}
              placeholder="Group name"
              onChange={(event) => setGroupName(event.target.value)}
              onBlur={() => {
                if (groupName.trim()) commitGroup();
                else setNamingGroup(false);
              }}
              onKeyDown={(event) => {
                if (event.key === "Escape") {
                  event.preventDefault();
                  setGroupName("");
                  setNamingGroup(false);
                }
              }}
              className="h-8 w-full rounded-lg border border-line bg-white px-2 text-sm text-ink outline-none placeholder:text-muted"
            />
          </form>
        ) : null}
        {documentsStatus === "loading" ? <p className="px-2 py-2 text-sm text-muted">Loading…</p> : null}
        {documentsStatus === "error" ? (
          <button type="button" onClick={() => refreshDocuments().catch(() => undefined)} className="px-2 py-2 text-left text-sm text-danger">
            {documentsError ?? "Could not load documents."} Retry
          </button>
        ) : null}
        {documentsStatus === "ready" && groups.length === 0 && !namingGroup ? (
          <p className="px-2 py-2 text-sm leading-6 text-muted">Create a group for a topic, then add chats inside it.</p>
        ) : null}
        <ul className="mt-1 flex flex-col">
          {groups.map((group) => {
            const open = openGroups[group.id] ?? false;
            const chats = group.documentIds
              .map((id) => documentsById.get(id))
              .filter((document): document is DocumentSummary => Boolean(document));
            return (
              <li
                key={group.id}
                data-group-id={group.id}
                className={dropGroupId === group.id ? "rounded-lg bg-selected ring-1 ring-ink" : undefined}
              >
                <div className="group/row flex items-center">
                  <button
                    type="button"
                    aria-expanded={open}
                    onClick={() => setOpenGroups((current) => ({ ...current, [group.id]: !open }))}
                    className="flex min-w-0 flex-1 items-center gap-1 rounded-lg px-2 py-1.5 text-left text-sm text-ink hover:bg-hover"
                  >
                    {open ? (
                      <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted" strokeWidth={1.5} />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted" strokeWidth={1.5} />
                    )}
                    <span className="truncate">{group.name}</span>
                  </button>
                  <button
                    type="button"
                    aria-label={`New chat in ${group.name}`}
                    onClick={() => {
                      setOpenGroups((current) => ({ ...current, [group.id]: true }));
                      startNewChat(group.id);
                    }}
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-muted hover:bg-hover hover:text-ink"
                  >
                    <Plus className="h-3.5 w-3.5" strokeWidth={1.5} />
                  </button>
                  <button
                    type="button"
                    aria-label={`Remove group ${group.name}`}
                    title="Remove group. Chats stay in the library."
                    onClick={() => removeGroup(group.id)}
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-muted opacity-0 hover:bg-hover hover:text-ink group-hover/row:opacity-100"
                  >
                    <Trash2 className="h-3.5 w-3.5" strokeWidth={1.5} />
                  </button>
                </div>
                {open ? (
                  <ul className="mb-1 ml-4 flex flex-col">
                    {newChat && activeGroupId === group.id ? (
                      <li className="rounded-lg bg-selected px-2 py-1.5 text-sm text-ink">New chat</li>
                    ) : null}
                    {chats.length === 0 && !(newChat && activeGroupId === group.id) ? (
                      <li className="px-2 py-1 text-xs text-muted">No chats yet</li>
                    ) : null}
                    {chats.map((document) => (
                      <ChatRow
                        key={document.document_id}
                        document={document}
                        selected={document.document_id === selectedId && !newChat}
                        onOpen={() => selectDocument(document.document_id)}
                        onDelete={() => setPendingDelete(document)}
                      />
                    ))}
                  </ul>
                ) : null}
              </li>
            );
          })}
        </ul>
        {ungrouped.length > 0 || (newChat && !activeGroupId) ? (
          <div className="mt-3">
            <p className="px-2 pb-1 text-xs font-medium text-muted">Ungrouped</p>
            {newChat && !activeGroupId ? (
              <p className="rounded-lg bg-selected px-2 py-1.5 text-sm text-ink">New chat</p>
            ) : null}
            <ul className="flex flex-col">
              {ungrouped.map((document) => (
                <ChatRow
                  key={document.document_id}
                  document={document}
                  selected={document.document_id === selectedId && !newChat}
                  draggable
                  onOpen={() => {
                    if (suppressClick.current) {
                      suppressClick.current = false;
                      return;
                    }
                    selectDocument(document.document_id);
                  }}
                  onDragStart={(event) => beginDrag(event, document)}
                  onDelete={() => setPendingDelete(document)}
                />
              ))}
            </ul>
          </div>
        ) : null}
      </div>
      {pendingDelete ? <DeleteDialog document={pendingDelete} onClose={() => setPendingDelete(null)} /> : null}
      {dragGhost ? (
        <div
          className="pointer-events-none fixed z-50 rounded-lg border border-line bg-white px-2 py-1 text-sm text-ink shadow-sm"
          style={{ left: dragGhost.x + 12, top: dragGhost.y + 12 }}
        >
          {dragGhost.name}
        </div>
      ) : null}
    </div>
  );
}

function ChatRow({
  document,
  selected,
  draggable = false,
  onOpen,
  onDragStart,
  onDelete,
}: {
  document: DocumentSummary;
  selected: boolean;
  draggable?: boolean;
  onOpen: () => void;
  onDragStart?: (event: ReactPointerEvent) => void;
  onDelete: () => void;
}) {
  return (
    <li className="group flex items-center">
      <button
        type="button"
        aria-selected={selected}
        onClick={onOpen}
        onPointerDown={onDragStart}
        className={`flex min-w-0 flex-1 items-center gap-1 rounded-lg px-2 py-1.5 text-left text-sm ${draggable ? "cursor-grab active:cursor-grabbing" : ""} ${selected ? "bg-selected text-ink" : "text-secondary hover:bg-hover hover:text-ink"}`}
      >
        {draggable ? (
          <GripVertical className="h-3.5 w-3.5 shrink-0 text-muted" strokeWidth={1.5} />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted" strokeWidth={1.5} />
        )}
        <span className="truncate">{document.filename.replace(/\.pdf$/i, "")}</span>
      </button>
      <button
        type="button"
        aria-label={`Delete ${document.filename}`}
        onClick={onDelete}
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-muted opacity-0 hover:bg-hover hover:text-ink group-hover:opacity-100"
      >
        <Trash2 className="h-3.5 w-3.5" strokeWidth={1.5} />
      </button>
    </li>
  );
}

function NavButton({
  icon,
  label,
  active,
  onClick,
}: {
  icon: ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`flex h-9 w-full items-center gap-2 rounded-lg px-2 text-sm ${active ? "bg-selected text-ink" : "text-secondary hover:bg-hover hover:text-ink"}`}
    >
      {icon}
      {label}
    </button>
  );
}
