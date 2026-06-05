import requests
import json
import os
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SEEN_FILE = "seen_quests.json"
SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "min_reward": 1,
    "non_usdt_notify": False
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            s = json.load(f)
            for k, v in DEFAULT_SETTINGS.items():
                if k not in s:
                    s[k] = v
            return s
    return DEFAULT_SETTINGS.copy()

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    return []

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    r = requests.post(url, json=data)
    return r.status_code == 200

def get_headers(referer="https://taskon.xyz/"):
    import time
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://taskon.xyz",
        "Referer": referer,
        "Authorization": os.environ.get("TASKON_AUTH", ""),
        "X-Api-Key": os.environ.get("TASKON_API_KEY", "07053609F54C953681896C28"),
        "Fp-Id": os.environ.get("TASKON_FP_ID", "1206899621"),
        "Timestamp": str(int(time.time() * 1000)),
        "Session-Id": os.environ.get("TASKON_SESSION_ID", ""),
        "Sec-Ch-Ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
    }

def fetch_all_campaigns():
    url = "https://api.taskon.xyz/v1/getCampaignList"
    all_campaigns = {}
    PAGE_SIZE = 40

    # Featured
    try:
        r = requests.post(url, headers=get_headers(), json={
            "options": {"feature_campaigns": True, "campaign_type": "Campaign"},
            "page": {"page_no": 0, "size": 50}
        }, timeout=15)
        if r.status_code == 200:
            campaigns = r.json().get("result", {}).get("data", [])
            for c in campaigns:
                cid = str(c.get("id", ""))
                if cid:
                    all_campaigns[cid] = c
            print(f"Featured: {len(campaigns)}")
    except Exception as e:
        print(f"Featured error: {e}")

    # All pages
    page_no = 0
    while True:
        payload = {
            "page": {"page_no": page_no, "size": PAGE_SIZE},
            "options": {
                "name_like": "", "campaign_status": "OnGoing",
                "user_campaign_status": "NotCompleted", "reward_type": ["All"],
                "network": [], "project_category": ["All"],
                "campaign_type": "Campaign", "order_by": "Comprehensive",
                "include_private": False, "end_day": 0,
                "contain_task_type": ["AllOffChainOpt", "AllOnChainOpt"],
                "is_global_search": False, "social_campaign": False, "end_tab_sort": False
            }
        }
        try:
            r = requests.post(url, headers=get_headers(), json=payload, timeout=15)
            if r.status_code != 200:
                break
            campaigns = r.json().get("result", {}).get("data", [])
            if not campaigns:
                break
            new_c = 0
            for c in campaigns:
                cid = str(c.get("id", ""))
                if cid and cid not in all_campaigns:
                    all_campaigns[cid] = c
                    new_c += 1
            print(f"Page {page_no}: {len(campaigns)} | নতুন: {new_c} | মোট: {len(all_campaigns)}")
            if len(campaigns) < PAGE_SIZE:
                break
            page_no += 1
        except Exception as e:
            print(f"Page {page_no} error: {e}")
            break

    return list(all_campaigns.values())

def get_campaign_info(campaign_id):
    url = "https://api.taskon.xyz/v1/getCampaignInfo"
    try:
        r = requests.post(url, headers=get_headers(f"https://taskon.xyz/quest/{campaign_id}"),
                         json={"campaign_id": campaign_id}, timeout=15)
        if r.status_code == 200:
            return r.json().get("result", {})
    except Exception as e:
        print(f"Detail error: {e}")
    return None

def parse_reward(detail):
    total_usdt = 0
    per_amount = 0
    max_winners = 0
    reward_symbol = "USDT"
    reward_type_label = "🎲 Winner Draw"
    has_non_usdt = False
    non_usdt_info = []

    for wr in detail.get("winner_rewards", []):
        draw_type = str(wr.get("automatically_winner_draw_type", "")).upper()
        winner_draw_type = str(wr.get("winner_draw_type", "")).upper()
        if "FCFS" in draw_type or "FCFS" in winner_draw_type:
            reward_type_label = "🎯 FCFS (First Come First Serve)"

        for layer in wr.get("winner_layer_rewards", []):
            max_winners += layer.get("max_winners", 0)
            for reward in layer.get("rewards", []):
                params = reward.get("reward_params", {})
                symbol = params.get("token_name", "")
                if symbol == "USDT":
                    total_usdt += float(params.get("total_amount", 0) or 0)
                    per_amount = float(params.get("per_amount", 0) or 0)
                else:
                    if symbol:
                        has_non_usdt = True
                        amt = params.get("total_amount") or params.get("per_amount") or "?"
                        non_usdt_info.append(f"{amt} {symbol}")

    return total_usdt, per_amount, max_winners, reward_symbol, reward_type_label, has_non_usdt, non_usdt_info

def parse_tasks(detail):
    tasks = []
    for task in detail.get("tasks", [])[:5]:
        name = task.get("custom_name") or task.get("name") or task.get("template_id") or ""
        if name:
            tasks.append(f"• {name}")
    return tasks

def format_message(detail, total_usdt, per_amount, max_winners, reward_symbol,
                   reward_type_label, has_non_usdt, non_usdt_info):
    name = detail.get("name", "Unknown")
    campaign_id = detail.get("id", "")
    link = f"https://taskon.xyz/quest/{campaign_id}"
    from_supported = detail.get("from_supported_country", True)
    tasks = parse_tasks(detail)
    task_text = "\n".join(tasks) if tasks else "• বিস্তারিত লিংকে দেখুন"
    country_text = "" if from_supported else "\n⚠️ <b>আপনার দেশে সাপোর্টেড নয়!</b>"
    now = datetime.now().strftime("%I:%M %p")

    if total_usdt > 0:
        reward_line = f"💰 <b>Total Pool:</b> {total_usdt} USDT\n👤 <b>প্রতিজন:</b> {per_amount} USDT"
    else:
        reward_line = f"🪙 <b>Reward:</b> {', '.join(non_usdt_info) if non_usdt_info else 'লিংকে দেখুন'}"

    return (
        f"🚨 <b>নতুন কোয়েস্ট পাওয়া গেছে!</b>\n\n"
        f"📋 <b>নাম:</b> {name}\n"
        f"{reward_type_label}\n"
        f"{reward_line}\n"
        f"👥 <b>মোট স্লট:</b> {max_winners} জন\n\n"
        f"📌 <b>রিকোয়ারমেন্ট:</b>\n{task_text}{country_text}\n\n"
        f"🔗 <b>লিংক:</b> {link}\n\n"
        f"⏰ পাওয়া গেছে: {now}"
    )

def main():
    print(f"[{datetime.now()}] TaskOn quests চেক করছি...")

    settings = load_settings()
    MIN_REWARD = settings["min_reward"]
    NON_USDT_NOTIFY = settings["non_usdt_notify"]
    print(f"সেটিংস: Min=${MIN_REWARD} | Non-USDT={'চালু' if NON_USDT_NOTIFY else 'বন্ধ'}")

    seen = load_seen()
    campaigns = fetch_all_campaigns()
    print(f"মোট campaigns: {len(campaigns)}")

    new_count = 0
    for c in campaigns:
        campaign_id = str(c.get("id", ""))
        if not campaign_id or campaign_id in seen:
            continue

        quick_usdt = sum(
            float(wr.get("reward_amount", 0) or 0)
            for wr in c.get("winner_rewards", [])
            if wr.get("reward_symbol") == "USDT"
        )
        quick_has_non_usdt = any(
            wr.get("reward_symbol") and wr.get("reward_symbol") != "USDT"
            for wr in c.get("winner_rewards", [])
        )

        if quick_usdt < MIN_REWARD and not (NON_USDT_NOTIFY and quick_has_non_usdt and quick_usdt == 0):
            print(f"Skip ({quick_usdt} USDT): {c.get('name', '')[:40]}")
            continue

        print(f"চেক করছি: {c.get('name', '')[:40]} | ~{quick_usdt} USDT")
        detail = get_campaign_info(int(campaign_id))
        if not detail:
            continue

        total_usdt, per_amount, max_winners, reward_symbol, reward_type_label, has_non_usdt, non_usdt_info = parse_reward(detail)

        should_send = (total_usdt >= MIN_REWARD) or (NON_USDT_NOTIFY and has_non_usdt and total_usdt == 0)
        if not should_send:
            continue

        msg = format_message(detail, total_usdt, per_amount, max_winners,
                             reward_symbol, reward_type_label, has_non_usdt, non_usdt_info)
        print(f"✅ পাঠাচ্ছি: {detail.get('name', '')[:40]}")

        if send_telegram(msg):
            print("📨 পাঠানো হয়েছে!")
            seen.append(campaign_id)
            new_count += 1
        else:
            print("❌ ব্যর্থ")

    save_seen(seen)
    print(f"শেষ। {new_count}টি নতুন notification পাঠানো হয়েছে।")

if __name__ == "__main__":
    main()
        
