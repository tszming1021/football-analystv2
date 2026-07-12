"use client";

import Link from "next/link";
import { ArrowLeft, CheckCircle2, KeyRound, Mail, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { getBrowserClient } from "../lib/supabase/browser";

export function AuthForm() {
  const router = useRouter();
  const client = getBrowserClient();
  const [email, setEmail] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [token, setToken] = useState("");
  const [awaitingVerification, setAwaitingVerification] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  function selectMode(nextMode: "login" | "register") {
    setMode(nextMode);
    setAwaitingVerification(false);
    setToken("");
    setMessage("");
  }

  async function submitCredentials(event: FormEvent) {
    event.preventDefault();
    if (!client) { setMessage("网站还缺少 Supabase 公钥配置，请联系管理员。"); return; }
    setBusy(true); setMessage("");
    const normalizedEmail = email.trim();
    if (mode === "register" && password !== confirmPassword) {
      setBusy(false);
      setMessage("两次输入的密码不一致。");
      return;
    }

    const result = mode === "login"
      ? await client.auth.signInWithPassword({ email: normalizedEmail, password })
      : await client.auth.signUp({ email: normalizedEmail, password });
    setBusy(false);
    if (result.error) { setMessage(formatAuthError(result.error.message, mode)); return; }

    if (mode === "register" && !result.data.session) {
      setAwaitingVerification(true);
      setMessage("注册验证码已发送，请检查邮箱（包括垃圾邮件）。");
      return;
    }

    router.push("/");
    router.refresh();
  }

  async function verifyCode(event: FormEvent) {
    event.preventDefault();
    if (!client) return;
    setBusy(true); setMessage("");
    const { error } = await client.auth.verifyOtp({ email: email.trim(), token: token.trim(), type: "signup" });
    setBusy(false);
    if (error) { setMessage("验证码不正确或已过期，请重新注册。"); return; }
    router.push("/"); router.refresh();
  }

  return (
    <main className="auth-shell">
      <div className="auth-card">
        <Link href="/" className="back-link"><ArrowLeft size={17} /> 返回比赛列表</Link>
        <div className="auth-title"><div className="auth-icon"><ShieldCheck size={24} /></div><div><p className="eyebrow">Football Analyst</p><h1>邮箱注册 / 登录</h1></div></div>
        <p className="auth-copy">注册后可查看第一场比赛的完整分析。其他比赛需要管理员单独开通。</p>
        <div className="auth-tabs" role="tablist" aria-label="账号操作">
          <button type="button" className={mode === "login" ? "auth-tab active" : "auth-tab"} onClick={() => selectMode("login")}>登录</button>
          <button type="button" className={mode === "register" ? "auth-tab active" : "auth-tab"} onClick={() => selectMode("register")}>注册</button>
        </div>
        {!awaitingVerification ? (
          <form onSubmit={submitCredentials} className="auth-form">
            <label htmlFor="email">邮箱地址</label>
            <div className="input-wrap"><Mail size={18} /><input id="email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@example.com" /></div>
            <label htmlFor="password">{mode === "login" ? "登录密码" : "设置密码"}</label>
            <div className="input-wrap"><KeyRound size={18} /><input id="password" type="password" required minLength={6} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="至少 6 位" /></div>
            {mode === "register" && <><label htmlFor="confirm-password">确认密码</label><div className="input-wrap"><KeyRound size={18} /><input id="confirm-password" type="password" required minLength={6} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="再次输入密码" /></div></>}
            <button className="primary-button" disabled={busy}>{busy ? "处理中..." : mode === "login" ? "登录" : "注册并发送验证码"}</button>
          </form>
        ) : (
          <form onSubmit={verifyCode} className="auth-form">
            <label htmlFor="token">邮箱验证码</label>
            <input id="token" className="code-input" inputMode="numeric" autoComplete="one-time-code" required maxLength={8} value={token} onChange={(event) => setToken(event.target.value)} placeholder="输入验证码" />
            <button className="primary-button" disabled={busy}>{busy ? "验证中..." : "验证并登录"}</button>
            <button type="button" className="text-button" onClick={() => { setAwaitingVerification(false); setToken(""); }}>返回注册</button>
          </form>
        )}
        {message && <p className="auth-message"><CheckCircle2 size={16} />{message}</p>}
      </div>
    </main>
  );
}

function formatAuthError(error: string, mode: "login" | "register") {
  if (error.toLowerCase().includes("invalid login credentials")) return "邮箱或密码不正确。";
  if (error.toLowerCase().includes("user already registered")) return "该邮箱已经注册，请切换到登录。";
  if (error.toLowerCase().includes("email address not authorized")) return "当前 Supabase 邮件服务只允许项目成员邮箱，请先使用项目所有者邮箱测试。";
  return mode === "register" ? `注册失败：${error}` : `登录失败：${error}`;
}
