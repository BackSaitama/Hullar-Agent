"""Tüm araçları toplayıp ToolBox oluşturur."""

from .base import Tool, ToolBox
from . import (keyboard_mouse, app_control, file_system, browser,
               whatsapp, analysis, social)


def build_toolbox(ctx) -> ToolBox:
    box = ToolBox(ctx)
    keyboard_mouse.register(box)
    app_control.register(box)
    file_system.register(box)
    browser.register(box)
    whatsapp.register(box)
    analysis.register(box)
    social.register(box)
    return box


__all__ = ["Tool", "ToolBox", "build_toolbox"]
