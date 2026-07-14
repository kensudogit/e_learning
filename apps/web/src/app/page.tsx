import Link from "next/link";
import { AppNav } from "@/components/AppNav";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchHealth(): Promise<{ status: string; app: string; env: string } | null> {
  try {
    const res = await fetch(`${apiBase}/health`, { next: { revalidate: 10 } });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

type CourseSummary = {
  id: string;
  code: string;
  title: string;
  description: string | null;
  price: string | number | null;
  status: string;
};

async function fetchCourses(): Promise<CourseSummary[]> {
  try {
    const res = await fetch(`${apiBase}/api/v1/courses`, { next: { revalidate: 10 } });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

const services = [
  "個人向け通信教育",
  "法人研修",
  "資格講座",
  "動画・ライブ配信",
  "紙教材",
  "添削課題",
  "試験・修了認定",
];

export default async function Home() {
  const [health, courses] = await Promise.all([fetchHealth(), fetchCourses()]);

  return (
    <div className="relative flex min-h-full flex-1 flex-col overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_20%_0%,#b8d4d6_0%,transparent_55%),radial-gradient(ellipse_at_90%_10%,#9ec5c9_0%,transparent_40%),linear-gradient(180deg,#eef5f6_0%,#e2eef0_100%)]"
      />
      <AppNav />

      <main className="relative z-10 mx-auto flex w-full max-w-6xl flex-1 flex-col justify-center px-6 pb-20 pt-4">
        <p className="mb-4 font-display text-5xl tracking-tight text-brand-deep sm:text-6xl md:text-7xl">
          学びの基盤
        </p>
        <h1 className="max-w-2xl text-2xl font-medium leading-relaxed text-foreground sm:text-3xl">
          通信教育から法人研修・資格・ライブ・添削・認定までを統合する学習プラットフォーム。
        </h1>
        <p className="mt-5 max-w-xl text-base leading-7 text-muted">
          受講者数・申込転換・継続率を見える化し、問い合わせと運用工数を減らしながら、商品投入を速くします。
        </p>

        <div className="mt-10 flex flex-wrap items-center gap-4">
          <Link
            href="/courses"
            className="inline-flex h-12 items-center justify-center bg-brand px-7 text-sm font-medium text-white transition-colors hover:bg-brand-deep"
          >
            コースを見る
          </Link>
          <Link
            href="/dashboard"
            className="inline-flex h-12 items-center justify-center border border-line bg-surface/70 px-7 text-sm font-medium text-foreground backdrop-blur transition-colors hover:border-brand"
          >
            経営KPI
          </Link>
        </div>

        <ul className="mt-14 flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted">
          {services.map((s) => (
            <li key={s} className="border-b border-line/80 pb-0.5">
              {s}
            </li>
          ))}
        </ul>

        {courses.length > 0 && (
          <section className="mt-14 max-w-2xl">
            <h2 className="text-sm font-medium tracking-wide text-brand">公開コース（DB）</h2>
            <ul className="mt-4 space-y-4">
              {courses.slice(0, 4).map((c) => (
                <li key={c.id} className="border-b border-line/70 pb-3">
                  <Link href={`/courses/${c.id}`} className="text-base font-medium text-foreground hover:text-brand">
                    {c.title}
                  </Link>
                  <p className="mt-1 text-xs text-muted">
                    {c.code}
                    {c.price != null ? ` · ¥${Number(c.price).toLocaleString()}` : ""}
                  </p>
                </li>
              ))}
            </ul>
          </section>
        )}

        <div className="mt-10 flex items-center gap-3 text-sm text-muted">
          <span
            className={`inline-block h-2.5 w-2.5 rounded-full ${health ? "bg-brand" : "bg-accent"}`}
            aria-hidden
          />
          {health
            ? `API 接続OK — ${health.app} (${health.env}) · 公開コース ${courses.length} 件`
            : "API 未接続 — DB/API を起動してください"}
        </div>
      </main>
    </div>
  );
}
