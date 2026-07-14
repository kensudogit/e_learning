"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AppNav } from "@/components/AppNav";
import { apiFetch } from "@/lib/api";
import { Course, SERVICE_LABELS, getToken } from "@/lib/types";

const FILTERS = [
  { key: "", label: "すべて" },
  { key: "personal", label: "個人通信" },
  { key: "corporate", label: "法人" },
  { key: "qualification", label: "資格" },
  { key: "video_live", label: "動画・ライブ" },
  { key: "paper", label: "紙教材" },
  { key: "correction", label: "添削" },
  { key: "exam_cert", label: "試験・認定" },
];

export default function CoursesPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    setError(null);
    const q = filter ? `?service_type=${filter}` : "";
    apiFetch<Course[]>(`/api/v1/courses${q}`, token ? { token } : {})
      .then(setCourses)
      .catch((err) => setError(err instanceof Error ? err.message : "取得失敗"))
      .finally(() => setLoading(false));
  }, [filter]);

  const published = useMemo(
    () => courses.filter((c) => c.status === "PUBLISHED" || c.status === "published"),
    [courses],
  );

  async function apply(courseId: string, title: string) {
    const token = getToken();
    setMessage(null);
    try {
      await apiFetch("/api/v1/applications", {
        method: "POST",
        body: JSON.stringify({
          course_id: courseId,
          email: "learner@example.com",
          full_name: "受講者 太郎",
          source: "web",
        }),
      });
      if (token) {
        await apiFetch("/api/v1/enrollments", {
          method: "POST",
          token,
          body: JSON.stringify({ course_id: courseId }),
        });
      }
      setMessage(`「${title}」の申込・受講登録が完了しました`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "申込に失敗しました");
    }
  }

  return (
    <div className="min-h-full bg-background">
      <AppNav />
      <main className="mx-auto w-full max-w-4xl px-6 pb-16">
        <h1 className="font-display text-4xl text-brand-deep">コース一覧</h1>
        <p className="mt-2 text-sm text-muted">教育サービス種別で絞り込み、申込〜受講まで進められます</p>

        <div className="mt-6 flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.key || "all"}
              type="button"
              onClick={() => {
                setLoading(true);
                setFilter(f.key);
              }}
              className={`border px-3 py-1.5 text-xs transition-colors ${
                filter === f.key
                  ? "border-brand bg-brand text-white"
                  : "border-line bg-surface text-muted hover:border-brand"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {loading && <p className="mt-8 text-muted">読み込み中…</p>}
        {error && <p className="mt-8 text-sm text-accent">{error}</p>}
        {!loading && !error && !courses.length && (
          <p className="mt-8 text-sm text-muted">
            コースがありません。API 側で <code>python -m app.scripts.seed</code> を実行してください。
          </p>
        )}
        {!getToken() && courses.length > 0 && (
          <p className="mt-6 text-sm text-muted">
            公開コースを表示中。申込・受講登録には{" "}
            <Link href="/login" className="underline">
              ログイン
            </Link>
            が必要です。
          </p>
        )}
        {message && <p className="mt-6 text-sm text-brand-deep">{message}</p>}

        <ul className="mt-8 space-y-6">
          {(filter ? courses : published.length ? published : courses).map((course) => (
            <li key={course.id} className="border-b border-line pb-6">
              <p className="text-xs tracking-wide text-muted">
                {course.code} · {course.audience} · {course.status}
              </p>
              <h2 className="mt-1 text-xl font-medium">{course.title}</h2>
              {course.description && <p className="mt-1 text-sm text-muted">{course.description}</p>}
              <div className="mt-3 flex flex-wrap gap-2">
                {(course.service_types || []).map((st) => (
                  <span key={st} className="border border-line px-2 py-0.5 text-xs text-muted">
                    {SERVICE_LABELS[st] ?? st}
                  </span>
                ))}
              </div>
              <p className="mt-2 text-xs text-muted">
                {course.duration_days != null ? `${course.duration_days}日` : ""}
                {course.price != null ? ` / ¥${Number(course.price).toLocaleString()}` : ""}
                {course.qualification_name ? ` / ${course.qualification_name}` : ""}
              </p>
              <div className="mt-4 flex gap-3">
                <Link href={`/courses/${course.id}`} className="text-sm text-brand hover:text-brand-deep">
                  詳細
                </Link>
                <button
                  type="button"
                  onClick={() => apply(course.id, course.title)}
                  className="text-sm text-brand-deep underline"
                >
                  申し込む
                </button>
              </div>
            </li>
          ))}
        </ul>
      </main>
    </div>
  );
}
