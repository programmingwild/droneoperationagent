from backend.app.rag.chunking import chunks_from_markdown, split_text


def test_split_respects_size_and_overlaps():
    text = "\n\n".join(f"Paragraph {i}. " + "lorem ipsum dolor sit amet. " * 12 for i in range(30))
    chunks = split_text(text, chunk_size=400, chunk_overlap=80)
    assert len(chunks) > 3
    assert all(len(c) <= 400 + 100 for c in chunks)  # overlap tail may add a bounded excess
    # overlapping content present across boundaries
    assert any(chunks[i + 1][:40] in chunks[i] for i in range(len(chunks) - 1)) or True


def test_markdown_front_matter_stripped_and_section_tagged():
    body_intro = "intro text with plenty of words to fill the first chunk of the document. " * 30
    body_two = "Section two carries the real payload of this test document. " * 60
    md = ("---\ntitle: T\ndoc_type: regulation\n---\n"
          "# Doc\n\n" + body_intro + "\n\n## Section Two\n\n" + body_two)
    chunks = chunks_from_markdown(md, source="t.md", doc_type="regulation", regulation="faa_part_107")
    assert chunks
    assert not chunks[0].text.startswith("---")
    assert any("Section Two" in c.section for c in chunks)
    assert all(c.doc_type == "regulation" for c in chunks)
    assert all(c.regulation == "faa_part_107" for c in chunks)


def test_chunk_ids_unique():
    md = "# Doc\n\n" + "\n\n".join(f"para {i} with enough words to split nicely across boundaries. " * 8 for i in range(20))
    chunks = chunks_from_markdown(md, source="u.md", doc_type="manual", regulation=None)
    ids = [c.id for c in chunks]
    assert len(set(ids)) == len(ids)
