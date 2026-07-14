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

type Master = {
  id: string;
  code: string;
  title: string;
  max_score: number;
  requires_correction: boolean;
};

type Correction = {
  id: string;
  score: number | null;
  status: string;
  feedback: string | null;
  turnaround_hours: number | null;
  corrected_at: string;
};

type Enrollment = { id: string; course_id: string; status: string };

export default function AssignmentsPage() {
  const [mine, setMine] = useState<Assignment[]>([]);
  const [pending, setPending] = useState<Assignment[]>([]);
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [masters, setMasters] = useState<Master[]>([]);
  const [corrections, setCorrections] = useState<Correction[]>([]);
  const [assignmentId, setAssignmentId] = useState("");
  const [title, setTitle] = useState("添削課題");
  const [body, setBody] = useState("");
  const [enrollmentId, setEnrollmentId] = useState("");
  const [score, setScore] = useState(85);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function refresh(token: string, enrollId?: string) {
    const eid = enrollId || enrollmentId;
    const [m, e, corr] = await Promise.all([
      apiFetch<Assignment[]>("/api/v1/assignments/mine", { token }),
      apiFetch<Enrollment[]>("/api/v1/enrollments", { token }),
      apiFetch<Correction[]>("/api/v1/assignments/corrections", { token }),
    ]);
    setMine(m);
    setEnrollments(e);
    setCorrections(corr);
    const nextEnroll = eid || e[0]?.id || "";
    if (!enrollmentId && e[0]) setEnrollmentId(e[0].id);
    if (nextEnroll) {
      try {
        const mastersRes = await apiFetch<Master[]>(
          `/api/v1/assignments/masters?enrollment_id=${encodeURIComponent(nextEnroll)}`,
          { token },
        );
        setMasters(mastersRes);
        if (mastersRes[0] && !assignmentId) {
          setAssignmentId(mastersRes[0].id);
          setTitle(mastersRes[0].title);
        }
      } catch {
        setMasters([]);
      }
    }
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

  async function onEnrollmentChange(id: string) {
    setEnrollmentId(id);
    setAssignmentId("");
    const token = getToken();
    if (!token) return;
    await refresh(token, id);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token || !enrollmentId) return;
    try {
      await apiFetch("/api/v1/assignments/submit", {
        method: "POST",
        token,
        body: JSON.stringify({
          enrollment_id: enrollmentId,
          title,
          body,
          assignment_id: assignmentId || null,
        }),
      });
      setBody("");
      setMessage("提出しました（学習履歴に記録）");
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
        body: JSON.stringify({
          feedback: "よく書けています。次は具体例を増やしましょう。",
          status: "returned",
          score,
          assignment_id: assignmentId || null,
        }),
      });
      setMessage(`添削を返却しました（成績 ${score} 点・CorrectionResult 連携）`);
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
        <p className="mt-2 text-sm text-muted">
          課題マスタ提出・返却・点数。添削結果は成績・学習履歴に反映されます
        </p>
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
              onChange={(e) => onEnrollmentChange(e.target.value)}
            >
              {enrollments.map((en) => (
                <option key={en.id} value={en.id}>
                  {en.id.slice(0, 8)}… ({en.status})
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className="text-muted">課題マスタ</span>
            <select
              className="mt-1 w-full border border-line bg-surface px-3 py-2"
              value={assignmentId}
              onChange={(e) => {
                const id = e.target.value;
                setAssignmentId(id);
                const m = masters.find((x) => x.id === id);
                if (m) setTitle(m.title);
              }}
            >
              <option value="">自由題（マスタなし）</option>
              {masters.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.code} {m.title}
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
                <p className="text-muted">
                  {a.status}
                  {a.turnaround_hours != null ? ` · TAT ${a.turnaround_hours}h` : ""}
                </p>
                {a.feedback && <p className="mt-1">FB: {a.feedback}</p>}
              </li>
            ))}
          </ul>
        </section>

        <section className="mt-12">
          <h2 className="text-lg font-medium">添削結果（成績連携）</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {corrections.map((c) => (
              <li key={c.id} className="border-b border-line py-2">
                {c.score != null ? `${c.score}点` : "未採点"} · {c.status}
                {c.turnaround_hours != null ? ` · TAT ${c.turnaround_hours}h` : ""}
                {c.feedback ? ` · ${c.feedback.slice(0, 60)}` : ""}
              </li>
            ))}
            {!corrections.length && <li className="text-muted">まだありません</li>}
          </ul>
        </section>

        {pending.length > 0 && (
          <section className="mt-12">
            <h2 className="text-lg font-medium">添削待ち（運用）</h2>
            <label className="mt-2 block text-sm text-muted">
              返却点数{" "}
              <input
                type="number"
                min={0}
                max={100}
                className="ml-2 w-20 border border-line px-2 py-1"
                value={score}
                onChange={(e) => setScore(Number(e.target.value))}
              />
            </label>
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
