import os
import json
import random
import time
import re
import unicodedata
import requests
from collections import defaultdict

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

DATA_FILE = "leaderboard.json"

# =========================
# DEFAULT DATA
# =========================
def default_data():
    return {
        "global": {},
        "daily": {},
        "weekly": {},
        "monthly": {},
        "group": {},
        "users": {},
        "chats": []
    }

# =========================
# LOAD DATA
# =========================
def load_data():
    if not os.path.exists(DATA_FILE):
        return default_data()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default_data()

data = load_data()

# =========================
# STATE
# =========================
games = {}
VALID_CACHE = set()
INVALID_CACHE = set()
last_msg_time = defaultdict(float)

# =========================
# USER NAMES
# =========================
user_names = defaultdict(str)

for uid, name in data.get("users", {}).items():
    user_names[int(uid)] = name

# =========================
# LEADERBOARDS
# =========================
global_leaderboard = defaultdict(int)
daily_scores = defaultdict(int)
weekly_scores = defaultdict(int)
monthly_scores = defaultdict(int)

for uid, score in data.get("global", {}).items():
    global_leaderboard[int(uid)] = int(score)

for uid, score in data.get("daily", {}).items():
    daily_scores[int(uid)] = int(score)

for uid, score in data.get("weekly", {}).items():
    weekly_scores[int(uid)] = int(score)

for uid, score in data.get("monthly", {}).items():
    monthly_scores[int(uid)] = int(score)

leaderboard = defaultdict(lambda: defaultdict(int))

for chat_id, users in data.get("group", {}).items():
    leaderboard[int(chat_id)] = defaultdict(int)

    for uid, score in users.items():
        leaderboard[int(chat_id)][int(uid)] = int(score)

known_chats = set()

for chat_id in data.get("chats", []):
    known_chats.add(int(chat_id))

# =========================
# SAVE DATA
# =========================
def save_data():
    data = {
        "global": dict(global_leaderboard),
        "daily": dict(daily_scores),
        "weekly": dict(weekly_scores),
        "monthly": dict(monthly_scores),
        "group": {
            str(chat): dict(scores)
            for chat, scores in leaderboard.items()
        },
        "users": dict(user_names),
        "chats": list(known_chats)
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
# =========================
# WORDLIST (200+ EACH)
# =========================
WORDLIST = {
4: [
"game","word","play","time","code","fire","love","work","mind","test","cool","fast","team","goal","ring","dark","blue","home","talk","read",
"book","data","chat","send","mail","bank","shop","plan","idea","luck","rain","snow","wind","bird","fish","tree","frog","lion","wolf","bear",
"deer","milk","rice","salt","gold","iron","rock","sand","wave","boat","road","path","door","wall","roof","hero","jump","kick","sync","ping",
"pong","byte","load","save","edit","view","scan","open","lock","call","text","note","file","city","grow","able","acid","aged","also","area",
"army","away","baby","back","ball","band","base","bath","bell","belt","best","bill","blow","body","bomb","bond","bone","boom","born","boss",
"both","bowl","bulk","burn","bush","busy","cake","calm","camp","card","care","case","cash","cast","cell","chip","club","coal","coat","come",
"cook","cope","copy","core","cost","crew","crop","date","dawn","days","dead","deal","dear","debt","deep","deny","desk","dial","diet","disk",
"done","dose","down","draw","drop","drug","dual","duck","dust","duty","earn","ease","east","easy","edge","else","even","ever","evil","exit",
"face","fact","fail","fair","fall","farm","fear","feed","feel","feet","fell","felt","find","fine","firm","five","flag","flat","flow","food",
"fool","foot","form","four","free","fuel","full","gain","gate","gave","gear","gift","girl","give","glad","goat","goes","gone","good","grab",
"gray","grew","grid","grip","hair","half","hall","hand","hard","harm","hate","head","heal","hear","heat","held","hell","help","hill","hire",
"hold","hole","holy","hope","host","hour","huge","hunt","hurt","icon","inch","into","item","join","joke","king","knee","knew","land","lane",
"last","late","lead","leaf","left","lend","less","life","lift","like","line","link","list","live","logo","long","look","lord","lost","main"
],

5: [
"apple","crane","stone","brain","table","chair","plant","smile","grape","plane","train","flame","water","earth","power","money","dream","story","music","party",
"night","world","house","phone","glass","river","ocean","beach","storm","cloud","snake","eagle","tiger","zebra","mouse","horse","sheep","bread","sugar","spice",
"cream","juice","green","black","white","brown","clock","brick","metal","cable","field","crown","knife","torch","brave","quick","sharp","happy","angry","peace",
"glory","faith","trust","crash","flash","about","above","abuse","actor","acute","admit","adopt","adult","after","again","agent","agree","ahead","alarm","album",
"alert","alike","alive","allow","alone","along","alter","among","angel","anger","apart","apply","arena","argue","arise","array","aside","asset","audio","audit",
"avoid","award","aware","badly","baker","bases","basic","basis","began","begin","begun","being","below","bench","birth","blame","blind","block","blood","board",
"boost","booth","bound","brand","break","breed","brief","bring","broad","broke","build","built","buyer","carry","catch","cause","chain","chart","chase","cheap",
"check","chest","chief","child","chose","civil","claim","class","clean","clear","click","close","coach","coast","court","cover","craft","cross","daily","dance",
"death","delay","depth","dirty","doubt","dozen","draft","drama","dress","drink","drive","eager","early","empty","enemy","enjoy","enter","entry","equal","error",
"event","every","exact","exist","extra","faint","false","fault","favor","final","first","focus","force","frame","fresh","front","fruit","funny","giant","given",
"grand","grant","grass","great","group","guard","guess","guest","guide","habit","heart","heavy","honey","human","ideal","image","index","inner","input","issue",
"joint","judge","known","label","large","laser","later","layer","learn","leave","legal","level","light","limit","local","logic","loose","lucky","magic","major"
],

6: [
"stream","planet","mirror","object","socket","school","mobile","system","laptop","python","rocket","bridge","forest","castle","animal","silver","golden","random","coding","signal",
"vector","output","window","circle","square","radius","energy","motion","charge","sensor","flight","driver","kernel","server","client","module","buffer","memory","cursor","packet",
"router","thread","device","galaxy","shadow","bright","future","orange","purple","yellow","binary","crypto","upload","import","export","format","global","native","status","button",
"screen","battle","secret","hidden","decode","network","browser","tablet","accept","access","across","acting","action","active","actual","advice","advise","affect","afford","afraid",
"agency","agenda","almost","always","amount","annual","answer","anyone","appeal","appear","around","arrive","artist","aspect","assess","assist","assume","attack","attend","author",
"backup","beauty","became","become","before","behalf","behind","belief","belong","better","border","bottle","bottom","branch","breath","broken","budget","burden","camera","cannot",
"career","caught","center","chance","change","choice","choose","church","closed","closer","coffee","column","combat","coming","common","cookie","corner","costly","county","course",
"covers","create","credit","crisis","custom","damage","danger","dealer","debate","decide","deeply","defeat","defend","define","degree","demand","depend","design","detail","dinner",
"direct","doctor","double","dragon","during","easily","effect","effort","either","eleven","emerge","empire","enable","ending","engage","engine","enough","ensure","entire","escape",
"estate","ethics","expert","fabric","factor","failed","fairly","family","famous","father","fellow","female","figure","finger","finish","flower","follow","forget","formal","former",
"friend","garden","gather","gender","ground","growth","handle","happen","health","honest","hunter","impact","income","indeed","injury","inside","intent","island","itself","junior"
]
}

WORDSET = {
    4: set(WORDLIST[4]),
    5: set(WORDLIST[5]),
    6: set(WORDLIST[6]),
}

# =========================
# CLEAN INPUT
# =========================
def clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = re.sub(r"[^a-z]", "", text)
    return text.strip()

# =========================
# DICTIONARY CHECK
# =========================
def is_valid_word(word: str) -> bool:
    word = clean(word)

    if not word:
        return False

    if word in VALID_CACHE:
        return True

    if word in INVALID_CACHE:
        return False

    if word in WORDSET.get(len(word), set()):
        VALID_CACHE.add(word)
        return True

    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        res = requests.get(url, timeout=3)

        if res.status_code == 200:
            VALID_CACHE.add(word)
            return True

        INVALID_CACHE.add(word)
        return False

    except:
        INVALID_CACHE.add(word)
        return False
# =========================
# NEW GAME
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

# =========================
# FANCY WORD
# =========================
def fancy(word):
    return " ".join(word.upper())

# =========================
# CHECK GUESS
# =========================
def check_guess(secret, guess):
    secret = list(secret)
    guess = list(guess)

    result = ["🟥"] * len(guess)
    used = [False] * len(secret)

    # Green check
    for i in range(len(guess)):
        if guess[i] == secret[i]:
            result[i] = "🟩"
            used[i] = True

    # Yellow check
    for i in range(len(guess)):
        if result[i] == "🟩":
            continue

        for j in range(len(secret)):
            if not used[j] and guess[i] == secret[j]:
                result[i] = "🟨"
                used[j] = True
                break

    return " ".join(result)

# =========================
# BUILD HISTORY
# =========================
def build_history(game):
    text = f"{game['length']}-letter mode · {len(game['history'])}/30\n\n"

    for guess, hint in game["history"]:
        text += f"{hint}  {fancy(guess)}\n"

    return text

# =========================
# SAVE USER INFO
# =========================
def save_user(update: Update):
    user = update.effective_user

    if not user:
        return

    uid = user.id

    name = (
        user.username
        or user.first_name
        or f"User{uid}"
    )

    user_names[uid] = name

# =========================
# GET GLOBAL RANK
# =========================
def get_global_rank(user_id):
    sorted_users = sorted(
        global_leaderboard.items(),
        key=lambda x: x[1],
        reverse=True
    )

    for rank, (uid, score) in enumerate(sorted_users, start=1):
        if uid == user_id:
            return rank

    return 0
# =========================
# LEADERBOARD FORMATTER
# =========================
def format_lb(title, data):
    if not data:
        return f"🏆 {title}\n\nNo scores yet."

    text = f"🏆 {title} 🏆\n\n"

    top = sorted(
        data.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    for rank, (uid, score) in enumerate(top, start=1):
        name = user_names.get(uid) or f"User{uid}"

        if rank == 1:
            icon = "🥇"
        elif rank == 2:
            icon = "🥈"
        elif rank == 3:
            icon = "🥉"
        else:
            icon = "⭐"

        text += f"{icon} {name} • {score} pts\n"

    return text

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    await update.message.reply_text(
        "👋 WordSeek Bot Ready!\n\n"
        "🟩 Correct\n"
        "🟨 Wrong position\n"
        "🟥 Not in word\n\n"
        "🎮 Game Commands:\n"
        "/new4 /new5 /new6 - Start Game\n\n"
        "🏆 Leaderboards:\n"
        "/leaderboard - This Chat\n"
        "/global - Global\n"
        "/today - Daily\n"
        "/week - Weekly\n"
        "/month - Monthly\n\n"
        "📊 /stats - My Stats\n"
        "❔ /help - Help\n\n"
        "📢 Support: @jp_network"
    )

# =========================
# HELP
# =========================
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    await update.message.reply_text(
        "▸ WordSeek Help\n\n"
        "🟩 Correct\n"
        "🟨 Wrong position\n"
        "🟥 Not in word\n\n"
        "/new4 /new5 /new6 - Start Game\n"
        "/leaderboard - This Chat Leaderboard\n"
        "/global - Global Leaderboard\n"
        "/today - Daily Leaderboard\n"
        "/week - Weekly Leaderboard\n"
        "/month - Monthly Leaderboard\n"
        "/stats - My Stats\n"
        "/help - Help me\n\n"
        "📢 Support Channel: @jp_network",
        reply_to_message_id=update.message.message_id
    )

# =========================
# STATS
# =========================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    user = update.effective_user.id
    chat = update.effective_chat.id

    text = (
        f"📊 {user_names.get(user, f'User{user}')}'s Stats\n\n"
        f"🏠 Group: {leaderboard[chat].get(user, 0)} pts\n"
        f"🌍 Global: {global_leaderboard.get(user, 0)} pts\n"
        f"📅 Today: {daily_scores.get(user, 0)} pts\n"
        f"📆 Week: {weekly_scores.get(user, 0)} pts\n"
        f"🗓 Month: {monthly_scores.get(user, 0)} pts"
    )

    await update.message.reply_text(text)

# =========================
# LEADERBOARD COMMANDS
# =========================
async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    await update.message.reply_text(
        format_lb("THIS CHAT", leaderboard[update.effective_chat.id])
    )

async def global_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    await update.message.reply_text(
        format_lb("GLOBAL LEADERBOARD", global_leaderboard)
    )

async def today_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    await update.message.reply_text(
        format_lb("TODAY", daily_scores)
    )

async def week_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    await update.message.reply_text(
        format_lb("THIS WEEK", weekly_scores)
    )

async def month_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    await update.message.reply_text(
        format_lb("THIS MONTH", monthly_scores)
    )

# =========================
# BROADCAST
# =========================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Not allowed")
        return

    msg = " ".join(context.args)

    if not msg:
        await update.message.reply_text(
            "Usage:\n/broadcast Your message"
        )
        return

    all_chats = set(known_chats)

    for chat_id in games.keys():
        all_chats.add(chat_id)

    for chat_id in leaderboard.keys():
        all_chats.add(chat_id)

    sent = 0
    failed = 0

    for chat_id in all_chats:
        try:
            await context.bot.send_message(
                chat_id,
                f"📢 Broadcast\n\n{msg}"
            )
            sent += 1
        except:
            failed += 1

    await update.message.reply_text(
        f"✅ Broadcast Done\n\n"
        f"Sent: {sent}\n"
        f"Failed: {failed}"
    )

# =========================
# GAME START COMMANDS
# =========================
async def new4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    new_game(update.effective_chat.id, 4)

    await update.message.reply_text(
        "🎮 4-letter WordSeek started!\nStart guessing..."
    )

async def new5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    new_game(update.effective_chat.id, 5)

    await update.message.reply_text(
        "🎮 5-letter WordSeek started!\nStart guessing..."
    )

async def new6(update: Update, context: ContextTypes.DEFAULT_TYPE):
    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    new_game(update.effective_chat.id, 6)

    await update.message.reply_text(
        "🎮 6-letter WordSeek started!\nStart guessing..."
    )
# =========================
# MESSAGE HANDLER
# =========================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg or not msg.text:
        return

    chat = update.effective_chat.id
    user = update.effective_user.id

    known_chats.add(chat)
    save_user(update)

    text = clean(msg.text)

    if chat not in games or not games[chat]["active"]:
        return

    game = games[chat]

    if len(text) != game["length"]:
        return

    now = time.time()

    if now - last_msg_time[user] < 1.0:
        return

    last_msg_time[user] = now

    if not is_valid_word(text):
        await msg.reply_text("❌ Invalid word")
        return

    if text in game["guessed"]:
        await msg.reply_text("❌ Already used")
        return

    game["guessed"].add(text)
    game["tries"] += 1

    hint = check_guess(game["word"], text)
    game["history"].append((text, hint))

    # =========================
    # WIN
    # =========================
    if text == game["word"]:
        game["active"] = False

        score = max(5, 35 - game["tries"])

        leaderboard[chat][user] += score
        global_leaderboard[user] += score
        daily_scores[user] += score
        weekly_scores[user] += score
        monthly_scores[user] += score

        save_data()

        rank = get_global_rank(user)

        win_text = (
            f"{build_history(game)}\n\n"
            f"🎉 CONGRATULATIONS!\n\n"
            f"✅ Word: {game['word'].upper()}\n"
            f"🏆 Earned: +{score} pts\n"
            f"🌍 Global Rank: #{rank}\n"
            f"⭐ Total Global Score: {global_leaderboard[user]} pts\n\n"
            f"🎮 Start New Game:\n"
            f"/new4\n"
            f"/new5\n"
            f"/new6"
        )

        await msg.reply_text(win_text)
        return

    # =========================
    # LOSE
    # =========================
    if game["tries"] >= 30:
        game["active"] = False
        save_data()

        await msg.reply_text(
            build_history
          
   # =========================
   # MAIN
   # =========================
   def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN missing")
        return

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
    app.add_handler(CommandHandler("today", today_cmd))
    app.add_handler(CommandHandler("week", week_cmd))
    app.add_handler(CommandHandler("month", month_cmd))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle
        )
    )

    print("🚀 WordSeek AI PRO FINAL RUNNING")
    app.run_polling()


if __name__ == "__main__":
    main()
