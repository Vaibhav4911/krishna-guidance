# Sanskrit Bhagavad Gita corpus

This corpus contains the original Sanskrit mūlapāṭha transcribed from the 18
chapter pages linked by the [Sanskrit Wikisource Bhagavad Gita index](https://sa.wikisource.org/wiki/भगवद्गीता).
The ingestion script extracts verse text only from `<poem>` blocks; commentary
outside those blocks is not ingested.

- Language: Sanskrit (`sa`)
- Granularity: chapter and verse
- Expected total: 700 verses, checked against the standard chapter counts
- Source metadata: each verse has a revision-specific Wikisource URL; the
  manifest stores revision IDs, timestamps, and a SHA-256 hash of each source
  page's wikitext
- Scope limitation: this is a contributor-transcribed source, not an
  independently reviewed critical edition. Compare against a scholarly edition
  before treating it as definitive.

Regenerate the corpus from the API directory:

```powershell
cd apps/api
python -m app.scripts.ingest_wikisource_sanskrit
```

The script follows redirects, extracts only verse blocks, and fails rather
than writing the corpus if any chapter has a missing, duplicated, or
out-of-sequence verse marker. It retries Wikimedia API rate limits and writes
the corpus and manifest only after validating all 18 chapters.

For local development, install Ollama and download BGE-M3:

```cmd
ollama pull bge-m3
```

Set `LLM_PROVIDER=ollama`,
`LLM_EMBEDDINGS_BASE_URL=http://127.0.0.1:11434`, and
`LLM_EMBEDDING_MODEL=bge-m3` in `apps/api/.env`, then create the index:

```cmd
cd apps\api
python -m app.scripts.ingest_sanskrit_embeddings
```

This creates multilingual BGE-M3 embeddings for the original Sanskrit text and
stores them in local Qdrant. Use `--replace` only to intentionally rebuild an
existing collection. No paid model API is used. Hosted deployments can replace
Ollama with private self-hosted inference endpoints and configure
`QDRANT_URL`/`QDRANT_API_KEY` for a Qdrant server. Protect inference endpoints
so only the API server can access them.

## Attribution and reuse

Wikimedia contributor text is generally made available under CC BY-SA 4.0
unless a page states otherwise. Review the
[Wikimedia Terms of Use](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use)
and the linked page histories before redistribution. Attribute Sanskrit
Wikisource contributors, link to the applicable source revision, identify
changes, and distribute adapted versions under the applicable share-alike
terms. This note is provenance guidance, not legal advice or a jurisdictional
rights clearance.
