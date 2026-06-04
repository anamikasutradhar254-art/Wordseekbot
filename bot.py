import os
import random
from collections import defaultdict

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

games = {}

# leaderboard: chat_id -> {user_id -> score}
leaderboard = defaultdict(lambda: defaultdict(int))

WORDLIST = {
    4: ["game", "word", "play", "time", "code"],
    5: ["apple", "crane", "stone", "light", "brain"],
    6: ["stream", "planet", "mirror", "object", "socket"]
}

# -------------------------
# NEW GAME
# -------------------------
def new_game(chat_id, length):
    word = random.choice(WORDLIST[length])
    games[chat_id] = {
        "word": word,
        "length": length,
        "tries": 0,
        "active": True
    }

# -------------------------
# FIXED LETTER CHECK (NO DUPLICATE BUG)
# -------------------------
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

# -------------------------
# START GAME
# -------------------------
async def new4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_game(update.effective_chat.id, 4)
    await update.message.reply_text("🎮 4-letter game started!")

async def new5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_game(update.effective_chat.id, 5)
    await update.message.reply_text("🎮 5-letter game started!")

async def new6(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_game(update.effective_chat.id, 6)
    await update.message.reply_text("🎮 6-letter game started!")

# -------------------------
# LEADERBOARD COMMAND
# -------------------------
async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    data = leaderboard[chat]

    if not data:
        await update.message.reply_text("No scores yet!")
        return

    text = "🏆 LEADERBOARD:\n\n"
    sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)

    for user_id, score in sorted_data:
        text += f"User {user_id}: {score} pts\n"

    await update.message.reply_text(text)

# -------------------------
# MESSAGE HANDLER
# -------------------------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    user = update.effective_user.id
    text = update.message.text.lower()

    if chat not in games or not games[chat]["active"]:
        return

    game = games[chat]

    if len(text) != game["length"]:
        return

    game["tries"] += 1

    # WIN CONDITION
    if text == game["word"]:
        game["active"] = False

        score = max(0, 30 - game["tries"])
        leaderboard[chat][user] += score

        await update.message.reply_text(
            f"🎉 CORRECT!\nWord: {game['word']}\n"
            f"Tries: {game['tries']}\n"
            f"🏆 Score: +{score}\n\n"
            "👉 New game: /new4 /new5 /new6"
        )
        return

    hint = check_guess(game["word"], text)

    await update.message.reply_text(
        f"{hint}\nTries: {game['tries']}"
    )

# -------------------------
# HELP
# -------------------------
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/new4 - 4 letters\n"
        "/new5 - 5 letters\n"
        "/new6 - 6 letters\n"
        "/leaderboard - show scores"
    )

# -------------------------
# MAIN
# -------------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("new4", new4))
    app.add_handler(CommandHandler("new5", new5))
    app.add_handler(CommandHandler("new6", new6))
    app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
    app.add_handler(CommandHandler("help", help_cmd))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
