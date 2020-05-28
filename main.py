import os
import lib
import argparse
import logging
import threading
from StreamDeck.DeviceManager import DeviceManager

if __name__ == "__main__":

  parser = argparse.ArgumentParser(description="Elgato Streamdeck Daemon.")
  parser.add_argument('--log_level', dest='log', help='Sets logging level to either: CRITICAL, ERROR, WARNING, INFO or DEBUG')
  parser.add_argument('--config_dir', dest='config', help='Directory where config is stored. Defaults to \'$XDG_CONFIG_HOME/streamdeck_manager\'')

  args = parser.parse_args()

  streamdecks = DeviceManager().enumerate()

  streamdecks_arr = list()
  logger = logging.getLogger(lib.STANDARD_LOGGER_ID)
  log_formatter   = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
  console_handler = logging.StreamHandler()
  console_handler.setFormatter(log_formatter)
  logger.setLevel(logging.DEBUG)
  for index, deck in enumerate(streamdecks):
    streamdecks_arr.append(deck)


  if len(streamdecks_arr) > 1:
    raise ValueError("This only supports one Streamdeck at once")
  elif len(streamdecks_arr) < 1:
    raise ValueError("No Streamdeck found")
  else:
    config_dir = args.config if args.config is not None else os.path.join(os.environ.get('XDG_CONFIG_HOME'), 'streamdeck_manager')
    parser = lib.Parser('config.json', streamdecks_arr[0], config_path=config_dir, callback_source='functions.py')

    for t in threading.enumerate():
      if t is threading.currentThread():
        continue
      if t.is_alive():
        t.join()
