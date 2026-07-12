"use client";

import Link from "next/link";
import { ArrowLeft, Check, LoaderCircle, ShieldCheck, X } from "lucide-react";
import { useEffect, useState } from "react";

type AdminUser = { id: string; email: string; accessAll: boolean; createdAt: string; confirmed: boolean };

export default function AdminPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState("");

  async function loadUsers() {
    setLoading(true); setMessage("");
    const response = await fetch("/api/admin/users", { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) setMessage(data.error || "无法加载用户");
    else setUsers(data.users || []);
    setLoading(false);
  }

  async function changeAccess(user: AdminUser) {
    setBusyId(user.id); setMessage("");
    const response = await fetch(user.accessAll ? "/api/admin/revoke-all" : "/api/admin/grant-all", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ userId: user.id })
    });
    const data = await response.json();
    if (!response.ok) setMessage(data.error || "操作失败");
    else setUsers((current) => current.map((item) => item.id === user.id ? { ...item, accessAll: !user.accessAll } : item));
    setBusyId(null);
  }

  useEffect(() => { void loadUsers(); }, []);

  return <main className="shell admin-shell">
    <header className="topbar"><div><p className="eyebrow">Football Analyst</p><h1>管理员后台</h1></div><Link href="/" className="back-link"><ArrowLeft size={17} /> 返回比赛列表</Link></header>
    <section className="admin-intro"><div><h2>用户权限</h2><p>开通“全部比赛”后，该用户可以查看所有比赛的完整分析。</p></div><button className="secondary-button" onClick={() => void loadUsers()} disabled={loading}>刷新列表</button></section>
    {message && <p className="admin-error">{message}</p>}
    <section className="admin-table-wrap"><table className="admin-table"><thead><tr><th>用户邮箱</th><th>注册时间</th><th>邮箱状态</th><th>全部比赛</th><th>操作</th></tr></thead><tbody>{loading ? <tr><td colSpan={5} className="admin-empty">正在加载...</td></tr> : users.map((user) => <tr key={user.id}><td><strong>{user.email}</strong></td><td>{new Date(user.createdAt).toLocaleString("zh-CN")}</td><td><span className={user.confirmed ? "user-status confirmed" : "user-status"}>{user.confirmed ? "已确认" : "未确认"}</span></td><td>{user.accessAll ? <span className="access-status granted"><Check size={15} />已开通</span> : <span className="access-status"><X size={15} />未开通</span>}</td><td><button className={user.accessAll ? "access-button revoke" : "access-button"} onClick={() => void changeAccess(user)} disabled={busyId === user.id}>{busyId === user.id ? <LoaderCircle size={15} className="spin" /> : <ShieldCheck size={15} />}{user.accessAll ? "取消全部权限" : "开通全部比赛"}</button></td></tr>)}</tbody></table>{!loading && users.length === 0 && <p className="admin-empty">暂无注册用户</p>}</section>
  </main>;
}
