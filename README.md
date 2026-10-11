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

After installing and restarting Writer, open the new **Markdown** menu.

### Formatting commands

Apply Markdown semantics to the current selection or paragraph:

- **Bold**, **Italic**, **Strikethrough**, **Inline Code**
- **Heading 1** … **Heading 6**, **Body Text**
- **Bullet List**, **Numbered List**, **Block Quote**, **Code Block**
- **Horizontal Rule**, **Insert Link…**, **Insert Table**

### Import / export

- **Open Markdown File…** — open a `.md` file as a Writer document.
- **Export as Markdown…** — write the current document to a `.md` file
  (the open document is left untouched).
- **Save as Markdown…** — save the current document as `.md` (switches the
  document to the Markdown filter).

### Preview and source editing

- **Preview Markdown** — renders the current document as HTML in a separate
  window (a read-only preview you can place next to the editor).
- **Edit Markdown Source…** — opens a dialog with the document's raw Markdown
  for editing, with **Preview** (render in a window) and **Apply to Document**
  (replace the current document with the edited Markdown, rendered through the
  built-in Markdown filter).

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

Live mode is **on by default**. It attaches itself to every Writer document as
soon as it is loaded *after* the extension has been activated. To make sure it
is active, open a document, use any Markdown Writer command once (for example
**Bold**), then open/create documents as usual. **Markdown ▸ Toggle Live
Markdown** turns the feature off and on.

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
MarkdownWriter.xcu         best-effort document-event job registration
mdwriter.py                UNO bootstrap (g_ImplementationHelper)
pythonpath/mdwriter/
    __init__.py
    dispatch.py            protocol handler (menu/toolbar commands)
    formatter.py           formatting operations (bold, headings, ...)
    live.py                live auto-formatting (document watcher + listener)
    markdown.py            pure-text Markdown parsing
    exporter.py            Markdown import/export helpers
    md2html.py             Markdown -> HTML converter
    preview.py             preview window + source editor dialog
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
