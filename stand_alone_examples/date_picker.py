#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import calendar
import datetime
import enum
import random
import sys
import urwid


_TYPE_ERR_MSG = "type {} was expected for {}, but found: {}."
_VALUE_ERR_MSG = "unrecognized value: {}."


class MODIFIER_KEY(enum.Enum):
    NONE = ""
    SHIFT = "shift"
    ALT = "meta"
    CTRL = "ctrl"
    SHIFT_ALT = "shift meta"
    SHIFT_CTRL = "shift ctrl"
    ALT_CTRL = "meta ctrl"
    SHIFT_ALT_CTRL = "shift meta ctrl"
    
    def append_to(self, text, separator=" "):
        return (text + separator + self.value) if (self != MODIFIER_KEY.NONE) else text
    
    def prepend_to(self, text, separator=" "):
        return (self.value + separator + text) if (self != MODIFIER_KEY.NONE) else text


# This class has been slightly modified, but essentially corresponds to this class posted on stackoverflow.com:
# https://stackoverflow.com/questions/52106244/how-do-you-combine-multiple-tui-forms-to-write-more-complex-applications#answer-52174629
class SelectableRow(urwid.WidgetWrap):
    def __init__(self, contents, *, align="left", on_select=None):
        # A list-like object, where each element represents the value of a column.
        self.contents = contents
        
        self._columns = urwid.Columns([urwid.Text(c, align=align) 
                                       for c in contents])
        
        # Wrap 'urwid.Columns'.
        super().__init__(self._columns)
        
        # A hook which defines the behavior that is executed when triggered.
        self.on_select = on_select
    
    def __repr__(self):
        return "{}(contents='{}')".format(self.__class__.__name__,
                                          self.contents)
    
    def selectable(self):
        return True
    
    def keypress(self, size, key):
        if (key == "enter") and (self.on_select is not None):
            self.on_select(self)
            key = None
            
        return key
    
    def set_contents(self, contents):
        # Update the list record inplace...
        self.contents[:] = contents
        
        # ... and update the displayed items.
        for t, (w, _) in zip(contents, self._columns.contents):
            w.set_text(t)


class IndicativeListBox(urwid.WidgetWrap):
    # These values are translated by '_get_nearest_valid_position()' into the corresponding int values.
    class POSITION(enum.Enum):
        LAST = 1
        MIDDLE = 2
        RANDOM = 3
        
    def __init__(self, body, *, position=0, on_selection_change=None, initialization_is_selection_change=False,
                 modifier_key=MODIFIER_KEY.NONE, return_unused_navigation_input=True, topBar_align="center",
                 topBar_endCovered_prop=("▲", None, None), topBar_endExposed_prop=("───", None, None), bottomBar_align="center",
                 bottomBar_endCovered_prop=("▼", None, None), bottomBar_endExposed_prop=("───", None, None), highlight_offFocus=None,
                 placeholder=urwid.Filler(urwid.Text("Not enough space to display this widget.", align="center"))):
        # If not already done, wrap each item of the body in an 'urwid.AttrMap'.This is necessary to enable off focus highlighting.
        body[:] = [urwid.AttrMap(item, None) if not isinstance(item, urwid.AttrMap) else item
                   for item in body]
        
        # Wrap 'urwid.ListBox'.
        super().__init__(urwid.ListBox(body))
        
        # Select the specified list position, or the nearest valid one.
        nearest_valid_position = self._get_nearest_valid_position(position)
        
        if nearest_valid_position is not None:
            self._w.set_focus(nearest_valid_position)
        
        # A hook which is triggered when the selection changes.
        self.on_selection_change = on_selection_change
        
        # Initialization can be seen as a special case of selection change. This is interesting in combination with the hook.
        self._initialization_is_selection_change = initialization_is_selection_change
        
        # 'MODIFIER_KEY' changes the behavior of the list box, so that it responds only to modified input. ('up' => 'ctrl up')
        self._modifier_key = modifier_key
        
        # If the list item at the top is selected and you navigate further upwards, the input is normally not swallowed by the
        # list box, but passed on so that other widgets can interpret it. This may result in transferring the focus.
        self._return_unused_navigation_input = return_unused_navigation_input
        
        # The bars are just 'urwid.Text' widgets.
        self._top_bar = urwid.AttrMap(urwid.Text("", align=topBar_align),
                                      None)
        
        self._bottom_bar = urwid.AttrMap(urwid.Text("", align=bottomBar_align),
                                         None)
        
        # If there is not enough space available to display the widget, a placeholder will be shown instead.
        self._placeholder = placeholder
        
        # During the initialization of 'urwid.AttrMap', the value can be passed as non-dict. After initializing, its value can be
        # manipulated by passing a dict. The dicts I create below will be used later to change the appearance of the bars.
        self._topBar_endCovered_markup = topBar_endCovered_prop[0]
        self._topBar_endCovered_focus = {None:topBar_endCovered_prop[1]}
        self._topBar_endCovered_offFocus = {None:topBar_endCovered_prop[2]}
        
        self._topBar_endExposed_markup = topBar_endExposed_prop[0]
        self._topBar_endExposed_focus = {None:topBar_endExposed_prop[1]}
        self._topBar_endExposed_offFocus = {None:topBar_endExposed_prop[2]}
        
        self._bottomBar_endCovered_markup = bottomBar_endCovered_prop[0]
        self._bottomBar_endCovered_focus = {None:bottomBar_endCovered_prop[1]}
        self._bottomBar_endCovered_offFocus = {None:bottomBar_endCovered_prop[2]}
        
        self._bottomBar_endExposed_markup = bottomBar_endExposed_prop[0]
        self._bottomBar_endExposed_focus = {None:bottomBar_endExposed_prop[1]}
        self._bottomBar_endExposed_offFocus = {None:bottomBar_endExposed_prop[2]}
        
        # This is used to highlight the selected item when the widget does not have the focus.
        self._highlight_offFocus = {None:highlight_offFocus}
        self._last_focus_state = None
        self._original_item_attr_map = None
        
        # Is 'on_selection_change' triggered during the initialization?
        if initialization_is_selection_change and (on_selection_change is not None):
            on_selection_change(None,
                                self.get_selected_position())
    
    def __repr__(self):
        return "{}(body='{}', position='{}')".format(self.__class__.__name__,
                                                     self.get_body(),
                                                     self.get_selected_position())
    
    def render(self, size, focus=False):
        just_maxcol = (size[0],)
        
        # The size also includes the two bars, so subtract these.
        modified_size = (size[0],                                                                           # cols
                         size[1] - self._top_bar.rows(just_maxcol) - self._bottom_bar.rows(just_maxcol))    # rows
        
        if modified_size[1] < 1:
            # If there is not enough space left to show the list box, return the placeholder.
            return self._placeholder.render(size, focus=focus)
        
        else:
            # Evaluates which ends are visible and calculates how many list entries are hidden above/below. This is a modified form
            # of 'urwid.ListBox.ends_visible()'.
            middle, top, bottom = self._w.calculate_visible(modified_size, focus=focus)
            
            if middle is None:                      # empty list box
                top_is_visible = True
                bottom_is_visible = True
                
            else:
                top_is_visible = False
                bottom_is_visible = False
            
                trim_top, above = top
                trim_bottom, below = bottom
                
                if trim_top == 0:
                    pos = above[-1][1] if (len(above) != 0) else middle[2]
                    
                    if self._w._body.get_prev(pos) == (None,None):
                        top_is_visible = True
                    else:
                        covered_above = pos
                
                if trim_bottom == 0:
                    row_offset, _, pos, rows, _ = middle
                    
                    row_offset += rows              # Include the selected position.
                    
                    for _, pos, rows in below:      # 'pos' is overridden
                        row_offset += rows
                        
                    if (row_offset < modified_size[1]) or (self._w._body.get_next(pos) == (None, None)):
                        bottom_is_visible = True
                    else:
                        covered_below = self.rearmost_position() - pos
            
            # Changes the appearance of the bar at the top depending on whether the first list item is visible and the widget has
            # the focus.
            if top_is_visible:
                self._top_bar.original_widget.set_text(self._topBar_endExposed_markup)
                self._top_bar.set_attr_map(self._topBar_endExposed_focus
                                          if focus else self._topBar_endExposed_offFocus)
            else:
                self._top_bar.original_widget.set_text(self._topBar_endCovered_markup.format(covered_above))
                self._top_bar.set_attr_map(self._topBar_endCovered_focus
                                           if focus else self._topBar_endCovered_offFocus)
            
            # Changes the appearance of the bar at the bottom depending on whether the last list item is visible and the widget
            # has the focus.
            if bottom_is_visible:
                self._bottom_bar.original_widget.set_text(self._bottomBar_endExposed_markup)
                self._bottom_bar.set_attr_map(self._bottomBar_endExposed_focus
                                              if focus else self._bottomBar_endExposed_offFocus)
            else:
                self._bottom_bar.original_widget.set_text(self._bottomBar_endCovered_markup.format(covered_below))
                self._bottom_bar.set_attr_map(self._bottomBar_endCovered_focus
                                              if focus else self._bottomBar_endCovered_offFocus)
            
            # The highlighting in urwid is bound to the focus. This means that the selected item is only distinguishable as long
            # as the widget has the focus. Therefore, I highlight the selected item by temporarily changing its color scheme when
            # the 'IndicativeListBox' does not have the focus.
            if focus and not self._last_focus_state and (self._original_item_attr_map is not None):
                # Resets the appearance of the selected item to its original value.
                self._w.focus.set_attr_map(self._original_item_attr_map)
                
            elif (self._highlight_offFocus is not None) \
                        and not focus \
                        and (self._last_focus_state or (self._last_focus_state is None)) \
                        and not self.body_is_empty():
                # Store the 'attr_map' of the selected item and then change it to accomplish off focus highlighting.
                self._original_item_attr_map = self._w.focus.get_attr_map()
                self._w.focus.set_attr_map(self._highlight_offFocus)
            
            # Store the last focus to do/undo the off focus highlighting only if the focus has really changed and not if the
            # widget is re-rendered because the terminal size has changed or similar.
            self._last_focus_state = focus
            
            # 'urwid.CanvasCombine' puts the passed canvases one above the other.
            return urwid.CanvasCombine([(self._top_bar.render(just_maxcol), None, False),
                                        (self._w.render(modified_size, focus=focus), None, True),
                                        (self._bottom_bar.render(just_maxcol), None, False)])
    
    def keypress(self, size, key):
        just_maxcol = (size[0],)
        
        # The size also includes the two bars, so subtract these.
        modified_size = (size[0],                                                                           # cols
                         size[1] - self._top_bar.rows(just_maxcol) - self._bottom_bar.rows(just_maxcol))    # rows
        
        # If there is not enough space left to display the list box, just return the key code.
        if modified_size[1] >= 1:
            # Store the focus position before passing the keystroke to the original list box. That way, it can be compared with the 
            # position after the input is processed. If the list box body is empty, store None.
            focus_position_before_input = self.get_selected_position()
            
            # A keystroke is changed to a modified one ('up' => 'ctrl up'). This prevents the original widget from responding when
            # the arrows keys are used to navigate between widgets. That way it can be used in a 'urwid.Pile' or similar.
            if key == self._modifier_key.prepend_to("up"):
                key = self._pass_key_to_original_widget(modified_size, "up")
                
            elif key == self._modifier_key.prepend_to("down"):
                key = self._pass_key_to_original_widget(modified_size, "down")
                
            elif key == self._modifier_key.prepend_to("page up"):
                key = self._pass_key_to_original_widget(modified_size, "page up")
                
            elif key == self._modifier_key.prepend_to("page down"):
                key = self._pass_key_to_original_widget(modified_size, "page down")
                
            elif key == self._modifier_key.prepend_to("home"):
                # Check if the first list item is already selected.
                if (focus_position_before_input is not None) and (focus_position_before_input != 0):
                    self.select_first_item()
                    key = None
                elif not self._return_unused_navigation_input:
                    key = None
                    
            elif key == self._modifier_key.prepend_to("end"):
                # Check if the last list item is already selected.
                if (focus_position_before_input is not None) and (focus_position_before_input != self.rearmost_position()):
                    self.select_last_item()
                    key = None
                elif not self._return_unused_navigation_input:
                    key = None
            
            focus_position_after_input = self.get_selected_position()
            
            # If the focus position has changed, execute the hook (if existing).
            if (focus_position_before_input != focus_position_after_input) and (self.on_selection_change is not None):
                self.on_selection_change(focus_position_before_input,
                                         focus_position_after_input)
            
        return key
    
    def mouse_event(self, size, event, button, col, row, focus):
        just_maxcol = (size[0],)
        
        topBar_rows = self._top_bar.rows(just_maxcol)
        bottomBar_rows = self._bottom_bar.rows(just_maxcol)
        
        # The size also includes the two bars, so subtract these.
        modified_size = (size[0],                                   # cols
                         size[1] - topBar_rows - bottomBar_rows)    # rows
        
        was_handeled = False
        
        # If there is not enough space left to display the list box, ignore the mouse event by returning 'False'.
        if focus and (modified_size[1] >= 1):
            # An event is changed to a modified one ('mouse press' => 'ctrl mouse press'). This prevents the original widget from
            # responding when mouse buttons are also used to navigate between widgets.
            if event == self._modifier_key.prepend_to("mouse press"):
                # Store the focus position before passing the input to the original list box. That way, it can be compared with the 
                # position after the input is processed. If the list box body is empty, store None.
                focus_position_before_input = self.get_selected_position()
                
                # left mouse button, if not top bar or bottom bar.
                if (button == 1.0) and (topBar_rows <= row < (size[1] - bottomBar_rows)):
                    # Because 'row' includes the top bar, the offset must be substracted before passing it to the original list box.
                    result = self._w.mouse_event(modified_size, event, button, col, (row - topBar_rows), focus)
                    was_handeled = result if self._return_unused_navigation_input else True
                
                # mousewheel up
                elif button == 4.0:
                    was_handeled = self._pass_key_to_original_widget(modified_size, "page up")
                    
                # mousewheel down
                elif button == 5.0:
                    was_handeled = self._pass_key_to_original_widget(modified_size, "page down")
                    
                focus_position_after_input = self.get_selected_position()
                
                # If the focus position has changed, execute the hook (if existing).
                if (focus_position_before_input != focus_position_after_input) and (self.on_selection_change is not None):
                    self.on_selection_change(focus_position_before_input,
                                             focus_position_after_input)
        
        return was_handeled
    
    # Pass the keystroke to the original widget. If it is not used, evaluate the corresponding variable to decide if it gets
    # swallowed or not.
    def _pass_key_to_original_widget(self, size, key):
        result = self._w.keypress(size, key)
        return result if self._return_unused_navigation_input else None
    
    def get_body(self):
        return self._w.body
    
    def body_len(self):
        return len(self.get_body())
    
    def rearmost_position(self):
        return self.body_len() - 1           # last valid index
    
    def body_is_empty(self):
        return self.body_len() == 0
    
    def position_is_valid(self, position):
        return (position < self.body_len()) and (position >= 0)
    
    # If the passed position is valid, it is returned. Otherwise, the nearest valid position is returned. This ensures that
    # positions which are out of range do not result in an error.
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
            
        elif pos_type == IndicativeListBox.POSITION:
            if position == IndicativeListBox.POSITION.LAST:
                return self.rearmost_position()
                
            elif position == IndicativeListBox.POSITION.MIDDLE:
                return self.body_len() // 2
                
            elif position == IndicativeListBox.POSITION.RANDOM:
                return random.randint(0,
                                      self.rearmost_position())
                
            else:
                raise ValueError(_VALUE_ERR_MSG.format(position))
            
        else:
            raise TypeError(_TYPE_ERR_MSG.format("<class 'int'> or <enum 'IndicativeListBox.POSITION'>",
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
        # Resets the appearance of the selected item to its original value, if off focus highlighting is active.
        if not self._last_focus_state and (self._original_item_attr_map is not None):
            self._w.focus.set_attr_map(self._original_item_attr_map)
        
        # The next time the widget is rendered, the highlighting is redone.
        self._original_item_attr_map = None
        self._last_focus_state = None
    
    def set_body(self, body, *, alternative_position=None):
        focus_position_before_change = self.get_selected_position()
        
        self._reset_highlighting()
        
        # Wrap each item in an 'urwid.AttrMap', if not already done.
        self._w.body[:] = [urwid.AttrMap(item, None) if not isinstance(item, urwid.AttrMap) else item
                           for item in body]
        
        # Normally it is tried to hold the focus position. If this is not desired, a position can be passed.
        if alternative_position is not None:
            nearest_valid_position = self._get_nearest_valid_position(alternative_position)
            
            if nearest_valid_position is not None:
                # Because the widget has been re-rendered, the off focus highlighted item must be restored to its original state.
                self._reset_highlighting()
                
                self._w.set_focus(nearest_valid_position)
        
        # If an initialization is considered a selection change, execute the hook (if existing).
        if self._initialization_is_selection_change and (self.on_selection_change is not None):
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
    def __init__(self, value, *, min_v=(-sys.maxsize - 1), max_v=sys.maxsize, step_len=1, jump_len=100, on_selection_change=None,
                 initialization_is_selection_change=False, modifier_key=MODIFIER_KEY.NONE, ascending=True,
                 return_unused_navigation_input=True, topBar_align="center", topBar_endCovered_prop=("▲", None, None),
                 topBar_endExposed_prop=("───", None, None), bottomBar_align="center", bottomBar_endCovered_prop=("▼", None, None),
                 bottomBar_endExposed_prop=("───", None, None), display_syntax="{}", display_align="center", display_prop=(None, None)):
        assert (min_v <= max_v), "'min_v' must be less than or equal to 'max_v'."
        
        assert (min_v <= value <= max_v), "'min_v <= value <= max_v' must be True."
        
        self._value = value
        
        self._minimum = min_v
        self._maximum = max_v
    
        # Specifies how far to move in the respective direction when the keys 'up/down' are pressed.
        self._step_len = step_len
        
        # Specifies how far to jump in the respective direction when the keys 'page up/down' or the mouse events 'wheel up/down'
        # are passed.
        self._jump_len = jump_len
        
        # A hook which is triggered when the value changes.
        self.on_selection_change = on_selection_change
        
        # 'MODIFIER_KEY' changes the behavior, so that the widget responds only to modified input. ('up' => 'ctrl up')
        self._modifier_key = modifier_key
        
        # Specifies whether moving upwards represents a decrease or an increase of the value.
        self._ascending = ascending
        
        # If the minimum has been reached and an attempt is made to select an even smaller value, the input is normally not
        # swallowed by the widget, but passed on so that other widgets can interpret it. This may result in transferring the focus.
        self._return_unused_navigation_input = return_unused_navigation_input
        
        # The bars are just 'urwid.Text' widgets.
        self._top_bar = urwid.AttrMap(urwid.Text("", topBar_align),
                                      None)
        
        self._bottom_bar = urwid.AttrMap(urwid.Text("", bottomBar_align),
                                         None)
        
        # During the initialization of 'urwid.AttrMap', the value can be passed as non-dict. After initializing, its value can be
        # manipulated by passing a dict. The dicts I create below will be used later to change the appearance of the widgets.
        self._topBar_endCovered_markup = topBar_endCovered_prop[0]
        self._topBar_endCovered_focus = {None:topBar_endCovered_prop[1]}
        self._topBar_endCovered_offFocus = {None:topBar_endCovered_prop[2]}
        
        self._topBar_endExposed_markup = topBar_endExposed_prop[0]
        self._topBar_endExposed_focus = {None:topBar_endExposed_prop[1]}
        self._topBar_endExposed_offFocus = {None:topBar_endExposed_prop[2]}
        
        self._bottomBar_endCovered_markup = bottomBar_endCovered_prop[0]
        self._bottomBar_endCovered_focus = {None:bottomBar_endCovered_prop[1]}
        self._bottomBar_endCovered_offFocus = {None:bottomBar_endCovered_prop[2]}
        
        self._bottomBar_endExposed_markup = bottomBar_endExposed_prop[0]
        self._bottomBar_endExposed_focus = {None:bottomBar_endExposed_prop[1]}
        self._bottomBar_endExposed_offFocus = {None:bottomBar_endExposed_prop[2]}
        
        # Format the number before displaying it. That way it is easier to read.
        self._display_syntax = display_syntax
        
        # The current value is displayed via this widget.
        self._display = SelectableRow([display_syntax.format(value)],
                                     align=display_align)
        
        display_attr = urwid.AttrMap(self._display,
                                     display_prop[1],
                                     display_prop[0])
        
        # wrap 'urwid.Pile'
        super().__init__(urwid.Pile([self._top_bar,
                                     display_attr,
                                     self._bottom_bar]))
        
        # Is 'on_selection_change' triggered during the initialization?
        if initialization_is_selection_change and (on_selection_change is not None):
            on_selection_change(None, value)
            
    def __repr__(self):
        return "{}(value='{}', min_v='{}', max_v='{}', ascending='{}')".format(self.__class__.__name__,
                                                                               self._value,
                                                                               self._minimum,
                                                                               self._maximum,
                                                                               self._ascending)
            
    def render(self, size, focus=False):
        # Changes the appearance of the bar at the top depending on whether the upper limit is reached.
        if self._value == (self._minimum if self._ascending else self._maximum):
            self._top_bar.original_widget.set_text(self._topBar_endExposed_markup)
            self._top_bar.set_attr_map(self._topBar_endExposed_focus
                                       if focus else self._topBar_endExposed_offFocus)
        else:
            self._top_bar.original_widget.set_text(self._topBar_endCovered_markup)
            self._top_bar.set_attr_map(self._topBar_endCovered_focus
                                       if focus else self._topBar_endCovered_offFocus)
        
        # Changes the appearance of the bar at the bottom depending on whether the lower limit is reached.
        if self._value == (self._maximum if self._ascending else self._minimum):
            self._bottom_bar.original_widget.set_text(self._bottomBar_endExposed_markup)
            self._bottom_bar.set_attr_map(self._bottomBar_endExposed_focus
                                          if focus else self._bottomBar_endExposed_offFocus)
        else:
            self._bottom_bar.original_widget.set_text(self._bottomBar_endCovered_markup)
            self._bottom_bar.set_attr_map(self._bottomBar_endCovered_focus
                                          if focus else self._bottomBar_endCovered_offFocus)
            
        return super().render(size, focus=focus)
    
    def keypress(self, size, key):
        # A keystroke is changed to a modified one ('up' => 'ctrl up'). This prevents the widget from responding when the arrows 
        # keys are used to navigate between widgets. That way it can be used in a 'urwid.Pile' or similar.
        if key == self._modifier_key.prepend_to("up"):
            successful = self._change_value(-self._step_len)
        
        elif key == self._modifier_key.prepend_to("down"):
            successful = self._change_value(self._step_len)
        
        elif key == self._modifier_key.prepend_to("page up"):
            successful = self._change_value(-self._jump_len)
        
        elif key == self._modifier_key.prepend_to("page down"):
            successful = self._change_value(self._jump_len)
        
        elif key == self._modifier_key.prepend_to("home"):
            successful = self._change_value(float("-inf"))
        
        elif key == self._modifier_key.prepend_to("end"):
            successful = self._change_value(float("inf"))
        
        else:
            successful = False
        
        return key if not successful else None
    
    def mouse_event(self, size, event, button, col, row, focus):
        if focus:
            # An event is changed to a modified one ('mouse press' => 'ctrl mouse press'). This prevents the original widget from
            # responding when mouse buttons are also used to navigate between widgets.
            if event == self._modifier_key.prepend_to("mouse press"):
                # mousewheel up
                if button == 4.0:
                    result = self._change_value(-self._jump_len)
                    return result if self._return_unused_navigation_input else True
                
                # mousewheel down
                elif button == 5.0:
                    result = self._change_value(self._jump_len)
                    return result if self._return_unused_navigation_input else True
        
        return False
    
    # This method tries to change the value depending on the desired arrangement and returns True if this change was successful.
    def _change_value(self, summand):
        value_before_input = self._value
        
        if self._ascending:
            new_value = self._value + summand
            
            if summand < 0:
                # If the corresponding limit has already been reached, then determine whether the unused input should be
                # returned or swallowed.
                if self._value == self._minimum:
                    return not self._return_unused_navigation_input
                
                # If the new value stays within the permitted range, use it.
                elif new_value > self._minimum:
                    self._value = new_value
                
                # The permitted range would be exceeded, so the limit is set instead.
                else:
                    self._value = self._minimum
            
            elif summand > 0:
                if self._value == self._maximum:
                    return not self._return_unused_navigation_input
                
                elif new_value < self._maximum:
                    self._value = new_value
                
                else:
                    self._value = self._maximum
        else:
            new_value = self._value - summand
            
            if summand < 0:
                if self._value == self._maximum:
                    return not self._return_unused_navigation_input
                
                elif new_value < self._maximum:
                    self._value = new_value
                
                else:
                    self._value = self._maximum
            
            elif summand > 0:
                if self._value == self._minimum:
                    return not self._return_unused_navigation_input
                
                elif new_value > self._minimum:
                    self._value = new_value
                
                else:
                    self._value = self._minimum
        
        # Update the displayed value.
        self._display.set_contents([self._display_syntax.format(self._value)])
        
        # If the value has changed, execute the hook (if existing).
        if (value_before_input != self._value) and (self.on_selection_change is not None):
            self.on_selection_change(value_before_input,
                                     self._value)
        
        return True
    
    def get_value(self):
        return self._value
    
    def set_value(self, value):
        if not (self._minimum <= value <= self._maximum):
            raise ValueError("'minimum <= value <= maximum' must be True.")
            
        if value != self._value:
            value_before_change = self._value
            self._value = value
            
            # Update the displayed value.
            self._display.set_contents([self._display_syntax.format(self._value)])
            
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


# Clones an iterable and recursively replace specific values.
def recursively_replace(original, replacements, include_original_keys=False):
    # If this function would be called recursively, the parameters 'replacements' and 'include_original_keys' would have to be 
    # passed each time. Therefore, a helper function with a reduced parameter list is used for the recursion, which nevertheless
    # can access the said parameters.
    
    def _recursion_helper(obj):
        #Determine if the object should be replaced. If it is not hashable, the search will throw a TypeError.
        try:
            if obj in replacements:
                return replacements[obj]
        except TypeError:
            pass

        # An iterable is recursively processed depending on its class.
        if hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes, bytearray)):
            if isinstance(obj, dict):
                contents = {}

                for key, val in obj.items():
                    new_key = _recursion_helper(key) if include_original_keys else key
                    new_val = _recursion_helper(val)

                    contents[new_key] = new_val

            else:
                contents = []

                for element in obj:
                    new_element = _recursion_helper(element)

                    contents.append(new_element)

            # Use the same class as the original.
            return obj.__class__(contents)

        # If it is not replaced and it is not an iterable, return it.
        return obj

    return _recursion_helper(original)


class DatePicker(urwid.WidgetWrap):
    # These values are interpreted during the creation of the list items for the day picker.
    class DAY_FORMAT(enum.Enum):
        DAY_OF_MONTH = 1
        DAY_OF_MONTH_TWO_DIGIT = 2
        WEEKDAY = 3
        
    # These values are interpreted during the initialization and define the arrangement of the pickers.
    class PICKER(enum.Enum):
        YEAR = 1
        MONTH = 2
        DAY = 3
    
    # Specifies which dates are selectable.
    class RANGE(enum.Enum):
        ALL = 1
        ONLY_PAST = 2
        ONLY_FUTURE = 3
    
    def __init__(self, initial_date=datetime.date.today(), *, date_range=RANGE.ALL, month_names=calendar.month_name, day_names=calendar.day_abbr,
                 day_format=(DAY_FORMAT.WEEKDAY, DAY_FORMAT.DAY_OF_MONTH), columns=(PICKER.DAY, PICKER.MONTH, PICKER.YEAR),
                 modifier_key=MODIFIER_KEY.CTRL, return_unused_navigation_input=False, year_jump_len=50, space_between=2, 
                 min_width_each_picker=9, year_align="center", month_align="center", day_align="center", topBar_align="center", 
                 topBar_endCovered_prop=("▲", None, None), topBar_endExposed_prop=("───", None, None), bottomBar_align="center",
                 bottomBar_endCovered_prop=("▼", None, None), bottomBar_endExposed_prop=("───", None, None), highlight_prop=(None, None)):
        assert (type(date_range) == DatePicker.RANGE), _TYPE_ERR_MSG.format("<enum 'DatePicker.RANGE'>",
                                                                            "'date_range'",
                                                                            type(date_range))
        
        for df in day_format:
            assert (type(df) == DatePicker.DAY_FORMAT), _TYPE_ERR_MSG.format("<enum 'DatePicker.DAY_FORMAT'>",
                                                                             "all elements of 'day_format'",
                                                                             type(df))
        
        # Relevant for 'RANGE.ONLY_PAST' and 'RANGE.ONLY_FUTURE' to limit the respective choices.
        self._initial_year = initial_date.year
        self._initial_month = initial_date.month
        self._initial_day = initial_date.day
        
        # The date pool can be limited, so that only past or future dates are selectable. The initial date is included in the
        # pool.
        self._date_range = date_range
        
        # The presentation of months and weekdays can be changed by passing alternative values (e.g. abbreviations or numerical
        # representations).
        self._month_names = month_names
        self._day_names = day_names
        
        # Since there are different needs regarding the appearance of the day picker, an iterable can be passed, which allows a
        # customization of the presentation.
        self._day_format = day_format
        
        # Specifies the text alignment of the individual pickers. The year alignment is passed directly to the year picker.
        self._month_align = month_align
        self._day_align = day_align
        
        # The default style of a list entry. Since only one list entry will be visible at a time and there is also off focus 
        # highlighting, the normal value can be 'None' (it is never shown).
        self._item_attr = (None, highlight_prop[0])
        
        # A full list of months. (From 'January' to 'December'.)
        self._month_list = self._generate_months()
        
        # Set the respective values depending on the date range.
        min_year = datetime.MINYEAR
        max_year = datetime.MAXYEAR
        
        month_position = self._initial_month - 1
        day_position = self._initial_day - 1
        
        if date_range == DatePicker.RANGE.ALL:
            initial_month_list = self._month_list
            
        elif date_range == DatePicker.RANGE.ONLY_PAST:
            max_year = self._initial_year
            
            # The months of the very last year may be shorten.
            self._shortened_month_list = self._generate_months(end=self._initial_month)
            initial_month_list = self._shortened_month_list
            
        elif date_range == DatePicker.RANGE.ONLY_FUTURE:
            min_year = self._initial_year
            
            # The months of the very first year may be shorten.
            self._shortened_month_list = self._generate_months(start=self._initial_month)
            initial_month_list = self._shortened_month_list
            
            # The list may not start at 1 but some other day of month, therefore use the first list item.
            month_position = 0
            day_position = 0
            
        else:
            raise ValueError(_VALUE_ERR_MSG.format(date_range))
        
        # Create pickers.
        self._year_picker = IntegerPicker(self._initial_year,
                                          min_v=min_year,
                                          max_v=max_year,
                                          jump_len=year_jump_len,
                                          on_selection_change=self._year_has_changed,
                                          modifier_key=modifier_key,
                                          return_unused_navigation_input=return_unused_navigation_input,
                                          topBar_align=topBar_align,
                                          topBar_endCovered_prop=topBar_endCovered_prop,
                                          topBar_endExposed_prop=topBar_endExposed_prop,
                                          bottomBar_align=bottomBar_align,
                                          bottomBar_endCovered_prop=bottomBar_endCovered_prop,
                                          bottomBar_endExposed_prop=bottomBar_endExposed_prop,
                                          display_syntax="{:04}",
                                          display_align=year_align,
                                          display_prop=highlight_prop)
        
        self._month_picker = IndicativeListBox(initial_month_list,
                                               position=month_position,
                                               on_selection_change=self._month_has_changed,
                                               modifier_key=modifier_key,
                                               return_unused_navigation_input=return_unused_navigation_input,
                                               topBar_align=topBar_align,
                                               topBar_endCovered_prop=topBar_endCovered_prop,
                                               topBar_endExposed_prop=topBar_endExposed_prop,
                                               bottomBar_align=bottomBar_align,
                                               bottomBar_endCovered_prop=bottomBar_endCovered_prop,
                                               bottomBar_endExposed_prop=bottomBar_endExposed_prop,
                                               highlight_offFocus=highlight_prop[1])
        
        self._day_picker = IndicativeListBox(self._generate_days(self._initial_year, self._initial_month),
                                             position=day_position,
                                             modifier_key=modifier_key,
                                             return_unused_navigation_input=return_unused_navigation_input,
                                             topBar_align=topBar_align,
                                             topBar_endCovered_prop=topBar_endCovered_prop,
                                             topBar_endExposed_prop=topBar_endExposed_prop,
                                             bottomBar_align=bottomBar_align,
                                             bottomBar_endCovered_prop=bottomBar_endCovered_prop,
                                             bottomBar_endExposed_prop=bottomBar_endExposed_prop,
                                             highlight_offFocus=highlight_prop[1])
        
        # To mimic a selection widget, 'IndicativeListbox' is wrapped in a 'urwid.BoxAdapter'. Since two rows are used for the bars,
        # size 3 makes exactly one list item visible.
        boxed_month_picker = urwid.BoxAdapter(self._month_picker, 3)
        boxed_day_picker = urwid.BoxAdapter(self._day_picker, 3)
        
        # Replace the 'DatePicker.PICKER' elements of the parameter 'columns' with the corresponding pickers.
        replacements = {DatePicker.PICKER.YEAR  : self._year_picker,
                        DatePicker.PICKER.MONTH : boxed_month_picker,
                        DatePicker.PICKER.DAY   : boxed_day_picker}
        
        columns = recursively_replace(columns, replacements)
        
        # wrap 'urwid.Columns'
        super().__init__(urwid.Columns(columns,
                                       min_width=min_width_each_picker,
                                       dividechars=space_between))
    
    def __repr__(self):
        return "{}(date='{}', date_range='{}', initial_date='{}-{:02}-{:02}')".format(self.__class__.__name__,
                                                                                      self.get_date(),
                                                                                      self._date_range,
                                                                                      self._initial_year,
                                                                                      self._initial_month,
                                                                                      self._initial_day)
    
    # The returned widget is used for all list entries.
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
        weekday, end = calendar.monthrange(year, month)         # end is included in the range
        
        # If the date range is 'ONLY_PAST', the last month does not end as usual but on the specified day.
        if (self._date_range == DatePicker.RANGE.ONLY_PAST) and (year == self._initial_year) and (month == self._initial_month):
            end = self._initial_day
        
        # If the date range is 'ONLY_FUTURE', the first month does not start as usual but on the specified day.
        elif (self._date_range == DatePicker.RANGE.ONLY_FUTURE) and (year == self._initial_year) and (month == self._initial_month):
            start = self._initial_day
            weekday = calendar.weekday(year, month, start)
        
        days = []
        
        for day in range(start, end+1):
            cols = []
            
            # The 'DatePicker.DAY_FORMAT' elements of the iterable are translated into columns of the day picker. This allows the
            # presentation to be customized.
            for df in self._day_format:
                if df == DatePicker.DAY_FORMAT.DAY_OF_MONTH:
                    cols.append(str(day))
                    
                elif df == DatePicker.DAY_FORMAT.DAY_OF_MONTH_TWO_DIGIT:
                    cols.append(str(day).zfill(2))
                    
                elif df == DatePicker.DAY_FORMAT.WEEKDAY:
                    cols.append(self._day_names[weekday])
                    
                else:
                    raise ValueError(_VALUE_ERR_MSG.format(df))
            
            item = self._generate_item(cols, align=self._day_align)
            
            # Add a new instance variable which holds the numerical value. This makes it easier to get the displayed value.
            item._numerical_value = day
            
            # Keeps track of the weekday.
            weekday = (weekday + 1) if (weekday < 6) else 0
            
            days.append(item)
        
        return days
    
    def _year_has_changed(self, previous_year, current_year):
        month_position_before_change = self._month_picker.get_selected_position()
        
        # Since there are no years in 'RANGE.ALL' that do not have the full month range, the body never needs to be changed after
        # initialization.
        if self._date_range != DatePicker.RANGE.ALL:
            # 'None' stands for trying to keep the old value.
            provisional_position = None
            
            # If the previous year was the specified year, the shortened month range must be replaced by the complete one. If this
            # shortened month range does not begin at 'January', then the difference must be taken into account.
            if previous_year == self._initial_year:
                if self._date_range == DatePicker.RANGE.ONLY_FUTURE:
                    provisional_position = self._month_picker.get_selected_item()._numerical_value - 1
                    
                self._month_picker.set_body(self._month_list,
                                            alternative_position=provisional_position)
            
            # If the specified year is selected, the full month range must be replaced with the shortened one.
            elif current_year == self._initial_year:
                if self._date_range == DatePicker.RANGE.ONLY_FUTURE:
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
        
        # Out of range values are changed by 'IndicativeListBox' to the nearest valid values.
        
        # If the date range is 'ONLY_FUTURE', it may be that a month does not start on the first day. In this case, the value must
        # be changed to reflect this difference.
        if self._date_range == DatePicker.RANGE.ONLY_FUTURE:
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
        
    def set_date(self, date):
        # If the date range is limited, test for the new limit.
        if self._date_range != DatePicker.RANGE.ALL:
            limit = datetime.date(self._initial_year, self._initial_month, self._initial_day)
            
            if (self._date_range == DatePicker.RANGE.ONLY_PAST) and (date > limit):
                raise ValueError("The passed date is outside the upper bound of the date range.")
            
            elif (self._date_range == DatePicker.RANGE.ONLY_FUTURE) and (date < limit):
                raise ValueError("The passed date is outside the lower bound of the date range.")
            
        year = date.year
        month = date.month
        day = date.day
        
        # Set the new values, if needed.
        if year != self._year_picker.get_value():
            self._year_picker.set_value(year)
        
        if month != self._month_picker.get_selected_item()._numerical_value:
            month_position = month - 1          # '-1' because it's an index.
            
            if (self._date_range == DatePicker.RANGE.ONLY_FUTURE) and (year == self._initial_year):
                # If the value should be negative, the behavior of 'IndicativeListBox' shows effect and position 0 is selected.
                month_position = month_position - (self._initial_month - 1)
            
            self._month_picker.select_item(month_position)
        
        if day != self._day_picker.get_selected_item()._numerical_value:
            day_position = day - 1              # '-1' because it's an index.
            
            if (self._date_range == DatePicker.RANGE.ONLY_FUTURE) and (year == self._initial_year) and (month == self._initial_month):
                day_position = day_position - (self._initial_day - 1)
            
            self._day_picker.select_item(day_position)


# Demonstration
if __name__ == "__main__":
    # Color schemes that specify the appearance off focus and in focus.
    PALETTE = [("reveal_focus",             "black",            "white"),
               ("dp_barActive_focus",       "light gray",       ""),
               ("dp_barActive_offFocus",    "black",            ""),
               ("dp_barInactive_focus",     "dark gray",        ""),
               ("dp_barInactive_offFocus",  "black",            ""),
               ("dp_placeholder_focus",     "",                 ""),
               ("dp_placeholder_offFocus",  "",                 ""),
               ("dp_highlight_focus",       "black",            "brown",   "standout"),
               ("dp_highlight_offFocus",    "white",            "black"),
               ("text_highlight",           "yellow,bold",      ""),
               ("text_bold",                "bold",             ""),
               ("text_esc",                 "light red,bold",   "")]
    
    date = datetime.date(2018, 10, 8)
    
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
    
    pickers = {"left":[], "right":[]}
    
    # Left columns
    left_heading = "default:"
    
    pickers["left"].append(DatePicker(date,
                                      highlight_prop=("reveal_focus", None)))
    
    pickers["left"].append(DatePicker(date,
                                      date_range=DatePicker.RANGE.ONLY_PAST,
                                      day_format=[DatePicker.DAY_FORMAT.DAY_OF_MONTH, DatePicker.DAY_FORMAT.WEEKDAY],
                                      highlight_prop=("reveal_focus", None)))
    
    pickers["left"].append(DatePicker(date,
                                      date_range=DatePicker.RANGE.ONLY_FUTURE,
                                      highlight_prop=("reveal_focus", None)))
    
    left_column = urwid.Pile([urwid.AttrMap(urwid.Text(left_heading, align="center"),
                                            "text_bold"),
                                            
                              urwid.Text("▔" * len(left_heading), align="center"),
                              
                              urwid.Text("all dates:"),
                              pickers["left"][0],
                              
                              urwid.Divider(" "),
                              
                              urwid.Text("only past:"),
                              pickers["left"][1],
                              
                              urwid.Divider(" "),
                              
                              urwid.Text("only future:"),
                              pickers["left"][2]])
    
    # Right
    right_heading = "additional parameters:"
    
    pickers["right"].append(DatePicker(date,
                                       day_format=[DatePicker.DAY_FORMAT.DAY_OF_MONTH_TWO_DIGIT],
                                       topBar_endCovered_prop=("ᐃ",  "dp_barActive_focus", "dp_barActive_off_focus"),
                                       topBar_endExposed_prop=("───", "dp_barInactive_focus", "dp_barInactive_off_focus"),
                                       bottomBar_endCovered_prop=("ᐁ",  "dp_barActive_focus", "dp_barActive_off_focus"),
                                       bottomBar_endExposed_prop=("───", "dp_barInactive_focus", "dp_barInactive_off_focus"),
                                       highlight_prop=("dp_highlight_focus", "dp_highlight_off_focus")))
    
    pickers["right"].append(DatePicker(date,
                                       date_range=DatePicker.RANGE.ONLY_PAST,
                                       day_format=[DatePicker.DAY_FORMAT.DAY_OF_MONTH],
                                       columns=(DatePicker.PICKER.MONTH, DatePicker.PICKER.DAY, DatePicker.PICKER.YEAR),
                                       topBar_endCovered_prop=("ᐃ",  "dp_barActive_focus", "dp_barActive_off_focus"),
                                       topBar_endExposed_prop=("───", "dp_barInactive_focus", "dp_barInactive_off_focus"),
                                       bottomBar_endCovered_prop=("ᐁ",  "dp_barActive_focus", "dp_barActive_off_focus"),
                                       bottomBar_endExposed_prop=("───", "dp_barInactive_focus", "dp_barInactive_off_focus"),
                                       highlight_prop=("dp_highlight_focus", "dp_highlight_off_focus")))
    
    pickers["right"].append(DatePicker(date,
                                       date_range=DatePicker.RANGE.ONLY_FUTURE,
                                       month_names=[str(i).zfill(2) for i in range(13)],
                                       day_format=[DatePicker.DAY_FORMAT.DAY_OF_MONTH],
                                       columns=((6, DatePicker.PICKER.YEAR), (4, DatePicker.PICKER.MONTH), (4, DatePicker.PICKER.DAY)),
                                       space_between=1,
                                       min_width_each_picker=4,
                                       topBar_endCovered_prop=("ᐃ",  "dp_barActive_focus", "dp_barActive_off_focus"),
                                       topBar_endExposed_prop=("───", "dp_barInactive_focus", "dp_barInactive_off_focus"),
                                       bottomBar_endCovered_prop=("ᐁ",  "dp_barActive_focus", "dp_barActive_off_focus"),
                                       bottomBar_endExposed_prop=("───", "dp_barInactive_focus", "dp_barInactive_off_focus"),
                                       highlight_prop=("dp_highlight_focus", "dp_highlight_off_focus")))
    
    right_column = urwid.Pile([urwid.AttrMap(urwid.Text(right_heading, align="center"),
                                             "text_bold"),
                                             
                               urwid.Text("▔" * len(right_heading), align="center"),
                               
                               urwid.Text("d-m-y, all dates:"),       
                               pickers["right"][0],
                               
                               urwid.Divider(" "),
                               
                               urwid.Text("m-d-y, only past:"),
                               pickers["right"][1],
                               
                               urwid.Divider(" "),
                               
                               urwid.Text("y-m-d, numerical, only future:"),
                               pickers["right"][2]])
    
    # Both
    columns = urwid.Columns([left_column, right_column],
                            dividechars=10)
    
    # Reset button
    def reset(btn):
        for col in pickers:
            for picker in pickers[col]:
                picker.set_date(date)

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
    
    def keypress(key):
        if key in ('q', 'Q', 'esc'):
            raise urwid.ExitMainLoop()
    
    loop = urwid.MainLoop(main_widget,
                          PALETTE,
                          unhandled_input=keypress)
    loop.run()
    
    for col in pickers:
        for i, picker in enumerate(pickers[col]):
            print("{} picker {}: {}".format(col, i+1, picker.get_date()))
    
