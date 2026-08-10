# pdf-tools

One page, one button. Upload a pile of files — get back a single compressed PDF.

- **PDFs** are compressed: oversized images are downsampled and re-encoded, fonts
  are subset, streams are deflated, the cross-reference table is cleaned.
- **Anything else** (photos, text, code, CSV, HTML, Office docs, video) is first
  turned into pages, then merged with the PDFs in the order you picked the files,
  then compressed the same way.
- The finished PDF downloads straight back to the browser. Uploads are held in
  memory; the `ffmpeg` and LibreOffice steps use a temporary directory that is
  deleted as soon as they finish, so nothing survives the response.

Quality presets, chosen on the page:

| Preset | Image detail | Good for |
| --- | --- | --- |
| High | 300 dpi, JPEG q88 | archiving, reprinting |
| Balanced | 150 dpi, JPEG q80 | everyday documents, printing |
| Small | 110 dpi, JPEG q68 | email and screen reading (default) |

If compression cannot beat the original, the original is returned untouched — a
file never grows by passing through.

## Requirements

**Python 3.10+** and three pip packages (`Flask`, `PyMuPDF`, `Pillow`). That is
the whole base install: compressing PDFs, converting images, text and HTML needs
**no external programs at all**.

### Optional external tools

Everything below is opt-in. Without a tool, the formats that need it are refused
with a message naming what to install; every other format keeps working.

| Tool | Enables | Install (Debian / Raspberry Pi OS) |
| --- | --- | --- |
| `ffmpeg` | HEIC/HEIF/AVIF/JXL/JP2 and RAW photos (`.dng`, `.cr2`, `.nef`, `.arw`), plus video → a 3×3 contact sheet of frames | `sudo apt install ffmpeg` |
| `libreoffice` | Word, Excel, PowerPoint, OpenDocument, RTF, EPUB | `sudo apt install libreoffice --no-install-recommends` |

Tools are found on `PATH` — no install locations are hard-coded. To point at a
specific binary instead, set `FFMPEG_BIN` or `SOFFICE_BIN`. `ffprobe` is used
when present (it ships with `ffmpeg`) to spread contact-sheet frames evenly
across a clip; without it, frames are sampled from the opening seconds.

LibreOffice is by far the heaviest addition (~400 MB, slow to start on a Pi). If
Office files are rare for you, skip it and export those to PDF yourself.

### Fonts for non-Latin text

Text files render with PyMuPDF's built-in Courier, which covers Latin-1 and needs
no font installed. Other scripts need a system font:

```sh
sudo apt install fonts-dejavu-core     # Cyrillic, Greek, Arabic letterforms, ~1 MB
sudo apt install fonts-noto-cjk        # Chinese, Japanese, Korean (large)
```

The search list is `UNICODE_FONT_CANDIDATES` in [pdf_tools/fonts.py](pdf_tools/fonts.py);
`TEXT_FONT=/path/to/font.ttf` overrides it without editing code. Characters no
available font can draw become `?`, and the response says so.

## Quick start

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py                      # http://127.0.0.1:5000
```

`HOST`, `PORT` and `DEBUG` are read from the environment.

## Supported formats

| Converter | Extensions | Needs |
| --- | --- | --- |
| pdf | `.pdf` | — |
| image | `.png .jpg .jpeg .jpe .jfif .gif .bmp .tif .tiff .webp .ppm .pgm .tga .ico` | — |
| text | `.txt .md .rst .log .csv .tsv .json .yaml .toml .ini .cfg .conf .env .py .js .ts .jsx .tsx .java .c .h .cpp .hpp .cs .go .rs .rb .php .sh .sql .xml .svg .css .scss .tex .srt .vtt` and friends | — |
| html | `.html .htm` | — |
| camera-image | `.heic .heif .avif .jxl .jp2 .j2k .dng .cr2 .nef .arw` | `ffmpeg` |
| video | `.mp4 .mov .m4v .avi .mkv .webm .mpg .mpeg .wmv .flv` | `ffmpeg` |
| office | `.doc .docx .odt .rtf .xls .xlsx .ods .ppt .pptx .odp .epub` | `libreoffice` |

Password-protected PDFs are refused (they cannot be re-saved without the
password). Empty files in a batch are skipped and reported.

## Running on a Raspberry Pi

- Use **64-bit** Raspberry Pi OS. PyMuPDF and Pillow then install from prebuilt
  `aarch64` wheels; on a 32-bit OS pip may try to compile them.
- Serve it with a real WSGI server and a long timeout — compression is CPU-bound
  and a Pi is not fast:

  ```sh
  pip install gunicorn
  gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 app:app
  ```

  Two workers suits a Pi 4/5; use one on a Pi Zero. Add a systemd unit to start
  it at boot.
- **Memory** is the real limit, not CPU. Peak usage is a few times the size of
  the largest single file, because pages are held in memory. `MAX_UPLOAD_MB` and
  `MAX_FILES` at the top of [app.py](app.py) are set to 500 MB / 100 files;
  on a 1–2 GB Pi, lower `MAX_UPLOAD_MB` to something like 100.
- The upload cap is enforced by Flask; if you put nginx in front, raise its
  `client_max_body_size` to match or it will reject large uploads first.

## Configuration

| Setting | Where | Default |
| --- | --- | --- |
| `HOST`, `PORT`, `DEBUG` | environment | `127.0.0.1`, `5000`, off |
| `MAX_UPLOAD_MB`, `MAX_FILES` | [app.py](app.py) | 500, 100 |
| `FFMPEG_BIN`, `SOFFICE_BIN` | environment | found on `PATH` |
| `TEXT_FONT` | environment | first font in `UNICODE_FONT_CANDIDATES` |
| Quality presets | [pdf_tools/quality.py](pdf_tools/quality.py) | see table above |

## How it is organised

```
app.py                     Flask routes: upload in, PDF out
templates/index.html       the single page
static/style.css, app.js   styling and the upload/download logic
pdf_tools/
  pipeline.py              the one pipeline: dispatch -> merge -> compress
  compress.py              image downsampling, font subsetting, saving
  quality.py               the quality presets
  imaging.py               decode any bitmap, place it on a page
  fonts.py                 font choice and line wrapping for text pages
  externals.py             optional tool discovery (PATH only) and ffmpeg calls
  errors.py                ProcessingError - messages shown to the user
  converters/
    base.py                the Converter contract (Upload, Context)
    __init__.py            extension -> converter registry
    pdf_doc.py image.py text.py html.py video.py office.py
```

`pipeline.py` knows nothing about formats: it asks the registry which converter
claims a file extension, hands it the upload, and lets it append pages.

### Adding a format

1. Add `pdf_tools/converters/yourformat.py` with a `Converter` subclass that
   declares `extensions` (and `requires`, if it needs an external tool) and
   implements `add_pages(doc, upload, ctx)`.
2. List the class in `REGISTRY` in `pdf_tools/converters/__init__.py`.

Nothing else changes: the upload form's `accept` list, the registry and the
compression stage all follow automatically. Two converters claiming the same
extension is a startup error rather than a silent surprise.

## Limitations

- **No OCR.** A scanned PDF stays a picture of text; it is compressed, not read.
- **Right-to-left shaping.** Arabic and Hebrew glyphs embed and are searchable,
  but letters are not joined or reordered — for polished RTL output, convert to
  PDF in a word processor first.
- **Video becomes one page** of sampled frames, not every frame.
- **Bitonal (1-bit) scans are left alone**; their existing encoding already beats
  JPEG.
- Images with transparency inside an existing PDF are not re-encoded, so their
  masks survive intact.
