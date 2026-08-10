# pdf-tools

A one-page website: pick some files, get back a single compressed PDF where every
page is A4.

Throw in PDFs, photos, text files, code, CSV, HTML, even a video. PDFs get
compressed and rescaled to A4 if they came as Letter or A3; everything else is
turned into pages first. They're merged in the order you picked them, compressed,
and the finished PDF downloads itself. Nothing is kept on the server.

The slider is just dpi — 10 to 300, default 100. No image is kept sharper than
that for the size it appears at. 300 is print quality, 150 is comfortable, 100
looks fine on screen. If compressing can't beat the original, you get the original
back instead.

## Running it

You need Python 3.10 or newer.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python app.py --port 8080
```

That's it — open the address it prints. `--port` defaults to 5000, and
`--host 0.0.0.0` makes it reachable from other machines.

To leave it running properly, put it behind gunicorn with a long timeout, because
compressing is slow on a Pi:

```sh
pip install gunicorn
gunicorn -w 1 -b 0.0.0.0:8080 --timeout 600 app:app
```

Stick to **one worker** on a 1 GB machine — each request in flight needs the memory
described below. Start it from the project folder so `config.py` is found.

## ffmpeg (optional)

Everything above works without it. If you install it:

```sh
sudo apt install ffmpeg
```

you also get HEIC, AVIF and RAW photos from phones and cameras, plus video files,
which turn into a page holding nine frames from across the clip. Without ffmpeg
those uploads are politely refused and nothing else changes.

## What you can upload

| Kind | Extensions | Needs |
| --- | --- | --- |
| PDF | `.pdf` | — |
| Images | `.png .jpg .jpeg .gif .bmp .tif .tiff .webp .ppm .pgm .tga .ico .jfif .jpe` | — |
| Text & code | `.txt .md .rst .log .csv .tsv .json .yaml .toml .ini .cfg .conf .env .py .js .ts .jsx .tsx .java .c .h .cpp .hpp .cs .go .rs .rb .php .sh .sql .xml .svg .css .scss .tex .srt .vtt` | — |
| HTML | `.html .htm` | — |
| Camera photos | `.heic .heif .avif .jxl .jp2 .j2k .dng .cr2 .nef .arw` | ffmpeg |
| Video | `.mp4 .mov .m4v .avi .mkv .webm .mpg .mpeg .wmv .flv` | ffmpeg |

Word, Excel and PowerPoint files aren't supported — that would mean installing all
of LibreOffice. Export them to PDF first. Password-protected PDFs are refused, and
empty files in a batch are skipped and mentioned in the result.

Text pages use Courier for plain Latin text and Cascadia Mono, which comes with the
`pymupdf-fonts` package, for anything needing Greek, Cyrillic, Arabic or Hebrew. No
system fonts are involved and there's nothing to configure. Chinese, Japanese,
Korean and emoji aren't covered by either font, so they come out as `?` and the
page tells you.

## Memory

`MAX_UPLOAD_MB` is 120 because of this. Worst case measured — a pile of different
image-heavy PDFs at 300 dpi:

| Upload | Peak memory |
| --- | --- |
| 40 MB | 385 MB |
| 80 MB | 500 MB |
| 120 MB | 700 MB |
| 200 MB | 861 MB |

Roughly 250 MB plus 3 MB per MB uploaded, so 120 MB stays inside a 1 GB budget.
Normal uploads at the default dpi use about half of that. Only raise the cap if the
machine has more RAM.

## Settings

They're all in [config.py](config.py) with a comment each, and any of them can be
set as an environment variable instead:

```sh
MAX_UPLOAD_MB=60 DPI_DEFAULT=150 python app.py --port 8080
```

The useful ones: `MAX_UPLOAD_MB`, `MAX_FILES`, `DPI_DEFAULT`, `JPEG_QUALITY`,
`PAGE_SIZE` (`letter`, `a5`, …) and `ALLOW_LANDSCAPE` (set it to `0` if you want
every page upright, even wide ones).

## Layout of the code

```
app.py                     Flask routes and the --port command line
config.py                  every setting
templates/, static/        the single page
pdf_tools/
  pipeline.py              dispatch -> resize to A4 -> merge -> compress
  compress.py              image downsampling, font subsetting, saving
  layout.py                page geometry, and keeping links intact when resizing
  imaging.py               decode any bitmap, place it on a page
  fonts.py                 the two fonts, and line wrapping
  quality.py               the dpi slider
  externals.py             finding ffmpeg, and calling it
  memory.py                purging MuPDF's page cache
  converters/              one module per format, plus the registry
```

`pipeline.py` doesn't know about any format. It asks the registry which converter
claims a file extension and lets it add pages. To support something new, write a
`Converter` subclass in `converters/`, list its extensions, and add it to
`REGISTRY`. If two converters claim the same extension the app refuses to start.

## Known limits

- No OCR — a scanned PDF gets compressed, not read.
- Arabic and Hebrew letters aren't joined or reordered right-to-left, though the
  text is still searchable.
- A video becomes one page of sampled frames, not every frame.
- Resizing a page to A4 keeps its text and links but loses comments, highlights and
  form fields. Pages already A4 are left completely alone.
- 1-bit scans and images with transparency are left as they are; re-encoding them
  would make them bigger or lose their masks.
