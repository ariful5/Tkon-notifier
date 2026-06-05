import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
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

# ─── Settings menu builder ──────────────────────────────────────────

def build_settings_menu(s):
    non_usdt_label = "🟢 চালু আছে — বন্ধ করতে চাপুন" if s["non_usdt_notify"] else "🔴 বন্ধ আছে — চালু করতে চাপুন"

    keyboard = [
        [InlineKeyboardButton(
            f"💵 সর্বনিম্ন রিওয়ার্ড: ${s['min_reward']} USDT",
            callback_data="noop"
        )],
        [InlineKeyboardButton(
            "✏️ পরিমাণ পরিবর্তন করুন",
            callback_data="set_min_reward"
        )],

        [InlineKeyboardButton("─────────────────────", callback_data="noop")],

        [InlineKeyboardButton(
            "🪙 Non-USDT কোয়েস্ট নোটিফিকেশন",
            callback_data="noop"
        )],
        [InlineKeyboardButton(
            non_usdt_label,
            callback_data="toggle_non_usdt"
        )],

        [InlineKeyboardButton("─────────────────────", callback_data="noop")],

        [InlineKeyboardButton("📊 বর্তমান স্ট্যাটাস দেখুন", callback_data="show_status"),
         InlineKeyboardButton("❓ সাহায্য", callback_data="show_help")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ─── /start command ─────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text(
        "👋 <b>TaskOn Notifier Bot এ স্বাগতম!</b>\n\n"
        "📌 <b>কমান্ড লিস্ট:</b>\n\n"
        "⚙️ সেটিংস মেনু খুলুন          /settings\n"
        "📊 বর্তমান সেটিংস দেখুন       /status\n"
        "❓ সাহায্য দেখুন                  /help\n\n"
        "👇 নিচের <b>/settings</b> চাপুন বা লিখুন শুরু করতে।",
        parse_mode="HTML"
    )

# ─── /settings command ───────────────────────────────────────────────

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    s = load_settings()
    reply_markup = build_settings_menu(s)

    await update.message.reply_text(
        "⚙️ <b>সেটিংস মেনু</b>\n\n"
        "💵 <b>সর্বনিম্ন রিওয়ার্ড:</b> এই পরিমাণের কম USDT রিওয়ার্ডের কোয়েস্ট skip হবে\n"
        "🪙 <b>Non-USDT Notify:</b> USDT ছাড়া অন্য টোকেনের কোয়েস্টে নোটিফিকেশন পাবেন কিনা\n\n"
        "নিচের বাটন চাপুন পরিবর্তন করতে 👇",
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
        f"💵 <b>সর্বনিম্ন রিওয়ার্ড:</b> ${s['min_reward']} USDT\n"
        f"   └ এর কম হলে notification আসবে না\n\n"
        f"🪙 <b>Non-USDT Notify:</b> {non_usdt_status}\n"
        f"   └ {'USDT ছাড়া অন্য টোকেনেও নোটিফাই করবে' if s['non_usdt_notify'] else 'শুধু USDT কোয়েস্টে নোটিফাই করবে'}",
        parse_mode="HTML"
    )

# ─── /help command ───────────────────────────────────────────────────

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text(
        "❓ <b>সাহায্য</b>\n\n"
        "🔹 <b>সর্বনিম্ন রিওয়ার্ড কী?</b>\n"
        "   TaskOn এ যে কোয়েস্টের মোট USDT পুরস্কার এই পরিমাণের কম,\n"
        "   সেগুলোর notification আসবে না।\n"
        "   উদাহরণ: $5 সেট করলে $4 এর কোয়েস্ট skip হবে।\n\n"
        "🔹 <b>Non-USDT Notify কী?</b>\n"
        "   কিছু কোয়েস্টে USDT এর বদলে অন্য টোকেন (যেমন: ETH, BNB) দেয়।\n"
        "   চালু থাকলে সেগুলোরও notification পাবেন।\n\n"
        "🔹 <b>সেটিংস পরিবর্তন করতে:</b>\n"
        "   /settings লিখুন → বাটন চাপুন",
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

    if data == "noop":
        return

    elif data == "show_help":
        await query.edit_message_text(
            "❓ <b>সাহায্য</b>\n\n"
            "🔹 <b>সর্বনিম্ন রিওয়ার্ড কী?</b>\n"
            "   এই পরিমাণের কম USDT রিওয়ার্ডের কোয়েস্ট skip হবে।\n"
            "   উদাহরণ: $5 সেট করলে $4 এর কোয়েস্ট আসবে না।\n\n"
            "🔹 <b>Non-USDT Notify কী?</b>\n"
            "   USDT ছাড়া অন্য টোকেন (ETH, BNB ইত্যাদি) এর কোয়েস্টেও\n"
            "   notification পেতে চাইলে চালু রাখুন।\n\n"
            "⬅️ ফিরে যেতে /settings লিখুন",
            parse_mode="HTML"
        )

    elif data == "show_status":
        non_usdt_status = "✅ চালু" if s["non_usdt_notify"] else "❌ বন্ধ"
        await query.edit_message_text(
            f"📊 <b>বর্তমান সেটিংস:</b>\n\n"
            f"💵 <b>সর্বনিম্ন রিওয়ার্ড:</b> ${s['min_reward']} USDT\n"
            f"   └ এর কম হলে notification আসবে না\n\n"
            f"🪙 <b>Non-USDT Notify:</b> {non_usdt_status}\n"
            f"   └ {'USDT ছাড়া অন্য টোকেনেও নোটিফাই করবে' if s['non_usdt_notify'] else 'শুধু USDT কোয়েস্টে নোটিফাই করবে'}\n\n"
            f"⬅️ ফিরে যেতে /settings লিখুন",
            parse_mode="HTML"
        )

    elif data == "toggle_non_usdt":
        s["non_usdt_notify"] = not s["non_usdt_notify"]
        save_settings(s)
        status = "✅ চালু" if s["non_usdt_notify"] else "❌ বন্ধ"
        desc = "এখন Non-USDT কোয়েস্টেও notification পাবেন।" if s["non_usdt_notify"] else "এখন শুধু USDT কোয়েস্টে notification পাবেন।"

        await query.edit_message_text(
            f"🪙 <b>Non-USDT Notify: {status}</b>\n\n"
            f"✔️ {desc}\n\n"
            f"⬅️ আবার মেনু দেখতে /settings লিখুন",
            parse_mode="HTML"
        )

    elif data == "set_min_reward":
        await query.edit_message_text(
            f"💵 <b>সর্বনিম্ন রিওয়ার্ড পরিবর্তন করুন</b>\n\n"
            f"📌 বর্তমান সেটিং: <b>${s['min_reward']} USDT</b>\n\n"
            f"নতুন পরিমাণ লিখে পাঠান:\n"
            f"(যেমন: <code>5</code> বা <code>50</code> বা <code>100</code>)\n\n"
            f"⚠️ শুধু সংখ্যা লিখুন, কোনো চিহ্ন নয়",
            parse_mode="HTML"
        )
        context.user_data["waiting_for"] = "min_reward"

# ─── Message handler ──────────────────────────────────────────────────

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
                f"✅ <b>সেটিং সেভ হয়েছে!</b>\n\n"
                f"💵 সর্বনিম্ন রিওয়ার্ড: <b>${value} USDT</b>\n\n"
                f"এখন থেকে ${value} বা এর বেশি USDT এর কোয়েস্টে notification পাবেন।\n\n"
                f"⬅️ মেনুতে ফিরতে /settings লিখুন",
                parse_mode="HTML"
            )
        except ValueError:
            await update.message.reply_text(
                "❌ <b>ভুল ইনপুট!</b> শুধু সংখ্যা লিখুন।\n"
                "যেমন: <code>5</code> বা <code>50</code>",
                parse_mode="HTML"
            )

# ─── BotFather কমান্ড সেটআপ ──────────────────────────────────────────

async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start",    "🤖 Bot শুরু করুন"),
        BotCommand("settings", "⚙️ সেটিংস মেনু খুলুন"),
        BotCommand("status",   "📊 বর্তমান সেটিংস দেখুন"),
        BotCommand("help",     "❓ সাহায্য দেখুন"),
    ])

# ─── Main ────────────────────────────────────────────────────────────

def main():
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("🤖 Bot চালু হয়েছে...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
