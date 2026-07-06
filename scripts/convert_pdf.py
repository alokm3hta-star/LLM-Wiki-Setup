"""Convert a PDF to Markdown using pymupdf4llm. Writes result to stdout."""
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 convert_pdf.py <path-to-pdf>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]

    try:
        import pymupdf4llm
    except ImportError:
        print(
            "ERROR: pymupdf4llm is not installed. Run: pip install pymupdf4llm",
            file=sys.stderr,
        )
        sys.exit(2)

    md = pymupdf4llm.to_markdown(path)
    print(md)


if __name__ == "__main__":
    main()
