"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  ApiError,
  askDocument,
  deleteDocument,
  getDocument,
  listDocuments,
  renameDocument as renameDocumentRequest,
  uploadDocument,
} from "@/lib/api";
import { readGroups, writeGroups, type TopicGroup } from "@/lib/groups";
import type {
  ChatMessage,
  DocumentDetail,
  DocumentSummary,
  PanelName,
  SelectedSource,
  SourceCitation,
} from "@/lib/types";

type WorkspaceValue = {
  documents: DocumentSummary[];
  documentsStatus: "loading" | "ready" | "error";
  documentsError: string | null;
  refreshDocuments: () => Promise<void>;
  selectedId: string | null;
  selected: DocumentSummary | null;
  selectedDetail: DocumentDetail | null;
  selectDocument: (documentId: string) => void;
  renameDocument: (documentId: string, filename: string) => Promise<void>;
  page: number;
  pdfPageCount: number;
  setPdfPageCount: (count: number) => void;
  scrollToken: number;
  goToPage: (page: number) => void;
  noteVisiblePage: (page: number) => void;
  showPreviousPage: () => void;
  showNextPage: () => void;
  messages: ChatMessage[];
  draft: string;
  setDraft: (value: string) => void;
  asking: boolean;
  ask: () => Promise<void>;
  selectedSource: SelectedSource | null;
  openSource: (source: SourceCitation) => void;
  removeDocument: (documentId: string) => Promise<void>;
  section: "home" | "library";
  setSection: (section: "home" | "library") => void;
  newChat: boolean;
  groups: TopicGroup[];
  activeGroupId: string | null;
  createGroup: (name: string) => string | null;
  removeGroup: (groupId: string) => void;
  moveDocumentToGroup: (documentId: string, groupId: string) => void;
  startNewChat: (groupId?: string | null) => void;
  ingest: IngestState | null;
  uploadPdf: (file: File) => Promise<void>;
  clearIngest: () => void;
  panel: PanelName;
  setPanel: (panel: PanelName) => void;
  libraryOpen: boolean;
  setLibraryOpen: (open: boolean) => void;
  chatOpen: boolean;
  setChatOpen: (open: boolean) => void;
};

export type IngestState = {
  name: string;
  bytes: number;
  progress: number;
  error: string | null;
  active: boolean;
};

const WorkspaceContext = createContext<WorkspaceValue | null>(null);

function messageId() {
  return crypto.randomUUID();
}

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [documentsStatus, setDocumentsStatus] = useState<"loading" | "ready" | "error">("loading");
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<DocumentDetail | null>(null);
  const [page, setPage] = useState(1);
  const [pdfPageCount, setPdfPageCount] = useState(0);
  const [scrollToken, setScrollToken] = useState(0);
  const [messagesById, setMessagesById] = useState<Record<string, ChatMessage[]>>({});
  const [draft, setDraft] = useState("");
  const [asking, setAsking] = useState(false);
  const [selectedSource, setSelectedSource] = useState<SelectedSource | null>(null);
  const [panel, setPanel] = useState<PanelName>("reader");
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [section, setSection] = useState<"home" | "library">("home");
  const [newChat, setNewChat] = useState(false);
  const [groups, setGroups] = useState<TopicGroup[]>([]);
  const [activeGroupId, setActiveGroupId] = useState<string | null>(null);
  const [ingest, setIngest] = useState<IngestState | null>(null);
  const ingestTimer = useRef<number | null>(null);
  const groupsReady = useRef(false);

  const refreshDocuments = useCallback(async () => {
    const list = await listDocuments();
    setDocuments(list);
    setDocumentsError(null);
  }, []);

  useEffect(() => {
    setGroups(readGroups());
    groupsReady.current = true;
  }, []);

  useEffect(() => {
    if (!groupsReady.current) return;
    writeGroups(groups);
  }, [groups]);

  useEffect(() => {
    if (!groupsReady.current || documentsStatus !== "ready") return;
    const ids = new Set(documents.map((document) => document.document_id));
    setGroups((current) => {
      let changed = false;
      const next = current.map((group) => {
        const documentIds = group.documentIds.filter((id) => ids.has(id));
        if (documentIds.length !== group.documentIds.length) changed = true;
        return documentIds.length === group.documentIds.length ? group : { ...group, documentIds };
      });
      return changed ? next : current;
    });
  }, [documents, documentsStatus]);

  useEffect(() => {
    let active = true;
    listDocuments()
      .then((list) => {
        if (!active) return;
        setDocuments(list);
        setDocumentsStatus("ready");
      })
      .catch((error: unknown) => {
        if (!active) return;
        setDocumentsStatus("error");
        setDocumentsError(error instanceof Error ? error.message : "Could not load documents.");
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setSelectedDetail(null);
      return;
    }
    let active = true;
    getDocument(selectedId)
      .then((detail) => {
        if (active) setSelectedDetail(detail);
      })
      .catch(() => {
        if (active) setSelectedDetail(null);
      });
    return () => {
      active = false;
    };
  }, [selectedId, documents]);

  const selectDocument = useCallback((documentId: string) => {
    setSelectedId(documentId);
    setNewChat(false);
    setSection("home");
    setPage(1);
    setPdfPageCount(0);
    setScrollToken((token) => token + 1);
    setSelectedSource(null);
    setDraft("");
    setPanel("reader");
    setLibraryOpen(false);
    setChatOpen(true);
  }, []);

  const renameDocument = useCallback(async (documentId: string, filename: string) => {
    const updated = await renameDocumentRequest(documentId, filename);
    setDocuments((current) =>
      current.map((document) =>
        document.document_id === documentId ? { ...document, filename: updated.filename } : document,
      ),
    );
  }, []);

  const createGroup = useCallback((name: string) => {
    const trimmed = name.trim().replace(/\s+/g, " ").slice(0, 80);
    if (!trimmed) return null;
    const group: TopicGroup = {
      id: crypto.randomUUID(),
      name: trimmed,
      documentIds: [],
      createdAt: new Date().toISOString(),
    };
    setGroups((current) => [group, ...current]);
    return group.id;
  }, []);

  const removeGroup = useCallback((groupId: string) => {
    setGroups((current) => current.filter((group) => group.id !== groupId));
    setActiveGroupId((current) => (current === groupId ? null : current));
  }, []);

  const moveDocumentToGroup = useCallback((documentId: string, groupId: string) => {
    setGroups((current) =>
      current.map((group) => {
        const without = group.documentIds.filter((id) => id !== documentId);
        if (group.id !== groupId) {
          return without.length === group.documentIds.length ? group : { ...group, documentIds: without };
        }
        return { ...group, documentIds: [...without, documentId] };
      }),
    );
  }, []);

  const startNewChat = useCallback((groupId?: string | null) => {
    const inferred = groups.find((group) => selectedId && group.documentIds.includes(selectedId))?.id ?? null;
    setActiveGroupId(groupId === undefined ? inferred : groupId);
    setSelectedId(null);
    setSelectedDetail(null);
    setSelectedSource(null);
    setDraft("");
    setPage(1);
    setPdfPageCount(0);
    setNewChat(true);
    setSection("home");
    setPanel("reader");
    setLibraryOpen(false);
    setChatOpen(true);
  }, [groups, selectedId]);

  const clearIngest = useCallback(() => {
    if (ingestTimer.current) window.clearInterval(ingestTimer.current);
    ingestTimer.current = null;
    setIngest(null);
  }, []);

  const uploadPdf = useCallback(
    async (file: File) => {
      const looksLikePdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
      if (!looksLikePdf) {
        setIngest({ name: file.name, bytes: file.size, progress: 0, error: "Only PDF files can be uploaded.", active: false });
        return;
      }
      if (file.size === 0) {
        setIngest({ name: file.name, bytes: 0, progress: 0, error: "The uploaded file is empty.", active: false });
        return;
      }
      if (ingestTimer.current) window.clearInterval(ingestTimer.current);
      const started = Date.now();
      setIngest({ name: file.name, bytes: file.size, progress: 8, error: null, active: true });
      ingestTimer.current = window.setInterval(() => {
        const elapsed = Date.now() - started;
        const value = 8 + 84 * (1 - Math.exp(-elapsed / 40000));
        setIngest((current) =>
          current && current.active ? { ...current, progress: Math.min(92, value) } : current,
        );
      }, 200);
      try {
        const uploaded = await uploadDocument(file);
        if (ingestTimer.current) window.clearInterval(ingestTimer.current);
        ingestTimer.current = null;
        setIngest({ name: file.name, bytes: file.size, progress: 100, error: null, active: false });
        await refreshDocuments();
        if (activeGroupId) {
          const documentId = uploaded.document_id;
          setGroups((current) =>
            current.map((group) =>
              group.id === activeGroupId && !group.documentIds.includes(documentId)
                ? { ...group, documentIds: [...group.documentIds, documentId] }
                : group,
            ),
          );
        }
        selectDocument(uploaded.document_id);
        setActiveGroupId(null);
        window.setTimeout(() => setIngest(null), 600);
      } catch (error) {
        if (ingestTimer.current) window.clearInterval(ingestTimer.current);
        ingestTimer.current = null;
        const message = error instanceof Error ? error.message : "Ingestion failed.";
        setIngest({ name: file.name, bytes: file.size, progress: 0, error: message, active: false });
      }
    },
    [activeGroupId, refreshDocuments, selectDocument],
  );

  const goToPage = useCallback((nextPage: number) => {
    setPage((current) => {
      const next = Math.max(1, nextPage);
      return next === current ? current : next;
    });
    setScrollToken((token) => token + 1);
  }, []);

  const noteVisiblePage = useCallback((nextPage: number) => {
    setPage((current) => (current === nextPage ? current : Math.max(1, nextPage)));
  }, []);

  const showPreviousPage = useCallback(() => {
    setPage((current) => Math.max(1, current - 1));
    setScrollToken((token) => token + 1);
  }, []);

  const showNextPage = useCallback(() => {
    setPage((current) => current + 1);
    setScrollToken((token) => token + 1);
  }, []);

  const openSource = useCallback((source: SourceCitation) => {
    setSelectedSource({
      documentId: source.document_id,
      chunkId: source.chunk_id,
      pageNumber: source.page_number,
      sourceType: source.source_type,
    });
    if (source.page_number && source.page_number > 0) {
      setPage(source.page_number);
      setScrollToken((token) => token + 1);
    }
    setPanel("reader");
    setChatOpen(false);
    setLibraryOpen(false);
  }, []);

  const ask = useCallback(async () => {
    const documentId = selectedId;
    const question = draft.trim();
    if (!documentId || !question || asking || question.length > 2000) return;
    const userMessage: ChatMessage = { id: messageId(), role: "user", text: question };
    const pendingId = messageId();
    setDraft("");
    setAsking(true);
    setMessagesById((current) => ({
      ...current,
      [documentId]: [
        ...(current[documentId] ?? []),
        userMessage,
        { id: pendingId, role: "assistant", text: "", pending: true },
      ],
    }));
    try {
      const answer = await askDocument(documentId, question);
      setMessagesById((current) => {
        const existing = current[documentId];
        if (!existing) return current;
        return {
          ...current,
          [documentId]: existing.map((message) =>
            message.id === pendingId
              ? {
                  id: pendingId,
                  role: "assistant",
                  text: answer.answer,
                  groundingStatus: answer.grounding_status,
                  sources: answer.sources,
                }
              : message,
          ),
        };
      });
    } catch (error) {
      const text = error instanceof ApiError ? error.message : "The question could not be answered.";
      setMessagesById((current) => {
        const existing = current[documentId];
        if (!existing) return current;
        return {
          ...current,
          [documentId]: existing.map((message) =>
            message.id === pendingId
              ? { id: pendingId, role: "assistant", text: "", error: text }
              : message,
          ),
        };
      });
    } finally {
      setAsking(false);
    }
  }, [asking, draft, selectedId]);

  const removeDocument = useCallback(
    async (documentId: string) => {
      await deleteDocument(documentId);
      setMessagesById((current) => {
        const next = { ...current };
        delete next[documentId];
        return next;
      });
      if (selectedId === documentId) {
        setSelectedId(null);
        setSelectedDetail(null);
        setPage(1);
        setPdfPageCount(0);
        setSelectedSource(null);
        setDraft("");
      }
      setGroups((current) =>
        current.map((group) =>
          group.documentIds.includes(documentId)
            ? { ...group, documentIds: group.documentIds.filter((id) => id !== documentId) }
            : group,
        ),
      );
      await refreshDocuments();
    },
    [refreshDocuments, selectedId],
  );

  const selected = documents.find((document) => document.document_id === selectedId) ?? null;
  const messages = selectedId ? messagesById[selectedId] ?? [] : [];

  const value = useMemo<WorkspaceValue>(
    () => ({
      documents,
      documentsStatus,
      documentsError,
      refreshDocuments,
      selectedId,
      selected,
      selectedDetail,
      selectDocument,
      renameDocument,
      page,
      pdfPageCount,
      setPdfPageCount,
      scrollToken,
      goToPage,
      noteVisiblePage,
      showPreviousPage,
      showNextPage,
      messages,
      draft,
      setDraft,
      asking,
      ask,
      selectedSource,
      openSource,
      removeDocument,
      section,
      setSection,
      newChat,
      groups,
      activeGroupId,
      createGroup,
      removeGroup,
      moveDocumentToGroup,
      startNewChat,
      ingest,
      uploadPdf,
      clearIngest,
      panel,
      setPanel,
      libraryOpen,
      setLibraryOpen,
      chatOpen,
      setChatOpen,
    }),
    [
      documents,
      documentsStatus,
      documentsError,
      refreshDocuments,
      selectedId,
      selected,
      selectedDetail,
      selectDocument,
      renameDocument,
      page,
      pdfPageCount,
      scrollToken,
      goToPage,
      noteVisiblePage,
      showPreviousPage,
      showNextPage,
      messages,
      draft,
      asking,
      ask,
      selectedSource,
      openSource,
      removeDocument,
      section,
      setSection,
      newChat,
      groups,
      activeGroupId,
      createGroup,
      removeGroup,
      moveDocumentToGroup,
      startNewChat,
      ingest,
      uploadPdf,
      clearIngest,
      panel,
      libraryOpen,
      chatOpen,
    ],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) {
    throw new Error("useWorkspace must be used inside WorkspaceProvider");
  }
  return value;
}
