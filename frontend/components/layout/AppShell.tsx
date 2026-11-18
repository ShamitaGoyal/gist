"use client";

import { ChatPanel } from "@/components/chat/ChatPanel";
import { DocumentLibrary } from "@/components/documents/DocumentLibrary";
import { LibraryBoard } from "@/components/documents/LibraryBoard";
import { PdfReader } from "@/components/pdf/PdfReader";
import { useViewport } from "@/hooks/useViewport";
import { useWorkspace } from "@/hooks/useWorkspace";

export function AppShell() {
  const { isDesktop, isMobile } = useViewport();
  const { panel, setPanel, libraryOpen, setLibraryOpen, chatOpen, setChatOpen, section } = useWorkspace();

  const libraryVisible = isDesktop || (isMobile ? panel === "library" : libraryOpen);
  const readerVisible = isDesktop || !isMobile || panel === "reader";
  const chatVisible = isDesktop || (isMobile ? panel === "chat" : chatOpen);

  return (
    <div className="h-dvh bg-[#f4f4f4] p-2 text-ink sm:p-3">
      <div className="relative flex h-full min-h-0 overflow-hidden rounded-[20px] border border-[#e8e8e8] bg-white">
        {!isDesktop ? (
          <nav className="absolute left-3 right-3 top-3 z-30 flex h-11 items-center gap-1 rounded-xl border border-line bg-white px-2 min-[1100px]:hidden">
            <PanelButton label="Sidebar" active={isMobile ? panel === "library" : libraryOpen} onClick={() => (isMobile ? setPanel("library") : setLibraryOpen(!libraryOpen))} />
            <PanelButton
              label="Reader"
              active={isMobile ? panel === "reader" : true}
              onClick={() => {
                setPanel("reader");
                setLibraryOpen(false);
                setChatOpen(false);
              }}
            />
            <PanelButton label="Chat" active={isMobile ? panel === "chat" : chatOpen} onClick={() => (isMobile ? setPanel("chat") : setChatOpen(!chatOpen))} />
          </nav>
        ) : null}
        <div className="relative flex min-h-0 min-w-0 flex-1">
          {libraryVisible ? (
            <aside
              className={`flex min-h-0 flex-col border-r border-line-subtle bg-white ${
                isDesktop ? "w-[var(--gist-panel-library)] shrink-0" : isMobile ? "min-w-0 flex-1" : "absolute inset-y-0 left-0 z-20 w-[280px] shadow-none"
              }`}
            >
              <DocumentLibrary />
            </aside>
          ) : null}
          {readerVisible ? (
            <main className={`flex min-h-0 min-w-0 flex-1 flex-col bg-white ${isDesktop ? "" : "pt-12"}`}>
              {section === "library" ? <LibraryBoard /> : <PdfReader />}
            </main>
          ) : null}
          {chatVisible ? (
            <aside
              className={`flex min-h-0 flex-col border-l border-line-subtle bg-white ${
                isDesktop ? "w-[var(--gist-panel-chat)] shrink-0" : isMobile ? "min-w-0 flex-1 pt-12" : "absolute inset-y-0 right-0 z-20 w-[var(--gist-panel-chat)] pt-12"
              }`}
            >
              <ChatPanel />
            </aside>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function PanelButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`h-8 rounded-lg px-3 text-sm ${active ? "bg-selected text-ink" : "text-secondary hover:bg-hover"}`}
    >
      {label}
    </button>
  );
}
