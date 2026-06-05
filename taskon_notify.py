import requests
import json
import os
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SEEN_FILE = "seen_quests.json"
MIN_REWARD = 400

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

def get_campaign_list():
    url = "https://api.taskon.xyz/v1/getCampaignList"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": "https://taskon.xyz",
        "Referer": "https://taskon.xyz/quest"
    }
    payload = {
        "page": {"page_no": 0, "size": 40},
        "options": {
            "name_like": "",
            "campaign_status": "OnGoing",
            "user_campaign_status": "All",
            "reward_type": ["All"]
        }
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data.get("result", {}).get("data", [])
    except Exception as e:
        print(f"List error: {e}")
    return []

def get_campaign_info(campaign_id):
    url = "https://api.taskon.xyz/v1/getCampaignInfo"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Origin": "https://taskon.xyz",
        "Referer": f"https://taskon.xyz/quest/{campaign_id}"
    }
    try:
        r = requests.post(url, headers=headers, json={"campaign_id": campaign_id}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data.get("result", {})
    except Exception as e:
        print(f"Detail error: {e}")
    return None

def parse_reward(detail):
    """Extract total USDT reward, per winner amount, max winners, and type."""
    total_usdt = 0
    per_amount = 0
    max_winners = 0
    reward_symbol = "USDT"
    reward_type_label = "🎲 Winner Draw"

    winner_rewards = detail.get("winner_rewards", [])
    for wr in winner_rewards:
        # Check FCFS or Draw
        draw_type = wr.get("automatically_winner_draw_type", "")
        winner_draw_type = wr.get("winner_draw_type", "")
        if "FCFS" in str(draw_type).upper() or "FCFS" in str(winner_draw_type).upper():
            reward_type_label = "🎯 FCFS (First Come First Serve)"

        layers = wr.get("winner_layer_rewards", [])
        for layer in layers:
            max_winners += layer.get("max_winners", 0)
            rewards = layer.get("rewards", [])
            for reward in rewards:
                params = reward.get("reward_params", {})
                total = float(params.get("total_amount", 0) or 0)
                per = float(params.get("per_amount", 0) or 0)
                symbol = params.get("token_name", "USDT")
                if symbol == "USDT":
                    total_usdt += total
                    per_amount = per
                    reward_symbol = symbol

    return total_usdt, per_amount, max_winners, reward_symbol, reward_type_label

def parse_tasks(detail):
    tasks = []
    for task in detail.get("tasks", [])[:5]:
        name = task.get("custom_name") or task.get("name") or task.get("template_id") or ""
        if name:
            tasks.append(f"• {name}")
    return tasks

def format_message(detail, total_usdt, per_amount, max_winners, reward_symbol, reward_type_label):
    name = detail.get("name", "Unknown")
    campaign_id = detail.get("id", "")
    link = f"https://taskon.xyz/quest/{campaign_id}"
    from_supported = detail.get("from_supported_country", True)
    tasks = parse_tasks(detail)

    task_text = "\n".join(tasks) if tasks else "• বিস্তারিত লিংকে দেখুন"
    country_text = "" if from_supported else "\n⚠️ <b>আপনার দেশে সাপোর্টেড নয়!</b>"
    now = datetime.now().strftime("%I:%M %p")

    return f"""🚨 <b>নতুন কোয়েস্ট পাওয়া গেছে!</b>

📋 <b>নাম:</b> {name}
{reward_type_label}
💰 <b>Total Pool:</b> {total_usdt} {reward_symbol}
👤 <b>প্রতিজন:</b> {per_amount} {reward_symbol}
👥 <b>মোট স্লট:</b> {max_winners} জন

📌 <b>রিকোয়ারমেন্ট:</b>
{task_text}{country_text}

🔗 <b>লিংক:</b> {link}

⏰ পাওয়া গেছে: {now}"""

def main():
    print(f"[{datetime.now()}] Checking TaskOn quests...")
    seen = load_seen()

    campaigns = get_campaign_list()
    print(f"Total campaigns found: {len(campaigns)}")

    new_count = 0
    for c in campaigns:
        campaign_id = str(c.get("id", ""))
        if not campaign_id:
            continue

        if campaign_id in seen:
            continue

        # Quick filter: check winner_rewards_simple for USDT amount
        simple = c.get("winner_rewards", [])
        quick_usdt = 0
        for wr in simple:
            if wr.get("reward_symbol") == "USDT":
                quick_usdt += float(wr.get("reward_amount", 0) or 0)

        if quick_usdt < MIN_REWARD:
            print(f"Skip (low reward {quick_usdt} USDT): {c.get('name', '')[:40]}")
            continue

        # Get full detail
        print(f"Checking detail for: {c.get('name', '')[:40]}")
        detail = get_campaign_info(campaign_id)
        if not detail:
            continue

        total_usdt, per_amount, max_winners, reward_symbol, reward_type_label = parse_reward(detail)

        if total_usdt < MIN_REWARD:
            print(f"Skip after detail check ({total_usdt} USDT): {detail.get('name', '')[:40]}")
            continue

        print(f"✅ New quest: {detail.get('name', '')[:40]} | {total_usdt} USDT")
        msg = format_message(detail, total_usdt, per_amount, max_winners, reward_symbol, reward_type_label)

        if send_telegram(msg):
            print(f"📨 Notification sent!")
            seen.append(campaign_id)
            new_count += 1
        else:
            print(f"❌ Failed to send notification")

    save_seen(seen)
    print(f"Done. {new_count} new notifications sent.")

if __name__ == "__main__":
    main()
    
