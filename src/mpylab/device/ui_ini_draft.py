# -*- coding: utf-8 -*-
"""Shared autosave support for editable INI tabs in device UIs."""

from PySide6 import QtCore


SETTINGS_ORG = "mpylab"
INI_DRAFT_KEY = "ini_draft"
INI_DRAFT_DIRTY_KEY = "ini_draft_dirty"


def _read_ini_source(ini_source, default_text=""):
    if hasattr(ini_source, "read"):
        try:
            return ini_source.read()
        except Exception:
            return default_text
    if ini_source is None:
        return default_text
    return str(ini_source)


def _is_dirty(settings):
    value = settings.value(INI_DRAFT_DIRTY_KEY, False)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def load_ini_with_draft(owner, editor, ini_source, default_text, settings_app):
    """Load INI text, preferring an unsaved draft stored in QSettings."""
    settings = QtCore.QSettings(SETTINGS_ORG, settings_app)
    draft = settings.value(INI_DRAFT_KEY, "", str)
    content = draft if _is_dirty(settings) and draft else _read_ini_source(ini_source, default_text)

    editor.blockSignals(True)
    editor.setPlainText(content)
    editor.blockSignals(False)

    timer = QtCore.QTimer(owner)
    timer.setSingleShot(True)
    timer.setInterval(500)
    owner._ini_draft_dirty = False

    def save_draft():
        if not getattr(owner, "_ini_draft_dirty", False):
            return
        settings.setValue(INI_DRAFT_KEY, editor.toPlainText())
        settings.setValue(INI_DRAFT_DIRTY_KEY, True)
        owner._ini_draft_dirty = False

    def schedule_save():
        owner._ini_draft_dirty = True
        timer.start()

    timer.timeout.connect(save_draft)
    editor.textChanged.connect(schedule_save)

    app = QtCore.QCoreApplication.instance()
    if app is not None:
        app.aboutToQuit.connect(save_draft)

    owner._ini_draft_settings = settings
    owner._ini_draft_timer = timer
    owner._save_ini_draft = save_draft
    return content


def clear_ini_draft(owner):
    """Drop the autosaved draft after an explicit successful file save."""
    timer = getattr(owner, "_ini_draft_timer", None)
    if timer is not None and timer.isActive():
        timer.stop()

    settings = getattr(owner, "_ini_draft_settings", None)
    if settings is None:
        return
    settings.remove(INI_DRAFT_KEY)
    settings.setValue(INI_DRAFT_DIRTY_KEY, False)
    owner._ini_draft_dirty = False
