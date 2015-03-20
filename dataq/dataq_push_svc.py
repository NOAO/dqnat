#! /usr/bin/env python3
"""Read data records from socket and push to queue.

Record: <md5sum> <absolute_filename> [<others> ...]

The checksum provided for each data record is used as an ID.  If the
checksum of two records is the same, we assume the data is. So we can
throw one of them away.
"""

import argparse
import sys
import logging
import socketserver
import json

import redis


from tada import config
from . import dqutils
#! from . import default_config
from .dbvars import *

class DqTCPHandler(socketserver.StreamRequestHandler):
    "Read records from TCP socket, push to DataQueue."
    
    def handle(self):
        r = self.server.r
        cfg = self.server.cfg
        if r.get(readP) == 'off':
            return False

        if r.llen(aq) > cfg['maxium_queue_size']:
            logging.error('Queue is full! '
                          + 'Turning off read from socket. '
                          + 'Disabling push to queue.  '
                          + 'To reenable: "dqcli --read on"  '
                          )
            r.set(readP, 'off')

        self.data = self.rfile.readline().strip().decode()
        logging.debug('Data line read from socket="%s"', self.data)
        #!(fname,checksum,size) = self.data.split() #! specific to our APP
        #!rec = dict(list(zip(['filename','size'],[fname,size])))
        (checksum, fname, *others) = self.data.split()
        rec = dict(filename=fname, checksum=checksum)

        pl = r.pipeline()
        pl.watch(rids, aq, aqs, checksum)
        pl.multi()
        if r.sismember(aqs, checksum) == 1:
            logging.warning(': Record for %s is already in queue.'
                            +' Ignoring duplicate.', checksum)
            self.wfile.write(bytes('Ignored ID=%s'%checksum, 'UTF-8'))
        else:
            # add to DB
            pl.sadd(aqs, checksum)
            pl.lpush(aq, checksum)
            pl.sadd(rids, checksum)
            pl.hmset(checksum, rec)
            pl.hset(ecnt, checksum, 0) # error count against file
            pl.save()
            self.wfile.write(bytes('Pushed ID=%s'%checksum, 'UTF-8'))
        pl.execute()
        #!logging.debug('Data line read from socket="%s"', self.data)

##############################################################################
def main():
    'Parse args, then start reading queue forever.'
    possible_qnames = ['transfer', 'submit']
    parser = argparse.ArgumentParser(
        description='Read data from socket and push to Data Queue',
        epilog='EXAMPLE: %(prog)s '
        )

    parser.add_argument('--cfg',
                        help='Configuration file',
                        type=argparse.FileType('r'))
    parser.add_argument('--queue', '-q',
                        choices=possible_qnames,
                        help='Name of queue to pop from. Must be in cfg file.')

    #! parser.add_argument('action',  choices=['start','stop','restart'])


    parser.add_argument('--logfile',
                        help='Log file name',
                        )
    parser.add_argument('--loglevel',
                        help='Kind of diagnostic output',
                        choices=['CRTICAL', 'ERROR', 'WARNING',
                                 'INFO', 'DEBUG'],
                        default='WARNING')
    args = parser.parse_args()

    log_level = getattr(logging, args.loglevel.upper(), None)
    if not isinstance(log_level, int):
        parser.error('Invalid log level: %s' % args.loglevel)
    logging.basicConfig(level=log_level,
                        format='%(levelname)s %(message)s',
                        datefmt='%m-%d %H:%M'
                        )
    logging.debug('Debug output is enabled!')
    ######################################################################

    qcfg, dirs = config.get_config(possible_qnames)

    dqutils.save_pid(sys.argv[0], piddir=dirs['run_dir'])

    dq_host = qcfg[args.queue]['dq_host']
    dq_port = qcfg[args.queue]['dq_port']
    logging.debug('Queue "{}" read data from {}:{} and push to REDIS'
                  .format(args.queue, dq_host, dq_port))
    server = socketserver.TCPServer((dq_host, dq_port), DqTCPHandler)
    server.r = redis.StrictRedis()
    server.cfg = qcfg[args.queue]
    server.serve_forever()


if __name__ == '__main__':
    main()
