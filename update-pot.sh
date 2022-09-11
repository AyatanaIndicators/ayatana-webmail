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

cp data/etc/xdg/autostart/ayatana-webmail-autostart.desktop      data/etc/xdg/autostart/ayatana-webmail-autostart.desktop.keep
cp data/usr/share/applications/ayatana-webmail.desktop           data/usr/share/applications/ayatana-webmail.desktop.keep

./setup.py build_i18n 1>/dev/null 2>/dev/null

mv data/etc/xdg/autostart/ayatana-webmail-autostart.desktop.keep data/etc/xdg/autostart/ayatana-webmail-autostart.desktop
mv data/usr/share/applications/ayatana-webmail.desktop.keep      data/usr/share/applications/ayatana-webmail.desktop

rm ./build -Rf
rm ./data/usr/share/locale/ -Rf

sed -e 's@#: \.\./@#: @g'		\
    -i po/${GETTEXT_DOMAIN}.pot
