#!/usr/bin/env python3
"""
JiETNG Telegram Bot
Calls JiETNG API via Telegram
Uses Telegram User ID directly as JiETNG user_id
"""

import json
import logging
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler
)

from api_client import JiETNGAPIClient

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load configuration
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Initialize API client
api_client = JiETNGAPIClient(
    base_url=config['api']['base_url'],
    token=config['api']['token']
)

# Admin user IDs
ADMIN_USER_IDS = set(config['telegram'].get('admin_user_ids', []))


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_USER_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user

    welcome_text = (
        f"Welcome, {user.first_name}!\n\n"
        "JiETNG Telegram Bot - maimai Account Management\n\n"
        "Available commands:\n"
        "/bind - Register account\n"
        "/unbind - Unbind account\n"
        "/myinfo - View my information\n"
        "/update - Update my data\n"
        "/b50 - Generate Best 50 image\n"
        "/search <keyword> - Search songs\n"
        "/versions - View all versions\n"
    )

    if is_admin(user.id):
        welcome_text += (
            "\nAdmin commands:\n"
            "/users - View all users\n"
            "/deleteuser <user_id> - Delete user\n"
        )

    await update.message.reply_text(welcome_text)


async def bind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /bind command"""
    user = update.effective_user
    user_id = str(user.id)
    nickname = user.full_name or user.first_name or f"User{user.id}"

    await update.message.reply_text("Creating account...")

    # Call API to create user
    result = api_client.create_user(
        user_id=user_id,
        nickname=nickname,
        language="en"
    )

    if result['success']:
        data = result['data']
        bind_url = data.get('bind_url', '')
        expires_in = data.get('expires_in', 120)

        keyboard = [[InlineKeyboardButton("Click to bind account", url=bind_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Account created successfully!\n\n"
            f"Nickname: {nickname}\n"
            f"User ID: {user_id}\n\n"
            f"Bind URL expires in {expires_in} seconds",
            reply_markup=reply_markup
        )
    else:
        error_msg = result['data'].get('message', 'Unknown error')
        await update.message.reply_text(f"Failed to create account: {error_msg}")

async def unbind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unbind command"""
    user = update.effective_user
    user_id = str(user.id)

    await update.message.reply_text(f"Unbinding account...")

    result = api_client.delete_user(user_id)

    if result['success']:
        await update.message.reply_text(f"Account unbound successfully")
    else:
        error_msg = result['data'].get('message', 'Unknown error')
        await update.message.reply_text(f"Failed to unbind: {error_msg}")


async def myinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /myinfo command"""
    user = update.effective_user
    user_id = str(user.id)

    await update.message.reply_text("Fetching information...")

    result = api_client.get_user(user_id)

    if result['success']:
        data = result['data']
        user_data = data.get('data', {})

        info_text = (
            f"User Information\n\n"
            f"User ID: {data.get('user_id', 'N/A')}\n"
            f"Nickname: {data.get('nickname', 'N/A')}\n"
            f"Language: {user_data.get('language', 'N/A')}\n"
            f"Version: {user_data.get('version', 'N/A')}\n"
        )

        if 'sega_id' in user_data:
            info_text += f"SEGA account: Bound\n"
        else:
            info_text += f"SEGA account: Not bound\n"

        if 'registered_at' in user_data:
            info_text += f"Registered: {user_data['registered_at']}\n"

        await update.message.reply_text(info_text)
    else:
        error_msg = result['data'].get('message', 'User not found')
        await update.message.reply_text(f"Failed to fetch info: {error_msg}\n\nUse /bind to register")


async def update_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /update command"""
    user = update.effective_user
    user_id = str(user.id)

    await update.message.reply_text("Sending update request...")

    result = api_client.update_user(user_id)
    task_id = result['data']['task_id']

    if result['success']:
        data = result['data']
        queue_size = data.get('queue_size', 0)

        keyboard = [
            [
                InlineKeyboardButton("Check update status", callback_data=f"update_status:{task_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Update task queued successfully!\n\n"
            f"Queue length: {queue_size}\n",
            reply_markup=reply_markup
        )
    else:
        error_msg = result['data'].get('message', 'Unknown error')
        await update.message.reply_text(f"Update failed: {error_msg}")


async def b50(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /b50 command - Generate Best 50 image"""
    user = update.effective_user
    user_id = str(user.id)

    # Arguments as filter command (e.g. /b50 -lv 14 15)
    command = " ".join(context.args) if context.args else ""

    await update.message.reply_text("Generating Best 50 image...")

    try:
        from image_generator import generate_b50_image

        # Generate image (fetch data via API)
        img_data = generate_b50_image(
            api_client=api_client,
            user_id=user_id,
            record_type="best50",
            command=command,
            ver="jp"
        )

        # Send image
        await update.message.reply_document(
            document=InputFile(img_data, filename="best50.png"),
            caption=f"Best 50 Scores" + (f"\nFilters: {command}" if command else "")
        )

    except ValueError as e:
        await update.message.reply_text(f"Generation failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error generating b50 image: {e}", exc_info=True)
        await update.message.reply_text(f"Generation failed: System error")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search command"""
    if not context.args:
        await update.message.reply_text("Please provide search keyword\n\nUsage: /search <song name>")
        return

    query = " ".join(context.args)

    await update.message.reply_text(f"Searching: {query}")

    result = api_client.search_songs(query=query, ver="jp", max_results=20)

    if result['success']:
        data = result['data']
        songs = data.get('songs', [])
        count = data.get('count', 0)

        if count == 0:
            await update.message.reply_text("No songs found")
            return

        # Generate image
        try:
            from image_generator import generate_search_image

            img_data = generate_search_image(songs=songs, query=query)

            await update.message.reply_document(
                document=InputFile(img_data, filename="search_result.png"),
                caption=f"Search results: {query}\nFound {count} songs"
            )
        except Exception as e:
            logger.error(f"Error generating search image: {e}", exc_info=True)

            # If image generation fails, return text list
            reply_text = f"Found {count} songs:\n\n"

            await update.message.reply_text(reply_text)
    else:
        error_msg = result['data'].get('message', 'Unknown error')
        await update.message.reply_text(f"Search failed: {error_msg}")


async def versions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /versions command"""
    await update.message.reply_text("Fetching version list...")

    result = api_client.get_versions()

    if result['success']:
        data = result['data']
        versions_list = data.get('versions', [])

        reply_text = f"maimai Versions (Total: {len(versions_list)}):\n\n"

        for version in versions_list:
            ver_name = version.get('version', 'Unknown')
            reply_text += f"{ver_name}\n"

        await update.message.reply_text(reply_text)
    else:
        error_msg = result['data'].get('message', 'Unknown error')
        await update.message.reply_text(f"Failed to fetch: {error_msg}")


# ==================== Admin Commands ====================

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /users command (admin only)"""
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("This command is for admins only")
        return

    await update.message.reply_text("Fetching user list...")

    result = api_client.get_users()

    if result['success']:
        data = result['data']
        users_list = data.get('users', [])
        count = data.get('count', 0)

        reply_text = f"User List (Total: {count}):\n\n"

        for i, u in enumerate(users_list[:20], 1):  # Show first 20 only
            user_id = u.get('user_id', 'N/A')
            nickname = u.get('nickname', 'Unknown')
            reply_text += f"{i}. {nickname} ({user_id})\n"

        if count > 20:
            reply_text += f"\n... {count - 20} more users not shown"

        await update.message.reply_text(reply_text)
    else:
        error_msg = result['data'].get('message', 'Unknown error')
        await update.message.reply_text(f"Failed to fetch: {error_msg}")


async def delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /deleteuser command (admin only)"""
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("This command is for admins only")
        return

    if not context.args:
        await update.message.reply_text("Please provide user ID\n\nUsage: /deleteuser <user_id>")
        return

    target_user_id = context.args[0]

    await update.message.reply_text(f"Deleting user {target_user_id}...")

    result = api_client.delete_user(target_user_id)

    if result['success']:
        await update.message.reply_text(f"User {target_user_id} deleted successfully")
    else:
        error_msg = result['data'].get('message', 'Unknown error')
        await update.message.reply_text(f"Deletion failed: {error_msg}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Error handler"""
    logger.error(f"Update {update} caused error {context.error}")

    if update and update.effective_message:
        await update.effective_message.reply_text(
            "An error occurred. Please try again later or contact admin."
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    old_text = query.message.text
    if data.startswith("update_status:"):
        task_id = data.split(":")[1]
        # Query update status and reply
        status_resp = api_client.get_task_status(task_id)
        status = status_resp['data']['status']
        if status == "running":
            new_text = f"Update task is running\nTask ID: {task_id}"
        elif status == "queued":
            new_text = f"Update task is still queued\nTask ID: {task_id}"
        elif status == "completed":
            new_text = "Update task completed successfully!"
        elif status == "cancelled":
            new_text = "Update task was cancelled"
        else:
            new_text = "Task not found. Please send command again."

        if old_text == new_text:
            return

        keyboard = [
            [
                InlineKeyboardButton("Check update status", callback_data=f"update_status:{task_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            new_text,
            reply_markup=reply_markup
        )

def main():
    """Main function"""
    # Create application
    application = Application.builder()\
        .token(config['telegram']['bot_token'])\
        .read_timeout(60)\
        .write_timeout(60)\
        .connect_timeout(30)\
        .pool_timeout(30)\
        .build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("bind", bind))
    application.add_handler(CommandHandler("unbind", unbind))
    application.add_handler(CommandHandler("myinfo", myinfo))
    application.add_handler(CommandHandler("update", update_data))
    application.add_handler(CommandHandler("b50", b50))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("versions", versions))

    # Admin commands
    application.add_handler(CommandHandler("users", users))
    application.add_handler(CommandHandler("deleteuser", delete_user))

    # Error handler
    application.add_error_handler(error_handler)
    
    # Button handler
    application.add_handler(CallbackQueryHandler(button_handler))

    # Start bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
