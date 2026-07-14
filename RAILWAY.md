# Railway 公開設定メモ

## 今回の問題
`/` が `WEB_BASE_URL=http://127.0.0.1:3000` へリダイレクトしていたため、
Public URL を開いてもローカルへ飛ばされていました。

## 修正後
- `/` は **公開オリジン上のポータル**（127.0.0.1 には飛ばさない）
- `RAILWAY_PUBLIC_DOMAIN` があればそれを優先
- uvicorn は `0.0.0.0:$PORT` で待受

## Railway Networking
画面の Target Port はログの待受ポートと一致させてください（現在は **5000**）。

Variables 推奨:
- `WEB_BASE_URL=` （空）
- `CORS_ORIGINS=*`
- `APP_ENV=production`
- `PORT` は手動設定しない（Railway 自動注入）
