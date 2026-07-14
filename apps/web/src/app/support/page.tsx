"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppNav } from "@/components/AppNav";
import { apiFetch } from "@/lib/api";

type Faq = {
  id: string;
  category: string;
  question: string;
  answer: string;
  view_count: number;
  helpful_count: number;
};

export default function SupportPage() {
  const [faqs, setFaqs] = useState<Faq[]>([]);
  const [openId, setOpenId] = useState<string | null>(null);
  const [email, setEmail] = useState("prospect@example.com");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [category, setCategory] = useState("enrollment");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Faq[]>("/api/v1/faqs").then(setFaqs).catch(() => setFaqs([]));
  }, []);

  async function openFaq(faq: Faq) {
    setOpenId(faq.id);
    await apiFetch<Faq>(`/api/v1/faqs/${faq.id}/view`, { method: "POST" });
  }

  async function helpful(id: string) {
    const updated = await apiFetch<Faq>(`/api/v1/faqs/${id}/helpful`, { method: "POST" });
    setFaqs((prev) => prev.map((f) => (f.id === id ? updated : f)));
  }

  async function onInquiry(e: FormEvent) {
    e.preventDefault();
    try {
      const inquiry = await apiFetch<{ id: string; answer: string | null }>("/api/v1/inquiries", {
        method: "POST",
        body: JSON.stringify({ email, subject, body, category }),
      });
      setMessage(
        inquiry.answer
          ? `受付しました。FAQで自己解決できる可能性があります。→ ${inquiry.answer}`
          : "問い合わせを受け付けました",
      );
      // デモ: FAQ で解決したことにするボタン導線
      setSubject("");
      setBody("");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "送信失敗");
    }
  }

  return (
    <div className="min-h-full bg-background">
      <AppNav />
      <main className="mx-auto w-full max-w-3xl px-6 pb-16">
        <h1 className="font-display text-4xl text-brand-deep">FAQ・問い合わせ</h1>
        <p className="mt-2 text-sm text-muted">自己解決を促し、問い合わせ件数を削減します</p>

        <section className="mt-8 space-y-3">
          {faqs.map((faq) => (
            <div key={faq.id} className="border-b border-line pb-3">
              <button type="button" className="text-left text-base font-medium" onClick={() => openFaq(faq)}>
                {faq.question}
              </button>
              {openId === faq.id && (
                <div className="mt-2 text-sm text-muted">
                  <p>{faq.answer}</p>
                  <button type="button" className="mt-2 text-brand underline" onClick={() => helpful(faq.id)}>
                    役立った（{faq.helpful_count}）
                  </button>
                </div>
              )}
            </div>
          ))}
        </section>

        <section className="mt-12">
          <h2 className="text-lg font-medium">問い合わせフォーム</h2>
          {message && <p className="mt-3 text-sm text-brand-deep">{message}</p>}
          <form onSubmit={onInquiry} className="mt-4 space-y-3">
            <input
              className="w-full border border-line bg-surface px-3 py-2 text-sm"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              required
            />
            <select
              className="w-full border border-line bg-surface px-3 py-2 text-sm"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="enrollment">受講・申込</option>
              <option value="correction">添削</option>
              <option value="certificate">修了認定</option>
              <option value="corporate">法人</option>
              <option value="general">その他</option>
            </select>
            <input
              className="w-full border border-line bg-surface px-3 py-2 text-sm"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="件名"
              required
            />
            <textarea
              className="min-h-24 w-full border border-line bg-surface px-3 py-2 text-sm"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="内容"
              required
            />
            <button type="submit" className="h-10 bg-brand px-5 text-sm text-white hover:bg-brand-deep">
              送信
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}
