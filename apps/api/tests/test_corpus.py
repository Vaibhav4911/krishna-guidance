from pathlib import Path

from app.schemas import ChatMessageRequest
from app.services.corpus_service import (
    load_passages,
    parse_gutenberg_text,
    retrieve_related_passages,
)
from app.services.sanskrit_corpus import (
    EXPECTED_VERSE_COUNTS,
    load_sanskrit_verses,
    parse_chapter_wikitext,
)


CORPUS_DIR = Path(__file__).resolve().parents[1] / "data" / "corpora" / "edwin_arnold"


def test_source_and_ingested_corpus_cover_all_chapters_without_verse_numbers():
    source_text = (CORPUS_DIR / "pg2388.txt").read_text(encoding="utf-8-sig")
    parsed_passages = parse_gutenberg_text(source_text)
    ingested_passages = load_passages()

    assert len(parsed_passages) == len(ingested_passages)
    assert {passage.chapter for passage in ingested_passages} == set(range(1, 19))
    assert all(passage.verse is None for passage in ingested_passages)
    assert all(passage.text.strip() for passage in ingested_passages)


def test_retrieval_returns_exact_chapter_level_source_passage():
    citations = retrieve_related_passages("Duryodhana")

    assert citations
    assert citations[0].chapter == 1
    assert citations[0].verse is None
    assert citations[0].source == "Project Gutenberg eBook #2388"
    assert citations[0].quote


def test_modern_work_and_results_query_finds_chapter_two_translation_passage():
    citations = retrieve_related_passages(
        "I am worried about the results of my work",
        limit=8,
    )

    assert 2 in {citation.chapter for citation in citations}


def test_unmatched_query_does_not_receive_a_scripture_citation():
    assert retrieve_related_passages("qzxvplmnonexistent") == []


def test_daily_wisdom_returns_sanskrit_verse_source(test_context):
    client, _ = test_context

    response = client.get("/api/v1/daily-wisdom")

    assert response.status_code == 200
    passage = response.json()["passage"]
    assert passage["chapter"] in range(1, 19)
    assert passage["verse"] in range(
        1, EXPECTED_VERSE_COUNTS[passage["chapter"] - 1] + 1
    )
    assert passage["language"] == "sa"
    assert passage["source_url"].startswith("https://sa.wikisource.org/")
    assert passage["quote"].endswith("॥")


def test_sanskrit_corpus_has_all_sequential_source_verses():
    verses = load_sanskrit_verses()

    assert len(verses) == 700
    assert [(verse.chapter, verse.verse) for verse in verses] == [
        (chapter, verse_number)
        for chapter, verse_count in enumerate(EXPECTED_VERSE_COUNTS, start=1)
        for verse_number in range(1, verse_count + 1)
    ]
    assert all(verse.language == "sa" and verse.text.endswith("॥") for verse in verses)
    verse_2_47 = next(
        verse for verse in verses if (verse.chapter, verse.verse) == (2, 47)
    )
    assert verse_2_47.text == (
        "कर्मण्येवाधिकारस्ते मा फलेषु कदाचन । "
        "मा कर्मफलहेतुर्भूर्मा ते सङ्गोऽस्त्वकर्मणि ॥"
    )


def test_sanskrit_parser_extracts_only_numbered_poem_verses():
    devanagari_digits = str.maketrans("0123456789", "०१२३४५६७८९")
    verses_text = "\n".join(
        (
            "अध्यायः",
            "धृतराष्ट्र उवाच",
            *(
                "धर्मक्षेत्रे कुरुक्षेत्रे नमुना श्लोकः "
                f"॥१-{str(verse_number).translate(devanagari_digits)}॥"
                for verse_number in range(1, 48)
            ),
        )
    )
    wikitext = (
        f"<poem>{verses_text}</poem>"
        "व्याख्या: ॥१-१॥ commentary is not part of the verse."
    )

    verses = parse_chapter_wikitext(
        wikitext,
        expected_chapter=1,
        source_url="https://sa.wikisource.org/wiki/test?oldid=1",
        revision_id=1,
    )

    assert len(verses) == 47
    assert verses[0].chapter == 1
    assert verses[0].verse == 1
    assert "commentary" not in verses[0].text
    assert "धृतराष्ट्र उवाच" not in verses[0].text
    assert verses[0].text.startswith("धर्मक्षेत्रे कुरुक्षेत्रे")
