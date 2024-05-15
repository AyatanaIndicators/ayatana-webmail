#!/bin/bash

# Copyright (C) 2017 by Mike Gabriel <mike.gabriel@das-netzwerkteam.de>
#
# This package is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 3 of the License.
#
# This package is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

GETTEXT_DOMAIN="ayatanawebmail"

cp data/etc/xdg/autostart/ayatana-webmail-autostart.desktop.in data/etc/xdg/autostart/ayatana-webmail-autostart.desktop
cp data/usr/share/applications/ayatana-webmail.desktop.in      data/usr/share/applications/ayatana-webmail.desktop

./setup.py build_i18n 1>/dev/null 2>/dev/null

rm data/etc/xdg/autostart/ayatana-webmail-autostart.desktop
rm data/usr/share/applications/ayatana-webmail.desktop

rm ./build -Rf
rm ./data/usr/share/locale/ -Rf

sed -E					\
    -e 's@^#: \.\./@#: @g'		\
    -e 's@(:[0-9]+) \.\./@\1 @g'	\
    -i po/${GETTEXT_DOMAIN}.pot
