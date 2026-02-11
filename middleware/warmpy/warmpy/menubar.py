from __future__ import annotations

import pkgutil
import logging
from pathlib import Path

from AppKit import (
    NSApplication,
    NSImage,
    NSMenu,
    NSMenuItem,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSWorkspace,
)
from Foundation import NSObject

from warmpy.bootstrap import init_env


_HANDLER = None


class MenuHandler(NSObject):
    def initWithPluginsDir_logFile_(self, plugins_dir: str, log_file: str):
        self = self.init()
        if self is None:
            return None
        self._plugins_dir = plugins_dir
        self._log_file = log_file
        return self

    def openPlugins_(self, _sender):
        logging.info("MENU: Open plugins folder")
        NSWorkspace.sharedWorkspace().openFile_(self._plugins_dir)

    def openLog_(self, _sender):
        logging.info("MENU: Open log file")
        NSWorkspace.sharedWorkspace().openFile_(self._log_file)

    def quit_(self, _sender):
        logging.info("MENU: Quit")
        NSApplication.sharedApplication().terminate_(None)


def run_app():
    cfg, plugins_dir = init_env()

    app = NSApplication.sharedApplication()

    status = NSStatusBar.systemStatusBar().statusItemWithLength_(
        NSVariableStatusItemLength
    )

    button = status.button()

    # 🔑 ИМЯ АССЕТА (без .icns)
    image = NSImage.imageNamed_("warmpy")
    if image is not None:
        image.setTemplate_(False)     # цветная иконка
        image.setSize_((18, 18))      # меню-бар
        button.setImage_(image)
        button.setTitle_("")
    else:
        # fallback, если ассет не подхватился
        button.setTitle_("WP")

    menu = NSMenu.alloc().init()

    # Put plugin list into a submenu to avoid cluttering the root menu.
    plugins_menu = NSMenu.alloc().init()
    plugins_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Plugins", None, ""
    )
    plugins_item.setSubmenu_(plugins_menu)
    menu.addItem_(plugins_item)

    plugins_dir = Path(plugins_dir)
    if plugins_dir.exists():
        for mod in pkgutil.iter_modules([str(plugins_dir)]):
            plugins_menu.addItem_(
                NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    mod.name, None, ""
                )
            )

    menu.addItem_(NSMenuItem.separatorItem())

    handler = MenuHandler.alloc().initWithPluginsDir_logFile_(
        str(plugins_dir),
        str(cfg["log_file"]),
    )

    item_plugins = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Open plugins folder", "openPlugins:", ""
    )
    item_plugins.setTarget_(handler)
    menu.addItem_(item_plugins)

    item_log = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Open log file", "openLog:", ""
    )
    item_log.setTarget_(handler)
    menu.addItem_(item_log)

    menu.addItem_(NSMenuItem.separatorItem())

    item_quit = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Quit", "quit:", "q"
    )
    item_quit.setTarget_(handler)
    menu.addItem_(item_quit)

    status.setMenu_(menu)

    global _HANDLER
    _HANDLER = handler

    app.run()