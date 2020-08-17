#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Ayatana Webmail, message actions dialog
# Authors: Robert Tari <robert@tari.in>
# License: GNU GPL 3 or higher; http://www.gnu.org/licenses/gpl.html

import gi

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk
from ayatanawebmail.appdata import APPNAME

class DialogAccounts(Gtk.Dialog):

    def __init__(self, strKey, getDataPath, lstAccounts):

        Gtk.Dialog.__init__(self, _('Select account'), None, 0, (Gtk.STOCK_OK, Gtk.ResponseType.OK))

        self.lstURLs = []
        self.set_icon_from_file(getDataPath('/usr/share/icons/hicolor/scalable/apps/' + APPNAME + '.svg'))
        self.set_position(Gtk.WindowPosition.CENTER)
        oImage = Gtk.Image()
        oImage.set_from_file(getDataPath('/usr/share/icons/hicolor/scalable/apps/' + APPNAME + '.svg'))
        oImage.props.valign = Gtk.Align.START
        oImage.props.icon_size = Gtk.IconSize.DIALOG
        oGrid = Gtk.Grid(border_width=10, row_spacing=2, column_spacing=10)
        oGrid.attach(oImage, 0, 0, 1, 4)
        oGrid.attach(Gtk.Label('<b>'+_('Which account\'s command/web page would you like to open?')+'</b>', use_markup=True, xalign=0, margin_bottom=10), 1, 0, 1, 1)

        for nIndex, dctAccount in enumerate(lstAccounts):

            self.__dict__['oRadioButton' + str(nIndex)] = Gtk.RadioButton.new_with_label_from_widget(None if not 'oRadioButton0' in self.__dict__ else self.__dict__['oRadioButton0'], dctAccount['Login'] + '@' + dctAccount['Host'])
            self.__dict__['oRadioButton' + str(nIndex)].props.valign = Gtk.Align.START

            if nIndex == len(lstAccounts) - 1:
                self.__dict__['oRadioButton' + str(nIndex)].props.vexpand = True

            oGrid.attach(self.__dict__['oRadioButton' + str(nIndex)] , 1, 1 + nIndex, 1, 1)
            self.lstURLs.append(dctAccount[strKey])

        self.get_content_area().add(oGrid)
        self.connect('response', self.onResponse)
        self.set_keep_above(True)
        self.show_all()
        self.strURL = None

    def onResponse(self, oWidget, nResponse):

        if nResponse == Gtk.ResponseType.OK:

            for nIndex, strURL in enumerate(self.lstURLs):

                if self.__dict__['oRadioButton' + str(nIndex)].get_active():

                    self.strURL = strURL
                    break
