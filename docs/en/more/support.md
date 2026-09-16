# Support

## Common Checks

### Records are not updated

- SEGA users: send `maimai update`.
- Import Token users: open the bookmarklet again and upload records.
- Query commands do not automatically resync official data.

### Binding fails

- Use `bind` in a private chat.
- Choose the correct server: `jp` or `intl`.
- If you only want bookmarklet uploads, choose import-only mode.

### Bookmarklet fails

- Open an official maimai mobile page:
  - `https://maimaidx.jp/maimai-mobile/home/`
  - `https://maimaidx-eng.com/maimai-mobile/home/`
- Make sure the browser is logged in.
- Image generation times out after 15 seconds.
- For uploads, make sure the Import Token has not been revoked.

### Mention query fails

The mentioned user must be registered in JiETNG and have score data. Missing targets do not fall back to your own data.

## When Reporting

Include the command, JP or INTL, whether you use SEGA binding or Import Token, screenshots or returned text, and approximate time.

Do not share SEGA passwords, Import Tokens, or developer tokens publicly.

## Channels

- GitHub Issues: [github.com/Matsuk1/JiETNG/issues](https://github.com/Matsuk1/JiETNG/issues)
- Discord: [Join server](https://discord.gg/NXxFn9T8Xz)

## More checks

- **Stale LINE menu**: send `refreshmenu` in private chat; successful refresh has no extra reply.
- **OCR fails**: use LINE Reply on the original image, then send `rec`. Include the title, achievement, and secondary judgement table. Use `rec -flex` for correction cards or `crop` to inspect regions.
- **Mention blocked / absent from rankings**: inspect the separate mention-query and ranking-participation switches in `settings`.
- **Bookmarklet keeps old scores**: it reuses profile/records from the tab's sessionStorage, even after reload. Close the old tab, open the official site in a new tab, and run the bookmarklet again. Recollect after switching Aime too.
- **Expired links**: bind/rebind last 2 minutes, settings 30 minutes, unbind 10 minutes. Request a new link with the corresponding command.

Demo and bookmarklet endpoints use different CORS allowlists. Rendering the demo locally does not mean the production demo API permits localhost; operators must configure `DEMO_CORS_ORIGINS` for that use.
