"use client";

import Link from "next/link";
import { LogIn, LogOut, UserRound } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getBrowserClient } from "../lib/supabase/browser";

export function AuthButton() {
  const [email, setEmail] = useState<string | null>(null);
  const client = useMemo(() => getBrowserClient(), []);

  useEffect(() => {
    if (!client) return;
    client.auth.getUser().then(({ data }) => setEmail(data.user?.email ?? null));
    const { data } = client.auth.onAuthStateChange((_event, session) => setEmail(session?.user?.email ?? null));
    return () => data.subscription.unsubscribe();
  }, [client]);

  if (!email) {
    return <Link href="/login" className="auth-button"><LogIn size={17} />邮箱登录</Link>;
  }

  return (
    <button className="auth-button" onClick={async () => { await client?.auth.signOut(); window.location.reload(); }}>
      <UserRound size={17} /><span>{email}</span><LogOut size={16} />
    </button>
  );
}
