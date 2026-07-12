// Supabase's URL and publishable key are safe to use in browser code.
// Environment variables remain the preferred deployment configuration; the
// fallbacks keep the public app usable if a host omits the public variables.
export const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "https://phvybpewvojirxnlybkw.supabase.co";

export const SUPABASE_ANON_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  "sb_publishable_yCbWtf_wlXkNAq7i866uQA_iBOC6mha";
