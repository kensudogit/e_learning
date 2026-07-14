export const SERVICE_LABELS: Record<string, string> = {
  personal: "個人通信教育",
  corporate: "法人研修",
  qualification: "資格講座",
  video_live: "動画・ライブ",
  paper: "紙教材",
  correction: "添削課題",
  exam_cert: "試験・修了認定",
};

export type Course = {
  id: string;
  code: string;
  title: string;
  description: string | null;
  status: string;
  audience: string;
  service_types: string[];
  duration_days: number | null;
  price: string | number | null;
  qualification_name: string | null;
  created_at: string;
};

export type KpiDashboard = {
  learner_count: number;
  active_enrollments: number;
  application_count: number;
  converted_applications: number;
  conversion_rate: number;
  retention_rate: number;
  renewed_enrollments: number;
  inquiry_count: number;
  inquiry_faq_resolved_rate: number;
  open_inquiries: number;
  pending_corrections: number;
  avg_correction_turnaround_hours: number | null;
  avg_product_launch_days: number | null;
  published_courses: number;
  draft_courses: number;
  by_service_type: Record<string, number>;
};

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}
