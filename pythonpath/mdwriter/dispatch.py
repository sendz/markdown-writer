"""Protocol handler that receives commands from the Markdown Writer UI.

The extension's menu items use URLs of the form::

    service:com.sendyyeah.mdwriter.Dispatch?command=<command>

LibreOffice instantiates this class (service ``com.sun.star.frame.ProtocolHandler``)
for the frame that owns the menu, then calls ``queryDispatch`` with the URL above.
We parse ``command`` from the URL and return an ``XDispatch`` that actually runs it.
"""

import unohelper

from com.sun.star.frame import XDispatchProvider, XDispatch, XFrame
from com.sun.star.lang import XInitialization, XServiceInfo
from com.sun.star.awt import MessageBoxButtons

IMPLE_NAME = "com.sendyyeah.mdwriter.Dispatch"
SERVICE_NAMES = ("com.sun.star.frame.ProtocolHandler",)

URL_PREFIX = "service:com.sendyyeah.mdwriter.Dispatch"


def _parse_command(url):
    """Extract the ``command`` query parameter from a parsed UNO URL."""
    complete = url.Complete
    if "?" not in complete:
        return ""
    query = complete.split("?", 1)[1]
    for part in query.split("&"):
        key, _, value = part.partition("=")
        if key == "command":
            return value
    return ""


class Dispatch(unohelper.Base, XServiceInfo, XInitialization,
               XDispatchProvider, XDispatch):

    def __init__(self, ctx, *args):
        self.ctx = ctx
        self.frame = None
        self.command = ""

    # ------------------------------------------------------------------ #
    # XServiceInfo
    # ------------------------------------------------------------------ #
    def getImplementationName(self):
        return IMPLE_NAME

    def supportsService(self, name):
        return name in SERVICE_NAMES

    def getSupportedServiceNames(self):
        return SERVICE_NAMES

    # ------------------------------------------------------------------ #
    # XInitialization
    # ------------------------------------------------------------------ #
    def initialize(self, args):
        """Called by the frame with the frame itself as the only argument."""
        if args and isinstance(args[0], XFrame):
            self.frame = args[0]

    # ------------------------------------------------------------------ #
    # XDispatchProvider
    # ------------------------------------------------------------------ #
    def queryDispatch(self, url, target_frame_name, search_flags):
        if url.Protocol == "service:" and url.Complete.startswith(URL_PREFIX):
            dispatch = Dispatch(self.ctx)
            dispatch.frame = self.frame
            dispatch.command = _parse_command(url)
            return dispatch
        return None

    def queryDispatches(self, requests):
        return tuple(
            self.queryDispatch(r.FeatureURL, r.FrameName, r.SearchFlags)
            for r in requests
        )

    # ------------------------------------------------------------------ #
    # XDispatch
    # ------------------------------------------------------------------ #
    def dispatch(self, url, args):
        if not self.command:
            self.command = _parse_command(url)
        handler = getattr(self, "_cmd_" + self.command, None)
        if handler is None:
            self._error("Unknown command: %r" % self.command)
            return
        handler()

    def addStatusListener(self, listener, url):
        pass

    def removeStatusListener(self, listener, url):
        pass

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _show_info(self, title, message):
        toolkit = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.awt.Toolkit", self.ctx)
        parent = None
        if self.frame is not None:
            parent = self.frame.getContainerWindow()
        box = toolkit.createMessageBox(
            parent, "infobox", MessageBoxButtons.BUTTONS_OK, title, message)
        box.execute()

    def _error(self, message):
        self._show_info("Markdown Writer", message)

    def _model(self):
        """Return the current document model, or None if there is no document."""
        if self.frame is None:
            return None
        controller = self.frame.getController()
        if controller is None:
            return None
        return controller.getModel()

    # ------------------------------------------------------------------ #
    # Commands
    # ------------------------------------------------------------------ #
    def _cmd_about(self):
        import mdwriter
        self._show_info(
            "About Markdown Writer",
            "Markdown Writer %s\n\n"
            "Write Markdown inside LibreOffice Writer." % mdwriter.__version__,
        )
