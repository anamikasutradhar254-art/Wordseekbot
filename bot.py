import os
import random
import json

try:
    import requests
except:
    requests = None

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# =====================
# ENV
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")

# =====================
# GAME STATE
# =====================
games = {}  # chat_id -> game data

# =====================
# SMALL FALLBACK WORDLIST
# (expand or replace with API later)
# =====================
WORDLIST = {
    4: ["game", "word", "code", "play", "time", "link"],
    5: ["apple", "brain", "crane", "flame", "stone", "light"],
    6: ["stream", "planet", "object", "socket", "mirror"]
}

# =====================
# REAL DICTIONARY CHECK
# =====================
def is_valid_word(word: str) -> bool:
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    try:
        r = requests.get(url, timeout=5)
        return r.status_code == 200
    except:
        return word.lower() in sum(WORDLIST.values(), [])

# =====================
# GAME CREATE
# =====================
def new_game(chat_id, length):
    word = random.choice(WORDLIST[length]).lower()

    games[chat_id] = {
        "word": word,
        "length": length,
        "tries": 0,
        "max_tries": 10,
        "active": True
    }

# =====================
# START GAME COMMANDS
# =====================
async def start_4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    new_game(chat, 4)
    await update.message.reply_text("🎮 4-letter WordSeek started!\nGuess the word...")

async def start_5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    new_game(chat, 5)
    await update.message.reply_text("🎮 5-letter WordSeek started!\nGuess the word...")

async def start_6(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    new_game(chat, 6)
    await update.message.reply_text("🎮 6-letter WordSeek started!\nGuess the word...")

# =====================
# GUESS HANDLER
# =====================
def check_guess(secret, guess):
    result = []
    for i, ch in enumerate(guess):
        if ch == secret[i]:
            result.append("🟩")
        elif ch in secret:
            result.append("🟨")
        else:
            result.append("🟥")
    return " ".join(result)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    text = update.message.text.lower()

    if chat not in games or not games[chat]["active"]:
        return

    game = games[chat]

    if len(text) != game["length"]:
        await update.message.reply_text(f"❌ {game['length']}-letter word required!")
        return

    if not is_valid_word(text):
        await update.message.reply_text("❌ Not a valid word!")
        return

    game["tries"] += 1

    if text == game["word"]:
        game["active"] = False
        await update.message.reply_text(f"🎉 Correct! Word was: {game['word']}")
        return

    hint = check_guess(game["word"], text)

    if game["tries"] >= game["max_tries"]:
        game["active"] = False
        await update.message.reply_text(f"💀 Game Over! Word was: {game['word']}")
    else:
        await update.message.reply_text(f"{hint}\nTries: {game['tries']}/{game['max_tries']}")

# =====================
# HELP
# =====================
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 WordSeek Bot\n\n"
        "/new4 - 4 letter game\n"
        "/new5 - 5 letter game\n"
        "/new6 - 6 letter game\n\n"
        "Guess words in chat!"
    )

# =====================
# MAIN
# =====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("new4", start_4))
    app.add_handler(CommandHandler("new5", start_5))
    app.add_handler(CommandHandler("new6", start_6))
    app.add_handler(CommandHandler("help", help_cmd))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
