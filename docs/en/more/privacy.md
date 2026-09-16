# Privacy Policy

## Overview

JiETNG is a personally maintained maimai DX score management tool. This page describes the data the current project may collect and process.

## Data Sources

- **SEGA account sync**: the binding page collects SEGA ID, password, server version, and Aime so JiETNG can log in to maimai NET and sync records.
- **Import Token import**: the settings page creates user Import Tokens. The bookmarklet or trusted tools upload processed `profile`, `best`, and `recent` data.

## Stored Data

JiETNG may store LINE user ID, language/timezone/background settings, SEGA credentials, server version, Aime, maimai profile display data, Best/Recent records, Import Token hashes and status, developer tokens, permission relationships, command usage events, and error logs.

Import Token plaintext is shown once. The server stores a hash.

## Usage

Data is used to sync or import records, generate score images and progress views, provide settings/export/API features, prevent abuse, debug issues, and maintain service stability.

## Third Parties

JiETNG interacts with LINE Platform and SEGA maimai NET. The bookmarklet runs on the official maimai mobile page, but uploaded data is processed score data and does not include the SEGA password.

## Delete and Export

Send `unbind` in a private LINE chat, open the returned web page, and confirm there. The link expires after 10 minutes; send `unbind` again if needed. Confirmation deletes the JiETNG user profile, Best/Recent records, custom backgrounds, and nickname cache. The bot has no undo operation.

```text
export json
export xml
```

Exports contain processed score data. Unbinding does not immediately purge every copy from historical logs, generated images, or existing backups; retention depends on the deployment.

## Security

- Web pages use HTTPS.
- Current application code writes SEGA passwords into the user JSON without field-level encryption. It does not establish an encrypted-at-rest guarantee. Use import-only mode if you do not want the service to store a password.
- Import Tokens and developer tokens should be treated like passwords.
- Revoked tokens cannot keep uploading or accessing resources.

## Contact

- GitHub Issues: [github.com/Matsuk1/JiETNG/issues](https://github.com/Matsuk1/JiETNG/issues)
- Discord: [Join server](https://discord.gg/NXxFn9T8Xz)

Effective date: 2026-09-16

## Visibility, demo, and images

Ranking participation and mention queries default to enabled and can be disabled separately in `settings`. Authorized integrations can access user data; permissions, including the owner association, can be revoked by the user in settings.

The online demo sends SEGA ID/password to JiETNG for that login and image generation without creating a persistent bound account. If Remember credentials is enabled, the browser's `demo_creds` cookie stores the credentials including the password for 90 days; unchecking it clears the cookie. The bookmarklet stores its Import Token in localStorage on the official site, separately for JP and INTL.

OCR downloads quoted LINE images for recognition. Generated images may be served as temporary files to LINE; recognition alone does not write personal records. Custom backgrounds are stored on the server. Log, backup, and temporary-image retention depends on deployment settings.
