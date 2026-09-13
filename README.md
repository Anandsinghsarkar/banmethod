# GroupGuard — Telegram Group Moderation Bot

A small Telegram bot for moderation in groups where you are an authorized admin. It does not mass-report accounts or act on accounts outside your group.

## Features

- `/start` — help menu and command list
- `/ban` — reply to a member's message to ban them
- `/unban USER_ID` — unban by numeric Telegram user ID
- `/mute [minutes]` — reply to a member; default 10 minutes (maximum 7 days)
- `/unmute` — reply to a member to restore send permissions
- `/warn` — reply to a member to issue a warning
- `/warnings` — check your warnings; admins can reply to check another member
- `/rules` and `/setrules TEXT` — view/set group rules
- Bot command menu is registered automatically at startup

Warnings and custom rules are stored in memory and reset when the bot restarts.

## Run in Termux

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy its token. Never publish the token.
2. Add the bot to your Telegram group and grant only the permissions it needs: **Ban users** and **Restrict members**. Promote yourself as a group admin.
3. Install and run:

```bash
pkg update -y
pkg install python git -y
git clone https://github.com/Anandsinghsarkar/banmethod.git
cd banmethod
python -m pip install --upgrade pip
pip install -r requirements.txt
export BOT_TOKEN='PASTE_YOUR_BOT_TOKEN_HERE'
python main.py
```

Keep the Termux session running while you want the bot online. Use `Ctrl+C` to stop it.

## Usage

In your group, reply to a member's message with `/ban`, `/mute`, `/mute 30`, `/unmute`, or `/warn`. Use `/unban 123456789` with the user's numeric ID. `/setrules Be respectful; no spam` sets the group's rules.

## Notes

- Commands that change membership are admin-only and depend on Telegram bot permissions.
- Telegram does not allow bots to ban group admins; the bot must have adequate permissions.
- This is a basic starter bot, not a persistent database-backed moderation system.
