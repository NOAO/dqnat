"Actions that can be run against entry when popped off queue."
# Put directly in dataq_pop_svc.py since NATICA does all actions from mars
# and dqnat is tailored for NATICA.

##############################################################################

#!!import random
#!!import logging
#!!#import os
#!!#from natica.externals import dq_ingest
#!!#import marssite.marssite.settings
#!!#marssite.marssite.settings.configure()
#!!
#!!
#!!
#!!def echo30(rec, qname, **kwargs):
#!!    "For diagnostics (fails 30% of the time)"
#!!    prop_fail = 0.30
#!!    print('[{}] Action=echo30: rec={} kwargs={}'.format(qname, rec, kwargs))
#!!    # randomize success to simulate errors on cmds
#!!    return random.random() >= prop_fail
#!!
#!!
#!!action_lut = dict(
#!!    echo30=echo30, # sample. Not used for production.
#!!    submit=dq_ingest,
#!!    )
