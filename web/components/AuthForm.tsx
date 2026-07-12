"use client";

import Link from "next/link";
import { ArrowLeft, CheckCircle2, Mail, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { getBrowserClient } from "../lib/supabase/browser";

export function AuthForm() {
  const router = useRouter();
  const client = getBrowserClient();
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [sent, setSent] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function sendCode(event: FormEvent) {
    event.preventDefault();
    if (!client) { setMessage("网站还缺少 Supabase 公钥配置，请联系管理员。"); return; }
    setBusy(true); setMessage("");
    const { error } = await client.auth.signInWithOtp({ email: email.trim(), options: { shouldCreateUser: true } });
    setBusy(false);
    if (error) { setMessage(error.message); return; }
    setSent(true); setMessage("验证码已发送，请检查邮箱（包括垃圾邮件）。");
  }

  async function verifyCode(event: FormEvent) {
    event.preventDefault();
    if (!client) return;
    setBusy(true); setMessage("");
    const { error } = await client.auth.verifyOtp({ email: email.trim(), token: token.trim(), type: "email" });
    setBusy(false);
    if (error) { setMessage("验证码不正确或已过期，请重新获取。"); return; }
    router.push("/"); router.refresh();
  }

  return (
    <main className="auth-shell">
      <div className="auth-card">
        <Link href="/" className="back-link"><ArrowLeft size={17} /> 返回比赛列表</Link>
        <div className="auth-title"><div className="auth-icon"><ShieldCheck size={24} /></div><div><p className="eyebrow">Football Analyst</p><h1>邮箱注册 / 登录</h1></div></div>
        <p className="auth-copy">注册后可查看第一场比赛的完整分析。其他比赛需要管理员单独开通。</p>
        {!sent ? (
          <form onSubmit={sendCode} className="auth-form">
            <label htmlFor="email">邮箱地址</label>
            <div className="input-wrap"><Mail size={18} /><input id="email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@example.com" /></div>
            <button className="primary-button" disabled={busy}>{busy ? "发送中..." : "发送邮箱验证码"}</button>
          </form>
        ) : (
          <form onSubmit={verifyCode} className="auth-form">
            <label htmlFor="token">邮箱验证码</label>
            <input id="token" className="code-input" inputMode="numeric" autoComplete="one-time-code" required maxLength={8} value={token} onChange={(event) => setToken(event.target.value)} placeholder="输入验证码" />
            <button className="primary-button" disabled={busy}>{busy ? "验证中..." : "验证并登录"}</button>
            <button type="button" className="text-button" onClick={() => { setSent(false); setToken(""); }}>更换邮箱或重新发送</button>
          </form>
        )}
        {message && <p className="auth-message"><CheckCircle2 size={16} />{message}</p>}
      </div>
    </main>
  );
}
