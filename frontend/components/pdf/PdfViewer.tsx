"use client";

import { useEffect, useRef, useState } from "react";

type PdfViewport = { width: number; height: number };

type PdfPage = {
  getViewport: (params: { scale: number }) => PdfViewport;
  render: (params: {
    canvas: HTMLCanvasElement;
    canvasContext: CanvasRenderingContext2D;
    viewport: PdfViewport;
  }) => { promise: Promise<void>; cancel: () => void };
};

type PdfDocument = {
  numPages: number;
  getPage: (pageNumber: number) => Promise<PdfPage>;
  destroy: () => Promise<void> | void;
};

type PdfjsModule = {
  getDocument: (source: string) => { promise: Promise<PdfDocument>; destroy: () => void };
  GlobalWorkerOptions: { workerSrc: string };
};

let pdfjsModule: Promise<PdfjsModule> | null = null;

function loadPdfjs() {
  if (!pdfjsModule) {
    const load = new Function("url", "return import(url)") as (url: string) => Promise<PdfjsModule>;
    pdfjsModule = load("/pdf.min.mjs").then((mod) => {
      const pdfjs = mod as PdfjsModule;
      pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
      return pdfjs;
    });
  }
  return pdfjsModule;
}

type PdfViewerProps = {
  fileUrl: string;
  page: number;
  scrollToken: number;
  fitWidth: boolean;
  scale: number;
  highlightedPage: number | null;
  onVisiblePage: (page: number) => void;
  onPageCount: (count: number) => void;
  onError: (message: string) => void;
};

export function PdfViewer({
  fileUrl,
  page,
  scrollToken,
  fitWidth,
  scale,
  highlightedPage,
  onVisiblePage,
  onPageCount,
  onError,
}: PdfViewerProps) {
  const scrollerRef = useRef<HTMLDivElement>(null);
  const pageNodes = useRef(new Map<number, HTMLDivElement>());
  const canvasNodes = useRef(new Map<number, HTMLCanvasElement>());
  const programmatic = useRef(false);
  const pageRef = useRef(page);
  const onVisiblePageRef = useRef(onVisiblePage);
  const onPageCountRef = useRef(onPageCount);
  const onErrorRef = useRef(onError);
  pageRef.current = page;
  onVisiblePageRef.current = onVisiblePage;
  onPageCountRef.current = onPageCount;
  onErrorRef.current = onError;

  const [pdf, setPdf] = useState<PdfDocument | null>(null);
  const [frameWidth, setFrameWidth] = useState(640);
  const [slotHeight, setSlotHeight] = useState(900);

  useEffect(() => {
    const node = scrollerRef.current;
    if (!node) return;
    const observer = new ResizeObserver(() => {
      setFrameWidth(Math.max(240, node.clientWidth - 48));
    });
    observer.observe(node);
    setFrameWidth(Math.max(240, node.clientWidth - 48));
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let cancelled = false;
    let active: PdfDocument | null = null;
    let task: { destroy: () => void; promise: Promise<PdfDocument> } | null = null;
    loadPdfjs()
      .then((pdfjs) => {
        if (cancelled) return null;
        task = pdfjs.getDocument(fileUrl);
        return task.promise;
      })
      .then((document) => {
        if (!document || cancelled) {
          void document?.destroy();
          return;
        }
        active = document;
        setPdf(document);
        onPageCountRef.current(document.numPages);
      })
      .catch(() => {
        if (!cancelled) onErrorRef.current("The PDF could not be rendered.");
      });
    return () => {
      cancelled = true;
      task?.destroy();
      void active?.destroy();
      setPdf(null);
    };
  }, [fileUrl]);

  useEffect(() => {
    if (!pdf) return;
    let cancelled = false;
    const tasks: Array<{ cancel: () => void }> = [];
    const numbers = [page - 1, page, page + 1].filter(
      (number) => number >= 1 && number <= pdf.numPages,
    );
    numbers.forEach((number) => {
      void pdf.getPage(number).then((pdfPage) => {
        if (cancelled) return;
        const canvas = canvasNodes.current.get(number);
        const context = canvas?.getContext("2d");
        if (!canvas || !context) return;
        const base = pdfPage.getViewport({ scale: 1 });
        const renderedWidth = fitWidth ? frameWidth : base.width * scale;
        const viewport = pdfPage.getViewport({ scale: renderedWidth / base.width });
        canvas.width = Math.ceil(viewport.width);
        canvas.height = Math.ceil(viewport.height);
        setSlotHeight(Math.ceil(viewport.height));
        const task = pdfPage.render({ canvas, canvasContext: context, viewport });
        tasks.push(task);
        void task.promise.catch(() => undefined);
      });
    });
    return () => {
      cancelled = true;
      tasks.forEach((task) => task.cancel());
    };
  }, [pdf, page, fitWidth, scale, frameWidth]);

  useEffect(() => {
    const root = scrollerRef.current;
    if (!root || !pdf) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (programmatic.current) return;
        const best = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (!best) return;
        const next = Number((best.target as HTMLElement).dataset.page);
        if (next) onVisiblePageRef.current(next);
      },
      { root, threshold: [0.35, 0.6] },
    );
    pageNodes.current.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, [pdf]);

  useEffect(() => {
    const root = scrollerRef.current;
    if (!root || !pdf) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const align = (behavior: ScrollBehavior, minimum: number) => {
      const node = pageNodes.current.get(pageRef.current);
      if (!node) return;
      const delta = node.getBoundingClientRect().top - root.getBoundingClientRect().top;
      if (Math.abs(delta) < minimum) return;
      root.scrollTo({ top: Math.max(0, root.scrollTop + delta), behavior });
    };
    programmatic.current = true;
    align(reduced ? "auto" : "smooth", 2);
    const retry = window.setTimeout(() => align(reduced ? "auto" : "smooth", 48), 420);
    const release = window.setTimeout(() => {
      programmatic.current = false;
    }, reduced ? 280 : 900);
    return () => {
      window.clearTimeout(retry);
      window.clearTimeout(release);
      programmatic.current = false;
    };
  }, [scrollToken, pdf]);

  if (!pdf) {
    return <p className="px-6 py-6 text-sm text-muted">Opening document…</p>;
  }

  return (
    <div ref={scrollerRef} className="min-h-0 flex-1 overflow-auto bg-canvas">
      {Array.from({ length: pdf.numPages }, (_, index) => {
        const number = index + 1;
        const near = Math.abs(number - page) <= 1;
        const highlighted = highlightedPage === number;
        return (
          <div
            key={number}
            data-page={number}
            ref={(node) => {
              if (node) pageNodes.current.set(number, node);
              else pageNodes.current.delete(number);
            }}
            className="mx-auto mb-4 flex justify-center px-6 pt-4"
          >
            {near ? (
              <canvas
                ref={(node) => {
                  if (node) canvasNodes.current.set(number, node);
                  else canvasNodes.current.delete(number);
                }}
                className={highlighted ? "border border-line-strong" : undefined}
              />
            ) : (
              <div style={{ width: frameWidth, height: slotHeight }} />
            )}
          </div>
        );
      })}
    </div>
  );
}
