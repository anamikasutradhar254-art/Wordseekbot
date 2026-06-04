# 🧠 WordSeek Telegram Bot

WordSeek is a fun Wordle-style multiplayer word guessing game built for Telegram groups and private chats.

Players guess hidden words and get color-coded hints:
🟩 Correct letter in correct position  
🟨 Correct letter in wrong position  
🟥 Letter not in the word  

---

## 🚀 Features

- 🎮 4-letter, 5-letter, 6-letter game modes
- 👥 Group & private chat support
- 🏆 Leaderboard system with points
- 📊 Win tracking system
- 🎯 Daily WordSeek mode (private chat only)
- 🔥 Owner broadcast system
- ⚡ Simple commands system

---

## 🎮 Commands

### Game Start
- `/new` → Start default 5-letter game  
- `/new4` → Start 4-letter game  
- `/new5` → Start 5-letter game  
- `/new6` → Start 6-letter game  

### Controls
- `/end` → End current game  
- `/help` → Show help menu  
- `/leaderboard` → Show top players  
- `/mystats` → Your stats  

### Daily Mode (Private Only)
- `/daily` → Start daily puzzle  
- `/pausedaily` → Exit daily mode  

### Admin (Owner Only)
- `/broadcast message` → Send message to all users  

---

## 🧩 How to Play

1. Start a game using `/new4`, `/new5`, or `/new6`
2. Guess the hidden word
3. Get color hints after each guess:
   - 🟩 Correct letter in right place
   - 🟨 Correct letter in wrong place
   - 🟥 Letter not in word
4. First correct guess wins points!

---

## 🛠 Setup (For Developers)

### 1. Clone Repo
```bash
git clone https://github.com/anamikasutradhar254-art/Wordseekbot.git
cd wordseek-bot
