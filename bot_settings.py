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

# ✅ আপনার GitHub Pages URL এখানে দিন
MINI_APP_URL   = "https://ariful5.github.io/Tkon-notifier/"

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
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content), data["sha"]
    return None, None

def load_settings():
    if GITHUB_TOKEN and GITHUB_REPO:
        settings, sha = get_github_file()
        if settings:
            for k, v in DEFAULT_SETTINGS.items():
                if k not in settings:
                    settings[k] = v
            return settings
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
    if GITHUB_TOKEN and GITHUB_REPO:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{SETTINGS_FILE}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        content = base64.b64encode(
            json.dumps(settings, indent=2).encode("utf-8")
        ).decode("utf-8")
        _, sha = get_github_file()
        payload = {
            "message": f"Update settings: min_reward={settings['min_reward']}, non_usdt={settings['non_usdt_notify']}",
            "content": content,
        }
        if sha:
            payload["sha"] = sha
        response = requests.put(url, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            logging.info("✅ GitHub এ settings save হয়েছে")
        else:
            logging.error(f"❌ GitHub save failed: {response.status_code} - {response.text}")

def is_authorized(update: Update) -> bool:
    return str(update.effective_chat.id) == str(CHAT_ID)

# ─── Settings menu (Telegram buttons) ────────────────────────────────

def build_settings_menu(s):
    reward   = s["min_reward"]
    non_usdt = s["non_usdt_notify"]

    def preset_label(v):
        return f"✅ ${int(v) if v == int(v) else v}" if reward == v else f"${int(v) if v == int(v) else v}"

    if non_usdt:
        switch = "꩜ চালু আছে ●━━━━━━━━━━━ বন্ধ করুন"
    else:
        switch = "꩜ বন্ধ আছে ━━━━━━━━━━━● চালু করুন"

    keyboard = [
        # ── Mini App বাটন (সবার উপরে) ──
        [InlineKeyboardButton(
            "🎛️ Mini App এ খুলুন (সুন্দর UI)",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )],
        [InlineKeyboardButton(
            "━━━━━ 💵 সর্বনিম্ন রিওয়ার্ড ━━━━━",
            callback_data="noop"
        )],
        [
            InlineKeyboardButton(" ➖ ", callback_data="reward_dec"),
            InlineKeyboardButton(f"💰 ${reward} USDT", callback_data="noop"),
            InlineKeyboardButton(" ➕ ", callback_data="reward_inc"),
        ],
        [
            InlineKeyboardButton(preset_label(1),  callback_data="reward_set_1"),
            InlineKeyboardButton(preset_label(5),  callback_data="reward_set_5"),
            InlineKeyboardButton(preset_label(10), callback_data="reward_set_10"),
            InlineKeyboardButton(preset_label(50), callback_data="reward_set_50"),
            InlineKeyboardButton("✏️ কাস্টম",      callback_data="reward_custom"),
        ],
        [InlineKeyboardButton(
            "━━━━ 🪙 Non-USDT Notify ━━━━",
            callback_data="noop"
        )],
        [InlineKeyboardButton(switch, callback_data="toggle_non_usdt")],
        [InlineKeyboardButton(
            "━━━━━━━━━━━━━━━━━━━━━━━",
            callback_data="noop"
        )],
        [
            InlineKeyboardButton("📊 স্ট্যাটাস দেখুন", callback_data="show_status"),
            InlineKeyboardButton("❓ সাহায্য",         callback_data="show_help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def settings_text(s):
    reward   = s["min_reward"]
    non_usdt = s["non_usdt_notify"]
    usdt_bar = "🟩🟩🟩🟩🟩" if non_usdt else "🟥🟥🟥🟥🟥"
    return (
        "╔═══════════════════════╗\n"
        "║ ⚙️ <b>সেটিংস মেনু</b> ║\n"
        "╚═══════════════════════╝\n\n"
        f"💵 <b>সর্বনিম্ন রিওয়ার্ড:</b> <code>${reward} USDT</code>\n"
        f" └ এর কম হলে notification আসবে না\n\n"
        f"🪙 <b>Non-USDT Notify:</b> {usdt_bar}\n"
        f" └ {'✅ চালু — অন্য টোকেনেও নোটিফাই করবে' if non_usdt else '❌ বন্ধ — শুধু USDT কোয়েস্টে নোটিফাই'}\n\n"
        "👇 নিচের বাটন চাপুন অথবা 🎛️ Mini App খুলুন"
    )

# ─── Commands ────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    await update.message.reply_text(
        "╔═══════════════════════╗\n"
        "║ 👋 <b>TaskOn Notifier Bot</b> ║\n"
        "╚═══════════════════════╝\n\n"
        "📌 <b>কমান্ড লিস্ট:</b>\n\n"
        " ⚙️ /settings → সেটিংস মেনু\n"
        " 📊 /status   → বর্তমান সেটিংস\n"
        " ❓ /help     → সাহায্য\n\n"
        "👇 <b>/settings</b> লিখুন শুরু করতে",
        parse_mode="HTML"
    )

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    s = load_settings()
    await update.message.reply_text(
        settings_text(s),
        parse_mode="HTML",
        reply_markup=build_settings_menu(s)
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    s = load_settings()
    non_usdt_status = "✅ চালু" if s["non_usdt_notify"] else "❌ বন্ধ"
    await update.message.reply_text(
        "╔══════════════════════╗\n"
        "║ 📊 <b>বর্তমান সেটিংস</b> ║\n"
        "╚══════════════════════╝\n\n"
        f"💵 <b>সর্বনিম্ন রিওয়ার্ড:</b> <code>${s['min_reward']} USDT</code>\n"
        f" └ এর কম হলে notification আসবে না\n\n"
        f"🪙 <b>Non-USDT Notify:</b> {non_usdt_status}\n"
        f" └ {'USDT ছাড়া অন্য টোকেনেও নোটিফাই করবে' if s['non_usdt_notify'] else 'শুধু USDT কোয়েস্টে নোটিফাই করবে'}",
        parse_mode="HTML"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    await update.message.reply_text(
        "╔══════════════════════╗\n"
        "║ ❓ <b>সাহায্য</b> ║\n"
        "╚══════════════════════╝\n\n"
        "🔹 <b>➖ / ➕ বাটন:</b>\n"
        " এক এক করে কমানো বা বাড়ানো\n\n"
        "🔹 <b>$1 / $5 / $10 / $50:</b>\n"
        " এক চাপেই সেট হয়ে যাবে\n\n"
        "🔹 <b>✏️ কাস্টম বাটন:</b>\n"
        " যেকোনো পরিমাণ নিজে লিখুন\n\n"
        "🔹 <b>Non-USDT Notify:</b>\n"
        " ETH, BNB ইত্যাদি টোকেনের\n"
        " কোয়েস্টেও notification পেতে চালু করুন\n\n"
        "🔹 <b>🎛️ Mini App:</b>\n"
        " সুন্দর UI তে settings করতে\n\n"
        "⚙️ মেনু খুলতে: /settings",
        parse_mode="HTML"
    )

# ─── Callbacks ────────────────────────────────────────────────────────

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_authorized(update): return
    data = query.data
    s = load_settings()

    if data == "noop":
        return
    elif data == "reward_inc":
        s["min_reward"] = round(s["min_reward"] + 1, 2)
        save_settings(s)
        await query.edit_message_text(settings_text(s), parse_mode="HTML", reply_markup=build_settings_menu(s))
    elif data == "reward_dec":
        s["min_reward"] = round(max(1, s["min_reward"] - 1), 2)
        save_settings(s)
        await query.edit_message_text(settings_text(s), parse_mode="HTML", reply_markup=build_settings_menu(s))
    elif data.startswith("reward_set_"):
        preset = float(data.replace("reward_set_", ""))
        s["min_reward"] = preset
        save_settings(s)
        await query.edit_message_text(settings_text(s), parse_mode="HTML", reply_markup=build_settings_menu(s))
    elif data == "reward_custom":
        await query.edit_message_text(
            "╔══════════════════════╗\n"
            "║ ✏️ <b>কাস্টম রিওয়ার্ড</b> ║\n"
            "╚══════════════════════╝\n\n"
            f"📌 বর্তমান: <code>${s['min_reward']} USDT</code>\n\n"
            "নতুন পরিমাণ লিখে পাঠান:\n"
            "<code>200</code> বা <code>1000</code> বা <code>2500</code>\n\n"
            "⚠️ শুধু সংখ্যা, কোনো চিহ্ন নয়",
            parse_mode="HTML"
        )
        context.user_data["waiting_for"] = "min_reward"
    elif data == "toggle_non_usdt":
        s["non_usdt_notify"] = not s["non_usdt_notify"]
        save_settings(s)
        await query.edit_message_text(settings_text(s), parse_mode="HTML", reply_markup=build_settings_menu(s))
    elif data == "show_status":
        non_usdt_status = "✅ চালু" if s["non_usdt_notify"] else "❌ বন্ধ"
        await query.edit_message_text(
            "╔══════════════════════╗\n"
            "║ 📊 <b>বর্তমান সেটিংস</b> ║\n"
            "╚══════════════════════╝\n\n"
            f"💵 <b>সর্বনিম্ন রিওয়ার্ড:</b> <code>${s['min_reward']} USDT</code>\n"
            f" └ এর কম হলে notification আসবে না\n\n"
            f"🪙 <b>Non-USDT Notify:</b> {non_usdt_status}\n"
            f" └ {'USDT ছাড়া অন্য টোকেনেও নোটিফাই করবে' if s['non_usdt_notify'] else 'শুধু USDT কোয়েস্টে নোটিফাই করবে'}\n\n"
            "⬅️ মেনুতে ফিরতে /settings",
            parse_mode="HTML"
        )
    elif data == "show_help":
        await query.edit_message_text(
            "╔══════════════════════╗\n"
            "║ ❓ <b>সাহায্য</b> ║\n"
            "╚══════════════════════╝\n\n"
            "🔹 <b>➖ / ➕:</b> এক এক করে কমানো/বাড়ানো\n"
            "🔹 <b>✏️ কাস্টম:</b> নিজে লিখুন (200, 1000...)\n"
            "🔹 <b>প্রিসেট:</b> $1/$5/$10/$50 এক চাপে সেট\n"
            "🔹 <b>Non-USDT:</b> অন্য টোকেনের কোয়েস্টেও notify\n"
            "🔹 <b>🎛️ Mini App:</b> সুন্দর UI তে settings করুন\n\n"
            "⬅️ মেনুতে ফিরতে /settings",
            parse_mode="HTML"
        )

# ─── Mini App data handler ────────────────────────────────────────────

async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mini App থেকে settings পাঠালে এখানে আসবে"""
    if not is_authorized(update): return
    try:
        data = json.loads(update.message.web_app_data.data)
        s = load_settings()
        if "min_reward" in data:
            s["min_reward"] = float(data["min_reward"])
        if "non_usdt_notify" in data:
            s["non_usdt_notify"] = bool(data["non_usdt_notify"])
        save_settings(s)
        await update.message.reply_text(
            "╔══════════════════════╗\n"
            "║ ✅ <b>Mini App থেকে সেভ হয়েছে!</b> ║\n"
            "╚══════════════════════╝\n\n"
            f"💵 সর্বনিম্ন রিওয়ার্ড: <code>${s['min_reward']} USDT</code>\n"
            f"🪙 Non-USDT Notify: {'✅ চালু' if s['non_usdt_notify'] else '❌ বন্ধ'}",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Mini App data error: {e}")
        await update.message.reply_text("❌ ডেটা পেতে সমস্যা হয়েছে।")

# ─── Message handler ──────────────────────────────────────────────────

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return

    # Mini App data
    if update.message.web_app_data:
        await web_app_data_handler(update, context)
        return

    if context.user_data.get("waiting_for") == "min_reward":
        text = update.message.text.strip()
        try:
            value = float(text)
            if value <= 0: raise ValueError
            s = load_settings()
            s["min_reward"] = value
            save_settings(s)
            context.user_data["waiting_for"] = None
            await update.message.reply_text(
                "╔══════════════════════╗\n"
                "║ ✅ <b>সেটিং সেভ হয়েছে!</b> ║\n"
                "╚══════════════════════╝\n\n"
                f"💵 সর্বনিম্ন রিওয়ার্ড: <code>${value} USDT</code>\n\n"
                f"এখন থেকে ${value} বা বেশি USDT\n"
                "এর কোয়েস্টে notification পাবেন।",
                parse_mode="HTML",
                reply_markup=build_settings_menu(s)
            )
        except ValueError:
            await update.message.reply_text(
                "❌ <b>ভুল ইনপুট!</b>\n"
                "শুধু সংখ্যা লিখুন।\n"
                "যেমন: <code>200</code> বা <code>1000</code>",
                parse_mode="HTML"
            )

# ─── BotFather setup ──────────────────────────────────────────────────

async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start",    "🤖 Bot শুরু করুন"),
        BotCommand("settings", "⚙️ সেটিংস মেনু খুলুন"),
        BotCommand("status",   "📊 বর্তমান সেটিংস দেখুন"),
        BotCommand("help",     "❓ সাহায্য দেখুন"),
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
    app.add_handler(CommandHandler("help",     help_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, message_handler))

    print("🤖 Bot চালু হয়েছে...")

    async def run_with_timeout():
        async with app:
            await app.start()
            await app.updater.start_polling()
            print("⏳ ৯ মিনিট পর বন্ধ হবে...")
            await asyncio.sleep(9 * 60)
            print("⏰ টাইমআউট! Bot বন্ধ হচ্ছে...")
            await app.updater.stop()
            await app.stop()

    asyncio.run(run_with_timeout())

if __name__ == "__main__":
    main()
        
