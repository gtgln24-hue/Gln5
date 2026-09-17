"""
GLN Quiz Bot - Core Commands Handler
Handles /choose, /stopgln, /approvegln, /help, /status, /start, and /leaderboard.
Enforces strict live member permissions, owner authorization, and structured audit logs.
"""

import logging
from typing import List, Optional
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import settings
from bot.database.queries import (
    is_group_approved,
    get_or_create_group,
    register_or_update_group,
    register_or_update_user,
    get_all_broadcast_destinations,
    get_unapproved_groups,
    approve_group,
    get_active_session,
    get_subject_cooldown,
    update_session_status,
)
from bot.services.quiz_service import quiz_manager
from bot.services.broadcast_service import broadcast_service
from bot.utils.permissions import is_group_admin_or_owner, is_bot_admin, is_bot_owner
from bot.utils.command_parser import (
    SafeCommand,
    log_handler_executed,
    log_command_rejected,
)

logger = logging.getLogger(__name__)
commands_router = Router(name="commands_router")

async def safe_reply(message: Message, text: str, **kwargs):
    """Safely replies to a message, falling back to message.answer if the original message was deleted in group."""
    try:
        return await message.reply(text, **kwargs)
    except Exception:
        try:
            return await message.answer(text, **kwargs)
        except Exception as e:
            logger.warning(f"Could not send reply/answer to chat {message.chat.id}: {e}")
            return None

@commands_router.message(SafeCommand("start"))
async def cmd_start(message: Message, bot: Bot):
    """Start command handler for direct or group chats."""
    log_handler_executed("cmd_start")
    chat = message.chat
    user = message.from_user
    if chat.type in ["group", "supergroup"]:
        await register_or_update_group(
            group_id=chat.id,
            group_name=chat.title or "Telegram Group",
            group_username=chat.username,
        )
        await safe_reply(
            message,
            "👋 <b>Welcome to GLN Quiz Bot!</b>\n\n"
            "An authorized Group Admin or Owner can start a quiz anytime with:\n"
            "👉 /choose\n\n"
            "Type /help for full instructions and quiz rules.",
            parse_mode="HTML",
        )
    else:
        if user:
            await register_or_update_user(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                is_dm=True,
            )
        await safe_reply(
            message,
            "🎓 <b>GLN Quiz Bot</b>\n\n"
            "I am a specialized Telegram Group Quiz Bot supporting Hindi language questions across 8 subjects:\n"
            "1. 📖 Hindi\n"
            "2. 🌍 Samajik Vigyan (Social Science)\n"
            "3. 🏛️ Itihas (History)\n"
            "4. 🔬 Science\n"
            "5. 🌿 Botany\n"
            "6. 🦁 Zoology\n"
            "7. 📐 Mathematics\n"
            "8. 🧪 Chemistry\n\n"
            "Add me to your Telegram group and promote me to Administrator to begin!\n"
            "Commands: /choose, /stopgln, /status, /help",
            parse_mode="HTML",
        )

@commands_router.message(SafeCommand("choose"))
async def cmd_choose(message: Message, bot: Bot):
    """
    Command: /choose (case-insensitive, e.g. /Choose, /CHOOSE, /choose@BotUsername)
    Starts the subject selection workflow.
    STRICT SECURITY: Only group administrators or owners may invoke this command.
    Checks live Telegram member status directly.
    """
    chat = message.chat
    user = message.from_user

    if not user:
        log_command_rejected("No from_user present on message")
        return

    # Check chat type: Normal groups and supergroups supported
    if chat.type not in ["group", "supergroup"]:
        log_command_rejected("/choose invoked outside group/supergroup")
        await safe_reply(
            message,
            "⚠️ <i>This command can only be used inside a Telegram group.</i>\n"
            "Add me to your group, promote me to Administrator, and send /choose.",
            parse_mode="HTML",
        )
        return

    # 1. Check if bot is an administrator in this group
    bot_is_admin = await is_bot_admin(bot, chat.id)
    if not bot_is_admin:
        log_command_rejected(f"Bot is not admin in group {chat.id}")
        await safe_reply(
            message,
            "⚠️ <b>PLEASE MAKE ME ADMIN IN YOUR GROUP</b>\n\n"
            "I need administrator rights to manage 15s timers and quizzes properly.",
            parse_mode="HTML",
        )
        return

    # Ensure group is registered regardless of approval status
    await register_or_update_group(
        group_id=chat.id,
        group_name=chat.title or "Telegram Group",
        group_username=chat.username,
        is_admin=bot_is_admin,
    )

    # 2. Check if group is approved by Bot Owner
    approved = await is_group_approved(chat.id)
    if not approved:
        log_command_rejected(f"Group {chat.id} is not approved")
        await safe_reply(
            message,
            "⚠️ <b>PLEASE CONTACT MY OWNER AND GET YOUR GROUP APPROVED.</b>\n\n"
            f"Group ID: <code>{chat.id}</code>",
            parse_mode="HTML",
        )
        return

    # 3. Check user permissions (Live Telegram API call: Owner or Administrator)
    is_admin = await is_group_admin_or_owner(bot, chat.id, user.id)
    if not is_admin:
        log_command_rejected(f"User {user.id} (@{user.username}) is not group admin or owner")
        await safe_reply(
            message,
            "❌ Only Group Admins or Owners can use this command.",
            parse_mode="HTML",
        )
        return

    # 4. Check if a quiz is already active
    active = quiz_manager.get_active(chat.id)
    if active:
        log_command_rejected(f"Quiz already running in group {chat.id} (Session: {active.session_id})")
        await safe_reply(
            message,
            "⚠️ <b>A quiz is already running in this group.</b>\n"
            "Use /stopgln to end it before starting a new one.",
            parse_mode="HTML",
        )
        return

    log_handler_executed("cmd_choose")

    # 5. Build Subject Selection Inline Keyboard
    buttons = [
        [
            InlineKeyboardButton(text="📖 Hindi", callback_data="choose_subject:Hindi"),
            InlineKeyboardButton(text="🌍 Samajik Vigyan", callback_data="choose_subject:Samajik Vigyan"),
        ],
        [
            InlineKeyboardButton(text="🏛️ Itihas", callback_data="choose_subject:Itihas"),
            InlineKeyboardButton(text="🔬 Science", callback_data="choose_subject:Science"),
        ],
        [
            InlineKeyboardButton(text="🌿 Botany", callback_data="choose_subject:Botany"),
            InlineKeyboardButton(text="🦁 Zoology", callback_data="choose_subject:Zoology"),
        ],
        [
            InlineKeyboardButton(text="📐 Maths", callback_data="choose_subject:Mathematics"),
            InlineKeyboardButton(text="🧪 Chemistry", callback_data="choose_subject:Chemistry"),
        ],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await safe_reply(
        message,
        "📚 <b>SELECT SUBJECT</b>\n\n"
        "Please select a subject to start the 100-question quiz session:",
        parse_mode="HTML",
        reply_markup=keyboard,
    )

@commands_router.message(SafeCommand("stopgln"))
async def cmd_stop(message: Message, bot: Bot):
    """
    Command: /stopgln (case-insensitive, e.g. /Stopgln, /STOPGLN, /stopgln@BotUsername)
    Stops current running quiz immediately and shows final rankings.
    Only allows:
    - Group Owner
    - Group Administrator
    - Bot Owner
    """
    chat = message.chat
    user = message.from_user

    if not user:
        log_command_rejected("No from_user on message")
        return

    if chat.type not in ["group", "supergroup"]:
        log_command_rejected("/stopgln invoked outside group/supergroup")
        await message.reply("⚠️ <i>This command can only be used inside a Telegram group.</i>", parse_mode="HTML")
        return

    # Check permissions (Group Owner, Group Admin, or Bot Owner)
    is_admin = await is_group_admin_or_owner(bot, chat.id, user.id)
    if not is_admin:
        log_command_rejected(f"User {user.id} not authorized to stop quiz")
        await message.reply(
            "❌ <b>Only Group Admins, Group Owners, or the Bot Owner can stop a quiz.</b>",
            parse_mode="HTML",
        )
        return

    active = quiz_manager.get_active(chat.id)
    if not active:
        active_db = await get_active_session(chat.id)
        if active_db:
            await update_session_status(active_db.session_id, "STOPPED")
            log_handler_executed("cmd_stop (db)")
            await message.reply(
                "🛑 <b>Active quiz session has been stopped.</b>\n\n"
                "You can now start a new quiz session using /choose.",
                parse_mode="HTML",
            )
            return
        log_command_rejected(f"No quiz active in group {chat.id}")
        await message.reply("⚠️ <i>No quiz is currently running in this group.</i>", parse_mode="HTML")
        return

    log_handler_executed("cmd_stop")
    username = user.username or user.first_name or f"User_{user.id}"
    await quiz_manager.stop_quiz(bot, chat.id, username)

@commands_router.message(SafeCommand("approvegln"))
async def cmd_approvegln(message: Message, bot: Bot, command_args: List[str] = None):
    """
    Command: /approvegln [GROUP_ID]
    Allowed ONLY for BOT OWNER (user_id == OWNER_ID).
    Never checks username for authorization.
    Saves approval permanently in the database.
    """
    user = message.from_user
    if not user:
        return

    # Strictly verify Bot Owner by user_id
    if not is_bot_owner(user.id):
        log_command_rejected(f"User {user.id} (@{user.username}) is NOT the Bot Owner (OWNER_ID: {settings.OWNER_ID})")
        await message.reply("❌ Only the Bot Owner can use this command.", parse_mode="HTML")
        return

    # Extract group_id from command arguments or from current chat
    target_group_id = None
    if command_args and len(command_args) > 0:
        raw_id = command_args[0].strip()
        try:
            target_group_id = int(raw_id)
        except ValueError:
            log_command_rejected(f"Invalid group ID format: '{raw_id}'")
            await message.reply(
                "❌ <b>Invalid Group ID format.</b> Must be an integer.\n\n"
                "Example: <code>/approvegln -1001234567890</code>",
                parse_mode="HTML",
            )
            return
    elif message.chat.type in ["group", "supergroup"]:
        target_group_id = message.chat.id
    else:
        # Private chat without arguments: Show unapproved groups or instructions
        unapproved = await get_unapproved_groups()
        if unapproved:
            buttons = [
                [
                    InlineKeyboardButton(
                        text=f"✅ Approve {grp['group_name'][:25]}",
                        callback_data=f"approve_grp:{grp['group_id']}",
                    )
                ]
                for grp in unapproved[:8]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await message.reply(
                "📋 <b>Unapproved Groups Waiting for Approval:</b>\n\n"
                "Tap a group below to approve it instantly, or use:\n"
                "<code>/approvegln &lt;group_id&gt;</code>\n\n"
                + "\n".join([f"• <b>{g['group_name']}</b>: <code>{g['group_id']}</code>" for g in unapproved[:8]]),
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            return

        log_command_rejected("No group ID provided for /approvegln in private chat")
        await message.reply(
            "⚠️ <b>How to Approve a Group:</b>\n\n"
            "<b>Option 1 (Easiest):</b> Add bot to the group, make it admin, and type <code>/approvegln</code> directly in that group.\n\n"
            "<b>Option 2:</b> In this private chat, specify the Group ID:\n"
            "<code>/approvegln &lt;group_id&gt;</code>\n\n"
            "Example:\n<code>/approvegln -1004375206761</code>",
            parse_mode="HTML",
        )
        return

    log_handler_executed("cmd_approvegln")

    # Record permanent approval in database
    await approve_group(target_group_id, owner_id=user.id)
    logger.info(f"Group {target_group_id} approved permanently in database by owner {user.id}")

    await message.reply(
        f"✅ <b>Group <code>{target_group_id}</code> has been approved successfully.</b>\n"
        f"Group Admins and Owners can now start quizzes with /choose.",
        parse_mode="HTML",
    )

    # Deliver announcement to the approved group
    try:
        await bot.send_message(
            chat_id=target_group_id,
            text=(
                "✅ <b>This group has been approved by the Bot Owner!</b>\n\n"
                "Group Admins and Owners can now start a quiz using:\n"
                "👉 /choose"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning(f"Could not deliver approval announcement to group {target_group_id}: {e}")

@commands_router.callback_query(F.data.startswith("approve_grp:"))
async def on_approve_group_callback(call: CallbackQuery, bot: Bot):
    """Handles 1-tap group approval button from Owner DM."""
    user = call.from_user
    if not user or not is_bot_owner(user.id):
        await call.answer("❌ Only Bot Owner can approve groups.", show_alert=True)
        return

    try:
        grp_id = int(call.data.split(":")[1])
    except (IndexError, ValueError):
        await call.answer("❌ Invalid group ID.")
        return

    await approve_group(grp_id, owner_id=user.id)
    logger.info(f"Group {grp_id} approved via 1-tap button by owner {user.id}")
    await call.answer("✅ Group approved successfully!")

    try:
        await call.message.edit_text(
            f"✅ <b>Group <code>{grp_id}</code> has been approved successfully!</b>\n"
            f"Admins in that group can now start quizzes using /choose.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    try:
        await bot.send_message(
            chat_id=grp_id,
            text=(
                "✅ <b>This group has been approved by the Bot Owner!</b>\n\n"
                "Group Admins and Owners can now start a quiz using:\n"
                "👉 /choose"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning(f"Could not deliver approval announcement to group {grp_id}: {e}")

@commands_router.message(SafeCommand("broadcast"))
async def cmd_broadcast(message: Message, bot: Bot, command_args_str: str = ""):
    """
    Command: /broadcast <message> (case-insensitive: /broadcast, /BROADCAST, /Broadcast, /broadcast@BotUsername)
    STRICT SECURITY: Works ONLY for the configured BOT OWNER (user_id == OWNER_ID).
    Never checks username.
    Shows preview confirmation first before sending.
    """
    user = message.from_user
    if not user:
        return

    # 1. Authorization: Only BOT OWNER by OWNER_ID environment variable
    if user.id != settings.OWNER_ID:
        log_command_rejected(f"Unauthorized /broadcast attempt by user {user.id}")
        await message.reply("❌ You are not authorized to use this command.")
        return

    log_handler_executed("cmd_broadcast")

    # 2. Extract message text after /broadcast
    broadcast_text = (command_args_str or "").strip()
    if not broadcast_text:
        await message.reply(
            "⚠️ Please provide a message.\n\n"
            "Example:\n"
            "/broadcast 🚀 Quiz bot has been updated!"
        )
        return

    # 3. Fetch all broadcast destinations to show accurate targets (both approved & unapproved groups + users)
    destinations = await get_all_broadcast_destinations()
    group_ids = destinations.get("groups", [])
    user_ids = destinations.get("users", [])
    approved_count = destinations.get("approved_count", 0)
    unapproved_count = destinations.get("unapproved_count", 0)
    total_targets = len(group_ids) + len(user_ids)

    preview_id = broadcast_service.create_preview(user.id, broadcast_text)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ SEND TO ALL", callback_data=f"bcast_send:{preview_id}"),
                InlineKeyboardButton(text="❌ CANCEL", callback_data=f"bcast_cancel:{preview_id}"),
            ]
        ]
    )

    preview_message = (
        f"📢 <b>BROADCAST PREVIEW</b>\n\n"
        f"<b>Message Content:</b>\n"
        f"{broadcast_text}\n\n"
        f"🎯 <b>Audience / Destinations:</b>\n"
        f"• 👥 <b>Total Groups:</b> {len(group_ids)} ({approved_count} approved, {unapproved_count} unapproved)\n"
        f"• 👤 <b>Bot Users:</b> {len(user_ids)}\n"
        f"• 📦 <b>Combined Total Targets:</b> {total_targets}\n\n"
        f"<i>Message will be sent to EVERY group (approved or not) and all bot users.</i>\n\n"
        f"Are you sure you want to broadcast now?"
    )

    await message.reply(preview_message, reply_markup=keyboard, parse_mode="HTML")

@commands_router.callback_query(F.data.startswith("bcast_cancel:"))
async def on_broadcast_cancel(call: CallbackQuery):
    """Handles cancellation of a pending broadcast."""
    user = call.from_user
    if not user or user.id != settings.OWNER_ID:
        await call.answer("❌ You are not authorized to use this command.", show_alert=True)
        return

    preview_id = call.data.split(":", 1)[1]
    broadcast_service.cancel_preview(preview_id)

    await call.answer("Cancelled")
    try:
        await call.message.edit_text("❌ Broadcast cancelled.")
    except Exception:
        await call.message.reply("❌ Broadcast cancelled.")

@commands_router.callback_query(F.data.startswith("bcast_send:"))
async def on_broadcast_send(call: CallbackQuery, bot: Bot):
    """Handles confirmation and initiates the rate-limited broadcast."""
    user = call.from_user
    if not user or user.id != settings.OWNER_ID:
        await call.answer("❌ You are not authorized to use this command.", show_alert=True)
        return

    preview_id = call.data.split(":", 1)[1]
    preview = broadcast_service.cancel_preview(preview_id)
    if not preview:
        await call.answer("⚠️ Broadcast expired or already initiated.", show_alert=True)
        return

    if broadcast_service.is_broadcasting:
        await call.answer("⚠️ Another broadcast is currently running. Please wait for it to complete.", show_alert=True)
        return

    message_text = preview["message_text"]

    await call.answer("Starting broadcast...")
    try:
        await call.message.edit_text(
            f"📢 <b>BROADCAST STARTED</b>\n\n"
            f"<b>Message:</b>\n"
            f"{message_text}\n\n"
            f"⏳ <i>Broadcasting to all groups and users in the background...</i>",
            parse_mode="HTML",
        )
    except Exception:
        await call.message.reply(
            f"📢 <b>BROADCAST STARTED</b>\n\n"
            f"<b>Message:</b>\n"
            f"{message_text}\n\n"
            f"⏳ <i>Broadcasting to all groups and users in the background...</i>",
            parse_mode="HTML",
        )

    # Execute asynchronous broadcasting to existing database destinations
    stats = await broadcast_service.execute_broadcast(bot, user.id, message_text)

    # Deliver final statistics strictly to the Bot Owner
    stats_text = (
        f"✅ <b>BROADCAST COMPLETED</b>\n\n"
        f"📊 <b>Detailed Delivery Report:</b>\n"
        f"• 👥 <b>Groups Delivered:</b> {stats.get('groups_sent', 0)} / {stats.get('groups_count', 0)}\n"
        f"  └ <i>(Includes approved: {stats.get('approved_groups_count', 0)}, unapproved: {stats.get('unapproved_groups_count', 0)})</i>\n"
        f"• 👤 <b>Bot Users Delivered:</b> {stats.get('users_sent', 0)} / {stats.get('users_count', 0)}\n"
        f"• 📦 <b>Total Delivered:</b> {stats.get('sent', 0)} / {stats.get('total', 0)}\n"
        f"• ❌ <b>Failed / Inaccessible:</b> {stats.get('failed', 0)}\n\n"
        f"<i>Delivered to all active groups and users regardless of approval status.</i>"
    )

    try:
        await bot.send_message(
            chat_id=user.id,
            text=stats_text,
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning(f"Could not send broadcast stats directly to owner chat {user.id}: {e}")
        try:
            await call.message.reply(stats_text, parse_mode="HTML")
        except Exception:
            pass

@commands_router.message(SafeCommand("help"))
async def cmd_help(message: Message, bot: Bot):
    """Help command showing bot capabilities and commands."""
    log_handler_executed("cmd_help")
    help_text = (
        "📚 <b>GLN QUIZ BOT - COMMANDS & GUIDE</b>\n\n"
        "<b>Available Commands:</b>\n"
        "• <code>/choose</code> - Start a new 100-question quiz (Group Admins & Owners)\n"
        "• <code>/stopgln</code> - Stop active quiz immediately and show final leaderboard\n"
        "• <code>/status</code> - View group approval and current quiz status\n"
        "• <code>/leaderboard</code> - View all-time top performers for this group\n"
        "• <code>/approvegln &lt;group_id&gt;</code> - Approve group for quizzes (Bot Owner only)\n"
        "• <code>/help</code> - Show this commands guide\n\n"
        "<b>Quiz Mechanics:</b>\n"
        "• ⏱️ <b>15 seconds</b> per question\n"
        "• 🟢 Instant private answer feedback (✅ Correct / ❌ Wrong)\n"
        "• 📊 Statistics & answer explanation shown when timer finishes\n"
        "• ⏳ <b>3-hour cooldown</b> applied to completed/stopped subjects\n"
        "• ⏸️ Auto-pause if 2 consecutive questions receive zero answers\n"
    )
    await message.reply(help_text, parse_mode="HTML")

@commands_router.message(SafeCommand("status"))
async def cmd_status(message: Message, bot: Bot):
    """Displays current group status, approval state, bot admin state, and active quiz state."""
    log_handler_executed("cmd_status")
    chat = message.chat
    if chat.type not in ["group", "supergroup"]:
        await message.reply(
            "ℹ️ <b>GLN Quiz Bot Status:</b> Online\n"
            "Add me to a Telegram group and promote me to Administrator to host quizzes.",
            parse_mode="HTML",
        )
        return

    approved = await is_group_approved(chat.id)
    bot_admin = await is_bot_admin(bot, chat.id)
    active = quiz_manager.get_active(chat.id)

    status_lines = [
        "📊 <b>GLN QUIZ BOT STATUS</b>\n",
        f"<b>Group:</b> {chat.title}",
        f"<b>Group ID:</b> <code>{chat.id}</code>",
        f"<b>Approval Status:</b> {'✅ Approved' if approved else '❌ Pending Approval'}",
        f"<b>Bot Admin Status:</b> {'✅ Administrator' if bot_admin else '⚠️ Not Admin (Promote to Admin)'}",
        f"<b>Active Quiz:</b> {'🟢 Running' if active else '⚪ Idle'}",
    ]

    if active:
        status_lines.append(f"<b>Current Subject:</b> {active.subject}")
        status_lines.append(f"<b>Progress:</b> Question {active.current_index + 1}/{active.total_questions}")

    await message.reply("\n".join(status_lines), parse_mode="HTML")

@commands_router.message(SafeCommand("leaderboard"))
async def cmd_leaderboard(message: Message, bot: Bot):
    """Displays top group performers."""
    log_handler_executed("cmd_leaderboard")
    chat = message.chat
    if chat.type not in ["group", "supergroup"]:
        await message.reply("⚠️ <i>Leaderboards are tracked per Telegram group.</i>", parse_mode="HTML")
        return

    from bot.database.db import AsyncSessionLocal
    from bot.database.models import GroupLeaderboard
    from sqlalchemy import select, desc

    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(GroupLeaderboard)
            .where(GroupLeaderboard.group_id == chat.id)
            .order_by(desc(GroupLeaderboard.points))
            .limit(10)
        )
        rows = res.scalars().all()

    if not rows:
        await message.reply("📊 <i>No leaderboard data recorded yet for this group.</i>", parse_mode="HTML")
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, r in enumerate(rows):
        badge = medals[i] if i < len(medals) else f"<b>{i+1}.</b>"
        user_tag = f"@{r.username}" if r.username and not r.username.startswith("User_") else (r.username or "Anonymous")
        acc = round((r.correct_count / (r.correct_count + r.wrong_count) * 100), 1) if (r.correct_count + r.wrong_count) > 0 else 0
        lines.append(f"{badge} {user_tag} — <b>{r.points} pts</b> ({r.correct_count}✅ / {r.wrong_count}❌, {acc}%)")

    board_text = (
        f"🏆 <b>ALL-TIME GROUP LEADERBOARD</b>\n"
        f"<i>Group: {chat.title}</i>\n\n"
        + "\n".join(lines)
    )
    await message.reply(board_text, parse_mode="HTML")
