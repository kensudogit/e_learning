"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { AppNav } from "@/components/AppNav";
import { apiFetch } from "@/lib/api";
import { getToken } from "@/lib/types";

type Address = {
  id: string;
  postal_code: string;
  city: string;
  address_line: string;
  country: string;
  is_default: boolean;
};
type Material = { id: string; title: string; material_type: string };
type Order = {
  id: string;
  status: string;
  material_id: string;
  scheduled_ship_date: string | null;
  split_group: string | null;
  split_sequence: number;
  is_overseas: boolean;
  tracking_no: string | null;
};
type Inventory = { id: string; material_id: string; quantity: number; warehouse: string };
type Bundle = { id: string; code: string; name: string; price: string | number };

export default function ShippingPage() {
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [inventory, setInventory] = useState<Inventory[]>([]);
  const [bundles, setBundles] = useState<Bundle[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [postal, setPostal] = useState("100-0001");
  const [city, setCity] = useState("千代田区");
  const [line, setLine] = useState("丸の内1-1");
  const [country, setCountry] = useState("JP");

  async function refresh(token: string) {
    const [a, m, o, i, b] = await Promise.all([
      apiFetch<Address[]>("/api/v1/shipping/addresses", { token }),
      apiFetch<Material[]>("/api/v1/materials", { token }),
      apiFetch<Order[]>("/api/v1/shipping/orders", { token }),
      apiFetch<Inventory[]>("/api/v1/shipping/inventory", { token }).catch(() => []),
      apiFetch<Bundle[]>("/api/v1/shipping/bundles", { token }),
    ]);
    setAddresses(a);
    setMaterials(m);
    setOrders(o);
    setInventory(i);
    setBundles(b);
  }

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setMessage("ログインが必要です");
      return;
    }
    refresh(token).catch((e) => setMessage(e instanceof Error ? e.message : "取得失敗"));
  }, []);

  async function addAddress(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token) return;
    await apiFetch("/api/v1/shipping/addresses", {
      method: "POST",
      token,
      body: JSON.stringify({
        postal_code: postal,
        city,
        address_line: line,
        country,
        is_default: true,
      }),
    });
    setMessage("住所を登録/変更しました");
    await refresh(token);
  }

  async function scheduleShip(materialId: string, splitSeq: number) {
    const token = getToken();
    if (!token || !addresses[0]) {
      setMessage("住所を先に登録してください");
      return;
    }
    const shipDate = new Date(Date.now() + splitSeq * 14 * 86400000).toISOString().slice(0, 10);
    await apiFetch("/api/v1/shipping/orders", {
      method: "POST",
      token,
      body: JSON.stringify({
        address_id: addresses[0].id,
        material_id: materialId,
        scheduled_ship_date: shipDate,
        split_group: "SPLIT-A",
        split_sequence: splitSeq,
        is_overseas: country !== "JP",
      }),
    });
    setMessage(`発送予約（分割 ${splitSeq}）: ${shipDate}`);
    await refresh(token);
  }

  async function ship(orderId: string) {
    const token = getToken();
    if (!token) return;
    try {
      await apiFetch(`/api/v1/shipping/orders/${orderId}/ship`, {
        method: "POST",
        token,
        body: JSON.stringify({ tracking_no: `TRK-${Date.now().toString().slice(-8)}` }),
      });
      setMessage("発送済みに更新");
      await refresh(token);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "発送失敗");
    }
  }

  async function reship(orderId: string) {
    const token = getToken();
    if (!token) return;
    try {
      await apiFetch(`/api/v1/shipping/orders/${orderId}/reship`, { method: "POST", token });
      setMessage("再発送を作成");
      await refresh(token);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "再発送失敗");
    }
  }

  async function returnOrder(orderId: string) {
    const token = getToken();
    if (!token) return;
    try {
      await apiFetch(`/api/v1/shipping/orders/${orderId}/return`, {
        method: "POST",
        token,
        body: JSON.stringify({ return_reason: "宛所不明" }),
      });
      setMessage("返送処理");
      await refresh(token);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "返送失敗");
    }
  }

  return (
    <div className="min-h-full bg-background">
      <AppNav />
      <main className="mx-auto w-full max-w-3xl px-6 pb-16">
        <h1 className="font-display text-4xl text-brand-deep">教材発送</h1>
        <p className="mt-2 text-sm text-muted">
          発送時期・分割発送・在庫・住所変更・再発送・返送・海外・版管理・セット商品
        </p>
        {message && <p className="mt-4 text-sm text-brand-deep">{message}</p>}
        {!getToken() && (
          <Link href="/login" className="text-brand underline">
            ログイン
          </Link>
        )}

        <form onSubmit={addAddress} className="mt-8 grid gap-2 text-sm sm:grid-cols-2">
          <input className="border border-line px-3 py-2" value={postal} onChange={(e) => setPostal(e.target.value)} placeholder="郵便番号" />
          <input className="border border-line px-3 py-2" value={city} onChange={(e) => setCity(e.target.value)} placeholder="市区町村" />
          <input className="border border-line px-3 py-2 sm:col-span-2" value={line} onChange={(e) => setLine(e.target.value)} placeholder="番地" />
          <select className="border border-line px-3 py-2" value={country} onChange={(e) => setCountry(e.target.value)}>
            <option value="JP">日本</option>
            <option value="US">海外(US)</option>
          </select>
          <button type="submit" className="bg-brand px-4 py-2 text-white">
            住所登録・変更
          </button>
        </form>

        <section className="mt-10">
          <h2 className="text-lg font-medium">紙教材（分割発送）</h2>
          <ul className="mt-3 space-y-3 text-sm">
            {materials
              .filter((m) => m.material_type === "paper" || m.material_type === "PAPER")
              .concat(materials)
              .filter((m, i, arr) => arr.findIndex((x) => x.id === m.id) === i)
              .map((m) => (
                <li key={m.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-line py-2">
                  <span>
                    {m.title} · {m.material_type}
                  </span>
                  <span className="flex gap-2">
                    <button type="button" className="text-brand underline" onClick={() => scheduleShip(m.id, 1)}>
                      第1回発送
                    </button>
                    <button type="button" className="text-brand underline" onClick={() => scheduleShip(m.id, 2)}>
                      第2回発送
                    </button>
                  </span>
                </li>
              ))}
          </ul>
        </section>

        <section className="mt-10">
          <h2 className="text-lg font-medium">発送一覧</h2>
          <ul className="mt-3 space-y-3 text-sm">
            {orders.map((o) => (
              <li key={o.id} className="border-b border-line pb-3">
                <p>
                  {o.status} · {o.scheduled_ship_date}
                  {o.split_group ? ` · ${o.split_group}#${o.split_sequence}` : ""}
                  {o.is_overseas ? " · 海外" : ""}
                  {o.tracking_no ? ` · ${o.tracking_no}` : ""}
                </p>
                <div className="mt-1 flex gap-3">
                  <button type="button" className="underline" onClick={() => ship(o.id)}>
                    発送
                  </button>
                  <button type="button" className="underline" onClick={() => reship(o.id)}>
                    再発送
                  </button>
                  <button type="button" className="underline" onClick={() => returnOrder(o.id)}>
                    返送
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section className="mt-10">
          <h2 className="text-lg font-medium">在庫</h2>
          <ul className="mt-2 text-sm text-muted">
            {inventory.map((i) => (
              <li key={i.id}>
                {i.warehouse}: {i.quantity}
              </li>
            ))}
            {!inventory.length && <li>在庫レコードなし</li>}
          </ul>
        </section>

        <section className="mt-10">
          <h2 className="text-lg font-medium">eラーニングセット商品</h2>
          <ul className="mt-2 text-sm">
            {bundles.map((b) => (
              <li key={b.id}>
                {b.code} {b.name} · ¥{Number(b.price).toLocaleString()}
              </li>
            ))}
            {!bundles.length && <li className="text-muted">なし</li>}
          </ul>
        </section>
      </main>
    </div>
  );
}
