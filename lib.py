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
    self.logger_id      = logger_id
    self.state          = state
    self.on_press_fun   = on_press
    self.pressed        = False
    self.logger.info("Key {} created.".format(str(self)))
    delf.logger.debug(json.dumps({
        "name": self.name,
        "icon": {
          "pressed": self.icon_pressed,
          "released": self.icon_released
        },
        "label": {
          "pressed": self.label_pressed,
          "released": self.label_released
        },
        "logger": self.logger_id
      }))

  def on_press(self, page, deck_man):
    """
    Wrapper for on_press_fun that already passes key along to callback.
    """
    self.logger.info("Key {} was {}.".format(str(self),
      "pressed" if self.pressed else "releassed"))
    self.on_press_fun(self, page, deck_man)

  def __str__(self):
    return "(SDKey {})".format(self.name)


class Page:
  """
  This class represents a page of icons on a Streamdeck.
  """

  def __init__(self, name, dimensions, logger_id=STANDARD_LOGGER_ID):
    self.deck_keys = [None] * (dimensions[0] * dimensions[1])
    self.logger_id = logger_id
    self.logger    = logging.getLogger(logger_id)


  def __str__(self):
    keys = list(map(lambda x: str(x), self.deck_keys))
    return json.dumps({"name": self.__name, "type": self.__deck_type, "data": keys})

  def get_key_style(self, key):
    """
    Returns styling information for given key.
    """
    key = self.deck_keys[key]

    return {
      "name":  key.name,
      "icon":  key.icon_pressed  if key.pressed else key.icon_released,
      "label": key.label_pressed if key.pressed else key.pressed_released
    }

  def on_press(self, key, deck_man):
    """
    Wrapper function that calls callback of given key.
    """
    if self.deck_keys[key] is not None:
      self.deck_keys[key].on_press(self, deck_man)
    else:
      self.logger.warning("Key you try to access ({}, {}) is not defined."
        .format(key // deck_man.key_layout()[1], key % deck_man.key_layout()[1]))
