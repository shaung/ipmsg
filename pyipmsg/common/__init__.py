# -*- coding: utf-8 -*-

import config

APPNAME = 'pyipmsg'
VERSION = '0.0.1.0'
APPDESC = 'ipmsg alternative for gnome'
AUTHOR = 'Shaung'
EMAIL = 'shaun.geng@gmail.com'
URL = 'http://github.com/shaung/pyipmsg'
LICENSE = 'GPLv3'
LICENSE_DESC = """This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License version 3, as published by the Free Software Foundation.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranties of MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.  If not, see <http://www.gnu.org/licenses/>."""

import os.path

INSTALL_ROOT_DIR = '/usr/share/pyipmsg/'
CONF_PATH = os.path.expanduser('~/.pyipmsg/ipmsg.conf')
WEB_SHARE_DIR = '/tmp/pyipmsg/webshare/'
DEBUG_LOG = os.path.expanduser('~/.pyipmsg/debug.log')

