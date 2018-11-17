#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""Wraps 'urwid.ListBox' to add bars that indicate that only a part of the list is visible."""


from ..assisting_modules.modifier_key import MODIFIER_KEY        # pylint: disable=unused-import

import enum
import random
import urwid


class IndicativeListBox(urwid.WidgetWrap):
    _TYPE_ERR_MSG = "type {} was expected for {}, but found: {}."
    _VALUE_ERR_MSG = "unrecognized value: {}."

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
        
        if (modified_size[0] < 1) or (modified_size[1] < 1):
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
                raise ValueError(IndicativeListBox._VALUE_ERR_MSG.format(position))
            
        else:
            raise TypeError(IndicativeListBox._TYPE_ERR_MSG.format("<class 'int'> or <enum 'IndicativeListBox.POSITION'>",
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
