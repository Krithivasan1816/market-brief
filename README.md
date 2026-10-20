# Market Brief

Free, serverless investing news + guide. India and US markets.

- **Site**: static PWA in `docs/`, hosted on GitHub Pages.
- **Daily refresh**: GitHub Actions runs `scripts/fetch_news.py` at 07:00 IST (01:30 UTC), commits `docs/data/*.json`.
- **Push alert**: optional, via free [ntfy](https://ntfy.sh) app.
- **AI summary**: optional, free Gemini key (no billing account = cannot be charged).

Cost: $0. Repo must be **public** (free Actions minutes and Pages on free plan).

## Setup

1. Create a **public** repo on GitHub, e.g. `market-brief`. Push this folder:
   ```
   git remote add origin https://github.com/<you>/market-brief.git
   git branch -M main
   git push -u origin main
   ```
2. Repo -> Settings -> Pages -> Source: *Deploy from a branch* -> `main` / `/docs` -> Save.
3. Repo -> Settings -> Actions -> General -> Workflow permissions -> *Read and write permissions* -> Save.
4. **Push alert (optional)**
   - Install **ntfy** from the App Store, tap `+`, subscribe to a long random topic (e.g. `brief-` + 20 random chars). Anyone who knows the topic name can read it, so keep it private.
   - Repo -> Settings -> Secrets and variables -> Actions -> New secret: `NTFY_TOPIC` = that topic name.
5. **AI summary (optional)**
   - Get a key at <https://aistudio.google.com/apikey> (do not attach billing).
   - Add secret `GEMINI_API_KEY`. Quota exceeded = summary skipped, nothing is charged.
6. Repo -> Actions -> *Daily market brief* -> *Run workflow* once.
7. iPhone: Safari -> `https://<you>.github.io/market-brief/` -> Share -> **Add to Home Screen**.

## Local run

```
pip install -r requirements.txt
python scripts/fetch_news.py          # writes docs/data/
python -m http.server -d docs 8000    # open http://localhost:8000
```

## Customise

- News sources and index quotes: `scripts/feeds.json`.
- Investment options, resources, glossary: `docs/data/invest.json`.
- Run time: cron line in `.github/workflows/daily.yml` (UTC). GitHub may start it 5-30 min late.

## Notes

- Quotes use Yahoo's unofficial chart endpoint. If it breaks, the tiles disappear; news still works.
- A failing feed is skipped. If every feed fails, previous data stays.
- Rates and tax rules in `invest.json` are approximate. Verify with official sources before acting.
- Educational only, not financial advice.
