import os
import logging
from datetime import timedelta

from telegram import Update, BotCommand
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)

TOKEN = os.getenv("BOT_TOKEN", "").strip()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("GroupGuard")

HELP = (
    "🛡️ *GroupGuard moderation bot*\n\n"
    "Admin commands (reply to a member's message where noted):\n"
    "/ban — ban replied-to member\n"
    "/unban USER_ID — unban by numeric ID\n"
    "/mute [minutes] — mute replied-to member (default 10)\n"
    "/unmute — unmute replied-to member\n"
    "/warn — issue a warning to replied-to member\n"
    "/rules — show group rules\n"
    "/setrules TEXT — set this group's rules\n"
    "/warnings — show your warnings (reply to member as admin to check theirs)\n"
    "/start — show this help\n\n"
    "Commands work only for group admins. No mass-reporting or external account actions."
)

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user or chat.type == "private":
        return False
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False

async def target_from_reply(update: Update):
    msg = update.effective_message
    if msg and msg.reply_to_message and msg.reply_to_message.from_user:
        return msg.reply_to_message.from_user
    await msg.reply_text("Is command ko member ke message par reply karke use karo.")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(HELP, parse_mode="Markdown")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.effective_message.reply_text("Sirf group admins ye command use kar sakte hain.")
    target = await target_from_reply(update)
    if target:
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, target.id)
            await update.effective_message.reply_text(f"🚫 {target.mention_html()} banned.", parse_mode="HTML")
        except Exception as e:
            log.warning("ban failed: %s", e)
            await update.effective_message.reply_text("Ban nahi hua. Bot ko ban permission do aur target admin na ho.")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.effective_message.reply_text("Sirf group admins ye command use kar sakte hain.")
    if not context.args or not context.args[0].isdigit():
        return await update.effective_message.reply_text("Usage: /unban USER_ID")
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, int(context.args[0]), only_if_banned=True)
        await update.effective_message.reply_text("✅ User unbanned (if previously banned).")
    except Exception as e:
        log.warning("unban failed: %s", e)
        await update.effective_message.reply_text("Unban nahi hua. ID aur bot permissions check karo.")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.effective_message.reply_text("Sirf group admins ye command use kar sakte hain.")
    target = await target_from_reply(update)
    if not target:
        return
    minutes = 10
    if context.args:
        if not context.args[0].isdigit() or not 1 <= int(context.args[0]) <= 10080:
            return await update.effective_message.reply_text("Minutes 1 se 10080 ke beech rakho.")
        minutes = int(context.args[0])
    try:
        until = update.effective_message.date + timedelta(minutes=minutes)
        from telegram import ChatPermissions
        await context.bot.restrict_chat_member(
            update.effective_chat.id, target.id,
            permissions=ChatPermissions(can_send_messages=False), until_date=until
        )
        await update.effective_message.reply_text(f"🔇 {target.mention_html()} muted for {minutes} min.", parse_mode="HTML")
    except Exception as e:
        log.warning("mute failed: %s", e)
        await update.effective_message.reply_text("Mute nahi hua. Bot ko restrict permission do aur target admin na ho.")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.effective_message.reply_text("Sirf group admins ye command use kar sakte hain.")
    target = await target_from_reply(update)
    if not target:
        return
    try:
        from telegram import ChatPermissions
        await context.bot.restrict_chat_member(
            update.effective_chat.id, target.id,
            permissions=ChatPermissions(can_send_messages=True, can_send_audios=True,
                can_send_documents=True, can_send_photos=True, can_send_videos=True,
                can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True,
                can_send_other_messages=True, can_add_web_page_previews=True)
        )
        await update.effective_message.reply_text(f"🔊 {target.mention_html()} unmuted.", parse_mode="HTML")
    except Exception as e:
        log.warning("unmute failed: %s", e)
        await update.effective_message.reply_text("Unmute nahi hua. Bot permissions check karo.")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.effective_message.reply_text("Sirf group admins ye command use kar sakte hain.")
    target = await target_from_reply(update)
    if not target:
        return
    key = f"warnings:{update.effective_chat.id}:{target.id}"
    count = context.application.bot_data.setdefault(key, 0) + 1
    context.application.bot_data[key] = count
    await update.effective_message.reply_text(f"⚠️ {target.mention_html()} warned. Total warnings: {count}.", parse_mode="HTML")

async def warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg = update.effective_message
    target = msg.reply_to_message.from_user if msg.reply_to_message else update.effective_user
    if target.id != update.effective_user.id and not await is_admin(update, context):
        return await msg.reply_text("Dusre member ke warnings dekhne ke liye admin hona zaroori hai.")
    count = context.application.bot_data.get(f"warnings:{chat.id}:{target.id}", 0)
    await msg.reply_text(f"{target.full_name}: {count} warning(s).")

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = context.application.bot_data.get(f"rules:{chat_id}", "Rules abhi set nahi hain. Admin se /setrules TEXT karne ko bolo.")
    await update.effective_message.reply_text(f"📜 Group rules\n\n{text}")

async def setrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.effective_message.reply_text("Sirf group admins rules set kar sakte hain.")
    text = " ".join(context.args).strip()
    if not text:
        return await update.effective_message.reply_text("Usage: /setrules Be respectful; no spam")
    context.application.bot_data[f"rules:{update.effective_chat.id}"] = text[:3500]
    await update.effective_message.reply_text("✅ Group rules updated.")

async def post_init(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start", "Show help and commands"),
        BotCommand("ban", "Ban replied-to member (admin)"),
        BotCommand("unban", "Unban by user ID (admin)"),
        BotCommand("mute", "Mute replied-to member (admin)"),
        BotCommand("unmute", "Unmute replied-to member (admin)"),
        BotCommand("warn", "Warn replied-to member (admin)"),
        BotCommand("rules", "Show group rules"),
        BotCommand("setrules", "Set group rules (admin)"),
        BotCommand("warnings", "Check warnings"),
    ])

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.error("Unhandled error: %s", context.error)


def main():
    if not TOKEN:
        raise SystemExit("BOT_TOKEN missing. Set it in Termux: export BOT_TOKEN='YOUR_BOT_TOKEN'")
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("warnings", warnings))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("setrules", setrules))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, lambda u, c: start(u, c)))
    app.add_error_handler(error_handler)
    log.info("GroupGuard started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
