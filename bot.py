#!/usr/bin/env python3
import os, time, random, logging, requests, feedparser, schedule, threading, json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

GEMINI_API_KEY      = os.environ.get("GEMINI_API_KEY", "")
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")
TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")
ADMIN_ID            = 6779799030

WEEKLY_SCHEDULE = {
    "Monday":    {"theme": "Tip of the Week",          "emoji": "💡", "post_time": "10:00", "prompt": "Write a funny but genuinely useful chess tip for beginners. Sound like a confused but enthusiastic friend. Include a real chess concept but add silly commentary. End with a question. Max 180 words."},
    "Tuesday":   {"theme": "Famous Game Breakdown",    "emoji": "🎯", "post_time": "11:00", "prompt": "Pick a famous chess game moment (Fischer, Carlsen, Kasparov) and explain it like a dramatic sports commentator. Educational but hilarious. Max 180 words."},
    "Wednesday": {"theme": "Mind-Blowing Chess Fact",  "emoji": "🤯", "post_time": "10:00", "prompt": "Share a mind-blowing chess fact. React like you just discovered something shocking. Add funny comparisons to everyday life. Max 180 words."},
    "Thursday":  {"theme": "Opening of the Week",      "emoji": "♟️", "post_time": "11:00", "prompt": "Explain a chess opening (Sicilian, King's Gambit, etc.) as a dramatic movie plot. Funny and memorable. Include first 3 moves. Max 180 words."},
    "Friday":    {"theme": "Puzzle Challenge",         "emoji": "🧩", "post_time": "12:00", "prompt": "Create a fun chess puzzle challenge. Describe a position in words and ask followers to guess the best move. Make it dramatic. Beginner-friendly. Max 180 words."},
    "Saturday":  {"theme": "Chess Humor",              "emoji": "😂", "post_time": "13:00", "prompt": "Write a funny chess post players relate to — blundering, playing fast, being overconfident. Feel like a personal story. Max 180 words."},
    "Sunday":    {"theme": "Resource Recommendation",  "emoji": "🛠️", "post_time": "10:00", "prompt": "Recommend a chess tool or website like an excited friend who discovered something amazing. Mention specific benefits. Not salesy. Max 180 words."},
}
DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
CHESS_RSS_FEEDS = ["https://www.chess.com/news/rss","https://en.chessbase.com/rss/news","https://www.reddit.com/r/chess.rss"]

def fetch_chess_news():
    for url in CHESS_RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                e = feed.entries[0]
                return f"{e.get('title','')}. {e.get('summary','')[:300]}"
        except: pass
    return ""

def fetch_chess_photo():
    try:
        r = requests.get("https://api.unsplash.com/photos/random",
            params={"query": random.choice(["chess board","chess pieces","chess game","chess tournament"]), "orientation":"landscape","content_filter":"high"},
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}, timeout=15)
        r.raise_for_status()
        return r.json()["urls"]["regular"]
    except: return None

def generate_post(theme, prompt, news=""):
    system = ("You are a funny, slightly chaotic chess enthusiast on Telegram. "
              "Genuinely informative but hilariously written, casual English, dramatic flair, "
              "feels human-written, natural emojis. NEVER sound corporate or AI-generated. "
              "Occasionally add self-corrections like 'wait, I mean...' to seem human. "
              "Do NOT add hashtags or links.")
    full = prompt + (f"\n\nReference this chess news optionally (don't copy): {news[:300]}" if news else "")
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}",
            json={"contents":[{"parts":[{"text":f"{system}\n\n{full}"}]}],"generationConfig":{"temperature":0.95,"maxOutputTokens":350}},
            timeout=30)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        logging.error(f"Gemini failed: {e}")
        return get_fallback(theme)

def get_fallback(theme):
    return {"Tip of the Week":"♟️ Chess tip: Don't move the same piece twice in the opening. Unless you enjoy losing. Some people do. No judgment.",
            "Famous Game Breakdown":"🎯 Bobby Fischer once said chess is life. He was right. Terrifyingly right.",
            "Mind-Blowing Chess Fact":"🤯 More possible chess games exist than atoms in the universe. Let that sink in while you blunder your queen.",
            "Opening of the Week":"♟️ The Sicilian Defense: Named after Sicily, dangerous like the mafia, and just as hard to understand.",
            "Puzzle Challenge":"🧩 White to move and win in 2. Think carefully. Or don't. Either way we're having fun.",
            "Chess Humor":"😂 That moment you spend 20 minutes planning a brilliant attack and your opponent takes a different piece. Every. Single. Time.",
            "Resource Recommendation":"🛠️ Chess.com is genuinely amazing. Free lessons, puzzles, games. No excuses not to improve!"
            }.get(theme, "♟️ Chess is beautiful. Even when losing. Especially when losing.")

def build_post(day):
    c = WEEKLY_SCHEDULE[day]
    news = fetch_chess_news()
    content = generate_post(c["theme"], c["prompt"], news)
    photo = fetch_chess_photo()
    text = f"{c['emoji']} *{c['theme']}*\n\n{content}\n\n#Chess #ChessTips #LearnChess #ChessCommunity #ChessChaosDaily"
    return {"text": text, "photo": photo}

def post_to_telegram(day):
    logging.info(f"Posting for {day}...")
    post = build_post(day)
    try:
        if post["photo"]:
            r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                data={"chat_id":TELEGRAM_CHANNEL_ID,"photo":post["photo"],"caption":post["text"],"parse_mode":"Markdown"}, timeout=30)
        else:
            r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                data={"chat_id":TELEGRAM_CHANNEL_ID,"text":post["text"],"parse_mode":"Markdown"}, timeout=30)
        r.raise_for_status()
        logging.info(f"✅ Posted for {day}!")
        return True
    except Exception as e:
        logging.error(f"❌ Post failed: {e}")
        return False

def send_msg(chat_id, text, kb=None):
    data = {"chat_id":chat_id,"text":text,"parse_mode":"Markdown"}
    if kb: data["reply_markup"] = json.dumps(kb)
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data=data, timeout=15)
    except Exception as e: logging.error(f"send_msg failed: {e}")

def cmd_start(cid):
    send_msg(cid,
        "♟️ *Chess Chaos Daily Bot*\n━━━━━━━━━━━━━━━━━━━\n\n"
        "👋 Welcome Admin!\n\n📋 *Commands:*\n\n"
        "📤 `/post today` — Post abhi karo\n"
        "📤 `/post Monday` — Specific din ka post\n"
        "📅 `/schedule` — Schedule dekho\n"
        "🔄 `/scheduleupdate` — Schedule update karo\n"
        "📊 `/status` — Bot status\n\n━━━━━━━━━━━━━━━━━━━",
        kb={"inline_keyboard":[[{"text":"📤 Post Today","callback_data":"post_today"},{"text":"📅 Schedule","callback_data":"show_schedule"}],[{"text":"📊 Status","callback_data":"show_status"}]]})

def cmd_post(cid, args):
    day = args.strip().capitalize()
    if day.lower() == "today": day = datetime.now().strftime("%A")
    if day not in WEEKLY_SCHEDULE:
        send_msg(cid, f"❌ Invalid: `{day}`\nUse: Monday...Sunday or `today`"); return
    send_msg(cid, f"⏳ Posting for *{day}*...")
    ok = post_to_telegram(day)
    send_msg(cid, f"✅ *{day}* ka post bhej diya!" if ok else "❌ Post failed! Logs check karo.")

def cmd_schedule(cid):
    txt = "📅 *Current Schedule (IST):*\n━━━━━━━━━━━━━━━\n\n"
    for day, c in WEEKLY_SCHEDULE.items():
        h,m = map(int, c["post_time"].split(":"))
        ih = (h+5)%24; im = m+30
        if im>=60: im-=60; ih=(ih+1)%24
        txt += f"{c['emoji']} *{day}* — {c['theme']} — `{ih:02d}:{im:02d} IST`\n"
    send_msg(cid, txt+"\n━━━━━━━━━━━━━━━")

def cmd_status(cid):
    send_msg(cid,
        f"📊 *Bot Status*\n━━━━━━━━━━━━━━━\n\n"
        f"🟢 *Bot:* Running\n"
        f"📅 *Today:* {datetime.now().strftime('%A, %d %b %Y')}\n"
        f"🕐 *UTC:* {datetime.now().strftime('%H:%M')}\n"
        f"📡 *Channel:* {TELEGRAM_CHANNEL_ID}\n\n━━━━━━━━━━━━━━━")

def cmd_scheduleupdate(cid):
    send_msg(cid,
        "🔄 *Schedule Update*\n\nNaya schedule bhejo:\n\n"
        "`Monday 10:00`\n`Tuesday 11:00`\n`Wednesday 10:00`\n"
        "`Thursday 11:00`\n`Friday 12:00`\n`Saturday 13:00`\n`Sunday 10:00`\n\n"
        "⚠️ *Time UTC mein likho!*\nIST 3:30 PM = UTC 10:00")

def apply_schedule_update(cid, text):
    errors = []; new = {}
    for line in text.strip().split("\n"):
        p = line.strip().split()
        if len(p)!=2: errors.append(f"❌ Invalid: `{line}`"); continue
        day,t = p[0].capitalize(),p[1]
        if day not in WEEKLY_SCHEDULE: errors.append(f"❌ Unknown: `{day}`"); continue
        try:
            h,m = map(int,t.split(":")); assert 0<=h<=23 and 0<=m<=59
            new[day] = f"{h:02d}:{m:02d}"
        except: errors.append(f"❌ Bad time: `{t}`")
    if errors: send_msg(cid,"\n".join(errors)); return
    for d,t in new.items(): WEEKLY_SCHEDULE[d]["post_time"]=t
    schedule.clear(); setup_schedule()
    result="\n".join(f"{WEEKLY_SCHEDULE[d]['emoji']} *{d}* — `{WEEKLY_SCHEDULE[d]['post_time']} UTC`" for d in DAYS)
    send_msg(cid, f"✅ *Schedule updated!*\n\n{result}")

last_uid = 0
waiting  = set()

def poll_updates():
    global last_uid
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
                params={"offset":last_uid+1,"timeout":30}, timeout=40)
            r.raise_for_status()
            for upd in r.json().get("result",[]):
                last_uid = upd["update_id"]
                if "callback_query" in upd:
                    cb=upd["callback_query"]; cid=cb["message"]["chat"]["id"]; uid=cb["from"]["id"]; cbd=cb["data"]
                    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery",data={"callback_query_id":cb["id"]},timeout=10)
                    if uid!=ADMIN_ID: send_msg(cid,"🚫 Admin only!"); continue
                    if cbd=="post_today": cmd_post(cid,"today")
                    elif cbd=="show_schedule": cmd_schedule(cid)
                    elif cbd=="show_status": cmd_status(cid)
                    continue
                if "message" not in upd: continue
                msg=upd["message"]; cid=msg["chat"]["id"]; uid=msg["from"]["id"]; txt=msg.get("text","").strip()
                if not txt: continue
                if uid!=ADMIN_ID: send_msg(cid,"🚫 *Sorry, this bot is for admin only!*"); continue
                if uid in waiting and not txt.startswith("/"):
                    waiting.discard(uid); apply_schedule_update(cid,txt); continue
                if txt=="/start": cmd_start(cid)
                elif txt.startswith("/post"):
                    a=txt[5:].strip()
                    if not a: send_msg(cid,"Usage: `/post today` or `/post Monday`")
                    else: cmd_post(cid,a)
                elif txt=="/schedule": cmd_schedule(cid)
                elif txt=="/scheduleupdate": waiting.add(uid); cmd_scheduleupdate(cid)
                elif txt=="/status": cmd_status(cid)
                else: send_msg(cid,"❓ Unknown command. Type /start to see all commands.")
        except Exception as e:
            logging.error(f"Poll error: {e}"); time.sleep(5)

class HH(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"Chess Bot alive!")
    def log_message(self,*a): pass

def run_health():
    HTTPServer(("0.0.0.0",int(os.environ.get("PORT",8080))),HH).serve_forever()

def setup_schedule():
    dm={"Monday":schedule.every().monday,"Tuesday":schedule.every().tuesday,"Wednesday":schedule.every().wednesday,
        "Thursday":schedule.every().thursday,"Friday":schedule.every().friday,"Saturday":schedule.every().saturday,"Sunday":schedule.every().sunday}
    for day,c in WEEKLY_SCHEDULE.items():
        dm[day].at(c["post_time"]).do(post_to_telegram,day=day)
        logging.info(f"Scheduled {day} {c['post_time']} — {c['theme']}")

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO,format="%(asctime)s — %(levelname)s — %(message)s",handlers=[logging.StreamHandler()])
    import sys
    if len(sys.argv)>1 and sys.argv[1]=="test":
        day=sys.argv[2] if len(sys.argv)>2 else datetime.now().strftime("%A")
        post_to_telegram(day)
    else:
        logging.info("♟️ Chess Chaos Daily Bot Starting...")
        threading.Thread(target=run_health,daemon=True).start()
        threading.Thread(target=poll_updates,daemon=True).start()
        setup_schedule()
        logging.info("📅 Schedule active!")
        while True:
            schedule.run_pending(); time.sleep(30)