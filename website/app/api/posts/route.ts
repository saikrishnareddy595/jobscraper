import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

export const dynamic = "force-dynamic";

export async function GET() {
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );

  try {
    const { data, error } = await supabase
      .from("linkedin_posts")
      .select("*")
      .eq("is_job_posting", true)
      .order("score", { ascending: false })
      .limit(200);

    if (error) throw error;
    return NextResponse.json(data ?? []);
  } catch (err: unknown) {
    console.error("Posts fetch error:", err);
    return NextResponse.json(
      { error: "Failed to fetch posts" },
      { status: 500 }
    );
  }
}
