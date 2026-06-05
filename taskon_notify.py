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

def get_headers(referer="https://taskon.xyz/quest"):
    return {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://taskon.xyz",
        "Referer": referer,
        "X-App-Version": "2.9.21",
        "Save-Data": "on",
        "Sec-Ch-Ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?1",
        "Sec-Ch-Ua-Platform": '"Android"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
    }

def get_campaign_list():
    url = "https://api.taskon.xyz/v1/getCampaignList"
    all_campaigns = {}

    payloads = [
        # Featured campaigns (pinned top 3)
        {
            "options": {"feature_campaigns": True, "campaign_type": "Campaign"},
            "page": {"page_no": 0, "size": 50}
        },
        # All quests (Token Rewards tab)
        {
            "page": {"page_no": 0, "size": 40},
            "options": {
                "name_like": "",
                "campaign_status": "OnGoing",
                "user_campaign_status": "All",
                "reward_type": ["All"]
            }
        }
    ]

    for payload in payloads:
        try:
            r = requests.post(url, headers=get_headers(), json=payload, timeout=15)
            print(f"List status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                result = data.get("result", {})
                campaigns = []
                if isinstance(result, dict):
                    campaigns = result.get("data", [])
                elif isinstance(result, list):
                    campaigns = result
                for c in campaigns:
                    cid = str(c.get("id", ""))
                    if cid:
                        all_campaigns[cid] = c
                print(f"Running total: {len(all_campaigns)} unique campaigns")
        except Exception as e:
            print(f"List error: {e}")

    print(f"List response preview: {str(list(all_campaigns.values())[:1])[:300]}")
    return list(all_campaigns.values())

def get_campaign_info(campaign_id):
    url = "https://api.taskon.xyz/v1/getCampaignInfo"
    try:
        r = requests.post(url, headers=get_headers(f"https://taskon.xyz/quest/{campaign_id}"),
                         json={"campaign_id": campaign_id}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data.get("result", {})
    except Exception as e:
        print(f"Detail error: {e}")
    return None

def parse_reward(detail):
    total_usdt = 0
    per_amount = 0
    max_winners = 0
    reward_symbol = "USDT"
    reward_type_label = "🎲 Winner Draw"

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
                    reward_symbol = "USDT"

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
    print(f"Total campaigns: {len(campaigns)}")

    new_count = 0
    for c in campaigns:
        campaign_id = str(c.get("id", ""))
        if not campaign_id or campaign_id in seen:
            continue

        # Quick USDT filter from list data
        quick_usdt = sum(
            float(wr.get("reward_amount", 0) or 0)
            for wr in c.get("winner_rewards", [])
            if wr.get("reward_symbol") == "USDT"
        )

        if quick_usdt < MIN_REWARD:
            print(f"Skip ({quick_usdt} USDT): {c.get('name', '')[:40]}")
            continue

        print(f"Checking: {c.get('name', '')[:40]} | ~{quick_usdt} USDT")
        detail = get_campaign_info(int(campaign_id))
        if not detail:
            continue

        total_usdt, per_amount, max_winners, reward_symbol, reward_type_label = parse_reward(detail)

        if total_usdt < MIN_REWARD:
            continue

        msg = format_message(detail, total_usdt, per_amount, max_winners, reward_symbol, reward_type_label)
        print(f"✅ Sending: {detail.get('name', '')[:40]} | {total_usdt} USDT")

        if send_telegram(msg):
            print("📨 Sent!")
            seen.append(campaign_id)
            new_count += 1
        else:
            print("❌ Failed")

    save_seen(seen)
    print(f"Done. {new_count} new notifications sent.")

if __name__ == "__main__":
    main()
    
