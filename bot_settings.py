import os
import json
import logging
import base64
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID        = os.environ.get("CHAT_ID")
GITHUB_TOKEN   = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO    = os.environ.get("GITHUB_REPO")

MINI_APP_URL  = "https://ariful5.github.io/Tkon-notifier/"
SETTINGS_FILE = "settings.json"
DEFAULT_SETTINGS = {
    "min_reward": 1,
    "non_usdt_notify": False
}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ─── GitHub helpers ───────────────────────────────────────────────────

def get_github_file():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{SETTINGS_FILE}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content), data["sha"]
    return None, None

def load_settings():
    if GITHUB_TOKEN and GITHUB_REPO:
        s, _ = get_github_file()
        if s:
            for k, v in DEFAULT_SETTINGS.items():
                if k not in s: s[k] = v
            return s
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE) as f:
            s = json.load(f)
            for k, v in DEFAULT_SETTINGS.items():
                if k not in s: s[k] = v
            return s
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)
    if GITHUB_TOKEN and GITHUB_REPO:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{SETTINGS_FILE}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        content = base64.b64encode(json.dumps(settings, indent=2).encode()).decode()
        _, sha = get_github_file()
        payload = {
            "message": f"settings: reward={settings['min_reward']}, non_usdt={settings['non_usdt_notify']}",
            "content": content,
        }
        if sha: payload["sha"] = sha
        r = requests.put(url, headers=headers, json=payload)
        if r.status_code in [200, 201]:
            logging.info("✅ GitHub এ settings save হয়েছে")
        else:
            logging.error(f"❌ GitHub save failed: {r.status_code}")

def is_authorized(update: Update) -> bool:
    return str(update.effective_chat.id) == str(CHAT_ID)

# ─── একটাই বাটন ──────────────────────────────────────────────────────

def mini_app_button():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "⚙️ সেটিংস খুলুন",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )
    ]])

# ─── /start ──────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    s = load_settings()
    non_usdt = "✅ চালু" if s["non_usdt_notify"] else "❌ বন্ধ"

    await update.message.reply_text(
        "👋 <b>TaskOn Quest Notifier Bot</b>\n\n"
        "এই বট TaskOn প্ল্যাটফর্মের নতুন কোয়েস্ট আসলে\n"
        "আপনাকে <b>Telegram এ সাথে সাথে notify</b> করে।\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎛️ <b>Mini App এ যা করতে পারবেন:</b>\n\n"
        "💵 <b>সর্বনিম্ন রিওয়ার্ড সেট করুন</b>\n"
        "   └ যেমন $5 সেট করলে, $5 এর কম\n"
        "      রিওয়ার্ডের কোয়েস্টে notify আসবে না\n\n"
        "➕ <b>+/- বাটন দিয়ে বাড়ান/কমান</b>\n"
        "   └ এক এক করে adjust করুন\n\n"
        "⚡ <b>Quick preset বাটন</b>\n"
        "   └ $1 / $5 / $10 / $50 এক চাপে সেট\n\n"
        "✏️ <b>Custom amount লিখুন</b>\n"
        "   └ $200, $1000 — যেকোনো পরিমাণ\n\n"
        "🪙 <b>Non-USDT Notify টগল</b>\n"
        "   └ ETH, BNB ইত্যাদি অন্য টোকেনের\n"
        "      কোয়েস্টেও notify পেতে চালু করুন\n\n"
        "📊 <b>বর্তমান সেটিংস দেখুন</b>\n"
        "   └ আপনার active filter একনজরে\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>এখন চালু আছে:</b>\n"
        f"   💵 সর্বনিম্ন: <code>${s['min_reward']} USDT</code>\n"
        f"   🪙 Non-USDT: {non_usdt}\n\n"
        "👇 নিচের বাটন চাপুন সেটিংস করতে",
        parse_mode="HTML",
        reply_markup=mini_app_button()
    )

# ─── /settings ───────────────────────────────────────────────────────

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    s = load_settings()
    non_usdt = "✅ চালু" if s["non_usdt_notify"] else "❌ বন্ধ"
    await update.message.reply_text(
        "⚙️ <b>সেটিংস</b>\n\n"
        f"💵 সর্বনিম্ন রিওয়ার্ড: <code>${s['min_reward']} USDT</code>\n"
        f"🪙 Non-USDT Notify: {non_usdt}\n\n"
        "👇 Mini App খুলে সেটিংস পরিবর্তন করুন",
        parse_mode="HTML",
        reply_markup=mini_app_button()
    )

# ─── /status ─────────────────────────────────────────────────────────

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    s = load_settings()
    non_usdt = "✅ চালু" if s["non_usdt_notify"] else "❌ বন্ধ"
    filter_text = f"${s['min_reward']}+ {'সব টোকেন' if s['non_usdt_notify'] else 'শুধু USDT'}"
    await update.message.reply_text(
        "📊 <b>বর্তমান সেটিংস</b>\n\n"
        f"💵 সর্বনিম্ন রিওয়ার্ড: <code>${s['min_reward']} USDT</code>\n"
        f"🪙 Non-USDT Notify: {non_usdt}\n"
        f"📌 ফিল্টার: <code>{filter_text}</code>",
        parse_mode="HTML",
        reply_markup=mini_app_button()
    )

# ─── Mini App থেকে data আসলে ─────────────────────────────────────────

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return

    if update.message.web_app_data:
        try:
            data = json.loads(update.message.web_app_data.data)
            s = load_settings()
            if "min_reward"    in data: s["min_reward"]    = float(data["min_reward"])
            if "non_usdt_notify" in data: s["non_usdt_notify"] = bool(data["non_usdt_notify"])
            save_settings(s)
            non_usdt = "✅ চালু" if s["non_usdt_notify"] else "❌ বন্ধ"
            await update.message.reply_text(
                "✅ <b>সেটিং সেভ হয়েছে!</b>\n\n"
                f"💵 সর্বনিম্ন রিওয়ার্ড: <code>${s['min_reward']} USDT</code>\n"
                f"🪙 Non-USDT Notify: {non_usdt}",
                parse_mode="HTML",
                reply_markup=mini_app_button()
            )
        except Exception as e:
            logging.error(f"Mini App data error: {e}")

# ─── BotFather commands ───────────────────────────────────────────────

async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start",    "🤖 Bot শুরু করুন"),
        BotCommand("settings", "⚙️ সেটিংস খুলুন"),
        BotCommand("status",   "📊 বর্তমান সেটিংস"),
    ])

# ─── Main ────────────────────────────────────────────────────────────

import asyncio

def main():
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("start",    start_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("status",   status_command))
    app.add_handler(MessageHandler(
        filters.StatusUpdate.WEB_APP_DATA | (filters.TEXT & ~filters.COMMAND),
        message_handler
    ))

    print("🤖 Bot চালু হয়েছে...")

    async def run_with_timeout():
        async with app:
            await app.start()
            await app.updater.start_polling()
            print("⏳ ৯ মিনিট পর বন্ধ হবে...")
            await asyncio.sleep(9 * 60)
            await app.updater.stop()
            await app.stop()

    asyncio.run(run_with_timeout())

if __name__ == "__main__":
    main()
    
