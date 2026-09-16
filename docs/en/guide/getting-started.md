# Getting Started

JiETNG supports two data sources: automatic sync from a bound SEGA account, or processed record uploads through an Import Token and the bookmarklet.

## Add JiETNG on LINE

Add JiETNG using the button below, then start binding in a private chat.

<LineFriendButton />

## Requirements

- A LINE account
- One data source:
  - SEGA ID and maimai NET account for `maimai update`
  - or a JiETNG Import Token for bookmarklet uploads

## Bind

Send this in a private chat:

```text
bind
```

The web page lets you choose:

- **Bind a SEGA account**: enter SEGA ID, password, server version (`jp` or `intl`), language, and Aime.
- **Use Import Token without SEGA binding**: create an account that only receives imported records.

Binding links expire. Send `bind` again to get a new link.

## Sync or Import Records

### SEGA Account

```text
maimai update
update
```

The bot syncs profile, Best records, Recent records, and related data from the selected maimai NET version. This command is self-only.

### Import Token

```text
settings
```

Save the Import Token from the setup success page, or create a new one in settings, then install the [bookmarklet](/en/bookmarklet). Open the official maimai mobile site, click the bookmarklet, generate a B50 / AP50 image, and click **Upload** when you want to upload best / recent / profile data.

Import Token plaintext is shown only once. The settings page can list tokens, revoke active tokens, and delete revoked tokens.

## Common Commands

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

See [command reference](/en/commands/) and [record commands](/en/commands/record).

## Settings and Rebind

```text
settings
```

Change language, timezone, background, display settings, and Import Tokens.

```text
rebind
```

Update SEGA password, version, and Aime. This is only available to users with a full SEGA binding. The SEGA ID itself cannot be changed through rebind.

## Unbind

Send `unbind` in a private LINE chat, open the returned web page, and confirm there. The link expires after 10 minutes; send `unbind` again if needed. Confirmation deletes the JiETNG user profile, Best/Recent records, custom backgrounds, and nickname cache. The bot has no undo operation.

## JP and INTL

- JP: `https://maimaidx.jp/maimai-mobile/home/`
- INTL: `https://maimaidx-eng.com/maimai-mobile/home/`

## After initial setup

Import-only setup immediately creates an Import Token on the success page. Save that plaintext value; if lost, create a new token in `settings`. Import-only users can send `bind` again to add a SEGA account. Bind/rebind links expire after 2 minutes.

See [basic commands](/en/commands/basic) for skins, backgrounds, ranking, and mention settings.
