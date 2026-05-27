# Scout Dashboard

Observability dashboard for Scout's retrieval engine.

## Setup

```bash
npm install
npm run dev
```

Open http://localhost:3000

## Usage

Point the dashboard at your repo's `.scout/scout.log` file by uploading it,
or configure the `SCOUT_LOG_PATH` env var to auto-load from a fixed path.

## Stack

- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Recharts
