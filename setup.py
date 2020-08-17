#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, polib, configparser
from setuptools import setup
from ayatanawebmail.appdata import *

oFile = open('data/etc/xdg/autostart/ayatana-webmail-autostart.desktop', 'r+')
oConfigParser = configparser.ConfigParser()
oConfigParser.optionxform = str
oConfigParser.read_file(oFile)

for strRoot, lstDirnames, lstFilenames in os.walk('po.ayatana-webmail-autostart.desktop'):

    for strFilename in lstFilenames:

        if strFilename.endswith('po'):

            strLocale = os.path.splitext(strFilename)[0]

            for oEntry in polib.pofile('po.ayatana-webmail-autostart.desktop/' + strFilename).translated_entries():

                if oEntry.msgid == oConfigParser['Desktop Entry']['Name']:
                    oConfigParser['Desktop Entry']['Name[' + strLocale + ']'] = oEntry.msgstr
                elif oEntry.msgid == oConfigParser['Desktop Entry']['Comment']:
                    oConfigParser['Desktop Entry']['Comment[' + strLocale + ']'] = oEntry.msgstr

oFile.seek(0)
oConfigParser.write(oFile, False)
oFile.truncate()
oFile.close()

oFile = open('data/usr/share/applications/ayatana-webmail.desktop', 'r+')
oConfigParser = configparser.ConfigParser()
oConfigParser.optionxform = str
oConfigParser.read_file(oFile)

for strRoot, lstDirnames, lstFilenames in os.walk('po.ayatana-webmail.desktop'):

    for strFilename in lstFilenames:

        if strFilename.endswith('po'):

            strLocale = os.path.splitext(strFilename)[0]

            for oEntry in polib.pofile('po.ayatana-webmail.desktop/' + strFilename).translated_entries():

                if oEntry.msgid == oConfigParser['Desktop Entry']['Name']:
                    oConfigParser['Desktop Entry']['Name[' + strLocale + ']'] = oEntry.msgstr
                elif oEntry.msgid == oConfigParser['Desktop Entry']['Comment']:
                    oConfigParser['Desktop Entry']['Comment[' + strLocale + ']'] = oEntry.msgstr
                elif oEntry.msgid == oConfigParser['Desktop Action Clear']['Name']:
                    oConfigParser['Desktop Action Clear']['Name[' + strLocale + ']'] = oEntry.msgstr
                elif oEntry.msgid == oConfigParser['Desktop Action Compose']['Name']:
                    oConfigParser['Desktop Action Compose']['Name[' + strLocale + ']'] = oEntry.msgstr
                elif oEntry.msgid == oConfigParser['Desktop Action Sent']['Name']:
                    oConfigParser['Desktop Action Sent']['Name[' + strLocale + ']'] = oEntry.msgstr
                elif oEntry.msgid == oConfigParser['Desktop Action Change']['Name']:
                    oConfigParser['Desktop Action Change']['Name[' + strLocale + ']'] = oEntry.msgstr
                elif oEntry.msgid == oConfigParser['Desktop Action Inbox']['Name']:
                    oConfigParser['Desktop Action Inbox']['Name[' + strLocale + ']'] = oEntry.msgstr

oFile.seek(0)
oConfigParser.write(oFile, False)
oFile.truncate()
oFile.close()

m_lstDataFiles = []

for strRoot, lstDirnames, lstFilenames in os.walk('po'):

    for strFilename in lstFilenames:

        strLocale = os.path.splitext(strFilename)[0]

        if strLocale != APPNAME:

            strLocaleDir = 'data/usr/share/locale/' + strLocale + '/LC_MESSAGES/'

            if not os.path.isdir(strLocaleDir):
                os.makedirs(strLocaleDir)

            polib.pofile('po/' + strFilename).save_as_mofile(strLocaleDir + APPNAME + '.mo')

for strRoot, lstDirnames, lstFilenames in os.walk('data'):

    for strFilename in lstFilenames:

        strPath = os.path.join(strRoot, strFilename)
        m_lstDataFiles.append((os.path.dirname(strPath).lstrip('data'), [strPath]))

setup(
    name = APPNAME,
    version = APPVERSION,
    description = APPDESCRIPTION,
    long_description = APPLONGDESCRIPTION,
    url = APPURL,
    author = APPAUTHOR,
    author_email = APPMAIL,
    maintainer = APPAUTHOR,
    maintainer_email = APPMAIL,
    license = 'GPL-3',
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: X11 Applications :: GTK',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Communications :: Email'
        ],
    keywords = APPKEYWORDS,
    packages = [APPNAME],
    data_files = m_lstDataFiles,
    platforms = 'UNIX'
    )
