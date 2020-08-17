#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Ayatana Webmail, message actions dialog
# Authors: Robert Tari <robert@tari.in>
# License: GNU GPL 3 or higher; http://www.gnu.org/licenses/gpl.html

from gi.repository import Gtk
from ayatanawebmail.common import getDataPath
from ayatanawebmail.appdata import APPNAME

class DialogActions(Gtk.Dialog):

    def __init__(self, strSender, strSubject):

        Gtk.Dialog.__init__(self, _('Message actions'), None, 0, (_('Delete'), 100, _('Mark as read'), 200, _('Open message/Run command'), 300))
        self.set_icon_from_file(getDataPath('/usr/share/icons/hicolor/scalable/apps/' + APPNAME + '.svg'))
        self.set_position(Gtk.WindowPosition.CENTER)
        oImage = Gtk.Image()
        oImage.set_from_file(getDataPath('/usr/share/icons/hicolor/scalable/apps/' + APPNAME + '.svg'))
        oImage.props.valign = Gtk.Align.START
        oImage.props.icon_size = Gtk.IconSize.DIALOG
        oGrid = Gtk.Grid(border_width=10, row_spacing=2, column_spacing=10)
        oGrid.attach(oImage, 0, 0, 1, 4)
        oGrid.attach(Gtk.Label('<b>' + _('Sender') + '</b>', xalign=0, use_markup=True, valign = Gtk.Align.START), 1, 0, 1, 1)
        oGrid.attach(Gtk.Label(strSender, xalign=0, margin_bottom=10, valign = Gtk.Align.START), 1, 1, 1, 1)
        oGrid.attach(Gtk.Label('<b>' + _('Subject') + '</b>', xalign=0, use_markup=True, valign = Gtk.Align.START), 1, 2, 1, 1)
        oGrid.attach(Gtk.Label(strSubject, xalign=0, valign = Gtk.Align.START, vexpand = True), 1, 3, 1, 1)
        self.get_content_area().add(oGrid)
        oButtonDelete = self.get_widget_for_response(100)
        oButtonDelete.set_image(Gtk.Image.new_from_icon_name('gtk-delete', Gtk.IconSize.BUTTON))
        oButtonMark = self.get_widget_for_response(200)
        oButtonMark.set_image(Gtk.Image.new_from_icon_name('gtk-ok', Gtk.IconSize.BUTTON))
        oButtonOpen = self.get_widget_for_response(300)
        oButtonOpen.set_image(Gtk.Image.new_from_icon_name('web-browser', Gtk.IconSize.BUTTON))
        self.set_keep_above(True)
        self.show_all()
