"""Monitor file additions to directorys and do something when then
happen.  On Linux 2.6 this uses inotify.  (Other platforms use
different underlying mechanisms which may be muc less efficient.)
"""

import os
import os.path
import logging
import shutil
import time
from pathlib import PurePath, Path
from glob import glob
import subprocess
import re
import hashlib
import socket
# External
import yaml
import watchdog.events
import watchdog.observers
# Local
#! from . import tada_settings as ts
import fits.fits_utils as fu
import fits.fpack as fp
import dataq.red_utils as ru

##############################################################################
### Monitor
###
### Monitor directory structure of watched_dir/<day>/<instrument>
### Where <day> is of form: YYYYMMDD
### We expect only a small subset of days to be changing. Therefore, it
### would be *better* if only the changing subset were watched.  But
### that's harder.  So, for now, recursively watch "watched_dir".
###

#!def md5(fname):
#!    hash_md5 = hashlib.md5()
#!    with open(fname, "rb") as f:
#!        for chunk in iter(lambda: f.read(4096), b""):
#!            hash_md5.update(chunk)
#!    return hash_md5.hexdigest()

#!def validate_personality(pdict):
#!    if 'params' not in pdict:
#!        raise tex.InvalidPersonality('Missing "params" in {}'
#!                                     .format(pdict))
#!    if 'md5sum' not in pdict['params']:
#!        raise tex.InvalidPersonality('Missing "params.md5sum" in {}'
#!                                     .format(pdict))
#!    if 'filename' not in pdict['params']:
#!        raise tex.InvalidPersonality('Missing "params.filename" in {}'
#!                                     .format(pdict))
#!    if 'options' not in pdict:
#!        raise tex.InvalidPersonality('Missing "options" in {}'
#!                                     .format(pdict))
#!
#!    return True

#class PushEventHandler(watchdog.events.FileSystemEventHandler):
class PushEventHandler(watchdog.events.PatternMatchingEventHandler):
    """Copy new FITS file to CACHE and push to DQ.  If can't push, move 
to ANTICACHE. 
After this, normal TADA takes over; pop record, perform q-action(transfer)
YAML file will be transfered with FITS because its in same directory..
"""
    patterns = ['**/*.fits', '**/*.fz']
    
    def __init__(self, drop_dir, status_dir):
        self.dropdir = drop_dir
        self.statusdir = status_dir
        self.cachedir= '/var/tada/cache'
        self.personalitydir= '/var/tada/personalities'
        self.anticachedir= '/var/tada/anticache'
        self.date_re=re.compile(r"^20\d{6}$")
        logging.info('init PushEventHandler({}, {})'
                     .format(drop_dir, status_dir))
        #super(watchdog.events.FileSystemEventHandler).__init__()
        super().__init__(patterns=self.patterns)

    def pushfile(self, md5sum, fullfname):
        logging.debug('Monitor: pushfile({})'.format(fullfname))
        rport = yaml.load(open('/etc/tada/tada.conf')).get('redis_port','6379')
        try:
            #!cmdstr = ('dqcli --pushfile "{}"'.format(fullfname))
            #!logging.debug('EXECUTING: {}'.format(cmdstr))
            #!subprocess.check_call(cmdstr, shell=True)
            logging.debug('EXECUTING: push_direct; redis_port="{}"'
                          .format(rport))
            ru.push_direct(socket.getfqdn(), # this host
                           rport, #qcfg['redis_port'],
                           fullfname,
                           md5sum)
        except Exception as err:
            logging.error('Could not push file. {}'.format(err))

    def on_created(self, event):
        if isinstance(event, watchdog.events.DirCreatedEvent):
            return None
        self.new_file(event.src_path)

    def on_moved(self, event):
        if isinstance(event, watchdog.events.DirMovedEvent):
            return None
        #logging.debug('DBG-0: on_moved; {}'.format(event.dest_path))
        if os.path.exists(event.dest_path):
            # for rsync: moved from tmp file to final filename
            self.new_file(event.dest_path)
        else:
            logging.debug('file gone: on_moved; {}'.format(event.dest_path))

    def on_modified(self, event):
        if isinstance(event, watchdog.events.DirModifiedEvent):
            return None
        #logging.debug('DBG-0: on_modified; {}'.format(event.src_path))
        # So we can trigger event with "touch"
        if os.path.exists(event.src_path):
            self.new_file(event.src_path)
        else:
            logging.debug('file gone: on_modified; {}; Ignoring event.'
                          .format(event.src_path))

        
    def valid_dir(self, ifname):
        """Validate directory structure sent to dropbox."""
        try:
            pp = PurePath(ifname).relative_to(PurePath(self.dropdir))
            if len(pp.parts) < 3:
                logging.error('File in dropbox has invalid parts.'
                              ' Path must start with "20YYMMDD/<instrum>/..."'
                              ' Got: {}'.format(str(pp)))
                return False
            day,inst,*d = pp.parts
            if not self.date_re.match(day):
                logging.error('File in dropbox has invalid date ({}) in'
                              ' path. Path must start with'
                              ' "20YYMMDD/<instrum>/"'
                              ' Got: {}'
                              .format(day, ifname))
                return False
        except Exception as ex:
            logging.error('Failed valid_dir({}); {}'
                          .format(ifname, ex))
            #tut.log_traceback()
            return False
            
        return True

    def new_file(self, ifname):
        #######
        ## Ignore: non-fits, invalid directory
        pp = PurePath(ifname).relative_to(PurePath(self.dropdir))
        if pp.suffix not in ['.fz', '.fits']:
            return None
        if not self.valid_dir(ifname):
            logging.error('Not submitting file: {}'.format(ifname))
            return None
        ##
        ########

        logging.debug('DBG: new_file({})'.format(ifname))
        try:
            pdict = self.options_from_yamls(ifname)
        #!except tex.NoPersonality:
        #!    raise
        except Exception as ex:
            logging.error('Failed to get options_from_yamls({}); {}'
                          .format(ifname, ex))
            #tut.log_traceback()
            return None

        logging.debug('Got pdict from yamls:{}'.format(pdict))
        md5sum = pdict['params']['md5sum']
        try:
            cachename = ifname.replace(self.dropdir, self.cachedir)
            os.makedirs(os.path.dirname(cachename), exist_ok=True)
            queuename = cachename.replace('/cache/','/cache/.queue/')
            os.makedirs(os.path.dirname(queuename), exist_ok=True)
            anticachename = ifname.replace(self.dropdir, self.anticachedir)
            os.makedirs(os.path.dirname(anticachename), exist_ok=True)
            statusname = ifname.replace(self.dropdir, self.statusdir)+'.status'
            os.makedirs(os.path.dirname(statusname), exist_ok=True)
            if ifname[-5:] == '.fits': # dropped file is not yet compressed
                queuename += '.fz'
                cachename += '.fz'
                anticachename += '.fz'
            yamlname = queuename + '.yaml'

            try:
                fu.fitsverify(ifname)
            except Exception as ex:
                logging.warning(('Dropbox file ({}) is invalid FITS.'
                                 ' Trying to continue anyhow. {}')
                                .format(os.path.basename(ifname), ex))

            try:
                fp.fpack_to(ifname, queuename)
            except Exception as ex:
                logging.error('Failed on: fpack_to({}, {}); {}'
                              .format(ifname, queuename, ex))
                return None

            # Combine all personalities into one and put in cache next to fits.
            # It will be sent to valley along with fits.
            with open(yamlname, 'w') as yf:
                yaml.safe_dump(pdict, yf, default_flow_style=False)

            try:
                self.pushfile(md5sum, queuename)
                logging.info('Pushed {} to cache: {}'.format(ifname, queuename))
                Path(statusname).touch(exist_ok=True)
            except Exception as ex:
                # Push to dataq failed (file not put into TADA processing)
                logging.error('Push FAILED with {}; {}'.format(ifname, ex))
                #tut.log_traceback()
                shutil.move(cachename, anticachename)
        except Exception as ex:
            # Something unexpected failed (makedirs, copy, yaml read/write)
            logging.error('PushEventHandler.new_file FAILED with {}; {}'
                          .format(ifname, ex))
            #tut.log_traceback()

    def options_from_yamls(self, ifname):
        """Returned combined options and parameters as single dict formed by 
    collecting YAML files. Three locations will be looked in for YAML files:
      1. <personality_dir>/<instrument>/*.yaml  (can be multiple)
      2. <dropbox/<instrument>/*.yaml           (can be multiple)
      3. <ifname>.yaml                          (just one)
     """
        #logging.debug('DBG: options_from_yamls:{}'.format(ifname))
        day,inst,*d = PurePath(ifname).relative_to(PurePath(self.dropdir)).parts
        #logging.debug('DBG: file={}, day={}, inst={}'.format(ifname, day, inst))

        pdict = dict(options={}, params={})
        #pdict['params']['filename'] = ifname # default 

        # from PERSONALITYDIR
        globpattern = os.path.join(self.personalitydir, inst, '*.yaml')
        yfiles1 = glob(globpattern)
        if len(yfiles1) == 0:
            #raise tex.NoPersonality(
            raise Exception(
                "Did not find expected YAML personality file(s) in: {}"
                .format(globpattern))
        for yfile in sorted(yfiles1):
            with open(yfile) as yy:
                yd = yaml.safe_load(yy)
                pdict['params'].update(yd.get('params', {}))
                pdict['options'].update(yd.get('options', {}))

        # from DROPDIR
        globpattern = os.path.join(self.dropdir, inst, '*.yaml')
        yfiles2 = glob(globpattern)
        for yfile in sorted(yfiles2):
            with open(yfile) as yy:
                yd = yaml.safe_load(yy)
                pdict['params'].update(yd.get('params', {}))
                pdict['options'].update(yd.get('options', {}))

        # From fits buddy
        yfile = ifname + '.yaml'
        if os.path.isfile(yfile):
            with open(yfile) as yy:
                yd = yaml.safe_load(yy)
                pdict['params'].update(yd.get('params', {}))
                pdict['options'].update(yd.get('options', {}))

        logging.debug('DBG: read YAML files: {}'
                      .format(yfiles1 + yfiles2 + [yfile]))
        logging.debug('DBG: pdict={}'.format(pdict))
        validate_personality(pdict)
        return pdict 
            

def push_drops(watch_dir = '/var/tada/dropbox',
               status_dir = '/var/tada/statusbox'):
    #logging.debug('DBG-0: push_drops()')
    os.makedirs(watch_dir, exist_ok=True)
    os.makedirs(status_dir, exist_ok=True)
    logging.info('Watching directory: {}'.format(watch_dir))

    handler = PushEventHandler(watch_dir, status_dir)
    observer = watchdog.observers.Observer()
    observer.schedule(handler, watch_dir, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
