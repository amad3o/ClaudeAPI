from markitdown import MarkItDown, StreamInfo
from io import BytesIO
from pathlib import Path
from pydantic import Field

# Leading bytes each supported format must start with (DOCX is a ZIP archive)
SUPPORTED_SIGNATURES = {"pdf": b"%PDF-", "docx": b"PK\x03\x04"}


def binary_document_to_markdown(binary_data: bytes, file_type: str) -> str:
    """Converts binary document data to markdown-formatted text."""
    md = MarkItDown()
    file_obj = BytesIO(binary_data)
    stream_info = StreamInfo(extension=file_type)
    result = md.convert(file_obj, stream_info=stream_info)
    return result.text_content


def document_path_to_markdown(
    file_path: str = Field(
        description="Absolute or relative path to a PDF (.pdf) or Word (.docx) file on the local filesystem"
    ),
) -> str:
    """Read a PDF or DOCX file from disk and convert its contents to markdown.

    Opens the file at the given path, checks that its extension is .pdf or
    .docx and that its contents really are that format, then converts it to
    markdown text. DOCX headings, lists, and tables become markdown syntax.
    PDF output is the extracted text with paragraph breaks; PDFs without a
    text layer (e.g. scanned images) produce empty output because no OCR is
    performed.

    When to use:
    - When you have a path to a PDF or DOCX file and need its text content
    - When you want a document's structure as markdown for reading or summarizing

    When not to use:
    - For other formats (.txt, .pptx, .xlsx, images); these raise an error
    - When you already have the file's bytes rather than a path

    Raises FileNotFoundError, IsADirectoryError, or PermissionError if the
    file cannot be read, and ValueError if the file type is unsupported, the
    file is empty, or its contents do not match its extension.

    Examples:
    >>> document_path_to_markdown("reports/overview.docx")
    '# Overview\\n\\nThe Model Context Protocol allows applications...'
    >>> document_path_to_markdown("/tmp/notes.pdf")
    'Overview\\n\\nThe Model Context Protocol allows applications...'
    """
    path = Path(file_path)
    file_type = path.suffix.lower().lstrip(".")
    if file_type not in SUPPORTED_SIGNATURES:
        raise ValueError(
            f"Unsupported file type for {file_path!r}; supported types: pdf, docx"
        )

    data = path.read_bytes()
    if not data:
        raise ValueError(f"File is empty: {file_path}")
    if not data.startswith(SUPPORTED_SIGNATURES[file_type]):
        raise ValueError(f"File contents are not a valid {file_type}: {file_path}")

    return binary_document_to_markdown(data, file_type)
