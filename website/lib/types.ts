// Job type union literals
export type JobType =
  | "full_time"
  | "contract"
  | "contract_to_hire"
  | "part_time";

export type RoleCategory =
  | "all"
  | "data_engineer"
  | "ai_engineer"
  | "ml_engineer"
  | "nlp_engineer"
  | "cv_engineer"
  | "data_scientist";

// A single job scraped by the Python pipeline
export interface Job {
  id: number;
  title: string;
  company: string;
  location: string;
  salary: number | null;
  url: string;
  source: string;
  posted_date: string;
  job_type: JobType | string;
  role_category: RoleCategory | string;
  score: number;
  llm_score?: number | null;
  llm_reason?: string | null;
  llm_summary?: string | null;
  skills?: string[] | null;
  easy_apply?: boolean | null;
  applicants?: number | null;
  description?: string | null;
  notes?: string | null;
  applied: boolean;
  saved: boolean;
  visa_sponsorship?: boolean | null; // true=sponsors, false=no, null=unknown
}

// A LinkedIn post scraped by the Python pipeline
export interface LinkedInPost {
  id: number;
  author_name: string;
  author_profile_url: string;
  author_headline: string;
  post_text: string;
  post_url: string;
  posted_date: string;
  score: number;
  role_category: string;
  extracted_title?: string | null;
  extracted_company?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  contact_linkedin?: string | null;
  applied?: boolean;
  saved?: boolean;
}

// Dashboard filter state
export interface Filters {
  role: RoleCategory;
  jobTypes: JobType[];
  sources: string[];
  minScore: number;
  remoteOnly: boolean;
  easyApplyOnly: boolean;
  visaFilter: "all" | "sponsors" | "no_sponsorship";
  search: string;
  sortBy: "score" | "date" | "salary";
}
