# ESP32 Corpus Inventory

This repository currently indexes three local Espressif PDF files from `data/`.
The files were inventoried on 2026-08-12. Their exact bytes are identified by
SHA-256 in `benchmarks/esp32-retrieval-v1/corpus.json`.

## Important version distinction

The documents were reached through the ESP-IDF v4.3
[ESP32 Hardware Reference](https://docs.espressif.com/projects/esp-idf/en/v4.3/esp32/hw-reference/index.html),
but the linked PDF URLs are rolling Espressif download URLs. The local corpus is
therefore **not an ESP-IDF v4.3 documentation snapshot**.

| Local file | Document | Local edition | PDF pages | Canonical source |
| --- | --- | ---: | ---: | --- |
| `data/esp32_datasheet_en.pdf` | ESP32 Series Datasheet | v5.3, 2026.07 | 78 | [Espressif PDF](https://www.espressif.com/documentation/esp32_datasheet_en.pdf) |
| `data/esp32_technical_reference_manual_en.pdf` | ESP32 Technical Reference Manual | v5.8 | 784 | [Espressif PDF](https://www.espressif.com/documentation/esp32_technical_reference_manual_en.pdf) |
| `data/esp-chip-errata-en-master-esp32.pdf` | ESP32 Series SoC Errata | v3.0, 2025-10-11 | 36 | [Espressif PDF](https://docs.espressif.com/projects/esp-chip-errata/en/latest/esp32/esp-chip-errata-en-master-esp32.pdf) |

The dates above come from each document's cover or revision history, not from
filesystem timestamps. PDF creation metadata describes when a particular PDF
was generated and is not treated as the publication version.

## Page numbering

Ground-truth evidence uses `pdf_page`, the one-based physical page number used
by the ingestion pipeline and PDF viewers. For these three editions, numbered
body pages generally agree with the printed footer, but front matter may use
Roman numerals or no printed page number. A human-readable `section` and a text
anchor accompany every page label so a version change cannot silently validate
against unrelated content.

## Reproducibility rules

- Treat `corpus.json` as the corpus lock file for benchmark v1.
- A changed file hash creates a new corpus revision and requires evidence-label
  validation; do not silently replace the PDF under the same benchmark result.
- Keep source provenance separate from the retrieval database. SQLite and FAISS
  are generated artifacts; the versioned JSON files are the inspectable ground
  truth.
- Do not use random chunk IDs as labels. Chunk boundaries can change while the
  source document, page, section, and quoted evidence remain stable.

## Current scope gaps

The v4.3 Hardware Reference page also links hardware design guidelines, module
and board datasheets, and other documents that are not present in `data/`.
Questions requiring those sources must be marked `unanswerable` for this corpus,
not counted as retrieval failures.
