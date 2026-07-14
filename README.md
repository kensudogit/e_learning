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

## AWS 構成（目標アーキテクチャ）

```
                     Internet
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
  CloudWatch・WAF・SES・SQS
```

| レイヤ | AWS サービス | 役割 |
|--------|--------------|------|
| DNS | Route 53 | 独自ドメイン・ヘルスチェック |
| CDN | CloudFront | Web / API エッジ配信、HTTPS |
| 静的資産 | S3 | 教材ファイル・画像・フロント静的配信 |
| 入口 | ALB | ECS へのロードバランス、パスルーティング |
| アプリ | ECS Fargate | 受講 API / 添削 API / 管理 API / バッチ |
| 認証 | Cognito | ユーザープール・アプリクライアント |
| DB | Aurora PostgreSQL (RDS) | 業務データ（Private subnet） |
| 横断 | CloudWatch / WAF / SES / SQS | 監視・防御・メール・非同期キュー |

`infra/terraform` に VPC / RDS / Cognito / ECS / CloudFront の骨格があります。  
Route53・S3・WAF・SES・SQS・Aurora クラスタ・API 分割は段階導入で拡充します。

> 本番適用前にシークレット、ACM 証明書、セキュリティグループ、オリジン実体の設定が必要です。

## AWS デプロイ手順

画面の「利用手順」→「9. AWS デプロイ（ECS × Docker）」に、構成図・構築・運用の要約があります。

### 前提

| 項目 | 内容 |
|------|------|
| AWS アカウント | `ap-northeast-1` 推奨 |
| ツール | AWS CLI v2、Terraform ≥ 1.5、Docker Desktop |
| 権限 | Route53 / CloudFront / S3 / ALB / ECR / ECS / RDS(Aurora) / Cognito / WAF / SES / SQS / IAM |
| 認証 | `aws configure` または SSO |

### Step 1 — 基盤（Terraform）

```powershell
cd infra\terraform
terraform init
terraform plan  -var="environment=prod" -var="aws_region=ap-northeast-1"
terraform apply -var="environment=prod" -var="aws_region=ap-northeast-1"
```

作成される骨格: VPC、RDS(PostgreSQL)、Cognito、ECS クラスタ、CloudFront（placeholder origin）

続けて手動またはモジュール拡張で:

1. **Route 53** … ホストゾーン / CloudFront・ALB への Alias
2. **S3** … 教材・画像バケット（OAC で CloudFront のみ公開）
3. **WAF** … CloudFront / ALB に Web ACL 関連付け
4. **SES** … ドメイン検証、送信権限
5. **SQS** … 添削通知・発送・バッチ用キュー
6. **Aurora** … 必要に応じ RDS 単一インスタンスから Aurora クラスタへ移行

### Step 2 — コンテナイメージ（ECR → ECS）

ルート `Dockerfile` は API + サービス画面（静的）を含みます。マイクロサービス分割時は受講/添削/管理/バッチでリポジトリを分けます。

```powershell
aws ecr create-repository --repository-name elearning-enrollment --region ap-northeast-1
aws ecr get-login-password --region ap-northeast-1 `
  | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.ap-northeast-1.amazonaws.com

docker build -t elearning-app .
docker tag elearning-app:latest <ACCOUNT_ID>.dkr.ecr.ap-northeast-1.amazonaws.com/elearning-enrollment:latest
docker push <ACCOUNT_ID>.dkr.ecr.ap-northeast-1.amazonaws.com/elearning-enrollment:latest
```

### Step 3 — ECS サービス（受講 / 添削 / 管理 / バッチ）

| サービス | 役割 | ALB パス例 |
|----------|------|------------|
| 受講 API | コース・申込・学習・発送 | `/api/v1/courses`, `/enrollments`, `/learning`, … |
| 添削 API | 課題提出・返却 | `/api/v1/assignments/*` |
| 管理 API | アカウント・KPI・FAQ | `/api/v1/accounts`, `/analytics`, … |
| バッチ | 督促・集計・SQS ワーカー | スケジュール / SQS トリガ（ALB なし可） |

共通タスク環境変数（Secrets Manager / SSM 推奨）:

| 変数 | 内容 |
|------|------|
| `PORT` | ALB ターゲットと一致（例: `8080`） |
| `DATABASE_URL` | Aurora/RDS エンドポイント |
| `CORS_ORIGINS` | CloudFront ドメイン |
| `COGNITO_*` | ユーザープール設定 |
| `WEB_BASE_URL` | 空（同一オリジン）または CloudFront URL |
| `S3_BUCKET` / `SQS_*` / `SES_*` | 教材・非同期・メール（導入後） |

起動: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT}`  
ヘルスチェック: `/health`

### Step 4 — CloudFront + S3 + ALB

1. **S3** に教材・画像を配置（非公開 + CloudFront OAC）
2. CloudFront ビヘイビア例:
   - `/assets/*`, `/materials/*` → S3
   - その他 → ALB（API + サービス画面）
3. **Route 53** で `app.example.com` → CloudFront
4. **WAF** を CloudFront に関連付け（ボット・SQLi 等）

### Step 5 — 認証・メール・非同期

1. **Cognito** … Hosted UI / JWT 検証を API に接続
2. **SES** … 申込完了・添削返却・督促メール
3. **SQS** … 添削割当、発送指示、バッチ連携
4. **CloudWatch** … ECS/ALB/RDS ログ・アラーム

### Step 6 — 初期データ

```bash
# ECS Exec またはワンショットタスク
python -m app.scripts.seed
```

デモ: `learner@example.com` / `password123`

### 確認チェックリスト

- [ ] Route 53 → CloudFront 解決
- [ ] CloudFront → S3（静的）/ ALB（動的）
- [ ] ALB → ECS 各サービス（`/health` 200）
- [ ] Cognito ログイン・トークン検証
- [ ] Aurora/RDS 接続・シード
- [ ] WAF / CloudWatch アラーム有効
- [ ] SES サンドボックス解除（本番送信時）
- [ ] SQS コンシューマ（バッチ）稼働

### 現状コードとの対応

| 目標構成 | 現状 |
|----------|------|
| ECS 複数サービス | 単一 FastAPI イメージ（パスで論理分割可能） |
| Aurora | Terraform は RDS PostgreSQL 骨格（Aurora へ拡張可） |
| S3 / SES / SQS / WAF / Route53 | ドキュメント上の目標。モジュール追加で導入 |
| Cognito / CloudFront / ECS / VPC | `infra/terraform` 骨格あり |

## マイクロサービス化（Phase 3）

画面の「利用手順」→「10. マイクロサービス化」に手順・留意点の要約があります。

現状は **単一 FastAPI イメージ**です。分割は負荷・チーム境界・障害隔離の必要が出てから進めます。

### 推奨手順（要約）

1. 境界定義（受講 / 添削 / 管理 / バッチ）と公開 API 契約の固定  
2. モノリス内で router/domain をモジュール化（同一リポ・ビルド分離）  
3. Cognito JWT 検証の共有化、データは初期共有 DB + 所有権明示  
4. 跨ぎ処理は SQS / EventBridge（同期連鎖を避ける）  
5. サービスごと ECR・ECS Service・ALB パスルール  
6. Strangler Fig でパス単位切替 → 旧モノリス撤去  

### 留意・懸念点（要約）

| 観点 | 内容 |
|------|------|
| 分散トランザクション | Saga / アウトボックス + 補償。2PC は使わない |
| 共有 DB | 複数サービスからの直接更新を禁止し、所有境界を守る |
| チャットリネス | 1画面多呼び出し増。BFF・集約・キャッシュを検討 |
| 運用コスト | 監視・デプロイ面が増える。分割理由が薄いなら延期 |
| 障害伝播 | タイムアウト・サーキットブレーカ・冪等リトライ |
| 個人情報削除 | 複数ストア横断の削除オーケストレーションを先に設計 |

## 開発フェーズ方針

1. **Phase 0（現在）** — ローカル開発基盤・ドメイン骨格
2. **Phase 1** — 受講申込・コース閲覧の本番相当フロー（単一 ECS + RDS）
3. **Phase 2** — Cognito・添削・S3 教材・SES
4. **Phase 3** — API 分割・SQS バッチ・Aurora・WAF・Route53 本格運用
