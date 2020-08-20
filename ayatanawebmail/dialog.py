#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Ayatana Webmail, the Preferences Dialog
# Authors: Dmitry Shachnev <mitya57@gmail.com>
#          Robert Tari <robert@tari.in>
# License: GNU GPL 3 or higher; http://www.gnu.org/licenses/gpl.html

import ayatanawebmail.imaplib2 as imaplib
import os.path
from socket import error as socketerror
from gi.repository import Gtk, GdkPixbuf, Gdk
from ayatanawebmail.common import g_oSettings, getDataPath, g_dctDefaultURLs
from ayatanawebmail.appdata import APPVERSION, APPURL, APPDESCRIPTION, APPAUTHOR, APPYEAR, APPTITLE
import webbrowser

MESSAGEACTION = {'OPEN': 1, 'MARK': 2, 'ASK': 3}

def utf7dec(lstInput):

    if not isinstance(lstInput, bytes):

        return lstInput

    lstResult = []
    lstBytes = bytearray()

    for nChar in lstInput:

        if nChar == b'&'[0] and not lstBytes:

            lstBytes.append(nChar)

        elif nChar == b'-'[0] and lstBytes:

            if len(lstBytes) == 1:
                lstResult.append('&')
            else:
                lstResult.append((b'+' + lstBytes[1:].replace(b',', b'/') + b'-').decode('utf-7'))

            lstBytes = bytearray()

        elif lstBytes:

            lstBytes.append(nChar)

        else:

            lstResult.append(chr(nChar))

    if lstBytes:
        lstResult.append((b'+' + lstBytes[1:].replace(b',', b'/') + b'-').decode('utf-7'))

    return ''.join(lstResult)

class ComboEntry(Gtk.ButtonBox):

    def __init__(self, strId, **kwargs):

        Gtk.ButtonBox.__init__(self, orientation=Gtk.Orientation.HORIZONTAL, layout_style=Gtk.ButtonBoxStyle.EXPAND, **kwargs)

        self.oComboBoxText = Gtk.ComboBoxText()
        self.oComboBoxText.append('HTTP:', _('Web page'))
        self.oComboBoxText.append('Exec:', _('Command'))
        self.oEntry = Gtk.Entry()
        self.oEntry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, 'gtk-revert-to-saved-ltr')
        self.oEntry.connect('icon-press', self.onReset)
        self.oComboBoxText.set_active_id('HTTP:')
        self.pack_start(self.oComboBoxText, False, False, 0)
        self.pack_start(self.oEntry, True, True, 0)
        self.set_homogeneous(False)
        self.strId = strId

    def onReset(self, oWidget, nPosition, oEvent):

        self.setText(g_dctDefaultURLs[self.strId]);

    def setText(self, strText):

        self.oEntry.set_text(strText[5:] if strText.startswith('Exec:') else strText)
        self.oComboBoxText.set_active_id('Exec:' if strText.startswith('Exec:') else 'HTTP:')

    def getText(self):

        return ('Exec:' if self.oComboBoxText.get_active_id() == 'Exec:' else '') + self.oEntry.get_text()

class EntryReset(Gtk.Entry):

    def __init__(self, oComboEntry, **kwargs):

        Gtk.Entry.__init__(self, **kwargs)

        self.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, 'gtk-revert-to-saved-ltr')
        self.connect('icon-press', self.onReset)
        self.oComboEntry = oComboEntry
        self.set_tooltip_text(_('Append an additional string - you can use the $MSG_THREAD and $MSG_UID placeholders.'))

    def onReset(self, oWidget, nPosition, oEvent):

        strText = ''

        if self.oComboEntry.oComboBoxText.get_active_id() == 'HTTP:' and self.oComboEntry.getText() == g_dctDefaultURLs['Inbox']:
            strText = '/$MSG_THREAD'

        self.set_text(strText);

class FileChooserButtonEx(Gtk.ButtonBox):

    def __init__(self, strFilename, **kwargs):

        Gtk.ButtonBox.__init__(self, orientation=Gtk.Orientation.HORIZONTAL, layout_style=Gtk.ButtonBoxStyle.EXPAND, **kwargs)

        oButtonClear = Gtk.Button.new_from_icon_name('gtk-clear', Gtk.IconSize.BUTTON)
        oButtonClear.connect('clicked', self.onClear)
        oButtonOpen = Gtk.Button()
        oButtonOpen.connect('clicked', self.onOpen)
        self.oLabel = Gtk.Label(os.path.basename(strFilename) or _('(None)'), xalign=0, margin_left=5)
        oImage = Gtk.Image.new_from_icon_name('gtk-open', Gtk.IconSize.BUTTON)
        oBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        oBox.pack_start(oImage, False, False, 0)
        oBox.pack_start(self.oLabel, True, True, 0)
        oButtonOpen.add(oBox)
        self.pack_start(oButtonOpen, True, True, 0)
        self.pack_start(oButtonClear, False, False, 0)
        self.set_homogeneous(False)
        self.strFilename = strFilename

    def onClear(self, oWidget):

        self.strFilename = ''
        self.oLabel.set_text(_('(None)'))

    def onOpen(self, oWidget):

        oDlg = Gtk.FileChooserDialog(None, oWidget.get_toplevel(), 0, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.APPLY))

        if self.strFilename:
            oDlg.set_filename(self.strFilename)

        nResponse = oDlg.run()

        if nResponse == Gtk.ResponseType.APPLY:

            self.strFilename = oDlg.get_filename()
            self.oLabel.set_text(os.path.basename(self.strFilename))

        oDlg.destroy()

    def getFilename(self):

        return self.strFilename

class PreferencesDialog(Gtk.Dialog):

    def __init__(self):

        self.bInit = False
        self.initConfig()
        Gtk.Dialog.__init__(self, _('Ayatana Webmail Preferences'), None, 0, (Gtk.STOCK_CONNECT, 100, Gtk.STOCK_APPLY, Gtk.ResponseType.APPLY, Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        self.set_icon_name('ayatana-webmail')
        self.connect('destroy', lambda w: Gtk.main_quit())
        self.connect('response', self.onResponse)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_property('width-request', 640)
        self.set_property('height-request', 480)
        self.oNotebook = Gtk.Notebook(vexpand=True, margin_left=5, margin_top=5, margin_right=5)
        self.oNotebook.append_page(self.pageAccounts(), Gtk.Label(_('Accounts')))
        self.oNotebook.append_page(self.pageOptions(), Gtk.Label(_('Options')))
        self.oNotebook.append_page(self.pageSupport(), Gtk.Label(_('Support')))
        self.oNotebook.append_page(self.pageAbout(), Gtk.Label(_('About')))
        oContentArea = self.get_content_area()
        oContentArea.set_property('vexpand', True)
        oContentArea.add(self.oNotebook)
        self.oButtonConnect = self.get_widget_for_response(100)
        self.oButtonApply = self.get_widget_for_response(Gtk.ResponseType.APPLY)
        self.lstDicts = [{'Host': 'imap.example.com', 'Port': '993', 'Login': '', 'Passwd': '', 'Folders': 'INBOX', 'InboxAppend': '/$MSG_THREAD'}]
        self.lstDicts[0].update(g_dctDefaultURLs)
        self.set_keep_above(True)
        self.show_all()
        self.bInit = True
        self.nIndex = 0

    def onResponse(self, oWidget, nResponse):

        if nResponse == 100:

            self.oNotebook.set_current_page(0)
            self.oListStore.clear()
            self.getFolderList(True)
            self.updateUI()

    def getFolderList(self, bAutoselect):

        try:

            oImap = None

            try:

                oImap = imaplib.IMAP4_SSL(self.EntryHost.get_text(), int(self.EntryPort.get_text()))

            except Exception:

                oImap = imaplib.IMAP4(self.EntryHost.get_text(), int(self.EntryPort.get_text()))
                oImap.starttls()

            oImap.login(self.EntryLogin.get_text(), self.EntryPassword.get_text())

            for f in oImap.list()[1]:

                flags, b, c = utf7dec(f).partition(' ')
                separator, b, strName = c.partition(' ')
                strName = strName.replace('"', '').replace('/ ', '')

                if strName != '[Gmail]' and 'All Mail' not in strName:
                    self.oListStore.append([strName, strName.replace('[Gmail]/', ''), strName.upper() == 'INBOX' if bAutoselect else False])

            oImap.logout()

        except (imaplib.IMAP4.error, socketerror) as oError:

            oDlg = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE, '')

            strError = str(oError)

            if strError.startswith("b'"):
                strError = strError[1:]

            if 'https://support.google.com/mail/accounts/answer/78754' in strError:

                oDlg.set_markup( _('Please visit the following link and enable access for less secure apps:') + '\n\n<a href="https://www.google.com/settings/security/lesssecureapps">https://www.google.com/settings/security/lesssecureapps</a>')
                oDlg.set_property('message_type', Gtk.MessageType.INFO)
                oDlg.set_title(_('Access blocked by Google'))

            else:

                oDlg.set_property('text', _('Failed to connect to mail account. The returned error was:') + '\n\n' + strError)
                oDlg.set_title(_('Connection failure'))

            oDlg.run()
            oDlg.destroy()

    def initConfig(self):

        self.bEnableNotifications = g_oSettings.get_boolean('enable-notifications')
        self.bPlaySound = g_oSettings.get_boolean('enable-sound')
        self.bHideCount = g_oSettings.get_boolean('hide-messages-count')
        self.strCommand = g_oSettings.get_string('exec-on-receive')
        self.strCustomSound = g_oSettings.get_string('custom-sound')
        self.bMergeConversation = g_oSettings.get_boolean('merge-messages')
        self.nMessageAction = g_oSettings.get_enum('message-action')

    def pageAccounts(self):

        acclabel = Gtk.Label(xalign=0, hexpand=True)
        acclabel.set_markup('<b>'+_('Choose an account')+'</b>')
        self.sb = Gtk.SpinButton.new_with_range(1, 1, 1)
        self.sb.set_numeric(True)
        self.sb.set_update_policy(Gtk.SpinButtonUpdatePolicy.IF_VALID)
        self.sb.connect('value-changed', self.onAccountChanged)
        self.addbtn = Gtk.Button.new_with_label(_('Add'))
        self.addbtn.connect('clicked', self.onAddAccount)
        self.rmbtn = Gtk.Button.new_with_label(_('Remove'))
        self.rmbtn.connect('clicked', self.onRemoveAccount)
        accbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5, hexpand=True)
        accbox.pack_start(self.sb, True, True, 0)
        accbox.pack_end(self.rmbtn, False, False, 0)
        accbox.pack_end(self.addbtn, False, False, 0)
        self.EntryHost = Gtk.Entry(hexpand=True)
        self.EntryHost.connect('changed', lambda w: self.updateUI())
        self.EntryPort = Gtk.Entry(hexpand=True)
        self.EntryPort.connect('changed', lambda w: self.updateUI())
        self.EntryLogin = Gtk.Entry(hexpand=True)
        self.EntryLogin.connect('changed', lambda w: self.updateUI())
        self.EntryPassword = Gtk.Entry(visibility=False, caps_lock_warning=True, hexpand=True)
        self.EntryPassword.connect('changed', lambda w: self.updateUI())
        srvlabel = Gtk.Label(xalign=0, margin_top=5, hexpand=True)
        srvlabel.set_markup('<b>'+_('Server data')+'</b>')
        infolabel = Gtk.Label(xalign=0, margin_top=5, hexpand=True)
        infolabel.set_markup('<b>'+_('Account data')+'</b>')
        self.oListStore = Gtk.ListStore(str, str, bool)
        oTreeView = Gtk.TreeView(self.oListStore, headers_visible=False, activate_on_single_click=True, margin_left=5, margin_top=5, margin_right=5, margin_bottom=5)
        oTreeView.set_property('height-request', 200)
        oTreeView.connect('row-activated', self.onFolderActivated)
        oTreeViewColumnBool = Gtk.TreeViewColumn('bool', Gtk.CellRendererToggle(), active=2)
        oTreeViewColumnBool.get_cells()[0].set_property('xalign', 1.0)
        oTreeView.append_column(Gtk.TreeViewColumn('folder', Gtk.CellRendererText(), text=1))
        oTreeView.append_column(oTreeViewColumnBool)
        oFrame = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN, hexpand=True, vexpand=True)
        oFrame.add(oTreeView)
        oLabelLinks = Gtk.Label(xalign=0, margin_top=5, hexpand=True)
        oLabelLinks.set_markup('<b>'+_('Links')+'</b>')
        self.oEntryHome = ComboEntry('Home', hexpand=True)
        self.oEntryCompose = ComboEntry('Compose', hexpand=True)
        self.oEntryInbox = ComboEntry('Inbox', hexpand=True)
        self.oEntrySent = ComboEntry('Sent', hexpand=True)
        self.oEntryInboxAppend = EntryReset(self.oEntryInbox)
        oGrid = Gtk.Grid(row_spacing=5, column_spacing=5, vexpand=True)
        oGrid.attach(srvlabel, 0, 0, 3, 1)
        oGrid.attach(Gtk.Label(_('Host:'), xalign=0, margin_right=5), 0, 1, 1, 1)
        oGrid.attach(self.EntryHost, 1, 1, 2, 1)
        oGrid.attach(Gtk.Label(_('Port:'), xalign=0, margin_right=5), 0, 2, 1, 1)
        oGrid.attach(self.EntryPort, 1, 2, 2, 1)
        oGrid.attach(infolabel, 0, 3, 3, 1)
        oGrid.attach(Gtk.Label(_('Login:'), xalign=0, margin_right=5), 0, 4, 1, 1)
        oGrid.attach(self.EntryLogin, 1, 4, 2, 1)
        oGrid.attach(Gtk.Label(_('Password:'), xalign=0, margin_right=5), 0, 5, 1, 1)
        oGrid.attach(self.EntryPassword, 1, 5, 2, 1)
        oGrid.attach(Gtk.Label(_('Folders:'), xalign=0, margin_right=5), 0, 6, 1, 1)
        oGrid.attach(oFrame, 1, 6, 2, 1)
        oGrid.attach(oLabelLinks, 0, 7, 3, 1)
        oGrid.attach(Gtk.Label(_('Home:'), xalign=0, margin_right=5), 0, 8, 1, 1)
        oGrid.attach(self.oEntryHome, 1, 8, 2, 1)
        oGrid.attach(Gtk.Label(_('Compose:'), xalign=0, margin_right=5), 0, 9, 1, 1)
        oGrid.attach(self.oEntryCompose, 1, 9, 2, 1)
        oGrid.attach(Gtk.Label(_('Inbox:'), xalign=0, margin_right=5), 0, 10, 1, 1)
        oGrid.attach(self.oEntryInbox, 1, 10, 1, 1)
        oGrid.attach(self.oEntryInboxAppend, 2, 10, 1, 1)
        oGrid.attach(Gtk.Label(_('Sent:'), xalign=0, margin_right=5), 0, 11, 1, 1)
        oGrid.attach(self.oEntrySent, 1, 11, 2, 1)
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, border_width=10, vexpand=True)
        page.add(acclabel)
        page.add(accbox)
        page.add(oGrid)
        oScrolledWindow = Gtk.ScrolledWindow()
        oScrolledWindow.add(page)

        nHeight = 721
        oDisplay = Gdk.Display.get_default()

        if oDisplay:

            oMonitor = None

            # get_primary_monitor is available in >= 3.22
            try:
                oMonitor = oDisplay.get_primary_monitor()
            except Exception as oException:
                pass

            if oMonitor:
                nHeight = oMonitor.get_workarea().height

        if nHeight > 720:

            # propagate_natural_height is available in >= 3.22
            try:
                oScrolledWindow.props.propagate_natural_height = True
            except Exception as oException:
                pass

        return oScrolledWindow

    def pageOptions(self):

        self.oComboMessageAction = Gtk.ComboBoxText()
        self.oComboMessageAction.append(str(MESSAGEACTION['MARK']), _('Mark message as read'))
        self.oComboMessageAction.append(str(MESSAGEACTION['OPEN']), _('Open message in browser/Execute command'))
        self.oComboMessageAction.append(str(MESSAGEACTION['ASK']), _('Ask me what to do'))
        self.oComboMessageAction.set_active_id(str(self.nMessageAction))
        self.oSwitchMerge = Gtk.Switch(active=self.bMergeConversation, halign=Gtk.Align.END)
        self.notifyswitch = Gtk.Switch(active=self.bEnableNotifications, halign=Gtk.Align.END)
        self.sndswitch = Gtk.Switch(active=self.bPlaySound, halign=Gtk.Align.END)
        self.sndswitch.connect('notify::active', self.onSoundSwitchActivate)
        self.hcswitch = Gtk.Switch(active=self.bHideCount, halign=Gtk.Align.END)
        self.commandchooser = FileChooserButtonEx(self.strCommand)
        self.sndchooser = FileChooserButtonEx(self.strCustomSound)
        oGrid = Gtk.Grid(row_spacing=5, column_spacing=10)
        oGrid.attach(Gtk.Label(_('Enable notifications:'), xalign=0), 0, 0, 1, 1)
        oGrid.attach(self.notifyswitch, 1, 0, 1, 1)
        oGrid.attach(Gtk.Label(_('Play sound when a message is received:'), xalign=0), 0, 1, 1, 1)
        oGrid.attach(self.sndswitch, 1, 1, 1, 1)
        oGrid.attach(Gtk.Label(_('Merge messages from the same conversation:'), xalign=0), 0, 2, 1, 1)
        oGrid.attach(self.oSwitchMerge, 1, 2, 1, 1)
        oGrid.attach(Gtk.Label(_('Hide count when zero:'), xalign=0), 0, 3, 1, 1)
        oGrid.attach(self.hcswitch, 1, 3, 1, 1)
        oGrid.attach(Gtk.Label(_('When a message is activated:'), xalign=0), 0, 4, 1, 1)
        oGrid.attach(self.oComboMessageAction, 1, 4, 1, 1)
        commandbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        commandbox.add(Gtk.Label(_('Execute this command when a message is received:'), xalign=0))
        commandbox.pack_end(self.commandchooser, True, True, 0)

        if self.commandchooser.get_allocated_width() < 180:
            self.commandchooser.set_size_request(180, 0)

        self.sndbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, sensitive=self.bPlaySound)
        self.sndbox.add(Gtk.Label(_('Custom sound to play:'), xalign=0))
        self.sndbox.pack_end(self.sndchooser, True, True, 0)

        if self.sndchooser.get_allocated_width() < 180:
            self.sndchooser.set_size_request(180, 0)

        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, border_width=10)
        page.add(oGrid)
        page.add(commandbox)
        page.add(self.sndbox)

        return page

    def pageSupport(self):

        oGrid = Gtk.Grid(border_width=10, row_spacing=2)
        oGrid.attach(Gtk.Label(_('Report a bug'), xalign=0), 0, 0, 1, 1)
        oGrid.attach(Gtk.Label('<a href="https://github.com/AyatanaIndicators/ayatana-webmail/issues">https://github.com/AyatanaIndicators/ayatana-webmail/issues</a>', xalign=0, use_markup=True, margin_bottom=10), 0, 1, 1, 1)
        oGrid.attach(Gtk.Label(_('Request a feature'), xalign=0), 0, 2, 1, 1)
        oGrid.attach(Gtk.Label('<a href="https://github.com/AyatanaIndicators/ayatana-webmail/issues">https://github.com/AyatanaIndicators/ayatana-webmail/issues</a>', xalign=0, use_markup=True), 0, 3, 1, 1)
        oGrid.attach(Gtk.Label(_('It\'s a good idea to add the {labelname} label to your issue.').format(labelname='<b>enhancement</b>'), xalign=0, margin_bottom=10, use_markup=True), 0, 4, 1, 1)
        oGrid.attach(Gtk.Label(_('Ask a question'), xalign=0), 0, 5, 1, 1)
        oGrid.attach(Gtk.Label('<a href="https://github.com/AyatanaIndicators/ayatana-webmail/issues">https://github.com/AyatanaIndicators/ayatana-webmail/issues</a>', xalign=0, use_markup=True), 0, 6, 1, 1)
        oGrid.attach(Gtk.Label(_('It\'s a good idea to add the {labelname} label to your issue.').format(labelname='<b>question</b>'), xalign=0, margin_bottom=10, use_markup=True), 0, 7, 1, 1)
        #oGrid.attach(Gtk.Label(_('Help translate'), xalign=0), 0, 4, 1, 1)
        #oGrid.attach(Gtk.Label('<a href="https://translations.launchpad.net/ayatana-webmail/trunk">https://translations.launchpad.net/ayatana-webmail/trunk</a>', xalign=0, use_markup=True, margin_bottom=10), 0, 5, 1, 1)
        oGrid.attach(Gtk.Label(_('Source code'), xalign=0), 0, 8, 1, 1)
        oGrid.attach(Gtk.Label('<a href="https://github.com/AyatanaIndicators/ayatana-webmail">https://github.com/AyatanaIndicators/ayatana-webmail</a>', xalign=0, use_markup=True, margin_bottom=10), 0, 9, 1, 1)
        oGrid.attach(Gtk.Label(_('Home page'), xalign=0), 0, 10, 1, 1)
        oGrid.attach(Gtk.Label('<a href="https://tari.in/www/software/ayatana-webmail/">https://tari.in/www/software/ayatana-webmail/</a>', xalign=0, use_markup=True, margin_bottom=10), 0, 11, 1, 1)

        return oGrid

    def onActivateLinkAbout(self, pAboutDialog, sUrl):

        webbrowser.open_new_tab(sUrl)

        return True

    def pageAbout(self):

        oBox = Gtk.Box()
        oAboutDialog = Gtk.AboutDialog()
        oAboutDialog.set_license_type(Gtk.License.GPL_3_0)
        oAboutDialog.set_program_name(APPTITLE)
        oAboutDialog.set_copyright(APPAUTHOR + ' ' + (APPYEAR if APPYEAR[-2:] == APPVERSION[:2] else APPYEAR + '-20' + APPVERSION[:2]))
        oAboutDialog.set_comments(_(APPDESCRIPTION))
        oAboutDialog.set_authors(['Dmitry Shachnev &lt;mitya57@gmail.com&gt;', 'Robert Tari &lt;robert@tari.in&gt;'])
        oAboutDialog.set_translator_credits(_('translator-credits'))
        oAboutDialog.set_version(APPVERSION)
        oAboutDialog.set_website(APPURL)
        oAboutDialog.set_website_label(APPURL)
        oAboutDialog.set_logo(GdkPixbuf.Pixbuf().new_from_file(getDataPath('/usr/share/icons/hicolor/scalable/apps/ayatanawebmail.svg')))
        oAboutDialog.get_content_area().reparent(oBox)
        oAboutDialog.get_content_area().set_hexpand(True)
        oAboutDialog.connect('activate_link', self.onActivateLinkAbout)

        lstChildren = oAboutDialog.action_area.get_children()

        for oWidget in lstChildren:

            if (isinstance(oWidget, Gtk.Button) and not isinstance(oWidget, Gtk.ToggleButton)) or (isinstance(oWidget, Gtk.ToggleButton) and len(lstChildren) == 3 and oWidget == lstChildren[1]):

                oWidget.set_property('no-show-all', True)
                oWidget.set_property('visible', False)

        return oBox

    def onFolderActivated(self, oView, nRow, oColumn):

        self.oListStore[nRow][2] = not self.oListStore[nRow][2]
        self.updateUI()

    def updateUI(self):

        bHasFolderSelection = [oRow for oRow in self.oListStore if oRow[2]]
        bHasAccountData = all([oWidget.get_text() for oWidget in [self.EntryHost, self.EntryPort, self.EntryLogin, self.EntryPassword]])
        bHasMultipleAccounts = len(self.lstDicts) > 1

        self.oButtonConnect.set_sensitive(bHasAccountData)
        self.oButtonApply.set_sensitive(bHasFolderSelection and bHasAccountData)
        self.rmbtn.set_sensitive(bHasMultipleAccounts)
        self.addbtn.set_sensitive(bHasFolderSelection and bHasAccountData)
        self.sb.set_sensitive(bHasFolderSelection and bHasAccountData and bHasMultipleAccounts)

    def run(self):

        if not self.lstDicts[0]['Passwd']:
            self.updateEntries()

        self.updateUI()
        Gtk.main()

    def saveAllSettings(self):

        g_oSettings.set_boolean('enable-notifications', self.notifyswitch.get_active())
        g_oSettings.set_boolean('enable-sound', self.sndswitch.get_active())
        g_oSettings.set_boolean('hide-messages-count', self.hcswitch.get_active())
        g_oSettings.set_string('exec-on-receive', self.commandchooser.getFilename())
        g_oSettings.set_string('custom-sound', self.sndchooser.getFilename())
        g_oSettings.set_boolean('merge-messages', self.oSwitchMerge.get_active())
        g_oSettings.set_enum('message-action', int(self.oComboMessageAction.get_active_id()))

    def onAddAccount(self, btn):

        self.updateAccounts()
        self.lstDicts.append({'Host': 'imap.example.com', 'Port': '993', 'Login': '', 'Passwd': '', 'Folders': 'INBOX', 'InboxAppend': '/$MSG_THREAD'})
        self.lstDicts[-1].update(g_dctDefaultURLs)
        self.sb.set_range(1, len(self.lstDicts))
        self.sb.set_value(len(self.lstDicts))
        self.updateUI()

    def onRemoveAccount(self, btn):

        self.updateAccounts()
        index = self.sb.get_value_as_int()-1

        del self.lstDicts[index]

        self.bInit = False
        self.sb.set_range(1, len(self.lstDicts))
        self.bInit = True
        self.updateEntries()
        self.updateUI()

        if index+1 > len(self.lstDicts):
            self.sb.set_value(index)

        self.updateUI()

    def setAccounts(self, lstDicts):

        self.bInit = False
        self.lstDicts = [dct for dct in lstDicts]
        self.nIndex = 0
        self.sb.set_range(1, len(lstDicts))
        self.updateEntries()
        self.updateUI()
        self.bInit = True

    def onAccountChanged(self, sb):

        self.updateAccounts()
        self.nIndex = self.sb.get_value_as_int() - 1
        self.updateEntries()
        self.updateUI()

    def onSoundSwitchActivate(self, sndswitch, param):

        self.sndbox.set_sensitive(sndswitch.get_active())

    def updateEntries(self):

        if self.lstDicts:

            nIndex = self.sb.get_value_as_int() - 1
            self.EntryHost.set_text(self.lstDicts[nIndex]['Host'])
            self.EntryPort.set_text(str(self.lstDicts[nIndex]['Port']))
            self.EntryLogin.set_text(self.lstDicts[nIndex]['Login'])
            self.EntryPassword.set_text(self.lstDicts[nIndex]['Passwd'])

            self.oListStore.clear()

            if self.lstDicts[nIndex]['Passwd']:

                self.getFolderList(False)

                lstFolders = self.lstDicts[nIndex]['Folders'].split('\t')

                for oRow in self.oListStore:
                    oRow[2] = oRow[0] in lstFolders

            self.oEntryHome.setText(self.lstDicts[nIndex]['Home'])
            self.oEntryCompose.setText(self.lstDicts[nIndex]['Compose'])
            self.oEntryInbox.setText(self.lstDicts[nIndex]['Inbox'])
            self.oEntrySent.setText(self.lstDicts[nIndex]['Sent'])
            self.oEntryInboxAppend.set_text(self.lstDicts[nIndex]['InboxAppend'])

    def updateAccounts(self):

        if self.bInit:

            self.lstDicts[self.nIndex]['Host'] = self.EntryHost.get_text()

            if self.EntryPort.get_text():
                self.lstDicts[self.nIndex]['Port'] = self.EntryPort.get_text()
            else:
                self.lstDicts[self.nIndex]['Port'] = '993'

            self.lstDicts[self.nIndex]['Login'] = self.EntryLogin.get_text()
            self.lstDicts[self.nIndex]['Passwd'] = self.EntryPassword.get_text()
            self.lstDicts[self.nIndex]['Folders'] = '\t'.join([oRow[0] for oRow in self.oListStore if oRow[2]])
            self.lstDicts[self.nIndex]['Home'] = self.oEntryHome.getText()
            self.lstDicts[self.nIndex]['Compose'] = self.oEntryCompose.getText()
            self.lstDicts[self.nIndex]['Inbox'] = self.oEntryInbox.getText()
            self.lstDicts[self.nIndex]['Sent'] = self.oEntrySent.getText()
            self.lstDicts[self.nIndex]['InboxAppend'] = self.oEntryInboxAppend.get_text()
