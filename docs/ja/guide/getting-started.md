# クイックスタート

JiETNG は 2 種類のデータ元に対応しています。SEGA アカウント連携による自動同期、または Import Token とブックマークレットによる加工済み成績のアップロードです。

## LINE で友だち追加

下のボタンから JiETNG を追加し、個別チャットで連携を始めましょう。

<LineFriendButton />

## 必要なもの

- LINE アカウント
- どちらか一つのデータ元：
  - `maimai update` 用の SEGA ID / maimai NET アカウント
  - またはブックマークレットアップロード用の JiETNG Import Token

## 連携

個別チャットで送信します。

```text
bind
```

Web ページでは次を選べます。

- **SEGA アカウント連携**：SEGA ID、パスワード、サーバー（`jp` / `intl`）、言語、Aime を入力。
- **Import Token モード**：SEGA 連携をせず、取り込みデータだけを使うアカウントを作成。

リンクが期限切れになった場合は、もう一度 `bind` を送信してください。

## 同期または取り込み

### SEGA アカウント

```text
maimai update
update
```

選択した maimai NET からプロフィール、Best、Recent などを同期します。このコマンドは自分自身にのみ作用します。

### Import Token

```text
settings
```

登録成功ページの Import Token を保存するか、設定ページで新規作成し、[ブックマークレット](/bookmarklet)を保存します。公式 maimai モバイルサイトでブックマークレットを実行すると、B50 / AP50 画像を生成できます。best / recent / profile をアップロードしたい場合は **Upload** を押します。

Token の平文は一度だけ表示されます。設定ページでは token の一覧、撤回、撤回済み token の削除ができます。

## よく使うコマンド

```text
b50
rct50
13.6 records
13sss+ prog
真極 plate
ヒバナ record
settings
export json
```

詳しくは[コマンド一覧](/commands/)と[レコードコマンド](/commands/record)を参照してください。

## 設定と再連携

```text
settings
```

言語、タイムゾーン、背景、表示設定、Import Token を管理できます。

```text
rebind
```

SEGA パスワード、サーバー、Aime を更新します。完全な SEGA 連携ユーザーのみ利用できます。SEGA ID 自体は変更できません。

## 解除

LINE の個別チャットで `unbind` を送り、返信の Web ページを開いて確定します。リンクの有効期限は 10 分です。期限切れの場合は再送してください。確定すると JiETNG のユーザー情報、Best/Recent、カスタム背景、ニックネームキャッシュを削除します。Bot から元に戻すことはできません。

## 初回設定のあと

Import Token モードの登録成功ページで Token が作成されます。その場で平文を保存してください。紛失した場合は `settings` で新規作成できます。取り込み専用ユーザーも再度 `bind` を送信して SEGA 連携へ移行できます。連携・再連携リンクの有効期限は 2 分です。

スキン、背景、ランキング、メンション設定は[基本コマンド](/commands/basic)を参照してください。
