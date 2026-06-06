import os
import json
import logging
import base64
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")  # format: "username/repo"
SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "min_reward": 1,
    "non_usdt_notify": False
}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ─── GitHub Settings helpers ─────────────────────────────────────────

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

# ─── Settings menu builder ───────────────────────────────────────────

def build_settings_menu(s):
    reward = s["min_reward"]
    non_usdt = s["non_usdt_notify"]

    # রিওয়ার্ড ডিসপ্লে
    reward_display = f"${reward} USDT" if reward == int(reward) else f"${reward} USDT"

    # Non-USDT সুইচ লেবেল
    switch_label = "🟢 চালু আছে  ●━━━━  বন্ধ করুন" if non_usdt else "🔴 বন্ধ আছে  ━━━━●  চালু করুন"

    keyboard = [
        # ── রিওয়ার্ড সেকশন হেডার ──
        [InlineKeyboardButton("💵  সর্বনিম্ন রিওয়ার্ড", callback_data="noop")],

        # বর্তমান ভ্যালু + +/- কন্ট্রোল
        [
            InlineKeyboardButton("➖", callback_data="reward_dec"),
            InlineKeyboardButton(f"✦  {reward_display}  ✦", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data="reward_inc"),
        ],

        # প্রিসেট চিপ বাটন
        [
            InlineKeyboardButton("$1"  if reward != 1   else "✓ $1",   callback_data="reward_set_1"),
            InlineKeyboardButton("$5"  if reward != 5   else "✓ $5",   callback_data="reward_set_5"),
            InlineKeyboardButton("$10" if reward != 10  else "✓ $10",  callback_data="reward_set_10"),
            InlineKeyboardButton("$50" if reward != 50  else "✓ $50",  callback_data="reward_set_50"),
            InlineKeyboardButton("✏️",                                   callback_data="reward_custom"),
        ],

        # ── ডিভাইডার ──
        [InlineKeyboardButton("┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄", callback_data="noop")],

        # ── Non-USDT সেকশন ──
        [InlineKeyboardButton("🪙  Non-USDT কোয়েস্ট নোটিফিকেশন", callback_data="noop")],
        [InlineKeyboardButton(switch_label, callback_data="toggle_non_usdt")],

        # ── ডিভাইডার ──
        [InlineKeyboardButton("┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄", callback_data="noop")],

        # ── নিচের বাটন ──
        [
            InlineKeyboardButton("📊  স্ট্যাটাস দেখুন", callback_data="show_status"),
            InlineKeyboardButton("❓  সাহায্য",          callback_data="show_help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

# ─── /start command ──────────────────────────────────────────────────

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
        "💵 <b>সর্বনিম্ন রিওয়ার্ড:</b> ➖/➕ চাপুন অথবা প্রিসেট বেছে নিন\n"
        "   ✏️ চাপলে যেকোনো কাস্টম পরিমাণ লিখতে পারবেন\n\n"
        "🪙 <b>Non-USDT Notify:</b> USDT ছাড়া অন্য টোকেনের কোয়েস্টে নোটিফিকেশন\n\n"
        "নিচের বাটন চাপুন 👇",
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
        "🔹 <b>➖ / ➕ বাটন:</b>\n"
        "   এক এক করে কমানো বা বাড়ানো যাবে।\n\n"
        "🔹 <b>✏️ কাস্টম বাটন:</b>\n"
        "   চাপলে নিজে লিখে দিতে পারবেন (যেমন: 200, 1000, 2500)।\n\n"
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

    # ── রিওয়ার্ড ➕/➖ ──
    elif data == "reward_inc":
        s["min_reward"] = round(s["min_reward"] + 1, 2)
        save_settings(s)
        await query.edit_message_reply_markup(build_settings_menu(s))

    elif data == "reward_dec":
        s["min_reward"] = round(max(1, s["min_reward"] - 1), 2)
        save_settings(s)
        await query.edit_message_reply_markup(build_settings_menu(s))

    # ── প্রিসেট বাটন ──
    elif data.startswith("reward_set_"):
        preset = float(data.replace("reward_set_", ""))
        s["min_reward"] = preset
        save_settings(s)
        await query.edit_message_reply_markup(build_settings_menu(s))

    # ── কাস্টম ইনপুট ──
    elif data == "reward_custom":
        await query.edit_message_text(
            f"✏️ <b>কাস্টম রিওয়ার্ড সেট করুন</b>\n\n"
            f"📌 বর্তমান সেটিং: <b>${s['min_reward']} USDT</b>\n\n"
            f"নতুন পরিমাণ লিখে পাঠান:\n"
            f"(যেমন: <code>200</code> বা <code>1000</code> বা <code>2500</code>)\n\n"
            f"⚠️ শুধু সংখ্যা লিখুন, কোনো চিহ্ন নয়",
            parse_mode="HTML"
        )
        context.user_data["waiting_for"] = "min_reward"

    # ── Non-USDT টগল ──
    elif data == "toggle_non_usdt":
        s["non_usdt_notify"] = not s["non_usdt_notify"]
        save_settings(s)
        await query.edit_message_reply_markup(build_settings_menu(s))

    elif data == "show_help":
        await query.edit_message_text(
            "❓ <b>সাহায্য</b>\n\n"
            "🔹 <b>➖ / ➕ বাটন:</b> এক এক করে কমানো/বাড়ানো\n"
            "🔹 <b>✏️ কাস্টম:</b> নিজে লিখুন (200, 1000, 2500...)\n"
            "🔹 <b>$1/$5/$10/$50:</b> এক চাপেই সেট\n\n"
            "🔹 <b>Non-USDT Notify:</b>\n"
            "   USDT ছাড়া অন্য টোকেন (ETH, BNB ইত্যাদি)\n"
            "   এর কোয়েস্টেও notification পেতে চালু রাখুন।\n\n"
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

# ─── Message handler ──────────────────────────────────────────────────

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    if context.user_data.get("waiting_for") == "min_reward":
        text = update.message.text.strip()
        try:
            value = float(text)
            if value <= 0:
                raise ValueError
            s = load_settings()
            s["min_reward"] = value
            save_settings(s)
            context.user_data["waiting_for"] = None

            # সেভ করে সাথে সাথে নতুন মেনু দেখাবে
            await update.message.reply_text(
                f"✅ <b>সেটিং সেভ হয়েছে!</b>\n\n"
                f"💵 সর্বনিম্ন রিওয়ার্ড: <b>${value} USDT</b>\n\n"
                f"এখন থেকে ${value} বা এর বেশি USDT এর কোয়েস্টে notification পাবেন।",
                parse_mode="HTML",
                reply_markup=build_settings_menu(s)
            )
        except ValueError:
            await update.message.reply_text(
                "❌ <b>ভুল ইনপুট!</b> শুধু সংখ্যা লিখুন।\n"
                "যেমন: <code>200</code> বা <code>1000</code>",
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

import asyncio

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
    
