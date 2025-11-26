#!/usr/bin/env python3
"""
JiETNG Telegram Bot
通过 Telegram 调用 JiETNG API
直接使用 Telegram User ID 作为 JiETNG user_id
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

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 加载配置
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 初始化 API 客户端
api_client = JiETNGAPIClient(
    base_url=config['api']['base_url'],
    token=config['api']['token']
)

# 管理员用户 ID 列表
ADMIN_USER_IDS = set(config['telegram'].get('admin_user_ids', []))


def is_admin(user_id: int) -> bool:
    """检查用户是否为管理员"""
    return user_id in ADMIN_USER_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    user = update.effective_user

    welcome_text = (
        f"欢迎，{user.first_name}\n\n"
        "JiETNG Telegram Bot - maimai 账户管理\n\n"
        "可用命令：\n"
        "/bind - 注册账户\n"
        "/unbind - 解绑账户\n"
        "/myinfo - 查看我的信息\n"
        "/update - 更新我的数据\n"
        "/b50 - 生成 Best 50 图片\n"
        "/search <关键词> - 搜索歌曲\n"
        "/versions - 查看所有版本\n"
    )

    if is_admin(user.id):
        welcome_text += (
            "\n管理员命令：\n"
            "/users - 查看所有用户\n"
            "/deleteuser <user_id> - 删除用户\n"
        )

    await update.message.reply_text(welcome_text)


async def bind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /bind 命令"""
    user = update.effective_user
    user_id = str(user.id)
    nickname = user.full_name or user.first_name or f"User{user.id}"

    await update.message.reply_text("正在创建账户...")

    # 调用 API 创建用户
    result = api_client.create_user(
        user_id=user_id,
        nickname=nickname,
        language="zh"
    )

    if result['success']:
        data = result['data']
        bind_url = data.get('bind_url', '')
        expires_in = data.get('expires_in', 120)

        keyboard = [[InlineKeyboardButton("点击绑定账户", url=bind_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"账户创建成功\n\n"
            f"昵称：{nickname}\n"
            f"用户ID：{user_id}\n\n"
            f"绑定链接将在 {expires_in} 秒后过期，请尽快绑定",
            reply_markup=reply_markup
        )
    else:
        error_msg = result['data'].get('message', '未知错误')
        await update.message.reply_text(f"创建失败：{error_msg}")

async def unbind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /unbind 命令"""
    user = update.effective_user
    user_id = str(user.id)

    await update.message.reply_text(f"正在解除绑定...")

    result = api_client.delete_user(user_id)

    if result['success']:
        await update.message.reply_text(f"已解除绑定")
    else:
        error_msg = result['data'].get('message', '未知错误')
        await update.message.reply_text(f"解除绑定失败：{error_msg}")


async def myinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /myinfo 命令"""
    user = update.effective_user
    user_id = str(user.id)

    await update.message.reply_text("正在获取信息...")

    result = api_client.get_user(user_id)

    if result['success']:
        data = result['data']
        user_data = data.get('data', {})

        info_text = (
            f"用户信息\n\n"
            f"用户ID：{data.get('user_id', 'N/A')}\n"
            f"昵称：{data.get('nickname', 'N/A')}\n"
            f"语言：{user_data.get('language', 'N/A')}\n"
            f"版本：{user_data.get('version', 'N/A')}\n"
        )

        if 'sega_id' in user_data:
            info_text += f"SEGA账户已绑定\n"
        else:
            info_text += f"SEGA账户未绑定\n"

        if 'registered_at' in user_data:
            info_text += f"注册时间：{user_data['registered_at']}\n"

        await update.message.reply_text(info_text)
    else:
        error_msg = result['data'].get('message', '用户不存在')
        await update.message.reply_text(f"获取失败：{error_msg}\n\n使用 /register 注册账户")


async def update_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /update 命令"""
    user = update.effective_user
    user_id = str(user.id)

    await update.message.reply_text("正在发送更新请求...")

    result = api_client.update_user(user_id)
    task_id = result['data']['task_id']

    if result['success']:
        data = result['data']
        queue_size = data.get('queue_size', 0)

        keyboard = [
            [
                InlineKeyboardButton("查看更新状态", callback_data=f"update_status:{task_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"更新任务已加入队列 🎉\n\n"
            f"当前队列长度：{queue_size}\n",
            reply_markup=reply_markup
        )
    else:
        error_msg = result['data'].get('message', '未知错误')
        await update.message.reply_text(f"更新失败：{error_msg}")


async def b50(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /b50 命令 - 生成 Best 50 图片"""
    user = update.effective_user
    user_id = str(user.id)

    # 参数作为筛选命令（如 /b50 -lv 14 15）
    command = " ".join(context.args) if context.args else ""

    await update.message.reply_text("正在生成 Best 50 图片...")

    try:
        from image_generator import generate_b50_image

        # 生成图片（通过 API 获取数据）
        img_data = generate_b50_image(
            api_client=api_client,
            user_id=user_id,
            record_type="best50",
            command=command,
            ver="jp"
        )

        # 发送图片
        await update.message.reply_document(
            document=InputFile(img_data, filename="best50.png"),
            caption=f"Best 50 成绩" + (f"\n筛选条件：{command}" if command else "")
        )

    except ValueError as e:
        await update.message.reply_text(f"生成失败：{str(e)}")
    except Exception as e:
        logger.error(f"Error generating b50 image: {e}", exc_info=True)
        await update.message.reply_text(f"生成失败：系统错误")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /search 命令"""
    if not context.args:
        await update.message.reply_text("请提供搜索关键词\n\n用法：/search <歌名>")
        return

    query = " ".join(context.args)

    await update.message.reply_text(f"搜索：{query}")

    result = api_client.search_songs(query=query, ver="jp", max_results=20)

    if result['success']:
        data = result['data']
        songs = data.get('songs', [])
        count = data.get('count', 0)

        if count == 0:
            await update.message.reply_text("未找到相关歌曲")
            return

        # 生成图片
        try:
            from image_generator import generate_search_image

            img_data = generate_search_image(songs=songs, query=query)

            await update.message.reply_document(
                document=InputFile(img_data, filename="search_result.png"),
                caption=f"搜索结果：{query}\n找到 {count} 首歌曲"
            )
        except Exception as e:
            logger.error(f"Error generating search image: {e}", exc_info=True)

            # 如果图片生成失败，返回文本列表
            reply_text = f"找到 {count} 首歌曲：\n\n"

            await update.message.reply_text(reply_text)
    else:
        error_msg = result['data'].get('message', '未知错误')
        await update.message.reply_text(f"搜索失败：{error_msg}")


async def versions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /versions 命令"""
    await update.message.reply_text("正在获取版本列表...")

    result = api_client.get_versions()

    if result['success']:
        data = result['data']
        versions_list = data.get('versions', [])

        reply_text = f"maimai 版本列表（共 {len(versions_list)} 个）：\n\n"

        for version in versions_list:
            ver_name = version.get('version', 'Unknown')
            reply_text += f"{ver_name}\n"

        await update.message.reply_text(reply_text)
    else:
        error_msg = result['data'].get('message', '未知错误')
        await update.message.reply_text(f"获取失败：{error_msg}")


# ==================== 管理员命令 ====================

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /users 命令（仅管理员）"""
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("此命令仅限管理员使用")
        return

    await update.message.reply_text("正在获取用户列表...")

    result = api_client.get_users()

    if result['success']:
        data = result['data']
        users_list = data.get('users', [])
        count = data.get('count', 0)

        reply_text = f"用户列表（共 {count} 人）：\n\n"

        for i, u in enumerate(users_list[:20], 1):  # 只显示前 20 个
            user_id = u.get('user_id', 'N/A')
            nickname = u.get('nickname', 'Unknown')
            reply_text += f"{i}. {nickname} ({user_id})\n"

        if count > 20:
            reply_text += f"\n... 还有 {count - 20} 个用户未显示"

        await update.message.reply_text(reply_text)
    else:
        error_msg = result['data'].get('message', '未知错误')
        await update.message.reply_text(f"获取失败：{error_msg}")


async def delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /deleteuser 命令（仅管理员）"""
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("此命令仅限管理员使用")
        return

    if not context.args:
        await update.message.reply_text("请提供用户ID\n\n用法：/deleteuser <user_id>")
        return

    target_user_id = context.args[0]

    await update.message.reply_text(f"正在删除用户 {target_user_id}...")

    result = api_client.delete_user(target_user_id)

    if result['success']:
        await update.message.reply_text(f"用户 {target_user_id} 已删除")
    else:
        error_msg = result['data'].get('message', '未知错误')
        await update.message.reply_text(f"删除失败：{error_msg}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """错误处理"""
    logger.error(f"Update {update} caused error {context.error}")

    if update and update.effective_message:
        await update.effective_message.reply_text(
            "发生错误，请稍后重试或联系管理员"
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    old_text = query.message.text
    if data.startswith("update_status:"):
        task_id = data.split(":")[1]
        # 查询更新状态并回复
        status_resp = api_client.get_task_status(task_id)
        status = status_resp['data']['status']
        if status == "running":
            new_text = f"更新任务正在运行中 🎉\n任务 ID: {task_id}"
        elif status == "queued":
            new_text = f"更新任务还在排队中 😵‍💫\n任务 ID: {task_id}"
        elif status == "completed":
            new_text = "更新任务已完成 ✅"
        elif status == "cancelled":
            new_text = "更新任务已取消 ☹️"
        else:
            new_text = "找不到该任务，请重新发送命令"

        if old_text == new_text:
            return

        keyboard = [
            [
                InlineKeyboardButton("查看更新状态", callback_data=f"update_status:{task_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            new_text,
            reply_markup=reply_markup
        )

def main():
    """主函数"""
    # 创建应用
    application = Application.builder()\
        .token(config['telegram']['bot_token'])\
        .read_timeout(60)\
        .write_timeout(60)\
        .connect_timeout(30)\
        .pool_timeout(30)\
        .build()

    # 注册命令处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("bind", bind))
    application.add_handler(CommandHandler("unbind", unbind))
    application.add_handler(CommandHandler("myinfo", myinfo))
    application.add_handler(CommandHandler("update", update_data))
    application.add_handler(CommandHandler("b50", b50))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("versions", versions))

    # 管理员命令
    application.add_handler(CommandHandler("users", users))
    application.add_handler(CommandHandler("deleteuser", delete_user))

    # 错误处理
    application.add_error_handler(error_handler)
    
    # 按钮处理
    application.add_handler(CallbackQueryHandler(button_handler))

    # 启动 Bot
    logger.info("Bot 启动中...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
