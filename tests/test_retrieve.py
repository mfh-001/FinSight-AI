from finsight.ingest import Document, Page
from finsight.retrieve import BM25, Hit, Retriever, rrf, tokenize


def docs():
    return [
        Document(
            "a.pdf",
            [
                Page("a.pdf", 1, "cover page of the annual report"),
                Page("a.pdf", 2, "total net sales 383,285 operating income 114,301"),
                Page("a.pdf", 3, "risk factors supply chain disruption"),
            ],
        ),
        Document("b.pdf", [Page("b.pdf", 1, "invoice number 42 total due 900")]),
    ]


def test_tokenize_joins_thousands():
    assert "383285" in tokenize("Net sales were $383,285 million")
    assert "the" not in tokenize("the revenue")


def test_bm25_finds_number_and_term():
    bm = BM25([p for d in docs() for p in d.pages])
    assert bm.search("net sales")[0].page == 2
    assert bm.search("383285")[0].key == ("a.pdf", 2)
    assert bm.search("supply chain")[0].key == ("a.pdf", 3)


def test_bm25_no_match_is_empty():
    bm = BM25([p for d in docs() for p in d.pages])
    assert bm.search("zebra") == []


def test_rrf_prefers_pages_in_both_lists():
    a = [Hit("d", 1, 9), Hit("d", 2, 8), Hit("d", 3, 7)]
    b = [Hit("d", 3, 5), Hit("d", 2, 4)]
    fused = rrf([a, b])
    assert {h.page for h in fused} == {1, 2, 3}
    assert fused[-1].page == 1


def test_retriever_with_fake_visual():
    class Fake:
        def search(self, query, pages, k):
            return [Hit("b.pdf", 1, 1.0)]

    r = Retriever(docs(), visual=Fake())
    keys = [h.key for h in r.search("net sales", k=3)]
    assert ("a.pdf", 2) in keys and ("b.pdf", 1) in keys
    assert r.page("b.pdf", 1).number == 1
