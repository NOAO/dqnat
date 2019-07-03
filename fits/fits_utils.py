#! /usr/bin/env python3
"""Fiddling with Fits (tm)

It would be nice if our FITS files always satisified the FITS Standard.
They do not according to:
http://fits.gsfc.nasa.gov/fits_verify.html
(or the standalone version of same)
"""
import sys
import argparse
import logging
import magic
from pprint import pprint

import requests
import astropy.io.fits as pyfits
import os.path
from pathlib import PurePath
#!import datetime as dt
import subprocess
import yaml
from astropy.utils.exceptions import AstropyWarning, AstropyUserWarning
 
#from . import file_naming as fn
from . import exceptions as tex
#!from . import hdr_calc_utils as hcu
from . import scrub
#from . import config 
from . import utils as tut
from . import tada_settings as ts
import tada.hdrfunclib.hdr_decorators as hd
import tada.hdrfunclib.hdr_funcs as hf

# EXAMPLE compliant header (included here for descriptions):
"""    
SIMPLE  =                    T / File conforms to FITS standard
BITPIX  =                    8 / Bits per pixel (not used)     
NAXIS   =                    0 / PHU contains no image matrix  
EXTEND  =                    T / File contains extensions      
NEXTEND =                    2 / Number of extensions          
FILENAME= 'n3.09786.fits'      / Original host filename        
OBJECT  = 'SkyFlat Blue'       / Observation title             
OBSTYPE = 'flat    '           / Observation type              
OBSMODE = 'sos_slit'           / Observation mode              
EXPTIME =                   20 / Exposure time (sec)           
RADECSYS= 'FK5     '           / Default coordinate system     
RADECEQ =                2000. / Default equinox test4         
RA      = '18:12:45.72'        / RA of observation (hr)        
DEC     = '31:57:45.0'         / DEC of observation (deg)      
OBJRA   = '18:12:45.72'        / Right Ascension               
OBJDEC  = '31:57:45.0'         / Declination                   
OBJEPOCH=               2014.7 / [yr] epoch                    
TIMESYS = 'UTC approximate'    / Time system                   
DATE-OBS= '2014-09-22T01:35:48.0'  /  UTC epoch                
TIME-OBS= '1:35:48 '           / Universal time                
MJD-OBS =       56922.06652778 / MJD of observation start      
ST      = '18:13:55'           / Sidereal time                 
MJDSTART=      56922.066558066 / MJD of observation start      
MJDEND  =      56922.067317367 / MJD of observation end        
OBSERVAT= 'KPNO    '           / Observatory                   
TELESCOP= 'KPNO 4.0 meter telescope' / Telescope               
TELRADEC= 'FK5     '           / Telescope coordinate system   
TELEQUIN=               2014.7 / Equinox of tel coords         
TELRA   = '18:12:45.72'        / RA of telescope (hr)          
TELDEC  = '31:57:45.0'         / DEC of telescope (deg)        
HA      = '0:00:00.00'         / Telescope hour angle          
ZD      =                    0 / Zenith distance               
AIRMASS =                    1 / Airmass                       
INSTRUME= 'KOSMOS  '           / Kosmos detector               
DETSIZE = '[1:2048,1:4096]'    / Kosmos detector size          
NDETS   =                    1 / Number of detectors in kosmos 
FILTER  = 'Open    '           / Filter                        
DISPERSR= 'b2k kb2k'           / Disperser                     
SLITWHL = '4pxB k4pxB'         / Slit Wheel                    
DEWAR   = 'KOSMOS Dewar'       / Dewar identification          
OBSERVER= 'Hirschauer, Salzer' / Observer(s)                   
PROPOSER= 'John Salzer'        / Proposer(s)                   
PROPID  = '2014B-0461'         / Proposal identification       
OBSID   = 'kp4m.20140922T013548' / Observation ID              
EXPID   =                    0 / Monsoon exposure ID           
NOCID   =      2456922.7748827 / NOCS exposure ID              
DHEFILE = 'kosmos_e2v_Sequencer_roiV206.ucd' / Sequencer file  
NOCROIRZ=                    0 / Detector ROI row size         
NOCDEVIC= 'e2v     '           / Detector device               
NOCOFFG = '0.0 0.0 '           / ntcs_gdroffset x y offset (mm)
NOCNO   =                    1 / observation number in this sequence        
NOCGAIN = 'unknown '           / Controller gain               
NOCDFIL =                    0 / Dither offsets file           
NOCDHS  = 'STFLAT  '           / DHS script name               
NOCGPXPS=                    0 / Monsoon pixel row/column shift
NOCFSTEP=                    0 / [um] step value for focus adjustments      
NOCSLEW = '00:00:00.00 00:00:00.0 2010' / ntcs_moveto ra dec epoch          
NOCFITER=                    0 / Number of focus positions                  
NOCCSN  = 'kHeNeAr '           / Calibration lamp serial number             
NOCTOT  =                    1 / Total number of observations in set        
NOCSCR  = 'STFLAT  '           / NOHS script run                            
NOCTIM  =                   20 / [s] Requested integration time             
NOCOFFT = '0.0 0.0 '           / ntcs_offset RA Dec offset (arcsec)         
NOCROIPT= 'FullFrame'        / Detector ROI pattern (FullFrame|4kx2k|4kx300|2k
NOCSYS  = 'kpno 4m '           / system ID                                  
NOCNUM  =                    1 / observation number request                 
NOCLAMP = 'off     '           / Dome flat lamp status (on|off|unknown)     
NOCRBIN =                    1 / CCD row binning                            
NOCROICS=                    0 / Detector ROI colum start                   
NOCNPOS =                    1 / observation number in requested number     
NOCROI  = 'disabled'           / Detector ROI flag (enabled|disabled)       
NOCCBIN =                    1 / CCD column binning                         
NOCTYP  = 'FLAT    '         / Observation type (zero|dark|flat|arc|focus|acq|
NOCPOST = 'sky     '         / Calibration position (unknown|init|sky|dfs|lamp
NOCDPOS =                    0 / Dither position                            
NOCROICZ=                    0 / Detector ROI column size                   
NOCROIRS=                    0 / Detector ROI row start                     
NOCCAL  = 'HeNeAr  '           / Calibration lamp                           
NOCDPAT = 'unknown '           / Dither pattern                             
RAZERO  =               -36.13 / [arcsec] RA zero                           
RAINDEX =                    0 / [arcsec] RA index                          
ALT     = '90:00:00.0'         / Telescope altitude                         
DECINST =                    0 / [arcsec] Dec instrument center             
DECDIFF =                    0 / [arcsec] Dec diff                          
PARALL  =                  360 / [deg] parallactic angle                    
RADIFF  =                    0 / [arcsec] RA diff                           
DECZERO =                61.25 / [arcsec] Dec zero                          
AZ      = '0:00:00.0'          / Telescope azimuth                          
RAINST  =                    0 / [arcsec] RA instrument center              
DECOFF  =                    0 / [arcsec] Dec offset                        
DECINDEX=                    0 / [arcsec] Dec index                         
RAOFF   =                    0 / [arcsec] RA offset                         
GCCROTAT=            90.199997 / [Degrees] Instrument rotator angle         
KSDPOS  = 'b2k     '         / actual name {between|lo|med|high|narrow|other|o
KSDWPOS =                    6 / wheel actual pos {0|1|2|3|4|5|6}           
KSFILCMD= 'Open    '           / actual name {between|U|B|V|R|I|open}       
KSFW1POS=                    2 / wheel 1 actual pos {0|1|2|3|4|5|6}         
KSFW2POS=                    1 / wheel 2 actual pos {0|1|2|3|4|5|6}         
KSSWPOS =                    2 / wheel actual pos {0|1|2|3|4|5|6}           
KSSPOS  = '4pxB    '         / actual name {between|long|1px|2px|narrow|other|
KSCAMFOC=           1849.97998 / [um] camera focus                          
KSCAMZRO=                 1850 / [um] camera focus zeropoint                
DOMEERR =                    0 / [deg] Dome error as distance from target   
DOMEAZ  =                    0 / [deg] Dome position                        
KSTEMP1 =                 23.6 / [Celsius] temperature sensor 1             
KSTEMP2 =                 18.9 / [Celsius] temperature sensor 2             
KSTEMP3 =                 18.8 / [Celsius] temperature sensor 3             
KSTEMP4 =                 18.1 / [Celsius] temperature sensor 4             
KSCOLFOC=           499.980011 / [um] collimator focus                      
KSCOLZRO=                  500 / [um] collimator focus zeropoint            
DTSITE  = 'kp                '  /  observatory location                     
DTTELESC= 'kp4m              '  /  telescope identifier                     
DTINSTRU= 'kosmos            '  /  instrument identifier                    
DTCALDAT= '2014-09-21        '  /  calendar date from observing schedule    
ODATEOBS= '                  '  /  previous DATE-OBS                        
DTUTC   = '2014-09-22T01:37:04'  /  post exposure UTC epoch from DTS        
DTOBSERV= 'NOAO              '  /  scheduling institution                   
DTPROPID= '2014B-0461        '  /  observing proposal ID                    
DTPI    = 'John Salzer       '  /  Principal Investigator                   
DTPIAFFL= 'Indiana University'  /  PI affiliation                           
DTTITLE = 'Spectroscopy of Ultra-Low Metallicity Star-Forming Galaxies' / titl
DTCOPYRI= 'AURA              '  /  copyright holder of data                 
DTACQUIS= 'kosmosdhs-4m.kpno.noao.edu' / host name of data acquisition compute
DTACCOUN= 'cache             '  /  observing account name                   
DTACQNAM= '/home/data/n3.09786.fits'  /  file name supplied at telescope    
DTNSANAM= 'k4k_140922_013704_fri.fits'  /  file name in NOAO Science Archive
DT_RTNAM= 'k4k_140922_013704_fri'  /  NSA root name                         
DTSTATUS= 'done              '  /  data transport status                    
SB_HOST = 'kosmosdhs-4m.kpno.noao.edu'  /  iSTB client host                 
SB_ACCOU= 'cache             '  /  iSTB client user account                 
SB_SITE = 'kp                '  /  iSTB host site                           
SB_LOCAL= 'kp                '  /  locale of iSTB daemon                    
SB_DIR1 = '20140921          '  /  level 1 directory in NSA DS              
SB_DIR2 = 'kp4m              '  /  level 2 directory in NSA DS              
SB_DIR3 = '2014B-0461        '  /  level 3 directory in NSA DS              
SB_RECNO=              2025139  /  iSTB sequence number                     
SB_ID   = 'kp2025139         '  /  unique iSTB identifier                   
SB_NAME = 'k4k_140922_013704_fri.fits'  /  name assigned by iSTB            
SB_RTNAM= 'k4k_140922_013704_fri'  /  NSA root name                         
RMCOUNT =                    0  /  remediation counter                      
RECNO   =              2025139  /  NOAO Science Archive sequence number     
CHECKSUM= 'mhElmh9lmhClmh9l'    /  ASCII 1's complement checksum            
DATASUM = '0         '          /  checksum of data records                 
"""    


#!#DOC: vvv
#!# All bets are off in the original FITS file does not contain all of these.
#!RAW_REQUIRED_FIELDS = set([
#!    #!'OBSERVAT',
#!    'TELESCOP',
#!    # 'PROPOSER', #!!! will use PROPID when PROPOSER doesn't exist in raw hdr
#!])
#!
#!# These fields are required to construct the Archive filename and path.
#!# Some may be common with INGEST_REQUIRED (below).
#!FILENAME_REQUIRED_FIELDS = set([
#!    'DATE-OBS',  # triplespec doesn't have it; comes from other field
#!
#!    # for BASENAME
#!    'DTSITE',
#!    'DTTELESC',
#!    'DTINSTRU',
#!    'OBSTYPE',
#!    'PROCTYPE',
#!    'PRODTYPE',
#!
#!    # for PATH (dome)
#!    'DTCALDAT',
#!    'DTTELESC',
#!    'DTPROPID',
#!
#!    # for PATH (pipeline)
#!    #! 'DTSUBMIT',
#!    #! 'PLQUEUE',
#!    #! 'PLQNAME',
#!])
#!
#!# To be able to ingest a fits file into the archive, all of these must
#!# be present in the header.
#!# The commented out lines are Requirements per document, but did not seem to
#!# be required in Legacy code.
#!INGEST_REQUIRED_FIELDS = set([
#!    'SIMPLE',
#!    'OBSERVAT', # needed for std filename
#!    'DTPROPID', # observing proposal ID
#!    'DTCALDAT', # calendar date from observing schedule
#!    'DTTELESC', # needed to construct full file path in archive
#!    'DTACQNAM', # file name supplied at telescope; User knows only THIS name
#!    'DTNSANAM', # file name in archive (renamed from user supplied)
#!    'DTSITE',   # Required for standard file name (pg 9, "File Naming Conv...")
#!    'DTTELESC', # Required for standard file name (pg 9, "File Naming Conv...")
#!    'DTINSTRU', # Required for standard file name (pg 9, "File Naming Conv...")
#!])
#!
#!# We should try to fill these fields were practical. They are used in
#!# the archive. Under the portal they may affect ability to query or
#!# show as the results of queries.  If any of these are missing just
#!# before ingest, a warning will be logged indicating the missing
#!# fields.
#!INGEST_RECOMMENDED_FIELDS = set([
#!    'INSTRUME', # !!! moved from RAW_REQUIRED to satisfy:
#!                # /scraped/mtn_raw/ct15m-echelle/chi150724.1000.fits
#!    'DTACQNAM',
#!    'DTCALDAT', # calendar date from observing schedule
#!    'DTCOPYRI', # copyright holder of data (ADDED!!!)
#!    'DTINSTRU',
#!    'DTNSANAM',
#!    'DTOBSERV',
#!    'DTPI',
#!    'DTPIAFFL',
#!    'DTPROPID', # observing proposal ID
#!    'DTSITE',
#!    'DTTELESC',
#!    'DTTITLE',
#!    'PROCTYPE',
#!    'PRODTYPE',
#!    'OBSID',

#!#   'DTACCOUN', # observing account name
#!#   'DTACQUIS', # host name of data acquisition computer
#!#   'DTOBSERV', # scheduling institution
#!#   'DTPIAFFL', # PI affiliation 
#!#   'DTPUBDAT', # calendar date of public release 
#!#   'DTUTC',
#!])    
#!#DOC: ^^^
#!
#!# Fields used in hdr_calc_funcs.py
#!SUPPORT_FIELDS = set([
#!    'IMAGETYP',
#!    'DATE-OBS',
#!    'TIME-OBS',
#!    'DATE',
#!    'PROPID',
#!    #!'PLDSID',
#!    #!'PLQUEUE',
#!    #!'PLQNAME',
#!    ])

USED_FIELDS = (ts.RAW_REQUIRED_FIELDS
               | ts.FILENAME_REQUIRED_FIELDS
               | ts.INGEST_REQUIRED_FIELDS
               | ts.INGEST_RECOMMENDED_FIELDS
               | ts.SUPPORT_FIELDS)


def print_header(msg, hdr=None, fits_filename=None):
    """Provide HDR or FITS_FILENAME"""
    if hdr == None:
        hdulist = pyfits.open(fits_filename) 
        hdr = hdulist[0].header # use only first in list.
    # Print without blank cards or trailing whitespace
    hdrstr = hdr.tostring(sep='\n',padding=False)
    print('{}: '.format(msg))
    print(*[s.rstrip() for s in hdrstr.splitlines()
            if s.strip() != ''],
          sep='\n')

def changed_kw_str(funcname, hdr, new, outkws):
    """RETURN: string explaining what changed from HDR to NEW"""
    hset = set(hdr.keys())
    nset = set(new.keys()) | outkws
    added = nset - hset
    oldvals = dict()
    for k in added:
        oldvals[k] = hdr[k]
    msg = ('Applied {} which added/modified fields ({}). Old values were: {}'
           .format(funcname,
                   added,
                   ', '.join(['{}={}'.format(k,w) for (k,w) in oldvals.items()])
                   ))
    return msg

    
    
# It seems unconscionably complex for Ingest to require extra lines be
# prepended to the text of the fits header.  The only reason those
# same 5 fields couldn't be added to the header itself is that one of
# them is 9 characters but fits limites field names to 8 characters.
# Once Ingest made the decision to require special non-header fields,
# it should have just defined exactly what it needed (not prepended);
# including defining what is optional.  There is no published
# "contract" for what exactly should be sent to Ingest via TCP!
def get_archive_header(fits_file, checksum):
    "Get the 'header' that archive ingest wants to see sent to it over TCP"
    # Only look at first/primary HDU?!!! (Header Data Unit)
    hdu = pyfits.open(fits_file)[0] # can be compressed
    #hdr_keys = set(hdu.header.keys())
    params = dict(filename=fits_file,
                  filesize=os.path.getsize(fits_file),
                  checksum=checksum,
                  hdr=hdu.header,
              )
    return """\
#filename = {filename}
#reference = {filename}
#filetype = UNKNOWN
#filesize = {filesize} bytes
#file_md5 = {checksum}

{hdr}
""".format(**params)

def missing_in_hdr(hdr, required_fields):
    hdr_keys = set(hdr.keys())
    missing = required_fields - hdr_keys
    return missing

def missing_in_raw_hdr(hdr):
    """Header from original FITS input to TADA doesn't contain minimum
 acceptable fields."""
    return missing_in_hdr(hdr, ts.RAW_REQUIRED_FIELDS)

def missing_in_filename_hdr(hdr):
    """Header from FITS doesn't contain minimum fields acceptable for
 generating standard filename."""
    return missing_in_hdr(hdr, ts.FILENAME_REQUIRED_FIELDS)

def missing_in_archive_hdr(hdr):
    """Header from FITS doesn't contain minimum fields acceptable for
 Archive Ingest."""
    return missing_in_hdr(hdr, ts.INGEST_REQUIRED_FIELDS)

def missing_in_recommended_hdr(hdr):
    "Header from FITS doesn't contain all fields recommended for ingest."
    return missing_in_hdr(hdr, ts.INGEST_RECOMMENDED_FIELDS)

#! def valid_header(fits_file):
#!     """Read FITS metadata and insure it has what we need. 
#! Raise exception if not."""
#!     try:
#!         # Only look at first/primary HDU?!!! (Header Data Unit)
#!         hdulist = pyfits.open(fits_file) # can be compressed
#!         hdr = hdulist[0].header
#!     except Exception as err:
#!         raise tex.InvalidHeader('Metadata keys could not be read: {}'
#!                                        .format(err))
#!     missing = missing_in_raw_hdr(hdr)
#!     if len(missing) > 0:
#!         raise tex.HeaderMissingKeys(
#!             'Missing required metadata keys: {} in file {}'
#!             .format(missing, hdr.get(DTACQNAM,'NA')))
#!     return True




def validate_raw_hdr(hdr, orig_fullname):
    missing = missing_in_raw_hdr(hdr)
    #!logging.debug('EXECUTE fu.validate_raw_hdr(); missing={}'.format(missing))
    if len(missing) > 0:
        msg = ('Raw FITS header is missing required metadata fields ({}) '
               'in file {}').format(', '.join(sorted(missing)), orig_fullname)
        #raise tex.IngestRejection(orig_fullname, msg, hdr)
        raise tex.InvalidHeader(msg)
    return True    

def validate_cooked_hdr(hdr, orig_fullname):
    missing = missing_in_archive_hdr(hdr)  | missing_in_filename_hdr(hdr)
    if len(missing) > 0:
        msg = ('Modified FITS header is missing required metadata fields ({}) '
               'in file {}').format(', '.join(sorted(missing)), orig_fullname)
        #raise tex.IngestRejection(orig_fullname, msg, hdr)
        raise tex.InvalidHeader(msg)
    return True

def validate_recommended_hdr(hdr, orig_fullname):
    missing = missing_in_recommended_hdr(hdr)
    if len(missing) > 0:
        logging.warning(
            'Modified FITS header is missing recommended metadata fields ({}) '
            'in file {}'
            .format(', '.join(sorted(missing)), orig_fullname))
    return True

def fitsverify(fname):
    '''Verify FITS file. Throw exception on invalid.'''
    logging.debug('fitsverify({})'.format(fname))
    cmd = ['/usr/local/bin/fitsverify', '-e', '-q', fname]
    try:
        subprocess.check_output(cmd)
    except Exception as err:
        #!raise tex.InvalidFits('Verify failed: {}'.format(' '.join(cmd)))
        raise tex.InvalidFits('Verify failed: /usr/local/bin/fitsverify -e -q {}'
                              .format(os.path.basename(fname)))
    logging.debug('{} PASSED fitsverify()'.format(fname))
    return True

# propid=`curl 'http://127.0.0.1:8000/schedule/propid/kp4m/kosmos/2016-02-01/'`
def http_get_propid_for_db(telescope, instrument, date, hdrpid,
                           timeout=10, #secs to wait for any bytes
                           host=None, port=8000) :
    '''Use MARS web-service to get PROPID to use in DB 
given: Telescope, Instrument, Date of observation.  
    '''
    url = ('http://{}:{}/schedule/dbpropid/{}/{}/{}/{}/'
           .format(host, port, telescope, instrument, date, hdrpid))
    logging.debug('MARS: get PROPID from schedule; url = {}'.format(url))
    pid = None
    r = requests.get(url, timeout=timeout)
    response = r.text
    logging.debug('MARS: server response="{}"'.format(response))
    if r.status_code == 200:
        logging.debug('MARS: server status ok')
        return response
    else:
        msg = ('{}:MARS svc={}; {}.'
               .format(r.status_code, url.replace(host,'mars.host'), response))
        logging.info(msg)
        raise tex.MarsWebserviceError(response)

def ws_get_propid(date, telescope, instrument, hdr_pid):
    """Return propid suitiable for use in DB."""
    host=ts.natica_host
    port=ts.natica_port
    if host == None or port == None:
        msg = 'Missing MARS host ({}) or port ({}).'.format(host,port)
        logging.info(msg)
        raise tex.MarsWebserviceError(msg)

    # telescope, instrument, date = ('kp4m', 'kosmos', '2016-02-01')
    logging.debug('WS schedule lookup; '
                  'DTCALDAT="{}", DTTELESC="{}", DTINSTRU="{}"'
                  .format(date, telescope, instrument))
    try:
        pid = http_get_propid_for_db(telescope, instrument, date, hdr_pid,
                                     host=host, port=port)
    except Exception as err:
        msg = ('Failed Propid lookup '
               'tele={}, instr={}, date={}, hdrpid={}; {}')\
               .format(telescope, instrument, date, hdr_pid, err)
        logging.info(msg)
        raise tex.MarsWebserviceError(err)
    return pid

def set_dtpropid(orig, **kwargs):
    pid = ws_get_propid(orig.get('DTCALDAT'),
                            orig.get('DTTELESC'),
                            orig.get('DTINSTRU'),
                            orig.get('DTPROPID', orig.get('PROPID', None)))
    return {'DTPROPID': pid}
    

def fix_hdr(hdr, fname, options, opt_params, ignore_schedule=False, **kwargs):
    '''
SIDE-EFFECT: Modify hdr dict in place to suit Archive Ingest. 
Include fields in hdr needed to construct new filename that fullfills standards.

    options :: e.g. {'INSTRUME': 'KOSMOS', 'OBSERVAT': 'KPNO'}
    '''
    orig_fullname = opt_params.get('filename',
                                   hdr.get('DTACQNAM',
                                           '<no filename option provided>'))
    logging.debug('fix_hdr; options={}'.format(options))
    for k,v in options.items():
        hdr[k] = v

    scrub_errors = scrub.scrub_hdr(hdr)
    if opt_params.get('VERBOSE', False):
        if len(scrub_errors) > 0:
            logging.warning('scrub_errors={}'.format(scrub_errors))
    #tex.BadFieldContent(scrub_errors)

    # Validate after explicit overrides, before calculated fields.
    # This is because calc-funcs may depend on required fields.
    #!validate_raw_hdr(hdr)

    calc_param = opt_params.get('calchdr',None)
    calc_funcs = []
    origkws = set(hdr.keys())
    if calc_param != None:
        for funcname in calc_param:
            try:
                func = eval('hf.'+funcname)
                #!func = ts.HDR_FUNCS[funcname]
                calc_funcs.append(func)
                #!logging.error('hdrfunc use DISABLED')
            except:
                raise Exception('Function name "{}" given in option "calchdr"'
                                ' does not exist in MARSHOST/admin/tada/hdrfunc/'
                                .format(funcname))
    logging.error('calc_funcs={}'.format([f.__name__ for f in calc_funcs]))
    #!for calcfunc in calc_funcs:
    #!    funcname = calcfunc.__name__
    #!    try:
    #!        if not calcfunc.inkws.issubset(origkws):
    #!            missing = calcfunc.inkws.difference(origkws)
    #!            msg = ('Some keywords ({}) required (per inkeywords) by HDR'
    #!                   ' FUNC "{}" are not in the header of file "{}". '
    #!                   ' SOLUTIONS: Fix FITS, change HDR FUNC inkeywords')
    #!            raise tex.InvalidHeader(msg.format(', '.join(missing),
    #!                                               funcname, fname))
    #!        new = calcfunc(hdr, **kwargs)
    #!        if not calcfunc.outkws.issubset(new.keys()):
    #!            missing = calcfunc.outkws.difference(new.keys())
    #!            msg = ('Some keywords ({}) produced (per outkeywords) by HDR'
    #!                   ' FUNC "{}" are not in the new header of file "{}". '
    #!                   ' SOLUTION: Fix HDR FUNC defintion or change'
    #!                   ' outkeywords')
    #!            raise tex.InvalidHeader(msg.format(', '.join(missing),
    #!                                               funcname, fname))
    #!    except Exception as ex:
    #!        raise tex.InvalidHeader(
    #!            'Could not apply hdr_calc_funcs ({}) to {}; {}'
    #!            .format(funcname, fname, ex))
    #!    logging.debug('Apply {} to {}; new field values={}'
    #!                  .format(funcname, fname, new))
    #!    hdr.update(new)
    #!    hdr['HISTORY'] = changed_kw_str(funcname, hdr, new, calcfunc.outkws)

    #new = hf.set_dtpropid(hdr, **kwargs)
    if ignore_schedule:
        new = {}
    else:
        new = set_dtpropid(hdr, **kwargs) # !!! Emitted warning ref orig_fullname

    logging.debug('Updating DTPROPID from {} => {}'
                  .format(hdr.get('DTPROPID'),
                          new.get('DTPROPID')))
    hdr.update(new)
    
    if hdr.get('DTPROPID') == 'BADSCRUB' or hdr.get('DTPROPID') == 'NOSCHED': 
        raise tex.SubmitException(
            'Could not create good DTPROPID from PROPID ({}) or from schedule '
            'lookup for header of: {} (DTPROPID={})'
            .format(hdr.get('PROPID', 'NA'), orig_fullname,
                    hdr.get('DTPROPID')))
        

def show_hdr_values(msg, hdr):
    """Show the values for 'interesting' header fields"""
    #!for key in RAW_REQUIRED_FIELDS.union(INGEST_REQUIRED_FIELDS):
    print('{}: '.format(msg), end='')
    for key in ts.RAW_REQUIRED_FIELDS:
        print('{}="{}"'.format(key,hdr.get(key,'<not given>')),end=', ')
    print()

def get_options_dict(fits_filename):
    if os.path.exists(fits_filename + '.yaml'):
        with open(fits_filename + '.yaml') as yy:
            yd = yaml.safe_load(yy)
            options = yd.get('options', {})
            opt_params = yd.get('params', {})
    else:
        logging.error('Options file not found for: {}'.format(fits_filename))
        return dict(), dict()

    return options, opt_params

def get_personality_dict(personality_file):
    logging.debug('EXECUTING: get_personality_dict({})'
                  .format(personality_file))

    options = dict()
    opt_params = dict()
    if not os.path.exists(personality_file):
        logging.warning('personality_file does not exist: {}'
                        .format(personality_file))
        return options, opt_params

    if PurePath(personality_file).suffix == '.yaml':
        with open(personality_file) as yy:
            yd = yaml.safe_load(yy)
            options = yd.get('options', {})
            opt_params = yd.get('params', {})
#!    elif PurePath(personality_file).suffix == '.personality':
#!        cmd = 'source {}; echo $TADAOPTS'.format(personality_file)
#!        optstr = subprocess.check_output(['bash', '-c', cmd ]).decode()
#!        for opt in optstr.replace('-o ', '').split():
#!            k, v = opt.split('=')
#!            if k[0] != '_':
#!                continue
#!            if k[1] == '_':
#!                opt_params[k[2:]] = v
#!            else:
#!                options[k[1:]] = v.replace('_', ' ')                

        if 'calchdr' in opt_params:
            opt_params['calchdr'] = opt_params['calchdr'].split(',')
        
    logging.debug('get_personality_dict({}) => popts_dict={}, pprms_dict={}'
                  .format(personality_file, options, opt_params))
    return options, opt_params
    
def apply_options(options, hdr):
    for k,v in options.items():
        hdr[k] = v  # overwrite with explicit fields from personality

def UNCOMPPLETE_hdrtxt_to_dict(ffile):
    hdr = dict()
    with open(ffile) as f:
        for line in f:
            if '=' in line:
                kstr,vstr = line.split('/')[0].strip().split('=')
                hdr[kstr.strip()] = vstr.strip()
    return hdr

def hdrtxt_to_hdr(ffile):
    hdr = pyfits.Header()
    with open(ffile) as f:
        for line in f:
            if '=' in line:
                kstr,vstr = line.split('/')[0].strip().split('=')
                hdr[kstr.strip()] = vstr.strip()
    return hdr

def txt_to_hdr(ffile):
    hdr = dict()
    with open(ffile) as f:
        for line in f:
            if '=' in line:
                kstr,vstr = line.split('/')[0].strip().split('=')
                hdr[kstr.strip()] = vstr.strip()
    return hdr

def get_hdr_as_dict(fitsfile):
    #!hdict = dict()
    #!for hdu in pyfits.open(fitsfile):
    #!    hdict.update(dict(hdu.header))

    hdict = dict()
    hdulist = pyfits.open(fitsfile)
    for field in (USED_FIELDS | hd.all_in_keywords | hd.all_out_keywords):
        if field in hdulist[0].header:
            # use existing Primary HDU field
            hdict[field] = hdulist[0].header[field]
        else:
            # use last existing Extension HDU field
            for hdu in hdulist[1:]:
                if field in hdu.header:
                    hdict[field] = hdu.header[field]

    modified_keys = sorted(list(hdict.keys()))
    hdict['COMMENT'] = 'MODIFIED:{}'.format(','.join(modified_keys))
    return hdict


#!FLOAT_FIELDS =  [#'BSCALE', 'BZERO',
#!    'DATAMAX', 'DATAMIN',
#!    'PSCAL', 'PZERO',
#!    'TSCAL', 'TZERO',
#!    'CRPIX', 'CRVAL', 'CDELT', 'CROTA', 'PC', 'CD',
#!    'PV', 'CRDER', 'CSYER',
#!    'EPOCH', 'EQUINOX',
#!    #'DATE-OBS', # standard calls this Float and String
#!    'MJD-OBS', 'MJD-AVG',
#!    'LONPOLE', 'LATPOLE', 
#!    'OBSGEO-X', 'OBSGEO-Y', 'OBSGEO-Z',
#!    'RESTFRQ', 'RESTWAV',
#!    'VELANGL', 'VELOSYS', 'ZSOURCE']
#!

def is_floatingpoint(fitsfile):
    hdulist = pyfits.open(fitsfile)
    fpimage=False
    for hdu in hdulist:
        hdr = hdu.header
        if hdr.get('BITPIX',None) == -32 or hdr.get('BITPIX',None) == -64:
            fpimage=True
    return fpimage



# FITS standard 3.0 (July 2010) defines these fields as floats:
#  BSCALE, BZERO,
#  DATAMAX, DATAMIN,
#  PSCALn, PZEROn,
#  TSCALn, TZEROn,
#  CRPIXj, CRVALi, CDELTi, CROTAi, PCi_j, CDi_j
#  PVi_m, CRDERi, CSYERi,
#  EPOCH, EQUINOXa, DATE-OBS, MJD-OBS, LONPOLEa, LATPOLEa, MJD-AVG,
#  OBSGEO-Za, OBSGEO-Ya, OBSGEO-Za,
#  RESTFRQa, RESTWAVa,
#  VELANGLa, VELOSYSa, ZSOURCEa
def scrub_fits(fitsfname):
    """Fix some violations against FITS standard (3.0) IN PLACE."""

    hdulist = pyfits.open(fitsfname, mode='update')
    for hdu in hdulist:
        # Remove any fields defined by standard as FLOAT whos value is NOT float.
        for kw in ts.FLOAT_FIELDS:
            hdr = hdu.header
            if (kw in hdr) and (type(hdr[kw]) is str):
                try:
                    ff = float(hdr(kw))
                except:
                    msg = ('Removed "{}" since its value ("{}") was a string'
                       .format(kw, hdr[kw]))
                    hdr['HISTORY'] = msg
                    del hdr[kw]
                    logging.warning('Invalid FITS file "{}": {}'
                                    .format(fitsfname, msg))
                else:
                    hdr = ff
    hdulist.close(output_verify='fix')

# EXAMPLE:
#   find /data/raw -name "*.fits*" -print0 | xargs --null  fits_compliant
#!def fits_compliant(fits_file_list,
#!                   personalities=[],
#!                   quiet=False, ignore_recommended=False,
#!                   show_values=False, show_header=False, show_stdfname=True,
#!                   required=False, verbose=False, trace=False):
#!    """Check FITS file for complaince with Archive Ingest."""
#!    import warnings
#!
#!    logging.debug('EXECUTING fits_compliant({}, personalities={}, '
#!                  'quiet={}, show_values={}, show_header={}, show_stdfname={}, '
#!                  'required={}, verbose={}, trace={})'
#!                  .format(fits_file_list, personalities, quiet,
#!                          show_values, show_header, show_stdfname,
#!                          required, verbose, trace))
#!
#!    warnings.simplefilter('error',AstropyWarning)
#!    warnings.simplefilter('error',AstropyUserWarning)
#!
#!    if personalities == None:
#!        personalities = []
#!    bad = 0
#!    bad_files = set()
#!    exception_cnt = 0
#!    if required:
#!        print()
#!        print('## RAW_REQUIRED_FIELDS:\n'
#!              'These fields MUST be in raw fits header (or provided by '
#!              'options at submit time). If not, field calculation will not '
#!              'be attempted, and ingest will be aborted: \n\n1.\t{}'
#!              .format( '\n1.\t'.join(sorted(ts.RAW_REQUIRED_FIELDS))))
#!        print()
#!        print('## FILENAME_REQUIRED_FIELDS:\n'
#!              'These fields MUST be in hdr to be able to calculate standard '
#!              'Archive filename and path. They may '
#!              'be calculated from raw fits fields and options provided '
#!              'at submit time. If any of these fields are not in hdr after '
#!              'calculation, ingest will be aborted: \n\n1.\t{}'
#!              .format( '\n1.\t'.join(sorted(ts.FILENAME_REQUIRED_FIELDS))))
#!        print()
#!        print('##INGEST_REQUIRED_FIELDS:\n'
#!              'These fields MUST be in hdr given to Ingest. They may '
#!              'be calculated from raw fits fields and options provided '
#!              'at submit time. If any of these fields are not in hdr after '
#!              'calculation, ingest will be aborted: \n\n1.\t{}'
#!              .format( '\n1.\t'.join(sorted(ts.INGEST_REQUIRED_FIELDS))))
#!        print()
#!        print('## SUPPORT_FIELDS:\n'
#!              'These fields are used by hdr_cacl_funcs.py '
#!              '(aka Mapping functions) or Pipeline. '
#!              'They are likely required, but it depends on the personality '
#!              'and pipeline uses.'
#!              '\n\n1.\t{}'
#!              .format( '\n1.\t'.join(sorted(ts.SUPPORT_FIELDS))))
#!        print()
#!        print('## INGEST_RECOMMENDED_FIELDS:\n'
#!              'These fields SHOULD be in hdr given to Ingest. They may '
#!              'be calculated from raw fits fields and options provided '
#!              'at submit time. If any of these fields are not in hdr after '
#!              'calculation, portal queries may lack features: \n\n1.\t{}'
#!              .format( '\n1.\t'.join(sorted(ts.INGEST_RECOMMENDED_FIELDS))))
#!        print()
#!
#!
#!    
#!    all_missing_raw = set()
#!    all_missing_cooked = set()
#!    all_missing_recommended = set()
#!    options = dict()
#!    opt_params = dict()
#!    for p in personalities:
#!        opts, prms = get_personality_dict(p)
#!        options.update(opts)
#!        opt_params.update(prms)
#!    #!print('DBG: options={}, opt_params={}'.format(options, opt_params))
#!    for ffile in fits_file_list:
#!        is_text = (magic.from_file(ffile).decode() == 'ASCII text')
#!        valid = True
#!        missing_raw = []
#!        missing_cooked = []
#!        missing_recommended = []
#!        #!fname_fields = None
#!        try:
#!            #!valid_header(ffile)
#!            if is_text:
#!                logging.debug('fits_compliant: {} is TEXT header'.format(ffile))
#!                hdr = hdrtxt_to_hdr(ffile)
#!            else:
#!                # use only first in list.
#!                #! hdr = pyfits.open(ffile)[0].header
#!                hdr = get_hdr_as_dict(ffile)
#!            hdr['DTNSANAM'] = 'NA' # we will set after we generate_fname, here to pass validate
#!            #! hdr['DTACQNAM'] = ffile
#!
#!            if opt_params.get('OPS_PREAPPLY_UPDATE','no') == 'yes': #!!!
#!                apply_options(options, hdr)
#!            if show_header:
#!                print('Post modify:')
#!                pprint(hdr)
#!            missing_raw = missing_in_raw_hdr(hdr)
#!            if len(missing_raw) == 0:
#!                #!fname_fields = modify_hdr(hdr, ffile, options, opt_params)
#!                fix_hdr(hdr, ffile, options, opt_params, ignore_schedule=True)
#!                missing_cooked = missing_in_archive_hdr(hdr)
#!                missing_recommended = missing_in_recommended_hdr(hdr)
#!        except Exception as err:
#!            exception_cnt += 1
#!            print('EXCEPTION in fits_compliant on {}: {}'.format(ffile, err))
#!            tut.trace_if(trace)
#!            valid = False
#!            bad_files.add(ffile)
#!            bad += 1
#!            continue
#!
#!        all_missing_raw.update(missing_raw)
#!        all_missing_cooked.update(missing_cooked)
#!        all_missing_recommended.update(missing_recommended)
#!        if (len(missing_raw) + len(missing_cooked)) > 0:
#!            valid = False
#!        new_basename = 'NA'
#!        if show_stdfname:
#!            try:
#!                new_basename = fn.generate_fname(hdr, fn.fits_extension(ffile),
#!                                                 orig=ffile,
#!                                                 require_known=False)
#!            except Exception as ex:
#!                logging.warning('Could not generate archive fname; {}'.format(ex))
#!            if not quiet:
#!                print('{} produced from {}'.format(new_basename, ffile))
#!        if show_values:
#!            show_hdr_values('Post modify', hdr) # only "interesting" ones
#!
#!        if valid:
#!            if not quiet:
#!                print('{}:\t IS compliant'.format(ffile))
#!        else:
#!            bad_files.add(ffile)
#!            bad += 1
#!            if ignore_recommended:
#!                print('{}:\t NOT compliant; '
#!                      'Missing fields or bad content; '
#!                      'raw: {}, cooked: {}, exceptions: {}'
#!                      .format(ffile,
#!                              sorted(missing_raw),
#!                              sorted(missing_cooked),
#!                              exception_cnt,
#!                  ))
#!            else:
#!                print('{}:\t NOT compliant; '
#!                      'Missing fields or bad content; '
#!                      'raw: {}, cooked: {}, recommended: {}, '
#!                      'exceptions: {}'
#!                      .format(ffile,
#!                              sorted(missing_raw),
#!                              sorted(missing_cooked),
#!                              sorted(missing_recommended),
#!                              exception_cnt,
#!                  ))
#!    # END for ffile
#!
#!    if (verbose and (bad > 0)):
#!        print('Non-complaint files: {}'.format(', '.join(bad_files)))
#!
#!    if len(fits_file_list) > 0:
#!        recom_cnt = 0 if ignore_recommended else len(all_missing_recommended)
#!        if (len(all_missing_raw) + len(all_missing_cooked)+ recom_cnt) > 0:
#!            print('Fields missing from at least one file:\n'
#!                  '   Raw:         {}\n'
#!                  '   Cooked:      {}\n'
#!                  '   Recommended: {}\n'
#!                  '   Exceptions:  {}\n'
#!                  '   (Cooked & Recommended exclude files that have missing '
#!                  'Raw fields)'
#!                  .format(sorted(all_missing_raw),
#!                          sorted(all_missing_cooked),
#!                          sorted(all_missing_recommended),
#!                          exception_cnt,
#!                  ))
#!        print('\n{} of {} files are compliant (for Archive Ingest)'
#!              .format(len(fits_file_list)-bad, len(fits_file_list)))
#!        if exception_cnt > 0:
#!            sys.exit('Abnormal termination due to exception(s)')


##############################################################################

def main():
    "Parse command line arguments and do the work."
    #!dflt_config = '/etc/tada/tada.conf'
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=('Check for compliance of FITS files with respect '
                     'to Archive Ingest'),
        epilog=('EXAMPLES: '
                '\n\t{prog} --required'
                '\n\t{prog} foo.fits bar.fits.fz'
                .format(prog='%(prog)s'))
        )

    with open('/opt/tada/build/lib/tada/VERSION') as version_file:
        tada_version = version_file.read().strip()
    
    parser.add_argument('--version', action='version', version=tada_version)
    parser.add_argument('infiles',
                        nargs='*',
                        help='Input file')
    parser.add_argument('-q','--quiet',
                        action='store_true',
                        help='Do not list each compliant file')
    parser.add_argument('--ignore_recommended',
                        action='store_true',
                        help='Do not report on RECOMMENDED fields.')
    parser.add_argument('-t','--trace',
                        action='store_true',
                        help='Produce stack trace on error')
    parser.add_argument('-p','--personality',
                        action='append',
                        help=('Personality file that adds explicit and '
                        'calculated fields to each FITS hdr'))
    parser.add_argument('--required',
                        action='store_true',
                        help='Report on fields required for Archive Ingest')
    parser.add_argument('--values',
                        action='store_true',
                        help='Show header values for interesting fields')
    parser.add_argument('--header',
                        action='store_true',
                        help='Show full header')
    parser.add_argument('--loglevel',
                        help='Kind of diagnostic output',
                        choices=['CRTICAL', 'ERROR', 'WARNING',
                                 'INFO', 'DEBUG'],
                        default='WARNING')
    args = parser.parse_args()
    #!args.outfile.close()
    #!args.outfile = args.outfile.name

    #!print 'My args=',args
    #!print 'infile=',args.infile

    log_level = getattr(logging, args.loglevel.upper(), None)
    if not isinstance(log_level, int):
        parser.error('Invalid log level: %s' % args.loglevel)
    logging.basicConfig(level=log_level,
                        format='%(levelname)s %(message)s',
                        datefmt='%m-%d %H:%M')
    logging.debug('Debug output is enabled in %s !!!', sys.argv[0])

    # fits_compliant /data/raw/nhs_2014_n14_299403.fits
    #!fits_compliant(args.infiles,
    #!               personalities=args.personality,
    #!               quiet=args.quiet,
    #!               required=args.required,
    #!               ignore_recommended=args.ignore_recommended,
    #!               show_values=args.values,
    #!               show_header=args.header,
    #!               #show_stdfname=False, #!!!
    #!               trace=args.trace )

    

if __name__ == '__main__':

    main()

 

