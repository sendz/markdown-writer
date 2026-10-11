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

from mdwriter import formatter
from mdwriter import live
from mdwriter import exporter
from mdwriter import preview

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
        live.bootstrap(self.ctx)
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
    def _run(self, func):
        """Run *func(ctx, model)* after checking we are in a Writer document."""
        model = self._model()
        if not formatter.is_writer(model):
            self._error("This command only works in a Writer document.")
            return
        live.bootstrap(self.ctx)
        live.attach(self.ctx, model)
        try:
            func(self.ctx, model)
        except Exception as exc:  # keep the UI informative, never crash
            self._error("Command failed: %s" % exc)

    def _run_heading(self, level):
        self._run(lambda ctx, model: formatter.set_heading(ctx, model, level))

    def _cmd_about(self):
        import mdwriter
        self._show_info(
            "About Markdown Writer",
            "Markdown Writer %s\n\n"
            "Write Markdown inside LibreOffice Writer." % mdwriter.__version__,
        )

    def _cmd_bold(self):
        self._run(formatter.toggle_bold)

    def _cmd_italic(self):
        self._run(formatter.toggle_italic)

    def _cmd_strike(self):
        self._run(formatter.toggle_strike)

    def _cmd_code(self):
        self._run(formatter.toggle_code)

    def _cmd_heading1(self):
        self._run_heading(1)

    def _cmd_heading2(self):
        self._run_heading(2)

    def _cmd_heading3(self):
        self._run_heading(3)

    def _cmd_heading4(self):
        self._run_heading(4)

    def _cmd_heading5(self):
        self._run_heading(5)

    def _cmd_heading6(self):
        self._run_heading(6)

    def _cmd_body(self):
        self._run(formatter.set_body)

    def _cmd_bullet(self):
        self._run(formatter.toggle_bullet_list)

    def _cmd_number(self):
        self._run(formatter.toggle_number_list)

    def _cmd_quote(self):
        self._run(formatter.toggle_quote)

    def _cmd_codeblock(self):
        self._run(formatter.toggle_code_block)

    def _cmd_hr(self):
        self._run(formatter.insert_rule)

    def _cmd_link(self):
        self._run(formatter.insert_link)

    def _cmd_table(self):
        self._run(formatter.insert_table)

    def _cmd_openmd(self):
        try:
            exporter.open_dialog(self.ctx, self.frame)
        except Exception as exc:
            self._error("Could not open Markdown file: %s" % exc)

    def _cmd_exportmd(self):
        model = self._model()
        if not formatter.is_writer(model):
            self._error("This command only works in a Writer document.")
            return
        try:
            exporter.export_dialog(self.ctx, model)
        except Exception as exc:
            self._error("Could not export Markdown: %s" % exc)

    def _cmd_saveasmd(self):
        model = self._model()
        if not formatter.is_writer(model):
            self._error("This command only works in a Writer document.")
            return
        url = exporter.choose_save_markdown(
            self.ctx, exporter._default_name(model))
        if not url:
            return
        try:
            model.storeAsURL(url, (exporter._prop("FilterName", exporter.MARKDOWN_FILTER),))
        except Exception as exc:
            self._error("Could not save as Markdown: %s" % exc)

    def _cmd_preview(self):
        model = self._model()
        if not formatter.is_writer(model):
            self._error("This command only works in a Writer document.")
            return
        try:
            preview.preview(self.ctx, model)
        except Exception as exc:
            self._error("Could not render preview: %s" % exc)

    def _cmd_source(self):
        model = self._model()
        if not formatter.is_writer(model):
            self._error("This command only works in a Writer document.")
            return
        try:
            preview.edit_source(self.ctx, model, self.frame)
        except Exception as exc:
            self._error("Could not open source editor: %s" % exc)

    def _cmd_togglelive(self):
        live.LIVE_ENABLED = not live.LIVE_ENABLED
        if live.LIVE_ENABLED:
            # (Re)attach to the active document.
            model = self._model()
            if formatter.is_writer(model):
                live.attach(self.ctx, model)
        state = "ON" if live.LIVE_ENABLED else "OFF"
        self._show_info(
            "Markdown Writer",
            "Live Markdown auto-formatting is now %s." % state,
        )
