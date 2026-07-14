"use client";

import { useCallback, useRef, useState } from "react";
import styles from "./UsageGuidePanel.module.css";

const techStack = [
  "Next.js · React",
  "Python · FastAPI",
  "PostgreSQL · RDS",
  "JWT · Cognito",
  "Docker · ECS",
  "CloudFront · Terraform",
] as const;

const serviceFlow = `ログイン
    │
    ▼
コース閲覧 / 申込・契約
    │ クーポン · 見積 · 請求
    ▼
マイ学習 / 学習管理
    │ 動画 · PDF · SCORM · 進捗
    ▼
教材発送 / 添削課題
    │
    ▼
試験・修了 / 経営KPI`;

const recommendedFlow = [
  "ログイン（デモ: learner@example.com / password123）",
  "「コース」で講座一覧を確認し、気になるコースを開く",
  "「申込・契約」で個人/法人の申込フローを確認",
  "「マイ学習」で進捗・ブックマーク・理解度クイズを試す",
  "管理者なら「経営KPI」で受講者数・転換・継続を確認",
] as const;

const demoAccounts = [
  "learner@example.com … 受講者",
  "admin@example.com … 管理者",
  "corrector@example.com … 添削者",
  "corp@example.com … 法人担当",
  "共通パスワード: password123",
] as const;

const localTips = [
  "API: py -3.12 で uvicorn（PORT は .env の NEXT_PUBLIC_API_BASE_URL に合わせる）",
  "DB: docker compose の Postgres はホスト 5433（5432 衝突回避）",
  "DATABASE_URL は postgresql:// でも可 → アプリが asyncpg に自動変換",
  "シード: apps/api で python -m app.scripts.seed",
  "Railway: ルート Dockerfile（API+静的Web）· Target Port はログの PORT と一致",
] as const;

const steps = [
  {
    title: "0. 最短フロー（画面操作）",
    body: "デモアカウントでログインし、コース→申込→学習まで一通り確認できます。",
    items: [...recommendedFlow],
  },
  {
    title: "1. ログイン",
    body: "役割別のデモユーザーで画面を切り替えられます。",
    items: [
      "ナビ「ログイン」を開く",
      ...demoAccounts,
      "トークンはブラウザに保持され、以降の API 呼び出しに使います",
    ],
  },
  {
    title: "2. コースを探す",
    body: "公開中の通信教育・法人・資格・動画講座を一覧します。",
    items: [
      "「コース」→ カードから詳細へ",
      "詳細でカリキュラム概要・ステータスを確認",
      "受講開始は契約・申込完了後（デモでは申込画面から確認）",
    ],
  },
  {
    title: "3. 申込・契約",
    body: "個人/法人、Web/電話/代理店などチャネルを含む契約フローです。",
    items: [
      "「申込・契約」で契約一覧・新規申込を確認",
      "クーポン / 紹介 / キャンペーンの付与イメージを確認",
      "見積・請求・領収のドキュメント種別を確認",
      "変更・解約・分割払いのステータス遷移を確認",
    ],
  },
  {
    title: "4. マイ学習・学習管理",
    body: "コンテンツ視聴と進捗・理解度を管理します。",
    items: [
      "「マイ学習」→ 受講中コースと進捗率",
      "動画 / PDF / テキスト / SCORM のコンテンツ順と前提条件",
      "ブックマーク・理解度クイズ・再受験",
      "期限・リマインダー・オフライン学習フラグ",
    ],
  },
  {
    title: "5. 教材発送・添削",
    body: "紙教材と添削課題の運用画面です。",
    items: [
      "「教材発送」→ 予定出荷・分割出荷・在庫・住所変更",
      "再送・返品・海外発送・版管理・eラーニング+紙セット",
      "「添削」→ 課題提出・添削者割当・フィードバック",
    ],
  },
  {
    title: "6. アカウント・組織",
    body: "契約者と受講者、法人メンバー、家族リンクを管理します。",
    items: [
      "「アカウント」→ 契約者/受講者の切替イメージ",
      "組織管理者・複数組織メンバーシップ",
      "ログインID変更・停止・退会・個人情報削除",
    ],
  },
  {
    title: "7. FAQ・経営KPI",
    body: "問い合わせ導線と経営ダッシュボードです。",
    items: [
      "「FAQ・問合せ」でサポート導線を確認",
      "「経営KPI」で受講者数・申込転換・継続率を確認",
      "API: /api/v1/analytics/kpi ・ /dashboard",
    ],
  },
  {
    title: "8. ローカル / Railway",
    body: "開発起動と PaaS（Railway）接続の注意点です。",
    items: [...localTips],
  },
  {
    title: "9. AWS デプロイ",
    body: "本番相当は VPC / RDS / Cognito / ECS / CloudFront（Terraform 骨格）で構築します。",
    items: [
      "前提: AWS CLI ログイン、Terraform ≥ 1.5、Docker、ECR 権限",
      "1) infra/terraform で terraform init → plan → apply（VPC・RDS・Cognito・ECS）",
      "2) ECR にルート Dockerfile のイメージを push（API + 静的 Web）",
      "3) ECS タスクに DATABASE_URL / CORS_ORIGINS / COGNITO_* / PORT を設定",
      "4) ALB ターゲットを ECS サービスに接続し、/health で疎通確認",
      "5) CloudFront オリジンを ALB（または S3 の静的配信）に切替",
      "6) Cognito ユーザープール作成後、COGNITO_* を API に反映",
      "詳細手順はリポジトリ README の「AWS デプロイ手順」を参照",
    ],
  },
] as const;

type Props = {
  open: boolean;
  onClose: () => void;
};

export function UsageGuidePanel({ open, onClose }: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    originX: number;
    originY: number;
  } | null>(null);

  const [expanded, setExpanded] = useState(true);
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const [dragging, setDragging] = useState(false);

  const onHeaderPointerDown = useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      if ((e.target as HTMLElement).closest("[data-ug-toggle]")) return;
      if (!pos) return;
      dragRef.current = {
        pointerId: e.pointerId,
        startX: e.clientX,
        startY: e.clientY,
        originX: pos.x,
        originY: pos.y,
      };
      setDragging(true);
      e.currentTarget.setPointerCapture(e.pointerId);
    },
    [pos],
  );

  const onHeaderPointerMove = useCallback((e: React.PointerEvent<HTMLElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== e.pointerId) return;
    setPos({
      x: drag.originX + (e.clientX - drag.startX),
      y: drag.originY + (e.clientY - drag.startY),
    });
  }, []);

  const onHeaderPointerUp = useCallback((e: React.PointerEvent<HTMLElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== e.pointerId) return;
    dragRef.current = null;
    setDragging(false);
    e.currentTarget.releasePointerCapture(e.pointerId);
  }, []);

  if (!open) return null;

  const style =
    pos != null
      ? ({
          position: "fixed" as const,
          left: pos.x,
          top: pos.y,
          right: "auto",
          bottom: "auto",
          width: "min(420px, calc(100vw - 2rem))",
          margin: 0,
        } as const)
      : undefined;

  return (
    <div
      ref={panelRef}
      className={`${styles.panel}${expanded ? "" : ` ${styles.collapsed}`}${dragging ? ` ${styles.dragging}` : ""}`}
      style={style}
      role="dialog"
      aria-label="利用手順"
      aria-modal="false"
    >
      <header
        className={styles.header}
        onPointerDown={(e) => {
          if ((e.target as HTMLElement).closest("[data-ug-toggle]")) return;
          if (pos == null && panelRef.current) {
            const rect = panelRef.current.getBoundingClientRect();
            setPos({ x: rect.left, y: rect.top });
            dragRef.current = {
              pointerId: e.pointerId,
              startX: e.clientX,
              startY: e.clientY,
              originX: rect.left,
              originY: rect.top,
            };
            setDragging(true);
            e.currentTarget.setPointerCapture(e.pointerId);
            return;
          }
          onHeaderPointerDown(e);
        }}
        onPointerMove={onHeaderPointerMove}
        onPointerUp={onHeaderPointerUp}
        onPointerCancel={onHeaderPointerUp}
      >
        <div className={styles.headerText}>
          <span aria-hidden>☰</span>
          <div className={styles.headerTitles}>
            <strong>利用手順</strong>
            <span className={styles.headerSub}>Architecture &amp; Ops</span>
          </div>
          <span className={styles.dragHint}>ドラッグで移動</span>
        </div>
        <div className={styles.headerActions}>
          <button
            type="button"
            className={styles.toggle}
            data-ug-toggle
            aria-label={expanded ? "折りたたむ" : "開く"}
            aria-expanded={expanded}
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? "▼" : "▲"}
          </button>
          <button
            type="button"
            className={styles.closeBtn}
            data-ug-toggle
            aria-label="閉じる"
            onClick={onClose}
          >
            ×
          </button>
        </div>
      </header>

      {expanded ? (
        <div className={styles.body}>
          <div className={styles.hero}>
            <p className={styles.heroKicker}>Learning platform demo</p>
            <h2 className={styles.heroTitle}>e-Learning — 申込 · 学習 · 運用</h2>
            <p className={styles.heroLead}>
              通信教育から法人研修・資格・動画・紙教材・添削・認定までを一つの画面群で確認するデモ向けワークフローです。
              まずログイン → コース → 申込 → マイ学習の順が最短です。
            </p>
            <div className={styles.stack} aria-label="Tech stack">
              {techStack.map((tag) => (
                <span key={tag} className={styles.stackPill}>
                  {tag}
                </span>
              ))}
            </div>
          </div>

          <section className={styles.featured} aria-label="サービスフロー">
            <div className={styles.featuredHead}>
              <span className={styles.featuredBadge}>Architecture</span>
              <strong>エンドツーエンド・学習フロー</strong>
            </div>
            <p>
              ログイン → コース閲覧 → 申込・契約 → 学習進捗 → 教材発送 / 添削 → 試験・修了 → 経営KPI
              までを一連で確認します。
            </p>
          </section>

          <section className={styles.featured} aria-label="推奨フロー">
            <div className={styles.featuredHead}>
              <span className={styles.featuredBadge}>Recommended</span>
              <strong>最短・安全な進め方</strong>
            </div>
            <p>
              デモ受講者でログインし、コース詳細と申込画面を見たあと、マイ学習で進捗を確認します。法人・添削は別アカウントで切り替えます。
            </p>
            <ul className={styles.items}>
              {recommendedFlow.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>

          <section className={styles.featured} aria-label="デモアカウント">
            <div className={styles.featuredHead}>
              <span className={styles.featuredBadge}>Accounts</span>
              <strong>デモアカウント</strong>
            </div>
            <ul className={styles.items}>
              {demoAccounts.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>

          <section className={styles.featured} aria-label="ローカル起動">
            <div className={styles.featuredHead}>
              <span className={styles.featuredBadge}>Ops</span>
              <strong>ローカル起動のポイント</strong>
            </div>
            <ul className={styles.items}>
              {localTips.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>

          <figure className={styles.diagram} aria-label="Service topology">
            <figcaption>Service topology</figcaption>
            <pre>{serviceFlow}</pre>
          </figure>

          <p className={styles.scrollHint}>↓ 画面ごとの手順</p>

          <ol className={styles.steps}>
            {steps.map((step) => (
              <li key={step.title}>
                <strong>{step.title}</strong>
                <p>{step.body}</p>
                <ul className={styles.items}>
                  {step.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>

          <p className={styles.footer}>
            ▼▲ で開閉 · ドラッグで移動 · × で閉じる · 常用はログイン→コース→申込→マイ学習 · 役割はデモアカウントで切替
          </p>
        </div>
      ) : null}
    </div>
  );
}
