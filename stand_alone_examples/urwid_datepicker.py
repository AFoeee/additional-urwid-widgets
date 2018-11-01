#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import calendar
import datetime
import enum
import random
import sys
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


# This class was posted by user 'elias' on stackoverflow.com: 
# https://stackoverflow.com/questions/52106244/how-do-you-combine-multiple-tui-forms-to-write-more-complex-applications#answer-52174629
class SelectableRow(urwid.WidgetWrap):
    def __init__(self, contents, align="left", on_select=None):
        # A list-like object, where each element represents the value of a column.
        self.contents = contents
        
        self._columns = urwid.Columns([urwid.Text(c, align=align) 
                                       for c in contents])
        
        # Wrap 'urwid.Columns'.
        super().__init__(self._columns)
        
        # A hook that gets executed when (the key modifier +) 'enter' is pressed while the widget has the focus.
        self.on_select = on_select
    
    def __repr__(self):
        return "%s(contents=%r)" % (self.__class__.__name__, self.contents)
    
    def selectable(self):
        return True
    
    def keypress(self, size, key):
        if (key == "enter") and (self.on_select is not None):
            self.on_select(self)
            key = None
            
        return key
    
    def set_contents(self, contents):
        # update the list record inplace...
        self.contents[:] = contents
        
        # ... and update the displayed items
        for t, (w, _) in zip(contents, self._columns.contents):
            w.set_text(t)


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


class IntegerPicker(urwid.WidgetWrap):
    def __init__(self, value, *, minimum=(-sys.maxsize - 1), maximum=sys.maxsize, step_length=1, jump_length=100, 
                 on_selection_change=None, initialization_is_selection_change=False, key_modifier=KeyModifier.NONE, 
                 ascending=True, return_unused_navigation_keystroke=True, display_syntax="{}", display_align="center", 
                 display=(None, None), top_align="center", top_covered=("▲", None, None), top_exposed=("───", None, None),
                 bottom_align="center", bottom_covered=("▼", None, None), bottom_exposed=("───", None, None)):
        
        assert (minimum <= maximum), "'minimum' must be less than or equal to 'maximum'."
        
        assert (minimum <= value <= maximum), "'minimum <= value <= maximum' must be True."
        
        self._value = value
        
        self._minimum = minimum
        self._maximum = maximum
    
        # Specifies how far to move in the respective direction when the keys 'up' or 'down' are pressed.
        self._step_length = step_length
        
        # Specifies how far to jump in the respective direction when the keys 'page up' or 'page down' are pressed.
        self._jump_length = jump_length
        
        # A hook which is triggered when the value changes.
        self.on_selection_change = on_selection_change
        
        # KeyModifier changes the behavior, so that the widget responds only to modified keystrokes. ('up' => 'ctrl up')
        self._key_modifier = key_modifier
        
        # Specifies whether an upward key stroke represents a decrease or an increase of the value.
        self._ascending = ascending
        
        # If the minimum has been reached and an attempt is made to select an even smaller value, the keystroke is not swallowed 
        # by the widget, but passed on. This allows other widgets to interpret it, but can result in losing the focus (which may
        # not be a desirable behavior).
        self._return_unused_navigation_keystroke = return_unused_navigation_keystroke
        
        # Format the number before displaying it. That way it is easier to read.
        self._display_syntax = display_syntax
        
        # The current value is displayed via this widget.
        self.display = SelectableRow([display_syntax.format(value)],
                                     align=display_align)
        
        display_attr = urwid.AttrMap(self.display,
                                     display[1],
                                     display[0])
        
        # The bars are just 'urwid.Text' widgets.
        self._bar_top = urwid.AttrMap(urwid.Text("", top_align),
                                      None)
        
        self._bar_bottom = urwid.AttrMap(urwid.Text("", bottom_align),
                                         None)
        
        # wrap 'urwid.Pile'
        super().__init__(urwid.Pile([self._bar_top,
                                     display_attr,
                                     self._bar_bottom]))
        
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
        
        # Is 'on_selection_change' triggered during the initialization?
        if (on_selection_change is not None) and initialization_is_selection_change:
            on_selection_change(None, value)
    
    def render(self, size, focus=False):
        # Changes the appearance of the bar at the top depending on whether the upper limit is reached.
        if self._value == (self._minimum if self._ascending else self._maximum):
            self._bar_top.original_widget.set_text(self._top_exposed_markup)
            self._bar_top.set_attr_map(self._top_exposed_focus
                                       if focus else self._top_exposed_off_focus)
        else:
            self._bar_top.original_widget.set_text(self._top_covered_markup)
            self._bar_top.set_attr_map(self._top_covered_focus
                                       if focus else self._top_covered_off_focus)
        
        # Changes the appearance of the bar at the bottom depending on whether the lower limit is reached.
        if self._value == (self._maximum if self._ascending else self._minimum):
            self._bar_bottom.original_widget.set_text(self._bottom_exposed_markup)
            self._bar_bottom.set_attr_map(self._bottom_exposed_focus
                                          if focus else self._bottom_exposed_off_focus)
        else:
            self._bar_bottom.original_widget.set_text(self._bottom_covered_markup)
            self._bar_bottom.set_attr_map(self._bottom_covered_focus
                                          if focus else self._bottom_covered_off_focus)
            
        return super().render(size, focus)
    
    def keypress(self, size, key):
        # If a 'KeyModifier' is provided (except 'NONE'), a keystroke is changed to a modified one ('up' => 'ctrl up'). This
        # prevents the widget from responding when the arrows keys are used to navigate between widgets. That way it can be used
        # in a 'urwid.Pile' or similar.
        if key == self._key_modifier.prepend_to("up"):
            successful = self._change_value(-self._step_length)
        
        elif key == self._key_modifier.prepend_to("down"):
            successful = self._change_value(self._step_length)
        
        elif key == self._key_modifier.prepend_to("page up"):
            successful = self._change_value(-self._jump_length)
        
        elif key == self._key_modifier.prepend_to("page down"):
            successful = self._change_value(self._jump_length)
        
        elif key == self._key_modifier.prepend_to("home"):
            successful = self._change_value(float("-inf"))
        
        elif key == self._key_modifier.prepend_to("end"):
            successful = self._change_value(float("inf"))
        
        else:
            successful = False
        
        return key if not successful else None
    
    # This method tries to change the value depending on the desired arrangement and returns True if this change was successful.
    def _change_value(self, summand):
        value_before_input = self._value
        
        if self._ascending:
            new_value = self._value + summand
            
            if summand < 0:
                # If the corresponding limit has already been reached, then determine whether the unused keystroke should be
                # returned or swallowed.
                if self._value == self._minimum:
                    return not self._return_unused_navigation_keystroke
                
                # If the new value stays within the permitted range, use it.
                elif new_value > self._minimum:
                    self._value = new_value
                
                # The permitted range would be exceeded, so the limit is set instead.
                else:
                    self._value = self._minimum
            
            elif summand > 0:
                if self._value == self._maximum:
                    return not self._return_unused_navigation_keystroke
                
                elif new_value < self._maximum:
                    self._value = new_value
                
                else:
                    self._value = self._maximum
        else:
            new_value = self._value - summand
            
            if summand < 0:
                if self._value == self._maximum:
                    return not self._return_unused_navigation_keystroke
                
                elif new_value < self._maximum:
                    self._value = new_value
                
                else:
                    self._value = self._maximum
            
            elif summand > 0:
                if self._value == self._minimum:
                    return not self._return_unused_navigation_keystroke
                
                elif new_value > self._minimum:
                    self._value = new_value
                
                else:
                    self._value = self._minimum
        
        # Update the displayed value.
        self.display.set_contents([self._display_syntax.format(self._value)])
        
        # If the value has changed, execute the hook (if existing).
        if (self.on_selection_change is not None) and (value_before_input != self._value):
            self.on_selection_change(value_before_input, self._value)
        
        return True
    
    def get_value(self):
        return self._value
    
    def set_value(self, value):
        if value != self._value:
            
            if not (self._minimum <= value <= self._maximum):
                raise ValueError("'minimum <= value <= maximum' must be True.")
            
            value_before_change = self._value
            self._value = value
            
            # Update the displayed value.
            self.display.set_contents([self._display_syntax.format(self._value)])
            
            # Execute the hook (if existing).
            if (self.on_selection_change is not None):
                self.on_selection_change(value_before_change, self._value)
        
    def set_to_minimum(self):
        self.set_value(self._minimum)
    
    def set_to_maximum(self):
        self.set_value(self._maximum)
        
    def minimum_is_selected(self):
        return self._value == self._minimum
    
    def maximum_is_selected(self):
        return self._value == self._maximum


class DatePicker(urwid.WidgetWrap):
    # Specifies the order in which the individual pickers are arranged.
    class Arrangement(enum.Enum):
        DAY_MONTH_YEAR = 1
        MONTH_DAY_YEAR = 2
        YEAR_MONTH_DAY = 3
    
    # These values are interpreted during the creation of the list items for the day picker.
    class DayFormat(enum.Enum):
        DAY_OF_MONTH = 1
        DAY_OF_MONTH_TWO_DIGIT = 2
        WEEKDAY = 3
        
    # Specifies which dates are selectable.
    class Range(enum.Enum):
        ALL = 1
        ONLY_PAST = 2
        ONLY_FUTURE = 3
    
    def __init__(self, year, month, day, *, date_range=Range.ALL, month_names=calendar.month_name, day_names=calendar.day_abbr,
                 day_format=(DayFormat.WEEKDAY, DayFormat.DAY_OF_MONTH), arrangement=Arrangement.DAY_MONTH_YEAR, key_modifier=KeyModifier.CTRL,
                 return_unused_navigation_keystroke=False, year_jump_length=50, min_width_each_picker=9, width_day_picker=("weight", 1),
                 width_month_picker=("weight", 1), width_year_picker=("weight", 1), space_between=2, year_align="center", month_align="center",
                 day_align="center", top_align="center", top_covered=("▲", None, None), top_exposed=("───", None, None), bottom_align="center",
                 bottom_covered=("▼", None, None), bottom_exposed=("───", None, None), highlight=(None, None)):
        
        assert (type(date_range) == DatePicker.Range), TYPE_ERR_MSG.format("<enum 'DatePicker.Range'>",
                                                                           "'date_range'",
                                                                           type(date_range))
        
        for df in day_format:
            assert (type(df) == DatePicker.DayFormat), TYPE_ERR_MSG.format("<enum 'DatePicker.DayFormat'>",
                                                                           "all elements of 'day_format'",
                                                                           type(df))
        
        assert (type(arrangement) == DatePicker.Arrangement), TYPE_ERR_MSG.format("<enum 'DatePicker.Arrangement'>",
                                                                                  "'arrangement'",
                                                                                  type(arrangement))
        
        # Invalid dates throw a ValueError.
        datetime.date(year, month, day)
        
        # Relevant for 'DatePicker.Range.ONLY_PAST' and 'DatePicker.Range.ONLY_FUTURE' to limit the respective choices.
        self._initial_year = year
        self._initial_month = month
        self._initial_day = day
        
        # The date pool can be limited, so that only past or future dates are selectable. The initial date is included in the
        # pool and represents the starting point.
        self._date_range = date_range
        
        # The presentation of months and weekdays can be changed by passing alternative values (e.g. abbreviations or numerical
        # representations).
        self._month_names = month_names
        self._day_names = day_names
        
        # Since there are different needs regarding the appearance of the date picker, an iterable can be passed, which allows a
        # customization of the presentation.
        self._day_format = day_format
        
        # Specifies the text alignment of the individual pickers. The year alignment is passed directly to the year picker.
        self._month_align = month_align
        self._day_align = day_align
        
        # The default style of a list entry. Since only one list entry will be visible at a time, it defines the appearance of the
        # widget's display part.
        self._item_attr = (None, highlight[0])
        
        # A full list of months. (From 'January' to 'December'.)
        self._month_list = self._generate_months()
        
        # Set the respective values depending on the date range.
        year_minimum = datetime.MINYEAR
        year_maximum = datetime.MAXYEAR
        
        month_position = month - 1
        day_position = day - 1
        
        if date_range == DatePicker.Range.ALL:
            initial_month_list = self._month_list
            
        elif date_range == DatePicker.Range.ONLY_PAST:
            year_maximum = year
            
            # The months of the very last year may be shorten.
            self._shortened_month_list = self._generate_months(end=month)
            initial_month_list = self._shortened_month_list
            
        elif date_range == DatePicker.Range.ONLY_FUTURE:
            year_minimum = year
            
            # The months of the very first year may be shorten.
            self._shortened_month_list = self._generate_months(start=month)
            initial_month_list = self._shortened_month_list
            
            # The list may not start at 1 but some other day of month, therefore use the first list item.
            month_position = 0
            day_position = 0
            
        else:
            raise ValueError(VALUE_ERR_MSG.format(date_range))
        
        # Create pickers.
        self._year_picker = IntegerPicker(year,
                                          minimum=year_minimum,
                                          maximum=year_maximum,
                                          jump_length=year_jump_length,
                                          on_selection_change=self._year_has_changed,
                                          key_modifier=key_modifier,
                                          return_unused_navigation_keystroke=return_unused_navigation_keystroke,
                                          display_align=year_align,
                                          display=highlight,
                                          top_align=top_align,
                                          top_covered=top_covered,
                                          top_exposed=top_exposed,
                                          bottom_align=bottom_align,
                                          bottom_covered=bottom_covered,
                                          bottom_exposed=bottom_exposed)
        
        self._month_picker = IndicativeListBox(initial_month_list,
                                               selected_position=month_position,
                                               on_selection_change=self._month_has_changed,
                                               key_modifier=key_modifier,
                                               return_unused_navigation_keystroke=return_unused_navigation_keystroke,
                                               top_align=top_align,
                                               top_covered=top_covered,
                                               top_exposed=top_exposed,
                                               bottom_align=bottom_align,
                                               bottom_covered=bottom_covered,
                                               bottom_exposed=bottom_exposed,
                                               highlight_off_focus=highlight[1])
        
        self._day_picker = IndicativeListBox(self._generate_days(year, month),
                                             selected_position=day_position,
                                             key_modifier=key_modifier,
                                             return_unused_navigation_keystroke=return_unused_navigation_keystroke,
                                             top_align=top_align,
                                             top_covered=top_covered,
                                             top_exposed=top_exposed,
                                             bottom_align=bottom_align,
                                             bottom_covered=bottom_covered,
                                             bottom_exposed=bottom_exposed,
                                             highlight_off_focus=highlight[1])
        
        # To mimic a selection widget, IndicativeListbox is wrapped in a 'urwid.BoxAdapter'. Since two rows are used for the bars,
        # size 3 makes exactly one list item visible.
        boxed_month_picker = urwid.BoxAdapter(self._month_picker, 3)
        boxed_day_picker = urwid.BoxAdapter(self._day_picker, 3)
        
        # Combine the pickers with their respective width. This is interpreted by the 'urwid.Columns' widget.
        col_year_picker = (*width_year_picker, self._year_picker)
        col_month_picker = (*width_month_picker, boxed_month_picker)
        col_day_picker = (*width_day_picker, boxed_day_picker)
        
        # Depending on the value of 'arrangement', the individual pickers are arranged differently.
        if arrangement == DatePicker.Arrangement.DAY_MONTH_YEAR:
            cols = [col_day_picker, col_month_picker, col_year_picker]
        
        elif arrangement == DatePicker.Arrangement.MONTH_DAY_YEAR:
            cols = [col_month_picker, col_day_picker, col_year_picker]
        
        elif arrangement == DatePicker.Arrangement.YEAR_MONTH_DAY:
            cols = [col_year_picker, col_month_picker, col_day_picker]
        
        else:
            raise ValueError(VALUE_ERR_MSG.format(arrangement))
        
        # wrap 'urwid.Columns'
        super().__init__(urwid.Columns(cols,
                                       min_width=min_width_each_picker,
                                       dividechars=space_between))
    
    # This widget is used for all list entries.
    def _generate_item(self, cols, *, align="center"):
        return urwid.AttrMap(SelectableRow(cols, align=align),
                             self._item_attr[0],
                             self._item_attr[1])
    
    def _generate_months(self, start=1, end=12):
        months = []
        
        for month in range(start, end+1):
            item = self._generate_item([self._month_names[month]], align=self._month_align)
            
            # Add a new instance variable which holds the numerical value. This makes it easier to get the displayed value.
            item._numerical_value = month
            
            months.append(item)
        
        return months
    
    def _generate_days(self, year, month):
        start = 1
        weekday, end = calendar.monthrange(year, month)         # end is included
        
        # If the date range is 'ONLY_PAST', the last month does not end as usual but on the specified day.
        if (self._date_range == DatePicker.Range.ONLY_PAST) and (year == self._initial_year) and (month == self._initial_month):
            end = self._initial_day
        
        # If the date range is 'ONLY_FUTURE', the first month does not start as usual but on the specified day.
        elif (self._date_range == DatePicker.Range.ONLY_FUTURE) and (year == self._initial_year) and (month == self._initial_month):
            start = self._initial_day
            weekday = calendar.weekday(year, month, self._initial_day)
        
        days = []
        
        for day in range(start, end+1):
            cols = []
            
            # The 'DatePicker.DayFormat' elements of the iterable are translated into columns of the date picker. This allows the
            # presentation to be customized.
            for df in self._day_format:
                if df == DatePicker.DayFormat.DAY_OF_MONTH:
                    cols.append(str(day))
                    
                elif df == DatePicker.DayFormat.DAY_OF_MONTH_TWO_DIGIT:
                    cols.append(str(day).zfill(2))
                    
                elif df == DatePicker.DayFormat.WEEKDAY:
                    cols.append(self._day_names[weekday])
                    
                else:
                    raise ValueError(VALUE_ERR_MSG.format(df))
            
            item = self._generate_item(cols, align=self._day_align)
            
            # Add a new instance variable which holds the numerical value. This makes it easier to get the displayed value.
            item._numerical_value = day
            
            # Keeps track of the day of the week.
            weekday = (weekday + 1) if (weekday < 6) else 0
            
            days.append(item)
        
        return days
    
    def _year_has_changed(self, previous_year, current_year):
        month_position_before_change = self._month_picker.get_selected_position()
        
        # Since there are no years in 'Range.ALL' that do not have the full month range, the body never needs to be changed after
        # initialization.
        if self._date_range != DatePicker.Range.ALL:
            
            # 'None' stands for trying to keep the old value.
            provisional_position = None
            
            # If the previous year was the specified year, the shortened month range must be replaced by the complete one. If this
            # shortened month range does not begin at 'January', then the difference must be taken into account.
            if previous_year == self._initial_year:
                
                if self._date_range == DatePicker.Range.ONLY_FUTURE:
                    provisional_position = self._month_picker.get_selected_item()._numerical_value - 1
                    
                self._month_picker.set_body(self._month_list,
                                            alternative_position=provisional_position)
            
            # If the specified year is selected, the full month range must be replaced with the shortened one.
            elif current_year == self._initial_year:
                
                if self._date_range == DatePicker.Range.ONLY_FUTURE:
                    provisional_position = month_position_before_change - (self._initial_month - 1)
                    
                self._month_picker.set_body(self._shortened_month_list,
                                            alternative_position=provisional_position)
    
        # Since the month has changed, the corresponding method is called.
        self._month_has_changed(month_position_before_change,
                                self._month_picker.get_selected_position(),
                                previous_year=previous_year)
    
    def _month_has_changed(self, previous_position, current_position, *, previous_year=None):
        # 'None' stands for trying to keep the old value.
        provisional_position = None
        
        current_year = self._year_picker.get_value()
        
        # If the date range is 'ONLY_FUTURE', it may be that a month does not start on the first day. In this case, the value must
        # be changed to reflect this difference.
        if self._date_range == DatePicker.Range.ONLY_FUTURE:
            # If the current or previous year is the specified year and the month was the specified month, the value has an offset
            # of the specified day. Therefore the deposited numerical value is used. ('-1' because it's an index.)
            if ((current_year == self._initial_year) or (previous_year == self._initial_year)) and (previous_position == 0):
                provisional_position = self._day_picker.get_selected_item()._numerical_value - 1
            
            # If the current year is the specified year and the current month is the specified month, the month begins not with 
            # the first day, but with the specified day.
            elif (current_year == self._initial_year) and (current_position == 0):
                provisional_position = self._day_picker.get_selected_position() - (self._initial_day - 1)
            
        self._day_picker.set_body(self._generate_days(current_year,
                                                      self._month_picker.get_selected_item()._numerical_value),
                                  alternative_position=provisional_position)
        
    def get_date(self):
        return datetime.date(self._year_picker.get_value(),
                             self._month_picker.get_selected_item()._numerical_value,
                             self._day_picker.get_selected_item()._numerical_value)
        
    def set_date(self, year, month, day):
        # Invalid dates will raise a ValueError. This includes values beyond the minimum or maximum.
        date_to_be_tested = datetime.date(year, month, day)
        
        # If the date range is limited, test for the new limit.
        if self._date_range != DatePicker.Range.ALL:
            
            limit = datetime.date(self._initial_year, self._initial_month, self._initial_day)
            
            if (self._date_range == DatePicker.Range.ONLY_PAST) and (date_to_be_tested > limit):
                raise ValueError("The passed date is outside the upper bound of the date range.")
            
            elif (self._date_range == DatePicker.Range.ONLY_FUTURE) and (date_to_be_tested < limit):
                raise ValueError("The passed date is outside the lower bound of the date range.")
        
        # Set the new values, if needed.
        # Year
        if year != self._year_picker.get_value():
            self._year_picker.set_value(year)
        
        # Month
        if month != self._month_picker.get_selected_item()._numerical_value:
            month_position = month - 1          # '-1' because it's an index.
            
            if (self._date_range == DatePicker.Range.ONLY_FUTURE) and (year == self._initial_year):
                # If the value should be negative, the behavior of 'IndicativeListBox' shows effect and position 0 is selected.
                month_position = month_position - (self._initial_month - 1)
            
            self._month_picker.select_item(month_position)
        
        # Day
        if day != self._day_picker.get_selected_item()._numerical_value:
            day_position = day - 1              # '-1' because it's an index.
            
            if (self._date_range == DatePicker.Range.ONLY_FUTURE) and (year == self._initial_year) and (month == self._initial_month):
                # If the value should be negative, the behavior of 'IndicativeListBox' shows effect and position 0 is selected.
                day_position = day_position - (self._initial_day - 1)
            
            self._day_picker.select_item(day_position)


# Demonstration
if __name__ == "__main__":
    
    PALETTE = [("default_entry",            "",                 "black"),
               ("reveal_focus",             "black",            "white"),
               ("dp_barActive_focus",       "light gray",       ""),
               ("dp_barActive_off_focus",   "black",            ""),
               ("dp_barInactive_focus",     "dark gray",        ""),
               ("dp_barInactive_off_focus", "black",            ""),
               ("dp_placeholder_focus",     "",                 ""),
               ("dp_placeholder_off_focus", "",                 ""),
               ("dp_highlight_focus",       "black",            "brown",   "standout"),
               ("dp_highlight_off_focus",   "white",            "black"),
               ("text_highlight",           "yellow,bold",      ""),
               ("text_bold",                "bold",             ""),
               ("text_esc",                 "light red,bold",   "")]
    
    
    class TestApp(object):
        def __init__(self, year, month, day):
            self.pickers = []
            
            # Navigation instructions
            text_arrow_keys = urwid.Text([("text_highlight", "ctrl"),
                                          " + (",
                                          ("text_highlight", "↑"),
                                          " or ",
                                          ("text_highlight", "↓"),
                                          ") to move one step_length."])
            
            text_pages = urwid.Text([("text_highlight", "ctrl"),
                                     " + (",
                                     ("text_highlight", "page up"),
                                     " or ",
                                     ("text_highlight", "page down"),
                                     ") to move one jump_length."])
            
            text_home_end = urwid.Text([("text_highlight", "ctrl"),
                                        " + (",
                                        ("text_highlight", "home"),
                                        " or ",
                                        ("text_highlight", "end"),
                                        ") to jump to the corresponding end."])
            
            # Columns
            # Left
            left_heading = "default:"
            
            self.pickers.append(DatePicker(year, month, day,
                                           key_modifier=KeyModifier.CTRL,
                                           highlight=("reveal_focus", None)))
            
            self.pickers.append(DatePicker(year, month, day,
                                           date_range=DatePicker.Range.ONLY_PAST,
                                           key_modifier=KeyModifier.CTRL,
                                           day_format=(DatePicker.DayFormat.DAY_OF_MONTH, DatePicker.DayFormat.WEEKDAY),
                                           highlight=("reveal_focus", None)))
            
            self.pickers.append(DatePicker(year, month, day,
                                           date_range=DatePicker.Range.ONLY_FUTURE,
                                           key_modifier=KeyModifier.CTRL,
                                           highlight=("reveal_focus", None)))
            
            left_column = urwid.Pile([urwid.AttrMap(urwid.Text(left_heading, align="center"),
                                                    "text_bold"),
                                                    
                                      urwid.Text("▔" * len(left_heading), align="center"),
                                      
                                      urwid.Text("all dates:"),       
                                      self.pickers[0],
                                      
                                      urwid.Divider(" "),
                                      
                                      urwid.Text("only past:"),
                                      self.pickers[1],
                                      
                                      urwid.Divider(" "),
                                      
                                      urwid.Text("only future:"),
                                      self.pickers[2]])
            
            # Right
            right_heading = "additional parameters:"
            
            self.pickers.append(DatePicker(year, month, day,
                                           key_modifier=KeyModifier.CTRL,
                                           day_format=(DatePicker.DayFormat.DAY_OF_MONTH_TWO_DIGIT,),
                                           top_covered=("ᐃ",  "dp_barActive_focus", "dp_barActive_off_focus"),
                                           top_exposed=("─x─", "dp_barInactive_focus", "dp_barInactive_off_focus"),
                                           bottom_covered=("ᐁ",  "dp_barActive_focus", "dp_barActive_off_focus"), 
                                           bottom_exposed=("─x─", "dp_barInactive_focus", "dp_barInactive_off_focus"), 
                                           highlight=("dp_highlight_focus", "dp_highlight_off_focus")))
            
            self.pickers.append(DatePicker(year, month, day,
                                           date_range=DatePicker.Range.ONLY_PAST,
                                           key_modifier=KeyModifier.CTRL,
                                           day_format=(DatePicker.DayFormat.DAY_OF_MONTH,),
                                           arrangement=DatePicker.Arrangement.MONTH_DAY_YEAR,
                                           top_covered=("ᐃ",  "dp_barActive_focus", "dp_barActive_off_focus"),
                                           top_exposed=("─x─", "dp_barInactive_focus", "dp_barInactive_off_focus"),
                                           bottom_covered=("ᐁ",  "dp_barActive_focus", "dp_barActive_off_focus"), 
                                           bottom_exposed=("─x─", "dp_barInactive_focus", "dp_barInactive_off_focus"), 
                                           highlight=("dp_highlight_focus", "dp_highlight_off_focus")))
            
            self.pickers.append(DatePicker(year, month, day,
                                           date_range=DatePicker.Range.ONLY_FUTURE,
                                           key_modifier=KeyModifier.CTRL,
                                           month_names=["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
                                           day_format=(DatePicker.DayFormat.DAY_OF_MONTH,),
                                           arrangement=DatePicker.Arrangement.YEAR_MONTH_DAY,
                                           min_width_each_picker=4,
                                           width_day_picker=(4,),
                                           width_month_picker=(4,),
                                           width_year_picker=(6,),
                                           space_between=1,
                                           top_covered=("ᐃ",  "dp_barActive_focus", "dp_barActive_off_focus"),
                                           top_exposed=("─x─", "dp_barInactive_focus", "dp_barInactive_off_focus"),
                                           bottom_covered=("ᐁ",  "dp_barActive_focus", "dp_barActive_off_focus"), 
                                           bottom_exposed=("─x─", "dp_barInactive_focus", "dp_barInactive_off_focus"), 
                                           highlight=("dp_highlight_focus", "dp_highlight_off_focus")))
            
            right_column = urwid.Pile([urwid.AttrMap(urwid.Text(right_heading, align="center"),
                                                     "text_bold"),
                                                     
                                       urwid.Text("▔" * len(right_heading), align="center"),
                                       
                                       urwid.Text("d-m-y, all dates:"),       
                                       self.pickers[3],
                                       
                                       urwid.Divider(" "),
                                       
                                       urwid.Text("m-d-y, only past:"),
                                       self.pickers[4],
                                       
                                       urwid.Divider(" "),
                                       
                                       urwid.Text("y-m-d, numerical, only future:"),
                                       self.pickers[5]])
            
            # Both
            columns = urwid.Columns([left_column, right_column],
                                    dividechars=10)
            
            # Reset button
            def reset(btn):
                for picker in self.pickers:
                    picker.set_date(year, month, day)
            
            reset_button = urwid.AttrMap(SelectableRow(["Reset"], align="center", on_select=reset),
                                         "",
                                         "reveal_focus")
            
            # Termination instructions
            text_esc = urwid.Text([("text_esc", "Q"),
                                   " or ",
                                   ("text_esc", "Esc"),
                                   " to quit."])
            
            pile = urwid.Pile([text_arrow_keys,
                               text_pages,
                               text_home_end,
                            
                               urwid.Divider("─"),
                               
                               columns,
                            
                               urwid.Divider(" "),
                               
                               reset_button,
                               
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
    

    # run TestApp
    today = datetime.date.today()
    
    test = TestApp(today.year, today.month, today.day)
    test.start()
    
    for i, picker in enumerate(test.pickers):
        print("picker {}: {}".format(i, picker.get_date()))
    
