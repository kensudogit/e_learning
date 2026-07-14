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
    │ クーポン · 見積 · 請求 · 入金
    │ （紙教材 → 発送予定を自動作成）
    ▼
教材発送 / マイ学習
    │ 進捗 · 学習履歴
    ▼
添削課題（マスタ提出 → 返却・成績）
    │
    ▼
試験・修了 / 経営KPI`;

/** 通信教育の業務ループ（実装済み） */
const correspondenceLoop = `  申込・契約（/contracts）
         │ 紙教材あり講座
         ▼ 自動
  ShippingOrder 予定作成 ──→ 教材発送（/shipping）
         │
         ▼
  入金記録（/payments）· 分割消込
         │
         ▼
  学習進捗 · LearningHistory（/my · /learning）
         │
         ▼
  課題マスタ提出（/assignments）
         │ corrector が返却
         ▼
  CorrectionResult + Grade + 履歴
         │
         ▼
  試験合格 → 修了証 · KPI`;

const recommendedFlow = [
  "ログイン（デモ: learner@example.com / password123）",
  "「コース」で通信教育講座を確認し詳細を開く",
  "「申込・契約」で申込 → 紙教材の発送予定が自動作成される",
  "「入金」で入金記録または分割回次の消込を試す",
  "「教材発送」で自動登録された予定を確認",
  "「添削」で課題マスタ提出 → corrector@ で返却・点数",
  "「マイ学習」で進捗・学習履歴・試験・修了を確認",
] as const;
const awsArchitecture = `                     Internet
                         │
                Route53（DNS）
                         │
                  CloudFront
              （高速コンテンツ配信）
          ┌──────────┴──────────┐
          │                     │
     S3（教材・画像）        ALB
                                │
                       ECS(Fargate)
        ┌──────────┬──────────┬──────────┐
        │          │          │          │
     受講API    添削API    管理API    バッチ
        │
    Cognito（認証）
        │
 Aurora PostgreSQL(RDS)
        │
  CloudWatch・WAF・SES・SQS`;

/** 本パッケージの Docker → ECR → ECS 運用構成 */
const ecsDockerArchitecture = `  [リポジトリルート Dockerfile]
   multi-stage: Next.js static → FastAPI + web_static
              │
              ▼  docker build / tag / push
         Amazon ECR
              │
              ▼  タスク定義で image 参照
    ECS Cluster (Fargate)
         │
         ├─ Service: elearning-app（現状: 単一コンテナ）
         │     container PORT（既定 5000）
         │     CMD: uvicorn app.main:app --host 0.0.0.0
         │     ヘルス: GET /health
         │
         └─ （将来）受講 / 添削 / 管理 / バッチ にサービス分割
              │
         ALB ターゲットグループ
              │
    CloudWatch Logs · ローリング更新 · Auto Scaling`;

const ecsBuildSteps = [
  "前提: AWS CLI v2 · Docker · Terraform ≥ 1.5 · リージョン ap-northeast-1 推奨",
  "成果物: ルート Dockerfile（API + 静的 Web 同梱）。ローカル分離は docker-compose.yml",
  "1) 基盤: cd infra/terraform → terraform init / plan / apply（VPC·RDS·Cognito·ECS·CloudFront）",
  "2) ECR: aws ecr create-repository --repository-name elearning-app",
  "3) ログイン: aws ecr get-login-password | docker login …dkr.ecr.…amazonaws.com",
  "4) ビルド: docker build -t elearning-app . （リポジトリルート）",
  "5) タグ/push: docker tag …:latest <ACCOUNT>.dkr.ecr…/elearning-app:latest → docker push",
  "6) タスク定義: CPU/MEM · イメージURI · PORT · 環境変数/Secrets · awslogs ドライバ",
  "7) サービス: Fargate · desiredCount · ALB ターゲット（コンテナPORT一致）· /health",
  "8) エッジ: CloudFront→ALB（+S3教材）· Route53 Alias · 必要なら WAF",
  "9) 接続: DATABASE_URL(RDS/Aurora) · CORS_ORIGINS · WEB_BASE_URL空(同一オリジン) · Cognito",
  "10) 初期データ: ECS Exec またはワンショットタスクで python -m app.scripts.seed",
] as const;

const ecsOpsSteps = [
  "デプロイ更新: 新イメージ push → タスク定義 revision 更新 → サービス force-new-deployment",
  "ローリング: minimumHealthyPercent / maximumPercent で無停止寄せ替え",
  "ヘルス: ALB + コンテナヘルスチェックは /health（200）",
  "ログ: CloudWatch Logs（/ecs/elearning-app 等）で uvicorn・アプリ出力を確認",
  "スケール: Service Auto Scaling（CPU/ALB RequestCount）または desiredCount 手動変更",
  "設定変更: Secrets Manager / SSM Parameter をタスク定義で注入（DATABASE_URL 等）",
  "障害切り分け: タスク停止理由 → ログ → RDS 到達性（SG・subnet）→ ALB ターゲット健全性",
  "バッチ将来: EventBridge / SQS トリガの別 Fargate タスク（ALB なし可）",
  "現状対応: Phase1 は単一 FastAPI イメージ。受講/添削/管理/バッチ分割は Phase3",
  "詳細コマンドは README「AWS デプロイ手順」「デプロイ（Docker）」を参照",
] as const;

const awsDeploySteps = [
  "構成図: Internet → Route53 → CloudFront → (S3 | ALB → ECS)",
  "ECS(Fargate) + Docker: ルート Dockerfile を ECR 経由で起動（上図「ECS × Docker」）",
  "認証・DB: Cognito → Aurora PostgreSQL(RDS)",
  "横断基盤: CloudWatch · WAF · SES · SQS",
  "構築: terraform apply → ECR push → タスク定義/サービス → ALB·CloudFront",
  "運用: ローリング更新 · /health · CloudWatch · Auto Scaling · seed",
  "手順の詳細は「9. AWS デプロイ」内の構築・運用リストと README を参照",
] as const;

/** 単一 FastAPI → 受講/添削/管理/バッチ 分割の目標構成 */
const microservicesArchitecture = `  [現状 Phase0–1]
   単一 ECS Service（FastAPI + web_static）
   /api/v1/* を1プロセスで処理 · 共有 DB
              │  段階分割（Strangler Fig）
              ▼
  [目標 Phase3]
       CloudFront / ALB
            │ パスベースルーティング
   ┌────────┼────────┬────────┐
   ▼        ▼        ▼        ▼
 受講API  添削API  管理API   バッチ
 courses  assignments accounts EventBridge
 contracts learning  analytics / SQS worker
 shipping  …         faq
   │        │        │        │
   └────────┴──┬─────┴────────┘
               ▼
     Cognito JWT（共通検証）
     Aurora（初期は共有スキーマ
             → 境界ごと DB/スキーマ分離）
     SQS / SES / S3（非同期・教材）`;

const microservicesSteps = [
  "前提: Phase1 で単一 ECS + RDS が安定稼働していること（分割は Phase3）",
  "0) 境界定義: 受講（courses/contracts/learning/shipping）· 添削（assignments）· 管理（accounts/analytics/faq）· バッチ（督促・集計・SQS）",
  "1) モジュール化: apps/api 内で router/domain を境界ごとに切り、同一リポでビルド分離可能にする",
  "2) 契約（API）固定: 公開パス /api/v1/... と OpenAPI をサービス契約として版管理",
  "3) 認証共通化: Cognito JWT 検証を共有ライブラリ化（各サービスで同じ issuer/audience）",
  "4) データ: まずは共有 Aurora + スキーマ/テーブル所有権を明示 → 後から DB 分離または Read モデル",
  "5) 同期→非同期: 添削割当・発送指示・督促は SQS（または EventBridge）へ。同期 HTTP 連鎖を避ける",
  "6) ECR/ECS: サービスごとリポジトリ・タスク定義・Service・ターゲットグループを作成",
  "7) ALB: パスルールで振り分け（例: /api/v1/assignments/* → 添削、他受講、/api/v1/accounts|/analytics → 管理）",
  "8) バッチ: ALB なし Fargate をスケジュール/SQS トリガ。冪等性と DLQ を必須化",
  "9) 観測: サービス別 CloudWatch Logs · トレース（X-Ray 等）· 相関 ID をリクエストに付与",
  "10) 移行: Strangler — パス単位で新サービスへ切替、旧モノリスはフォールバック残置→最終撤去",
  "11) フロント: 同一オリジン（CloudFront）を維持し、クライアントのベース URL 変更を最小化",
] as const;

const microservicesConcerns = [
  "分散トランザクション: 申込→請求→発送など跨ぎ処理は2相コミット不可。Saga/アウトボックス + 補償を設計",
  "共有 DB の罠: テーブルを複数サービスから直接更新すると結合が残る。所有境界を破らない",
  "N+1 / チャットリネス: 画面1操作で多サービス呼び出しが増える。BFF または集約 API・キャッシュを検討",
  "一貫性: 最終的整合性を許容する UX（「処理中」表示・再取得）が必要",
  "認証・認可: ロール（受講者/添削/管理/法人）を各サービスで再実装しない。クレームとポリシーを共通化",
  "スキーマ進化: 後方互換の API 版、破壊的変更は新パスまたはバージョンヘッダ",
  "運用コスト: サービス数×デプロイ・監視・障害面が増える。分割理由（スケール・チーム・障害隔離）が薄いなら延期",
  "ローカル開発: docker-compose で全サービス起動が重荷。モック/契約テストで単体開発可能にする",
  "障害伝播: タイムアウト・サーキットブレーカ・リトライ（冪等時のみ）を標準装備",
  "個人情報: 退会・削除が複数ストアに跨る。削除オーケストレーションと監査ログを先に決める",
  "バッチとオンラインの競合: 集計ジョブがオンライン更新と衝突しないロック/読み取り分離",
  "コスト: Fargate 常時複数サービス + NAT/ALB ルール増。低負荷期はモノリス継続も選択肢",
] as const;

const demoAccounts = [
  "learner@example.com … 受講者",
  "family@example.com … 家族受講者（太郎の子リンク）",
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
    title: "0. 最短フロー（通信教育）",
    body: "申込→発送自動作成→入金→学習→添削→試験まで一連で確認できます。",
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
      "「コース」→ カードから詳細へ（通信教育タグ付きを優先）",
      "詳細でカリキュラム・紙教材・添削・試験の有無を確認",
      "受講開始は「申込・契約」完了後",
    ],
  },
  {
    title: "3. 申込・契約",
    body: "個人/法人、受付チャネル、クーポン、分割払い、書類発行。紙教材あり講座は発送予定を自動作成します。",
    items: [
      "「申込・契約」で講座を選んで同時申込",
      "クーポン（例: WELCOME10）/ 紹介 / キャンペーンを付与",
      "支払: 一括 / 分割 / 請求書払い",
      "見積・請求・領収を発行",
      "紙教材（shipping_required）→ ShippingOrder が自動登録（「教材発送」で確認）",
      "変更・キャンセルは契約の「キャンセル」から",
    ],
  },
  {
    title: "3b. 入金",
    body: "通信教育の代金入金と分割消込です（ゲートウェイ連携前の運用デモ）。",
    items: [
      "ナビ「入金」を開く",
      "契約を選び金額・手段（振込/カード/コンビニ等）で入金記録",
      "分割契約は回次ごとに「入金する」で消込（Payment + paid フラグ）",
      "API: POST /api/v1/payments · POST /api/v1/payments/installments/{id}/pay",
    ],
  },
  {
    title: "4. マイ学習・学習管理",
    body: "コンテンツ視聴と進捗・理解度・学習イベント履歴を管理します。",
    items: [
      "「マイ学習」→ 受講中コースと進捗率",
      "学習履歴タイムライン（view / complete / submit / exam / correction）",
      "「学習管理」→ 動画/PDF/テキスト/SCORM・前提科目・BM・理解度クイズ",
      "試験を受ける → 合否・修了証・Grade / LearningHistory に記録",
      "継続更新（renew）もマイ学習から",
    ],
  },
  {
    title: "5. 教材発送・添削",
    body: "紙教材の発送運用と添削課題（マスタ・成績連携）です。",
    items: [
      "「教材発送」→ 契約時に自動作成された予定・分割出荷・在庫・住所",
      "再送・返品・海外・版管理・eラーニング+紙セット",
      "「添削」→ 課題マスタを選んで提出（学習履歴に submit）",
      "corrector@ でログイン → 添削待ちを返却（点数入力）",
      "返却時: CorrectionResult + Grade + 履歴（correction）を自動作成",
      "添削結果一覧で点数・TAT（ターンアラウンド）を確認",
    ],
  },
  {
    title: "6. アカウント・組織",
    body: "契約者/受講者、法人メンバー、家族リンクを管理します。",
    items: [
      "「アカウント」でプロフィール・ログインID変更・利用停止",
      "法人組織の作成とメンバー追加（メール指定可）",
      "家族リンク: member_email で追加（デモ: family@example.com / 続柄「子」）",
      "シード済み: learner（保護者）→ family（子）の FamilyLink",
    ],
  },
  {
    title: "7. FAQ・経営KPI",
    body: "問い合わせ導線と経営ダッシュボードです。",
    items: [
      "「FAQ・問合せ」でサポート導線を確認",
      "「経営KPI」で受講者数・申込転換・継続率・添削TATを確認",
      "API: /api/v1/analytics/kpi ・ /dashboard",
    ],
  },
  {
    title: "8. ローカル / Railway",
    body: "開発起動と PaaS（Railway）接続の注意点です。",
    items: [...localTips],
  },
  {
    title: "9. AWS デプロイ（ECS × Docker）",
    body: "本パッケージを Amazon ECS（Fargate）上の Docker コンテナで構築・運用する手順です。全体図は「AWS Architecture」、コンテナ流れは「ECS × Docker」を参照。",
    items: [
      "—— 構成の要点 ——",
      ...awsDeploySteps,
      "—— 構築（Build / Deploy）——",
      ...ecsBuildSteps,
      "—— 運用（Operate）——",
      ...ecsOpsSteps,
    ],
  },
  {
    title: "10. マイクロサービス化",
    body: "単一 FastAPI イメージから受講 / 添削 / 管理 / バッチへ段階分割する手順です。構成は上図「Microservices」、Phase3 想定。",
    items: [
      "—— 分割手順 ——",
      ...microservicesSteps,
      "—— 留意・懸念点 ——",
      ...microservicesConcerns,
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
              通信教育の申込・入金・紙教材発送・学習履歴・添削成績・修了までを一連で確認できるデモです。
              最短はログイン → 申込・契約 → 入金 / 発送 → 添削 → マイ学習です。
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
              ログイン → コース → 申込・契約（発送自動作成）→ 入金 → 学習・履歴 → 添削（成績連携）→
              試験・修了 → 経営KPI までを一連で確認します。
            </p>
          </section>

          <section className={styles.featured} aria-label="推奨フロー">
            <div className={styles.featuredHead}>
              <span className={styles.featuredBadge}>Recommended</span>
              <strong>通信教育の最短確認手順</strong>
            </div>
            <p>
              learner で申込すると紙教材の発送予定が自動作成されます。入金・添削は別画面／別ロールで切り替えます。
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

          <section className={styles.featured} aria-label="通信教育ループ">
            <div className={styles.featuredHead}>
              <span className={styles.featuredBadge}>Correspondence</span>
              <strong>通信教育機能（実装済み）</strong>
            </div>
            <p>
              契約時の発送自動作成、入金・分割消込、課題マスタ添削と成績連携、学習履歴タイムライン、家族メールリンクを追加済みです。
            </p>
            <ul className={styles.items}>
              <li>契約 → 紙教材の ShippingOrder 自動登録（/shipping）</li>
              <li>入金記録・分割消込（/payments）</li>
              <li>添削返却 → CorrectionResult / Grade / 履歴</li>
              <li>マイ学習の学習履歴（view / submit / exam / correction）</li>
              <li>家族リンク・組織メンバーをメールで追加（family@example.com）</li>
            </ul>
          </section>

          <figure className={`${styles.diagram} ${styles.diagramAws}`} aria-label="Correspondence loop">
            <figcaption>Correspondence loop</figcaption>
            <pre>{correspondenceLoop}</pre>
          </figure>

          <section className={styles.featured} aria-label="AWS構成">
            <div className={styles.featuredHead}>
              <span className={styles.featuredBadge}>AWS</span>
              <strong>本番目標アーキテクチャ</strong>
            </div>
            <p>
              Route53 で受け、CloudFront から教材（S3）と API（ALB→ECS）へ振り分けます。
              ECS 上で受講・添削・管理・バッチを動かし、Cognito 認証と Aurora に接続します。
            </p>
          </section>

          <figure className={`${styles.diagram} ${styles.diagramAws}`} aria-label="AWS Architecture">
            <figcaption>AWS Architecture</figcaption>
            <pre>{awsArchitecture}</pre>
          </figure>

          <section className={styles.featured} aria-label="ECS Docker">
            <div className={styles.featuredHead}>
              <span className={styles.featuredBadge}>ECS</span>
              <strong>Docker コンテナでの構築・運用</strong>
            </div>
            <p>
              ルート <code>Dockerfile</code> で Next.js 静的画面と FastAPI を1イメージにまとめ、ECR へ push したうえで
              ECS Fargate サービスとして起動します。インフラ骨格は <code>infra/terraform</code>、ヘルスは{" "}
              <code>/health</code>、更新は新イメージのローリングデプロイです。
            </p>
            <ul className={styles.items}>
              <li>構築: terraform → ECR build/push → タスク定義 → ECS Service + ALB</li>
              <li>運用: CloudWatch Logs · /health · force-new-deployment · Auto Scaling</li>
              <li>環境変数: PORT · DATABASE_URL · CORS_ORIGINS · WEB_BASE_URL（空=同一オリジン）</li>
            </ul>
          </section>

          <figure className={`${styles.diagram} ${styles.diagramAws}`} aria-label="ECS Docker flow">
            <figcaption>ECS × Docker</figcaption>
            <pre>{ecsDockerArchitecture}</pre>
          </figure>

          <section className={styles.featured} aria-label="マイクロサービス化">
            <div className={styles.featuredHead}>
              <span className={styles.featuredBadge}>Phase 3</span>
              <strong>マイクロサービス化</strong>
            </div>
            <p>
              現状は単一 FastAPI + 静的 Web です。負荷・チーム・障害隔離の必要が出たら、受講 / 添削 / 管理 / バッチへ
              Strangler Fig 方式で分割します。ALB パス振り分けと SQS 非同期、共有 JWT を軸にします。
            </p>
            <ul className={styles.items}>
              <li>手順: 境界定義 → モジュール化 → ECR/ECS 分割 → ALB ルール → 旧モノリス撤去</li>
              <li>懸念: 分散トランザクション · 共有DB · チャットリネス · 運用コスト増</li>
              <li>詳細は手順「10. マイクロサービス化」を参照</li>
            </ul>
          </section>

          <figure className={`${styles.diagram} ${styles.diagramAws}`} aria-label="Microservices">
            <figcaption>Microservices（目標）</figcaption>
            <pre>{microservicesArchitecture}</pre>
          </figure>

          <p className={styles.scrollHint}>
            ↓ 画面手順（0〜7 通信教育 / 3b 入金 / 8 ローカル / 9 ECS / 10 マイクロサービス）
          </p>

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
            ▼▲ で開閉 · ドラッグで移動 · × で閉じる · 通信教育は申込→入金→発送→添削→マイ学習 · 役割はデモアカウントで切替
          </p>
        </div>
      ) : null}
    </div>
  );
}
