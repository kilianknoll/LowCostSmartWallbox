# Subroutine to define a timestamp for logging
# 24.12.2015 
#

import datetime
import time


def loggerdate():
    meintimestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H:%M:%S')    
    return (meintimestamp)

        
