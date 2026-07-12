import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { cookies } from "next/headers";
import { getAdminClient } from "./admin";
import { SUPABASE_ANON_KEY, SUPABASE_URL } from "./config";

export async function getServerClient() {
  const cookieStore = await cookies();
  return createServerClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    global: {
      fetch: (input: RequestInfo | URL, init?: RequestInit) => fetch(input, { ...init, signal: AbortSignal.timeout(6_000) })
    },
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
        try {
          cookiesToSet.forEach(({ name, value, options }) => cookieStore.set(name, value, options));
        } catch {
          // Middleware refreshes the session when server components cannot write cookies.
        }
      }
    }
  });
}

export async function getCurrentUser() {
  const client = await getServerClient();
  if (!client) return null;
  try {
    const { data } = await client.auth.getUser();
    return data.user;
  } catch {
    return null;
  }
}

export async function canViewMatch(fixturePageId: string, firstMatchId: string | undefined) {
  const user = await getCurrentUser();
  if (!user) return { allowed: false, authenticated: false };
  if (fixturePageId === firstMatchId) return { allowed: true, authenticated: true };

  const client = await getServerClient();
  if (!client) return { allowed: false, authenticated: true };
  // Read permission server-side with the service role so RLS/session refresh
  // cannot leave a user locked after an administrator grants access.
  const admin = getAdminClient();
  const permissionClient = admin || client;
  const [{ data: profile }, { data: access }] = await Promise.all([
    permissionClient.from("profiles").select("access_all").eq("id", user.id).maybeSingle(),
    permissionClient.from("match_access").select("fixture_page_id").eq("user_id", user.id).eq("fixture_page_id", fixturePageId).maybeSingle()
  ]);

  return { allowed: Boolean(profile?.access_all || access), authenticated: true };
}
