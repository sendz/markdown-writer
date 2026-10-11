# Markdown Writer

Write Markdown directly inside LibreOffice Writer.

Markdown Writer is a LibreOffice extension (`.oxt`) that lets you author in
Markdown while working in Writer.

## Status

| Milestone | Feature                                              | State |
|-----------|------------------------------------------------------|-------|
| M0        | Extension scaffold, build/install scripts, About box | done  |
| M1        | Formatting commands (bold, headings, lists, ...)     | todo  |
| M2        | Live auto-format while typing (Typora-like)          | todo  |
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

- **Markdown ▸ About Markdown Writer** — shows the extension version.

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
