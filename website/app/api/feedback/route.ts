import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );

  try {
    const body = await req.json();
    const { id, table = "jobs", liked } = body as {
      id: number;
      table?: string;
      liked: boolean;
    };

    if (!id || liked === undefined) {
      return NextResponse.json({ error: "Missing id or liked" }, { status: 400 });
    }

    const { error } = await supabase.from("job_feedback").upsert(
      {
        job_id: id,
        source_table: table,
        liked,
        rated_at: new Date().toISOString(),
      },
      { onConflict: "job_id,source_table" }
    );

    if (error) throw error;
    return NextResponse.json({ ok: true });
  } catch (err: unknown) {
    console.error("Feedback error:", err);
    return NextResponse.json({ error: "Failed to save feedback" }, { status: 500 });
  }
}
