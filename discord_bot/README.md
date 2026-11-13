# JiETNG Discord Bot

Discord slash-command bot for the JiETNG API.

Responses and slash-command descriptions are localized for English, Japanese,
and Chinese according to the user's Discord locale.

## Install

```bash
cd discord_bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure

Create a Discord application and bot token, then set:

```bash
export DISCORD_BOT_TOKEN="your_discord_bot_token"
export JIETNG_API_TOKEN="your_jietng_api_token"
```

Optional:

```bash
export JIETNG_BASE_URL="https://jietng-endpoint.matsuk1.com/api/v2"
export JIETNG_DISCORD_GUILD_ID="123456789012345678"
export JIETNG_DISCORD_DB="data/bot.sqlite3"
```

`JIETNG_DISCORD_GUILD_ID` syncs commands to one server immediately during
development. If omitted, commands are synced globally and may take longer to
appear.

## Run

```bash
python -m jietng_discord_bot
```

## Commands

- `/link user_id` links an existing external JiETNG user after permission approval.
- `/unlink` removes a `/link` external-user mapping and requests permission revocation.
- `/bind` creates a Discord-owned JiETNG user and sends a private binding button.
- `/unbind` deletes the Discord-owned JiETNG user created by `/bind`.
- `/profile` shows your JiETNG profile metadata.
- `/sync` streams your JiETNG data sync and replies when it finishes.
- `/b50 [command]`, `/b40 [command]`, `/b35 [command]`, `/b15 [command]` send Best records images.
- `/ab35 [command]`, `/ab50 [command]`, `/ap50 [command]`, `/fdx50 [command]`, `/r50 [command]`, `/idlb50 [command]` send specialized records images.
- `/achievement level [rank] [filter_mode]` sends a level / achievement image.
- `/plate title [filter_mode]` sends a plate image.
- `/song query [ver]` searches by song title / alias; one match sends the song info image, multiple matches send public selection buttons.
- `/record query` searches using the linked user's saved JP/INTL server version; one match sends your single-song record image, multiple matches send selection buttons.
- `/rec image [ver]` uploads a JPEG, PNG, or WebP result image through the JiETNG SDK 0.3 recognition API and displays the matched song, chart, judgements, BREAK details, and validation metadata.
- `/export format` downloads your processed records as JSON or XML.
- `/settings` creates your JiETNG settings button.
- `/rebind` creates your JiETNG rebind button.

The bot stores only Discord-to-JiETNG user id mappings in local SQLite. Score
data is requested from JiETNG API on demand.

`/link` and `/bind` are intentionally separate modes. `/link` connects this
Discord account to an existing JiETNG user through JiETNG's permission flow, and
`/unlink` only removes that permission-style connection. `/bind` creates a
Discord-owned JiETNG user id (`discord_<discord_user_id>`), stores that local
mapping, then returns JiETNG's private binding button. `/unbind` is the matching
destructive command for `/bind`: it deletes that Discord-owned JiETNG user from
JiETNG and removes the local mapping.

The two modes cannot be mixed for one Discord account. To switch from `/link`
mode to `/bind` mode, run `/unlink` first. To switch from `/bind` mode to
`/link` mode, run `/unbind` first.

The bot does not collect SEGA credentials inside Discord. For newly created
Discord accounts, the bot watches the JiETNG profile for a short time and sends
a private follow-up message when first-time binding is detected.

`/link` does not bypass JiETNG permissions: the target JiETNG user still needs
to accept the permission request before protected commands can read their data.
Because the JiETNG API token is shared by the whole Discord bot process, the
bot also enforces its own local Discord-user-to-JiETNG-user mapping. Protected
commands do not accept arbitrary `user_id` arguments.

## Differences from the LINE Bot

Discord does not have JiETNG's LINE mention identity model, so protected
commands are self-only. LINE commands that query mentioned users are not exposed
as arbitrary `user_id` inputs in Discord.

Some LINE-only commands are not included yet because they do not currently have
matching JiETNG v2 API endpoints in the SDK: friend records, ranking, artist /
designer search, random song, rating calculator, and permission accept/reject
management.
