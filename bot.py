import os
import random
from collections import defaultdict

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

# =========================
# GAME STATE
# =========================
games = {}
leaderboard = defaultdict(lambda: defaultdict(int))

# =========================
# WORDLIST (200+ each mode)
# =========================
WORDLIST = {
4: [
"game","word","play","time","code","love","work","mind","test","cool","fast","team","goal","ring","fire",
"dark","light","blue","home","talk","read","book","node","data","chat","send","mail","bank","shop","plan",
"idea","luck","rain","snow","wind","bird","fish","tree","frog","lion","wolf","bear","deer","milk","rice",
"salt","gold","iron","rock","sand","wave","boat","road","path","door","wall","roof","hero","jump","kick",
"sync","ping","pong","byte","load","save","edit","view","scan","open","lock","call","text","note","file",
"zone","area","heat","cold","dust","soil","farm","crop","seed","king","base","ball","join","hack","zero",
"edge","form","grid","link","zoom","user","chat","post","like","rate","drop","drag","flip","stop","turn"
],

5: [
"apple","crane","stone","brain","table","chair","plant","smile","grape","plane","train","flame","water","earth",
"power","money","dream","story","music","party","night","world","house","phone","glass","river","ocean","beach",
"storm","cloud","snake","eagle","tiger","zebra","mouse","horse","sheep","bread","sugar","spice","cream","juice",
"green","black","white","brown","clock","brick","metal","cable","field","crown","knife","torch","brave","quick",
"sharp","happy","angry","peace","glory","faith","trust","crash","flash","swing","bring","think","write","build",
"clean","throw","break","speak","learn","teach","dance","watch","sleep","drink","stand","drive","catch","float",
"solid","fluid","grain","fruit","berry","sweet","sour","fresh","young","large","small","heavy","music","light",
"tower","angel","devil","ghost","robot","ninja","magic","lucky","royal","beast","frost","shine","blaze"
],

6: [
"stream","planet","mirror","object","socket","school","mobile","system","laptop","google","python","button","screen",
"travel","rocket","bridge","forest","desert","island","castle","battle","animal","silver","golden","random","coding",
"signal","vector","output","window","circle","square","radius","energy","motion","charge","sensor","flight","driver",
"kernel","server","client","module","buffer","memory","cursor","packet","router","switch","galaxy","cosmic","launch",
"create","delete","insert","update","render","process","thread","storage","backup","restore","secure","access","domain",
"portal","network","stable","dynamic","design","format","convert","compile","execute","develop","control","manage",
"protect","binary","decode","encode","script","program","matrix","bright","shadow","camera","canvas","widget","search"
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

def check_guess(secret, guess):
    secret = list(secret)
    guess = list(guess)
    result = ["🟥"] * len(guess)

    for i in range(len(guess)):
        if guess[i] == secret[i]:
            result[i] = "🟩"
            secret[i] = None
            guess[i] = None

    for i in range(len(guess)):
        if guess[i] is not None and guess[i] in secret:
            result[i] = "🟨"
            secret[secret.index(guess[i])] = None

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
        "👋 WordSeek Bot\n\n"
        "/new4 /new5 /new6 - Start Game\n"
        "/leaderboard - Scores\n"
        "/stats - Your stats\n"
        "/help - Help"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "▸ WordSeek Help\n\n"
        "Guess words:\n🟩 correct\n🟨 wrong position\n🟥 not in word\n\n"
        "Rules:\n- No repeat words\n- Only fresh guesses count"
    )

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id

    total = 0
    for chat in leaderboard:
        total += leaderboard[chat].get(user, 0)

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
# MESSAGE HANDLER (FIXED)
# =========================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    chat = update.effective_chat.id
    user = update.effective_user.id

    # ❌ ignore bot messages
    if message.from_user.is_bot:
        return

    # ❌ ignore bot replies
    if message.reply_to_message and message.reply_to_message.from_user.is_bot:
        return

    if not message.text:
        return

    text = message.text.lower().strip()

    if chat not in games or not games[chat]["active"]:
        return

    game = games[chat]

    if len(text) != game["length"]:
        return

    # ❌ repeat word block
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
            f"\n🎉 Correct!\nWord: {game['word']}\n🏆 +{score} points"
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
