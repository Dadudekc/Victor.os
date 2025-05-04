# Discord Inbox

This directory serves as the bridge for Discord commands and directives into Dream.OS.

- A Discord bot listens to a designated channel (e.g., #dreamos-commands) and writes each command as a file here (JSON or Markdown).
- Dream.OS runs a poller or file-watcher that processes new files as high-priority user directives, overriding agent tasks as needed.
- All commands are logged for auditability.
- Only authorized Discord users (General Victor, Commander THEA, etc.) should be allowed to issue commands.
- Results and status updates can be posted back to Discord via the bot.

This enables real-time, remote control and integration with the Dream.OS swarm.
