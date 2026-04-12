"""
manga_tracker.py – 追蹤 manhuagui.com 指定漫畫更新，有新章節時透過 LINE 和 Telegram 推播通知
"""
import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

WATCHLIST = [
    "葬送的芙莉莲",
    "陰陽眼見子",
    "无职转生",
    "關於我轉生後成為史萊姆的那件事",
    "超自然武裝噹噹噹",
    "轉生精靈精通魔法後踏上旅程，因為長壽而成為活生生的傳說",
    "XXXHOLiC•戾",
]

UPDATE_URL    = "https://tw.manhuagui.com/update/"
STATE_FILE    = "manga_state.json"
LINE_API_URL  = "https://api.line.me/v2/bot/message/push"

LINE_TOKEN       = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_USER_ID     = os.environ["LINE_USER_ID"]
TELEGRAM_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def fetch_updates():
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    resp = requests.get(UPDATE_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    updates = {}
    current_date = ""
    for tag in soup.select("h5, ul.latest-list li"):
        if tag.name == "h5":
            current_date = tag.get_text(strip=True)[:10]
        elif tag.name == "li":
            a_tag = tag.find("a")
            if not a_tag:
                continue
            title = a_tag.get("title", "").strip()
            url = "https://tw.manhuagui.com" + a_tag.get("href", "")
            chapter_tag = tag.find("p")
            chapter = chapter_tag.get_text(strip=True) if chapter_tag else ""
            if title:
                updates[title] = {"chapter": chapter, "url": url, "date": current_date}
    if not updates:
        for li in soup.select("li"):
            a = li.find("a", title=True)
            if not a:
                continue
            title = a["title"].strip()
            url = "https://tw.manhuagui.com" + a.get("href", "")
            chapter = li.get_text(strip=True).replace(title, "").strip()
            if title:
                updates[title] = {"chapter": chapter, "url": url, "date": ""}
    print(f"[爬蟲] 本次共抓到 {len(updates)} 部漫畫更新")
    return updates


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"[狀態] 已更新 {STATE_FILE}")


def find_new_updates(updates, state):
    new_items = []
    for manga in WATCHLIST:
        if manga not in updates:
            continue
        info = updates[manga]
        last_chapter = state.get(manga, {}).get("chapter", "")
        if info["chapter"] != last_chapter:
            new_items.append({
                "title": manga,
                "chapter": info["chapter"],
                "url": info["url"],
                "date": info["date"],
            })
    return new_items


def send_line(message):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}",
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message}],
    }
    resp = requests.post(LINE_API_URL, headers=headers, json=payload)
    if resp.status_code == 200:
        print("LINE 推播成功！")
    else:
        print(f"LINE 推播失敗：{resp.status_code} {resp.text}")


def send_telegram(message):
    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for chunk in [message[i:i+4000] for i in range(0, len(message), 4000)]:
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": chunk}
        resp = requests.post(api_url, json=payload)
        if resp.status_code == 200:
            print("Telegram 推播成功！")
        else:
            print(f"Telegram 推播失敗：{resp.status_code} {resp.text}")


if __name__ == "__main__":
    state = load_state()
    updates = fetch_updates()
    new_items = find_new_updates(updates, state)

    if not new_items:
        print("沒有新章節更新")
    else:
        lines = ["📚 漫畫更新通知\n"]
        for item in new_items:
            lines.append(f"📖 {item['title']}")
            lines.append(f"{item['chapter']}")
            lines.append(f"{item['url']}\n")
            state[item["title"]] = {
                "chapter": item["chapter"],
                "url": item["url"],
                "date": item["date"],
            }
        message = "\n".join(lines).strip()
        print(message)
        send_line(message)
        send_telegram(message)
        save_state(state)
