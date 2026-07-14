# Railway「Application not found / train has not arrived」対処

## 意味
エッジがサービスに到達できない状態です（アプリ 404 とは別）。

よくある原因:
1. 最新デプロイが起動失敗（DB 接続待ちでヘルスチェック落ちなど）
2. Public Domain の Target Port 不一致
3. ドメイン未紐付け / デプロイ未成功

## コード側の対策（本リポジトリ）
- DB 初期化にタイムアウト（起動をブロックしない）
- `/health` は DB 不要で即応答
- railway.toml の healthcheck を外し、失敗デプロイで落ちにくくする
- `0.0.0.0:$PORT` 待受

## ダッシュボードで実施
1. **Deployments** で最新が Success か確認。失敗なら Redeploy
2. **Settings → Networking**
   - ドメインがあること
   - **Target Port = 5000**（またはログの PORT と一致）
3. Variables
   - `WEB_BASE_URL` を空に
   - `DATABASE_URL` は Postgres プラグインの参照を使う
4. ドメインが消えていたら **Generate Domain** を再実行
