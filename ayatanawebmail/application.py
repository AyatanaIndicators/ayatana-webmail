#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Ayatana Webmail, the main application class
# Authors: Dmitry Shachnev <mitya57@gmail.com>
#          Robert Tari <robert@tari.in>
# License: GNU GPL 3 or higher; http://www.gnu.org/licenses/gpl.html

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')

import email
import email.errors
import email.header
import email.utils
import dbus
import dbus.service
import logging
import secretstorage
import subprocess
import sys
import time
import re
import ayatanawebmail.imaplib2 as imaplib
import os.path
import os
import urllib3
import importlib
import locale
import psutil
from gi.repository import Gio, GLib, Gtk, Notify
from socket import error as socketerror
from dbus.mainloop.glib import DBusGMainLoop
from babel.dates import format_timedelta
from ayatanawebmail.common import g_oTranslation, g_oSettings, openURLOrCommand, g_lstAccounts
from ayatanawebmail.idler import Idler
from ayatanawebmail.dialog import PreferencesDialog, MESSAGEACTION
from ayatanawebmail.actions import DialogActions
from ayatanawebmail.appdata import APPNAME

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
imaplib._MAXLINE = 500000#160000 # See discussion in LP: #1309566
logger = logging.getLogger('Ayatana Webmail')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s: %(name)s: %(levelname)s: %(message)s'))
logger.addHandler(handler)
logger.propagate = False
m_reThrid = re.compile(b'THRID (\\d+)')
fixFormat = lambda string: string.replace('%(t0)s', '{t0}').replace('%(t1)s', '{t1}')

def checkNetwork():

    try:

        oResult = urllib3.PoolManager().request('HEAD', 'https://www.google.com', timeout=5)
        return True

    except Exception as oException:

        return False

def decodeWrapper(header):

    # Decodes an Email header, returns a string
    # A hack for headers without a space between decoded name and email
    try:

        dec = email.header.decode_header(header.replace('=?=<', '=?= <'))

    except email.errors.HeaderParseError:

        logger.warning('Exception in decode, skipping.')
        return header

    parts = []

    for dec_part in dec:

        if dec_part[1]:

            try:
                parts.append(dec_part[0].decode(dec_part[1]))
            except (AttributeError, LookupError, UnicodeDecodeError):
                logger.warning('Exception in decode, skipping.')

        elif isinstance(dec_part[0], bytes):

            parts.append(dec_part[0].decode())

        else:
            parts.append(dec_part[0])

    return str.join(' ', parts)

def getHeaderWrapper(message, header_name, decode):

    header = message[header_name]

    if isinstance(header, str):

        header = header.replace(' \r\n', '').replace('\r\n', '')
        return (decodeWrapper(header) if decode else header)

    return ''

def getSenderName(sender):

    # Strips address, and returns only name
    sname = email.utils.parseaddr(sender)[0]

    return sname if sname else sender

class MessagingMenu(object):

    oMessagingMenu = None
    oAppIndicator = None

    def __init__(self, fnActivate, fnSettings, fnUpdateMessageAges, fnCheckNetwork):

        self.fnActivate = fnActivate
        self.nMenuItems = 0
        self.nMessageAgeTimer = None
        self.nNetworkTimer = GLib.timeout_add_seconds(60, fnCheckNetwork)
        self.oMenuItemClear = None
        self.oMailIcon = Gio.Icon.new_for_string('mail-unread')
        self.nMessages = 0

        lstProcesses = [oProcess.name() for oProcess in psutil.process_iter()]

        if 'ayatana-indicator-messages-service' in lstProcesses:

            try:

                gi.require_version('AyatanaMessagingMenu', '1.0')
                self.oMessagingMenu = importlib.import_module('gi.repository.AyatanaMessagingMenu')

            except Exception as oException:

                gi.require_version('MessagingMenu', '1.0')
                self.oMessagingMenu = importlib.import_module('gi.repository.MessagingMenu')

        elif 'indicator-messages-service' in lstProcesses:

            gi.require_version('MessagingMenu', '1.0')
            self.oMessagingMenu = importlib.import_module('gi.repository.MessagingMenu')

        if self.oMessagingMenu:

            self.oIndicator = self.oMessagingMenu.App(desktop_id='ayatana-webmail.desktop')
            self.oIndicator.register()
            self.oIndicator.connect('activate-source', lambda a, i: self.onMenuItemClicked(i))

            return

        else:

            try:

                gi.require_version('AyatanaAppIndicator3', '0.1')
                self.oAppIndicator = importlib.import_module('gi.repository.AyatanaAppIndicator3')

            except Exception as oException:

                gi.require_version('AppIndicator3', '0.1')
                self.oAppIndicator = importlib.import_module('gi.repository.AppIndicator3')

        self.oIndicator = self.oAppIndicator.Indicator.new(APPNAME, 'ayatanawebmail-messages', self.oAppIndicator.IndicatorCategory.APPLICATION_STATUS)
        self.oIndicator.set_attention_icon('ayatanawebmail-messages-new')
        self.oIndicator.set_status(self.oAppIndicator.IndicatorStatus.ACTIVE)
        self.oMenu = Gtk.Menu()
        self.oMenu.append(Gtk.SeparatorMenuItem())
        oMenuItemInbox = Gtk.MenuItem()
        oMenuItemInbox.connect('activate', lambda w: openURLOrCommand('Home'))
        oBoxInbox = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 6)
        oBoxInbox.pack_start(Gtk.Image.new_from_stock(Gtk.STOCK_HOME, Gtk.IconSize.MENU), False, False, 0)
        oBoxInbox.pack_start(Gtk.Label(_('Open webmail home page'), xalign=0), True, True, 0)
        oMenuItemInbox.add(oBoxInbox)
        self.oMenu.append(oMenuItemInbox)
        self.oMenuItemClear = Gtk.MenuItem(sensitive=False)
        self.oMenuItemClear.connect('activate', self.onClear)
        oBoxClear = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 6)
        oBoxClear.pack_start(Gtk.Image.new_from_icon_name('gtk-clear', Gtk.IconSize.MENU), False, False, 0)
        oBoxClear.pack_start(Gtk.Label(_('Clear'), xalign=0), True, True, 0)
        self.oMenuItemClear.add(oBoxClear)
        self.oMenu.append(self.oMenuItemClear)
        oMenuItemConfig = Gtk.MenuItem()
        oMenuItemConfig.connect('activate', lambda w: fnSettings())
        oBoxConfig = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 6)
        oBoxConfig.pack_start(Gtk.Image.new_from_stock(Gtk.STOCK_PREFERENCES, Gtk.IconSize.MENU), False, False, 0)
        oBoxConfig.pack_start(Gtk.Label(_('Settings'), xalign=0), True, True, 0)
        oMenuItemConfig.add(oBoxConfig)
        self.oMenu.append(oMenuItemConfig)
        self.oMenu.show_all()
        self.oIndicator.set_menu(self.oMenu)
        self.nMenuItems = len(self.oMenu.get_children())
        self.nMessageAgeTimer = GLib.timeout_add_seconds(60, fnUpdateMessageAges)

    def getMessageAge(self, nTimestamp):

        nTimeDelta = int(time.time() - nTimestamp / 1000000)
        strGranularity = 'minute'

        if nTimeDelta > (7 * 24 * 60 * 60):
            strGranularity = 'week'
        elif nTimeDelta > (24 * 60 * 60):
            strGranularity = 'day'
        elif nTimeDelta > (60 * 60):
            strGranularity = 'hour'
        elif nTimeDelta < 60:
            nTimeDelta = 61

        return ' (' + format_timedelta(nTimeDelta, granularity=strGranularity, format='short', locale=locale.getlocale()[0]) + ')'

    def onMenuItemClicked(self, strId):

        if self.fnActivate(strId):

            self.setCount(-1, True)

            if not self.oMessagingMenu:
                self.remove(strId)

    def append(self, strId, strTitle, nTimestamp, bDrawAttention):

        if self.oMessagingMenu:

            self.oIndicator.append_source_with_time(strId, self.oMailIcon, strTitle, nTimestamp)

            if bDrawAttention:
                self.oIndicator.draw_attention(strId)

        else:

            oMenuItem = Gtk.MenuItem()
            oMenuItem.props.name = strId
            oMenuItem.connect('activate', lambda w: self.onMenuItemClicked(w.props.name))
            oBox = Gtk.Box(Gtk.Orientation.HORIZONTAL, 6)
            oBox.pack_start(Gtk.Image.new_from_icon_name('mail-unread', Gtk.IconSize.MENU), False, False, 0)
            oBox.pack_start(Gtk.Label(strTitle + self.getMessageAge(nTimestamp), xalign=0), True, True, 0)
            oMenuItem.add(oBox)
            oMenuItem.show_all()
            self.oMenu.insert(oMenuItem, len(self.oMenu.get_children()) - self.nMenuItems)

            if bDrawAttention:
                self.oIndicator.set_status(self.oAppIndicator.IndicatorStatus.ATTENTION)

            self.oMenuItemClear.set_sensitive(True)

        return False

    def remove(self, strId):

        if self.oMessagingMenu:

            if self.oIndicator.has_source(strId):
                self.oIndicator.remove_source(strId)

        else:

            for oItem in self.oMenu.get_children()[0:-self.nMenuItems]:

                if oItem.props.name == strId:
                    self.oMenu.remove(oItem)

            if len(self.oMenu.get_children()) - self.nMenuItems == 0:

                self.oIndicator.set_status(self.oAppIndicator.IndicatorStatus.ACTIVE)
                self.oMenuItemClear.set_sensitive(False)

        return False

    def hasSource(self, strId):

        if self.oMessagingMenu:

            return self.oIndicator.has_source(strId)

        else:

            for oItem in self.oMenu.get_children()[0:-self.nMenuItems]:

                if oItem.props.name == strId:
                    return True

        return False

    def close(self):

        if not self.oMessagingMenu:
            GLib.source_remove(self.nMessageAgeTimer)

        GLib.source_remove(self.nNetworkTimer)

    def update(self, strId, nTimestamp):

        for oItem in self.oMenu.get_children()[0:-self.nMenuItems]:

            if oItem.props.name == strId:

                oLabel = oItem.get_children()[0].get_children()[1]
                oLabel.set_text(oLabel.get_text().rpartition(' (')[0] + self.getMessageAge(nTimestamp))

        return False

    def onClear(self, oWidget):

        for oItem in self.oMenu.get_children()[0:-self.nMenuItems]:
            self.oMenu.remove(oItem)

        if len(self.oMenu.get_children()) - self.nMenuItems == 0:

            self.oIndicator.set_status(self.oAppIndicator.IndicatorStatus.ACTIVE)
            self.oMenuItemClear.set_sensitive(False)

        self.setCount(0, True)

    def setCount(self, nCount, bVisible):

        if nCount == -1:

            nCount = self.nMessages - 1

        bVisible = bVisible and ((nCount > 0) or not g_oSettings.get_boolean('hide-messages-count'))
        pBus = Gio.bus_get_sync(Gio.BusType.SESSION)
        pData = GLib.Variant("a{sv}", {"count": GLib.Variant("x", nCount), "count-visible": GLib.Variant("b", bVisible)})
        pParams = GLib.Variant.new_tuple(GLib.Variant("s", "application://ayatana-webmail.desktop"), pData)
        pBus.emit_signal(None, "/com/canonical/unity/launcherentry", "com.canonical.Unity.LauncherEntry", "Update", pParams)

        if not self.oMessagingMenu:

            self.oIndicator.set_label(str(nCount) if bVisible else '', '')

        self.nMessages = nCount

        return False

class SessionBus(dbus.service.Object):

    fnSettings = None
    fnClear = None
    fnIsInit = None

    def __init__(self, fnSettings, fnClear, fnIsInit, fnOpenURL):

        oBusName = dbus.service.BusName('org.ayatana.webmail', bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, oBusName, '/org/ayatana/webmail')

        self.fnSettings = fnSettings
        self.fnClear = fnClear
        self.fnIsInit = fnIsInit
        self.fnOpenURL = fnOpenURL

    @dbus.service.method('org.ayatana.webmail')
    def settings(self):
        self.fnSettings()

    @dbus.service.method('org.ayatana.webmail')
    def clear(self):
        self.fnClear()

    @dbus.service.method('org.ayatana.webmail')
    def isinit(self):
        return self.fnIsInit()

    @dbus.service.method('org.ayatana.webmail', in_signature='s')
    def openurl(self, strURL):
        return self.fnOpenURL(strURL)

class Connection(object):

    def __init__(self, sDebug, host, port, login, passwd, folder, fnIdle, strInbox):

        self.sDebug = sDebug
        self.strHost = host
        self.nPort = port
        self.strLogin = login
        self.strPasswd = passwd
        self.oImap = None
        self.lstNotificationQueue = []
        self.oIdler = None
        self.strFolder = folder
        self.fnIdle = fnIdle
        self.strInbox = strInbox
        self.bConnecting = False

    def close(self):

        if self.oIdler:

            self.oIdler.stop()
            self.oIdler.join()
            self.oIdler = None

        if self.oImap:

            try:
                self.oImap.close()
            except Exception as oException:
                pass

            try:
                self.oImap.logout()
            except Exception as oException:
                pass

            self.oImap = None

            if self.sDebug == 'info':

                logger.info('"{0}:{1}" has been cleaned up.'.format(self.strLogin, self.strFolder))

    def connect(self):

        try:

            self.oImap = imaplib.IMAP4_SSL(self.strHost, self.nPort, debug=int(self.sDebug == 'debug')*5)

        except Exception as e:

            logger.warning('"{0}:{1}" IMAP4_SSL failed, trying IMAP4.'.format(self.strLogin, self.strFolder))

            self.oImap = imaplib.IMAP4(self.strHost, self.nPort, debug=int(self.sDebug)*5)

            if 'STARTTLS' in self.oImap.capabilities:
                self.oImap.starttls()

        try:
            self.oImap.login(self.strLogin, self.strPasswd)

        except Exception as e:

            logger.error('"{0}:{1}" login failed.'.format(self.strLogin, self.strFolder))
            raise

        strFolderUTF7 = bytes(self.strFolder, 'utf-7').replace(b'+', b'&').replace(b' &', b'- &')

        if b' ' in strFolderUTF7:
            strFolderUTF7 = b'"' + strFolderUTF7 + b'"'

        if self.oImap.select(mailbox=strFolderUTF7)[0] != 'OK':

            raise Exception('Mailbox "{0}:{1}" does not exist.'.format(self.strLogin, self.strFolder))

        else:

            if self.sDebug == 'info':

                logger.info('"{0}:{1}" is now connected.'.format(self.strLogin, self.strFolder))

            self.fnIdle(self, False)
            self.oIdler = Idler(self, self.fnIdle, logger, self.sDebug)
            self.oIdler.start()

    def isOpen(self):

        return checkNetwork() and self.oImap and self.oImap.state != imaplib.LOGOUT and not self.oImap.Terminate

class Message(object):

    def __init__(self, oConnection, strUId, title, message_id, timestamp, strSender, thread_id=''):

        self.oConnection = oConnection
        self.strUId = strUId
        self.title = title
        self.message_id = message_id
        self.timestamp = timestamp
        self.thread_id = thread_id
        self.strSender = strSender

class AyatanaWebmail(object):

    def __init__(self, sDebug):

        self.sDebug = sDebug
        self.dlgSettings = None
        self.nLastMailTimestamp = 0
        self.first_run = True
        self.lstConnections = []
        self.lstUnreadMessages = []
        self.bDrawAttention = False
        self.bIdlerRunning = False
        self.bNoNetwork = True
        self.oMessagingMenu = MessagingMenu(self.onMenuItemClicked, self.openDialog, self.updateMessageAges, self.fnCheckNetwork)

        self.pGnomeSettings = Gio.Settings.new ('org.gnome.desktop.interface')
        self.pGnomeSettings.connect ('changed::color-scheme', self.onColorSchemeChanged)
        self.onColorSchemeChanged (self.pGnomeSettings, 'color-scheme')

        self.initKeyring()
        self.initConfig()
        DBusGMainLoop(set_as_default=True)
        SessionBus(self.openDialog, self.clear, lambda: bool(g_lstAccounts), openURLOrCommand)
        oSystemBus = dbus.SystemBus()
        oSystemBus.add_signal_receiver(self.onPrepareForSleep, 'PrepareForSleep', 'org.freedesktop.login1.Manager', 'org.freedesktop.login1')
        Notify.init('Ayatana Webmail')
        GLib.set_application_name('Ayatana Webmail')

        if not self.bIdlerRunning:

            self.bIdlerRunning = True

            for oConnection in self.lstConnections:
                oConnection.bConnecting = True

            GLib.timeout_add_seconds(5, self.connect, self.lstConnections)

        try:
            GLib.MainLoop().run()
        except KeyboardInterrupt:
            self.close(0)

    def onColorSchemeChanged (self, pSettings, sKey):

        sColorScheme = pSettings.get_string (sKey)
        bDark = (sColorScheme == 'prefer-dark')
        Gtk.Settings.get_default().props.gtk_application_prefer_dark_theme = bDark

    def onPrepareForSleep(self, bGoing):

        if not bGoing:

            if self.sDebug == 'info':

                logger.info('The System has resumed from sleep, reconnecting accounts.')

            for oConnection in self.lstConnections:

                oConnection.bConnecting = True
                oConnection.close()

            GLib.timeout_add_seconds(5, self.connect, self.lstConnections)

    def fnCheckNetwork(self):

        if not checkNetwork():

            if self.sDebug == 'info':

                logger.info('No network connection, checking in 1 minute.')

            self.bNoNetwork = True
            self.bIdlerRunning = False

        elif self.bNoNetwork:

            self.bNoNetwork = False
            self.bIdlerRunning = True

            for oConnection in self.lstConnections:
                oConnection.bConnecting = True

            GLib.timeout_add_seconds(5, self.connect, self.lstConnections)

        return True

    def clear(self):

        # WARNING: loadDataFromDicts also calls this!
        if g_lstAccounts:

            for oMessage in self.lstUnreadMessages:

                #self.markMessageAsRead(message)
                GLib.idle_add(self.oMessagingMenu.remove, oMessage.message_id)
                time.sleep(0.01)

            self.setLauncherCount(0)

    def closeConnections(self):

        for oConnection in self.lstConnections:
            oConnection.close()

        self.lstConnections = []
        self.bIdlerRunning = False

    def close(self, nCode):

        pBus = Gio.bus_get_sync(Gio.BusType.SESSION)
        pData = GLib.Variant("a{sv}", {"count": GLib.Variant("x", 0), "count-visible": GLib.Variant("b", False)})
        pParams = GLib.Variant.new_tuple(GLib.Variant("s", "application://ayatana-webmail.desktop"), pData)
        pBus.emit_signal(None, "/com/canonical/unity/launcherentry", "com.canonical.Unity.LauncherEntry", "Update", pParams)
        self.oMessagingMenu.close()
        self.closeConnections()
        print()
        sys.exit(nCode)

    def onMenuItemClicked(self, strId):

        for message in self.lstUnreadMessages:

            if message.message_id == strId:

                if self.nMessageAction == MESSAGEACTION['MARK']:

                    self.markMessageAsRead(message)

                elif self.nMessageAction == MESSAGEACTION['ASK']:

                    dlg = DialogActions(message.strSender, message.title)
                    nResponse = dlg.run()
                    dlg.destroy()

                    if nResponse == 100:

                        try:

                            if any(s in message.oConnection.strHost for s in ['gmail', 'google']):

                                message.oConnection.oImap.uid('STORE', message.strUId, '+X-GM-LABELS', '\\Trash')

                            else:

                                message.oConnection.oImap.uid('STORE', message.strUId, '+FLAGS', '\\Deleted')
                                message.oConnection.oImap.expunge()

                        except (imaplib.IMAP4.error, socketerror) as oError:

                            logger.error(str(oError))

                    elif nResponse == 200:

                        self.markMessageAsRead(message)

                    elif nResponse == 300:

                        openURLOrCommand(message.oConnection.strInbox.replace('$MSG_THREAD', message.thread_id).replace('$MSG_UID', message.strUId.decode('utf-8')))

                    else:

                        self.bDrawAttention = not message.timestamp < self.nLastMailTimestamp
                        self.appendToIndicator(message)
                        self.bDrawAttention = False
                        return False

                else:

                    openURLOrCommand(message.oConnection.strInbox.replace('$MSG_THREAD', message.thread_id).replace('$MSG_UID', message.strUId.decode('utf-8')))

        # True removes the message from Appindicator3
        return True

    def markMessageAsRead(self, message):

        # Mark entire conversation
        lstIndexes = [message.strUId]

        if message.thread_id and self.bMergeConversation:

            lstSearch = []

            try:

                lstSearch = message.oConnection.oImap.uid('SEARCH', None, '(X-GM-THRID ' + str(int(message.thread_id, 16)) + ')')

            except imaplib.IMAP4.error as oError:

                logger.error(str(oError))
                return

            if lstSearch[1][0] is not None:
                lstIndexes = [m for m in lstSearch[1][0].split()]

        for strIndex in lstIndexes:

            try:

                message.oConnection.oImap.uid('STORE', strIndex, '+FLAGS', '\\Seen')

            except (imaplib.IMAP4.error, socketerror) as e:

                logger.error(str(e))

    def initConfig(self):

        self.nMaxCount = g_oSettings.get_int('max-item-count')
        self.bEnableNotifications = g_oSettings.get_boolean('enable-notifications')
        self.bPlaySound = g_oSettings.get_boolean('enable-sound')
        self.bHideCount = g_oSettings.get_boolean('hide-messages-count')
        self.strCommand = g_oSettings.get_string('exec-on-receive')
        self.custom_sound = g_oSettings.get_string('custom-sound')
        self.bMergeConversation = g_oSettings.get_boolean('merge-messages')
        self.nMessageAction = g_oSettings.get_enum('message-action')

    def initKeyring(self):

        bus = secretstorage.dbus_init()

        try:

            self.collection = secretstorage.get_default_collection(bus)
            self.collection.is_locked()

        except secretstorage.SecretStorageException as e:

            logger.critical(str(e))
            self.close(1)

        if self.collection.is_locked():
            self.collection.unlock()

        if self.collection.is_locked():

            logger.critical('Failed to unlock the collection, exiting.')
            self.close(1)

        self.mail_keys = list(self.collection.search_items({'application': 'ayatana-webmail'}))

        if not self.mail_keys:
            self.openDialog()

        if not g_lstAccounts:

            for key in sorted(self.mail_keys, key=lambda item: item.item_path):

                dctAttributes = key.get_attributes()
                strHost = dctAttributes['server']
                nPort = int(dctAttributes['port'])
                strLogin = dctAttributes['username']
                strPasswd = key.get_secret().decode('utf-8')
                strFolders = dctAttributes['folders']
                strHome = dctAttributes['home']
                strCompose = dctAttributes['compose']
                strInbox = dctAttributes['inbox']
                strSent = dctAttributes['sent']
                strInboxAppend = dctAttributes['InboxAppend']

                g_lstAccounts.append({'Host': strHost, 'Port': nPort, 'Login': strLogin, 'Passwd': strPasswd, 'Folders': strFolders, 'Home': strHome, 'Compose': strCompose, 'Inbox': strInbox, 'Sent': strSent, 'InboxAppend': strInboxAppend})

                for strFolder in strFolders.split('\t'):
                    self.lstConnections.append(Connection(self.sDebug, strHost, nPort, strLogin, strPasswd, strFolder, self.onIdle, strInbox + strInboxAppend))

    def createKeyringItem(self, ind, update=False):

        attrs = {'application': 'ayatana-webmail', 'service': 'imap', 'server': g_lstAccounts[ind]['Host'], 'port': str(g_lstAccounts[ind]['Port']), 'username': g_lstAccounts[ind]['Login'], 'folders': g_lstAccounts[ind]['Folders'], 'home': g_lstAccounts[ind]['Home'], 'compose': g_lstAccounts[ind]['Compose'], 'inbox': g_lstAccounts[ind]['Inbox'], 'sent': g_lstAccounts[ind]['Sent'], 'InboxAppend': g_lstAccounts[ind]['InboxAppend']}
        label = 'ayatana-webmail: ' + g_lstAccounts[ind]['Login'] + ' at ' + g_lstAccounts[ind]['Host']

        if update:

            self.mail_keys[ind].set_attributes(attrs)
            self.mail_keys[ind].set_secret(g_lstAccounts[ind]['Passwd'])
            self.mail_keys[ind].set_label(label)

        else:

            self.collection.unlock()
            self.collection.create_item(label, attrs, g_lstAccounts[ind]['Passwd'], True)

    def openDialog(self):

        if not self.dlgSettings:

            self.dlgSettings = PreferencesDialog()
            self.dlgSettings.connect('response', self.onDialogResponse)

            if self.mail_keys:
                self.dlgSettings.setAccounts(g_lstAccounts)

            self.dlgSettings.run()
            self.dlgSettings.destroy()
            self.dlgSettings = None

    def onDialogResponse(self, dlg, response):

        global g_lstAccounts

        if response == Gtk.ResponseType.APPLY:

            dlg.updateAccounts()
            dlg.saveAllSettings()

            g_lstAccounts = dlg.lstDicts[:]

            self.loadDataFromDicts()

            for index in range(len(g_lstAccounts), len(self.mail_keys)):

                # Remove old keys
                self.mail_keys[index].delete()

            for index in range(len(g_lstAccounts)):

                # Create new keys or update existing
                self.createKeyringItem(index, update=(index < len(self.mail_keys)))

            self.mail_keys = list(self.collection.search_items({'application': 'ayatana-webmail'}))

            if self.mail_keys and g_lstAccounts and all(self.lstConnections) and not self.bIdlerRunning:

                self.bIdlerRunning = True

                for oConnection in self.lstConnections:
                    oConnection.bConnecting = True

                GLib.timeout_add_seconds(5, self.connect, self.lstConnections)

        if response in [Gtk.ResponseType.APPLY, Gtk.ResponseType.CANCEL]:
            dlg.destroy()

    def loadDataFromDicts(self):

        self.closeConnections()
        self.initConfig()
        self.clear()
        self.lstUnreadMessages = []
        self.nLastMailTimestamp = 0
        self.first_run = True

        for dct in g_lstAccounts:

            strFolders = 'INBOX'

            try:
                strFolders = dct['Folders']
            except KeyError:
                pass

            nPort = 993

            try:
                nPort = int(dct['Port'])
            except ValueError:
                pass

            for strFolder in strFolders.split('\t'):
                self.lstConnections.append(Connection(self.sDebug, dct['Host'], nPort, dct['Login'], dct['Passwd'], strFolder, self.onIdle, dct['Inbox'] + dct['InboxAppend']))

    def appendToIndicator(self, message):

        if self.oMessagingMenu.hasSource(message.message_id):
            return

        title = message.title

        if len(title) > 50:
            title = title[:50] + '...'

        if len(g_lstAccounts) > 1:
            title = '↪ ' + message.oConnection.strLogin + '\n' + title

        GLib.idle_add(self.oMessagingMenu.append, message.message_id, title, message.timestamp, self.bDrawAttention)
        time.sleep(0.01)

    def onIdle(self, oConnection, bAborted):

        if bAborted or not oConnection.isOpen():

            if not oConnection.bConnecting:

                oConnection.bConnecting = True
                GLib.timeout_add_seconds(1, oConnection.close)

                if self.sDebug == 'info':

                    logger.info('"{0}:{1}" will try to reconnect in 1 minute.'.format(oConnection.strLogin, oConnection.strFolder))

                GLib.timeout_add_seconds(60, self.connect, [oConnection])

            return

        lstMessages = []
        lstNewMessages = []
        lstUnread = []

        search = oConnection.oImap.uid('SEARCH', '(UNSEEN)')

        if search[1][0] is not None:
            lstMessages = search[1][0].split()

        for m in lstMessages[-1 * (self.nMaxCount // len(self.lstConnections)) : ]:

            typ = None
            msg_data = None
            thread_id = ''
            msg = None

            if any(s in oConnection.strHost for s in ['gmail', 'google']):

                typ, msg_data = oConnection.oImap.uid('FETCH', m, '(X-GM-THRID BODY.PEEK[HEADER.FIELDS (DATE SUBJECT FROM MESSAGE-ID)])')

                for lstField in msg_data:

                    if 'THRID' in str(lstField):

                        thread_id = '%x' % int(m_reThrid.search(lstField[0]).group(1))
                        break

            else:

                typ, msg_data = oConnection.oImap.uid('FETCH', m, '(BODY.PEEK[HEADER.FIELDS (DATE SUBJECT FROM MESSAGE-ID)])')

            for response_part in msg_data:

                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

            if msg is None:
                continue

            message_id = msg['Message-Id']

            if not isinstance(message_id, str):
                message_id = oConnection.strHost + ':' + oConnection.strLogin + ':' + oConnection.strFolder + ':' + str(m.decode())

            bMessageExists = False

            for cMessage in self.lstUnreadMessages:

                if cMessage.message_id == message_id:

                    bMessageExists = True
                    break

            if not bMessageExists:

                sender = getHeaderWrapper(msg, 'From', True)
                subj = getHeaderWrapper(msg, 'Subject', True)
                date = getHeaderWrapper(msg, 'Date', False)

                try:

                    tuple_time = email.utils.parsedate_tz(date)
                    timestamp = email.utils.mktime_tz(tuple_time)

                    if timestamp > time.time():

                        # Message time is larger than the current one
                        timestamp = time.time()

                except TypeError:

                    # Failed to get time from message
                    timestamp = time.time()

                # Number of seconds to number of microseconds
                timestamp *= (10**6)

                while subj.lower().startswith('re:'):
                    subj = subj[3:]

                while subj.lower().startswith('fwd:'):
                    subj = subj[4:]

                subj = subj.strip()

                if sender.startswith('"'):

                    pos = sender[1:].find('"')

                    if pos >= 0:
                        sender = sender[1:pos+1]+sender[pos+2:]

                ilabel = subj if subj else _('No subject')

                # Display only last message in thread
                bConversationInUnread = False
                bConversationInNew = False

                if thread_id and self.bMergeConversation:

                    for oMessage in self.lstUnreadMessages:

                        if oMessage.thread_id == thread_id:

                            oMessage.timestamp = max(timestamp, oMessage.timestamp)
                            bConversationInUnread = True
                            break

                    if not bConversationInUnread:

                        for oMessage in lstNewMessages:

                            if oMessage.thread_id == thread_id:

                                oMessage.timestamp = max(timestamp, oMessage.timestamp)
                                bConversationInNew = True
                                break

                if not bConversationInUnread and not bConversationInNew:

                    message = Message(oConnection, m, ilabel, message_id, timestamp, sender, thread_id)
                    lstNewMessages.append(message)

                if timestamp > self.nLastMailTimestamp:

                    if self.bEnableNotifications:

                        if not bConversationInNew:

                            oConnection.lstNotificationQueue.append([sender, subj, oConnection, thread_id])

                        else:

                            for lstNotification in oConnection.lstNotificationQueue:

                                if lstNotification[3] == thread_id:

                                    lstNotification[0] = sender
                                    break

                    self.nLastMailTimestamp = timestamp
                    self.bDrawAttention = True

                if self.strCommand and not self.first_run:

                    try:

                        subprocess.call((self.strCommand, sender, ilabel, oConnection.strHost))

                    except OSError as e:

                        # File doesn't exist or is not executable
                        logger.warning('Cannot execute command: {0}'.format(str(e)))

            else:

                lstUnread.append(message_id)

        self.updateIndicator(lstNewMessages, [oMessage for oMessage in self.lstUnreadMessages if oMessage.oConnection == oConnection and oMessage.message_id not in lstUnread], oConnection)

    def updateIndicator(self, lstNewMessages, lstRemovedMessages, oConnection):

        for oMessage in [oMessage for oMessage in self.lstUnreadMessages if oMessage.oConnection == oConnection]:

            # Removed outside the app
            if oMessage in lstRemovedMessages:

                GLib.idle_add(self.oMessagingMenu.remove, oMessage.message_id)
                time.sleep(0.01)

            # Cleared
            if not self.oMessagingMenu.hasSource(oMessage.message_id) and oMessage not in lstNewMessages:

                self.markMessageAsRead(oMessage)
                self.lstUnreadMessages.remove(oMessage)

        self.lstUnreadMessages = sorted(self.lstUnreadMessages + lstNewMessages, key=lambda m: m.timestamp)[-self.nMaxCount:]

        #logger.debug('Unread: {0}, New: {1}, Removed: {2}'.format(len(self.lstUnreadMessages), len(lstNewMessages), len(lstRemovedMessages)))

        if lstNewMessages:

            for cMessage in lstNewMessages:

                self.appendToIndicator(cMessage)

        try:

            if self.first_run and oConnection != self.lstConnections[-1]:

                pass

            elif self.first_run and oConnection == self.lstConnections[-1]:

                self.showNotifications()
                self.first_run = False

            elif lstNewMessages:

                self.showNotifications()

        except GLib.GError as e:

            logger.warning(str(e))

        self.setLauncherCount(len(self.lstUnreadMessages))

        if not self.first_run:
            self.bDrawAttention = False

    def updateMessageAges(self):

        for oMessage in self.lstUnreadMessages:

            GLib.idle_add(self.oMessagingMenu.update, oMessage.message_id, oMessage.timestamp)
            time.sleep(0.01)

        return True

    def connect(self, lstConnections):

        if self.sDebug == 'info':

            logger.info('Checking network...')

        if not checkNetwork():

            return False

        if (lstConnections):

            if self.sDebug == 'info':

                logger.info('Network connection active, connecting...')

            for oConnection in lstConnections:

                oConnection.close()

                try:

                    oConnection.connect()
                    oConnection.bConnecting = False

                except KeyboardInterrupt:

                    self.close(0)

                except Exception as oException:

                    logger.error('"{0}:{1}" could not connect: {2}'.format(oConnection.strLogin, oConnection.strFolder, str(oException)))

                    oNotification = Notify.Notification.new(_('Connection error'), '', APPNAME)
                    oNotification.set_property('body', _('Unable to connect to account "{accountName}", the application will now exit.').format(accountName=oConnection.strLogin))
                    oNotification.set_hint('desktop-entry', GLib.Variant.new_string(APPNAME))
                    oNotification.set_timeout(Notify.EXPIRES_NEVER)
                    oNotification.show()
                    self.close(1)

        return False

    def setLauncherCount(self, nCount):

        GLib.idle_add(self.oMessagingMenu.setCount, nCount, any([oImap for oImap in self.lstConnections]))
        time.sleep(0.01)

    def showNotifications(self):

        lstNotificationsQueue = []

        for oConnection in self.lstConnections:

            if oConnection:

                lstNotificationsQueue += oConnection.lstNotificationQueue
                oConnection.lstNotificationQueue = []

        number_of_mails = len(lstNotificationsQueue)
        basemessage = g_oTranslation.ngettext('You have %d unread message', 'You have %d unread messages', number_of_mails)
        basemessage = basemessage.replace('%d', '{0}')

        if number_of_mails and self.bPlaySound:

            try:

                if self.custom_sound:
                    subprocess.call(('canberra-gtk-play', '-f', self.custom_sound))
                else:
                    subprocess.call(('canberra-gtk-play', '-i', 'message-new-email'))

            except OSError as e:

                logger.warning(str(e))

        if number_of_mails > 1:

            senders = set(getSenderName(lstNotification[0]) for lstNotification in lstNotificationsQueue)
            unknown_sender = ('' in senders)

            if unknown_sender:
                senders.remove('')

            ts = tuple(senders)

            if len(ts) > 2 or (len(ts) == 2 and unknown_sender):
                message = fixFormat(_('from %(t0)s, %(t1)s and others')).format(t0=ts[0], t1=ts[1])
            elif len(ts) == 2 and not unknown_sender:
                message = fixFormat(_('from %(t0)s and %(t1)s')).format(t0=ts[0], t1=ts[1])
            elif len(ts) == 1 and not unknown_sender:
                message = _('from %s').replace('%s', '{0}').format(getSenderName(ts[0]))
            else:
                message = None

            oNotification = Notify.Notification.new(basemessage.format(number_of_mails), message, APPNAME)
            oNotification.set_hint('desktop-entry', GLib.Variant.new_string(APPNAME))
            oNotification.show()

        elif number_of_mails:

            lstNotification = lstNotificationsQueue[0]

            if lstNotification[0]:
                message = _('New mail from %s').replace('%s', '{0}').format(getSenderName(lstNotification[0]))
            else:
                message = basemessage.format(1)

            oNotification = Notify.Notification.new(message, lstNotification[1], APPNAME)
            oNotification.set_hint('desktop-entry', GLib.Variant.new_string(APPNAME))
            oNotification.show()
