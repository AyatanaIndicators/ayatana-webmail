#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, polib, configparser
from setuptools import setup
from ayatanawebmail.appdata import *

for sFile in ['data/etc/xdg/autostart/ayatana-webmail-autostart.desktop', 'data/usr/share/applications/ayatana-webmail.desktop']:

    oFile = open(sFile, 'r+')
    oConfigParser = configparser.ConfigParser()
    oConfigParser.optionxform = str
    oConfigParser.read_file(oFile)

    for strRoot, lstDirnames, lstFilenames in os.walk('po'):

        for strFilename in lstFilenames:

            if strFilename.endswith('po'):

                strLocale = os.path.splitext(strFilename)[0]

                for oEntry in polib.pofile('po/' + strFilename).translated_entries():

                    if oEntry.msgid == oConfigParser['Desktop Entry']['Name']:

                        oConfigParser['Desktop Entry']['Name[' + strLocale + ']'] = oEntry.msgstr

                    elif oEntry.msgid == oConfigParser['Desktop Entry']['Comment']:

                        oConfigParser['Desktop Entry']['Comment[' + strLocale + ']'] = oEntry.msgstr

                    for sAction in ['Clear', 'Compose', 'Sent', 'Change', 'Inbox']:

                        if 'Desktop Action ' + sAction in oConfigParser and oEntry.msgid == oConfigParser['Desktop Action ' + sAction]['Name']:

                            oConfigParser['Desktop Action ' + sAction]['Name[' + strLocale + ']'] = oEntry.msgstr

    for sSection in oConfigParser.sections():

        oConfigParser[sSection] = dict(sorted(oConfigParser[sSection].items(), key=lambda lParams: lParams[0]))

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
