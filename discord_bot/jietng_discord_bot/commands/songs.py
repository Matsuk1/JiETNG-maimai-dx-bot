from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from jietng import ValidationError

from ..i18n import interaction_lang, tr
from .support import (
    ServerVersion,
    SongChoiceView,
    attachment,
    localized_description,
    resolve_user_id,
    safe_filename_part,
    score_recognition_embed,
    song_search_summary,
)

if TYPE_CHECKING:
    from ..bot import JiETNGDiscordBot


def register_song_commands(bot: JiETNGDiscordBot) -> None:
    @bot.tree.command(name="song", description=localized_description("cmd.song.desc"))
    @app_commands.describe(
        query=localized_description("param.query"),
        ver=localized_description("param.ver"),
    )
    async def song(
        interaction: discord.Interaction,
        query: str,
        ver: ServerVersion = "jp",
    ) -> None:
        lang = interaction_lang(interaction)
        songs, payload = await _search_songs(bot, query, ver)
        if len(songs) != 1:
            view = SongChoiceView(
                bot, songs, mode="song", owner_id=None, ver=ver,
            ) if songs else None
            await interaction.response.send_message(
                song_search_summary(payload, lang),
                view=view,
            )
            return

        await interaction.response.defer(thinking=True)
        song_id = await _single_song_id(interaction, songs[0], lang)
        if song_id is None:
            return
        image = await bot.jietng.songs.info(song_id, ver=ver)
        await interaction.followup.send(
            file=attachment(image, f"jietng-song-{safe_filename_part(song_id)}.png")
        )

    @bot.tree.command(name="record", description=localized_description("cmd.record.desc"))
    @app_commands.describe(
        query=localized_description("param.query"),
    )
    async def record(
        interaction: discord.Interaction,
        query: str,
    ) -> None:
        lang = interaction_lang(interaction)
        user_id = resolve_user_id(bot, interaction)
        payload = await bot.jietng.songs.search(
            query.strip(), user_id=user_id, max_results=6,
        )
        songs = payload.get("songs") or []
        if len(songs) != 1:
            view = (
                SongChoiceView(
                    bot,
                    songs,
                    mode="record",
                    owner_id=interaction.user.id,
                    user_id=user_id,
                )
                if songs
                else None
            )
            await interaction.response.send_message(
                song_search_summary(payload, lang),
                view=view,
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)
        song_id = await _single_song_id(interaction, songs[0], lang)
        if song_id is None:
            return
        image = await bot.jietng.images.user_song(user_id, song_id)
        filename = (
            f"jietng-{safe_filename_part(user_id)}-"
            f"song-{safe_filename_part(song_id)}.png"
        )
        await interaction.followup.send(file=attachment(image, filename))

    @bot.tree.command(name="rec", description=localized_description("cmd.rec.desc"))
    @app_commands.describe(
        image=localized_description("param.image"),
        ver=localized_description("param.ver"),
    )
    async def recognize(
        interaction: discord.Interaction,
        image: discord.Attachment,
        ver: ServerVersion = "jp",
    ) -> None:
        lang = interaction_lang(interaction)
        await interaction.response.defer(thinking=True)
        image_bytes = await image.read(use_cached=True)
        try:
            payload = await bot.jietng.score_recognition.recognize(
                image_bytes,
                ver=ver,
                filename=image.filename,
            )
        except ValidationError as exc:
            if exc.status_code != 422:
                raise
            await interaction.followup.send(tr(lang, "recognition_failed"), ephemeral=True)
            return
        await interaction.followup.send(embed=score_recognition_embed(payload, lang))


async def _search_songs(
    bot: JiETNGDiscordBot,
    query: str,
    ver: ServerVersion,
) -> tuple[list, dict]:
    payload = await bot.jietng.songs.search(query.strip(), ver=ver, max_results=6)
    return payload.get("songs") or [], payload


async def _single_song_id(
    interaction: discord.Interaction,
    song: dict,
    lang: str,
) -> str | None:
    song_id = str(song.get("id") or "").strip()
    if song_id:
        return song_id
    await interaction.followup.send(tr(lang, "missing_song_id"), ephemeral=True)
    return None
