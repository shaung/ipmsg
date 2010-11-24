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
CONF_PATH = os.path.expanduser('~/.pyipmsg/ipmsg.conf')
SYS_CONF_PATH = os.path.expanduser('~/.pyipmsg/global.conf')
WEB_SHARE_DIR = os.path.expanduser('~/.pyipmsg/webshare/')
DEBUG_LOG = os.path.expanduser('~/.pyipmsg/debug.log')

from ConfigParser import SafeConfigParser
parser = SafeConfigParser()
parser.read(SYS_CONF_PATH)
INSTALL_ROOT_DIR = parser.get('install', 'root_dir')
