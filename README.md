About
=====
An IP Messenger(http://www.ipmsg.org) alternative for Linux, written in python.


Requirements
============
 * Python 2.6 or above. Python 3 support is not included for now.


Dependencies
============
 * PyCrypto
 * M2Crypto(will be removed in the future)

Status
======
Only tested under Ubuntu 10.04 / Python 2.6.
Not compatible with IP Messager 3.x yet.

Installation
============
To install::

    sudo python setup.py install


Known issues
============
The M2Crypto package on Pypi seems not working properly.
If you encounterd errors while installing M2Crypto using easy_install,
try download the package and manually install it instead.
Besides, it requires SWIG and OpenSSL being installed.
Hopefully the dependency to M2Crypto will be removed in the next version.

