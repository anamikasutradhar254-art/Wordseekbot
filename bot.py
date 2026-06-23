import os
import json
import random
import time
import re
import unicodedata
import requests
from collections import defaultdict
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

DATA_FILE = os.getenv("DATA_FILE", "leaderboard.json")

START_PHOTO = os.getenv("START_PHOTO", "https://kommodo.ai/i/5EHl4RtntMWZOLcncf8o")
UPDATE_CHANNEL = os.getenv("UPDATE_CHANNEL", "https://t.me/jp_network")
DISCUSSION_GROUP = os.getenv("DISCUSSION_GROUP", "https://t.me/+lct3XoQXdg85ZGFl")
DONATE_LINK = os.getenv("DONATE_LINK", "https://t.me/jp_network")

CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")


def current_week_id():
    now = datetime.now()
    sunday = now - timedelta(days=(now.weekday() + 1) % 7)
    return sunday.strftime("%Y-%m-%d")


def default_data():
    return {
        "global": {},
        "daily": {},
        "weekly": {},
        "group": {},
        "users": {},
        "chats": [],
        "banned": [],
        "last_daily_reset": CURRENT_DATE,
        "last_weekly_reset": current_week_id()
    }


def load_data():
    if not os.path.exists(DATA_FILE):
        return default_data()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            old = json.load(f)
            base = default_data()
            base.update(old)
            return base
    except:
        return default_data()


data = load_data()

games = {}
VALID_CACHE = set()
INVALID_CACHE = set()
last_msg_time = defaultdict(float)

user_names = defaultdict(str)
for uid, name in data.get("users", {}).items():
    user_names[int(uid)] = name

global_leaderboard = defaultdict(int)
daily_scores = defaultdict(int)
weekly_scores = defaultdict(int)
leaderboard = defaultdict(lambda: defaultdict(int))
known_chats = set()
banned_users = set(int(uid) for uid in data.get("banned", []))

for uid, score in data.get("global", {}).items():
    global_leaderboard[int(uid)] = int(score)

for uid, score in data.get("daily", {}).items():
    daily_scores[int(uid)] = int(score)

for uid, score in data.get("weekly", {}).items():
    weekly_scores[int(uid)] = int(score)

for chat_id, users in data.get("group", {}).items():
    leaderboard[int(chat_id)] = defaultdict(int)
    for uid, score in users.items():
        leaderboard[int(chat_id)][int(uid)] = int(score)

for chat_id in data.get("chats", []):
    known_chats.add(int(chat_id))


def save_data():
    save = {
        "global": dict(global_leaderboard),
        "daily": dict(daily_scores),
        "weekly": dict(weekly_scores),
        "group": {
            str(chat): dict(scores)
            for chat, scores in leaderboard.items()
        },
        "users": dict(user_names),
        "chats": list(known_chats),
        "banned": list(banned_users),
        "last_daily_reset": data.get("last_daily_reset", CURRENT_DATE),
        "last_weekly_reset": data.get("last_weekly_reset", current_week_id())
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(save, f, ensure_ascii=False, indent=2)


def reset_scores_if_needed():
    today = datetime.now().strftime("%Y-%m-%d")
    week_id = current_week_id()

    changed = False

    if data.get("last_daily_reset") != today:
        daily_scores.clear()
        data["last_daily_reset"] = today
        changed = True

    if data.get("last_weekly_reset") != week_id:
        weekly_scores.clear()
        data["last_weekly_reset"] = week_id
        changed = True

    if changed:
        save_data()


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
        "last","late","lead","leaf","left","lend","less","life","lift","like","line","link","list","live","logo","long","look","lord","lost","main",
        "bout","bour","boun","boud","boul"
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


def clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = re.sub(r"[^a-z]", "", text)
    return text.strip()


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


def new_game(chat_id, length):
    games[chat_id] = {
        "word": random.choice(WORDLIST[length]).lower(),
        "length": length,
        "tries": 0,
        "active": True,
        "history": [],
        "guessed": set()
    }


BOLD_MAP = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇"
)


def fancy(word):
    return word.upper().translate(BOLD_MAP)


def check_guess(secret, guess):
    secret = list(secret)
    guess = list(guess)

    result = ["🟥"] * len(guess)
    used = [False] * len(secret)

    for i in range(len(guess)):
        if guess[i] == secret[i]:
            result[i] = "🟩"
            used[i] = True

    for i in range(len(guess)):
        if result[i] == "🟩":
            continue

        for j in range(len(secret)):
            if not used[j] and guess[i] == secret[j]:
                result[i] = "🟨"
                used[j] = True
                break

    return " ".join(result)


def build_history(game):
    text = f"{game['length']}-letter mode · {len(game['history'])}/30\n\n"

    for guess, hint in game["history"]:
        text += f"{hint} {fancy(guess)}\n"

    return text


def save_user(update: Update):
    user = update.effective_user

    if not user:
        return

    uid = user.id
    name = user.username or user.first_name or f"User{uid}"
    user_names[uid] = name


def is_banned(update: Update):
    user = update.effective_user
    if user and user.id in banned_users:
        return True
    return False


def mention_user(uid):
    name = user_names.get(uid) or f"User{uid}"
    name = str(name).replace("<", "").replace(">", "")
    return f'<a href="tg://user?id={uid}">{name}</a>'


def format_lb(title, scores):
    if not scores:
        return f"🏆 <b>{title}</b>\n\nNo scores yet."

    text = f"🏆 <b>{title}</b> 🏆\n\n"

    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]

    for rank, (uid, score) in enumerate(top, start=1):
        if rank == 1:
            icon = "🥇"
        elif rank == 2:
            icon = "🥈"
        elif rank == 3:
            icon = "🥉"
        else:
            icon = "☀️"

        text += f"{icon} {mention_user(uid)} - {score:,} pts\n"

    return text


def leaderboard_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("« Global »", callback_data="lb_global"),
            InlineKeyboardButton("🔄", callback_data="lb_refresh"),
            InlineKeyboardButton("This chat", callback_data="lb_chat"),
        ],
        [
            InlineKeyboardButton("Today", callback_data="lb_today"),
            InlineKeyboardButton("This week", callback_data="lb_week"),
        ],
        [
            InlineKeyboardButton("All time", callback_data="lb_global"),
        ],
        [
            InlineKeyboardButton("4 letters", callback_data="new4_btn"),
            InlineKeyboardButton("5 letters", callback_data="new5_btn"),
            InlineKeyboardButton("6 letters", callback_data="new6_btn"),
        ],
        [
            InlineKeyboardButton("📢 Updates ↗", url=UPDATE_CHANNEL),
            InlineKeyboardButton("💬 Discussion ↗", url=DISCUSSION_GROUP),
        ]
    ])


def start_keyboard(bot_username):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ Add me to your Group",
                url=f"https://t.me/{bot_username}?startgroup=true"
            )
        ],
        [
            InlineKeyboardButton("Updates ↗", url=UPDATE_CHANNEL),
            InlineKeyboardButton("Help", callback_data="help_menu"),
            InlineKeyboardButton("Discussion ↗", url=DISCUSSION_GROUP),
        ],
        [
            InlineKeyboardButton("💞 Donate ↗", url=DONATE_LINK)
        ]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    caption = (
        "Welcome to WordSeek!\n\n"
        "A fun and competitive Wordle-style game that you can play directly on Telegram.\n\n"
        "Quick Start:\n"
        "• Use /new4 /new5 /new6 to start a new game\n"
        "• Add me to a group with admin permissions to play with friends\n"
        "• Use /help for detailed instructions and command list\n\n"
        "Ready to test your word skills? Let's play!"
    )

    try:
        bot_username = context.bot.username
        await update.message.reply_photo(
            photo=START_PHOTO,
            caption=caption,
            reply_markup=start_keyboard(bot_username)
        )
    except:
        await update.message.reply_text(
            caption,
            reply_markup=start_keyboard(context.bot.username)
        )
      async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    text = (
        "▸ WordSeek Help\n\n"
        "🟩 Correct\n"
        "🟨 Wrong position\n"
        "🟥 Not in word\n\n"
        "/new4 /new5 /new6 - Start Game\n"
        "/leaderboard - Leaderboard Menu\n"
        "/global - Global Leaderboard\n"
        "/today - Today Global Leaderboard\n"
        "/week - Weekly Global Leaderboard\n"
        "/stats - My Stats\n"
        "/help - Help me\n\n"
        "📢 Support Channel: @jp_network"
    )

    await update.message.reply_text(
        text,
        reply_to_message_id=update.message.message_id
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat = query.message.chat.id
    data_btn = query.data

    reset_scores_if_needed()

    if data_btn == "help_menu":
        await query.message.reply_text(
            "▸ WordSeek Help\n\n"
            "🟩 Correct\n"
            "🟨 Wrong position\n"
            "🟥 Not in word\n\n"
            "/new4 /new5 /new6 - Start Game\n"
            "/leaderboard - Leaderboard Menu\n"
            "/global - Global Leaderboard\n"
            "/today - Today Global Leaderboard\n"
            "/week - Weekly Global Leaderboard\n"
            "/stats - My Stats\n\n"
            "📢 Support Channel: @jp_network"
        )
        return

    if data_btn == "lb_global":
        text = format_lb("GLOBAL LEADERBOARD", global_leaderboard)

    elif data_btn == "lb_chat":
        text = format_lb("THIS CHAT", leaderboard[chat])

    elif data_btn == "lb_today":
        text = format_lb("TODAY GLOBAL", daily_scores)

    elif data_btn == "lb_week":
        text = format_lb("THIS WEEK GLOBAL", weekly_scores)

    elif data_btn == "lb_refresh":
        text = format_lb("THIS CHAT", leaderboard[chat])

    elif data_btn == "new4_btn":
        new_game(chat, 4)
        await query.message.reply_text("🎮 4-letter WordSeek started!\nStart guessing...")
        return

    elif data_btn == "new5_btn":
        new_game(chat, 5)
        await query.message.reply_text("🎮 5-letter WordSeek started!\nStart guessing...")
        return

    elif data_btn == "new6_btn":
        new_game(chat, 6)
        await query.message.reply_text("🎮 6-letter WordSeek started!\nStart guessing...")
        return

    else:
        return

    await query.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=leaderboard_keyboard()
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    reset_scores_if_needed()

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
        f"📆 Week: {weekly_scores.get(user, 0)} pts"
    )

    await update.message.reply_text(text)


async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    reset_scores_if_needed()

    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    await update.message.reply_text(
        format_lb("THIS CHAT", leaderboard[update.effective_chat.id]),
        parse_mode="HTML",
        reply_markup=leaderboard_keyboard(),
        reply_to_message_id=update.message.message_id
    )


async def global_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    reset_scores_if_needed()
    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    await update.message.reply_text(
        format_lb("GLOBAL LEADERBOARD", global_leaderboard),
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )


async def today_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    reset_scores_if_needed()
    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    await update.message.reply_text(
        format_lb("TODAY GLOBAL", daily_scores),
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )


async def week_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    reset_scores_if_needed()
    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    await update.message.reply_text(
        format_lb("THIS WEEK GLOBAL", weekly_scores),
        parse_mode="HTML",
        reply_to_message_id=update.message.message_id
    )


async def new4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    reset_scores_if_needed()
    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    new_game(update.effective_chat.id, 4)

    await update.message.reply_text(
        "🎮 4-letter WordSeek started!\nStart guessing...",
        reply_to_message_id=update.message.message_id
    )


async def new5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    reset_scores_if_needed()
    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    new_game(update.effective_chat.id, 5)

    await update.message.reply_text(
        "🎮 5-letter WordSeek started!\nStart guessing...",
        reply_to_message_id=update.message.message_id
    )


async def new6(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_banned(update):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    reset_scores_if_needed()
    known_chats.add(update.effective_chat.id)
    save_user(update)
    save_data()

    new_game(update.effective_chat.id, 6)

    await update.message.reply_text(
        "🎮 6-letter WordSeek started!\nStart guessing...",
        reply_to_message_id=update.message.message_id
)
def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id

    if context.args:
        arg = context.args[0].replace("@", "").lower()

        if arg.isdigit():
            return int(arg)

        for uid, name in user_names.items():
            if str(name).lower().replace("@", "") == arg:
                return uid

    return None


async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Not allowed")
        return

    target = get_target_user(update, context)

    if not target:
        await update.message.reply_text("Usage:\n/ban user_id\nReply user message with /ban")
        return

    banned_users.add(target)
    save_data()

    await update.message.reply_text(f"✅ User banned: {target}")


async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Not allowed")
        return

    target = get_target_user(update, context)

    if not target:
        await update.message.reply_text("Usage:\n/unban user_id\nReply user message with /unban")
        return

    banned_users.discard(target)
    save_data()

    await update.message.reply_text(f"✅ User unbanned: {target}")


async def add_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Not allowed")
        return

    if len(context.args) < 2 and not update.message.reply_to_message:
        await update.message.reply_text(
            "Usage:\n"
            "/addpoints user_id points\n"
            "/addpoints @username points\n"
            "Ya user ke msg ko reply karke /addpoints 50"
        )
        return

    target = get_target_user(update, context)

    try:
        if update.message.reply_to_message:
            points = int(context.args[0])
        else:
            points = int(context.args[1])
    except:
        await update.message.reply_text("❌ Points number me do")
        return

    if not target:
        await update.message.reply_text("❌ User nahi mila")
        return

    global_leaderboard[target] += points

    if global_leaderboard[target] < 0:
        global_leaderboard[target] = 0

    save_data()

    await update.message.reply_text(
        f"✅ Points updated\n\n"
        f"User: {target}\n"
        f"Change: {points}\n"
        f"Total Global: {global_leaderboard[target]}"
    )


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Not allowed")
        return

    all_chats = set(known_chats)

    for chat_id in games.keys():
        all_chats.add(chat_id)

    for chat_id in leaderboard.keys():
        all_chats.add(chat_id)

    if update.message.reply_to_message:
        source = update.message.reply_to_message
        caption = " ".join(context.args) or source.caption or ""

        sent = 0
        failed = 0

        for chat_id in all_chats:
            try:
                if source.photo:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=source.photo[-1].file_id,
                        caption=caption
                    )
                elif source.video:
                    await context.bot.send_video(
                        chat_id=chat_id,
                        video=source.video.file_id,
                        caption=caption
                    )
                elif source.animation:
                    await context.bot.send_animation(
                        chat_id=chat_id,
                        animation=source.animation.file_id,
                        caption=caption
                    )
                elif source.document:
                    await context.bot.send_document(
                        chat_id=chat_id,
                        document=source.document.file_id,
                        caption=caption
                    )
                elif source.text:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=source.text
                    )
                else:
                    failed += 1
                    continue

                sent += 1

            except:
                failed += 1

        await update.message.reply_text(
            f"✅ Broadcast Done\n\nSent: {sent}\nFailed: {failed}"
        )
        return

    msg = " ".join(context.args)

    if not msg:
        await update.message.reply_text(
            "Usage:\n"
            "/broadcast Your text\n"
            "Photo/Video/Text ko reply karke /broadcast"
        )
        return

    sent = 0
    failed = 0

    for chat_id in all_chats:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=msg
            )
            sent += 1
        except:
            failed += 1

    await update.message.reply_text(
        f"✅ Broadcast Done\n\nSent: {sent}\nFailed: {failed}"
    )


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg or not msg.text:
        return

    if is_banned(update):
        return

    reset_scores_if_needed()

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
        await msg.reply_text("❌ Invalid word", reply_to_message_id=msg.message_id)
        return

    if text in game["guessed"]:
        await msg.reply_text("❌ Already used", reply_to_message_id=msg.message_id)
        return

    game["guessed"].add(text)
    game["tries"] += 1

    hint = check_guess(game["word"], text)
    game["history"].append((text, hint))

    try:
        await context.bot.set_message_reaction(
            chat_id=chat,
            message_id=msg.message_id,
            reaction=[{"type": "emoji", "emoji": "💞"}]
        )
    except:
        pass

    if text == game["word"]:
        game["active"] = False

        score = max(1, 30 - game["tries"])

        leaderboard[chat][user] += score
        global_leaderboard[user] += score
        daily_scores[user] += score
        weekly_scores[user] += score

        save_data()

        win_text = (
            "Congrats! You guessed it correctly.\n"
            f"Correct Word: {game['word']}\n"
            f"Added {score} to the leaderboard.\n"
            f"Start with /new{game['length']}"
        )

        await msg.reply_text(
            win_text,
            reply_to_message_id=msg.message_id
        )
        return

    if game["tries"] >= 30:
        game["active"] = False
        save_data()

        lose_text = (
            f"{build_history(game)}\n\n"
            "Game Over!\n"
            f"Correct Word: {game['word']}\n"
            f"Start with /new{game['length']}"
        )

        await msg.reply_text(
            lose_text,
            reply_to_message_id=msg.message_id
        )
        return

    await msg.reply_text(
        build_history(game),
        reply_to_message_id=msg.message_id
  )
  # =========================
# MAIN
# =========================

def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN missing")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # Start / Help
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))

    # Game Commands
    app.add_handler(CommandHandler("new4", new4))
    app.add_handler(CommandHandler("new5", new5))
    app.add_handler(CommandHandler("new6", new6))

    # Leaderboards
    app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
    app.add_handler(CommandHandler("global", global_cmd))
    app.add_handler(CommandHandler("today", today_cmd))
    app.add_handler(CommandHandler("week", week_cmd))
    app.add_handler(CommandHandler("stats", stats))

    # Owner Commands
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("addpoints", add_points))

    # Buttons
    app.add_handler(CallbackQueryHandler(button_handler))

    # Message Handler
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle
        )
    )

    print("🚀 WordSeek Ultimate Running...")
    app.run_polling()


if __name__ == "__main__":
    main()
