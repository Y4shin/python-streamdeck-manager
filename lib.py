import importlib.util
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

STANDARD_FONT = "Roboto-Regular.ttf"
"""
Standard font for key images.
"""

STANDARD_FONT_SIZE = 14
"""
Standard font size for key images.
"""

STANDARD_BRIGHTNESS = 50
"""
Standard streamdeck brightness.
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
    self.label_pressed  = label_pressed
    self.label_released = label_released
    self.logger         = logging.getLogger(logger_id)
    self.logger_id      = logger_id
    self.state          = state
    self.on_press_fun   = on_press
    self.pressed        = False
    self.logger.info("Key {} created.".format(str(self)))
    self.logger.debug(json.dumps({
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

  def dump(self):
    return {
      "name": self.name,
      "label": {
        "pressed":  self.label_pressed,
        "released": self.label_released
      },
      "icon": {
        "pressed":  self.icon_pressed,
        "released": self.icon_released
      },
      "logger": self.logger_id,
      "pressed": self.pressed,
      "state": self.state
    }

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
    self.name      = name


  def __str__(self):
    keys = list(map(lambda x: str(x), self.deck_keys))
    return json.dumps({"name": self.name, "data": keys})

  def get_key_style(self, key):
    """
    Returns styling information for given key.
    """
    key = self.deck_keys[key]
    if key is None:
      return {
        "name":  None,
        "icon":  None,
        "label": None
      }
    else:
      return {
        "name":  key.name,
        "icon":  key.icon_pressed  if key.pressed else key.icon_released,
        "label": key.label_pressed if key.pressed else key.label_released
      }

  def on_press(self, key, deck_man):
    """
    Wrapper function that calls callback of given key.
    """
    if self.deck_keys[key] is not None:
      self.deck_keys[key].on_press(self, deck_man)
    else:
      self.logger.warning("Key you try to access ({}, {}) is not defined."
        .format(key // deck_man.key_layout()[1],
                key % deck_man.key_layout()[1]))

class Manager:

  def __key_change_callback(self, deck, key, state):
    """
    Callback function that is passed to streamdeck. calls on_press function of
    key.
    """
    if deck == self.deck:
      dimensions = self.deck.key_layout()
      row = key // dimensions[1]
      col = key % dimensions[1]
      self.logger.debug("Key {}:{} {}.".format(
        self.page_stash[self.current_page].deck_keys[key].name,
        self.page_stash[self.current_page].name,
        ("has been pressed" if state else "has been released")))
      self.logger.debug("Key = {}".format(
        json.dumps(self.page_stash[self.current_page].deck_keys[key].dump())))
      self.page_stash[self.current_page].deck_keys[key].pressed = state
      self.page_stash[self.current_page].on_press(key, self)
      self.update_keys()


  def update_keys(self):
    """
    Update pictures on all keys.
    """
    dimensions = self.deck.key_layout()
    n_keys = dimensions[0] * dimensions[1]
    self.logger.debug("Updating keys")
    for key in list(range(0, n_keys)):
      self.__update_key_image(key)


  def __update_key_image(self, key):
    """
    Updates picture on one key.
    """
    dimensions = self.deck.key_layout()
    n_keys = dimensions[0] * dimensions[1]
    if key < n_keys:
      if self.page_stash[self.current_page].deck_keys[key] is not None:
        key_style = self.page_stash[self.current_page].get_key_style(key)
        icon_path = os.path.join(self.config_path, key_style["icon"])
        if os.path.isfile(icon_path):
          image = self.__render_key_image(icon_path,
                                          key_style["label"])
          self.deck.set_key_image(key, image)
        else:
          self.logger.critical("Image {} does not exist!, aborting!"
            .format(key_style["icon"]))
          raise IOError("Image {} does not exist!.".format(icon_path))
      else:
        image = self.__render_key_image(None, None)
        self.deck.set_key_image(key, image)
    else:
      raise ValueError("Key dimensions {} outside of board {}."
        .format((key // dimensions[1], key % dimensions[0]), dimensions))

  def __render_key_image(self,
                         icon_file,
                         label_text,
                         font_size=None):
    """
    Renders image to put onto a key.
    """
    image = PILHelper.create_image(self.deck)

    if icon_file is not None:
      icon = Image.open(os.path.join(self.config_path, icon_file)).convert('RGBA')
      icon.thumbnail((image.width, image.height - 20), Image.LANCZOS)
      icon_pos = ((image.width - icon.width) // 2, 0)
      image.paste(icon, icon_pos, icon)

    if label_text is not None:
      draw = ImageDraw.Draw(image)
      font = ImageFont.truetype(self.font,
        font_size if font_size is not None else self.font_size)
      label_w, label_h = draw.textsize(label_text, font=font)
      label_pos = ((image.width - label_w) // 2, image.height - 20)
      draw.text(label_pos, text=label_text, font=font, fill='white')

    return PILHelper.to_native_format(self.deck, image)



  def __init__(self, deck, font=STANDARD_FONT, font_size=STANDARD_FONT_SIZE, logger=STANDARD_LOGGER_ID, brightness=STANDARD_BRIGHTNESS, config_path=os.path.join(os.environ.get('XDG_CONFIG_HOME'), 'streamdeck_manager')):
    self.config_path  = config_path
    self.deck         = deck
    self.font         = font
    self.logger_id    = logger
    self.logger       = logging.getLogger(self.logger_id)
    self.page_stash   = {"main": Page("Default Page", deck.key_layout(), logger_id=self.logger_id)}
    self.current_page = "main"
    self.brightness   = brightness
    self.font_size    = font_size
    self.deck.open()
    self.deck.reset()
    self.deck.set_brightness(self.brightness)
    self.update_keys()
    self.deck.set_key_callback(self.__key_change_callback)
