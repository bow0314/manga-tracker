"""
manga_tracker.py - 追蹤 manhuagui.com 指定漫畫更新，有新章節時透過 LINE 推播通知
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
    "超自然武裝噹噠噹",
    "轉生精靈精通魔法後踏上旅程，因為長壽而成為活生生的傳說",
    "XXXHOLiC•戾",
]

UPDATE_URL   = "https://tw.manhuagui.com/update/"
STATE_FILE   = "manga_state.json"
LINE_API_URL = "https://api.line.me/v2/bot/message/broadcast"

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
            new_items.append({"title": manga, "chapter": info["chapter"], "url": info["url"], "date": info["date"]})
    return new_items

def send_line_notification(new_items):
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    if not token:
        print("[LINE] 未設定 LINE_CHANNEL_ACCESS_TOKEN，跳過推播")
        return
    bubbles = []
    for item in new_items:
        bubbles.append({
            "type": "bubble", "size": "kilo",
            "header": {"type": "box", "layout": "vertical",
                "contents": [{"type": "text", "text": "漫畫更新通知", "weight": "bold", "color": "#ffffff", "size": "sm"}],
                "backgroundColor": "#3D7EAA", "paddingAll": "10px"},
            "body": {"type": "box", "layout": "vertical", "contents": [
                {"type": "text", "text": item["title"], "weight": "bold", "size": "md", "wrap": True},
                {"type": "text", "text": item["chapter"], "size": "sm", "color": "#555555", "margin": "sm", "wrap": True},
                {"type": "text", "text": "date: " + item["date"], "size": "xs", "color": "#aaaaaa", "margin": "sm"}]},
            "footer": {"type": "box", "layout": "vertical",
                "contents": [{"type": "button", "style": "primary",
                    "action": {"type": "uri", "label": "立即閱讀", "uri": item["url"]},
                    "color": "#3D7EAA", "height": "sm"}]}
        })
    message = {"type": "flex", "altText": f"{len(new_items)} 部漫畫有新章節！",
                "contents": {"type": "carousel", "contents": bubbles[:12]}}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.post(LINE_API_URL, headers=headers,
                         data=json.dumps(message, ensure_ascii=False).encode("utf-8"), timeout=15)
    if resp.status_code == 200:
        print(f"[LINE] 推播成功！通知了 {len(new_items)} 部漫畫更新")
    else:
        print(f"[LINE] 推播失敗：{resp.status_code} {resp.text}")

def main():
    print(f"[開始] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 漫畫更新檢查")
    updates = fetch_updates()
    state = load_state()
    new_items = find_new_updates(updates, state)
    if not new_items:
        print("[結果] 追蹤清單中沒有新章節，靜默結束")
    else:
        print(f"[結果] 發現 {len(new_items)} 部有更新")
        send_line_notification(new_items)
        for item in new_items:
            state[item["title"]] = {"chapter": item["chapter"], "url": item["url"], "date": item["date"]}
        save_state(state)
    print("[完成] 執行結束")

if __name__ == "__main__":
    main()
