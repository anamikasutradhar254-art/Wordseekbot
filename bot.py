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
# WORDLIST (300+ WORDS)
# =========================
WORDLIST = {
4: [
"game","word","play","time","code","fire","love","work","mind","test","cool","fast","team","goal","ring","dark",
"blue","home","talk","read","book","data","chat","send","mail","bank","shop","plan","idea","luck","rain","snow",
"wind","bird","fish","tree","frog","lion","wolf","bear","deer","milk","rice","salt","gold","iron","rock","sand",
"wave","boat","road","path","door","wall","roof","hero","jump","kick","sync","ping","pong","byte","load","save",
"edit","view","scan","open","lock","call","text","note","file","city","grow","zoom","type","grid","mask","king",
"queen","rook","pawn","hunt","bold","soft","hard","tiny","huge","deep","cold","warm","calm","wild","free","busy"
],
5: [
"apple","crane","stone","brain","table","chair","plant","smile","grape","plane","train","flame","water","earth",
"power","money","dream","story","music","party","night","world","house","phone","glass","river","ocean","beach",
"storm","cloud","snake","eagle","tiger","zebra","mouse","horse","sheep","bread","sugar","spice","cream","juice",
"green","black","white","brown","clock","brick","metal","cable","field","crown","knife","torch","brave","quick",
"sharp","happy","angry","peace","glory","faith","trust","crash","flash","smoke","light","sound","robot","logic",
"craft","build","lemon","mango","pearl","shark","whale","cabin","hotel","wheel","chain","sword","arrow","blaze"
],
6: [
"stream","planet","mirror","object","socket","school","mobile","system","laptop","python","rocket","bridge","forest",
"castle","animal","silver","golden","random","coding","signal","vector","output","window","circle","square","radius",
"energy","motion","charge","sensor","flight","driver","kernel","server","client","module","buffer","memory","cursor",
"packet","router","thread","device","galaxy","shadow","bright","future","orange","purple","yellow","binary","crypto",
"upload","import","export","format","global","native","status","button","screen","planet","rocket","battle","secret",
"hidden","decode","network","browser","tablet","system","coding","python","server","client","memory","signal","vector"
]
}

# =========================
# GAME ENGINE
# =========================
def new_game(chat_id, length):
    games[chat_id] = {
        "word": random.choice(WORDLIST[length]),
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
# COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 WordSeek Bot Ready!\n\n"
        "/new4 /new5 /new6 - Start Game\n"
        "/leaderboard - Group\n"
        "/global - Global\n"
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
# LEADERBOARDS
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

    # valid word check
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

    print("🚀 Bot Running")
    app.run_polling()

if __name__ == "__main__":
    main()
