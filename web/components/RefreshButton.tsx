"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { RefreshCw } from "lucide-react";

type RefreshState = "idle" | "loading" | "success" | "error";

export function RefreshButton() {
  const router = useRouter();
  const [state, setState] = useState<RefreshState>("idle");
  const [message, setMessage] = useState("");

  async function refresh() {
    setState("loading");
    setMessage("正在抓取");
    try {
      const response = await fetch("/api/admin/refresh", { method: "POST" });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "刷新失败");
      }
      setState("success");
      setMessage(`已更新 ${payload.counts?.included ?? 0} 场`);
      router.refresh();
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "刷新失败");
    }
  }

  return (
    <div className="refresh-control">
      <button className="icon-button" type="button" onClick={refresh} disabled={state === "loading"}>
        <RefreshCw size={18} className={state === "loading" ? "spin" : ""} />
        <span>{state === "loading" ? "刷新中" : "刷新"}</span>
      </button>
      {message ? <span className={`refresh-message ${state}`}>{message}</span> : null}
    </div>
  );
}
