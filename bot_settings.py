import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "min_reward": 1,
    "non_usdt_notify": False
}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

WAITING_MIN_REWARD = 1

# ─── Settings helpers ───────────────────────────────────────────────

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            s = json.load(f)
            for k, v in DEFAULT_SETTINGS.items():
                if k not in s:
                    s[k] = v
            return s
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

def is_authorized(update: Update) -> bool:
    return str(update.effective_chat.id) == str(CHAT_ID)

# ─── /settings command ───────────────────────────────────────────────

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    s = load_settings()
    non_usdt_status = "✅ চালু" if s["non_usdt_notify"] else "❌ বন্ধ"

    keyboard = [
        [InlineKeyboardButton(f"💵 Minimum Reward: ${s['min_reward']} USDT", callback_data="set_min_reward")],
        [InlineKeyboardButton(f"🪙 Non-USDT Notify: {non_usdt_status}", callback_data="toggle_non_usdt")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚙️ <b>সেটিংস মেনু</b>\n\nনিচের বাটন চাপুন:",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

# ─── /status command ─────────────────────────────────────────────────

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    s = load_settings()
    non_usdt_status = "✅ চালু" if s["non_usdt_notify"] else "❌ বন্ধ"

    await update.message.reply_text(
        f"📊 <b>বর্তমান সেটিংস:</b>\n\n"
        f"💵 Minimum Reward: <b>${s['min_reward']} USDT</b>\n"
        f"🪙 Non-USDT Notify: <b>{non_usdt_status}</b>",
        parse_mode="HTML"
    )

# ─── Callback handlers ────────────────────────────────────────────────

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_authorized(update):
        return

    data = query.data
    s = load_settings()

    if data == "toggle_non_usdt":
        s["non_usdt_notify"] = not s["non_usdt_notify"]
        save_settings(s)
        status = "✅ চালু" if s["non_usdt_notify"] else "❌ বন্ধ"
        await query.edit_message_text(
            f"🪙 Non-USDT Notify এখন <b>{status}</b>!\n\n"
            f"আবার /settings দিয়ে মেনু খুলুন।",
            parse_mode="HTML"
        )

    elif data == "set_min_reward":
        await query.edit_message_text(
            f"💵 <b>Minimum Reward সেট করুন</b>\n\n"
            f"বর্তমান: <b>${s['min_reward']} USDT</b>\n\n"
            f"নতুন amount লিখুন (যেমন: <code>5</code> বা <code>100</code>):",
            parse_mode="HTML"
        )
        context.user_data["waiting_for"] = "min_reward"

# ─── Message handler (for min_reward input) ──────────────────────────

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    if context.user_data.get("waiting_for") == "min_reward":
        text = update.message.text.strip()
        try:
            value = float(text)
            if value < 0:
                raise ValueError
            s = load_settings()
            s["min_reward"] = value
            save_settings(s)
            context.user_data["waiting_for"] = None
            await update.message.reply_text(
                f"✅ Minimum Reward সেট হয়েছে: <b>${value} USDT</b>\n\n"
                f"এখন থেকে ${value}+ USDT এর quests এ নোটিফিকেশন পাবেন।",
                parse_mode="HTML"
            )
        except ValueError:
            await update.message.reply_text(
                "❌ ভুল! সংখ্যা লিখুন, যেমন: <code>5</code> বা <code>50.5</code>",
                parse_mode="HTML"
            )

# ─── Main ────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("🤖 Bot চালু হয়েছে...")
    app.run_polling()

if __name__ == "__main__":
    main()
      
