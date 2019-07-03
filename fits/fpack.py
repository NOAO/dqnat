#! /usr/bin/env python
"""Lossless fpack.  The default options for floating point fpack
result in lossy compression. Use FITS header info to choose options to
insure lossless compression in all cases.
"""

import logging
import subprocess
import os.path
import shutil
import sys
import argparse
import logging

from . import fits_utils as fu


def remove_if_exists(filename):
    try:
        os.remove(filename)
    except:
        pass

def fpack(*args):
    # for floating point 
    # $FPACK -Y -g -q 0 ${BASEFILE}.fits
    fpackcmd = '/usr/local/bin/fpack'
    cmd=[fpackcmd] + list(args)
    logging.debug('fpack: CMD={}'.format(cmd))
    subprocess.run(cmd, check=True)
    
def fpack_to(fitsfile, outfile, force=True):
    """Fpack FITSFILE into OUTFILE (or copy if already fpacked).
    If OUTFILE (.fz) already exists, overwrite IFF force=True.
    RETURN: True IFF fpack was run on this invocation.
    """
    fitscopycmd = '/usr/local/bin/fitscopy'
    logging.debug('fpack_to({}, {})'.format(fitsfile, outfile))
    tmpoutfile = None
    if force==False and os.path.exists(outfile):
        logging.warning('fpack_to: Outfile already exists. Doing nothing. {}'
                        .format(outfile))
        return False
    if fitsfile[-3:] == '.fz':
        logging.debug('fpack_to: FITSfile already *.fz. Copying to: {}'
                      .format(outfile))
        shutil.copy(fitsfile, outfile)
    else: # compress on the fly
        try:
            remove_if_exists(outfile)
            subprocess.run([fitscopycmd, fitsfile, outfile], check=True)
            is_fp = fu.is_floatingpoint(outfile)

            # FPACK BUG workaround.
            # Despite documentation, fpack will not compress in place
            # if file ends with ".fz"
            if outfile[-3:] == '.fz':
                tmpoutfile = outfile + 'z'  # now: *.fits.fzz
                os.rename(outfile, tmpoutfile)

            if is_fp:
                # is floating point image
                # Default options are lossy. Use lossless options instead.
                fpack('-Y', '-C', '-F', '-g', '-q', '0', tmpoutfile)
                # "fpack -L" should yield: "tiled_gzip"
            else:
                fpack('-Y', '-C', '-F', tmpoutfile)
                # "fpack -L" should yield: "tiled_rice"
                
            # FPACK BUG workaround.
            if tmpoutfile:
                os.rename(tmpoutfile, outfile)

        except subprocess.CalledProcessError as ex:
            logging.error('FAILED fpack_to: {}; returncode={}'
                          .format(ex, ex.returncode))
            raise
    #logging.debug('move to cache ({},{})'.format(tmpfile, outfile))
    #shutil.move(tmpfile, outfile)
    logging.debug('DONE: fpack_to({}, {})'.format(fitsfile, outfile))
    return outfile

##############################################################################

def main():
    "Parse command line arguments and do the work."
    parser = argparse.ArgumentParser(
        description='''\
FPACK as used in TADA. 
Uses CFITSIO to copy .fits file to fix some errors that
will trip up astropy. If the infile is *.fz, file is assumed to be compressed
and no attempt to fpack is done.  If its *.fits, fpack is run.  The options
used in fpack depend on value of BITPIX.  Value of -32 or -64 treated one way, all other values treated another.
''',
        epilog='EXAMPLE: %(prog)s a b"'
        )
    parser.add_argument('--version', action='version', version='1.2')
    parser.add_argument('infile', type=argparse.FileType('r'),
                        help='Input FITS file')
    parser.add_argument('outfile', type=argparse.FileType('w'),
                        help='Output FITS file')

    parser.add_argument('--loglevel',
                        help='Kind of diagnostic output',
                        choices=['CRTICAL', 'ERROR', 'WARNING',
                                 'INFO', 'DEBUG'],
                        default='WARNING')
    args = parser.parse_args()
    args.infile.close()
    args.infile = args.infile.name
    args.outfile.close()
    args.outfile = args.outfile.name

    #!print 'My args=',args
    #!print 'infile=',args.infile

    log_level = getattr(logging, args.loglevel.upper(), None)
    if not isinstance(log_level, int):
        parser.error('Invalid log level: %s' % args.loglevel)
    logging.basicConfig(level=log_level,
                        format='%(levelname)s %(message)s',
                        datefmt='%m-%d %H:%M')
    logging.debug('Debug output is enabled in %s !!!', sys.argv[0])

    fpack_to(args.infile, args.outfile)

if __name__ == '__main__':
    main()
