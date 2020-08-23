#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Ayatana Webmail, message actions dialog
# Authors: Robert Tari <robert@tari.in>
# License: GNU GPL 3 or higher; http://www.gnu.org/licenses/gpl.html

import gettext
import os
import psutil
import subprocess
import webbrowser
from gi.repository import Gio
from ayatanawebmail.appdata import APPEXECUTABLE, APPNAME
from ayatanawebmail.accounts import DialogAccounts

try:
    g_oTranslation = gettext.translation(APPNAME)
except IOError:
    g_oTranslation = gettext.NullTranslations()

g_oTranslation.install()
g_oSettings = Gio.Settings.new('org.ayatana.webmail')
g_lstAccounts = []

def getDataPath(strPath):

    try:

        strExecPath = os.path.split(APPEXECUTABLE)[0]
        strDataPath = os.getcwd().replace(strExecPath, '')
        strRelativePath = os.path.join(strDataPath, strPath.lstrip('/'))

        if os.path.exists(strRelativePath):
            return strRelativePath

    except:

        pass

    return strPath

def isRunning(sAppend = ''):

    nCount = 0

    for oProc in psutil.process_iter():

        strName = oProc.name

        if not isinstance(strName, str):

           strName = oProc.name()

        if strName == 'python3' or strName == 'python':

            lstCmdline = oProc.cmdline

            if not isinstance(lstCmdline, list):
               lstCmdline = oProc.cmdline()

            for strCmd in lstCmdline:

                if strCmd.endswith('ayatana-webmail' + sAppend):
                    nCount += 1

        elif strName.endswith('ayatana-webmail' + sAppend):

            nCount += 1

    return nCount

def resolveURL(strURL):

    if strURL.startswith('Exec:'):
        subprocess.Popen(strURL[5:], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    elif strURL.startswith('http'):
        webbrowser.open_new_tab(strURL)

def openURLOrCommand(strURL):

    if strURL in ['Home', 'Compose', 'Inbox', 'Sent']:

        strURL0 = g_lstAccounts[0][strURL]

        if len(g_lstAccounts) > 1:

            for dctAccount in g_lstAccounts[1:]:

                if dctAccount[strURL] != strURL0:

                    oDialogAccounts = DialogAccounts(strURL, getDataPath, g_lstAccounts)
                    oDialogAccounts.run()
                    strURL = oDialogAccounts.strURL
                    oDialogAccounts.destroy()

                    if strURL:
                        resolveURL(strURL)

                    return

        resolveURL(strURL0)

    elif strURL.startswith('Exec:') or strURL.startswith('http'):

        resolveURL(strURL)

    else:

        print('Unknown URL name!')
        print('Possible URL names: "Home", "Compose", "Inbox", "Sent", "Exec:...", "http..."')
