"use client";

import Link from "next/link";
import { AlertCircle, ArrowLeft, Eye, EyeOff, KeyRound, Mail, RefreshCw, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { getBrowserClient } from "../lib/supabase/browser";

export function AuthForm({ initialMode = "login", initialCaptcha = "" }: { initialMode?: "login" | "register"; initialCaptcha?: string }) {
  const router = useRouter();
  const client = getBrowserClient();
  const [email, setEmail] = useState("");
  const [mode] = useState<"login" | "register">(initialMode);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [captcha, setCaptcha] = useState(initialCaptcha);
  const [captchaInput, setCaptchaInput] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  function refreshCaptcha() {
    setCaptcha((current) => createCaptcha(current));
    setCaptchaInput("");
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
    if (mode === "register" && captchaInput.trim().toLowerCase() !== captcha.toLowerCase()) {
      setBusy(false);
      setMessage("验证码不正确，请重新输入。");
      setCaptcha(createCaptcha());
      setCaptchaInput("");
      return;
    }

    const result = mode === "login"
      ? await client.auth.signInWithPassword({ email: normalizedEmail, password })
      : await client.auth.signUp({ email: normalizedEmail, password });
    setBusy(false);
    if (result.error) { setMessage(formatAuthError(result.error.message, mode)); return; }

    if (mode === "register" && !result.data.session) {
      setMessage("注册已完成，但 Supabase 仍要求确认邮箱。请管理员关闭 Confirm email 后再登录。 ");
      return;
    }

    router.push("/");
    router.refresh();
  }

  return (
    <main className="auth-shell">
      <div className="auth-card">
        <Link href="/" className="back-link"><ArrowLeft size={17} /> 返回比赛列表</Link>
        <div className="auth-title"><div className="auth-icon"><ShieldCheck size={24} /></div><div><p className="eyebrow">Football Analyst</p><h1>{mode === "login" ? "欢迎回来" : "创建账号"}</h1></div></div>
        <p className="auth-copy">{mode === "login" ? "登录后查看你已获授权的比赛分析。" : "注册后可查看第一场比赛的完整分析，其他比赛需管理员开通。"}</p>
        <div className="auth-tabs" role="tablist" aria-label="账号操作">
          <Link href="/login" className={mode === "login" ? "auth-tab active" : "auth-tab"}>登录</Link>
          <Link href="/register" className={mode === "register" ? "auth-tab active" : "auth-tab"}>注册</Link>
        </div>
        <form onSubmit={submitCredentials} className="auth-form">
            <label htmlFor="email">邮箱地址</label>
            <div className="input-wrap"><Mail size={18} /><input id="email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@example.com" autoComplete="email" /></div>
            <div className="field-heading"><label htmlFor="password">{mode === "login" ? "登录密码" : "设置密码"}</label>{mode === "login" && <Link href="/forgot-password" className="field-link">忘记密码？</Link>}</div>
            <div className="input-wrap"><KeyRound size={18} /><input id="password" type={showPassword ? "text" : "password"} required minLength={6} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="至少 6 位" autoComplete={mode === "login" ? "current-password" : "new-password"} /><button type="button" className="password-toggle" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? "隐藏密码" : "显示密码"} title={showPassword ? "隐藏密码" : "显示密码"}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div>
            {mode === "register" && <><label htmlFor="confirm-password">确认密码</label><div className="input-wrap"><KeyRound size={18} /><input id="confirm-password" type={showConfirmPassword ? "text" : "password"} required minLength={6} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="再次输入密码" autoComplete="new-password" /><button type="button" className="password-toggle" onClick={() => setShowConfirmPassword((visible) => !visible)} aria-label={showConfirmPassword ? "隐藏确认密码" : "显示确认密码"} title={showConfirmPassword ? "隐藏确认密码" : "显示确认密码"}>{showConfirmPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div></>}
            {mode === "register" && <div className="captcha-block"><label htmlFor="captcha">随机验证码</label><div className="captcha-row"><span className="captcha-code" aria-label="随机验证码">{captcha || "加载中"}</span><button type="button" className="captcha-refresh" onClick={refreshCaptcha} title="换一个验证码" aria-label="换一个验证码"><RefreshCw size={16} /><span>换一组</span></button></div><input id="captcha" className="code-input" required value={captchaInput} onChange={(event) => setCaptchaInput(event.target.value)} placeholder="输入上面的验证码" autoComplete="off" /></div>}
            <button className="primary-button" disabled={busy}>{busy ? "处理中..." : mode === "login" ? "登录" : "注册"}</button>
        </form>
        {message && <p className="auth-message"><AlertCircle size={16} />{message}</p>}
      </div>
    </main>
  );
}

function createCaptcha(previous = "") {
  let next = String(Math.floor(1000 + Math.random() * 9000));
  while (next === previous) next = String(Math.floor(1000 + Math.random() * 9000));
  return next;
}

function formatAuthError(error: string, mode: "login" | "register") {
  if (error.toLowerCase().includes("invalid login credentials")) return "邮箱或密码不正确。";
  if (error.toLowerCase().includes("email not confirmed")) return "邮箱尚未确认，请先在 Supabase 关闭 Confirm email，或完成邮箱确认。";
  if (error.toLowerCase().includes("user already registered")) return "该邮箱已经注册，请切换到登录。";
  if (error.toLowerCase().includes("email address not authorized")) return "当前 Supabase 邮件服务只允许项目成员邮箱，请先使用项目所有者邮箱测试。";
  return mode === "register" ? `注册失败：${error}` : `登录失败：${error}`;
}
