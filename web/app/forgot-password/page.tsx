"use client";

import Link from "next/link";
import { AlertCircle, ArrowLeft, Mail, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";
import { getBrowserClient } from "../../lib/supabase/browser";

export default function ForgotPasswordPage() {
  const client = getBrowserClient();
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!client) { setMessage("网站还缺少 Supabase 公钥配置，请联系管理员。"); return; }
    setBusy(true); setMessage("");
    const { error } = await client.auth.resetPasswordForEmail(email.trim(), { redirectTo: `${window.location.origin}/auth/callback?next=/reset-password` });
    setBusy(false);
    setMessage(error ? "发送失败，请检查邮箱地址或稍后再试。" : "如果该邮箱已注册，密码重置邮件会发送到你的邮箱，请检查收件箱和垃圾邮件。" );
  }

  return <main className="auth-shell"><div className="auth-card">
    <Link href="/login" className="back-link"><ArrowLeft size={17} /> 返回登录</Link>
    <div className="auth-title"><div className="auth-icon"><ShieldCheck size={24} /></div><div><p className="eyebrow">Football Analyst</p><h1>找回密码</h1></div></div>
    <p className="auth-copy">输入注册邮箱，我们会发送密码重置链接。</p>
    <form onSubmit={submit} className="auth-form"><label htmlFor="reset-email">邮箱地址</label><div className="input-wrap"><Mail size={18} /><input id="reset-email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@example.com" autoComplete="email" /></div><button className="primary-button" disabled={busy}>{busy ? "发送中..." : "发送重置邮件"}</button></form>
    {message && <p className="auth-message"><AlertCircle size={16} />{message}</p>}
  </div></main>;
}
