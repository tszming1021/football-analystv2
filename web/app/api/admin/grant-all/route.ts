import { NextResponse } from "next/server";
import { getCurrentUser } from "../../../../lib/supabase/server";
import { getAdminClient, isAdminEmail } from "../../../../lib/supabase/admin";

export async function POST(request: Request) {
  const currentUser = await getCurrentUser();
  if (!isAdminEmail(currentUser?.email)) return NextResponse.json({ error: "无管理员权限" }, { status: 403 });
  const body = await request.json().catch(() => ({}));
  if (!body.userId) return NextResponse.json({ error: "缺少用户 ID" }, { status: 400 });
  const admin = getAdminClient();
  if (!admin) return NextResponse.json({ error: "服务器缺少 Supabase 管理配置" }, { status: 500 });

  const { data: userData, error: userError } = await admin.auth.admin.getUserById(body.userId);
  if (userError || !userData.user) return NextResponse.json({ error: userError?.message || "用户不存在" }, { status: 404 });
  const { error } = await admin.from("profiles").upsert({ id: body.userId, email: userData.user.email, access_all: true });
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ ok: true });
}
