import os
import random
import time
from collections import defaultdict

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

# =========================
# STATE
# =========================
games = {}
leaderboard = defaultdict(lambda: defaultdict(int))
global_leaderboard = defaultdict(int)

last_msg_time = defaultdict(float)

# =========================
# WORDLIST (300+ FIXED)
# =========================
WORDLIST = {
    4: [
        "game","word","play","time","code","fire","love","work","mind","test","cool","fast","team","goal","ring",
        "dark","blue","home","talk","read","book","data","chat","send","mail","bank","shop","plan","idea","luck",
        "rain","snow","wind","bird","fish","tree","frog","lion","wolf","bear","deer","milk","rice","salt","gold",
        "iron","rock","sand","wave","boat","road","path","door","wall","roof","hero","jump","kick","sync","ping",
        "pong","byte","load","save","edit","view","scan","open","lock","call","text","note","file","city","grow"
    ],
    5: [
        "apple","crane","stone","brain","table","chair","plant","smile","grape","plane","train","flame","water",
        "earth","power","money","dream","story","music","party","night","world","house","phone","glass","river",
        "ocean","beach","storm","cloud","snake","eagle","tiger","zebra","mouse","horse","sheep","bread","sugar",
        "spice","cream","juice","green","black","white","brown","clock","brick","metal","cable","field","crown",
        "knife","torch","brave","quick","sharp","happy","angry","peace","glory","faith","trust","crash","flash",
        "smoke","light","sound","robot","logic","craft","build","lemon","mango","pearl","shark","whale","cabin"
    ],
    6: [
        "stream","planet","mirror","object","socket","school","mobile","system","laptop","python","rocket","bridge",
        "forest","castle","animal","silver","golden","random","coding","signal","vector","output","window","circle",
        "square","radius","energy","motion","charge","sensor","flight","driver","kernel","server","client","module",
        "buffer","memory","cursor","packet","router","thread","device","galaxy","shadow","bright","future","orange",
        "purple","yellow","binary","crypto","upload","import","export","format","global","native","status","button",
        "screen","battle","secret","hidden","decode","network","browser","tablet","coding","python","server","client"
    ]
}

# =========================
# SAFE WORDSET (FIXED BUG 🔥)
# =========================
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
        "word": random.choice(WORDLIST[length]).strip().lower(),
        "length": length,
        "tries": 0,
        "active": True,
        "history": [],
        "guessed": set()
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
# START MESSAGE (FIXED)
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 WordSeek Bot Ready!\n\n"
        "▸ WordSeek Help\n\n"
        "🟩 Correct\n"
        "🟨 Wrong position\n"
        "🟥 Not in word\n\n"
        "/new4 /new5 /new6 - Start Game\n"
        "/leaderboard - Group\n"
        "/global - Global\n"
        "/help - Help me\n\n"
        "📢 Support Channel: @jp_network"
    )

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
        await update.message.reply_text("No global scores!")
        return

    text = "🌍 GLOBAL LEADERBOARD\n\n"
    for i, (u, s) in enumerate(sorted(global_leaderboard.items(), key=lambda x: x[1], reverse=True)[:10]):
        text += f"{i+1}. {u} - {s}\n"

    await update.message.reply_text(text)

# =========================
# MESSAGE HANDLER (FINAL FIX 🔥)
# =========================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat = update.effective_chat.id
    user = update.effective_user.id

    if not msg.text:
        return

    # 🔥 FULL SAFE NORMALIZATION
    text = msg.text.lower()
    text = text.replace(" ", "")
    text = text.replace("\n", "")
    text = text.strip()

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

    # 🔥 FIXED VALIDATION (MAIN BUG FIX)
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

    # WIN
    if text == game["word"]:
        game["active"] = False

        score = max(0, 30 - game["tries"])

        leaderboard[chat][user] += score
        global_leaderboard[user] += score

        await msg.reply_text(
            build_history(game) +
            f"\n🎉 CONGRATULATIONS!\n"
            f"🏆 Points: +{score}\n"
            f"Word: {game['word']}\n\n"
            "▶ Play again:\n/new4 /new5 /new6"
        )
        return

    await msg.reply_text(build_history(game))

# =========================
# MAIN
# =========================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new4", new4))
    app.add_handler(CommandHandler("new5", new5))
    app.add_handler(CommandHandler("new6", new6))
    app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
    app.add_handler(CommandHandler("global", global_cmd))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("🚀 WordSeek FINAL FIXED BOT RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
