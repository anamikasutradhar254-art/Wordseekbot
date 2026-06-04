import os
import json
import random
from datetime import datetime, timezone, timedelta

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "@jp_network")

DATA_FILE = "wordseek.json"

MAX_GUESSES = 30
ALLOWED = [4, 5, 6]

WORD_BANK = {
    4: ["rage", "game", "code", "team", "fire", "wave", "dark", "mint", "star", "plan"],
    5: ["apple", "brave", "chair", "dream", "flame", "grape", "smile", "tiger", "ocean", "river"],
    6: ["castle", "engine", "future", "garden", "hunter", "impact", "planet", "silver", "turtle"]
}

# ================= STORAGE =================
def load():
    if not os.path.exists(DATA_FILE):
        return {"games": {}, "lb": {}}
    return json.load(open(DATA_FILE))

def save(d):
    json.dump(d, open(DATA_FILE, "w"), indent=2)

DATA = load()

# ================= HELPERS =================
def norm(w): return "".join([c for c in w.lower() if c.isalpha()])

def pick(n): return random.choice(WORD_BANK[n])

def get_game(chat): return DATA["games"].get(str(chat))

def set_game(chat, g):
    DATA["games"][str(chat)] = g
    save(DATA)

def del_game(chat):
    DATA["games"].pop(str(chat), None)
    save(DATA)

# ================= BOARD =================
def colorize(g, a):
    res = ["🟥"] * len(g)
    a = list(a)

    for i in range(len(g)):
        if g[i] == a[i]:
            res[i] = "🟩"
            a[i] = None

    for i in range(len(g)):
        if res[i] == "🟩":
            continue
        if g[i] in a:
            res[i] = "🟨"
            a[a.index(g[i])] = None

    return " ".join(res)

def board(g):
    state = get_game(g)
    if not state:
        return ""

    lines = []
    lines.append(f"{state['len']}-letter mode · {len(state['guesses'])}/{MAX_GUESSES}")

    for x in state["guesses"]:
        lines.append(f"{colorize(x, state['answer'])}  {x.upper()}")

    return "\n".join(lines)

# ================= GAME =================
def new_game(chat, length):
    DATA["games"][str(chat)] = {
        "len": length,
        "answer": pick(length),
        "guesses": [],
        "active": True
    }
    save(DATA)

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Welcome to WordSeek!\n\nSupport: {SUPPORT_CHANNEL}\nUse /help"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "▸ WordSeek Help\n\n"
        "/new4 /new5 /new6 - Start game\n"
        "Guess words and get hints:\n"
        "🟩 correct\n🟨 wrong place\n🟥 not in word"
    )

async def new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id

    length = 5
    if context.args:
        try:
            length = int(context.args[0])
        except:
            pass

    if length not in ALLOWED:
        length = 5

    new_game(chat, length)

    await update.message.reply_text(
        f"{length}-letter WordSeek started!\nStart guessing..."
    )

async def new4(update, context): await new(update, context)
async def new5(update, context): await new(update, context)
async def new6(update, context): await new(update, context)

# ================= GUESS =================
async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    user = update.effective_user
    text = norm(update.message.text)

    game = get_game(chat)
    if not game or not game["active"]:
        return

    if len(text) != game["len"]:
        return

    game["guesses"].append(text)

    # WIN
    if text == game["answer"]:
        game["active"] = False
        del_game(chat)

        lb = DATA["lb"].get(str(user.id), {"name": user.full_name, "points": 0})
        lb["points"] += 10
        DATA["lb"][str(user.id)] = lb
        save(DATA)

        await update.message.reply_text(
            f"{board(chat)}\n\n"
            f"🎉 Congrats!\nCorrect Word: {game['answer']}\n+10 points\nUse /new{game['len']}"
        )
        return

    set_game(chat, game)

    await update.message.reply_text(board(chat))

# ================= LEADERBOARD =================
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = DATA.get("lb", {})

    if not data:
        await update.message.reply_text("🏆 No players yet. Start playing!")
        return

    sorted_lb = sorted(data.items(), key=lambda x: x[1]["points"], reverse=True)

    msg = ["🏆 Leaderboard"]
    for i, (uid, info) in enumerate(sorted_lb[:10], 1):
        msg.append(f"{i}. {info['name']} — {info['points']} pts")

    await update.message.reply_text("\n".join(msg))

# ================= BROADCAST =================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    text = " ".join(context.args)

    for chat in DATA["games"]:
        try:
            await context.bot.send_message(chat_id=int(chat), text=text)
        except:
            pass

    await update.message.reply_text("Broadcast sent!")

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("new", new))
    app.add_handler(CommandHandler("new4", new4))
    app.add_handler(CommandHandler("new5", new5))
    app.add_handler(CommandHandler("new6", new6))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, guess))

    print("WordSeek Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
