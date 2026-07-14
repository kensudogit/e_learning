"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppNav } from "@/components/AppNav";
import { apiFetch } from "@/lib/api";
import { KpiDashboard, SERVICE_LABELS, getToken } from "@/lib/types";

function Metric({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="border-b border-line py-4">
      <p className="text-xs tracking-wide text-muted">{label}</p>
      <p className="mt-1 font-display text-3xl text-brand-deep">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const [kpi, setKpi] = useState<KpiDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setError("管理者 / 講師 / 法人担当でログインしてください");
      return;
    }
    apiFetch<KpiDashboard>("/api/v1/analytics/kpi", { token })
      .then(setKpi)
      .catch((err) => setError(err instanceof Error ? err.message : "取得失敗"));
  }, []);

  return (
    <div className="min-h-full bg-background">
      <AppNav />
      <main className="mx-auto w-full max-w-4xl px-6 pb-16">
        <h1 className="font-display text-4xl text-brand-deep">経営KPI</h1>
        <p className="mt-2 text-sm text-muted">
          受講者数・申込転換率・継続率・問い合わせ削減・運用工数・商品投入期間
        </p>

        {error && (
          <p className="mt-8 text-sm text-accent">
            {error} —{" "}
            <Link href="/login" className="underline">
              admin@example.com でログイン
            </Link>
          </p>
        )}

        {kpi && (
          <div className="mt-8 grid gap-2 sm:grid-cols-2">
            <Metric label="受講者数" value={`${kpi.learner_count}`} hint={`稼働受講 ${kpi.active_enrollments}`} />
            <Metric
              label="申込転換率"
              value={`${kpi.conversion_rate}%`}
              hint={`${kpi.converted_applications} / ${kpi.application_count} 申込`}
            />
            <Metric
              label="継続率"
              value={`${kpi.retention_rate}%`}
              hint={`更新 ${kpi.renewed_enrollments}`}
            />
            <Metric
              label="問い合わせ削減（FAQ解決率）"
              value={`${kpi.inquiry_faq_resolved_rate}%`}
              hint={`未対応 ${kpi.open_inquiries} / 全 ${kpi.inquiry_count}`}
            />
            <Metric
              label="運用工数（添削待ち）"
              value={`${kpi.pending_corrections}`}
              hint={
                kpi.avg_correction_turnaround_hours != null
                  ? `平均返却 ${kpi.avg_correction_turnaround_hours} 時間`
                  : "返却実績なし"
              }
            />
            <Metric
              label="商品投入期間"
              value={
                kpi.avg_product_launch_days != null ? `${kpi.avg_product_launch_days} 日` : "—"
              }
              hint={`公開 ${kpi.published_courses} / 下書き ${kpi.draft_courses}`}
            />
          </div>
        )}

        {kpi && (
          <section className="mt-10">
            <h2 className="text-lg font-medium">サービス種別の商品数</h2>
            <ul className="mt-4 space-y-2 text-sm">
              {Object.entries(kpi.by_service_type).map(([k, v]) => (
                <li key={k} className="flex justify-between border-b border-line py-2">
                  <span>{SERVICE_LABELS[k] ?? k}</span>
                  <span className="text-muted">{v}</span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>
    </div>
  );
}
