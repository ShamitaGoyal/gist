import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const sourceDir = join(root, "node_modules", "pdfjs-dist", "build");
const publicDir = join(root, "public");

mkdirSync(publicDir, { recursive: true });
for (const name of ["pdf.min.mjs", "pdf.worker.min.mjs"]) {
  copyFileSync(join(sourceDir, name), join(publicDir, name));
}
