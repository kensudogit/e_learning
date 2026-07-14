"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { AppNav } from "@/components/AppNav";
import { apiFetch } from "@/lib/api";
import { getToken } from "@/lib/types";

type Content = {
  id: string;
  title: string;
  format: string;
  sort_order: number;
  offline_available: boolean;
  course_id: string;
};
type Progress = { content_id: string; progress_percent: number; completed: boolean };
type Enrollment = { id: string; course_id: string; progress_percent: number };
type Quiz = { id: string; title: string; max_attempts: number; content_id: string };

export default function LearningPage() {
  const [contents, setContents] = useState<Content[]>([]);
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [enrollmentId, setEnrollmentId] = useState("");
  const [progress, setProgress] = useState<Progress[]>([]);
  const [quizzes, setQuizzes] = useState<Quiz[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [bookmarks, setBookmarks] = useState<{ id: string; content_id: string; note: string | null }[]>([]);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setMessage("ログインが必要です");
      return;
    }
    Promise.all([
      apiFetch<Content[]>("/api/v1/learning/contents", { token }),
      apiFetch<Enrollment[]>("/api/v1/enrollments", { token }),
      apiFetch<{ id: string; content_id: string; note: string | null }[]>("/api/v1/learning/bookmarks", { token }),
      apiFetch<Quiz[]>("/api/v1/learning/quizzes", { token }),
    ])
      .then(([c, e, b, q]) => {
        setContents(c);
        setEnrollments(e);
        setBookmarks(b);
        setQuizzes(q);
        if (e[0]) setEnrollmentId(e[0].id);
      })
      .catch((err) => setMessage(err instanceof Error ? err.message : "取得失敗"));
  }, []);

  useEffect(() => {
    const token = getToken();
    if (!token || !enrollmentId) return;
    apiFetch<Progress[]>(`/api/v1/learning/progress?enrollment_id=${enrollmentId}`, { token })
      .then(setProgress)
      .catch(() => setProgress([]));
  }, [enrollmentId]);

  async function markProgress(contentId: string, percent: number) {
    const token = getToken();
    if (!token || !enrollmentId) return;
    try {
      await apiFetch("/api/v1/learning/progress", {
        method: "POST",
        token,
        body: JSON.stringify({
          enrollment_id: enrollmentId,
          content_id: contentId,
          progress_percent: percent,
          deadline_at: new Date(Date.now() + 14 * 86400000).toISOString(),
        }),
      });
      setMessage(`進捗 ${percent}% を記録`);
      const p = await apiFetch<Progress[]>(`/api/v1/learning/progress?enrollment_id=${enrollmentId}`, { token });
      setProgress(p);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "進捗更新失敗（前提科目未完了の可能性）");
    }
  }

  async function bookmark(contentId: string) {
    const token = getToken();
    if (!token) return;
    const bm = await apiFetch<{ id: string; content_id: string; note: string | null }>("/api/v1/learning/bookmarks", {
      method: "POST",
      token,
      body: JSON.stringify({ content_id: contentId, note: "後で復習" }),
    });
    setBookmarks((b) => [...b, bm]);
  }

  async function takeQuiz(quizId: string) {
    const token = getToken();
    if (!token) return;
    try {
      const result = await apiFetch<{ score: number; passed: boolean; attempt_no: number }>(
        `/api/v1/learning/quizzes/${quizId}/submit`,
        {
          method: "POST",
          token,
          body: JSON.stringify({ answers: { q1: "yes" } }),
        },
      );
      setMessage(
        `理解度テスト: ${result.passed ? "合格" : "不合格"} ${result.score}点（${result.attempt_no}回目）`,
      );
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "受験失敗");
    }
  }

  async function remind(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token || !enrollmentId) return;
    try {
      await apiFetch("/api/v1/learning/reminders", {
        method: "POST",
        token,
        body: JSON.stringify({
          enrollment_id: enrollmentId,
          message: "学習が進んでいません。期限内に受講してください。",
          channel: "email",
        }),
      });
      setMessage("督促を送信しました");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "督促失敗（権限が必要な場合があります）");
    }
  }

  return (
    <div className="min-h-full bg-background">
      <AppNav />
      <main className="mx-auto w-full max-w-3xl px-6 pb-16">
        <h1 className="font-display text-4xl text-brand-deep">学習管理</h1>
        <p className="mt-2 text-sm text-muted">
          動画/PDF/テキスト/SCORM・順序・前提・進捗・ブックマーク・理解度テスト・督促・オフライン
        </p>
        {message && <p className="mt-4 text-sm text-brand-deep">{message}</p>}
        {!getToken() && (
          <Link href="/login" className="mt-4 inline-block text-brand underline">
            ログイン
          </Link>
        )}

        <label className="mt-6 block text-sm">
          受講選択
          <select
            className="mt-1 w-full border border-line bg-surface px-3 py-2"
            value={enrollmentId}
            onChange={(e) => setEnrollmentId(e.target.value)}
          >
            {enrollments.map((en) => (
              <option key={en.id} value={en.id}>
                {en.id.slice(0, 8)}… 進捗{en.progress_percent}%
              </option>
            ))}
          </select>
        </label>

        <ul className="mt-8 space-y-4">
          {contents.map((c) => {
            const p = progress.find((x) => x.content_id === c.id);
            return (
              <li key={c.id} className="border-b border-line pb-4 text-sm">
                <p className="font-medium">
                  {c.sort_order}. {c.title} · {c.format}
                  {c.offline_available ? " · オフライン可" : ""}
                </p>
                <p className="text-muted">進捗 {p?.progress_percent ?? 0}%</p>
                <div className="mt-2 flex flex-wrap gap-3">
                  <button type="button" className="text-brand underline" onClick={() => markProgress(c.id, 50)}>
                    50%
                  </button>
                  <button type="button" className="text-brand underline" onClick={() => markProgress(c.id, 100)}>
                    完了
                  </button>
                  <button type="button" className="text-muted underline" onClick={() => bookmark(c.id)}>
                    ブックマーク
                  </button>
                </div>
              </li>
            );
          })}
          {!contents.length && <li className="text-muted">学習コンテンツがありません（管理者で登録）</li>}
        </ul>

        <section className="mt-10">
          <h2 className="text-lg font-medium">理解度テスト（再受験可）</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {quizzes.map((q) => (
              <li key={q.id} className="flex justify-between border-b border-line py-2">
                <span>
                  {q.title}（最大{q.max_attempts}回）
                </span>
                <button type="button" className="text-brand underline" onClick={() => takeQuiz(q.id)}>
                  受験
                </button>
              </li>
            ))}
            {!quizzes.length && <li className="text-muted">なし</li>}
          </ul>
        </section>

        <section className="mt-10">
          <h2 className="text-lg font-medium">ブックマーク</h2>
          <ul className="mt-2 text-sm text-muted">
            {bookmarks.map((b) => (
              <li key={b.id}>
                {b.content_id.slice(0, 8)}… {b.note}
              </li>
            ))}
          </ul>
        </section>

        <form onSubmit={remind} className="mt-10">
          <button type="submit" className="h-10 border border-line px-5 text-sm hover:border-brand">
            未受講督促を送る
          </button>
        </form>
      </main>
    </div>
  );
}
