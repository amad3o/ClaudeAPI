import asyncio
import gc
import io
import os
import shutil
import sys
import warnings
import zipfile
from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from tools.document import binary_document_to_markdown, document_path_to_markdown


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
DOCX_FIXTURE = os.path.join(FIXTURES_DIR, "mcp_docs.docx")
PDF_FIXTURE = os.path.join(FIXTURES_DIR, "mcp_docs.pdf")

# Phrases present in both fixtures, used to check that content survived conversion
FIXTURE_PHRASES = [
    "Overview",
    "Model Context Protocol",
    "Key Features of this Python SDK",
    "MCP Primitives",
    "Prompts",
    "User-controlled",
]


def make_blank_docx() -> bytes:
    """Build a minimal valid DOCX with an empty body."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body/></w:document>",
        )
    return buf.getvalue()


def make_blank_pdf() -> bytes:
    """Build a minimal valid single-page PDF with no text."""
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objs) + 1,
        xref,
    )
    return out


class TestDocumentPathToMarkdownContent:
    def test_docx_preserves_markdown_structure(self):
        """DOCX headings, bullets, and tables become markdown."""
        result = document_path_to_markdown(DOCX_FIXTURE)

        assert "# Overview" in result
        assert "## Key Features of this Python SDK" in result
        assert "## MCP Primitives" in result
        assert "* Build MCP clients that can connect to any MCP server" in result
        assert "| --- |" in result

    def test_pdf_preserves_text_content(self):
        """PDF text is extracted (markitdown does not emit markdown syntax for PDFs)."""
        result = document_path_to_markdown(PDF_FIXTURE)

        for phrase in FIXTURE_PHRASES:
            assert phrase in result, f"Missing {phrase!r} in PDF output"

    @pytest.mark.parametrize("path", [DOCX_FIXTURE, PDF_FIXTURE])
    def test_returns_non_empty_string(self, path):
        result = document_path_to_markdown(path)

        assert isinstance(result, str)
        assert result.strip()

    @pytest.mark.parametrize(
        "path,file_type", [(DOCX_FIXTURE, "docx"), (PDF_FIXTURE, "pdf")]
    )
    def test_matches_binary_document_to_markdown(self, path, file_type):
        """The path-based tool must agree with the binary-based tool."""
        with open(path, "rb") as f:
            expected = binary_document_to_markdown(f.read(), file_type)

        assert document_path_to_markdown(path) == expected


class TestDocumentPathToMarkdownPaths:
    def test_relative_path(self, monkeypatch):
        expected = document_path_to_markdown(DOCX_FIXTURE)
        monkeypatch.chdir(FIXTURES_DIR)

        assert document_path_to_markdown("mcp_docs.docx") == expected

    def test_pathlib_path(self):
        expected = document_path_to_markdown(PDF_FIXTURE)

        assert document_path_to_markdown(Path(PDF_FIXTURE)) == expected

    @pytest.mark.parametrize(
        "fixture,name",
        [(DOCX_FIXTURE, "MCP_DOCS.DOCX"), (PDF_FIXTURE, "MCP_DOCS.PDF")],
    )
    def test_uppercase_extension(self, tmp_path, fixture, name):
        target = tmp_path / name
        shutil.copy(fixture, target)

        assert document_path_to_markdown(str(target)) == document_path_to_markdown(
            fixture
        )

    @pytest.mark.parametrize(
        "fixture,name",
        [
            (DOCX_FIXTURE, "my report.docx"),
            (PDF_FIXTURE, "my report.pdf"),
            (DOCX_FIXTURE, "résumé_文档.docx"),
            (PDF_FIXTURE, "résumé_文档.pdf"),
        ],
    )
    def test_spaces_and_unicode_in_path(self, tmp_path, fixture, name):
        folder = tmp_path / "folder with spaces"
        folder.mkdir()
        target = folder / name
        shutil.copy(fixture, target)

        assert document_path_to_markdown(str(target)) == document_path_to_markdown(
            fixture
        )


class TestDocumentPathToMarkdownFileType:
    @pytest.mark.parametrize("ext", ["txt", "pptx", "png", "xlsx"])
    def test_unsupported_extension_raises(self, tmp_path, ext):
        target = tmp_path / f"file.{ext}"
        target.write_bytes(b"some content")

        with pytest.raises(ValueError) as exc_info:
            document_path_to_markdown(str(target))

        message = str(exc_info.value).lower()
        assert "pdf" in message and "docx" in message

    def test_no_extension_raises(self, tmp_path):
        target = tmp_path / "document"
        shutil.copy(PDF_FIXTURE, target)

        with pytest.raises(ValueError):
            document_path_to_markdown(str(target))

    @pytest.mark.parametrize(
        "fixture,name",
        [(PDF_FIXTURE, "actually_pdf.docx"), (DOCX_FIXTURE, "actually_docx.pdf")],
    )
    def test_content_not_matching_extension_raises(self, tmp_path, fixture, name):
        target = tmp_path / name
        shutil.copy(fixture, target)

        with pytest.raises(ValueError):
            document_path_to_markdown(str(target))


class TestDocumentPathToMarkdownErrors:
    def test_missing_file_raises(self, tmp_path):
        missing = tmp_path / "missing.pdf"

        with pytest.raises(FileNotFoundError) as exc_info:
            document_path_to_markdown(str(missing))

        assert "missing.pdf" in str(exc_info.value)

    def test_directory_raises(self, tmp_path):
        folder = tmp_path / "folder.pdf"
        folder.mkdir()

        with pytest.raises(IsADirectoryError):
            document_path_to_markdown(str(folder))

    def test_empty_path_raises(self):
        with pytest.raises((FileNotFoundError, ValueError)):
            document_path_to_markdown("")

    @pytest.mark.parametrize("ext", ["pdf", "docx"])
    def test_empty_file_raises(self, tmp_path, ext):
        target = tmp_path / f"empty.{ext}"
        target.write_bytes(b"")

        with pytest.raises(ValueError):
            document_path_to_markdown(str(target))

    @pytest.mark.parametrize("ext", ["pdf", "docx"])
    def test_corrupt_file_raises(self, tmp_path, ext):
        """markitdown silently falls back to plain text for garbage, so the tool must reject it."""
        target = tmp_path / f"corrupt.{ext}"
        target.write_bytes(os.urandom(2048))

        with pytest.raises(ValueError):
            document_path_to_markdown(str(target))

    @pytest.mark.skipif(
        sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
        reason="File permissions are not enforced on Windows or for root",
    )
    def test_unreadable_file_raises(self, tmp_path):
        target = tmp_path / "locked.pdf"
        shutil.copy(PDF_FIXTURE, target)
        target.chmod(0o000)
        try:
            with pytest.raises(PermissionError):
                document_path_to_markdown(str(target))
        finally:
            target.chmod(0o644)


class TestDocumentPathToMarkdownEdgeCases:
    def test_blank_docx_returns_empty_string(self, tmp_path):
        target = tmp_path / "blank.docx"
        target.write_bytes(make_blank_docx())

        result = document_path_to_markdown(str(target))

        # markitdown renders an empty DOCX body as the literal "b''"
        assert result.strip() in ("", "b''")

    def test_blank_pdf_returns_empty_string(self, tmp_path):
        """Covers PDFs with no text layer (e.g. scanned images); there is no OCR."""
        target = tmp_path / "blank.pdf"
        target.write_bytes(make_blank_pdf())

        result = document_path_to_markdown(str(target))

        assert result.strip() == ""


class TestDocumentPathToMarkdownSideEffects:
    @pytest.mark.parametrize("fixture", [DOCX_FIXTURE, PDF_FIXTURE])
    def test_source_file_unchanged(self, tmp_path, fixture):
        target = tmp_path / os.path.basename(fixture)
        shutil.copy2(fixture, target)
        before_bytes = target.read_bytes()
        before_mtime = target.stat().st_mtime_ns

        document_path_to_markdown(str(target))

        assert target.read_bytes() == before_bytes
        assert target.stat().st_mtime_ns == before_mtime

    def test_no_file_handle_leaks(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ResourceWarning)
            for _ in range(20):
                document_path_to_markdown(DOCX_FIXTURE)
                document_path_to_markdown(PDF_FIXTURE)
            gc.collect()

        leaks = [w for w in caught if issubclass(w.category, ResourceWarning)]
        assert not leaks, f"Unclosed resources: {[str(w.message) for w in leaks]}"


class TestDocumentPathToMarkdownMCP:
    TOOL_NAME = "document_path_to_markdown"

    def get_tool(self):
        from main import mcp

        tools = asyncio.run(mcp.list_tools())
        matches = [t for t in tools if t.name == self.TOOL_NAME]
        assert matches, f"{self.TOOL_NAME} is not registered in main.py"
        return matches[0]

    def test_tool_is_registered(self):
        self.get_tool()

    def test_input_schema_has_described_string_path(self):
        schema = self.get_tool().inputSchema
        properties = schema["properties"]

        assert len(properties) == 1, "Expected a single path parameter"
        name, prop = next(iter(properties.items()))
        assert prop["type"] == "string"
        assert prop.get("description"), "Path parameter needs a Field description"
        assert name in schema.get("required", [])

    def test_description_follows_docstring_convention(self):
        description = self.get_tool().description

        assert description
        assert description.strip().splitlines()[0].strip()
        assert "When to use" in description
        assert ">>>" in description or "Example" in description

    def test_call_tool_end_to_end(self):
        from main import mcp

        schema = self.get_tool().inputSchema
        param = next(iter(schema["properties"]))

        result = asyncio.run(mcp.call_tool(self.TOOL_NAME, {param: DOCX_FIXTURE}))

        assert "# Overview" in result[0].text

    def test_call_tool_missing_file_raises_tool_error(self, tmp_path):
        from main import mcp

        schema = self.get_tool().inputSchema
        param = next(iter(schema["properties"]))

        with pytest.raises(ToolError):
            asyncio.run(
                mcp.call_tool(self.TOOL_NAME, {param: str(tmp_path / "missing.pdf")})
            )
