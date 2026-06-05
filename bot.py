import os
import random
import time
from collections import defaultdict

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# =========================
# STATE
# =========================
games = {}
leaderboard = defaultdict(lambda: defaultdict(int))
global_leaderboard = defaultdict(int)
last_msg_time = defaultdict(float)

# =========================
# WORDLIST
# =========================
WORDLIST = {
    4: ["game","word","play","time","code","fire","love","work","mind","test","cool","fast","team","goal","ring"],
    5: ["apple","crane","stone","brain","table","chair","plant","smile","grape","plane","train","flame","water","earth"],
    6: ["stream","planet","mirror","object","socket","school","mobile","system","laptop","python","rocket","bridge","forest"]
}

WORDSET = {
    4: set(w.strip().lower() for w in WORDLIST[4]),
    5: set(w.strip().lower() for w in WORDLIST[5]),
    6: set(w.strip().lower() for w in WORDLIST[6]),
}

# =========================
# GAME ENGINE
# =========================
def new_game(chat_id, length):
    games[chat_id] = {
        "word": random.choice(WORDLIST[length]).lower(),
        "length": length,
        "tries": 0,
        "active": True,
        "history": [],
        "guessed": set()
    }

def fancy(word):
    return " ".join(word.upper())

def clean(text):
    return "".join(text.lower().split())

def check_guess(secret, guess):
    secret = list(secret)
    guess = list(guess)

    res = ["🟥"] * len(guess)
    used_s = [False] * len(secret)

    for i in range(len(guess)):
        if guess[i] == secret[i]:
            res[i] = "🟩"
            used_s[i] = True

    for i in range(len(guess)):
        if res[i] == "🟩":
            continue
        for j in range(len(secret)):
            if not used_s[j] and guess[i] == secret[j]:
                res[i] = "🟨"
                used_s[j] = True
                break

    return " ".join(res)

def build_history(game):
    txt = f"{game['length']}-letter · {len(game['history'])}/30\n\n"
    for g, h in game["history"]:
        txt += f"{h}  {fancy(g)}\n"
    return txt

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 WordSeek Bot Ready!\n\n"
        "/new4 /new5 /new6 - Start Game\n"
        "/help - Help\n"
        "/stats - Stats\n"
        "/leaderboard - Group\n"
        "/global - Global\n\n"
        "📢 @jp_network"
    )

# =========================
# HELP (FIXED QUOTE REPLY)
# =========================
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "▸ WordSeek Help\n\n"
        "🟩 Correct\n"
        "🟨 Wrong position\n"
        "🟥 Not in word\n\n"
        "/new4 /new5 /new6 - Start Game\n"
        "/leaderboard - Group\n"
        "/global - Global\n"
        "/help - Help me\n\n"
        "📢 Support Channel: @jp_network",
        reply_to_message_id=update.message.message_id
    )

# =========================
# STATS
# =========================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id
    chat = update.effective_chat.id

    user_score = leaderboard[chat].get(user, 0)
    global_score = global_leaderboard.get(user, 0)

    await update.message.reply_text(
        f"📊 Your Stats\n\n"
        f"🏆 Group: {user_score}\n"
        f"🌍 Global: {global_score}"
    )

# =========================
# BROADCAST (ADMIN ONLY)
# =========================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Not allowed")
        return

    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("Usage: /broadcast message")
        return

    # send to current chat
    await update.message.reply_text("📢 Broadcasting...")

    for chat_id in list(games.keys()):
        try:
            await context.bot.send_message(chat_id, f"📢 {msg}")
        except:
            pass

    await update.message.reply_text("✅ Broadcast done")

# =========================
# GAME START
# =========================
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
# MESSAGE HANDLER (FIXED 🔥)
# =========================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat = update.effective_chat.id
    user = update.effective_user.id

    if not msg.text:
        return

    text = clean(msg.text)

    if chat not in games or not games[chat]["active"]:
        return

    game = games[chat]

    if len(text) != game["length"]:
        return

    # anti spam
    now = time.time()
    if now - last_msg_time[user] < 1.0:
        return
    last_msg_time[user] = now

    # VALIDATION FIX 🔥
    if text not in WORDSET[game["length"]]:
        await msg.reply_text("❌ Invalid word")
        return

    if text in game["guessed"]:
        await msg.reply_text("❌ Already used")
        return

    game["guessed"].add(text)
    game["tries"] += 1

    hint = check_guess(game["word"], text)
    game["history"].append((text, hint))

    if text == game["word"]:
        game["active"] = False
        score = max(0, 30 - game["tries"])

        leaderboard[chat][user] += score
        global_leaderboard[user] += score

        await msg.reply_text(
            build_history(game) +
            f"\n🎉 CONGRATS!\n🏆 +{score} points\nWord: {game['word']}\n\n"
            "/new4 /new5 /new6"
        )
        return

    await msg.reply_text(build_history(game))

# =========================
# LEADERBOARD
# =========================
async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    data = leaderboard[chat]

    if not data:
        await update.message.reply_text("No scores")
        return

    text = "🏆 GROUP LEADERBOARD\n\n"
    for i, (u, s) in enumerate(sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]):
        text += f"{i+1}. {u} - {s}\n"

    await update.message.reply_text(text)

async def global_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not global_leaderboard:
        await update.message.reply_text("No global scores")
        return

    text = "🌍 GLOBAL LEADERBOARD\n\n"
    for i, (u, s) in enumerate(sorted(global_leaderboard.items(), key=lambda x: x[1], reverse=True)[:10]):
        text += f"{i+1}. {u} - {s}\n"

    await update.message.reply_text(text)

# =========================
# MAIN
# =========================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(CommandHandler("new4", new4))
    app.add_handler(CommandHandler("new5", new5))
    app.add_handler(CommandHandler("new6", new6))

    app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
    app.add_handler(CommandHandler("global", global_cmd))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("🚀 Bot Running Fixed Version")
    app.run_polling()

if __name__ == "__main__":
    main()
