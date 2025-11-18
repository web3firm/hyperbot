# 📺 Screen Quick Reference for HyperBot

Screen is a terminal multiplexer that lets your bot run 24/7 even after you disconnect from SSH.

## 🚀 Quick Start

### Install Screen (First Time Only)
```bash
sudo apt update
sudo apt install screen -y
```

### Start Bot in Screen
```bash
# Navigate to bot directory
cd ~/hyperbot

# Start new screen session
screen -S hyperbot

# Run your bot
python3 -m app.bot

# Detach (keeps bot running)
Press: Ctrl+A, then D
```

✅ **Bot is now running in background!** You can close SSH safely.

## 📋 Essential Commands

| Action | Command |
|--------|---------|
| **Start new session** | `screen -S hyperbot` |
| **Detach (keep running)** | `Ctrl+A` then `D` |
| **List sessions** | `screen -ls` |
| **Reattach to session** | `screen -r hyperbot` |
| **Kill session** | `screen -XS hyperbot quit` |
| **Stop bot gracefully** | Inside screen: `Ctrl+C` then `exit` |

## 🔄 Common Workflows

### View Running Bot
```bash
# Reattach to see live logs
screen -r hyperbot

# Detach again when done
Ctrl+A then D
```

### Restart Bot
```bash
# Method 1: Kill and restart
screen -XS hyperbot quit
screen -S hyperbot -dm python3 -m app.bot

# Method 2: Reattach, stop, restart
screen -r hyperbot
# Press Ctrl+C to stop bot
python3 -m app.bot
# Press Ctrl+A then D to detach
```

### Update Bot Code
```bash
# Kill running bot
screen -XS hyperbot quit

# Pull latest code
cd ~/hyperbot
git pull origin main

# Start updated bot
screen -S hyperbot
python3 -m app.bot
# Ctrl+A then D to detach
```

## 🔍 Troubleshooting

### Check if Bot is Running
```bash
# List screen sessions
screen -ls

# Should see: "hyperbot" with status
# If empty, bot is not running

# Alternative: Check process
ps aux | grep "app.bot"
```

### Multiple Sessions Running
```bash
# List all sessions
screen -ls

# Kill specific session
screen -XS hyperbot.12345 quit

# Or kill all hyperbot sessions
screen -ls | grep hyperbot | awk '{print $1}' | xargs -I {} screen -XS {} quit
```

### Can't Reattach (Session Attached)
```bash
# Force detach and reattach
screen -d -r hyperbot

# Or kill and restart
screen -XS hyperbot quit
screen -S hyperbot
```

### Screen Frozen/Not Responding
```bash
# Inside screen, try:
Ctrl+A then Ctrl+C  # Interrupt

# If still frozen, from another SSH:
screen -XS hyperbot quit
```

## 💡 Pro Tips

### 1. Create Alias (Shortcut)
Add to `~/.bashrc`:
```bash
alias bot-start='cd ~/hyperbot && screen -S hyperbot -dm python3 -m app.bot'
alias bot-attach='screen -r hyperbot'
alias bot-stop='screen -XS hyperbot quit'
alias bot-status='screen -ls | grep hyperbot && ps aux | grep app.bot | grep -v grep'
```

Then use:
```bash
bot-start   # Start bot
bot-attach  # View bot
bot-stop    # Stop bot
bot-status  # Check status
```

### 2. View Logs Without Attaching
```bash
# Real-time logs
tail -f ~/hyperbot/logs/bot_$(date +%Y%m%d).log

# Last 50 lines
tail -50 ~/hyperbot/logs/bot_*.log
```

### 3. Run Bot in Background (One Command)
```bash
screen -S hyperbot -dm bash -c "cd ~/hyperbot && python3 -m app.bot"
```

### 4. Auto-Start on Reboot
Add to crontab:
```bash
crontab -e

# Add this line:
@reboot cd /home/YOUR_USERNAME/hyperbot && screen -S hyperbot -dm python3 -m app.bot
```

## 🎯 Daily Operations

**Morning Check:**
```bash
screen -ls                  # Check bot running
screen -r hyperbot          # View status
# Ctrl+A then D to detach
```

**Update & Restart:**
```bash
screen -XS hyperbot quit    # Stop
git pull origin main        # Update
screen -S hyperbot          # Start
python3 -m app.bot          # Run
# Ctrl+A then D             # Detach
```

**Emergency Stop:**
```bash
screen -XS hyperbot quit    # Immediate kill
```

## 🆘 Help

**Show Screen Help:**
```bash
screen -help
```

**Screen Manual:**
```bash
man screen
```

**Key Bindings Inside Screen:**
- All commands start with `Ctrl+A`
- Then press second key:
  - `D` = Detach
  - `K` = Kill window
  - `C` = Create new window
  - `N` = Next window
  - `P` = Previous window
  - `?` = Show help

---

**Ready to run your bot 24/7! 🚀**
