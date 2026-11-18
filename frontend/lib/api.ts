import type {
  AnswerResponse,
  DeleteDocumentResponse,
  DocumentDetail,
  DocumentSummary,
} from "@/lib/types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function apiUrl(path: string) {
  return `${API_URL}${path}`;
}

async function request(path: string, init?: RequestInit) {
  try {
    return await fetch(apiUrl(path), init);
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(`Could not reach the API at ${API_URL}.`);
    }
    throw error;
  }
}

async function toError(response: Response) {
  let message = "The request failed.";
  try {
    const body = (await response.json()) as { error?: unknown };
    if (typeof body.error === "string" && body.error.trim()) {
      message = body.error;
    }
  } catch {
    message = "The request failed.";
  }
  return new ApiError(response.status, message);
}

export async function listDocuments(): Promise<DocumentSummary[]> {
  const response = await request("/api/documents", { cache: "no-store" });
  if (!response.ok) throw await toError(response);
  return response.json();
}

export async function getDocument(documentId: string): Promise<DocumentDetail> {
  const response = await request(`/api/documents/${encodeURIComponent(documentId)}`, {
    cache: "no-store",
  });
  if (!response.ok) throw await toError(response);
  return response.json();
}

export async function uploadDocument(file: File): Promise<DocumentDetail> {
  const body = new FormData();
  body.append("file", file, file.name);
  const response = await request("/api/documents/upload", {
    method: "POST",
    body,
  });
  if (!response.ok) throw await toError(response);
  return response.json();
}

export async function renameDocument(documentId: string, filename: string): Promise<DocumentDetail> {
  const response = await request(`/api/documents/${encodeURIComponent(documentId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename }),
  });
  if (!response.ok) throw await toError(response);
  return response.json();
}

export async function deleteDocument(documentId: string): Promise<DeleteDocumentResponse> {
  const response = await request(`/api/documents/${encodeURIComponent(documentId)}`, {
    method: "DELETE",
  });
  if (!response.ok) throw await toError(response);
  return response.json();
}

export async function askDocument(documentId: string, question: string): Promise<AnswerResponse> {
  const response = await request(`/api/documents/${encodeURIComponent(documentId)}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) throw await toError(response);
  return response.json();
}

export function fetchDocumentFile(documentId: string, signal?: AbortSignal): Promise<Blob> {
  return request(`/api/documents/${encodeURIComponent(documentId)}/file`, {
    signal,
    cache: "no-store",
  }).then(async (response) => {
    if (!response.ok) throw await toError(response);
    return response.blob();
  });
}
