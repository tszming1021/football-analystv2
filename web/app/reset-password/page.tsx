"use client";

import Link from "next/link";
import { AlertCircle, ArrowLeft, KeyRound, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { getBrowserClient } from "../../lib/supabase/browser";

export default function ResetPasswordPage() {
  const router = useRouter();
  const client = getBrowserClient();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!client) { setMessage("网站还缺少 Supabase 公钥配置，请联系管理员。"); return; }
    if (password !== confirmPassword) { setMessage("两次输入的密码不一致。"); return; }
    setBusy(true); setMessage("");
    const { error } = await client.auth.updateUser({ password });
    setBusy(false);
    if (error) { setMessage("重置失败，请重新打开邮件中的链接。 "); return; }
    router.replace("/login?reset=success");
  }

  return <main className="auth-shell"><div className="auth-card">
    <Link href="/login" className="back-link"><ArrowLeft size={17} /> 返回登录</Link>
    <div className="auth-title"><div className="auth-icon"><ShieldCheck size={24} /></div><div><p className="eyebrow">Football Analyst</p><h1>设置新密码</h1></div></div>
    <p className="auth-copy">请输入一个至少 6 位的新密码。</p>
    <form onSubmit={submit} className="auth-form"><label htmlFor="new-password">新密码</label><div className="input-wrap"><KeyRound size={18} /><input id="new-password" type="password" required minLength={6} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="至少 6 位" autoComplete="new-password" /></div><label htmlFor="new-confirm-password">确认新密码</label><div className="input-wrap"><KeyRound size={18} /><input id="new-confirm-password" type="password" required minLength={6} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="再次输入密码" autoComplete="new-password" /></div><button className="primary-button" disabled={busy}>{busy ? "保存中..." : "保存新密码"}</button></form>
    {message && <p className="auth-message"><AlertCircle size={16} />{message}</p>}
  </div></main>;
}
