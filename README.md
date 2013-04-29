# ipmsg

An IP Messenger(http://www.ipmsg.org) library for Linux, written in python.

For the GUI frontend, checkout https://github.com/shaung/ipmsg-pygtk


### Requirements

 * Python 2.6 or above. Python 3 support is not included for now.


### Dependencies

 * PyCrypto
 * rsa


### Installation

From pypi:

    pip install ipmsg
    
Or install from source:

    python setup.py install


### Command-line usage

    ipmsg [--port=<port>] [--user=<username>] [--group=<groupname>] [-s|--seal] [--help] ip[:port]


### License

Released under the BSD license.


### Troubleshooting

 * Not compatible with IP Messager 3.x yet.
