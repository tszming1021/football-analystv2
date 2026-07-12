import { NextResponse } from "next/server";
import { refreshMatchData, toRefreshResponse } from "../../../../lib/refresh";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const token = process.env.REFRESH_TOKEN;
  if (token && request.headers.get("x-refresh-token") !== token) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  try {
    const result = await refreshMatchData();
    return NextResponse.json(toRefreshResponse(result));
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : String(error)
      },
      { status: 500 }
    );
  }
}
