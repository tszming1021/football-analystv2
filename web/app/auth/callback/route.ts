import { NextResponse } from "next/server";
import { getServerClient } from "../../../lib/supabase/server";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const next = url.searchParams.get("next") || "/";
  const client = await getServerClient();
  if (code && client) await client.auth.exchangeCodeForSession(code);
  return NextResponse.redirect(new URL(next, url.origin));
}
