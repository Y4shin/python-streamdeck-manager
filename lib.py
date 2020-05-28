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


class Parser:

  def __folder_change_callback(self, key, page, deck):
    """
    Callback for changing folders.
    """
    key.logger.info(str(page))
    if key.pressed:
      key.logger.info("Changing folder to {} on release.".format(key.state))
    else:
      deck.current_page = key.state
      key.logger.info("Changed folder to {}.".format(key.state))

  def __empty_callback(self, key, page, deck):
    """
    Callback for non-functional key.
    """
    key.logger.info("Empty function.")

  def __function_callback(self, key, page, deck):
    spec = importlib.util.spec_from_file_location("fun_lib", os.path.join(self.config_path, self.callback_source))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    callback = getattr(mod, key.state["function_name"])
    callback(key, page, deck, parser=self)


  def __get_callback(self, key):
    """
    Returns the appropriate callback function and state object for giben key.
    """
    if key["type"] == "folder":
      return (self.__folder_change_callback, key["folder"]["name"])
    elif key["type"] == "empty":
      return (self.__empty_callback, None)
    elif key["type"] == "function":
      return (self.__function_callback, key["function_config"])

  def __populate_pages(self, page, parent=None):
    """
    Takes dict of page (read from configuration file) and creates the according
    data structures
    """
    print("populating")
    self.logger.debug("Populating page {}".format(page["name"]))
    self.deck_manager.page_stash[page["name"]] =\
      Page(page["name"], self.deck_manager.deck.key_layout(), logger_id=self.deck_manager.logger_id)
    dim = self.deck_manager.deck.key_layout()
    n_keys = dim[0] * dim[1]
    if parent is not None:

      self.deck_manager.page_stash[page["name"]].deck_keys[0] =\
        Key(name = page["name"] + str(0),
            icon_pressed = self.folder_up_img,
            icon_released = self.folder_up_img,
            on_press = self.__folder_change_callback,
            label_pressed = "up",
            label_released = "up",
            logger_id = self.deck_manager.logger_id,
            state = parent)
    for i in range(len(page["keys"])):
      index = i if parent is None else i + 1
      if index < n_keys:
        json_key = page["keys"][i]
        name = json_key["name"]
        if json_key["type"] == "folder":
          self.__populate_pages(json_key["folder"], parent=page["name"])
          img_on = self.folder_img
          img_off = self.folder_img
        elif "img" in list(json_key.keys()):
          img_on = json_key["img"]
          img_off = json_key["img"]
        else:
          if "img_on" in list(json_key.keys()):
            img_on = json_key["img_on"]
          else:
            img_on = self.default_img
          if "img_off" in list(json_key.keys()):
            img_off = json_key["img_off"]
          else:
            img_off = self.default_img
        if "label" in list(json_key.keys()):
          label_on = json_key["label"]
          label_off = json_key["label"]
        else:
          if "label_on" in list(json_key.keys()):
            label_on = json_key["label_on"]
          else:
            label_on = self.default_label
          if "label_off" in list(json_key.keys()):
            label_off = json_key["label_off"]
          else:
            label_off = self.default_label
        on_press, state = self.__get_callback(json_key)
        #(self, name="undefined",
        #               icon_pressed=STANDARD_ICON,
        #               icon_released=STANDARD_ICON,
        #               label_pressed=STANDARD_LABEL,
        #               label_released=STANDARD_LABEL,
        #               logger_id=STANDARD_LOGGER_ID,
        #               state=None,
        #               on_press=EMPTY_ON_PRESS):)
        self.deck_manager.page_stash[page["name"]].deck_keys[index] =\
          Key(name = name,
              icon_pressed = img_on,
              on_press = on_press,
              icon_released = img_off,
              label_pressed = label_on,
              label_released = label_off,
              logger_id = self.deck_manager.logger_id,
              state = state)
      else:
        self.logger.error("Key {} is outside of board range of {}."\
            .format(i, n_keys))

  def __init__(self, filename, deck, logger_id=STANDARD_LOGGER_ID, config_path=os.path.join(os.environ.get('XDG_CONFIG_HOME'), 'streamdeck_manager'), callback_source=None):
    self.config_path  = config_path
    self.deck_manager = Manager(deck, config_path=self.config_path)
    self.logger       = logging.getLogger(logger_id if logger_id is not None else\
                                                                 DEF_LOGGER)
    self.callback_source=callback_source
    print(os.path.join(config_path, filename))
    with open(os.path.join(config_path, filename)) as json_file:
      json_obj = json.load(json_file)
      keys = list(json_obj.keys())
      print(keys)
      if set(["page", "folder_up_img", "folder_img"]).issubset(set(keys)):
        if "default_img" in keys:
          self.default_img = json_obj["default_keys"]
        else:
          self.default_img = STANDARD_ICON
        if "default_label" in keys:
          self.default_label = json_obj["default_label"]
        else:
          self.default_label = STANDARD_LABEL
        self.folder_up_img = json_obj["folder_up_img"]
        self.folder_img = json_obj["folder_img"]
        json_obj["page"]["name"] = "main"
        print('keklmao')
        self.__populate_pages(json_obj["page"])
        self.deck_manager.current_page = json_obj["page"]["name"]
        self.deck_manager.update_keys()
