import requests
import json
import os
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SEEN_FILE = "seen_quests.json"
MIN_REWARD = 400  # Minimum reward pool in USDT

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

def get_quests():
    url = "https://taskon.xyz/api/quest/list"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://taskon.xyz/quest"
    }
    params = {
        "page": 1,
        "pageSize": 50,
        "status": "ongoing"
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"Error fetching quests: {e}")
    return None

def get_quest_detail(quest_id):
    url = f"https://taskon.xyz/api/quest/detail/{quest_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def parse_quest(quest):
    try:
        quest_id = str(quest.get("id", ""))
        name = quest.get("title", "Unknown")
        reward_pool = float(quest.get("rewardPool", 0) or 0)
        reward_per_winner = float(quest.get("rewardPerWinner", 0) or 0)
        total_winners = int(quest.get("winnerCount", 0) or 0)
        quest_type = quest.get("rewardType", "")  # FCFS or DRAW
        link = f"https://taskon.xyz/quest/{quest_id}"

        # Get tasks/requirements
        tasks = []
        task_list = quest.get("taskList", []) or []
        for task in task_list[:5]:
            task_name = task.get("title") or task.get("name") or ""
            if task_name:
                tasks.append(f"• {task_name}")

        # Country restrictions
        country_restrict = quest.get("countryBlacklist", []) or []
        restrict_note = ""
        if country_restrict:
            restrict_note = f"⚠️ সাপোর্টেড নয়: {', '.join(country_restrict[:5])}"

        return {
            "id": quest_id,
            "name": name,
            "reward_pool": reward_pool,
            "reward_per_winner": reward_per_winner,
            "total_winners": total_winners,
            "quest_type": quest_type,
            "link": link,
            "tasks": tasks,
            "restrict_note": restrict_note
        }
    except Exception as e:
        print(f"Parse error: {e}")
        return None

def format_message(q):
    reward_type_label = "🎯 FCFS" if "FCFS" in q["quest_type"].upper() else "🎲 Winner Draw"
    tasks_text = "\n".join(q["tasks"]) if q["tasks"] else "• বিস্তারিত লিংকে দেখুন"
    restrict_text = f"\n{q['restrict_note']}" if q["restrict_note"] else ""
    now = datetime.now().strftime("%I:%M %p")

    msg = f"""🚨 <b>নতুন কোয়েস্ট পাওয়া গেছে!</b>

📋 <b>নাম:</b> {q['name']}
{reward_type_label}
💰 <b>রিওয়ার্ড পুল:</b> {q['reward_pool']} USDT
👤 <b>প্রতিজন:</b> {q['reward_per_winner']} USDT
👥 <b>মোট স্লট:</b> {q['total_winners']} জন

📌 <b>রিকোয়ারমেন্ট:</b>
{tasks_text}{restrict_text}

🔗 <b>লিংক:</b> {q['link']}

⏰ পাওয়া গেছে: {now}"""
    return msg

def main():
    print(f"[{datetime.now()}] Checking TaskOn quests...")
    seen = load_seen()
    data = get_quests()

    if not data:
        print("Failed to fetch quests or no data returned.")
        # Try alternative approach
        alt_url = "https://taskon.xyz/api/campaign/list"
        try:
            r = requests.get(alt_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            print(f"Alt URL status: {r.status_code}")
            print(f"Alt response: {r.text[:500]}")
        except Exception as e:
            print(f"Alt error: {e}")
        return

    print(f"Raw response type: {type(data)}")
    print(f"Raw response preview: {str(data)[:500]}")

    quests = []
    if isinstance(data, list):
        quests = data
    elif isinstance(data, dict):
        quests = data.get("data", data.get("list", data.get("records", [])))

    print(f"Total quests found: {len(quests)}")
    new_count = 0

    for quest in quests:
        parsed = parse_quest(quest)
        if not parsed:
            continue

        if parsed["reward_pool"] < MIN_REWARD:
            continue

        if parsed["id"] in seen:
            continue

        print(f"New quest: {parsed['name']} | Pool: {parsed['reward_pool']} USDT")
        msg = format_message(parsed)
        if send_telegram(msg):
            print(f"✅ Notification sent for: {parsed['name']}")
            seen.append(parsed["id"])
            new_count += 1
        else:
            print(f"❌ Failed to send notification for: {parsed['name']}")

    save_seen(seen)
    print(f"Done. {new_count} new notifications sent.")

if __name__ == "__main__":
    main()
