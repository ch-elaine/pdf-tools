# pdf-tools

One page, one button. Upload a pile of files — get back a single compressed PDF,
every page A4.

- **PDFs** are compressed and rescaled to A4 if they arrive as Letter, A3 or
  anything else. Text stays selectable and hyperlinks keep working.
- **Anything else** (photos, text, code, CSV, HTML, video) becomes pages, merged
  in the order you picked the files, then compressed the same way.
- The result downloads straight back to the browser. Nothing is kept afterwards.

The **quality slider is the dpi**, 10–300, default 100: no image is kept at more
than that many dots per inch for the size it appears on the page. 300 is print
quality, 150 is comfortable, 100 is fine on screen. If compression cannot beat the
original, the original comes back untouched.

## Install and run

Needs Python 3.10+.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python app.py --port 8080          # or just: python app.py
```

`--port` / `-p`, `--host` and `--debug` are all optional; defaults come from
[config.py](config.py). Use `--host 0.0.0.0` to reach it from other machines.

For a long-running server, use a real WSGI server with a generous timeout —
compression is CPU-bound and a Raspberry Pi is not fast:

```sh
pip install gunicorn
gunicorn -w 1 -b 0.0.0.0:8080 --timeout 600 app:app
```

**One worker** on a 1 GB machine: each concurrent request pays the full memory
cost (see below). Run it from the project directory, or add `--chdir`.

## Optional: ffmpeg

Everything works without it. Install `ffmpeg` (`sudo apt install ffmpeg`) to also
accept HEIC/HEIF/AVIF/JXL/JP2 and RAW photos, and video files, which become a 3×3
contact sheet of frames. Without it those uploads are refused with a message
saying so; every other format is unaffected.

ffmpeg is found on `PATH` — no install location is hard-coded. `FFMPEG_BIN` points
at a specific binary if you need that.

## Supported formats

| Kind | Extensions | Needs |
| --- | --- | --- |
| PDF | `.pdf` | — |
| Images | `.png .jpg .jpeg .gif .bmp .tif .tiff .webp .ppm .pgm .tga .ico .jfif .jpe` | — |
| Text & code | `.txt .md .rst .log .csv .tsv .json .yaml .toml .ini .cfg .conf .env .py .js .ts .jsx .tsx .java .c .h .cpp .hpp .cs .go .rs .rb .php .sh .sql .xml .svg .css .scss .tex .srt .vtt` | — |
| HTML | `.html .htm` | — |
| Camera photos | `.heic .heif .avif .jxl .jp2 .j2k .dng .cr2 .nef .arw` | ffmpeg |
| Video | `.mp4 .mov .m4v .avi .mkv .webm .mpg .mpeg .wmv .flv` | ffmpeg |

Office documents are **not** supported — converting them would mean installing
LibreOffice. Export them to PDF first. Password-protected PDFs are refused; empty
files in a batch are skipped and reported.

Fonts come from the `pymupdf-fonts` package, so no system fonts are needed. Plain
Latin text uses built-in Courier; anything else embeds Cascadia Mono, which covers
Greek, Cyrillic, Arabic, Hebrew and box drawing. Characters no font has (CJK,
emoji) become `?` and the page says so — point `TEXT_FONT` at a `.ttf` if you need
those scripts.

## Memory

Peak memory is the reason `MAX_UPLOAD_MB` is 120. Measured worst case (many
different image-heavy PDFs at 300 dpi):

| Upload | Peak RSS |
| --- | --- |
| 40 MB | 385 MB |
| 80 MB | 500 MB |
| 120 MB | 700 MB |
| 200 MB | 861 MB |

So roughly **250 MB + 3 MB per MB uploaded**, which keeps a 120 MB upload inside a
1 GB budget. Ordinary uploads at the default dpi use about half as much. Raise the
cap only with more RAM, and remember one worker means one of these at a time.

## Configuration

Everything lives in [config.py](config.py), and every value can be overridden by
an environment variable of the same name:

```sh
MAX_UPLOAD_MB=60 DPI_DEFAULT=150 python app.py --port 8080
```

The ones worth knowing: `MAX_UPLOAD_MB`, `MAX_FILES`, `DPI_MIN`/`DPI_MAX`/
`DPI_DEFAULT`, `JPEG_QUALITY`, `PAGE_SIZE` (any name PyMuPDF knows, e.g. `letter`),
`ALLOW_LANDSCAPE` (set `0` to force every page upright), and `TEXT_FONT`.

## How it is organised

```
app.py                     Flask routes and the --port command line
config.py                  every setting
templates/, static/        the single page
pdf_tools/
  pipeline.py              dispatch -> resize to A4 -> merge -> compress
  compress.py              image downsampling, font subsetting, saving
  layout.py                page geometry, and keeping links intact when resizing
  imaging.py               decode any bitmap, place it on a page
  fonts.py                 font choice and line wrapping
  quality.py               the dpi slider
  externals.py             finding ffmpeg, and calling it
  memory.py                purging MuPDF's page cache
  converters/              one module per format, plus the registry
```

`pipeline.py` knows nothing about formats: it asks the registry which converter
claims a file extension and lets it append pages. To add a format, add a
`Converter` subclass in `converters/` declaring its `extensions`, and list it in
`REGISTRY`. Two converters claiming the same extension is a startup error.

## Limitations

- **No OCR.** A scanned PDF is compressed, not read.
- **Arabic and Hebrew are not shaped.** The glyphs embed and stay searchable, but
  letters are not joined or reordered right-to-left.
- **Video becomes one page** of sampled frames, not every frame.
- Resizing a page to A4 keeps text and links but drops other annotations
  (comments, highlights, form fields). Pages already A4 are left untouched.
- 1-bit scans and images with transparency are left as they are; re-encoding them
  would make them bigger or lose their masks.
