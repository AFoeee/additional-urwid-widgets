#! /usr/bin/env python3
# -*- coding: utf-8 -*-


import enum
import random
import urwid


TYPE_ERR_MSG = "type {} was expected for {}, but found: {}."
VALUE_ERR_MSG = "unrecognized value: {}"


class KeyModifier(enum.Enum):
    NONE = ""
    SHIFT = "shift"
    META = "meta"
    CTRL = "ctrl"
    SHIFT_META = "shift meta"
    SHIFT_CTRL = "shift ctrl"
    META_CTRL = "meta ctrl"
    SHIFT_META_CTRL = "shift meta ctrl"
    
    def __repr__(self):
        return self.value
    
    # Not every combination of key modifier and key is useful.
    def prepend_to(self, key, *, separator=" "):
        if self == KeyModifier.NONE:
            return key
        else:
            return self.value + separator + key


class IndicativeListBox(urwid.WidgetWrap):
    def __init__(self, body, *, selected_position=0, on_selection_change=None, initialization_is_selection_change=False,
                 key_modifier=KeyModifier.NONE, return_unused_navigation_keystroke=True, top_align="center",
                 top_covered=("▲", None, None), top_exposed=("───", None, None), bottom_align="center",
                 bottom_covered=("▼", None, None), bottom_exposed=("───", None, None), placeholder_align="center",
                 placeholder=("Not enough space to display this widget.", None, None), highlight_off_focus=None):
        
        # If not already done, wrap each item of the body in an 'urwid.AttrMap'. That way off-focus highlighting is enabled.
        body[:] = [urwid.AttrMap(item, None) if (type(item) != urwid.AttrMap) else item
                   for item in body]
        
        # Wrap 'urwid.ListBox'.
        super().__init__(urwid.ListBox(body))
        
        # Select the specified list position, or the nearest valid one.
        nearest_valid_position = self._get_nearest_valid_position(selected_position)
        
        if nearest_valid_position is not None:
            self._w.set_focus(nearest_valid_position)
        
        # A hook which is triggered when the selection changes.
        self.on_selection_change = on_selection_change
        
        # Initialization can be seen as a special case of selection change. This is interesting in combination with the hook.
        self._initialization_is_selection_change = initialization_is_selection_change
        
        # KeyModifier changes the behavior of the list box, so that it responds only to modified keystrokes. ('up' => 'ctrl up')
        self._key_modifier = key_modifier
        
        # If the list item at the top is selected and you navigate further upwards, the keystroke is normally not swallowed by the
        # list box, but passed on. This allows other widgets to interpret it, but can result in losing the focus (which may not be
        # a desirable behavior).
        self._return_unused_navigation_keystroke = return_unused_navigation_keystroke
        
        # The bars are just 'urwid.Text' widgets.
        self._bar_top = urwid.AttrMap(urwid.Text("", top_align),
                                      None)
        
        self._bar_bottom = urwid.AttrMap(urwid.Text("", bottom_align),
                                         None)
        
        # If there is not enough space available to display the widget, a placeholder will be shown instead.
        self._placeholder = urwid.AttrMap(urwid.Filler(urwid.Text(placeholder[0], placeholder_align)),
                                          None)
        
        # During the initialization of 'urwid.AttrMap', the value can be passed as non-dict. After initializing, its value can be
        # manipulated by passing a dict. The dicts I create below will be used later to change the appearance of the widgets.
        self._top_covered_markup = top_covered[0]
        self._top_covered_focus = {None:top_covered[1]}
        self._top_covered_off_focus = {None:top_covered[2]}
        
        self._top_exposed_markup = top_exposed[0]
        self._top_exposed_focus = {None:top_exposed[1]}
        self._top_exposed_off_focus = {None:top_exposed[2]}
        
        self._bottom_covered_markup = bottom_covered[0]
        self._bottom_covered_focus = {None:bottom_covered[1]}
        self._bottom_covered_off_focus = {None:bottom_covered[2]}
        
        self._bottom_exposed_markup = bottom_exposed[0]
        self._bottom_exposed_focus = {None:bottom_exposed[1]}
        self._bottom_exposed_off_focus = {None:bottom_exposed[2]}
        
        self._placeholder_focus = {None:placeholder[1]}
        self._placeholder_off_focus = {None:placeholder[2]}
        
        # This is used to highlight the selected item when the widget does not have the focus.
        self._highlight_off_focus = {None:highlight_off_focus}
        self._last_focus_state = None
        self._original_item_attr_map = None
        
        # Is 'on_selection_change' triggered during the initialization?
        if (on_selection_change is not None) and initialization_is_selection_change:
            on_selection_change(None,
                                self.get_selected_position())
    
    def render(self, size, focus=False):
        cols, rows = size
        
        bar_top_rows = self._bar_top.rows((cols,))
        bar_bottom_rows = self._bar_bottom.rows((cols,))
        
        # It seems that there is no minimum requirement for columns. The minimum would be defined by the cursor position of the
        # list box, but this position seems to shrink if it can not be displayed.
        
        # The minimum requirement for row: rows of each bar + at least one row for the original list box.
        min_rows = bar_top_rows + bar_bottom_rows + 1
        
        # If fewer rows are available than needed, return the placeholder.
        if rows < min_rows:
            # Change the appearance of the placeholder depending on whether the widget has the focus.
            self._placeholder.set_attr_map(self._placeholder_focus
                                           if focus else self._placeholder_off_focus)
            
            return self._placeholder.render(size, focus)
        
        else:
            # The size also includes the two bars, so subtract these.
            modified_size = (cols,
                             rows - bar_top_rows - bar_bottom_rows)
            
            # Returns a list of visible ends. ('top', 'bottom', both or neither)
            visible_ends = self._w.ends_visible(modified_size)
            
            # Changes the appearance of the bar at the top depending on whether the first list item is visible and the widget has
            # the focus.
            if "top" in visible_ends:
                self._bar_top.original_widget.set_text(self._top_exposed_markup)
                self._bar_top.set_attr_map(self._top_exposed_focus
                                           if focus else self._top_exposed_off_focus)
            else:
                self._bar_top.original_widget.set_text(self._top_covered_markup)
                self._bar_top.set_attr_map(self._top_covered_focus
                                           if focus else self._top_covered_off_focus)
            
            # Changes the appearance of the bar at the bottom depending on whether the last list item is visible and the widget
            # has the focus.
            if "bottom" in visible_ends:
                self._bar_bottom.original_widget.set_text(self._bottom_exposed_markup)
                self._bar_bottom.set_attr_map(self._bottom_exposed_focus
                                              if focus else self._bottom_exposed_off_focus)
            else:
                self._bar_bottom.original_widget.set_text(self._bottom_covered_markup)
                self._bar_bottom.set_attr_map(self._bottom_covered_focus
                                              if focus else self._bottom_covered_off_focus)
            
            # The highlighting in urwid is bound to the focus. This means that the selected item is only distinguishable as long
            # as the widget has the focus. Therefore, I highlight the selected item by temporarily changing its color scheme when
            # the 'IndicativeListBox' does not have the focus.
            if focus and not self._last_focus_state and (self._original_item_attr_map is not None):
                # Resets the appearance of the selected item to its original value.
                self._w.focus.set_attr_map(self._original_item_attr_map)
                
            elif (self._highlight_off_focus is not None) \
                        and not focus \
                        and (self._last_focus_state or (self._last_focus_state is None)) \
                        and not self.body_is_empty():
                # Store the 'attr_map' of the selected item and then change it to achieve off focus highlighting.
                self._original_item_attr_map = self._w.focus.get_attr_map()
                self._w.focus.set_attr_map(self._highlight_off_focus)
            
            # Store the last focus to do / undo the off focus highlighting only if the focus has really changed and not if the
            # widget is re-rendered because for example the terminal size has changed.
            self._last_focus_state = focus
            
            # 'urwid.CanvasCombine' puts the passed canvases one above the other.
            return urwid.CanvasCombine([(self._bar_top.render((cols,)), None, False),
                                        (self._w.render(modified_size, focus), None, True),
                                        (self._bar_bottom.render((cols,)), None, False)])
    
    def keypress(self, size, key):
        cols, rows = size

        bar_top_rows = self._bar_top.rows((cols,))
        bar_bottom_rows = self._bar_bottom.rows((cols,))
        
        # It seems that there is no minimum requirement for columns. The minimum would be defined by the cursor position of the
        # list box, but this position seems to shrink if it can not be displayed.
        
        # The minimum requirement for row: rows of each bar + at least one row for the original list box.
        min_rows = bar_top_rows + bar_bottom_rows + 1
        
        # If there is not enough space to display the widget, ignore the keystroke by returning the key code.
        if rows >= min_rows:
            
            # The size also includes the two bars, so subtract these.
            modified_size = (cols,
                             rows - bar_top_rows - bar_bottom_rows)
            
            # Store the focus position before passing the input to the original list box. That way, it can be compared with the 
            # position after the input is processed. If the list box body is empty, store None.
            focus_position_before_input = self.get_selected_position()
            
            # If a 'KeyModifier' is provided (except 'NONE'), a keystroke is changed to a modified one ('up' => 'ctrl up'). This
            # prevents the original widget from responding when the arrows keys are used to navigate between widgets. That way it
            # can be used in a 'urwid.Pile' or similar.
            if key == self._key_modifier.prepend_to("up"):
                key = self._pass_to_original_widget(modified_size, "up")
                
            elif key == self._key_modifier.prepend_to("down"):
                key = self._pass_to_original_widget(modified_size, "down")
                
            elif key == self._key_modifier.prepend_to("page up"):
                key = self._pass_to_original_widget(modified_size, "page up")
                
            elif key == self._key_modifier.prepend_to("page down"):
                key = self._pass_to_original_widget(modified_size, "page down")
                
            elif key == self._key_modifier.prepend_to("home"):
                # Check if the first list item is already selected.
                if (focus_position_before_input is not None) and (focus_position_before_input != 0):
                    self.select_first_item()
                    key = None
                elif not self._return_unused_navigation_keystroke:
                    key = None
                    
            elif key == self._key_modifier.prepend_to("end"):
                # Check if the last list item is already selected.
                if (focus_position_before_input is not None) and (focus_position_before_input != self.rearmost_position()):
                    self.select_last_item()
                    key = None
                elif not self._return_unused_navigation_keystroke:
                    key = None
            
            focus_position_after_input = self.get_selected_position()
            
            # If the focus position has changed, execute the hook (if existing).
            if (self.on_selection_change is not None) and (focus_position_before_input != focus_position_after_input):
                self.on_selection_change(focus_position_before_input,
                                         focus_position_after_input)
            
        return key
    
    # Pass the keystroke to the original widget. If it is not used, evaluate the corresponding variable to decide if it gets
    # swallowed or not.
    def _pass_to_original_widget(self, size, key):
        result = self._w.keypress(size, key)
        return result if self._return_unused_navigation_keystroke else None
    
    def get_body(self):
        return self._w.body
    
    def body_length(self):
        return len(self.get_body())
    
    def rearmost_position(self):
        return self.body_length() - 1           # last valid index
    
    def body_is_empty(self):
        return self.body_length() == 0
    
    def position_is_valid(self, position):
        return (position >= 0) and (position < self.body_length())
    
    # If the passed position is valid, it is returned. Otherwise, the nearest valid position is returned. This ensures that
    # invalid positions do not result in an error.
    def _get_nearest_valid_position(self, position):
        if self.body_is_empty():
            return None
        
        pos_type = type(position)
        
        if pos_type == int:
            if self.position_is_valid(position):
                return position
            
            elif position < 0:
                return 0
            
            else:
                return self.rearmost_position()
            
        elif pos_type == str:
            if position == "last":
                return self.rearmost_position()
            
            elif position == "middle":
                return self.body_length() // 2
            
            elif position == "random":
                return random.randint(0,
                                      self.rearmost_position())
                
            else:
                raise ValueError(VALUE_ERR_MSG.format(position))
            
        else:
            raise TypeError(TYPE_ERR_MSG.format("<class 'int'> or <class 'str'>",
                                                "'position'",
                                                pos_type))
    
    def get_item(self, position):
        if self.position_is_valid(position):
            body = self.get_body()
            return body[position]
        else:
            return None
    
    def get_first_item(self):
        return self.get_item(0)
    
    def get_last_item(self):
        return self.get_item(self.rearmost_position())
    
    def get_selected_item(self):
        return self._w.focus
    
    def get_selected_position(self):
        return self._w.focus_position if not self.body_is_empty() else None
    
    def first_item_is_selected(self):
        return self.get_selected_position() == 0
    
    def last_item_is_selected(self):
        return self.get_selected_position() == self.rearmost_position()
    
    def _reset_highlighting(self):
        if not self._last_focus_state and (self._original_item_attr_map is not None):
            # Resets the appearance of the selected item to its original value, if off focus highlighting is active.
            self._w.focus.set_attr_map(self._original_item_attr_map)
        
        # The next time the widget is rendered, the highlighting is redone.
        self._original_item_attr_map = None
        self._last_focus_state = None
    
    def set_body(self, body, *, alternative_position=None):
        focus_position_before_change = self.get_selected_position()
        
        self._reset_highlighting()
        
        # Wrap each item in an 'urwid.AttrMap', if not already done.
        self._w.body[:] = [urwid.AttrMap(item, None) if (type(item) != urwid.AttrMap) else item
                           for item in body]
        
        # Normally it is tried to hold the focus position. If this is not desired, a position can be passed.
        if alternative_position is not None:
            nearest_valid_position = self._get_nearest_valid_position(alternative_position)
            
            if nearest_valid_position is not None:
                # Because the widget has been re-rendered, the off focus highlighted item must be restored to its original state.
                self._reset_highlighting()
                
                self._w.set_focus(nearest_valid_position)
        
        # If an initialization is considered a selection change, execute the hook (if existing).
        if (self.on_selection_change is not None) and self._initialization_is_selection_change:
            self.on_selection_change(focus_position_before_change,
                                     self.get_selected_position())
    
    def select_item(self, position):
        focus_position_before_change = self.get_selected_position()
        
        nearest_valid_position = self._get_nearest_valid_position(position)
        
        # Focus the new position, if possible and not already focused.
        if (nearest_valid_position is not None) and (nearest_valid_position != focus_position_before_change):
            self._reset_highlighting()
            
            self._w.set_focus(nearest_valid_position)
            
            # Execute the hook (if existing).
            if (self.on_selection_change is not None):
                self.on_selection_change(focus_position_before_change,
                                         nearest_valid_position)
    
    def select_first_item(self):
        self.select_item(0)
        
    def select_last_item(self):
        self.select_item(self.rearmost_position())


# Demonstration
if __name__ == "__main__":
    
    ENTRIES = [c for c in "abcdefghijklmnopqrstuvwxyz"]
    
    PALETTE = [("default",                   "",                 "black"),
               ("item_in_focus",             "black",            "light cyan",   "standout"),
               ("ilb_barActive_focus",       "dark cyan",        "light gray"),
               ("ilb_barActive_off_focus",   "light gray",       "dark gray"),
               ("ilb_barInactive_focus",     "light cyan",       "dark gray"),
               ("ilb_barInactive_off_focus", "black",            "dark gray"),
               ("ilb_placeholder_focus",     "white,bold",       "dark red"),
               ("ilb_placeholder_off_focus", "white",            "dark red"),
               ("ilb_highlight_off_focus",   "black",            "dark cyan"),
               ("text_highlight",            "yellow,bold",      ""),
               ("text_bold",                 "bold",             ""),
               ("text_challenge",            "light green,bold", ""),
               ("text_esc",                  "light red,bold",   "")]
    
    
    class TestApp(object):
        def __init__(self):
            # Navigation instructions
            text_arrow_keys = urwid.Text([("text_highlight", "↑"),
                                          " or ",
                                          ("text_highlight", "↓"),
                                          " to move one line."])
            
            text_pages = urwid.Text([("text_highlight", "page up"),
                                     " or ",
                                     ("text_highlight", "page down"),
                                     " to move one list box length."])
            
            text_home_end = urwid.Text([("text_highlight", "home"),
                                        " or ",
                                        ("text_highlight", "end"),
                                        " to jump to the corresponding list end."])
            
            # Columns
            # Left
            left_heading = "default:"
            
            left_column = urwid.Pile([urwid.AttrMap(urwid.Text(left_heading, align="center"),
                                                    "text_bold"),
                                      
                                      urwid.Text("▔" * len(left_heading), align="center"),
                                      
                                      urwid.Text("The default is impractical in a pile, because you also navigate with the arrow"
                                                 + " keys between the widgets."),
                                      
                                      urwid.Divider(" "),
                                      
                                      urwid.Button("some button"),
                                      
                                      # Left list box, wrapped in a urwid.BoxAdapter to limit the extent.
                                      urwid.BoxAdapter(IndicativeListBox([urwid.Button(entry)
                                                                          for entry in ENTRIES]),
                                                       6),
                                      
                                      urwid.Button("another button")])
            
            # Right
            right_heading = "with additional parameters:"
            
            right_column = urwid.Pile([urwid.AttrMap(urwid.Text(right_heading, align="center"),
                                                     "text_bold"),
                                      
                                       urwid.Text("▔" * len(right_heading), align="center"),
                                      
                                       urwid.Text(["This list box responds only if you additionally press ",
                                                   ("text_highlight", "ctrl"),
                                                   "."]),
                                      
                                        urwid.Divider(" "),
                                      
                                        urwid.Button("some button"),
                                      
                                        # Right list box, wrapped in a urwid.BoxAdapter to limit the extent.
                                        urwid.BoxAdapter(IndicativeListBox([urwid.AttrMap(urwid.Button(entry),
                                                                                          "default",
                                                                                          "item_in_focus") for entry in ENTRIES],
                                                                           key_modifier=KeyModifier.CTRL,
                                                                           return_unused_navigation_keystroke=False,
                                                                           top_covered=("ᐃ",
                                                                                        "ilb_barActive_focus",
                                                                                        "ilb_barActive_off_focus"),
                                                                           top_exposed=("───",
                                                                                        "ilb_barInactive_focus",
                                                                                        "ilb_barInactive_off_focus"), 
                                                                           bottom_covered=("ᐁ",
                                                                                           "ilb_barActive_focus",
                                                                                           "ilb_barActive_off_focus"), 
                                                                           bottom_exposed=("───",
                                                                                           "ilb_barInactive_focus",
                                                                                           "ilb_barInactive_off_focus"),
                                                                           placeholder=("Something went wrong!",
                                                                                        "ilb_placeholder_focus",
                                                                                        "ilb_placeholder_off_focus"),
                                                                           highlight_off_focus="ilb_highlight_off_focus"),
                                                         6),
                                        
                                        urwid.Button("another button")])
            
            columns = urwid.Columns([left_column, right_column],
                                    dividechars=5)
            
            # Emphasize why KeyModifier is needed.
            text_challenge = urwid.AttrMap(urwid.Text("Try to get to the button at the top/bottom in each column.", align="center"),
                                           "text_challenge")
            
            # Termination instructions
            text_esc = urwid.Text([("text_esc", "Q"),
                                   " or ",
                                   ("text_esc", "Esc"),
                                   " to quit."])
            
            pile = urwid.Pile([text_arrow_keys,
                               text_pages,
                               text_home_end,
                               
                               urwid.Divider("─"),
                               urwid.Divider(" "),
                               
                               columns,
                               
                               urwid.Divider(" "),
                               
                               text_challenge,
                               
                               urwid.Divider(" "),
                               urwid.Divider("─"),
                               
                               text_esc])
            
            main_widget = urwid.Filler(pile, "top")
            
            self.loop = urwid.MainLoop(main_widget,
                                       PALETTE,
                                       unhandled_input=self.keypress)
        
        def keypress(self, key):
            if key in ('q', 'Q', 'esc'):
                self.exit()
    
        def start(self):
            self.loop.run()
            
        def exit(self):
            raise urwid.ExitMainLoop()
    
    
    test = TestApp()
    test.start()
    
