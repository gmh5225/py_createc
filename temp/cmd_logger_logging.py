import code
import sys
import yaml
import logging
import logging.config

class Tee(object):
  def __init__(self, logger):
    pass

  def __del__(self):
    # Restore sin, so, se
    sys.stdout = sys.__stdout__
    sys.stdir = sys.__stdin__
    sys.stderr = sys.__stderr__

  def write(self, data):
    logger.info(data)
    sys.__stdout__.write(data)
    sys.__stdout__.flush()

  def readline(self):
    s = sys.__stdin__.readline()
    sys.__stdin__.flush()
    logger.info(s)
    return s

  def flush(foo):
    return
	
with open('./cmd_logger.yaml', 'rt') as f:
    config = yaml.safe_load(f.read())
logging.config.dictConfig(config)    
logger = logging.getLogger('main')

sys.stdout = sys.stderr = sys.stdin = Tee(logger)

console = code.InteractiveConsole()
console.interact()