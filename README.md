# ⚡ Claude Token & Usage Tracker

A real-time token usage tracker for Claude Pro/Team — monitor your 5-hour rolling window, burn rate, and alert thresholds in one place.

## Features

- **5-Hour Rolling Window Timer** — tracks your Claude usage window with real-time countdown
- **Token Budget Monitoring** — set your estimated budget and watch remaining tokens with visual progress
- **Burn Rate Tracking** — see your tokens/minute consumption rate updated live
- **Hourly Breakdown** — 5-period bar chart showing token consumption by hour
- **Smart Alerts** — configurable warning thresholds at 70% and critical at 90% (customizable)
- **Session Log** — complete timestamped log of all token additions and events
- **Local Persistence** — all data saved to localStorage, survives browser refresh
- **Export CSV** — download your usage history for analysis

## How It Works

Claude Pro/Team uses a **rolling 5-hour window**, not a daily reset. When you hit your token limit, you must wait for older tokens to age out of the window before resuming full usage.

### Setup

1. **Open the tracker** and click **"Start / Reset Timer"**
2. **Set your budget** — Claude Pro gets roughly 88k–200k tokens per 5 hours (varies by model)
3. **Log token usage** — After each session, enter the tokens consumed and click "+Log"
4. **Watch alerts** — When you hit 70% and 90% thresholds, you'll get notifications

### Understanding Your Budget

- **Sonnet 4.6** (Cowork default) — generally ~150k tokens/5hr for Pro
- **Opus 4.6** — higher cost, fewer tokens available
- **Exact limits** — Anthropic doesn't publish exact numbers; adjust based on your experience

### Token Eaters

- Large file reads (PDFs, images, code archives)
- Screenshots and vision tasks
- Long conversation history (context carries forward)
- Tool-heavy workflows (API calls, bash, file operations)
- Multi-message back-and-forth in long chats

### Pro Tips

- **New chat = new context** — Each new Cowork conversation starts fresh, shedding old messages
- **Keep sessions focused** — Broad, open-ended prompts consume more tokens than specific ones
- **File size matters** — 1 KB of conversation history ≈ 300–400 tokens
- **30% left?** — Stick to short, focused tasks to avoid hitting the ceiling

## Session Analysis

Your session files tell a story:

- **143 sessions** across 193 MB total
- **30 sessions (21%)** hit the 2.2+ MB context limit (maxed out)
- **Recent sessions** (April) dropped to 500 KB average — good behavior shift
- **Estimated total burn** — ~50–60M tokens across all sessions

The big insight: You're now opening new chats deliberately instead of continuing long threads. This keeps context fresh and token burn predictable.

## Usage

```
1. Set your 5-hour budget (Pro users: try 150000–200000)
2. Click "Start / Reset Timer"
3. End each session: note your tokens from the timer and log them
4. Watch your burn rate and remaining balance
5. When window expires, timer auto-resets and you can go again
```

## Deployment

### Vercel

This tracker deploys instantly to Vercel as a static site:

```bash
npm install -g vercel
vercel --prod
```

Or connect this GitHub repo directly to Vercel and it auto-deploys on push.

### Local

Simply open `index.html` in any modern browser. All data persists in localStorage.

## Browser Support

Works in all modern browsers (Chrome, Safari, Firefox, Edge). Uses localStorage for persistence — data survives refresh but stays private (not synced to cloud).

## License

MIT
