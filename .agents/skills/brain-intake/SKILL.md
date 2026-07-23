---
name: brain-intake
description: Import and extract PDF, DOCX, XLSX, or TXT material into Main Brain with immutable provenance. Use when files are dropped for journals, notes, references, quotes, books, or lessons.
---

# Brain Intake

Version: `1.0.0`

1. Run `python -m main_brain ingest "<source>"`.
2. Report duplicate status, SHA-256, warnings, and the intake path.
3. Read the extraction and propose categorized derived notes with source links.
4. Leave derived notes as proposals until review.
5. Retain the immutable original and extraction artifact.
6. Flag image-only, encrypted, or unreadable files; do not invent OCR output.

