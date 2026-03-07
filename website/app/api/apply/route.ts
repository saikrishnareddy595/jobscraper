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
    const { id, applied, saved, notes } = body as {
      id: number;
      applied?: boolean;
      saved?: boolean;
      notes?: string;
    };

    if (!id) {
      return NextResponse.json({ error: "Missing id" }, { status: 400 });
    }

    const update: Record<string, unknown> = {};
    if (applied !== undefined) update.applied = applied;
    if (saved !== undefined) update.saved = saved;
    if (notes !== undefined) update.notes = notes;

    const { error } = await supabase
      .from("jobs")
      .update(update)
      .eq("id", id);

    if (error) throw error;
    return NextResponse.json({ ok: true });
  } catch (err: unknown) {
    console.error("Apply update error:", err);
    return NextResponse.json(
      { error: "Failed to update job" },
      { status: 500 }
    );
  }
}
