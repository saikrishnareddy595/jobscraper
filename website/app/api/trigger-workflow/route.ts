import { NextResponse } from "next/server";

const GITHUB_OWNER = process.env.GITHUB_OWNER ?? "saikrishnareddy595";
const GITHUB_REPO = process.env.GITHUB_REPO ?? "jobscraper";
const WORKFLOW_FILE = process.env.GITHUB_WORKFLOW_FILE ?? "scrape.yml";
const BRANCH = process.env.GITHUB_BRANCH ?? "main";

export async function POST() {
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    return NextResponse.json(
      { error: "GITHUB_TOKEN is not configured on the server." },
      { status: 500 }
    );
  }

  const url = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/${WORKFLOW_FILE}/dispatches`;

  const res = await fetch(url, {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${token}`,
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ ref: BRANCH }),
  });

  if (res.status === 204) {
    return NextResponse.json({ success: true, message: "Workflow triggered successfully." });
  }

  const body = await res.json().catch(() => ({ message: res.statusText }));
  return NextResponse.json(
    { error: body.message ?? "GitHub API error", status: res.status },
    { status: res.status }
  );
}

export async function GET() {
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    return NextResponse.json({ error: "GITHUB_TOKEN not configured" }, { status: 500 });
  }

  const url = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/${WORKFLOW_FILE}/runs?per_page=5`;

  const res = await fetch(url, {
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${token}`,
      "X-GitHub-Api-Version": "2022-11-28",
    },
    next: { revalidate: 0 },
  });

  if (!res.ok) {
    return NextResponse.json({ error: "Failed to fetch run history" }, { status: res.status });
  }

  const data = await res.json();
  const runs = (data.workflow_runs ?? []).map((r: Record<string, unknown>) => ({
    id: r.id,
    status: r.status,
    conclusion: r.conclusion,
    created_at: r.created_at,
    html_url: r.html_url,
    run_number: r.run_number,
  }));

  return NextResponse.json({ runs });
}
