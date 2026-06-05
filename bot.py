import os
import random
import time
import json
import hashlib
from datetime import datetime, timezone
from collections import defaultdict

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from groq import Groq

# =========================
# CONFIG
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

# =========================
# STORAGE
# =========================
games = {}
leaderboard = defaultdict(lambda: defaultdict(int))
global_leaderboard = defaultdict(int)

last_msg_time = defaultdict(float)

USED_FILE = "used_words.json"

try:
    with open(USED_FILE, "r") as f:
        used_words = set(json.load(f))
except:
    used_words = set()


def save_used():
    with open(USED_FILE, "w") as f:
        json.dump(list(used_words), f)

# =========================
# WORDLIST FALLBACK
# =========================
WORDLIST = {
    4: ["game","word","play","time","code","love","work","mind","test","fire","dark","blue","home"],
    5: ["apple","crane","stone","brain","table","chair","plant","smile","grape","plane"],
    6: ["stream","planet","mirror","object","socket","school","mobile","system","laptop","python"]
}

# =========================
# AI WORD GENERATOR
# =========================
def ai_generate_word(length):
    try:
        prompt = f"""
Generate ONE valid English word of exactly {length} letters.
Rules:
- real dictionary word
- no names
- no slang
Return only the word.
"""

        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8
        )

        word = res.choices[0].message.content.strip().lower()
        word = "".join([c for c in word if c.isalpha()])

        return word
    except:
        return random.choice(WORDLIST[length])


def get_unique_ai_word(length):
    for _ in range(20):
        word = ai_generate_word(length)

        if len(word) != length:
            continue

        if word in used_words:
            continue

        used_words.add(word)
        save_used()
        return word

    return random.choice(WORDLIST[length])

# =========================
# DAILY WORD
# =========================
def get_daily_word(length):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    seed = int(hashlib.md5(today.encode()).hexdigest(), 16)
    random.seed(seed)
    return random.choice(WORDLIST[length])

# =========================
# GAME ENGINE
# =========================
def new_game(chat_id, length):
    games[chat_id] = {
        "word": get_unique_ai_word(length),
        "length": length,
        "tries": 0,
        "active": True,
        "history": [],
        "guessed": set(),
        "daily": True
    }


def fancy(word):
    return " ".join(word.upper())


def check_guess(secret, guess):
    secret = list(secret)
    guess = list(guess)

    result = ["🟥"] * len(guess)
    used_s = [False] * len(secret)
    used_g = [False] * len(guess)

    for i in range(len(guess)):
        if guess[i] == secret[i]:
            result[i] = "🟩"
            used_s[i] = True
            used_g[i] = True

    for i in range(len(guess)):
        if used_g[i]:
            continue
        for j in range(len(secret)):
            if not used_s[j] and guess[i] == secret[j]:
                result[i] = "🟨"
                used_s[j] = True
                break

    return " ".join(result)


def build_history(game):
    text = f"{game['length']}-letter · {len(game['history'])}/30\n\n"
    for g, h in game["history"]:
        text += f"{h}  {fancy(g)}\n"
    return text

# =========================
# COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 WordSeek PRO Bot\n\n"
        "/new4 /new5 /new6 - Start Game\n"
        "/leaderboard - Group\n"
        "/global - Global ranking\n"
        "/skip - Skip word\n"
        "/help - Help"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🟩 correct\n🟨 wrong position\n🟥 not in word\n\n"
        "⚡ invalid words don't count\n🔥 AI words no repeat forever"
    )


async def new4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_game(update.effective_chat.id, 4)
    await update.message.reply_text("🎮 4-letter game started!")

async def new5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_game(update.effective_chat.id, 5)
    await update.message.reply_text("🎮 5-letter game started!")

async def new6(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_game(update.effective_chat.id, 6)
    await update.message.reply_text("🎮 6-letter game started!")

# =========================
# SKIP
# =========================
async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id

    if chat not in games:
        return

    word = games[chat]["word"]
    games[chat]["active"] = False

    await update.message.reply_text(f"⏭ Word was: {word}")

# =========================
# LEADERBOARD
# =========================
async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    data = leaderboard[chat]

    if not data:
        await update.message.reply_text("No scores yet!")
        return

    text = "🏆 GROUP LEADERBOARD\n\n"

    for i, (u, s) in enumerate(sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]):
        text += f"{i+1}. {u} - {s}\n"

    await update.message.reply_text(text)


async def global_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not global_leaderboard:
        await update.message.reply_text("No global data!")
        return

    text = "🌍 GLOBAL LEADERBOARD\n\n"

    for i, (u, s) in enumerate(sorted(global_leaderboard.items(), key=lambda x: x[1], reverse=True)[:10]):
        text += f"{i+1}. {u} - {s}\n"

    await update.message.reply_text(text)

# =========================
# MESSAGE HANDLER
# =========================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat = update.effective_chat.id
    user = update.effective_user.id

    if not msg.text:
        return

    text = msg.text.lower().strip()

    if chat not in games or not games[chat]["active"]:
        return

    game = games[chat]

    if len(text) != game["length"]:
        return

    # anti spam
    now = time.time()
    if now - last_msg_time[user] < 1.2:
        return
    last_msg_time[user] = now

    # valid check (NO COUNT IF INVALID)
    if text not in WORDLIST[game["length"]]:
        await msg.reply_text("❌ Invalid word")
        return

    if text in game["guessed"]:
        await msg.reply_text("❌ Already used")
        return

    game["guessed"].add(text)
    game["tries"] += 1

    hint = check_guess(game["word"], text)
    game["history"].append((text, hint))

    # WIN
    if text == game["word"]:
        game["active"] = False

        score = max(0, 30 - game["tries"])

        leaderboard[chat][user] += score
        global_leaderboard[user] += score

        await msg.reply_text(
            build_history(game) +
            f"\n🎉 WIN!\n🏆 +{score}\nWord: {game['word']}"
        )
        return

    await msg.reply_text(build_history(game))

# =========================
# MAIN
# =========================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("new4", new4))
    app.add_handler(CommandHandler("new5", new5))
    app.add_handler(CommandHandler("new6", new6))
    app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
    app.add_handler(CommandHandler("global", global_cmd))
    app.add_handler(CommandHandler("skip", skip))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("🚀 PRO BOT RUNNING")
    app.run_polling()


if __name__ == "__main__":
    main()
