# Corpus source: Project Gutenberg eBook #2388

This prototype corpus uses Sir Edwin Arnold's *The Song Celestial; Or, Bhagavad-Gita (from the Mahabharata)*.

- Source record: https://www.gutenberg.org/ebooks/2388
- Raw text: `pg2388.txt` (the Gutenberg text, including its notices)
- Translator: Sir Edwin Arnold
- Translation publication: 1885; the source identifies a 1900 printed edition
- Language: English
- Citation granularity: chapter only. The source does not provide verse numbers, so the ingestion pipeline deliberately does not assign them.
- Rights notice: Project Gutenberg identifies the eBook as public domain in the United States and instructs readers elsewhere to check local law. This is not a worldwide rights clearance or legal opinion.

The JSONL corpus is generated from the source using:

```powershell
cd apps/api
python -m app.scripts.ingest_gutenberg_2388
```

Use `--download` to fetch the source again. The generated `manifest.json` records its SHA-256 digest and source metadata. The app uses this chapter-level text only to improve retrieval of Sanskrit verse candidates; it does not display these passages as citations or claim that they align to individual verses. This poetic translation is only an English prototype source; it is not a substitute for a Sanskrit edition, a reviewed Hindi translation, or a verse-aligned critical text. Hindi queries are translated locally for search, not against a Hindi scripture corpus.
