# coding: utf-8

from __future__ import print_function, unicode_literals

import sys
import os

def main(args=sys.argv[1:]):
    import ipmsg
    from ipmsg.config import settings
    import ipmsg.consts as c
    from optparse import OptionParser

    usage = '%prog [options] message ip[:port]'
    parser = OptionParser(usage=usage)
    parser.add_option("-p", "--port", type="int", dest="port", default=c.IPMSG_DEFAULT_PORT,
                      help="port", metavar="PORT")
    parser.add_option("-u", "--user", dest="user", default='',
                      help="user name")
    parser.add_option("-g", "--group", dest="group", default='',
                      help="group name")
    parser.add_option("-b", "--broadcast", action="store_true", dest="broadcast", default=False,
                      help="broadcast", metavar="")
    parser.add_option("-s", "--seal", action="store_true", dest="seal", default=False,
                      help="seal message", metavar="")

    (options, args) = parser.parse_args()

    settings['user_name'] = options.user
    settings['group_name'] = options.group

    # TODO: It seems that I didn't implemented the multicast part...
    if options.broadcast:
        pass

    if len(args) < 2:
        parser.print_help()
        sys.exit()

    try:
        nics = ipmsg.get_all_network_interface()
        if len(nics) == 0:
            print('No network avalible.')
            sys.exit()

        msg = args[0]
        addrs = []
        for x in args[1:]:
            addr = x.split(':')
            if len(addr) == 1:
                addr.append(options.port)
            else:
                addr[1] = int(addr[1])
            addrs.append(tuple(addr))
    except NotImplemented:
        parser.print_help()
        sys.exit()
    else:
        ipmsg.init(port=options.port)
        ipmsg.engine.start_server()
        for addr in addrs:
            ipmsg.send(addrs=[addr], msg=msg, encrypt=False, seal=options.seal)
        print(ipmsg.whatsnew())
        ipmsg.engine.stop_server()
        sys.exit()

if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(message)s",
        filename="/tmp/ipmsg.log",
        filemode = 'w',
    )

    logging.debug('start')

    main()

