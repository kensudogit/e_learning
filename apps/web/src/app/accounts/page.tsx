"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { AppNav } from "@/components/AppNav";
import { apiFetch } from "@/lib/api";
import { getToken } from "@/lib/types";

type Account = {
  id: string;
  email: string | null;
  full_name: string;
  role: string;
  login_id: string | null;
  is_contractor: boolean;
  account_status: string;
};
type Membership = { id: string; organization_id: string; role: string; is_primary: boolean };
type Org = { id: string; name: string; code: string };
type Family = { id: string; member_user_id: string; relation: string };

export default function AccountsPage() {
  const [me, setMe] = useState<Account | null>(null);
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [family, setFamily] = useState<Family[]>([]);
  const [loginId, setLoginId] = useState("");
  const [orgName, setOrgName] = useState("デモ商事");
  const [orgCode, setOrgCode] = useState("DEMO-CO");
  const [message, setMessage] = useState<string | null>(null);

  async function refresh(token: string) {
    const [a, m, o, f] = await Promise.all([
      apiFetch<Account>("/api/v1/accounts/me", { token }),
      apiFetch<Membership[]>("/api/v1/accounts/me/memberships", { token }),
      apiFetch<Org[]>("/api/v1/organizations", { token }),
      apiFetch<Family[]>("/api/v1/accounts/family", { token }),
    ]);
    setMe(a);
    setMemberships(m);
    setOrgs(o);
    setFamily(f);
    setLoginId(a.login_id || "");
  }

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setMessage("ログインが必要です");
      return;
    }
    refresh(token).catch((e) => setMessage(e instanceof Error ? e.message : "取得失敗"));
  }, []);

  async function changeLogin(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token) return;
    try {
      const a = await apiFetch<Account>("/api/v1/accounts/me/login-id", {
        method: "POST",
        token,
        body: JSON.stringify({ new_login_id: loginId }),
      });
      setMe(a);
      setMessage("ログインIDを変更しました");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "変更失敗");
    }
  }

  async function createOrg(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token) return;
    try {
      await apiFetch("/api/v1/organizations", {
        method: "POST",
        token,
        body: JSON.stringify({ name: orgName, code: orgCode }),
      });
      setMessage("法人組織を作成（管理者として所属）");
      await refresh(token);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "組織作成失敗");
    }
  }

  async function suspend() {
    const token = getToken();
    if (!token || !me) return;
    try {
      await apiFetch(`/api/v1/accounts/${me.id}/status`, {
        method: "POST",
        token,
        body: JSON.stringify({ status: "suspended", reason: "本人申請" }),
      });
      setMessage("利用停止しました（再ログイン不可）");
      await refresh(token);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "停止失敗");
    }
  }

  return (
    <div className="min-h-full bg-background">
      <AppNav />
      <main className="mx-auto w-full max-w-3xl px-6 pb-16">
        <h1 className="font-display text-4xl text-brand-deep">アカウント管理</h1>
        <p className="mt-2 text-sm text-muted">
          契約者/受講者・法人管理者・複数企業所属・家族申込・ログインID・退会停止
        </p>
        {message && <p className="mt-4 text-sm text-brand-deep">{message}</p>}
        {!getToken() && (
          <Link href="/login" className="text-brand underline">
            ログイン
          </Link>
        )}

        {me && (
          <section className="mt-8 text-sm">
            <p>
              {me.full_name} / {me.email}
            </p>
            <p className="text-muted">
              ロール {me.role} · 契約者 {me.is_contractor ? "はい" : "いいえ"} · 状態 {me.account_status}
            </p>
          </section>
        )}

        <form onSubmit={changeLogin} className="mt-8 flex gap-2 text-sm">
          <input
            className="flex-1 border border-line px-3 py-2"
            value={loginId}
            onChange={(e) => setLoginId(e.target.value)}
            placeholder="新しいログインID"
          />
          <button type="submit" className="bg-brand px-4 text-white">
            ID変更
          </button>
        </form>

        <section className="mt-10">
          <h2 className="text-lg font-medium">所属組織（複数可）</h2>
          <ul className="mt-2 space-y-1 text-sm text-muted">
            {memberships.map((m) => {
              const org = orgs.find((o) => o.id === m.organization_id);
              return (
                <li key={m.id}>
                  {org?.name ?? m.organization_id.slice(0, 8)} · {m.role}
                  {m.is_primary ? " · 主所属" : ""}
                </li>
              );
            })}
            {!memberships.length && <li>所属なし</li>}
          </ul>
          <form onSubmit={createOrg} className="mt-4 flex flex-wrap gap-2 text-sm">
            <input className="border border-line px-3 py-2" value={orgName} onChange={(e) => setOrgName(e.target.value)} />
            <input className="border border-line px-3 py-2" value={orgCode} onChange={(e) => setOrgCode(e.target.value)} />
            <button type="submit" className="border border-line px-3 py-2">
              法人組織を作成
            </button>
          </form>
        </section>

        <section className="mt-10">
          <h2 className="text-lg font-medium">家族申込リンク</h2>
          <ul className="mt-2 text-sm text-muted">
            {family.map((f) => (
              <li key={f.id}>
                {f.relation}: {f.member_user_id.slice(0, 8)}…
              </li>
            ))}
            {!family.length && <li>なし（API で member_user_id を指定して登録）</li>}
          </ul>
        </section>

        <section className="mt-10">
          <h2 className="text-lg font-medium">退会・利用停止</h2>
          <button type="button" className="mt-2 border border-line px-4 py-2 text-sm" onClick={suspend}>
            利用停止する
          </button>
          <p className="mt-2 text-xs text-muted">個人情報削除・重複統合は管理者 API で実行します</p>
        </section>
      </main>
    </div>
  );
}
