import os
import threading
import logging
import json
from PIL import Image, ImageDraw, ImageFont
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper

###############################################################################
#                                  Constants                                  #
###############################################################################

STANDARD_ICON = None
"""
Standard icon for new keys if no icon was provided.
"""

STANDARD_LABEL = "key"
"""
Standard label for new keys if no label was provided.
"""

STANDARD_LOGGER_ID = "streamdeck"
"""
Standard logger id for new objects if no id was provided.
"""

def __standard_on_press(key, page, deck_man):
  key.logger.debug("Key {} has been {}, but no callback was assigned."
                   .format(key.name, "pressed" if key.pressed else "released"))

EMPTY_ON_PRESS = __standard_on_press
"""
Standard callback function that is called when its button is pressed.
"""

###############################################################################
#                                   Classes                                   #
###############################################################################


class Key:
  """
  This class represents a key configuration for the Elgato Streamdeck.
  This class stores information about styling of the key, a callback function,
  that is called when the button is pressed, as well as a "state" object, that
  can track the state of the key (like a counter, or configuration of a generic
  callback function.
  """
  def __init__(self, name="undefined",
               icon_pressed=STANDARD_ICON,
               icon_released=STANDARD_ICON,
               label_pressed=STANDARD_LABEL,
               label_released=STANDARD_LABEL,
               logger_id=STANDARD_LOGGER_ID,
               state=None,
               on_press=EMPTY_ON_PRESS):
    self.name           = name
    self.icon_pressed   = icon_pressed
    self.icon_released  = icon_released
    self.label_pressed  = icon_pressed
    self.label_released = label_released
    self.logger         = logging.getLogger(logger_id)
    self.state          = state
    self.on_press_fun   = on_press
    self.pressed        = False

  def on_press(self, page, deck_man):
    """
    Wrapper for on_press_fun that already passes key along to callback.
    """
    self.on_press_fun(self, page, deck_man)

  def __str__(self):
    return "(SDKey {})".format(self.name)
