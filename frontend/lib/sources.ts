import type { SourceCitation } from "@/lib/types";

const SOURCE_FOOTER = /\n+Sources:\n(?:\[Source:[^\n]*\]\n?)+$/;

/** Remove the citation block the API appends. The buttons render those sources. */
export function answerBody(answer: string) {
  return answer.replace(SOURCE_FOOTER, "").trim();
}

export function groundingLabel(status: string) {
  if (status === "grounded") return "Grounded";
  if (status === "partially_grounded") return "Partially grounded";
  if (status === "insufficient_context") return "Not enough context";
  return status;
}

export function sourceKey(source: SourceCitation) {
  return `${source.document_id}:${source.chunk_id}`;
}
