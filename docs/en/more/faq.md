# FAQ

## Do I need a SEGA ID?

Not always. JiETNG supports two modes:

- Bind a SEGA account and use `maimai update`.
- Use import-only mode and upload records with the bookmarklet.

Automatic maimai NET sync requires a full SEGA binding.

## How do I start?

1. Send `bind` in a private chat.
2. Bind a SEGA account, or choose import-only mode.
3. SEGA users send `maimai update`; Import Token users create a token in `settings` and use the [bookmarklet](/en/bookmarklet).
4. Try `b50`, `rct50`, `ヒバナ record`, or `真極 plate`.

## Can I type my SEGA password in chat?

No. JiETNG never asks you to send a password in LINE chat. Enter it only on the binding web page.

## What is an Import Token?

An Import Token is a user-level upload credential for processed score JSON. It is not a developer token and cannot access other users.

The plaintext token is shown only once. Revoked tokens cannot upload anymore and can be deleted from settings.

## Why is my B50 not updated?

Queries use records currently stored in JiETNG. Run `maimai update`, or upload again with the bookmarklet.

## Can rebind change my SEGA ID?

No. `rebind` updates password, version, and Aime. To switch to another SEGA ID, use `unbind` and then `bind` again.

## Can I export records?

Yes:

```text
export json
export xml
```

The export contains processed profile, Best, Recent, and normalized score fields, not raw database rows.

## Why does a mention query fail?

The mentioned user must be registered in JiETNG and have score data. Missing targets do not fall back to your own data.

## How does nearby arcade search work?

Send a LINE location message. JiETNG queries both JP and INTL arcade data sources, merges them, and sorts by distance.

## Can I hide scores or leave the ranking?

Disable mention queries and ranking participation separately in `settings`; both default to enabled. These switches do not revoke developer permissions. Manage app permissions separately.

## Why is image language or background different?

Bot language and image language are separate: JP images use Japanese, INTL uses English. Some skins do not use backgrounds. Check the skin, background switch, and selected images.

## Does rec import my score?

No. `rec`, `rec -flex`, and `fix-rcd` analyze judgements without saving Best/Recent. Use `maimai update` or an Import Token upload to save records.

## Where is my first Import Token?

The import-only setup success page creates one immediately and shows plaintext once. You do not need a second token to start. If lost, create a new one in `settings` and revoke unneeded tokens. For stale bookmarklet tab caches, see [support](/en/more/support).
