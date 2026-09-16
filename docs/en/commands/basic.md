# Basic Commands

Basic commands cover account management, settings, status, export, and support information. Commands are case-insensitive unless noted.

## Account and Settings

```text
bind
```

Sends a private binding link. The page supports full SEGA binding and import-only mode with an Import Token.

```text
rebind
```

Updates SEGA password, server version, and Aime for fully bound users. It cannot change the SEGA ID.

```text
settings
```

Opens the settings page. It manages language, timezone, background, display settings, and Import Tokens. Full SEGA users and Import Token users can both use it.

```text
profile
getme
```

Shows account profile and binding state.

Send `unbind` in private chat, open the returned web page, and confirm there. The link expires in 10 minutes. Confirmation removes the JiETNG profile, Best/Recent, custom backgrounds, and nickname cache; there is no bot undo.

## Update

```text
maimai update
update
```

Syncs latest records from maimai NET. Requires a full SEGA binding and is self-only.

Import Token users should upload through the bookmarklet.

## Export

```text
export json
export xml
```

Exports processed JiETNG data, not raw database rows. The export includes profile, version, Best records, Recent records, and normalized fields needed to reproduce score images.

## Other Commands

```text
status
rank
rank jp
rank intl
```

`rank` / `ranking` shows DX Rating rankings, optionally scoped to `jp` or `intl`.

## Scope

`bind`, `rebind`, `settings`, `update`, `export`, and `unbind` are self-only. They never operate on mentioned users.

## Settings in detail

Send `settings` in a private chat. The link expires after 30 minutes.

- **Language and time zone**: interactions support Simplified Chinese, Traditional Chinese, English, and Japanese. Image text follows the server: Japanese for JP, English for INTL.
- **Image skin**: choose an available skin. Some skins do not use backgrounds; missing templates fall back to the default skin.
- **Backgrounds**: enable backgrounds, select images, and adjust blur/overlay. Upload up to 2 custom images, each at most 5 MiB. PNG, JPEG, and WebP are supported; HEIC/HEIF also require server decoder support.
- **Ranking and mentions**: opt out of the global ranking or disable other users' mention queries. Both settings default to enabled when unset.
- **Import Tokens**: create, revoke, and delete revoked tokens. Plaintext is shown once.
- **App permissions**: review integrations and revoke permissions, including the account creator's owner association.

`rank` covers participating JiETNG users on the same server, not every player in SEGA's service. `rank jp` / `rank intl` show that server's top 15.

`refreshmenu` relinks the LINE menu for your current binding state without an extra success reply.

## Help

Send `help` for categories or `b50 -help`, `artist -help`, and `rec -help` for supported command help. Not every internal button action has chat help. Self-only commands reject mentions of another user instead of silently acting on your account.
