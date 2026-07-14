"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { UsageGuidePanel } from "./UsageGuidePanel";

const links = [
  { href: "/tables", label: "主要テーブル" },
  { href: "/courses", label: "コース" },
  { href: "/contracts", label: "申込・契約" },
  { href: "/payments", label: "入金" },
  { href: "/my", label: "マイ学習" },
  { href: "/learning", label: "学習管理" },
  { href: "/shipping", label: "教材発送" },
  { href: "/assignments", label: "添削" },
  { href: "/accounts", label: "アカウント" },
  { href: "/support", label: "FAQ・問合せ" },
  { href: "/dashboard", label: "経営KPI" },
  { href: "/login", label: "ログイン" },
];

export function AppNav() {
  const pathname = usePathname();
  const [guideOpen, setGuideOpen] = useState(false);

  return (
    <>
      <header className="relative z-10 mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-6">
        <Link href="/" className="text-sm font-medium tracking-[0.08em] text-brand">
          e-Learning Platform
        </Link>
        <nav className="flex flex-wrap items-center gap-4 text-sm text-muted">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`transition-colors hover:text-brand-deep ${
                pathname === l.href || pathname.startsWith(l.href + "/") ? "text-brand-deep" : ""
              }`}
            >
              {l.label}
            </Link>
          ))}
          <button
            type="button"
            onClick={() => setGuideOpen((v) => !v)}
            aria-pressed={guideOpen}
            className="rounded-full border border-brand/30 bg-white/80 px-3 py-1 text-sm font-medium text-brand transition-colors hover:border-brand hover:bg-white"
          >
            利用手順
          </button>
        </nav>
      </header>
      <UsageGuidePanel open={guideOpen} onClose={() => setGuideOpen(false)} />
    </>
  );
}
