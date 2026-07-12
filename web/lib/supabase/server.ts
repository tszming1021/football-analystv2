import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function getServerClient() {
  const cookieStore = await cookies();
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return null;

  return createServerClient(url, key, {
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
  const { data } = await client.auth.getUser();
  return data.user;
}

export async function canViewMatch(fixturePageId: string, firstMatchId: string | undefined) {
  const user = await getCurrentUser();
  if (!user) return { allowed: false, authenticated: false };
  if (fixturePageId === firstMatchId) return { allowed: true, authenticated: true };

  const client = await getServerClient();
  if (!client) return { allowed: false, authenticated: true };
  const [{ data: profile }, { data: access }] = await Promise.all([
    client.from("profiles").select("access_all").eq("id", user.id).maybeSingle(),
    client.from("match_access").select("fixture_page_id").eq("user_id", user.id).eq("fixture_page_id", fixturePageId).maybeSingle()
  ]);

  return { allowed: Boolean(profile?.access_all || access), authenticated: true };
}
