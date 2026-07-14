"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppNav } from "@/components/AppNav";
import { apiFetch } from "@/lib/api";
import { getToken } from "@/lib/types";

type Enrollment = {
  id: string;
  course_id: string;
  status: string;
  progress_percent: number;
  enrolled_at: string;
  renewed_at: string | null;
};

type Certificate = {
  id: string;
  certificate_no: string;
  title: string;
  issued_at: string;
};

type History = {
  id: string;
  enrollment_id: string;
  event_type: string;
  title: string;
  detail: string | null;
  occurred_at: string;
};

export default function MyLearningPage() {
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [certs, setCerts] = useState<Certificate[]>([]);
  const [history, setHistory] = useState<History[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  function load(token: string) {
    return Promise.all([
      apiFetch<Enrollment[]>("/api/v1/enrollments", { token }),
      apiFetch<Certificate[]>("/api/v1/certificates/mine", { token }),
      apiFetch<History[]>("/api/v1/learning/history", { token }),
    ]).then(([e, c, h]) => {
      setEnrollments(e);
      setCerts(c);
      setHistory(h);
    });
  }

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setError("ログインが必要です");
      return;
    }
    load(token).catch((err) => setError(err instanceof Error ? err.message : "取得失敗"));
  }, []);

  async function renew(id: string) {
    const token = getToken();
    if (!token) return;
    try {
      await apiFetch(`/api/v1/enrollments/${id}/renew`, { method: "POST", token });
      setMessage("継続更新しました");
      await load(token);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "更新失敗");
    }
  }

  async function takeExam(enrollmentId: string) {
    const token = getToken();
    if (!token) return;
    try {
      const exams = await apiFetch<{ id: string; course_id: string }[]>("/api/v1/exams", { token });
      const enrollment = enrollments.find((e) => e.id === enrollmentId);
      const exam = exams.find((e) => e.course_id === enrollment?.course_id);
      if (!exam) {
        setMessage("このコースに試験がありません");
        return;
      }
      const result = await apiFetch<{ score: number; status: string }>(`/api/v1/exams/${exam.id}/submit`, {
        method: "POST",
        token,
        body: JSON.stringify({
          enrollment_id: enrollmentId,
          answers: { q1: "yes", q2: "yes", q3: "no" },
        }),
      });
      setMessage(`試験結果: ${result.status}（${result.score}点）`);
      await load(token);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "試験失敗");
    }
  }

  return (
    <div className="min-h-full bg-background">
      <AppNav />
      <main className="mx-auto w-full max-w-3xl px-6 pb-16">
        <h1 className="font-display text-4xl text-brand-deep">マイ学習</h1>
        <p className="mt-2 text-sm text-muted">受講進捗・継続・試験・修了認定</p>
        {error && (
          <p className="mt-6 text-sm text-accent">
            {error} <Link href="/login">ログイン</Link>
          </p>
        )}
        {message && <p className="mt-4 text-sm text-brand-deep">{message}</p>}

        <ul className="mt-8 space-y-5">
          {enrollments.map((e) => (
            <li key={e.id} className="border-b border-line pb-5">
              <p className="text-xs text-muted">{e.status}</p>
              <p className="mt-1 text-lg">進捗 {e.progress_percent}%</p>
              <div className="mt-2 h-1.5 w-full bg-line">
                <div className="h-full bg-brand" style={{ width: `${e.progress_percent}%` }} />
              </div>
              <div className="mt-3 flex flex-wrap gap-4 text-sm">
                <button type="button" className="text-brand underline" onClick={() => renew(e.id)}>
                  継続する
                </button>
                <button type="button" className="text-brand underline" onClick={() => takeExam(e.id)}>
                  試験を受ける
                </button>
                <Link href={`/courses/detail/?id=${encodeURIComponent(e.course_id)}`} className="text-muted hover:text-brand">
                  コース詳細
                </Link>
              </div>
            </li>
          ))}
          {!enrollments.length && !error && <li className="text-muted">受講中のコースはありません</li>}
        </ul>

        <section className="mt-12">
          <h2 className="text-lg font-medium">修了認定</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {certs.map((c) => (
              <li key={c.id} className="border-b border-line py-2">
                {c.title} · {c.certificate_no}
              </li>
            ))}
            {!certs.length && <li className="text-muted">まだありません</li>}
          </ul>
        </section>

        <section className="mt-12">
          <h2 className="text-lg font-medium">学習履歴</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {history.map((h) => (
              <li key={h.id} className="border-b border-line py-2">
                <span className="text-muted">{h.occurred_at.slice(0, 16).replace("T", " ")}</span>
                {" · "}
                <span className="font-medium">{h.event_type}</span>
                {" · "}
                {h.title}
                {h.detail ? `（${h.detail}）` : ""}
              </li>
            ))}
            {!history.length && <li className="text-muted">学習・提出・試験の記録がここに溜まります</li>}
          </ul>
        </section>
      </main>
    </div>
  );
}
