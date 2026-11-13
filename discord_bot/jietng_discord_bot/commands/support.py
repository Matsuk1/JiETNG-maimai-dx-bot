from __future__ import annotations

import asyncio
import logging
import re
from io import BytesIO
from typing import TYPE_CHECKING, Literal, Optional

import discord
from discord import app_commands
from jietng import (
    APIError,
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    QueueFullError,
    RateLimitedError,
    ValidationError,
)

from ..i18n import COMMAND_TRANSLATIONS, interaction_lang, tr

if TYPE_CHECKING:
    from ..bot import JiETNGDiscordBot


logger = logging.getLogger("jietng_discord_bot")

ServerVersion = Literal["jp", "intl"]
ExportFormat = Literal["json", "xml"]
FilterMode = Literal["uncleared", "unplayed", "cleared"]
AchievementLevel = Literal["11", "11+", "12", "12+", "13", "13+", "14", "14+", "15"]
AchievementRank = Literal[
    "s", "s+", "ss", "ss+", "sss", "sss+", "fc", "fc+", "ap", "ap+", "fdx", "fdx+",
]


def localized_description(key: str) -> app_commands.locale_str:
    return app_commands.locale_str(COMMAND_TRANSLATIONS[key]["en"], key=key)


def display_error(exc: APIError, lang: str = "zh") -> str:
    message = exc.message or exc.error or str(exc)
    if isinstance(exc, AuthenticationError):
        return tr(lang, "api_token_invalid")
    if isinstance(exc, PermissionDeniedError):
        return tr(lang, "permission_denied")
    if isinstance(exc, NotFoundError):
        return tr(lang, "not_found", message=message)
    if isinstance(exc, ValidationError):
        return tr(lang, "bad_params", message=message)
    if isinstance(exc, RateLimitedError):
        return tr(lang, "rate_limited")
    if isinstance(exc, QueueFullError):
        return tr(lang, "queue_full")
    if exc.status_code == 409:
        return tr(lang, "already_bound")
    return tr(lang, "api_error", message=message)


def resolve_user_id(bot: JiETNGDiscordBot, interaction: discord.Interaction) -> str:
    linked = bot.links.get_link(interaction.user.id)
    if linked:
        return linked
    raise app_commands.AppCommandError(tr(interaction_lang(interaction), "need_link"))


def attachment(data: bytes, filename: str) -> discord.File:
    return discord.File(BytesIO(data), filename=filename)


def safe_filename_part(value: str) -> str:
    sanitized = re.sub(r"[^\w.+-]+", "_", value.strip())
    return sanitized.strip("._") or "file"


def profile_summary(payload: dict, lang: str) -> str:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    personal = data.get("personal_info") or {}
    name = payload.get("nickname") or personal.get("name") or personal.get("userName") or "(unknown)"
    rating = personal.get("rating")
    if rating is None:
        rating = personal.get("playerRating")
    if rating is None:
        rating = "?"
    version = data.get("version") or "?"
    updated_at = data.get("updated_at") or data.get("last_sync") or data.get("last_update") or "?"
    return "\n".join([
        f"{tr(lang, 'profile_user_id')}：`{payload.get('user_id', '?')}`",
        f"{tr(lang, 'profile_name')}：`{name}`",
        f"{tr(lang, 'profile_rating')}：`{rating}`",
        f"{tr(lang, 'profile_version')}：`{version}`",
        f"{tr(lang, 'profile_updated')}：`{updated_at}`",
    ])


def song_search_summary(payload: dict, lang: str) -> str:
    songs = payload.get("songs") or []
    if not songs:
        return tr(lang, "no_song")
    return "\n".join(
        f"`{song.get('id') or '?'}`  **{song.get('title') or '(untitled)'}**  "
        f"`{song.get('type') or '?'}` `{song.get('version') or '?'}`"
        for song in songs
    )


def url_view(label: str, url: object) -> discord.ui.View:
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label=label, url=str(url)))
    return view


def requester_name(interaction: discord.Interaction) -> str:
    user = interaction.user
    display_name = getattr(user, "display_name", None) or getattr(user, "global_name", None)
    return f"Discord: {display_name or user.name} ({user.id})"


def ensure_link_available(
    bot: JiETNGDiscordBot,
    interaction: discord.Interaction,
    user_id: str,
) -> None:
    record = bot.links.get_record(interaction.user.id)
    if not record:
        return
    lang = interaction_lang(interaction)
    if record.mode == "bind":
        raise app_commands.AppCommandError(
            tr(lang, "already_has_discord_bind", linked=record.jietng_user_id)
        )
    if record.jietng_user_id != user_id:
        raise app_commands.AppCommandError(
            tr(lang, "already_has_external_link", linked=record.jietng_user_id)
        )


def has_bound_account(payload: dict) -> bool:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    personal = data.get("personal_info")
    return isinstance(personal, dict) and bool(personal)


async def watch_binding_completion(
    bot: JiETNGDiscordBot,
    interaction: discord.Interaction,
    user_id: str,
    *,
    timeout: float = 180.0,
    interval: float = 5.0,
) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        await asyncio.sleep(interval)
        try:
            payload = await bot.jietng.users.get(user_id)
        except APIError as exc:
            logger.debug("Binding watch skipped: user_id=%s error=%s", user_id, exc)
            continue
        if not has_bound_account(payload):
            continue
        try:
            await interaction.followup.send(
                tr(interaction_lang(interaction), "binding_done", user_id=user_id),
                ephemeral=True,
            )
        except discord.HTTPException:
            logger.debug("Binding completion followup failed: user_id=%s", user_id, exc_info=True)
        return


def start_binding_watch(
    bot: JiETNGDiscordBot,
    interaction: discord.Interaction,
    user_id: str,
) -> None:
    task = asyncio.create_task(
        watch_binding_completion(bot, interaction, user_id),
        name=f"binding-watch:{user_id}",
    )

    def log_failure(done: asyncio.Task) -> None:
        if done.cancelled():
            return
        error = done.exception()
        if error is not None:
            logger.error(
                "Binding watch task failed: user_id=%s",
                user_id,
                exc_info=(type(error), error, error.__traceback__),
            )

    task.add_done_callback(log_failure)


DIFFICULTY_COLORS = {
    "basic": 0x34A853,
    "advanced": 0xF4B400,
    "expert": 0xEA4335,
    "master": 0x8E44AD,
    "remaster": 0xB06FD3,
    "utage": 0x111111,
}


def _score_validation_summary(payload: dict, lang: str) -> str:
    validation = payload.get("validation") or {}
    achievement_calc = validation.get("achievement_calc") or {}
    parts = [
        f"{tr(lang, 'recognition_title_match')}: {validation.get('title_match_type') or '-'}",
        f"{tr(lang, 'recognition_rows')}: {validation.get('matching_rows', '-')}/{validation.get('compared_rows', '-')}",
        f"{tr(lang, 'recognition_offsets')}: {validation.get('row_offset', 0)}, {validation.get('column_offset', 0)}",
        f"{tr(lang, 'recognition_calc')}: {'OK' if achievement_calc.get('consistent') is True else 'CHECK'}",
    ]
    correction_count = len(validation.get("calc_corrections") or [])
    uncertain_count = len(validation.get("uncertain_cells") or [])
    if correction_count or uncertain_count:
        parts.append(f"{tr(lang, 'recognition_corrections')}: {correction_count} / {uncertain_count}")
    return "\n".join(parts)


def _score_correction_summary(payload: dict) -> str:
    validation = payload.get("validation") or {}
    field_labels = {
        "critical_perfect": "CP",
        "perfect": "PF",
        "great": "GR",
        "good": "GD",
        "miss": "MS",
    }
    lines = []
    for correction in validation.get("calc_corrections") or []:
        if not isinstance(correction, dict):
            continue
        row = str(correction.get("row") or "").upper()
        field = field_labels.get(correction.get("field"), str(correction.get("field") or "").upper())
        lines.append(
            f"{row} {field}: {correction.get('ocr')} -> {correction.get('validated')} "
            f"(MS {correction.get('miss_ocr')} -> {correction.get('miss_validated')})"
        )
    for row, correction in (validation.get("miss_corrections") or {}).items():
        if isinstance(correction, dict):
            lines.append(f"{str(row).upper()} MS: {correction.get('ocr')} -> {correction.get('validated')}")
    return "\n".join(lines[:8])


def score_recognition_embed(payload: dict, lang: str) -> discord.Embed:
    song = payload.get("song") or {}
    chart = payload.get("chart") or {}
    score = payload.get("score") or {}
    title = song.get("title")
    display_title = '\"\"' if title == "" else str(title or "-")
    difficulty = str(chart.get("difficulty") or "-").upper()
    level = chart.get("internal_level")
    level = level if level is not None else chart.get("level")
    chart_text = f"{difficulty} {level}" if level is not None else difficulty
    achievement = score.get("achievement")
    achievement_text = f"{achievement:.4f}%" if isinstance(achievement, (int, float)) else "-"

    embed = discord.Embed(
        title=tr(lang, "recognition_title"),
        description=f"### {display_title} [{str(song.get('type') or '-').upper()}]\n`{song.get('id', '-')}`",
        color=DIFFICULTY_COLORS.get(str(chart.get("difficulty") or "").lower(), 0x267D8B),
    )
    embed.add_field(name=tr(lang, "recognition_achievement"), value=f"**{achievement_text}**", inline=True)
    embed.add_field(name=tr(lang, "recognition_chart"), value=f"**{chart_text}**", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)

    judgements = score.get("judgements") or {}
    lines = [f"`{'TYPE':<5} {'CP':>4} {'PF':>4} {'GR':>4} {'GD':>4} {'MS':>4}`"]
    fields = ("critical_perfect", "perfect", "great", "good", "miss")
    for row_name in ("tap", "hold", "slide", "touch", "break"):
        row = judgements.get(row_name) or {}
        values = " ".join(f"{int(row.get(field, 0) or 0):>4}" for field in fields)
        lines.append(f"`{row_name.upper():<5} {values}`")
    embed.add_field(name=tr(lang, "recognition_judgements"), value="\n".join(lines), inline=False)

    break_detail = score.get("break_detail") or {}
    if break_detail:
        break_lines = [
            f"**CP 2600** `{break_detail.get('critical_perfect', 0)}`",
            f"**PF 2550 / 2500** `{break_detail.get('perfect_high', 0)}` / `{break_detail.get('perfect_low', 0)}`",
            f"**GR 2000 / 1500 / 1250** `{break_detail.get('great_high', 0)}` / `{break_detail.get('great_middle', 0)}` / `{break_detail.get('great_low', 0)}`",
            f"**GD / MS** `{break_detail.get('good', 0)}` / `{break_detail.get('miss', 0)}`",
        ]
        embed.add_field(name=tr(lang, "recognition_break_detail"), value="\n".join(break_lines), inline=False)

    correction_text = _score_correction_summary(payload)
    if correction_text:
        embed.add_field(name=tr(lang, "recognition_auto_corrections"), value=correction_text, inline=False)
    embed.set_footer(text=_score_validation_summary(payload, lang).replace("\n", "  |  "))
    return embed


def _button_label(text: str, fallback: str = "Select") -> str:
    text = (text or fallback).strip()
    return text if len(text) <= 80 else text[:77] + "..."


class SongChoiceButton(discord.ui.Button):
    def __init__(
        self,
        bot: JiETNGDiscordBot,
        song: dict,
        *,
        mode: str,
        owner_id: Optional[int],
        user_id: Optional[str] = None,
        ver: str = "jp",
        row: Optional[int] = None,
    ):
        super().__init__(
            label=_button_label(song.get("title") or song.get("id") or "Song"),
            style=discord.ButtonStyle.secondary,
            row=row,
        )
        self.bot = bot
        self.song = song
        self.mode = mode
        self.owner_id = owner_id
        self.user_id = user_id
        self.ver = ver

    async def callback(self, interaction: discord.Interaction) -> None:
        lang = interaction_lang(interaction)
        is_private = self.mode == "record"
        if self.owner_id is not None and interaction.user.id != self.owner_id:
            await interaction.response.send_message(tr(lang, "button_not_for_you"), ephemeral=True)
            return
        await interaction.response.defer(thinking=True, ephemeral=is_private)
        song_id = str(self.song.get("id") or "").strip()
        if not song_id:
            await interaction.followup.send(tr(lang, "missing_song_id"), ephemeral=True)
            return
        try:
            if is_private:
                if not self.user_id:
                    await interaction.followup.send(tr(lang, "missing_user_id"), ephemeral=True)
                    return
                image = await self.bot.jietng.images.user_song(self.user_id, song_id)
                filename = f"jietng-{safe_filename_part(self.user_id)}-song-{safe_filename_part(song_id)}.png"
            else:
                image = await self.bot.jietng.songs.info(song_id, ver=self.ver)
                filename = f"jietng-song-{safe_filename_part(song_id)}.png"
        except APIError as exc:
            await interaction.followup.send(display_error(exc, lang), ephemeral=True)
            return
        await interaction.followup.send(file=attachment(image, filename), ephemeral=is_private)


class SongChoiceView(discord.ui.View):
    def __init__(
        self,
        bot: JiETNGDiscordBot,
        songs: list,
        *,
        mode: str,
        owner_id: Optional[int],
        user_id: Optional[str] = None,
        ver: str = "jp",
    ):
        super().__init__(timeout=180)
        for index, song in enumerate(songs[:10]):
            self.add_item(
                SongChoiceButton(
                    bot,
                    song,
                    mode=mode,
                    owner_id=owner_id,
                    user_id=user_id,
                    ver=ver,
                    row=index // 5,
                )
            )
