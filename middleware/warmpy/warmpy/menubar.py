# warmpy/menubar.py
import logging
import sys
from pathlib import Path

import objc
from Cocoa import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSImage,
    NSMenu,
    NSMenuItem,
    NSObject,
    NSStatusBar,
    NSWorkspace,
)

_HANDLER = None


def _resource_path(filename: str) -> Path:
    """
    Resolve a file inside warmpy.app/Contents/Resources using sys.executable.

    sys.executable inside a py2app bundle:
      .../warmpy.app/Contents/MacOS/warmpy
    Resources dir:
      .../warmpy.app/Contents/Resources
    """
    exe = Path(sys.executable).resolve()
    # exe.parents[0] = .../Contents/MacOS
    # exe.parents[1] = .../Contents
    res_dir = exe.parents[1] / "Resources"
    return res_dir / filename


class Handler(NSObject):
    def initWithWorker_(self, worker):
        self = objc.super(Handler, self).init()
        if self is None:
            return None
        self.worker = worker
        self.status_item = None
        self.menu = None
        return self

    def buildMenu(self):
        # Create status bar item + menu
        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(-1.0)

        # Try to set a real template image from Resources
        icon_path = _resource_path("warmpyStatusTemplate.png")
        logging.info("STATUS icon_path=%s exists=%s", icon_path, icon_path.exists())

        if icon_path.exists():
            img = NSImage.alloc().initWithContentsOfFile_(str(icon_path))
            logging.info("STATUS nsimage_loaded=%s", img is not None)
            if img is not None:
                img.setTemplate_(True)

                btn = None
                try:
                    btn = self.status_item.button()
                except Exception:
                    btn = None

                if btn is not None:
                    btn.setTitle_("")
                    btn.setImage_(img)
                    logging.info("STATUS icon_set method=button")
                else:
                    # Older API fallback
                    self.status_item.setTitle_("")
                    try:
                        self.status_item.setImage_(img)
                        logging.info("STATUS icon_set method=setImage")
                    except Exception:
                        # If even that fails, fall back to a simple title.
                        self.status_item.setTitle_("W")
                        logging.warning("STATUS icon_set failed; fallback title=W")
        else:
            # Fallback if resource not found
            self.status_item.setTitle_("W")

        # Menu
        self.menu = NSMenu.alloc().init()

        open_log = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Open Log", "openLog:", ""
        )
        open_log.setTarget_(self)
        self.menu.addItem_(open_log)

        self.menu.addItem_(NSMenuItem.separatorItem())

        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit", "quit:", ""
        )
        quit_item.setTarget_(self)
        self.menu.addItem_(quit_item)

        self.status_item.setMenu_(self.menu)

    def openLog_(self, _sender):
        try:
            from .paths import LOG_FILE

            NSWorkspace.sharedWorkspace().openFile_(str(LOG_FILE))
        except Exception:
            logging.exception("Open log failed")

    def quit_(self, _sender):
        NSApplication.sharedApplication().terminate_(None)


def run_app(worker):
    global _HANDLER

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    _HANDLER = Handler.alloc().initWithWorker_(worker)
    _HANDLER.buildMenu()

    logging.info("UI started")
    app.run()