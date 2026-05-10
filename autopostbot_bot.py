#!/usr/bin/env python3
"""
♟️ Chess Chaos Daily — Auto Post Bot
- News from RSS feeds
- Photos from Unsplash
- Posts written by Gemini AI (funny English)
- Weekly schedule Mon-Sun
- Posts to Telegram Channel
"""

import os
import time
import random
import logging
import requests
import feedparser
import schedule
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ============================================================
#                     CONFIGURATION
# ============================================================

GEMINI_API_KEY      = os.environ.get("GEMINI_API_KEY", "")
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")
TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")

# ============================================================
#                     WEEKLY SCHEDULE
# ============================================================

WEEKLY_SCHEDULE = {
    "Monday": {
        "theme": "Tip of the Week",
        "emoji": "💡",
        "prompt": (
            "Write a funny but genuinely useful chess tip for beginners. "
            "Sound like a confused but enthusiastic friend explaining it. "
            "Include a real chess concept but add silly commentary. "
            "End with a question to engage readers. Max 180 words."
        ),
        "post_time": "10:00",
    },
    "Tuesday": {
        "theme": "Famous Game Breakdown",
        "emoji": "🎯",
        "prompt": (
            "Pick a famous chess game moment (Fischer, Carlsen, Kasparov) "
            "and explain it like a dramatic sports commentator. "
            "Keep it educational but hilarious. Max 180 words."
        ),
        "post_time": "11:00",
    },
    "Wednesday": {
        "theme": "Mind-Blowing Chess Fact",
        "emoji": "🤯",
        "prompt": (
            "Share a mind-blowing chess fact or statistic. "
            "React to it like you just discovered something shocking. "
            "Add funny comparisons to everyday life. Max 180 words."
        ),
        "post_time": "10:00",
    },
    "Thursday": {
        "theme": "Opening of the Week",
        "emoji": "♟️",
        "prompt": (
            "Explain a chess opening (Sicilian, King's Gambit, etc.) "
            "as if narrating a dramatic movie plot. "
            "Funny and memorable. Include first 3 moves. Max 180 words."
        ),
        "post_time": "11:00",
    },
    "Friday": {
        "theme": "Puzzle Challenge",
        "emoji": "🧩",
        "prompt": (
            "Create a fun chess puzzle challenge. Describe a position in words "
            "and ask followers to guess the best move. "
            "Make it sound life-or-death dramatic. Beginner-friendly. Max 180 words."
        ),
        "post_time": "12:00",
    },
    "Saturday": {
        "theme": "Chess Humor",
        "emoji": "😂",
        "prompt": (
            "Write a funny chess-related post players will relate to — "
            "blundering a piece, playing too fast, being overconfident. "
            "Feel like a personal story. Very relatable. Max 180 words."
        ),
        "post_time": "13:00",
    },
    "Sunday": {
        "theme": "Resource Recommendation",
        "emoji": "🛠️",
        "prompt": (
            "Recommend a chess learning tool or website like an excited friend "
            "who just discovered something amazing. "
            "Mention specific benefits. Not salesy. Max 180 words."
        ),
        "post_time": "10:00",
    },
}

# ============================================================
#                     RSS FEEDS
# ============================================================

CHESS_RSS_FEEDS = [
    "https://www.chess.com/news/rss",
    "https://en.chessbase.com/rss/news",
    "https://www.reddit.com/r/chess.rss",
]

# ============================================================
#                     FETCH NEWS
# ============================================================

def fetch_chess_news() -> str:
    for feed_url in CHESS_RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            if feed.entries:
                entry   = feed.entries[0]
                title   = entry.get("title", "")
                summary = entry.get("summary", "")[:300]
                logging.info(f"Fetched news: {title}")
                return f"{title}. {summary}"
        except Exception as e:
            logging.warning(f"RSS feed failed ({feed_url}): {e}")
    return ""

# ============================================================
#                     FETCH PHOTO
# ============================================================

def fetch_chess_photo():
    queries = ["chess board", "chess pieces", "chess game", "chess strategy", "chess tournament"]
    query   = random.choice(queries)
    try:
        resp = requests.get(
            "https://api.unsplash.com/photos/random",
            params={"query": query, "orientation": "landscape", "content_filter": "high"},
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        url  = data["urls"]["regular"]
        logging.info(f"Fetched photo ok")
        return url
    except Exception as e:
        logging.warning(f"Unsplash failed: {e}")
        return None

# ============================================================
#                     GENERATE POST (GEMINI)
# ============================================================

def generate_post(theme: str, prompt: str, news_context: str = "") -> str:
    system = (
        "You are a funny, slightly chaotic chess enthusiast running a Telegram channel. "
        "Your style: genuinely informative but hilariously written, casual English, "
        "dramatic flair, occasional funny tangents, feels human-written, "
        "uses emojis naturally. NEVER sound corporate or AI-generated. "
        "Occasionally add small self-corrections like 'wait, I mean...' to seem human. "
        "Do NOT add hashtags or links — those are added separately."
    )

    full_prompt = prompt
    if news_context:
        full_prompt += (
            f"\n\nOptionally reference this recent chess news for inspiration "
            f"(don't copy it): {news_context[:300]}"
        )

    payload = {
        "contents": [{"parts": [{"text": f"{system}\n\n{full_prompt}"}]}],
        "generationConfig": {"temperature": 0.95, "maxOutputTokens": 350},
    }

    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        logging.info(f"Gemini generated post for: {theme}")
        return text
    except Exception as e:
        logging.error(f"Gemini failed: {e}")
        return get_fallback_post(theme)

# ============================================================
#                     FALLBACK POSTS
# ============================================================

def get_fallback_post(theme: str) -> str:
    fallbacks = {
        "Tip of the Week":         "♟️ Chess tip: Don't move the same piece twice in the opening. Unless you enjoy losing. Some people do. No judgment.",
        "Famous Game Breakdown":   "🎯 Bobby Fischer once said chess is life. He was right. Terrifyingly right.",
        "Mind-Blowing Chess Fact": "🤯 More possible chess games exist than atoms in the observable universe. Let that sink in while you blunder your queen.",
        "Opening of the Week":     "♟️ The Sicilian Defense: Named after Sicily, dangerous like the mafia, and just as hard to understand at first.",
        "Puzzle Challenge":        "🧩 White to move and win in 2. Think carefully. Or don't. Either way we're having fun.",
        "Chess Humor":             "😂 That moment you spend 20 minutes planning a brilliant attack and your opponent takes a completely different piece. Every. Single. Time.",
        "Resource Recommendation": "🛠️ Chess.com is genuinely amazing for learning. Free lessons, puzzles, games. No excuses not to improve!",
    }
    return fallbacks.get(theme, "♟️ Chess is beautiful. Even when you're losing. Especially when you're losing.")

# ============================================================
#                     BUILD FULL POST
# ============================================================

def build_post(day: str) -> dict:
    config  = WEEKLY_SCHEDULE[day]
    theme   = config["theme"]
    emoji   = config["emoji"]

    news    = fetch_chess_news()
    content = generate_post(theme, config["prompt"], news)
    photo   = fetch_chess_photo()

    hashtags = "#Chess #ChessTips #LearnChess #ChessCommunity #ChessChaosDaily"

    full_text = f"{emoji} *{theme}*\n\n{content}\n\n{hashtags}"

    return {"text": full_text, "photo": photo}

# ============================================================
#                     POST TO TELEGRAM
# ============================================================

def post_to_telegram(day: str):
    logging.info(f"Posting for {day}...")
    post = build_post(day)

    try:
        if post["photo"]:
            url  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            data = {
                "chat_id":    TELEGRAM_CHANNEL_ID,
                "photo":      post["photo"],
                "caption":    post["text"],
                "parse_mode": "Markdown",
            }
        else:
            url  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                "chat_id":    TELEGRAM_CHANNEL_ID,
                "text":       post["text"],
                "parse_mode": "Markdown",
            }

        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        logging.info(f"✅ Posted successfully for {day}!")

    except Exception as e:
        logging.error(f"❌ Telegram post failed: {e}")

# ============================================================
#                     HEALTH CHECK SERVER
#              (Render requires open port)
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Chess Bot is alive!")

    def log_message(self, format, *args):
        pass

def run_health_server():
    port   = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logging.info(f"Health server on port {port}")
    server.serve_forever()

# ============================================================
#                     SCHEDULER SETUP
# ============================================================

def setup_schedule():
    day_map = {
        "Monday":    schedule.every().monday,
        "Tuesday":   schedule.every().tuesday,
        "Wednesday": schedule.every().wednesday,
        "Thursday":  schedule.every().thursday,
        "Friday":    schedule.every().friday,
        "Saturday":  schedule.every().saturday,
        "Sunday":    schedule.every().sunday,
    }
    for day, config in WEEKLY_SCHEDULE.items():
        day_map[day].at(config["post_time"]).do(post_to_telegram, day=day)
        logging.info(f"Scheduled {day} at {config['post_time']} — {config['theme']}")

# ============================================================
#                     MAIN
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s — %(levelname)s — %(message)s",
        handlers=[logging.StreamHandler()]
    )

    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        day = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%A")
        logging.info(f"Test mode — posting for {day}")
        post_to_telegram(day)

    else:
        logging.info("♟️ Chess Chaos Daily Bot Starting...")

        # Health server (background thread — keeps Render happy)
        t = threading.Thread(target=run_health_server, daemon=True)
        t.start()

        # Weekly schedule
        setup_schedule()
        logging.info("📅 Schedule active — waiting for post times...")

        while True:
            schedule.run_pending()
            time.sleep(30)
