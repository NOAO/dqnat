"""Read, parse, and validate configuration file.
"""
#import json
import yaml
import logging
import json

Q_REQUIRED_FIELDS = {'name', 'type', 'dq_host', 'dq_port',
                     'action_name',
                     'maximum_errors_per_record',
                     'maximum_queue_size',
                 }

TYPE_SPECIFIC_REQ_FIELDS = dict(
    MOUNTAIN={
        #'cache_dir',
        #'mirror_dir',
        'next_queue',
    },
    VALLEY={
        #'mirror_dir',
        'archive_irods331',
        #'noarchive_dir',
    },
)

def get_config_lut(config):
    "Return dictionary indexed by queue name."
    return dict([[q['name'], q] for q in config['queues']])


def validate_config(cfg, fname=None, qnames=None):
    "Make sure config has the fields we expect."
    if qnames == None:
        qnames = list()
    if 'dirs' not in cfg:
        raise Exception('No "dirs" field in {}'.format(fname))
    if 'queues' not in cfg:
        raise Exception('No "queues" field in {}'.format(fname))

    for q in cfg['queues']:
        fields = set(q.keys())
        missing = Q_REQUIRED_FIELDS - fields
        if  len(missing) > 0:
            raise Exception('Queue "{}" in {} is missing fields: {}'
                            .format(
                                q.get('name','UNKNOWN'),
                                fname,
                                missing
                            ))
        qs_missing = TYPE_SPECIFIC_REQ_FIELDS[q['type']] - fields
        if  len(qs_missing) > 0:
            raise Exception('Queue "{}" in {} is missing fields: {}'
                            .format(
                                q.get('name', 'UNKNOWN'),
                                fname,
                                qs_missing
                            ))

    missingqs = set(qnames) - set([d['name'] for d in cfg['queues']])
    if len(missingqs) > 0:
        raise Exception(
            'Config in {} is missing required queues {}. Required {}.'
            .format(fname, ', '.join(missingqs), ', '.join(qnames) ))

def get_config(configfile='/etc/mars/dq-config.json'):
    with open(configfile) as f:
        dqcfg = json.load(f)
#!    with open(schemafile) as f:  #@@@ schema for DQ config
#!        schema = json.load(f)
#!        jsonschema.validate(dqcfg, schema)
    return dqcfg

def OLD_get_config(queue_names,
               yaml_filename='/etc/tada/tada.conf',
               hiera_filename='/etc/tada/from-hiera.yaml',
               validate=False):
    """Read multi-queue config from yaml_filename.  Validate its
contents. Insure queue_names are all in the list of named queues."""

    try:
        cfg = yaml.load(open(yaml_filename))
    except:
        raise Exception('ERROR: Could not read data-queue config file "{}"'
                        .format(yaml_filename))
    try:
        cfg.update(yaml.load(open(hiera_filename)))
    except Exception as err:
        raise Exception('ERROR: Could not read data-queue config file "{}"; {}'
                        .format(hiera_filename, str(err)))
    if validate:
        validate_config(cfg, qnames=queue_names, fname=yaml_filename)
    #!lut = get_config_lut(cfg)
    #return dict([[q['name'], q] for q in config['queues']])
    lut = cfg
    if validate:
        missing = set(queue_names) - set(lut.keys())
    else:
        missing = set()
    if len(missing) > 0:
        raise Exception(
            'ERROR: Config file "{}" does not contain named queues: {}'
            .format(yaml_filename, missing))
    #return lut, cfg['dirs']
    logging.debug('get_config got: {}'.format(lut))
    return lut, dict()

