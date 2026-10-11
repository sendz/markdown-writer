"""Sidebar deck/panel hosting the Markdown source editor.

Implements the pieces LibreOffice needs for a custom sidebar panel
(``type = toolpanel``):

* :class:`SidebarPanelFactory` - ``com.sun.star.ui.XUIElementFactory`` registered
  in ``Sidebar.xcu`` (``Registered/ContentFactories``).  It creates the panel
  for our ``ImplementationURL``.
* :class:`SidebarPanelElement` - ``com.sun.star.ui.XUIElement``, whose
  ``getRealInterface()`` returns the panel.
* :class:`SidebarPanel` - ``com.sun.star.ui.XToolPanel`` +
  ``com.sun.star.ui.XSidebarPanel``; it builds the source editor as a child of
  the window the sidebar hands over.
"""

import os

import uno
import unohelper

from com.sun.star.ui import XUIElementFactory, XUIElement, XToolPanel, XSidebarPanel
from com.sun.star.lang import XServiceInfo
from com.sun.star.container import NoSuchElementException
from com.sun.star.awt import XActionListener

from mdwriter import exporter
from mdwriter import preview

PANEL_URL = "private:resource/toolpanel/com.sendyyeah.mdwriter/Source"
FACTORY_IMPLE = "com.sendyyeah.mdwriter.PanelFactory"


def _log(message):
    path = os.environ.get("MARKDOWN_WRITER_DEBUG_LOG")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(message + "\n")
    except Exception:
        pass


def _arg(args, name):
    for entry in args or ():
        if getattr(entry, "Name", None) == name:
            return entry.Value
    return None


class _ActionListener(unohelper.Base, XActionListener):

    def __init__(self, callback):
        self.callback = callback

    def actionPerformed(self, event):
        self.callback()

    def disposing(self, source):
        pass


class SidebarPanelFactory(unohelper.Base, XServiceInfo, XUIElementFactory):

    IMPLE_NAME = FACTORY_IMPLE
    SERVICE_NAMES = ("com.sun.star.ui.UIElementFactory",)

    def __init__(self, ctx, *args):
        self.ctx = ctx

    def getImplementationName(self):
        return self.IMPLE_NAME

    def supportsService(self, name):
        return name in self.SERVICE_NAMES

    def getSupportedServiceNames(self):
        return self.SERVICE_NAMES

    def createUIElement(self, resource_url, args):
        _log("PanelFactory.createUIElement %r" % (resource_url,))
        if resource_url != PANEL_URL:
            raise NoSuchElementException(resource_url, self)
        return SidebarPanelElement(self.ctx, resource_url, args)


class SidebarPanelElement(unohelper.Base, XServiceInfo, XUIElement):

    SERVICE_NAMES = ("com.sun.star.ui.UIElement",)

    def __init__(self, ctx, resource_url, args):
        self.ctx = ctx
        self.resource_url = resource_url
        self.panel = SidebarPanel(ctx, args)

    def getImplementationName(self):
        return "com.sendyyeah.mdwriter.PanelElement"

    def supportsService(self, name):
        return name in self.SERVICE_NAMES

    def getSupportedServiceNames(self):
        return self.SERVICE_NAMES

    def getRealInterface(self):
        return self.panel

    @property
    def Resource(self):
        return self.resource_url

    @property
    def Type(self):
        return "toolpanel"


class SidebarPanel(unohelper.Base, XServiceInfo, XToolPanel, XSidebarPanel):

    SERVICE_NAMES = ("com.sun.star.ui.ToolPanel",)

    def __init__(self, ctx, args):
        self.ctx = ctx
        self.frame = _arg(args, "Frame")
        parent = _arg(args, "ParentWindow")
        self.dialog = None
        self.control = None
        self.reload = None
        self.apply = None
        self._build(parent)

    # XServiceInfo
    def getImplementationName(self):
        return "com.sendyyeah.mdwriter.Panel"

    def supportsService(self, name):
        return name in self.SERVICE_NAMES

    def getSupportedServiceNames(self):
        return self.SERVICE_NAMES

    # XToolPanel
    @property
    def Window(self):
        try:
            return self.dialog.getPeer()
        except Exception:
            return None

    def createAccessible(self, parent):
        return None

    # XSidebarPanel
    def getMinimalWidth(self):
        return 260

    def getHeightForWidth(self, width):
        size = uno.createUnoStruct("com.sun.star.ui.LayoutSize")
        size.Minimum = 200
        size.Preferred = 400
        size.Maximum = 2000
        return size

    # ------------------------------------------------------------------ #
    def _ui_scale(self):
        try:
            return preview._ui_scale(self.ctx, self.frame)
        except Exception:
            return (1.0, 1.0)

    def _panel_size(self, parent):
        try:
            rect = parent.getPosSize()
            return max(220, rect.Width), max(220, rect.Height)
        except Exception:
            return 260, 420

    def _build(self, parent):
        smgr = self.ctx.ServiceManager
        sx, sy = self._ui_scale()
        width_px, height_px = self._panel_size(parent)
        margin = 4
        btn_h = 26
        try:
            _log("panel parent=%r types=%s" % (
                parent, [t.typeName for t in parent.getTypes()]))
        except Exception as exc:
            _log("panel parent types failed: %r" % (exc,))

        def mx(px):
            return int(round(px / sx))

        def my(px):
            return int(round(px / sy))

        toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", self.ctx)

        cmodel = smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlContainerModel", self.ctx)
        cmodel.setPropertyValue("Width", mx(width_px))
        cmodel.setPropertyValue("Height", my(height_px))

        # A container (not a dialog) is embedded as a child window; a dialog is
        # always a top-level window.
        self.dialog = smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlContainer", self.ctx)
        self.dialog.setModel(cmodel)
        parent_peer = parent
        try:
            parent_peer = parent.queryInterface(
                uno.getTypeByName("com.sun.star.awt.XWindowPeer"))
        except Exception:
            parent_peer = parent
        try:
            self.dialog.createPeer(toolkit, parent_peer)
        except Exception as exc:
            _log("panel container createPeer failed: %r" % (exc,))
        self.dialog.setPosSize(0, 0, width_px, height_px, 15)

        btn_w = (width_px - 3 * margin) // 2
        btn_y = height_px - margin - btn_h

        self.control = self._add_edit(
            toolkit, "source", margin, margin,
            width_px - 2 * margin, height_px - 3 * margin - btn_h)
        self.apply = self._add_button(
            toolkit, "apply", "Apply", margin, btn_y, btn_w, btn_h)
        self.reload = self._add_button(
            toolkit, "reload", "Reload", margin * 2 + btn_w, btn_y, btn_w, btn_h)

        self.apply.addActionListener(_ActionListener(self._apply))
        self.reload.addActionListener(_ActionListener(self._load_source))
        self._load_source()

    def _add_control(self, toolkit, model, control, name, x, y, w, h):
        control.setModel(model)
        try:
            self.dialog.addControl(name, control)
        except Exception as exc:
            _log("addControl %s failed: %r" % (name, exc))
        try:
            control.createPeer(toolkit, self.dialog.getPeer())
        except Exception as exc:
            _log("createPeer %s failed: %r" % (name, exc))
        try:
            control.setPosSize(x, y, w, h, 15)
        except Exception:
            pass
        return control

    def _add_edit(self, toolkit, name, x, y, w, h):
        smgr = self.ctx.ServiceManager
        model = smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlEditModel", self.ctx)
        model.setPropertyValue("MultiLine", True)
        model.setPropertyValue("VScroll", True)
        model.setPropertyValue("HScroll", True)
        model.setPropertyValue("Tabstop", True)
        control = smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlEdit", self.ctx)
        return self._add_control(toolkit, model, control, name, x, y, w, h)

    def _add_button(self, toolkit, name, label, x, y, w, h):
        smgr = self.ctx.ServiceManager
        model = smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlButtonModel", self.ctx)
        model.setPropertyValue("Label", label)
        control = smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlButton", self.ctx)
        return self._add_control(toolkit, model, control, name, x, y, w, h)

    def _model(self):
        try:
            return self.frame.getController().getModel()
        except Exception:
            return None

    def _load_source(self):
        model = self._model()
        if model is None:
            return
        try:
            md_path = os.path.join("/tmp", "mdwriter-sidebar.md")
            text = preview.document_to_markdown(model, md_path)
            self.control.setText(text)
        except Exception as exc:
            _log("panel load source failed: %r" % (exc,))

    def _apply(self):
        model = self._model()
        if model is None:
            return
        try:
            preview._apply_source(self.ctx, model, self.control.getText())
        except Exception as exc:
            _log("panel apply failed: %r" % (exc,))
