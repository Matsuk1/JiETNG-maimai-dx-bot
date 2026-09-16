# 開発者 API

接続先：`https://jietng-endpoint.matsuk1.com`。開発者 API は `Authorization: Bearer <developer_token>`、取り込みは `Authorization: Bearer <import_token>` を使います。相互に代用できません。

## Token と権限

開発者 Token は管理者が管理画面で作成・撤回します。利用には保守者へ連絡してください。現在の LINE コアコマンドに `devtoken create/list/revoke/info` はありません。Import Token は取り込み専用登録の成功画面、または `settings` で取得でき、平文は一度だけ表示されます。

作成元 Token（owner）またはユーザーが承認した Token（granted）がアクセスできます。`POST /api/v2/users/<user_id>/permissions` で申請し、JSON `requester_name` は省略可能です。LINE ユーザーは権限メッセージの承認・拒否ボタンで処理します。ボタン操作は通常のテキストコマンドではありません。

| メソッド | パス | 権限・パラメータ |
|---|---|---|
| GET | `/api/v2/users` | 現 Token がアクセス可能なユーザー一覧 |
| POST | `/api/v2/users` | JSON/form の `user_id`・`nickname` 必須。201 で `bind_url`・`token`・`expires_in`。既存ユーザーは 409 |
| GET | `/api/v2/users/<user_id>` | owner/granted。SEGA ID・パスワード等を除くユーザー情報 |
| DELETE | `/api/v2/users/<user_id>` | owner のみ。ユーザー削除 |
| GET | `/api/v2/users/<user_id>/permissions/requests` | owner のみ。保留中の申請 |
| PATCH | `/api/v2/users/<user_id>/permissions/requests/<request_id>` | owner のみ。JSON `action` は `accept` / `reject` |
| DELETE | `/api/v2/users/<user_id>/permissions/<token_id>` | owner のみ。granted 権限撤回 |
| DELETE | `/api/v2/users/<user_id>/permissions/self` | granted 権限の自己撤回。owner は不可 |

## 連携と Web リンク

以下は owner または granted 権限が必要です。

```http
POST /api/v2/users/<user_id>/bind
PUT /api/v2/users/<user_id>/bind
GET /api/v2/users/<user_id>/bind-url
GET /api/v2/users/<user_id>/rebind-url
GET /api/v2/users/<user_id>/settings-url
```

POST は `sega_id`・`password` が必須。任意項目は `ver`（jp/intl）、`aime`、`timezone`、`language`。PUT は完全な連携済みであることが必要で、`sega_id`・`password`・`ver`・`aime` を更新し、言語とタイムゾーンを維持します。LINE の再連携フォームと異なり API PUT は SEGA ID も変更可能です。

連携・再連携リンクは 120 秒、設定リンクは 1800 秒有効です。リンク生成は 201 を返します。アカウント操作リンクは該当ユーザーだけに渡してください。

## 同期

```http
POST /api/v2/users/<user_id>/sync/stream
```

ユーザーへの権限と完全な SEGA 連携が必要です。`application/x-ndjson` で、ロック取得後に `accepted`、最後に `completed` または `failed` を返します。同期中の場合は `accepted` なしで `failed` になることがあります。HTTP 200 だけで成功と判断せず、最終イベントまで読んでください。ストリーム開始前の認証・頻度制限は HTTP エラーです。取り込み専用ユーザーは Import API を利用します。

## 画像・曲庫

```http
GET /api/v2/users/<user_id>/image?command=b50
GET /api/v2/users/<user_id>/songs/<song_id>/image
GET /api/v2/users/<user_id>/plate?title=真神
GET /api/v2/users/<user_id>/achievement?level=14%2B&rank=sss
GET /api/v2/songs/<song_id>/image?ver=jp
GET /api/v2/users/<user_id>/export?fmt=json
GET /api/v2/songs/search?q=ヒバナ&ver=jp&max_results=10
GET /api/v2/versions
GET /api/v2/dxdata?ver=jp
```

ユーザー画像・エクスポートには権限と保存済みデータが必要です。画像は既定で PNG。`format=base64` なら `{ "success": true, "format": "base64", "image": "..." }`。エクスポートは `fmt=json` / `fmt=xml`。`achievement` は `rank` を省略すると譜面一覧です。plate/achievement API には LINE の `-uc/-up/-c` フィルターはありません。

`songs/search` の `max_results` は 1–50、既定 10。現マッチャーは指定件数まで返すため、広い検索では先頭候補のみになることがあります。検索を絞ってください。バージョンは明示 `ver` > 権限のある `user_id` のバージョン > `jp`。候補なしは空の `songs` を持つ成功応答です。取得した曲 ID を楽曲画像に使用します。

### リザルト画像 OCR

```http
POST /api/v2/score-recognition
Authorization: Bearer <developer_token>
Content-Type: multipart/form-data
```

multipart フィールド：

| フィールド | 型 | 必須 | 説明 |
|------------|----|------|------|
| `image` | file | はい | JPEG、PNG、WebP。既定の上限は 20 MiB、4000 万画素 |
| `ver` | text | いいえ | `jp` または `intl`。既定は `jp` |

OCR は同期実行されます。曲名、達成率、完全な判定表を 1 つの譜面に照合して検証できた場合だけ成功します。検証可能な完全な結果を得られない場合は `422` です。Calc で不足判定を推定する場合があり、推定値を画像から直接読んだ値とは見なせません。

```bash
curl -X POST https://jietng-endpoint.matsuk1.com/api/v2/score-recognition \
  -H "Authorization: Bearer <developer_token>" \
  -F "ver=jp" \
  -F "image=@result.jpg"
```

成功 JSON の構造：

- `song`：dxdata の `id`、正式な `title`、`type`（`dx` / `std`）。
- `chart`：`difficulty`、表示レベル `level`、譜面定数 `internal_level`。
- `score.achievement`：達成率。
- `score.judgements`：`tap`、`hold`、`slide`、`touch`、`break`。各行は `critical_perfect`、`perfect`、`great`、`good`、`miss` を必ず含みます。
- `score.break_detail`：Flex で表示する現在最も可能性の高い BREAK 詳細判定です。`candidate_count` は選択した BREAK 行内の詳細候補数、Calc が行全体を推定した場合の任意フィールド `row_candidate_count` は行候補数です。離散的に一致する候補がない場合は `{}` です。
- `validation`：曲名一致方式、行列補正、MISS 補正、Calc 検証・補正、不確実な OCR セル。

```json
{
  "success": true,
  "song": {"id": "50d3df", "title": "Little \"Sister\" Bitch", "type": "dx"},
  "chart": {"difficulty": "master", "level": "13+", "internal_level": 13.8},
  "score": {
    "achievement": 100.5658,
    "judgements": {
      "tap": {"critical_perfect": 403, "perfect": 225, "great": 15, "good": 0, "miss": 1},
      "hold": {"critical_perfect": 18, "perfect": 7, "great": 0, "good": 0, "miss": 0},
      "slide": {"critical_perfect": 98, "perfect": 0, "great": 0, "good": 0, "miss": 0},
      "touch": {"critical_perfect": 66, "perfect": 0, "great": 0, "good": 0, "miss": 0},
      "break": {"critical_perfect": 20, "perfect": 13, "great": 0, "good": 0, "miss": 0}
    },
    "break_detail": {"critical_perfect": 20, "perfect_high": 12, "perfect_low": 1, "great_high": 0, "great_middle": 0, "great_low": 0, "good": 0, "miss": 0, "candidate_count": 1}
  },
  "validation": {
    "title_match_type": "exact",
    "exact_title_match": true,
    "compared_rows": 5,
    "matching_rows": 5,
    "row_offset": 0,
    "column_offset": 0,
    "miss_corrections": {},
    "achievement_calc": {"observed": 100.5658, "minimum": 100.4749, "maximum": 100.5733, "consistent": true, "complete": true},
    "calc_corrections": [],
    "uncertain_cells": []
  }
}
```

### OCR 結果画像

`POST /api/v2/score-recognition/image` は JSON エンドポイントと同じ multipart の `image`、`ver`、アップロード制限、認証方式を使用します。成功時は生成済みの `image/png` を返します。

```bash
curl -X POST https://jietng-endpoint.matsuk1.com/api/v2/score-recognition/image \
  -H "Authorization: Bearer <developer_token>" \
  -F "ver=jp" \
  -F "image=@result.jpg" \
  --output ocr-result.png
```

Calc に複数の有効解がある場合、画像エンドポイントは順位が最も高い候補を描画します。レスポンスヘッダー `X-JiETNG-OCR-Candidate-Index` と `X-JiETNG-OCR-Candidate-Count` で候補番号と候補総数を確認できます。

アップロード上限は `SCORE_RECOGNITION_API_MAX_IMAGE_BYTES` で変更できます。開発者 Token ごとにレート制限されます。

`/songs/search` のバージョン選択は、明示された `ver`、`user_id` に保存されたサーバー、既定の `jp` の順です。

`command` はユーザーが入力できる B 系コマンドを受け付けます。

| command | 意味 |
|---------|------|
| `b50` / `best50` | Best 50 |
| `b40` / `best40` | Best 40 |
| `b35` / `best35` | Best 35 |
| `b15` / `best15` | Best 15 |
| `ab35` / `allb35` | All Best 35 |
| `ab50` / `allb50` | All Best 50 |
| `apb50` / `ap50` | AP Best 50 |
| `fdxb50` / `fdx50` | FDX Best 50 |
| `rct50` / `r50` | Recent 50 |
| `idealb50` / `idlb50` | Ideal Best 50 |
| `s50` / `sun50` / `寸50` / `寸止め` | SSS+ / SSS 寸止め 50 |
| `unknown` | バージョン不明楽曲 |

`b50 -lv 14.7` のようにフィルターも含められます。

## ブックマークレット画像

```http
POST /api/web/session-image
Content-Type: application/json
```

ブックマークレットの JSON を受け取り、`image/jpeg` を返します。開発者 Token は不要です。

主な body：

```json
{
  "version": "jp",
  "cmd_type": "best50",
  "command": "-lv 14",
  "timezone": 9,
  "profile": {
    "name": "Player",
    "rating": "15000"
  },
  "records": {
    "best": [
      {
        "name": "Song Title",
        "difficulty": "master",
        "type": "dx",
        "score": "100.5000%",
        "dx_score": "1234",
        "score_icon": "sssp",
        "combo_icon": "ap",
        "sync_icon": "fdx"
      }
    ]
  }
}
```

`version` は `jp` または `intl` のみです。`cmd_type` は `best50`、`best40`、`best35`、`best15`、`allb35`、`allb50`、`apb50`、`fdxb50`、`idlb50`、`sun50` に対応し、`command` には `-lv 14` などのフィルターを指定します。`profile` と、1 件以上の有効な `records.best` が必要です。

画像内の言語はサーバーバージョンで固定されます。`jp` は日本語、`intl` は英語で描画され、ユーザーの言語設定やリクエスト内の他の言語フィールドでは変更できません。

このエンドポイントは画像生成のみです。保存には Import API を使います。

## 成績インポート

ユーザーは `settings` ページで Import Token を作成します。平文は一度だけ表示されます。

```http
POST /api/v2/import/records
Authorization: Bearer <import_token>
Content-Type: application/json
```

例：

```json
{
  "version": "jp",
  "profile": {
    "name": "Player",
    "rating": 15392,
    "trophy": "真皆伝",
    "trophy_content": "真皆伝",
    "trophy_url": "https://...",
    "icon_url": "https://...",
    "nameplate_url": "https://...",
    "class_rank_url": "https://...",
    "course_rank_url": "https://..."
  },
  "records": {
    "best": [
      {
        "title": "Song Title",
        "type": "DX",
        "difficulty": "Master",
        "achievement": 100.5,
        "dx_score": 1234,
        "dx_score_max": 1500,
        "rank": "SSS+",
        "combo": "AP+",
        "sync": "FDX+"
      }
    ],
    "recent": []
  }
}
```

`rating_block_path` はアップロード不要です。サーバーが `rating` から計算します。

置き換え規則：

- `"records": {"best": []}` は Best を空にします。
- `"records": {"recent": []}` は Recent を空にします。
- セクションを省略すると既存データを保持します。

成功レスポンス：

```json
{
  "success": true,
  "user_id": "U...",
  "best_count": 1200,
  "recent_count": 50,
  "version": "jp",
  "message": "Records imported successfully."
}
```

## CORS

本番 API は次のオリジンを許可しています。

- `https://maimaidx.jp`
- `https://maimaidx-eng.com`
- `https://dxrating.net`

ローカル開発では `http://localhost:5173` と `http://127.0.0.1:5173` も許可されます。

## エラー

| 状態 | 主な理由 |
|------|----------|
| `400` | パラメータまたは payload 不正 |
| `401` | Token 無効、SEGA 認証失敗 |
| `403` | 権限なし |
| `404` | ユーザー、Token、リクエスト、タスクがない |
| `409` | 連携状態の衝突 |
| `413` | OCR 画像がアップロード上限を超えた |
| `415` | OCR 画像形式が未対応 |
| `422` | 完全な成績として認識・検証できない画像 |
| `429` | レート制限 |
| `503` | 公式メンテナンスまたは同期キュー満杯 |

## 安全上の注意

- 開発者 Token や Import Token を公開フロントエンドに埋め込まないでください。
- Import Token はユーザー自身のブラウザまたは信頼できるツール用です。
- 第三者アプリは開発者 Token とユーザー権限フローを使ってください。
- unlink 時は `DELETE /api/v2/users/<user_id>/permissions/self` を呼び出してください。

## 取り込みの境界とクライアント

`records` に `best` または `recent` が必要です。明示した `[]` はその区画を消去し、省略した区画の記録は維持します。両方を空にすると 400。省略区画の `best_count` / `recent_count` は `null` です。

毎回 `profile` 全体を再構築します。省略した場合も同様で、名前・Rating・表示項目の不足は `Imported`・`0`・`N/A` 等の既定値になり、旧値は保持しません。バージョン優先順位は `maimai_version` > `version` > 保存済み > JP。無効値も現在は JP に戻るため、`jp` / `intl` のみ送ってください。

リポジトリの `client/` は同期・非同期 Python クライアントです。`discord_bot/` は開発者 API を使う独立した Discord 連携で、スラッシュコマンドは LINE テキストコマンドと異なります。導入方法は各ディレクトリの README を参照してください。

`achievement` は現在 `11`、`11+`、`12`、`12+`、`13`、`13+`、`14`、`14+`、`15` のみ対応し、LINE prog のカテゴリ・小数定数には対応しません。ユーザーは設定 Web で owner 関連付けを撤回できます。owner Token 自身による `/permissions/self` の撤回禁止とは別操作です。
