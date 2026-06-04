import os
import json
import random

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
def norm(w):
    return "".join([c for c in w.lower() if c.isalpha()])

def pick(n):
    return random.choice(WORD_BANK[n])

def get_game(chat):
    return DATA["games"].get(str(chat))

def set_game(chat, g):
    DATA["games"][str(chat)] = g
    save(DATA)

def del_game(chat):
    DATA["games"].pop(str(chat), None)
    save(DATA)

def is_valid_word(word, length):
    return len(word) == length and word.isalpha()

# ================= WORDLE COLOR ENGINE =================
def colorize(answer, guess):
    answer = list(answer)
    guess = list(guess)

    result = ["🟥"] * len(answer)

    # GREEN PASS
    for i in range(len(answer)):
        if guess[i] == answer[i]:
            result[i] = "🟩"
            answer[i] = None
            guess[i] = None

    # YELLOW PASS
    for i in range(len(answer)):
        if guess[i] is not None and guess[i] in answer:
            result[i] = "🟨"
            answer[answer.index(guess[i])] = None

    return " ".join(result)

# ================= BOARD =================
def board(state):
    if not state:
        return ""

    lines = []
    lines.append(f"{state['len']}-letter mode · {len(state['guesses'])}/{MAX_GUESSES}")

    for x in state["guesses"]:
        lines.append(f"{colorize(state['answer'], x)}  {x.upper()}")

    return "\n".join(lines)

# ================= GAME =================
def new_game(chat, length):
    DATA["games"][str(chat)] = {
        "len": length,
        "answer": pick(length),
        "guesses": [],
        "used": [],
        "active": True
    }
    save(DATA)

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE, length: int):
    chat = update.effective_chat.id
    new_game(chat, length)

    await update.message.reply_text(
        f"🎮 Game Started!\n"
        f"Guess the {length}-letter word! 🔤\n"
        f"You have {MAX_GUESSES} attempts."
    )

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if member.id == context.bot.id:
                await update.message.reply_text(
                    "🙏 thanks for adding me in your group...\n\n"
                    "Give me adminship Bcz I won't send msg without any power in your group ! 👾"
                )
                return

    await update.message.reply_text(
        f"Welcome to WordSeek!\nSupport: {SUPPORT_CHANNEL}\nUse /help"
    )

# ================= HELP =================
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "▸ WordSeek Help\n\n"
        "/new4 /new5 /new6 - Start game\n"
        "Guess words:\n"
        "🟩 correct\n🟨 wrong place\n🟥 not in word"
    )

# ================= NEW GAME =================
async def new4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_game(update, context, 4)

async def new5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_game(update, context, 5)

async def new6(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_game(update, context, 6)

# ================= GUESS =================
async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    user = update.effective_user
    text = norm(update.message.text)

    game = get_game(chat)
    if not game or not game["active"]:
        return

    # ❌ invalid length
    if len(text) != game["len"]:
        await update.message.reply_text(
            f"❌ {text.upper()} is not a valid {game['len']}-letter word."
        )
        return

    # ❌ invalid word
    if not is_valid_word(text, game["len"]):
        await update.message.reply_text(
            f"❌ {text.upper()} is not a valid word."
        )
        return

    # ❌ duplicate
    if text in game["used"]:
        await update.message.reply_text("⚠️ You already tried this word!")
        return

    # ✅ add guess
    game["used"].append(text)
    game["guesses"].append(text)

    # ================= WIN =================
    if text == game["answer"]:
        game["active"] = False

        attempts = len(game["guesses"])

        # 🔥 FINAL SCORE SYSTEM
        score = MAX_GUESSES - attempts

        lb = DATA["lb"].get(str(user.id), {"name": user.full_name, "points": 0})
        lb["points"] += score
        DATA["lb"][str(user.id)] = lb

        length = game["len"]
        del_game(chat)

        await update.message.reply_text(
            f"{board(game)}\n\n"
            f"🎉 Correct!\n"
            f"Word: {text.upper()}\n"
            f"Attempts: {attempts}/{MAX_GUESSES}\n"
            f"🏆 Score: {score}\n\n"
            f"🔁 Play Again:\n"
            f"/new{length}"
        )
        return

    set_game(chat, game)
    await update.message.reply_text(board(game))

# ================= LEADERBOARD =================
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = DATA.get("lb", {})

    if not data:
        await update.message.reply_text("🏆 No players yet!")
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
