"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { AppNav } from "@/components/AppNav";
import { apiFetch } from "@/lib/api";
import { getToken } from "@/lib/types";

type Assignment = {
  id: string;
  enrollment_id: string;
  title: string;
  body: string;
  status: string;
  feedback: string | null;
  turnaround_hours: number | null;
};

type Enrollment = { id: string; course_id: string; status: string };

export default function AssignmentsPage() {
  const [mine, setMine] = useState<Assignment[]>([]);
  const [pending, setPending] = useState<Assignment[]>([]);
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [title, setTitle] = useState("添削課題");
  const [body, setBody] = useState("");
  const [enrollmentId, setEnrollmentId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function refresh(token: string) {
    const [m, e] = await Promise.all([
      apiFetch<Assignment[]>("/api/v1/assignments/mine", { token }),
      apiFetch<Enrollment[]>("/api/v1/enrollments", { token }),
    ]);
    setMine(m);
    setEnrollments(e);
    if (!enrollmentId && e[0]) setEnrollmentId(e[0].id);
    try {
      const p = await apiFetch<Assignment[]>("/api/v1/assignments/pending", { token });
      setPending(p);
    } catch {
      setPending([]);
    }
  }

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setError("ログインが必要です");
      return;
    }
    refresh(token).catch((err) => setError(err instanceof Error ? err.message : "取得失敗"));
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token || !enrollmentId) return;
    try {
      await apiFetch("/api/v1/assignments/submit", {
        method: "POST",
        token,
        body: JSON.stringify({ enrollment_id: enrollmentId, title, body }),
      });
      setBody("");
      setMessage("提出しました");
      await refresh(token);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "提出失敗");
    }
  }

  async function feedback(id: string) {
    const token = getToken();
    if (!token) return;
    try {
      await apiFetch(`/api/v1/assignments/${id}/feedback`, {
        method: "POST",
        token,
        body: JSON.stringify({ feedback: "よく書けています。次は具体例を増やしましょう。", status: "returned" }),
      });
      setMessage("添削を返却しました（運用工数削減の計測対象）");
      await refresh(token);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "返却失敗");
    }
  }

  return (
    <div className="min-h-full bg-background">
      <AppNav />
      <main className="mx-auto w-full max-w-3xl px-6 pb-16">
        <h1 className="font-display text-4xl text-brand-deep">添削課題</h1>
        <p className="mt-2 text-sm text-muted">提出と返却。平均ターンアラウンドで運用工数を可視化します</p>
        {error && (
          <p className="mt-6 text-sm text-accent">
            {error} <Link href="/login">ログイン</Link>
          </p>
        )}
        {message && <p className="mt-4 text-sm text-brand-deep">{message}</p>}

        <form onSubmit={onSubmit} className="mt-8 space-y-3">
          <label className="block text-sm">
            <span className="text-muted">受講</span>
            <select
              className="mt-1 w-full border border-line bg-surface px-3 py-2"
              value={enrollmentId}
              onChange={(e) => setEnrollmentId(e.target.value)}
            >
              {enrollments.map((en) => (
                <option key={en.id} value={en.id}>
                  {en.id.slice(0, 8)}… ({en.status})
                </option>
              ))}
            </select>
          </label>
          <input
            className="w-full border border-line bg-surface px-3 py-2 text-sm"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="タイトル"
          />
          <textarea
            className="min-h-28 w-full border border-line bg-surface px-3 py-2 text-sm"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="本文"
            required
          />
          <button type="submit" className="h-10 bg-brand px-5 text-sm text-white hover:bg-brand-deep">
            提出する
          </button>
        </form>

        <section className="mt-12">
          <h2 className="text-lg font-medium">自分の提出</h2>
          <ul className="mt-3 space-y-3 text-sm">
            {mine.map((a) => (
              <li key={a.id} className="border-b border-line pb-3">
                <p className="font-medium">{a.title}</p>
                <p className="text-muted">{a.status}</p>
                {a.feedback && <p className="mt-1">FB: {a.feedback}</p>}
              </li>
            ))}
          </ul>
        </section>

        {pending.length > 0 && (
          <section className="mt-12">
            <h2 className="text-lg font-medium">添削待ち（運用）</h2>
            <ul className="mt-3 space-y-3 text-sm">
              {pending.map((a) => (
                <li key={a.id} className="flex items-start justify-between gap-4 border-b border-line pb-3">
                  <div>
                    <p className="font-medium">{a.title}</p>
                    <p className="text-muted">{a.body.slice(0, 80)}</p>
                  </div>
                  <button type="button" className="shrink-0 text-brand underline" onClick={() => feedback(a.id)}>
                    返却
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>
    </div>
  );
}
