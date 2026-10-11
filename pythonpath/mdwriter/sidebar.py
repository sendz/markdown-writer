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

        model = smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialogModel", self.ctx)
        model.setPropertyValue("Width", mx(width_px))
        model.setPropertyValue("Height", my(height_px))

        edit = model.createInstance("com.sun.star.awt.UnoControlEditModel")
        edit.setPropertyValue("Name", "source")
        edit.setPropertyValue("PositionX", mx(margin))
        edit.setPropertyValue("PositionY", my(margin))
        edit.setPropertyValue("Width", mx(width_px - 2 * margin))
        edit.setPropertyValue("Height", my(height_px - 3 * margin - btn_h))
        edit.setPropertyValue("MultiLine", True)
        edit.setPropertyValue("VScroll", True)
        edit.setPropertyValue("HScroll", True)
        edit.setPropertyValue("Tabstop", True)
        model.insertByName("source", edit)

        btn_w = (width_px - 3 * margin) // 2
        btn_y = height_px - margin - btn_h

        apply_btn = model.createInstance("com.sun.star.awt.UnoControlButtonModel")
        apply_btn.setPropertyValue("Name", "apply")
        apply_btn.setPropertyValue("Label", "Apply")
        apply_btn.setPropertyValue("PositionX", mx(margin))
        apply_btn.setPropertyValue("PositionY", my(btn_y))
        apply_btn.setPropertyValue("Width", mx(btn_w))
        apply_btn.setPropertyValue("Height", my(btn_h))
        model.insertByName("apply", apply_btn)

        reload_btn = model.createInstance("com.sun.star.awt.UnoControlButtonModel")
        reload_btn.setPropertyValue("Name", "reload")
        reload_btn.setPropertyValue("Label", "Reload")
        reload_btn.setPropertyValue("PositionX", mx(margin * 2 + btn_w))
        reload_btn.setPropertyValue("PositionY", my(btn_y))
        reload_btn.setPropertyValue("Width", mx(btn_w))
        reload_btn.setPropertyValue("Height", my(btn_h))
        model.insertByName("reload", reload_btn)

        self.dialog = smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialog", self.ctx)
        self.dialog.setModel(model)
        try:
            toolkit = smgr.createInstanceWithContext(
                "com.sun.star.awt.Toolkit", self.ctx)
            # createPeer expects the *peer* of the parent window, otherwise the
            # dialog becomes a separate top-level window instead of being
            # embedded in the sidebar panel.
            parent_peer = parent
            try:
                parent_peer = parent.queryInterface(
                    uno.getTypeByName("com.sun.star.awt.XWindowPeer"))
                _log("panel parent XWindowPeer=%r" % (parent_peer,))
            except Exception as exc:
                _log("panel parent peer query failed: %r" % (exc,))
                parent_peer = parent
            self.dialog.createPeer(toolkit, parent_peer)
            self.dialog.setPosSize(0, 0, width_px, height_px, 15)
            self.dialog.setVisible(True)
        except Exception as exc:
            _log("panel createPeer failed: %r" % (exc,))

        self.control = self.dialog.getControl("source")
        self.apply = self.dialog.getControl("apply")
        self.reload = self.dialog.getControl("reload")
        self.apply.addActionListener(_ActionListener(self._apply))
        self.reload.addActionListener(_ActionListener(self._load_source))
        self._load_source()

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
