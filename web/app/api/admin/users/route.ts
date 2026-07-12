import { NextResponse } from "next/server";
import { getCurrentUser } from "../../../../lib/supabase/server";
import { getAdminClient, isAdminEmail } from "../../../../lib/supabase/admin";

export async function GET() {
  const currentUser = await getCurrentUser();
  if (!isAdminEmail(currentUser?.email)) return NextResponse.json({ error: "无管理员权限" }, { status: 403 });
  const admin = getAdminClient();
  if (!admin) return NextResponse.json({ error: "服务器缺少 Supabase 管理配置" }, { status: 500 });

  const [{ data: authData, error: authError }, { data: profiles, error: profileError }] = await Promise.all([
    admin.auth.admin.listUsers({ page: 1, perPage: 1000 }),
    admin.from("profiles").select("id, email, access_all")
  ]);
  if (authError || profileError) return NextResponse.json({ error: authError?.message || profileError?.message }, { status: 500 });
  const profileMap = new Map((profiles || []).map((profile) => [profile.id, profile]));
  return NextResponse.json({ users: (authData.users || []).map((user) => ({
    id: user.id,
    email: user.email || profileMap.get(user.id)?.email || "",
    accessAll: Boolean(profileMap.get(user.id)?.access_all),
    createdAt: user.created_at,
    confirmed: Boolean(user.email_confirmed_at)
  })) });
}
