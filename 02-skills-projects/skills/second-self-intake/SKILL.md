---
name: second-self-intake
description: Import and extract PDF, DOCX, XLSX, or TXT material into Second Self with immutable provenance. Use when files are dropped for journals, notes, references, quotes, books, or lessons.
---

# Second Self Intake

Version: `1.0.0`

1. Run `python -m second_self ingest "<source>"`.
2. Report duplicate status, SHA-256, warnings, and the intake path.
3. Read the extraction and propose categorized derived notes with source links.
4. Leave derived notes as proposals until review.
5. Retain the immutable original and extraction artifact.
6. Flag image-only, encrypted, or unreadable files; do not invent OCR output.

