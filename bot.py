import os
import random
from collections import defaultdict

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

# =========================
# GAME STATE
# =========================
games = {}
leaderboard = defaultdict(lambda: defaultdict(int))

# =========================
# DYNAMIC KEYBOARD (NEW FIX)
# =========================
def get_keyboard(length):
    return ReplyKeyboardMarkup(
        [[f"/new{length}"]],
        resize_keyboard=True
    )

# =========================
# WORDLIST (your original)
# =========================
WORDLIST = {
4: [
"game","word","play","time","code","love","work","mind","test","cool","fast","team","goal","ring","fire",
"dark","light","blue","home","talk","read","book","node","data","chat","send","mail","bank","shop","plan",
"idea","luck","rain","snow","wind","bird","fish","tree","frog","lion","wolf","bear","deer","milk","rice",
"salt","gold","iron","rock","sand","wave","boat","road","path","door","wall","roof","hero","jump","kick",
"sync","ping","pong","byte","load","save","edit","view","scan","open","lock","call","text","note","file"
],

5: [
"apple","crane","stone","brain","table","chair","plant","smile","grape","plane","train","flame","water",
"earth","power","money","dream","story","music","party","night","world","house","phone","glass","river",
"ocean","beach","storm","cloud","snake","eagle","tiger","zebra","mouse","horse","sheep","bread","sugar",
"spice","cream","juice","green","black","white","brown","clock","brick","metal","cable","field","crown",
"knife","torch","brave","quick","sharp","happy","angry","peace","glory","faith","trust","crash","flash"
],

6: [
"stream","planet","mirror","object","socket","school","mobile","system","laptop","google","python","button",
"screen","travel","rocket","bridge","forest","desert","island","castle","battle","animal","silver","golden",
"random","coding","signal","vector","output","window","circle","square","radius","energy","motion","charge",
"sensor","flight","driver","kernel","server","client","module","buffer","memory","cursor","packet","router"
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
        "guessed_words": set()
    }

def fancy(word):
    return " ".join(word.upper())

# =========================
# FIXED WORDLE LOGIC
# =========================
def check_guess(secret, guess):
    secret = list(secret)
    guess = list(guess)

    result = ["🟥"] * len(guess)
    used_secret = [False] * len(secret)
    used_guess = [False] * len(guess)

    # 🟩 correct
    for i in range(len(guess)):
        if guess[i] == secret[i]:
            result[i] = "🟩"
            used_secret[i] = True
            used_guess[i] = True

    # 🟨 wrong position
    for i in range(len(guess)):
        if used_guess[i]:
            continue
        for j in range(len(secret)):
            if not used_secret[j] and guess[i] == secret[j]:
                result[i] = "🟨"
                used_secret[j] = True
                break

    return " ".join(result)

def build_history(game):
    header = f"{game['length']}-letter mode · {len(game['history'])}/30\n\n"
    body = ""
    for g, h in game["history"]:
        body += f"{h}  {fancy(g)}\n"
    return header + body

# =========================
# COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 WordSeek Bot Ready!\n\n"
        "/new4 /new5 /new6 - Start Game\n"
        "/leaderboard - Scores\n"
        "/stats - Your stats\n"
        "/help - Help"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "▸ WordSeek Help\n\n"
        "🟩 Correct\n🟨 Wrong position\n🟥 Not in word"
    )

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id
    total = sum(leaderboard[chat].get(user, 0) for chat in leaderboard)
    await update.message.reply_text(f"📊 Your Stats\n\n🏆 Total Points: {total}")

async def new4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_game(update.effective_chat.id, 4)
    await update.message.reply_text("🎮 4-letter game started!")

async def new5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_game(update.effective_chat.id, 5)
    await update.message.reply_text("🎮 5-letter game started!")

async def new6(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_game(update.effective_chat.id, 6)
    await update.message.reply_text("🎮 6-letter game started!")

async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    data = leaderboard[chat]

    if not data:
        await update.message.reply_text("No scores yet!")
        return

    text = "🏆 Leaderboard 🏆\n\n"
    medals = ["🥇","🥈","🥉"]

    for i, (u, s) in enumerate(sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]):
        prefix = medals[i] if i < 3 else "🔅"
        text += f"{prefix} {u} - {s} pts\n"

    await update.message.reply_text(text)

# =========================
# MESSAGE HANDLER
# =========================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat = update.effective_chat.id
    user = update.effective_user.id

    if not message.text:
        return

    text = message.text.lower().strip()

    if chat not in games or not games[chat]["active"]:
        return

    game = games[chat]

    if len(text) != game["length"]:
        return

    if text in game["guessed_words"]:
        await message.reply_text("❌ Word already used!")
        return

    game["guessed_words"].add(text)
    game["tries"] += 1

    hint = check_guess(game["word"], text)
    game["history"].append((text, hint))

    # WIN
    if text == game["word"]:
        game["active"] = False
        score = max(0, 30 - game["tries"])
        leaderboard[chat][user] += score

        await message.reply_text(
            build_history(game) +
            f"\n🎉 Correct!\nWord: {game['word']}\n🏆 +{score} points\n\n▶ Play again 👇",
            reply_markup=get_keyboard(game["length"])
        )
        return

    await message.reply_text(build_history(game))

# =========================
# MAIN
# =========================
def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN missing!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("new4", new4))
    app.add_handler(CommandHandler("new5", new5))
    app.add_handler(CommandHandler("new6", new6))
    app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
