# eラーニング統合プラットフォーム

通信教育・eラーニングの受講管理・申込・添削運用を統合する新規プラットフォームの開発リポジトリです。

## 技術スタック

| 領域 | 技術 |
|------|------|
| Frontend | React / Next.js (App Router) / TypeScript / Tailwind CSS |
| Backend | Python / FastAPI / SQLAlchemy / Alembic |
| Auth | ローカル JWT → 本番 Amazon Cognito |
| DB | PostgreSQL（ローカル Docker `:5433` / 本番 Amazon RDS） |
| Cache | Redis |
| Infra | AWS（ECS, CloudFront, Cognito, RDS, VPC） / Terraform |

## リポジトリ構成

```
e_learning/
├── apps/
│   ├── web/          # Next.js フロントエンド
│   └── api/          # FastAPI バックエンド
├── infra/terraform/  # AWS インフラ骨格
├── scripts/          # 開発用スクリプト
├── docker-compose.yml
└── .env.example
```

## 主要ドメイン（初期実装）

- **認証** — ユーザー登録 / ログイン（ローカル JWT）
- **コース** — 講座の一覧・作成・更新
- **受講（Enrollment）** — 申込・進捗
- **添削（Assignment）** — 課題提出・フィードバック

## データベース（PostgreSQL）

本プロジェクトの永続化層は **PostgreSQL のみ** です（SQLite 等は使用しません）。

| 項目 | 値 |
|------|-----|
| エンジン | PostgreSQL 16（Docker）/ 本番は Amazon RDS for PostgreSQL |
| Host | `localhost` |
| Port | `5433`（ホストの PostgreSQL 5432 と競合回避） |
| Database | `elearning` |
| User / Password | `elearning` / `elearning` |
| SQLAlchemy URL | `postgresql+asyncpg://elearning:elearning@localhost:5433/elearning` |

```powershell
# PostgreSQL 起動 + スキーマ適用
.\scripts\setup-postgres.ps1
```

ホストにインストール済みの PostgreSQL（例: `postgresql-x64-17`）を使う場合は、`.env` の `DATABASE_URL` を変更してください。

```env
DATABASE_URL=postgresql+asyncpg://<user>:<password>@localhost:5432/<dbname>
```

スキーマ定義: `sql/001_schema.sql`  
マイグレーション: `apps/api/alembic`（Alembic + asyncpg）

## デプロイ（Docker）

リポジトリ直下の `Dockerfile` が **API（FastAPI）** をビルドします。  
（PaaS がルートの `Dockerfile` を要求するため。Web は `apps/web/Dockerfile` を別サービスで指定）

```bash
# ローカル確認
docker build -t elearning-api .
docker run --rm -p 8000:8000 --env-file .env elearning-api
```

Railway 利用時は `railway.toml` で `dockerfilePath = "Dockerfile"` とヘルスチェック `/health` を設定済みです。

### 申込・契約 / アカウント / 学習 / 発送

| 領域 | 画面 | 主な API |
|------|------|----------|
| 申込・契約 | `/contracts` | `/api/v1/contracts`（個人/法人・チャネル・複数講座・クーポン・分割・変更キャンセル・見積請求領収） |
| アカウント | `/accounts` | `/api/v1/accounts/*` `/api/v1/organizations`（契約者/受講者・複数企業・家族・ID変更・停止・PII削除） |
| 学習管理 | `/learning` | `/api/v1/learning/*`（動画/PDF/テキスト/SCORM・前提・進捗・BM・理解度テスト再受験・督促・オフライン） |
| 教材発送 | `/shipping` | `/api/v1/shipping/*`（発送時期・分割・在庫・住所・再発送・返送・海外・版管理・セット） |

## 実装済み機能

### 教育サービス
| サービス | 実装 |
|----------|------|
| 個人向け通信教育 | `service_types=personal` コース、レッスン、紙教材 |
| 法人研修 | `audience=corporate`、法人担当ロール |
| 資格講座 | `qualification_name`、試験・認定連携 |
| 動画・ライブ配信 | `/api/v1/media`（VOD/LIVE） |
| 紙教材 | `/api/v1/materials` |
| 添削課題 | 提出・返却・ターンアラウンド計測 |
| 試験・修了認定 | 試験提出、自動合否、修了証発行 |

### 経営 KPI（`/api/v1/analytics/kpi` / `/dashboard`）
- 受講者数
- 申込転換率（Application → Enrollment）
- 継続率（完了・更新）
- 問い合わせ削減（FAQ 自己解決率）
- 運用工数（添削待ち・平均返却時間）
- 商品投入期間（draft → published 平均日数）

### シードデータ

```powershell
cd apps\api
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "."
python -m app.scripts.seed
```

| アカウント | 用途 |
|------------|------|
| `learner@example.com` | 受講者 |
| `admin@example.com` | 経営KPI |
| `corrector@example.com` | 添削 |
| `corp@example.com` | 法人担当 |

パスワードはすべて `password123`

## クイックスタート

### 前提

- Node.js 20+
- Python 3.11–3.12（推奨: `py -3.12`。3.14 は一部依存関係未対応）
- Docker Desktop

> ローカルに既に PostgreSQL が `5432` で動いている場合があるため、Docker の DB は **5433** にマッピングしています。

### 1. 環境変数

```powershell
Copy-Item .env.example .env
```

### 2. インフラ起動（DB / Redis）

```powershell
.\scripts\dev-up.ps1
# または
docker compose up -d db redis
```

### 3. API（FastAPI）

```powershell
cd apps\api
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/health

### 4. Web（Next.js）

```powershell
cd apps\web
npm install
npm run dev
```

- App: http://localhost:3000

### 一括起動（Docker）

```powershell
docker compose up --build
```

## API 概要

| Method | Path | 説明 |
|--------|------|------|
| GET | `/health` | ヘルスチェック |
| POST | `/api/v1/auth/register` | ユーザー登録 |
| POST | `/api/v1/auth/login` | ログイン |
| GET/POST | `/api/v1/courses` | コース一覧 / 作成 |
| GET/POST | `/api/v1/enrollments` | 受講一覧 / 申込 |
| POST | `/api/v1/assignments/submit` | 課題提出 |
| GET | `/api/v1/assignments/pending` | 添削待ち一覧 |
| POST | `/api/v1/assignments/{id}/feedback` | 添削フィードバック |

## AWS 構成（段階導入）

`infra/terraform` に以下の骨格を配置しています。

- **VPC** — Public / Private subnet
- **RDS** — PostgreSQL
- **Cognito** — ユーザープール / アプリクライアント
- **ECS + CloudFront** — API / Web 配信

> Terraform は骨格のため、本番適用前にシークレット・証明書・ドメイン・セキュリティグループ等の拡充が必要です。

## 開発フェーズ方針

1. **Phase 0（現在）** — ローカル開発基盤・ドメイン骨格
2. **Phase 1** — 受講申込・コース閲覧の本番相当フロー
3. **Phase 2** — Cognito 連携・添削ワークフロー
4. **Phase 3** — レガシー基幹システムとの段階連携・切替
"# e_learning" 
