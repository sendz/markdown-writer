"""Bootstrap module for the Markdown Writer LibreOffice extension.

LibreOffice's Python UNO loader imports this file (it is declared in
``META-INF/manifest.xml`` with the media type
``application/vnd.sun.star.uno-component;type=Python``) and reads the module
level ``g_ImplementationHelper`` to learn which UNO services the extension
provides.

The folder named ``pythonpath`` that sits next to this file is automatically
added to ``sys.path`` by the loader, so helper modules can simply be imported
from the ``mdwriter`` package.
"""

import unohelper

from mdwriter.dispatch import Dispatch

# Importing ``live`` also bootstraps the global document watcher that drives
# the live Markdown auto-formatting.
from mdwriter import live  # noqa: F401

g_ImplementationHelper = unohelper.ImplementationHelper()

g_ImplementationHelper.addImplementation(
    Dispatch,
    "com.sendyyeah.mdwriter.Dispatch",
    ("com.sun.star.frame.ProtocolHandler",),
)
