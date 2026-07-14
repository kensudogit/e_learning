"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { AppNav } from "@/components/AppNav";
import { apiFetch } from "@/lib/api";

type TokenResponse = { access_token: string; token_type: string };

const accounts = [
  { email: "learner@example.com", label: "受講者" },
  { email: "admin@example.com", label: "管理者（KPI）" },
  { email: "corrector@example.com", label: "添削担当" },
  { email: "corp@example.com", label: "法人担当" },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("learner@example.com");
  const [password, setPassword] = useState("password123");
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setMessage(null);
    try {
      const token = await apiFetch<TokenResponse>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem("access_token", token.access_token);
      setMessage("ログイン成功");
      router.push(email.startsWith("admin") || email.startsWith("corp") ? "/dashboard" : "/courses");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "ログインに失敗しました");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-full bg-background">
      <AppNav />
      <div className="mx-auto flex w-full max-w-md flex-col px-6 py-8">
        <h1 className="font-display text-4xl text-brand-deep">ログイン</h1>
        <p className="mt-2 text-sm text-muted">デモアカウント（パスワード共通: password123）</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {accounts.map((a) => (
            <button
              key={a.email}
              type="button"
              className="border border-line px-2 py-1 text-xs text-muted hover:border-brand"
              onClick={() => setEmail(a.email)}
            >
              {a.label}
            </button>
          ))}
        </div>

        <form onSubmit={onSubmit} className="mt-8 space-y-4">
          <label className="block text-sm">
            <span className="mb-1.5 block text-muted">メールアドレス</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-line bg-surface px-3 py-2.5 outline-none focus:border-brand"
              required
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1.5 block text-muted">パスワード</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-line bg-surface px-3 py-2.5 outline-none focus:border-brand"
              required
            />
          </label>
          <button
            type="submit"
            disabled={loading}
            className="h-11 w-full bg-brand text-sm font-medium text-white transition-colors hover:bg-brand-deep disabled:opacity-60"
          >
            {loading ? "認証中…" : "ログイン"}
          </button>
        </form>

        {message && <p className="mt-4 text-sm text-muted">{message}</p>}
        <Link href="/" className="mt-8 text-sm text-brand">
          ← トップへ
        </Link>
      </div>
    </div>
  );
}
