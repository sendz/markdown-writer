# Markdown Writer

Write Markdown directly inside LibreOffice Writer.

Markdown Writer is a LibreOffice extension (`.oxt`) that lets you author in
Markdown while working in Writer.

## Status

| Milestone | Feature                                              | State |
|-----------|------------------------------------------------------|-------|
| M0        | Extension scaffold, build/install scripts, About box | done  |
| M1        | Formatting commands (bold, headings, lists, ...)     | done  |
| M2        | Live auto-format while typing (Typora-like)          | done  |
| M3        | Markdown import/export helpers                       | done  |
| M4        | Source + preview panel                               | done  |
| M5        | Polish, docs, tests                                  | done  |

## Requirements

- LibreOffice 7.0 or newer (developed against LibreOffice 26.8)
- Python 3 UNO bridge (`libreoffice-pyuno` on openSUSE)

## Build, install, develop

```sh
./build.sh       # produce markdown-writer.oxt
./install.sh     # build + install for the current user (unopkg)
./uninstall.sh   # remove the extension
./dev.sh --run   # rebuild + reinstall + start Writer
```

Because Python UNO components are loaded at office startup, **restart
LibreOffice** after (re)installing for changes to take effect.

## Usage

After installing and restarting Writer, open the new **Markdown** menu:

- **Live Markdown** (check box) — auto-format Markdown as you type.
- **Open Markdown File…** — open a `.md` file as a Writer document.
- **Edit Markdown Source…** — edit the raw Markdown in a dialog with a preview.
- **Save as Markdown…** — save the document as `.md`.
- **About Markdown Writer**.

Basic formatting is done by typing Markdown syntax (with Live Markdown enabled).

### Import / export

- **Open Markdown File…** — open a `.md` file as a Writer document.
- **Save as Markdown…** — save the current document as `.md`.

### Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+Alt+P` | Preview Markdown |
| `Ctrl+Alt+M` | Markdown editor |

### Preview and source editing

- **Edit Markdown Source…** — opens the **Markdown** deck in the **Sidebar**
  (View ▸ Sidebar) with the document's Markdown source. **Apply** writes it back
  to the document; **Reload** re-reads it from the document.

### Live Markdown (Typora-like)

Type Markdown and it is reformatted as you go — the markers are consumed and
replaced by real formatting:

| You type            | You get                          |
|---------------------|----------------------------------|
| `# Title`           | Heading 1 "Title"                |
| `- item` / `* item` | bullet list                      |
| `1. item`           | numbered list                    |
| `> quote`           | block quote                      |
| ```` ``` ````       | code block paragraph             |
| `**bold**`          | bold text                        |
| `*italic*` `_i_`    | italic text                      |
| `~~strike~~`        | strikethrough                    |
| `` `code` ``        | inline code                      |
| `[text](url)`       | hyperlink                        |

Live mode is **off by default**. Tick **Markdown ▸ Live Markdown** (a
check box: ticked = Live ON) to enable it for the current and new documents.
Live attaches itself to every Writer document created or loaded while it is
enabled.

> **Note on live block conversion.** Converting a line to a *paragraph style*
> (heading, list, quote, code block) from inside the typing notification
> crashes some LibreOffice builds (an uncaught `std::out_of_range` in the GTK3
> VCL plugin). Live conversion of these block markers is therefore **off by
> default**; inline markers (bold, italic, code, strike, link) stay live, and
> headings/lists/quote/code are one toolbar click (or `Ctrl+Alt+…`) away. On a
> LibreOffice build without the bug you can re-enable it with the environment
> variable `MARKDOWN_WRITER_LIVE_BLOCKS=1`.

### Tests

```sh
./tests/run_tests.sh
```

Runs the pure-Python unit tests and the UNO integration tests against a
temporary headless LibreOffice.

## Project layout

```
description.xml            extension metadata
META-INF/manifest.xml      declares the Python UNO component and its modules
Addons.xcu                 "Markdown" menu and toolbar
Icons.xcu                  generated image set for the toolbar buttons
Shortcuts.xcu              Ctrl+Alt keyboard shortcuts
MarkdownWriter.xcu         best-effort document-event job registration
mdwriter.py                UNO bootstrap (g_ImplementationHelper)
pythonpath/mdwriter/
    __init__.py
    dispatch.py            protocol handler + XJobExecutor (menu/toolbar)
    formatter.py           formatting operations (bold, headings, ...)
    live.py                live auto-formatting + status indicator
    markdown.py            pure-text Markdown parsing
    exporter.py            Markdown import/export helpers
    md2html.py             Markdown -> HTML converter
    preview.py             preview window + two-pane editor dialog
tools/make_icons.py        generates icons/*.png and Icons.xcu
tests/                     unit and UNO integration tests
build.sh install.sh uninstall.sh dev.sh
```

## Limitations

- Live formatting is a pragmatic, regex-based subset of Markdown, not a full
  CommonMark implementation. Nested structures and tables typed as Markdown are
  not auto-converted (use **Insert Table** for tables).
- Live formatting asserts itself on the paragraph under the cursor; it consumes
  the markers rather than hiding them.

## License

Mozilla Public License 2.0 (MPL-2.0). See [LICENSE](LICENSE).
