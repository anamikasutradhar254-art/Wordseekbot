import asyncio
import json
import os
import random
import string
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatType, ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =========================
# Config
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "@jp_network")
DATA_FILE = os.getenv("DATA_FILE", "wordseek_data.json")

MAX_GUESSES = 30
DAILY_MAX_GUESSES = 6
DEFAULT_WORD_LEN = 5
ALLOWED_LENGTHS = {4, 5, 6}
KATHMANDU_TZ = timezone(timedelta(hours=5, minutes=45))

# A reasonably large pool of simple words. Add more if you want.
WORD_BANK = {
    4: [
        "rage", "game", "play", "word", "seek", "tone", "code", "team", "gold", "fire",
        "ring", "dark", "light", "wave", "move", "snap", "gain", "peak", "road", "time",
        "mint", "leaf", "book", "star", "plan", "risk", "made", "bold", "clue", "zone",
    ],
    5: [
        "apple", "brave", "chair", "dream", "eager", "flame", "glory", "honey", "input",
        "jolly", "knock", "lemon", "mango", "night", "ocean", "piano", "queen", "river",
        "stone", "tiger", "unity", "vivid", "wheat", "xenon", "young", "zesty", "crane",
        "plane", "sugar", "laser", "smile", "grape", "bloom", "march", "proud", "quick",
    ],
    6: [
        "banana", "castle", "dazzle", "engine", "future", "garden", "hunter", "impact",
        "jungle", "kitten", "legend", "master", "nature", "orange", "pocket", "ribbon",
        "silver", "turtle", "united", "vortex", "wander", "yellow", "zephyr", "breeze",
        "friend", "planet", "spring", "random", "secret", "winner", "bright",
    ],
}

# =========================
# Persistent storage
# =========================

def _default_data() -> dict:
    return {
        "leaderboard": {},  # user_id -> {name, points, wins, games}
        "daily": {
            "date": None,
            "answer": None,
            "chat_state": {},  # chat_id -> state
        },
    }


def load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        return _default_data()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        base = _default_data()
        base.update(data)
        base.setdefault("leaderboard", {})
        base.setdefault("daily", {"date": None, "answer": None, "chat_state": {}})
        base["daily"].setdefault("chat_state", {})
        return base
    except Exception:
        return _default_data()


def save_data(data: dict) -> None:
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


DATA = load_data()

# =========================
# Helpers
# =========================

def today_kathmandu() -> str:
    return datetime.now(KATHMANDU_TZ).strftime("%Y-%m-%d")


def normalize_word(word: str) -> str:
    return "".join(ch for ch in word.lower().strip() if ch.isalpha())


def pick_word(length: int) -> str:
    words = WORD_BANK[length]
    return random.choice(words)


def ensure_daily_answer() -> str:
    today = today_kathmandu()
    daily = DATA["daily"]
    if daily.get("date") != today or not daily.get("answer"):
        daily["date"] = today
        daily["answer"] = pick_word(5)
        daily["chat_state"] = {}
        save_data(DATA)
    return daily["answer"]


def get_user_record(user_id: int, full_name: str) -> dict:
    lb = DATA["leaderboard"]
    key = str(user_id)
    if key not in lb:
        lb[key] = {"name": full_name, "points": 0, "wins": 0, "games": 0}
    else:
        lb[key]["name"] = full_name
    return lb[key]


def update_points(user_id: int, full_name: str, delta: int, win: bool = False, game: bool = False) -> None:
    rec = get_user_record(user_id, full_name)
    rec["points"] += delta
    if win:
        rec["wins"] += 1
    if game:
        rec["games"] += 1
    save_data(DATA)


def get_top_leaderboard(limit: int = 10) -> List[Tuple[str, dict]]:
    items = list(DATA["leaderboard"].items())
    items.sort(key=lambda kv: (kv[1].get("points", 0), kv[1].get("wins", 0)), reverse=True)
    return items[:limit]


def build_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Help", callback_data="help")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")],
    ])


def make_game_state(length: int, answer: Optional[str] = None, daily: bool = False) -> dict:
    return {
        "active": True,
        "length": length,
        "answer": answer or pick_word(length),
        "guesses": [],
        "daily": daily,
        "max_guesses": DAILY_MAX_GUESSES if daily else MAX_GUESSES,
        "solved": False,
    }


def get_chat_state_key(chat_id: int) -> str:
    return str(chat_id)


def get_chat_state(chat_id: int) -> Optional[dict]:
    return DATA["daily"]["chat_state"].get(get_chat_state_key(chat_id))


def set_chat_state(chat_id: int, state: Optional[dict]) -> None:
    key = get_chat_state_key(chat_id)
    if state is None:
        DATA["daily"]["chat_state"].pop(key, None)
    else:
        DATA["daily"]["chat_state"][key] = state
    save_data(DATA)


def colorize_guess(guess: str, answer: str) -> str:
    # Wordle-style: handle duplicate letters correctly.
    result = ["🟥"] * len(guess)
    answer_chars = list(answer)

    # Greens
    for i, ch in enumerate(guess):
        if ch == answer[i]:
            result[i] = "🟩"
            answer_chars[i] = None

    # Yellows
    for i, ch in enumerate(guess):
        if result[i] == "🟩":
            continue
        if ch in answer_chars:
            result[i] = "🟨"
            answer_chars[answer_chars.index(ch)] = None
    return " ".join(result)


def format_board(state: dict) -> str:
    lines = []
    for guess in state.get("guesses", []):
        lines.append(f"{colorize_guess(guess, state['answer'])}  {guess.upper()}")
    return "\n".join(lines)


def help_text() -> str:
    return (
        "▸ How to Play WordSeek\n\n"
        "1. Start a game using /new, /new4, /new5, or /new6\n"
        "2. Guess the hidden word\n"
        "3. After each guess, you'll get color hints:\n"
        "   🟩 Correct letter in the right spot\n"
        "   🟨 Correct letter in the wrong spot\n"
        "   🟥 Letter not in the word\n"
        "4. First person to guess correctly wins!\n"
        "5. Maximum 30 guesses per game\n\n"
        "Word Length Modes:\n"
        "• /new → Start default 5-letter game\n"
        "• /new 4 → Start specific length (4, 5, or 6)\n"
        "• /new4 → Start 4-letter game\n"
        "• /new5 → Start 5-letter game\n"
        "• /new6 → Start 6-letter game\n\n"
        "Basic Commands:\n"
        "• /new - Start a new game (default 5 letters)\n"
        "• /new4 - Start a 4-letter game\n"
        "• /new5 - Start a 5-letter game\n"
        "• /new6 - Start a 6-letter game\n"
        "• /end - End current game (voting or admin only)\n"
        "• /help - Show this help menu\n"
        "• /daily - Play Daily WordSeek (private chat only)\n"
        "• /pausedaily - Pause Daily mode and go back to normal games\n\n"
        "Daily Mode (Private Chat Only):\n"
        "• Start a daily game using /daily command\n"
        "• Works like New York Times Wordle: one fixed word per day\n"
        "• You only get 6 guesses per daily puzzle\n"
        "• A new puzzle unlocks every day at 06:00 in Kathmandu time (GMT+5:45)\n"
        "• You build a streak by solving the daily puzzle without failing\n"
        "• You cannot play normal WordSeek and Daily at the same time:\n"
        "  - If a normal game is running, end it before using /daily\n"
        "  - If Daily is active, use /pausedaily to play normal WordSeek again"
    )


def start_text() -> str:
    return (
        "Welcome to WordSeek!\n\n"
        "A fun and competitive Wordle-style game that you can play directly on Telegram.\n"
        f"👾Support channel :- {SUPPORT_CHANNEL}"
    )


def can_use_group_game(chat_type: str) -> bool:
    return chat_type in {ChatType.GROUP, ChatType.SUPERGROUP, ChatType.PRIVATE}


def parse_length_arg(text: str) -> Optional[int]:
    parts = text.split()
    if len(parts) == 1:
        return None
    if len(parts) >= 2:
        try:
            val = int(parts[1])
            if val in ALLOWED_LENGTHS:
                return val
        except ValueError:
            return None
    return None


# =========================
# Game logic
# =========================
async def send_board(update: Update, context: ContextTypes.DEFAULT_TYPE, state: dict, win: bool = False) -> None:
    text = format_board(state)
    if win:
        text = (text + "\n\n" if text else "") + f"Congrats! You guessed it correctly.\nCorrect Word: {state['answer']}"
    else:
        text = (text + "\n\n" if text else "") + f"Game running... {len(state['guesses'])}/{state['max_guesses']} guesses used."
    await update.message.reply_text(text.strip())


def get_active_state_for_chat(chat_id: int) -> Optional[dict]:
    return get_chat_state(chat_id)


async def start_new_game(update: Update, context: ContextTypes.DEFAULT_TYPE, length: int) -> None:
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return

    if length not in ALLOWED_LENGTHS:
        await update.message.reply_text("Please choose 4, 5, or 6 letters.")
        return

    state = make_game_state(length=length, daily=False)
    set_chat_state(chat.id, state)
    await update.message.reply_text(
        f"New {length}-letter WordSeek started!\nGuess the hidden word.\nMaximum {MAX_GUESSES} guesses.",
        reply_markup=build_keyboard(),
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(start_text(), reply_markup=build_keyboard())


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(help_text(), disable_web_page_preview=True)


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if not chat:
        return
    if update.message and update.message.text:
        length = parse_length_arg(update.message.text)
        if length is None:
            length = DEFAULT_WORD_LEN
    else:
        length = DEFAULT_WORD_LEN
    await start_new_game(update, context, length)


async def cmd_new4(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_new_game(update, context, 4)


async def cmd_new5(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_new_game(update, context, 5)


async def cmd_new6(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_new_game(update, context, 6)


async def cmd_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return

    state = get_chat_state(chat.id)
    if not state:
        await update.message.reply_text("No active game in this chat.")
        return

    if chat.type in {ChatType.GROUP, ChatType.SUPERGROUP} and user.id != OWNER_ID:
        await update.message.reply_text("Only the owner can end a group game in this version.")
        return

    set_chat_state(chat.id, None)
    await update.message.reply_text("Current game ended.")


async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if not chat:
        return
    if chat.type != ChatType.PRIVATE:
        await update.message.reply_text("/daily works only in private chat.")
        return

    ensure_daily_answer()
    current = get_chat_state(chat.id)
    if current and current.get("daily"):
        await update.message.reply_text("Daily mode is already active in this chat.")
        return
    if current and not current.get("daily"):
        await update.message.reply_text("A normal game is running. Use /end first, then /daily.")
        return

    state = make_game_state(length=5, answer=DATA["daily"]["answer"], daily=True)
    set_chat_state(chat.id, state)
    await update.message.reply_text(
        "Daily WordSeek started! You have 6 guesses.\nToday's puzzle is fixed until the next reset.",
        reply_markup=build_keyboard(),
    )


async def cmd_pausedaily(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if not chat:
        return
    state = get_chat_state(chat.id)
    if not state or not state.get("daily"):
        await update.message.reply_text("Daily mode is not active here.")
        return
    set_chat_state(chat.id, None)
    await update.message.reply_text("Daily mode paused. You can start normal games again.")


async def broadcast_to_all(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str) -> None:
    failed = 0
    sent = 0
    # Broadcast to all known users from leaderboard.
    for uid_str in list(DATA["leaderboard"].keys()):
        try:
            await context.bot.send_message(chat_id=int(uid_str), text=message)
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(f"Broadcast done. Sent: {sent}, Failed: {failed}")


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or user.id != OWNER_ID:
        await update.message.reply_text("Owner only command.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast your message here")
        return
    message = " ".join(context.args)
    await broadcast_to_all(update, context, message)


async def cmd_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    top = get_top_leaderboard(10)
    if not top:
        await update.message.reply_text("Leaderboard is empty right now.")
        return

    lines = ["🏆 Leaderboard"]
    for i, (uid, rec) in enumerate(top, start=1):
        lines.append(f"{i}. {rec.get('name', 'Unknown')} — {rec.get('points', 0)} points | {rec.get('wins', 0)} wins")
    await update.message.reply_text("\n".join(lines))


async def cmd_mystats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    rec = get_user_record(user.id, user.full_name)
    await update.message.reply_text(
        f"Your stats:\nPoints: {rec['points']}\nWins: {rec['wins']}\nGames: {rec['games']}"
    )


async def on_guess(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.message
    if not chat or not user or not msg or not msg.text:
        return

    state = get_chat_state(chat.id)
    if not state or not state.get("active"):
        return

    text = normalize_word(msg.text)
    length = state["length"]
    if len(text) != length:
        return

    if state.get("solved"):
        return

    # Accept only if in bank or pure alphabetic guess; this keeps gameplay smooth.
    if text not in WORD_BANK[length]:
        await msg.reply_text(f"Please guess a valid {length}-letter word.")
        return

    # Record user in leaderboard.
    get_user_record(user.id, user.full_name)

    state["guesses"].append(text)
    save_data(DATA)

    if text == state["answer"]:
        state["solved"] = True
        state["active"] = False
        set_chat_state(chat.id, None)

        # Points: bonus for fewer guesses.
        remaining = max(0, state["max_guesses"] - len(state["guesses"]))
        points = 15 + remaining
        update_points(user.id, user.full_name, points, win=True, game=True)

        board = format_board(state)
        final_text = (
            f"{board}\n\n"
            f"Congrats! You guessed it correctly.\n"
            f"Correct Word: {state['answer']}\n"
            f"Added {points} to the leaderboard.\n"
            f"Start with /new{length if length in (4, 5, 6) else ''}"
        )
        await msg.reply_text(final_text.strip())
        return

    update_points(user.id, user.full_name, 0, game=True)

    if len(state["guesses"]) >= state["max_guesses"]:
        set_chat_state(chat.id, None)
        await msg.reply_text(
            f"{format_board(state)}\n\nGame over!\nCorrect Word: {state['answer']}\nStart again with /new{length if length in (4, 5, 6) else ''}".strip()
        )
        return

    await msg.reply_text(f"{colorize_guess(text, state['answer'])}  {text.upper()}")


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    if query.data == "help":
        await query.message.reply_text(help_text(), disable_web_page_preview=True)
    elif query.data == "leaderboard":
        top = get_top_leaderboard(10)
        if not top:
            await query.message.reply_text("Leaderboard is empty right now.")
            return
        lines = ["🏆 Leaderboard"]
        for i, (uid, rec) in enumerate(top, start=1):
            lines.append(f"{i}. {rec.get('name', 'Unknown')} — {rec.get('points', 0)} points | {rec.get('wins', 0)} wins")
        await query.message.reply_text("\n".join(lines))


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text("Something went wrong. Please try again.")
    except Exception:
        pass


# =========================
# App setup
# =========================

def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing")

    ensure_daily_answer()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("new4", cmd_new4))
    app.add_handler(CommandHandler("new5", cmd_new5))
    app.add_handler(CommandHandler("new6", cmd_new6))
    app.add_handler(CommandHandler("end", cmd_end))
    app.add_handler(CommandHandler("daily", cmd_daily))
    app.add_handler(CommandHandler("pausedaily", cmd_pausedaily))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    app.add_handler(CommandHandler("mystats", cmd_mystats))

    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_guess))
    app.add_error_handler(on_error)

    print("WordSeek bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
      
