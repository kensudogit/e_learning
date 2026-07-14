"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppNav } from "@/components/AppNav";
import { apiFetch, API_BASE } from "@/lib/api";

type TableCard = {
  key: string;
  label: string;
  table: string;
  count: number;
  samples: { id: string; summary: string }[];
};

type CatalogResponse = {
  tables: TableCard[];
  extras: Record<string, number>;
};

type DetailResponse = {
  key: string;
  label: string;
  table: string;
  count: number;
  rows: Record<string, unknown>[];
  error?: string;
};

export default function TablesPage() {
  const [data, setData] = useState<CatalogResponse | null>(null);
  const [active, setActive] = useState<string | null>(null);
  const [detail, setDetail] = useState<DetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<CatalogResponse>("/api/v1/catalog/tables")
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "取得失敗"));
  }, []);

  useEffect(() => {
    if (!active) {
      setDetail(null);
      return;
    }
    apiFetch<DetailResponse>(`/api/v1/catalog/tables/${active}`)
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : "詳細取得失敗"));
  }, [active]);

  return (
    <div className="min-h-full bg-background">
      <AppNav />
      <main className="mx-auto w-full max-w-6xl px-6 pb-16">
        <h1 className="font-display text-4xl text-brand-deep">主要テーブル</h1>
        <p className="mt-2 text-sm text-muted">
          顧客・受講者・法人・契約・申込・商品・講座・カリキュラム・教材・受講履歴・進捗・成績・課題・添削・請求・入金・発送・問い合わせ・修了・資格
        </p>
        <p className="mt-1 text-xs text-muted">API: {API_BASE}/api/v1/catalog/tables</p>

        {error && <p className="mt-6 text-sm text-accent">{error}</p>}

        {data && (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.tables.map((t) => (
              <button
                key={t.key}
                type="button"
                onClick={() => setActive(t.key === active ? null : t.key)}
                className={`border p-4 text-left transition-colors ${
                  active === t.key ? "border-brand bg-white" : "border-line bg-surface/80 hover:border-brand"
                }`}
              >
                <div className="flex items-baseline justify-between gap-2">
                  <h2 className="text-lg font-medium text-brand-deep">{t.label}</h2>
                  <span className="font-display text-2xl text-brand">{t.count}</span>
                </div>
                <p className="mt-1 text-xs text-muted">{t.table}</p>
                <ul className="mt-3 space-y-1 text-xs text-muted">
                  {t.samples.slice(0, 3).map((s) => (
                    <li key={s.id} className="truncate">
                      {s.summary}
                    </li>
                  ))}
                  {!t.samples.length && <li>データなし</li>}
                </ul>
              </button>
            ))}
          </div>
        )}

        {detail && (
          <section className="mt-10 overflow-x-auto border border-line bg-surface p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h2 className="text-lg font-medium">
                {detail.label} <span className="text-sm text-muted">({detail.table} · {detail.count}件)</span>
              </h2>
              <button type="button" className="text-sm text-brand" onClick={() => setActive(null)}>
                閉じる
              </button>
            </div>
            <table className="min-w-full text-left text-xs">
              <thead>
                <tr className="border-b border-line text-muted">
                  {detail.rows[0] &&
                    Object.keys(detail.rows[0]).map((col) => (
                      <th key={col} className="px-2 py-2 font-medium">
                        {col}
                      </th>
                    ))}
                </tr>
              </thead>
              <tbody>
                {detail.rows.map((row) => (
                  <tr key={String(row.id)} className="border-b border-line/60">
                    {Object.values(row).map((val, i) => (
                      <td key={i} className="max-w-[14rem] truncate px-2 py-2">
                        {val == null ? "—" : String(val)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {!detail.rows.length && <p className="text-sm text-muted">行がありません</p>}
          </section>
        )}

        <p className="mt-10 text-sm text-muted">
          <Link href="/courses" className="text-brand">
            コース一覧
          </Link>
          {" · "}
          <Link href="/dashboard" className="text-brand">
            経営KPI
          </Link>
        </p>
      </main>
    </div>
  );
}
