# Task 03 — Processor Step 2: PDF Text Extraction

## Goal

Implement the PDF text extraction layer. Provide two adapters behind a common interface, switchable via `PDF_ENGINE` env var. Wire Step 2 into the `Processor`.

---

## Deliverables

| File | Purpose |
|------|---------|
| `app/pdf/base.py` | `BasePdfExtractor` abstract class |
| `app/pdf/pdfplumber_adapter.py` | Extracts text using `pdfplumber` |
| `app/pdf/pymupdf_adapter.py` | Extracts text using `pymupdf` (fitz) |
| `app/pdf/factory.py` | `PdfExtractorFactory.create(settings)` |
| `app/processor/processor.py` | Step 2 wired in |
| `tests/unit/test_pdfplumber_adapter.py` | Unit tests |
| `tests/unit/test_pymupdf_adapter.py` | Unit tests |
| `tests/unit/test_pdf_factory.py` | Factory unit tests |

---

## Step-by-Step Implementation

### 1. `app/pdf/base.py`

```python
from abc import ABC, abstractmethod

class BasePdfExtractor(ABC):
    """Contract for all PDF text extraction adapters."""

    @abstractmethod
    def extract(self, pdf_bytes: bytes) -> str:
        """Extract plain text from PDF bytes.

        Args:
            pdf_bytes: Raw PDF file content.

        Returns:
            Extracted text as a single normalized string.

        Raises:
            PdfExtractionError: if extraction fails for any reason.
        """
```

Add `PdfExtractionError(Exception)` in `app/pdf/exceptions.py`.

### 2. `app/pdf/pdfplumber_adapter.py`

```python
import io
import pdfplumber

class PdfPlumberAdapter(BasePdfExtractor):
    """Extracts text from PDF using pdfplumber."""

    def extract(self, pdf_bytes: bytes) -> str:
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
            return "\n".join(pages).strip()
        except Exception as exc:
            raise PdfExtractionError(f"pdfplumber extraction failed: {exc}") from exc
```

### 3. `app/pdf/pymupdf_adapter.py`

```python
import io
import fitz  # pymupdf

class PyMuPdfAdapter(BasePdfExtractor):
    """Extracts text from PDF using PyMuPDF."""

    def extract(self, pdf_bytes: bytes) -> str:
        try:
            doc = fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
            pages = [page.get_text() for page in doc]
            return "\n".join(pages).strip()
        except Exception as exc:
            raise PdfExtractionError(f"pymupdf extraction failed: {exc}") from exc
```

### 4. `app/pdf/factory.py`

```python
class PdfExtractorFactory:
    """Creates the correct PDF extractor based on settings."""

    ADAPTERS: dict[str, type[BasePdfExtractor]] = {
        "pdfplumber": PdfPlumberAdapter,
        "pymupdf": PyMuPdfAdapter,
    }

    @classmethod
    def create(cls, settings: Settings) -> BasePdfExtractor:
        engine = settings.pdf_engine.lower()
        adapter_cls = cls.ADAPTERS.get(engine)
        if adapter_cls is None:
            raise ValueError(
                f"Unknown PDF engine '{engine}'. Choose from: {list(cls.ADAPTERS)}"
            )
        return adapter_cls()
```

### 5. Wire Step 2 in `app/processor/processor.py`

```python
def process(self, document_id: int, job_id: int) -> None:
    # Step 1: Load file
    document = self._doc_repo.find_by_id(document_id)
    raw_bytes = self._file_loader.load(document)

    # Step 2: Extract text
    extracted_text = self._pdf_extractor.extract(raw_bytes)

    # Steps 3–7: Not yet implemented
    raise NotImplementedError("Steps 3–7 not yet implemented")
```

---

## Output Normalization Rules

Both adapters must return text that:
- Uses `\n` as the page separator
- Has leading/trailing whitespace stripped
- Returns `""` (empty string) for empty or unreadable PDFs — never `None`
- Merges multiple consecutive blank lines into a single `\n\n` (optional but recommended)

---

## Tests

### `tests/unit/test_pdf_factory.py`

```python
def test_creates_pdfplumber_adapter():
    settings = Settings(pdf_engine="pdfplumber", ...)
    adapter = PdfExtractorFactory.create(settings)
    assert isinstance(adapter, PdfPlumberAdapter)

def test_creates_pymupdf_adapter():
    settings = Settings(pdf_engine="pymupdf", ...)
    adapter = PdfExtractorFactory.create(settings)
    assert isinstance(adapter, PyMuPdfAdapter)

def test_raises_for_unknown_engine():
    settings = Settings(pdf_engine="unknown", ...)
    with pytest.raises(ValueError, match="Unknown PDF engine"):
        PdfExtractorFactory.create(settings)
```

### `tests/unit/test_pdfplumber_adapter.py`

```python
def test_extract_returns_text(sample_pdf_bytes):
    adapter = PdfPlumberAdapter()
    result = adapter.extract(sample_pdf_bytes)
    assert isinstance(result, str)
    assert len(result) > 0

def test_extract_raises_on_invalid_bytes():
    adapter = PdfPlumberAdapter()
    with pytest.raises(PdfExtractionError):
        adapter.extract(b"not a pdf")
```

Use `conftest.py` to provide `sample_pdf_bytes` fixture — generate a minimal valid PDF with `reportlab` or embed a tiny base64-encoded PDF blob.

### `tests/unit/test_pymupdf_adapter.py`

Mirror tests of `test_pdfplumber_adapter.py` for `PyMuPdfAdapter`.

### Integration test fixture (conftest.py)

```python
MINIMAL_PDF = b"%PDF-1.4 ..."  # embed a real minimal PDF as bytes constant
```

Or use `reportlab` to generate a simple one-page PDF in the fixture.

---

## Notes

- Both adapters read from `bytes` (in-memory) — no temp files, no disk I/O in this layer
- If a page has no extractable text (scanned image), return `""` for that page rather than crashing
- Do not perform any filtering, anonymization, or normalization of the text — that's Steps 3–5

---

## Acceptance Criteria

- [ ] `make lint` passes
- [ ] `make test` — unit tests pass for both adapters and factory
- [ ] `PDF_ENGINE=pdfplumber` in `.env` → `PdfPlumberAdapter` is used
- [ ] `PDF_ENGINE=pymupdf` in `.env` → `PyMuPdfAdapter` is used
- [ ] Invalid engine name raises `ValueError` with a clear message
- [ ] Both adapters return `str` (never `None`) for any valid PDF input
- [ ] `PdfExtractionError` is raised for invalid/corrupt input
