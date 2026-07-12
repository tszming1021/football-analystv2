import { execFile } from "node:child_process";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { promisify } from "node:util";
import type { MatchPayload } from "./types";
import { persistPayload, type PersistenceResult } from "./database";

const execFileAsync = promisify(execFile);

export type RefreshResult = {
  payload: MatchPayload;
  stdout: string;
  stderr: string;
  persistence: PersistenceResult;
};

export async function refreshMatchData(): Promise<RefreshResult> {
  const webRoot = process.cwd();
  const repoRoot = path.resolve(webRoot, "..");
  const scriptPath = path.join(repoRoot, "scripts", "fetch_500_on_sale.py");
  const outputDir = path.join(os.tmpdir(), `football-analyst-refresh-${Date.now()}`);
  const currentDataPath = path.join(webRoot, "data", "current_matches.json");

  try {
    await fs.mkdir(outputDir, { recursive: true });
    const { stdout, stderr } = await execFileAsync(
      "python3",
      [scriptPath, "--out", outputDir, "--with-deep"],
      {
        cwd: repoRoot,
        maxBuffer: 1024 * 1024 * 20,
        timeout: 120_000
      }
    );

    const nextDataPath = path.join(outputDir, "on_sale_matches.json");
    const raw = await fs.readFile(nextDataPath, "utf-8");
    const payload = JSON.parse(raw) as MatchPayload;
    await fs.writeFile(currentDataPath, JSON.stringify(payload, null, 2), "utf-8");
    const persistence = await persistPayload(payload);

    return { payload, stdout, stderr, persistence };
  } finally {
    await fs.rm(outputDir, { recursive: true, force: true }).catch(() => undefined);
  }
}

export function toRefreshResponse(result: RefreshResult) {
  return {
    ok: true,
    fetched_at: result.payload.fetched_at,
    counts: result.payload.counts,
    errors: result.payload.errors,
    persistence: result.persistence,
    stdout: safeTail(result.stdout),
    stderr: safeTail(result.stderr)
  };
}

function safeTail(value: string) {
  return value.length > 4000 ? value.slice(-4000) : value;
}
