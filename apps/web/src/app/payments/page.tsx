"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { AppNav } from "@/components/AppNav";
import { apiFetch } from "@/lib/api";
import { getToken } from "@/lib/types";

type Contract = {
  id: string;
  contract_no: string;
  status: string;
  total_amount: string | number;
  payment_method: string;
};
type Payment = {
  id: string;
  payment_no: string;
  contract_id: string | null;
  amount: string | number;
  method: string;
  status: string;
  paid_at: string | null;
  note: string | null;
};
type Installment = {
  id: string;
  installment_no: number;
  due_date: string;
  amount: string | number;
  paid: boolean;
  paid_at: string | null;
};

export default function PaymentsPage() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [installments, setInstallments] = useState<Installment[]>([]);
  const [contractId, setContractId] = useState("");
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("bank_transfer");
  const [note, setNote] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  async function refresh(token: string, cid?: string) {
    const [ct, pay] = await Promise.all([
      apiFetch<Contract[]>("/api/v1/contracts", { token }),
      apiFetch<Payment[]>(
        cid ? `/api/v1/payments?contract_id=${encodeURIComponent(cid)}` : "/api/v1/payments",
        { token },
      ),
    ]);
    setContracts(ct);
    setPayments(pay);
    const active = cid || contractId || ct[0]?.id || "";
    if (!contractId && ct[0]) setContractId(ct[0].id);
    if (active) {
      try {
        const inst = await apiFetch<Installment[]>(`/api/v1/contracts/${active}/installments`, {
          token,
        });
        setInstallments(inst);
      } catch {
        setInstallments([]);
      }
    }
  }

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setMessage("ログインが必要です");
      return;
    }
    refresh(token).catch((e) => setMessage(e instanceof Error ? e.message : "取得失敗"));
  }, []);

  async function onRecord(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token || !contractId || !amount) return;
    try {
      await apiFetch("/api/v1/payments", {
        method: "POST",
        token,
        body: JSON.stringify({
          contract_id: contractId,
          amount: Number(amount),
          method,
          status: "received",
          note: note || null,
        }),
      });
      setMessage("入金を記録しました");
      setAmount("");
      setNote("");
      await refresh(token, contractId);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "入金失敗");
    }
  }

  async function payInstallment(id: string) {
    const token = getToken();
    if (!token) return;
    try {
      await apiFetch(`/api/v1/payments/installments/${id}/pay`, { method: "POST", token });
      setMessage("分割回次を入金済みにしました");
      await refresh(token, contractId);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "分割入金失敗");
    }
  }

  async function onSelectContract(id: string) {
    setContractId(id);
    const token = getToken();
    if (!token) return;
    await refresh(token, id);
  }

  return (
    <div className="min-h-full bg-background">
      <AppNav />
      <main className="mx-auto w-full max-w-3xl px-6 pb-16">
        <h1 className="font-display text-4xl text-brand-deep">入金管理</h1>
        <p className="mt-2 text-sm text-muted">
          通信教育の一括・分割・請求書払いに対する入金記録（ゲートウェイ連携前の運用デモ）
        </p>
        {message && <p className="mt-4 text-sm text-brand-deep">{message}</p>}
        {!getToken() && (
          <Link href="/login" className="mt-4 inline-block text-brand underline">
            ログイン
          </Link>
        )}

        <form onSubmit={onRecord} className="mt-8 space-y-3 border-b border-line pb-8 text-sm">
          <label className="block">
            <span className="text-muted">契約</span>
            <select
              className="mt-1 w-full border border-line bg-surface px-3 py-2"
              value={contractId}
              onChange={(e) => onSelectContract(e.target.value)}
            >
              {contracts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.contract_no} · ¥{Number(c.total_amount).toLocaleString()} · {c.payment_method}
                </option>
              ))}
            </select>
          </label>
          <div className="flex flex-wrap gap-3">
            <input
              className="border border-line px-3 py-2"
              type="number"
              min={1}
              placeholder="金額"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
            />
            <select
              className="border border-line px-3 py-2"
              value={method}
              onChange={(e) => setMethod(e.target.value)}
            >
              <option value="bank_transfer">銀行振込</option>
              <option value="card">カード</option>
              <option value="convenience">コンビニ</option>
              <option value="invoice">請求書</option>
            </select>
            <input
              className="flex-1 border border-line px-3 py-2"
              placeholder="備考"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </div>
          <button type="submit" className="h-10 bg-brand px-5 text-white hover:bg-brand-deep">
            入金を記録
          </button>
        </form>

        {installments.length > 0 && (
          <section className="mt-8">
            <h2 className="text-lg font-medium">分割スケジュール</h2>
            <ul className="mt-3 space-y-2 text-sm">
              {installments.map((i) => (
                <li key={i.id} className="flex items-center justify-between border-b border-line py-2">
                  <span>
                    第{i.installment_no}回 · 期日 {i.due_date} · ¥{Number(i.amount).toLocaleString()} ·{" "}
                    {i.paid ? `入金済 ${i.paid_at?.slice(0, 10) ?? ""}` : "未入金"}
                  </span>
                  {!i.paid && (
                    <button type="button" className="text-brand underline" onClick={() => payInstallment(i.id)}>
                      入金する
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="mt-10">
          <h2 className="text-lg font-medium">入金履歴</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {payments.map((p) => (
              <li key={p.id} className="border-b border-line py-2">
                {p.payment_no} · ¥{Number(p.amount).toLocaleString()} · {p.method} · {p.status}
                {p.note ? ` · ${p.note}` : ""}
              </li>
            ))}
            {!payments.length && <li className="text-muted">入金記録はありません</li>}
          </ul>
        </section>
      </main>
    </div>
  );
}
