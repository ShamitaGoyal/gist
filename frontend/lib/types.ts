/** Shapes returned by the FastAPI document and question routes. */

export type DocumentSummary = {
  document_id: string;
  filename: string;
  ingestion_status: string;
  total_pages: number;
  total_chunks: number;
  created_at: string;
  last_ingestion_at: string;
};

export type DocumentDetail = DocumentSummary & {
  total_embeddings: number;
  error: string | null;
};

export type DeleteDocumentResponse = {
  document_id: string;
  deleted: boolean;
};

export type SourceCitation = {
  chunk_id: string;
  document_id: string;
  page_number: number | null;
  source_type: string;
};

export type AnswerResponse = {
  document_id: string;
  question: string;
  answer: string;
  grounding_status: string;
  sources: SourceCitation[];
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  groundingStatus?: string;
  sources?: SourceCitation[];
  pending?: boolean;
  error?: string;
};

export type SelectedSource = {
  documentId: string;
  chunkId: string;
  pageNumber: number | null;
  sourceType: string;
};

export type PanelName = "library" | "reader" | "chat";
