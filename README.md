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
| M3        | Markdown import/export helpers                       | todo  |
| M4        | Source + preview panel                               | todo  |
| M5        | Polish, docs, tests                                  | todo  |

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
description.xml          # extension metadata
META-INF/manifest.xml    # declares the Python UNO component
Addons.xcu               # "Markdown" menu entries
mdwriter.py              # UNO bootstrap (g_ImplementationHelper)
pythonpath/mdwriter/     # Python implementation package
```

## License

Mozilla Public License 2.0 (MPL-2.0).
