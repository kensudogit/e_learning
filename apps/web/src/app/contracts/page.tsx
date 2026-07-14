"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { AppNav } from "@/components/AppNav";
import { apiFetch } from "@/lib/api";
import { getToken } from "@/lib/types";

type Course = { id: string; code: string; title: string; price: string | number | null };
type Contract = {
  id: string;
  contract_no: string;
  contract_type: string;
  channel: string;
  status: string;
  total_amount: string | number;
  discount_amount: string | number;
  payment_method: string;
  start_date: string | null;
  end_date: string | null;
};
type Doc = { id: string; doc_type: string; document_no: string; amount: string | number };

const CHANNELS = [
  { v: "web", l: "Web" },
  { v: "phone", l: "電話" },
  { v: "mail", l: "郵送" },
  { v: "agency", l: "代理店" },
];

export default function ContractsPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [contractType, setContractType] = useState("individual");
  const [channel, setChannel] = useState("web");
  const [coupon, setCoupon] = useState("");
  const [referral, setReferral] = useState("");
  const [payment, setPayment] = useState("lump_sum");
  const [installments, setInstallments] = useState(3);
  const [message, setMessage] = useState<string | null>(null);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  async function load(token: string) {
    const [c, ct] = await Promise.all([
      apiFetch<Course[]>("/api/v1/courses", { token }),
      apiFetch<Contract[]>("/api/v1/contracts", { token }),
    ]);
    setCourses(c);
    setContracts(ct);
  }

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setMessage("ログインが必要です");
      return;
    }
    load(token).catch((e) => setMessage(e instanceof Error ? e.message : "取得失敗"));
  }, []);

  function toggle(id: string) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token || !selected.length) return;
    const start = new Date().toISOString().slice(0, 10);
    const end = new Date(Date.now() + 90 * 86400000).toISOString().slice(0, 10);
    try {
      const contract = await apiFetch<Contract>("/api/v1/contracts", {
        method: "POST",
        token,
        body: JSON.stringify({
          contract_type: contractType,
          channel,
          coupon_code: coupon || null,
          referral_code: referral || null,
          campaign_name: coupon ? "春キャンペーン" : null,
          start_date: start,
          end_date: end,
          payment_method: payment,
          installment_count: payment === "installment" ? installments : null,
          items: selected.map((course_id) => ({ course_id })),
        }),
      });
      setMessage(`契約作成: ${contract.contract_no}（¥${Number(contract.total_amount).toLocaleString()}）`);
      setActiveId(contract.id);
      setSelected([]);
      await load(token);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "申込失敗");
    }
  }

  async function issueDoc(doc_type: string) {
    const token = getToken();
    if (!token || !activeId) return;
    const doc = await apiFetch<Doc>(`/api/v1/contracts/${activeId}/documents`, {
      method: "POST",
      token,
      body: JSON.stringify({ doc_type }),
    });
    setDocs((d) => [doc, ...d]);
    setMessage(`${doc.doc_type} 発行: ${doc.document_no}`);
  }

  async function cancelContract(id: string) {
    const token = getToken();
    if (!token) return;
    await apiFetch(`/api/v1/contracts/${id}/changes`, {
      method: "POST",
      token,
      body: JSON.stringify({ change_type: "cancel", reason: "受講者都合" }),
    });
    setMessage("キャンセルしました");
    await load(token);
  }

  return (
    <div className="min-h-full bg-background">
      <AppNav />
      <main className="mx-auto w-full max-w-4xl px-6 pb-16">
        <h1 className="font-display text-4xl text-brand-deep">申込・契約</h1>
        <p className="mt-2 text-sm text-muted">
          個人/法人・受付チャネル・複数講座・クーポン・分割払い・見積/請求/領収 · 契約時に紙教材の発送予定を自動作成
        </p>
        {message && <p className="mt-4 text-sm text-brand-deep">{message}</p>}
        {!getToken() && (
          <p className="mt-4 text-sm">
            <Link href="/login" className="text-brand underline">
              ログインへ
            </Link>
          </p>
        )}

        <form onSubmit={onSubmit} className="mt-8 space-y-4 border-b border-line pb-8">
          <div className="flex flex-wrap gap-4 text-sm">
            <label>
              種別{" "}
              <select className="border border-line bg-surface px-2 py-1" value={contractType} onChange={(e) => setContractType(e.target.value)}>
                <option value="individual">個人</option>
                <option value="corporate">法人一括</option>
              </select>
            </label>
            <label>
              受付{" "}
              <select className="border border-line bg-surface px-2 py-1" value={channel} onChange={(e) => setChannel(e.target.value)}>
                {CHANNELS.map((c) => (
                  <option key={c.v} value={c.v}>
                    {c.l}
                  </option>
                ))}
              </select>
            </label>
            <label>
              支払{" "}
              <select className="border border-line bg-surface px-2 py-1" value={payment} onChange={(e) => setPayment(e.target.value)}>
                <option value="lump_sum">一括</option>
                <option value="installment">分割</option>
                <option value="invoice">請求書払い</option>
              </select>
            </label>
            {payment === "installment" && (
              <label>
                回数{" "}
                <input
                  type="number"
                  min={2}
                  max={24}
                  className="w-16 border border-line px-2 py-1"
                  value={installments}
                  onChange={(e) => setInstallments(Number(e.target.value))}
                />
              </label>
            )}
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <input
              className="border border-line bg-surface px-3 py-2"
              placeholder="クーポンコード"
              value={coupon}
              onChange={(e) => setCoupon(e.target.value)}
            />
            <input
              className="border border-line bg-surface px-3 py-2"
              placeholder="紹介コード"
              value={referral}
              onChange={(e) => setReferral(e.target.value)}
            />
          </div>
          <ul className="space-y-2 text-sm">
            {courses.map((c) => (
              <li key={c.id}>
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={selected.includes(c.id)} onChange={() => toggle(c.id)} />
                  {c.code} {c.title}
                  {c.price != null ? ` · ¥${Number(c.price).toLocaleString()}` : ""}
                </label>
              </li>
            ))}
          </ul>
          <button type="submit" className="h-10 bg-brand px-5 text-sm text-white hover:bg-brand-deep">
            同時申込する
          </button>
        </form>

        <section className="mt-8">
          <h2 className="text-lg font-medium">契約一覧</h2>
          <ul className="mt-4 space-y-4 text-sm">
            {contracts.map((ct) => (
              <li key={ct.id} className="border-b border-line pb-4">
                <p className="font-medium">
                  {ct.contract_no} · {ct.contract_type} · {ct.channel} · {ct.status}
                </p>
                <p className="text-muted">
                  ¥{Number(ct.total_amount).toLocaleString()}（割引 ¥{Number(ct.discount_amount).toLocaleString()}） /{" "}
                  {ct.payment_method} / {ct.start_date}〜{ct.end_date}
                </p>
                <div className="mt-2 flex flex-wrap gap-3">
                  <button type="button" className="text-brand underline" onClick={() => setActiveId(ct.id)}>
                    選択
                  </button>
                  <button type="button" className="text-muted underline" onClick={() => cancelContract(ct.id)}>
                    キャンセル
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </section>

        {activeId && (
          <section className="mt-8">
            <h2 className="text-lg font-medium">書類発行</h2>
            <div className="mt-3 flex gap-3 text-sm">
              <button type="button" className="border border-line px-3 py-1.5" onClick={() => issueDoc("quote")}>
                見積
              </button>
              <button type="button" className="border border-line px-3 py-1.5" onClick={() => issueDoc("invoice")}>
                請求書
              </button>
              <button type="button" className="border border-line px-3 py-1.5" onClick={() => issueDoc("receipt")}>
                領収書
              </button>
              <Link href="/payments" className="border border-line px-3 py-1.5 text-brand">
                入金管理へ
              </Link>
              <Link href="/shipping" className="border border-line px-3 py-1.5 text-brand">
                教材発送へ
              </Link>
            </div>
            <p className="mt-2 text-xs text-muted">
              紙教材ありの講座は契約作成時に発送予定が自動登録されます。入金は「入金」画面で記録できます。
            </p>
            <ul className="mt-4 space-y-1 text-sm text-muted">
              {docs.map((d) => (
                <li key={d.id}>
                  {d.doc_type} {d.document_no} · ¥{Number(d.amount).toLocaleString()}
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>
    </div>
  );
}
