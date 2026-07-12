import Link from "next/link";
import { Settings } from "lucide-react";
import { getCurrentUser } from "../lib/supabase/server";
import { isAdminEmail } from "../lib/supabase/admin";

export async function AdminLink() {
  const user = await getCurrentUser();
  if (!isAdminEmail(user?.email)) return null;
  return <Link href="/admin" className="auth-button"><Settings size={17} />管理后台</Link>;
}
