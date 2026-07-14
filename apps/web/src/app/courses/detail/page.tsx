"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { AppNav } from "@/components/AppNav";
import { apiFetch } from "@/lib/api";
import { Course, SERVICE_LABELS, getToken } from "@/lib/types";

type Lesson = { id: string; title: string; content: string | null; has_correction: boolean; sort_order: number };
type Material = { id: string; title: string; material_type: string; shipping_required: boolean };
type Media = { id: string; title: string; media_type: string; is_live_now: boolean; stream_url: string | null };
type Exam = { id: string; title: string; passing_score: number; status: string };

function CourseDetailInner() {
  const search = useSearchParams();
  const id = search.get("id") || "";
  const [course, setCourse] = useState<Course | null>(null);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [media, setMedia] = useState<Media[]>([]);
  const [exams, setExams] = useState<Exam[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      setError("コースIDが指定されていません");
      return;
    }
    const token = getToken();
    const opts = token ? { token } : {};
    Promise.all([
      apiFetch<Course>(`/api/v1/courses/${id}`, opts),
      apiFetch<Lesson[]>(`/api/v1/courses/${id}/lessons`, opts).catch(() => []),
      apiFetch<Material[]>(`/api/v1/materials?course_id=${id}`, opts).catch(() => []),
      apiFetch<Media[]>(`/api/v1/media?course_id=${id}`, opts).catch(() => []),
      apiFetch<Exam[]>(`/api/v1/exams?course_id=${id}`, opts).catch(() => []),
    ])
      .then(([c, l, m, v, e]) => {
        setCourse(c);
        setLessons(l);
        setMaterials(m);
        setMedia(v);
        setExams(e);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "取得失敗"));
  }, [id]);

  return (
    <div className="min-h-full bg-background">
      <AppNav />
      <main className="mx-auto w-full max-w-3xl px-6 pb-16">
        <Link href="/courses/" className="text-sm text-brand">
          ← コース一覧
        </Link>
        {error && <p className="mt-6 text-sm text-accent">{error}</p>}
        {course && (
          <>
            <h1 className="mt-6 font-display text-4xl text-brand-deep">{course.title}</h1>
            <p className="mt-2 text-sm text-muted">{course.description}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {(course.service_types || []).map((st) => (
                <span key={st} className="border border-line px-2 py-0.5 text-xs text-muted">
                  {SERVICE_LABELS[st] ?? st}
                </span>
              ))}
            </div>

            <section className="mt-10">
              <h2 className="text-lg font-medium">レッスン</h2>
              <ul className="mt-3 space-y-2 text-sm">
                {lessons.map((l) => (
                  <li key={l.id} className="border-b border-line py-2">
                    {l.sort_order}. {l.title}
                    {l.has_correction ? "（添削あり）" : ""}
                  </li>
                ))}
                {!lessons.length && <li className="text-muted">なし</li>}
              </ul>
            </section>

            <section className="mt-8">
              <h2 className="text-lg font-medium">紙・デジタル教材</h2>
              <ul className="mt-3 space-y-2 text-sm">
                {materials.map((m) => (
                  <li key={m.id}>
                    {m.title} · {m.material_type}
                    {m.shipping_required ? " · 発送あり" : ""}
                  </li>
                ))}
                {!materials.length && <li className="text-muted">なし</li>}
              </ul>
            </section>

            <section className="mt-8">
              <h2 className="text-lg font-medium">動画・ライブ配信</h2>
              <ul className="mt-3 space-y-2 text-sm">
                {media.map((m) => (
                  <li key={m.id}>
                    {m.title} · {m.media_type}
                    {m.is_live_now ? " · LIVE中" : ""}
                  </li>
                ))}
                {!media.length && <li className="text-muted">なし</li>}
              </ul>
            </section>

            <section className="mt-8">
              <h2 className="text-lg font-medium">試験・修了認定</h2>
              <ul className="mt-3 space-y-2 text-sm">
                {exams.map((e) => (
                  <li key={e.id}>
                    {e.title} · 合格点 {e.passing_score} · {e.status}
                  </li>
                ))}
                {!exams.length && <li className="text-muted">なし</li>}
              </ul>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

export default function CourseDetailPage() {
  return (
    <Suspense fallback={<div className="p-8 text-sm text-muted">読み込み中…</div>}>
      <CourseDetailInner />
    </Suspense>
  );
}
