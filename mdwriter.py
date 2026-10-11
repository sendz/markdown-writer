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
from mdwriter.live import Job
from mdwriter.sidebar import SidebarPanelFactory

g_ImplementationHelper = unohelper.ImplementationHelper()

# Menu and toolbar commands.
g_ImplementationHelper.addImplementation(
    Dispatch,
    "com.sendyyeah.mdwriter.Dispatch",
    ("com.sun.star.frame.ProtocolHandler",),
)

# Custom sidebar panel (source editor).
g_ImplementationHelper.addImplementation(
    SidebarPanelFactory,
    "com.sendyyeah.mdwriter.PanelFactory",
    ("com.sun.star.ui.UIElementFactory",),
)

# Best-effort automatic hook: installs the live formatter when a document is
# opened, if the office runs job components in the current environment.
g_ImplementationHelper.addImplementation(
    Job,
    "com.sendyyeah.mdwriter.Job",
    ("com.sun.star.task.Job",),
)
