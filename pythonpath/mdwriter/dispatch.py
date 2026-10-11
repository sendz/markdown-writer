"""Command entry point for the Markdown Writer UI.

The extension's menu and toolbar items use URLs of the form::

    service:com.sendyyeah.mdwriter.Dispatch?command=<command>

For such URLs LibreOffice's ``com.sun.star.comp.framework.ServiceHandler``
creates the service named in the URL and, if the object supports
``com.sun.star.task.XJobExecutor``, calls ``trigger()`` with the text after the
``?`` (for example ``command=bold``).  That is the path the add-on UI uses, so
``XJobExecutor`` is what actually runs our commands.

``XDispatchProvider``/``XDispatch`` and ``XInitialization`` are also
implemented so the component works when used directly as a protocol handler
(e.g. from scripts or tests).
"""

import unohelper

from com.sun.star.frame import XDispatchProvider, XDispatch, XFrame
from com.sun.star.lang import XInitialization, XServiceInfo
from com.sun.star.awt import MessageBoxButtons
from com.sun.star.task import XJobExecutor

from mdwriter import formatter
from mdwriter import live
from mdwriter import exporter
from mdwriter import preview

IMPLE_NAME = "com.sendyyeah.mdwriter.Dispatch"
SERVICE_NAMES = ("com.sun.star.frame.ProtocolHandler",)

URL_PREFIX = "service:com.sendyyeah.mdwriter.Dispatch"


def _parse_command(url):
    """Extract the ``command`` parameter from a parsed UNO URL."""
    return _command_from_string(url.Complete)


def _command_from_string(text):
    """Extract ``command=`` from a URL or from a bare argument string."""
    if "?" in text:
        text = text.split("?", 1)[1]
    for part in text.split("&"):
        key, _, value = part.partition("=")
        if key == "command":
            return value
    return ""


class Dispatch(unohelper.Base, XServiceInfo, XInitialization,
               XDispatchProvider, XDispatch, XJobExecutor):

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
    # XInitialization (protocol handler path)
    # ------------------------------------------------------------------ #
    def initialize(self, args):
        # Do not isinstance-check against XFrame: pyuno's interface isinstance
        # is unreliable for UNO objects. The ProtocolHandler contract says the
        # first argument is the frame.
        if args:
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
        self._execute(self.command or _parse_command(url))

    def addStatusListener(self, listener, url):
        try:
            event = uno.createUnoStruct("com.sun.star.frame.FeatureStateEvent")
            event.Source = self
            event.FeatureURL = url
            event.FeatureDescriptor = ""
            event.IsEnabled = True
            event.Requery = False
            listener.statusChanged(event)
        except Exception:
            pass

    def removeStatusListener(self, listener, url):
        pass

    # ------------------------------------------------------------------ #
    # XJobExecutor  (this is the path used by the add-on menu/toolbar)
    # ------------------------------------------------------------------ #
    def trigger(self, event):
        self._execute(_command_from_string(event))

    # ------------------------------------------------------------------ #
    # Command dispatch
    # ------------------------------------------------------------------ #
    def _execute(self, command):
        preview._log("execute command=%r" % (command,))
        handler = getattr(self, "_cmd_" + command, None)
        if handler is None:
            self._error("Unknown command: %r" % command)
            return
        handler()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _show_info(self, title, message):
        toolkit = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.awt.Toolkit", self.ctx)
        parent = None
        frame = self._frame()
        if frame is not None:
            parent = frame.getContainerWindow()
        box = toolkit.createMessageBox(
            parent, "infobox", MessageBoxButtons.BUTTONS_OK, title, message)
        box.execute()

    def _error(self, message):
        self._show_info("Markdown Writer", message)

    def _model(self):
        """Return the current document model, or None if there is no document."""
        frame = self._frame()
        if frame is None:
            return None
        controller = frame.getController()
        if controller is None:
            return None
        return controller.getModel()

    def _frame(self):
        """Return the frame for this dispatch, falling back to the active one."""
        if self.frame is not None:
            return self.frame
        try:
            desktop = self.ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.frame.Desktop", self.ctx)
            return desktop.getCurrentFrame()
        except Exception:
            return None

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
            exporter.open_dialog(self.ctx, self._frame())
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
            self.ctx, exporter.default_name(model))
        if not url:
            return
        try:
            model.storeAsURL(url, (exporter.prop("FilterName", exporter.MARKDOWN_FILTER),))
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
            preview.edit_source(self.ctx, model, self._frame())
        except Exception as exc:
            preview._log("_cmd_source error: %r" % (exc,))
            self._error("Could not open source editor: %s" % exc)

    def _cmd_togglelive(self):
        live.LIVE_ENABLED = not live.LIVE_ENABLED
        if live.LIVE_ENABLED:
            model = self._model()
            if formatter.is_writer(model):
                live.attach(self.ctx, model)
        state = "ON" if live.LIVE_ENABLED else "OFF"
        self._show_info(
            "Markdown Writer",
            "Live Markdown auto-formatting is now %s." % state,
        )
