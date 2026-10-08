from finsight.answer import NOT_FOUND, answer_question, is_not_found, parse_citations
from finsight.config import Config
from finsight.ingest import Document, Page
from finsight.llm import MockBackend
from finsight.retrieve import Retriever


def retriever():
    return Retriever(
        [
            Document(
                "apple.pdf",
                [
                    Page("apple.pdf", 1, "cover"),
                    Page("apple.pdf", 2, "Total net sales 383,285 394,328\nNet income 96,995"),
                ],
            )
        ]
    )


def test_parse_citations():
    t = "Sales were 383,285 [apple.pdf p.2]. Also [a b.pdf p.3, p.5] and [x.pdf p. 7]."
    assert parse_citations(t) == [("apple.pdf", 2), ("a b.pdf", 3), ("a b.pdf", 5), ("x.pdf", 7)]
    assert parse_citations("no cites [1] here") == []


def test_not_found_detection():
    assert is_not_found("Not found in the documents.")
    assert not is_not_found("Sales were 5.")


def test_model_answer_keeps_valid_citation():
    b = MockBackend("Net sales were 383,285 million [apple.pdf p.2].")
    a = answer_question("What were total net sales?", retriever(), b, Config())
    assert a.found and a.citations == [("apple.pdf", 2)]
    assert "Pages:" in b.calls[0][1] and "[apple.pdf p.2]" in b.calls[0][1]


def test_invented_citation_is_dropped():
    b = MockBackend("Net sales were 383,285 [apple.pdf p.99].")
    a = answer_question("total net sales", retriever(), b, Config())
    assert a.citations == [("apple.pdf", 2)]
    assert "citation added" in a.text


def test_model_says_not_found():
    b = MockBackend("Not found in the documents.")
    a = answer_question("total net sales", retriever(), b, Config())
    assert not a.found and a.text == NOT_FOUND and a.citations == []


def test_no_hits_skips_model():
    b = MockBackend()
    a = answer_question("zebra", retriever(), b, Config())
    assert not a.found and a.mode == "empty" and b.calls == []


def test_retrieval_only_mode():
    a = answer_question("net income", retriever(), None, Config())
    assert a.mode == "retrieval-only" and "96,995" in a.text and a.citations == [("apple.pdf", 2)]


def test_retrieval_only_refuses_when_question_words_are_missing():
    a = answer_question("how many bitcoin does acme hold", retriever(), None, Config())
    assert not a.found and a.text == NOT_FOUND
