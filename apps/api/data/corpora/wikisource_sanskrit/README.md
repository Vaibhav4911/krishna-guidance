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

After setting `OPENAI_API_KEY`, create the semantic index (stop the API first
when using the local embedded Qdrant store):

```powershell
python -m app.scripts.ingest_sanskrit_embeddings
```

This creates multilingual OpenAI embeddings for the original Sanskrit text and
stores them in local Qdrant. Use `--replace` only to intentionally rebuild an
existing collection. Chat sends user messages and retrieved Sanskrit excerpts
to OpenAI for embedding and generation; use `QDRANT_URL` and `QDRANT_API_KEY`
to configure a Qdrant server instead of the local store.

## Attribution and reuse

Wikimedia contributor text is generally made available under CC BY-SA 4.0
unless a page states otherwise. Review the
[Wikimedia Terms of Use](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use)
and the linked page histories before redistribution. Attribute Sanskrit
Wikisource contributors, link to the applicable source revision, identify
changes, and distribute adapted versions under the applicable share-alike
terms. This note is provenance guidance, not legal advice or a jurisdictional
rights clearance.
