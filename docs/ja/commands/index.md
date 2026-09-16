---
title: maimai DX コマンド一覧
description: JiETNG の maimai B50、スコア管理、レート内訳、プレート達成状況、楽曲検索、エクスポート、Import Token コマンド一覧。
---

# JiETNG コマンド一覧

現在のコマンド登録に基づいた一覧です。特記がない限り大文字小文字は区別されません。

`help` で一覧、対応コマンドに `-help` を付けると説明を表示します。引数が必要な一部コマンドは単独送信でも説明を返します。

## アカウントとシステム

| コマンド | 説明 |
|----------|------|
| `bind` | SEGA 連携または Import Token モードのリンクを作成 |
| `rebind` | SEGA パスワード、サーバー、Aime を更新 |
| `settings` | 設定と Import Token 管理 |
| `profile` / `getme` | プロフィールと連携状態 |
| `unbind` | 保存データを削除 |
| `maimai update` / `update` | maimai NET から同期 |
| `export json` / `export xml` | 加工済み成績を出力 |
| `status` | Bot 稼働状態 |
| `help` | コマンド一覧を表示 |

`bind`、`rebind`、`settings`、`update`、`export`、`unbind` は自分自身にのみ作用します。

## B 系スコア画像

| コマンド | 説明 |
|----------|------|
| `b50` / `best50` | Best 35 + Best 15 |
| `b40` / `best40` | 旧 Rating 構成 |
| `b35` / `best35` | 旧曲 Best 35 |
| `b15` / `best15` | 新曲 Best 15 |
| `ab35` / `allb35` | All Best 35 |
| `ab50` / `allb50` | All Best 50 |
| `apb50` / `ap50` | AP/AP+ Best 50 |
| `fdxb50` / `fdx50` | FDX/FDX+ Best 50 |
| `rct50` / `r50` | Recent 50 |
| `idealb50` / `idlb50` | Ideal Best 50 |
| `s50` / `sun50` / `寸50` / `寸止め` | SSS+ / SSS 寸止め 50：100.4000%-100.4999%、99.9000%-99.9999% |

`-lv`、`-ra`、`-scr`、`-dx`、`-star`、`-diff`、`-ver`、`-type`、`-next` / `-nxt`、`-page`、`-times` を追加できます。

## 楽曲と成績

| 形式 | 説明 |
|------|------|
| `[曲名] record` | 単曲個人成績 |
| `[曲名] info` | 楽曲情報 |
| `artist <キーワード> [ページ]` | アーティスト検索 |
| `designer <キーワード> [ページ]` | 譜面制作者検索 |
| `bpm <BPMまたは範囲> [ページ]` | BPM 検索。例: `bpm 180` / `bpm 0-120` / `bpm 120-180` |

## リストと目標

| 形式 | 説明 |
|------|------|
| `[レベル/定数] records [ページ]` | 成績リスト |
| `[レベル/カテゴリ] levels` | 譜面リスト |
| `[レベル][目標] prog` | レベル目標 |

目標：`s`、`s+`、`ss`、`ss+`、`sss`、`sss+`、`fc`、`fc+`、`ap`、`ap+`、`fdx`、`fdx+`。

目標とプレートは `-uc`、`-up`、`-c` に対応しています。

## その他

| コマンド | 説明 |
|----------|------|
| `[プレート] plate` | プレート達成状況 |
| `[バージョン] ver` | バージョン楽曲一覧 |
| `friend list` / `friends` | maimai フレンド一覧 |
| `friend-rcd <コード> [コマンド] [フィルター]` | フレンド成績画像 |
| `rc <定数>` | Rating 表 |
| `calc <tap> <hold> <slide> [touch] <break>` | Note スコア計算 |
| `random [レベル/定数]` | ランダム選曲 |
| `rank` / `ranking` / `rank jp` / `rank intl` | ランキング |
| LINE 位置メッセージ | JP / INTL 店舗データを統合して近い店舗を表示 |

## 画像認識と利用範囲

| コマンド | 説明 |
|---|---|
| `rec` / `rec -flex` | リザルト画像を引用し、判定分析の画像 / カードを表示 |
| `crop` | 引用画像の切り抜き領域を表示 |
| `info`（画像引用） | 曲名を認識して楽曲検索 |
| `fix-rcd 曲名`（複数行） | 判定修正テンプレートを送信 |
| `refreshmenu` | LINE メニューを無返信で更新 |

`unbind` は Web 確認ページを開きます。2 回目の確認テキストは不要です。`friends` / `friend-rcd` は個別チャット・SEGA 連携が必要。`prog` は曲カテゴリにも対応。ランキングは参加許可済み JiETNG ユーザーが対象で、メンション検索は相手の設定に従います。`levels` は本人のデータ、本人専用操作で他人をメンションすると拒否されます。

フィルター・Recent の制限・OCR は[レコードコマンド](/commands/record)、スキン・プライバシー設定は[基本コマンド](/commands/basic)を参照してください。
