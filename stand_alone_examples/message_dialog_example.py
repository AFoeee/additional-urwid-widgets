#! /usr/bin/env python3
# -*- coding: utf-8 -*-


import enum
import random
import urwid


class MODIFIER_KEY(enum.Enum):
    """Represents modifier keys such as 'ctrl', 'shift' and so on.
    Not every combination of modifier and input is useful."""

    NONE = ""
    SHIFT = "shift"
    ALT = "meta"
    CTRL = "ctrl"
    SHIFT_ALT = "shift meta"
    SHIFT_CTRL = "shift ctrl"
    ALT_CTRL = "meta ctrl"
    SHIFT_ALT_CTRL = "shift meta ctrl"
    
    def append_to(self, text, separator=" "):
        return (text + separator + self.value) if (self != self.__class__.NONE) else text
    
    def prepend_to(self, text, separator=" "):
        return (self.value + separator + text) if (self != self.__class__.NONE) else text


class SelectableRow(urwid.WidgetWrap):
    """Wraps 'urwid.Columns' to make it selectable.
    This class has been slightly modified, but essentially corresponds to this class posted on stackoverflow.com:
    https://stackoverflow.com/questions/52106244/how-do-you-combine-multiple-tui-forms-to-write-more-complex-applications#answer-52174629"""

    def __init__(self, contents, *, align="left", on_select=None):
        # A list-like object, where each element represents the value of a column.
        self.contents = contents
        
        self._columns = urwid.Columns([urwid.Text(c, align=align) 
                                       for c in contents])
        
        # Wrap 'urwid.Columns'.
        super().__init__(self._columns)
        
        # A hook which defines the behavior that is executed when a specified key is pressed.
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
    """Adds two bars to a 'urwid.ListBox', that make it obvious that due to limited space only a part of the list items is displayed."""

    _TYPE_ERR_MSG = "type {} was expected for {}, but found: {}."
    _VALUE_ERR_MSG = "unrecognized value: {}."

    # These values are translated by 'get_nearest_valid_position()' into the corresponding int values.
    class POSITION(enum.Enum):
        LAST = 1
        MIDDLE = 2
        RANDOM = 3
        
    def __init__(self, body, *, position=0, on_selection_change=None, initialization_is_selection_change=False,
                 modifier_key=MODIFIER_KEY.NONE, return_unused_navigation_input=True, topBar_align="center",
                 topBar_endCovered_prop=("▲", None, None), topBar_endExposed_prop=("───", None, None), bottomBar_align="center",
                 bottomBar_endCovered_prop=("▼", None, None), bottomBar_endExposed_prop=("───", None, None), highlight_offFocus=None):
        # If not already done, wrap each item of the body in an 'urwid.AttrMap'. This is necessary to enable off focus highlighting.
        body[:] = [urwid.AttrMap(item, None) if not isinstance(item, urwid.AttrMap) else item
                   for item in body]
        
        # The body of the 'urwid.Frame' is a 'urwid.ListBox'.
        self._listbox = urwid.ListBox(body)
        
        # Select the specified list position, or the nearest valid one.
        nearest_valid_position = self._get_nearest_valid_position(position)
        
        if nearest_valid_position is not None:
            self._listbox.set_focus(nearest_valid_position)
        
        # The bars are just 'urwid.Text' widgets.
        self._top_bar = urwid.AttrMap(urwid.Text("", align=topBar_align),
                                      None)
        
        self._bottom_bar = urwid.AttrMap(urwid.Text("", align=bottomBar_align),
                                         None)
        
        # Wrap 'urwid.Frame'.
        super().__init__(urwid.Frame(self._listbox,
                                     header=self._top_bar,
                                     footer=self._bottom_bar,
                                     focus_part="body"))
        
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
        
        # A hook which is triggered when the selection changes.
        self.on_selection_change = on_selection_change
        
        # Initialization can be seen as a special case of selection change. This is interesting in combination with the hook.
        self._initialization_is_selection_change = initialization_is_selection_change
        
        # 'MODIFIER_KEY' changes the behavior of the list box, so that it responds only to modified input. ('up' => 'ctrl up')
        self._modifier_key = modifier_key
        
        # If the list item at the top is selected and you navigate further upwards, the input is normally not swallowed by the
        # list box, but passed on so that other widgets can interpret it. This may result in transferring the focus.
        self._return_unused_navigation_input = return_unused_navigation_input
        
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
        
        # Evaluates which ends are visible and calculates how many list entries are hidden above/below. This is a modified form
        # of 'urwid.ListBox.ends_visible()'.
        middle, top, bottom = self._listbox.calculate_visible(modified_size, focus=focus)
        
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
                
                if self._listbox._body.get_prev(pos) == (None,None):
                    top_is_visible = True
                else:
                    covered_above = pos
            else:
                covered_above = self.rearmost_position()
            
            if trim_bottom == 0:
                row_offset, _, pos, rows, _ = middle
                
                row_offset += rows              # Include the selected position.
                
                for _, pos, rows in below:      # 'pos' is overridden
                    row_offset += rows
                    
                if (row_offset < modified_size[1]) or (self._listbox._body.get_next(pos) == (None, None)):
                    bottom_is_visible = True
                else:
                    covered_below = self.rearmost_position() - pos
            else:
                covered_below = self.rearmost_position()
        
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
        
        # The highlighting in urwid is bound to the focus. This means that the selected item is only distinguishable as long as
        # the widget has the focus. To compensate this, the color scheme of the selected item is otherwiese temporarily changed.
        if focus and not self._last_focus_state and (self._original_item_attr_map is not None):
            # Resets the appearance of the selected item to its original value.
            self._listbox.focus.set_attr_map(self._original_item_attr_map)
            
        elif (self._highlight_offFocus is not None) \
                    and not focus \
                    and (self._last_focus_state or (self._last_focus_state is None)) \
                    and not self.body_is_empty():
            # Store the 'attr_map' of the selected item and then change it to accomplish off focus highlighting.
            self._original_item_attr_map = self._listbox.focus.get_attr_map()
            self._listbox.focus.set_attr_map(self._highlight_offFocus)
        
        # Store the last focus to do/undo the off focus highlighting only if the focus has really changed and not if the
        # widget is re-rendered because the terminal size has changed or similar.
        self._last_focus_state = focus
        
        return super().render(size, focus=focus)
    
    def keypress(self, size, key):
        just_maxcol = (size[0],)
        
        # The size also includes the two bars, so subtract these.
        modified_size = (size[0],                                                                           # cols
                         size[1] - self._top_bar.rows(just_maxcol) - self._bottom_bar.rows(just_maxcol))    # rows
        
        # Store the focus position before passing the keystroke to the contained list box. That way, it can be compared with the 
        # position after the input is processed. If the list box body is empty, store None.
        focus_position_before_input = self.get_selected_position()
        
        # A keystroke is changed to a modified one ('up' => 'ctrl up'). This prevents the widget from responding when the arrows
        # keys are used to navigate between widgets. That way it can be used in a 'urwid.Pile' or similar.
        if key == self._modifier_key.prepend_to("up"):
            key = self._pass_key_to_contained_listbox(modified_size, "up")
            
        elif key == self._modifier_key.prepend_to("down"):
            key = self._pass_key_to_contained_listbox(modified_size, "down")
            
        elif key == self._modifier_key.prepend_to("page up"):
            key = self._pass_key_to_contained_listbox(modified_size, "page up")
            
        elif key == self._modifier_key.prepend_to("page down"):
            key = self._pass_key_to_contained_listbox(modified_size, "page down")
            
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
                
        elif key not in ("up", "down", "page up", "page down", "home", "end"):
            key = self._listbox.keypress(modified_size, key)
        
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
        
        # An event is changed to a modified one ('mouse press' => 'ctrl mouse press'). This prevents the widget from responding
        # when mouse buttons are also used to navigate between widgets.
        if event == self._modifier_key.prepend_to("mouse press"):
            # Store the focus position before passing the input to the contained list box. That way, it can be compared with the 
            # position after the input is processed. If the list box body is empty, store None.
            focus_position_before_input = self.get_selected_position()
            
            # left mouse button, if not top bar or bottom bar.
            if (button == 1.0) and (topBar_rows <= row < (size[1] - bottomBar_rows)):
                # Because 'row' includes the top bar, the offset must be substracted before passing it to the contained list box.
                result = self._listbox.mouse_event(modified_size, event, button, col, (row - topBar_rows), focus)
                was_handeled = result if self._return_unused_navigation_input else True
            
            # mousewheel up
            elif button == 4.0:
                was_handeled = self._pass_key_to_contained_listbox(modified_size, "page up")
                
            # mousewheel down
            elif button == 5.0:
                was_handeled = self._pass_key_to_contained_listbox(modified_size, "page down")
                
            focus_position_after_input = self.get_selected_position()
            
            # If the focus position has changed, execute the hook (if existing).
            if (focus_position_before_input != focus_position_after_input) and (self.on_selection_change is not None):
                self.on_selection_change(focus_position_before_input,
                                         focus_position_after_input)
        
        return was_handeled
    
    # Pass the keystroke to the original widget. If it is not used, evaluate the corresponding variable to decide if it gets
    # swallowed or not.
    def _pass_key_to_contained_listbox(self, size, key):
        result = self._listbox.keypress(size, key)
        return result if self._return_unused_navigation_input else None
    
    def get_body(self):
        return self._listbox.body
    
    def body_len(self):
        return len(self.get_body())
    
    def rearmost_position(self):
        return len(self.get_body()) - 1           # last valid index
    
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
            
        elif pos_type == self.__class__.POSITION:
            if position == self.__class__.POSITION.LAST:
                return self.rearmost_position()
                
            elif position == self.__class__.POSITION.MIDDLE:
                return self.body_len() // 2
                
            elif position == self.__class__.POSITION.RANDOM:
                return random.randint(0, self.rearmost_position())
                
            else:
                raise ValueError(self.__class__._VALUE_ERR_MSG.format(position))
            
        else:
            raise TypeError(self.__class__._TYPE_ERR_MSG.format("<class 'int'> or <enum 'IndicativeListBox.POSITION'>",
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
        return self._listbox.focus
    
    def get_selected_position(self):
        return self._listbox.focus_position if not self.body_is_empty() else None
    
    def first_item_is_selected(self):
        return self.get_selected_position() == 0
    
    def last_item_is_selected(self):
        return self.get_selected_position() == self.rearmost_position()
    
    def _reset_highlighting(self):
        # Resets the appearance of the selected item to its original value, if off focus highlighting is active.
        if not self._last_focus_state and (self._original_item_attr_map is not None):
            self._listbox.focus.set_attr_map(self._original_item_attr_map)
        
        # The next time the widget is rendered, the highlighting is redone.
        self._original_item_attr_map = None
        self._last_focus_state = None
    
    def set_body(self, body, *, alternative_position=None):
        focus_position_before_change = self.get_selected_position()
        
        self._reset_highlighting()
        
        # Wrap each item in an 'urwid.AttrMap', if not already done.
        self._listbox.body[:] = [urwid.AttrMap(item, None) if not isinstance(item, urwid.AttrMap) else item
                                 for item in body]
        
        # Normally it is tried to hold the focus position. If this is not desired, a position can be passed.
        if alternative_position is not None:
            nearest_valid_position = self._get_nearest_valid_position(alternative_position)
            
            if nearest_valid_position is not None:
                # Because the widget has been re-rendered, the off focus highlighted item must be restored to its original state.
                self._reset_highlighting()
                
                self._listbox.set_focus(nearest_valid_position)
        
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
            
            self._listbox.set_focus(nearest_valid_position)
            
            # Execute the hook (if existing).
            if (self.on_selection_change is not None):
                self.on_selection_change(focus_position_before_change,
                                         nearest_valid_position)
    
    def select_first_item(self):
        self.select_item(0)
        
    def select_last_item(self):
        self.select_item(self.rearmost_position())
    
    def delete_position(self, position):
        # The saved properties get reseted, just in case that the appearance of the items differs.
        self._reset_highlighting()

        body = self.get_body()
        del body[position]
        
    def delete_selected_position(self):
        pos = self.get_selected_position()
        
        # If the list body is not empty, delete the selected item.
        if pos is not None:
            self.delete_position(pos)


class MessageDialog(urwid.WidgetWrap):
    """Wraps 'urwid.Overlay' to show a message and expects a reaction from the user."""
    
    def __init__(self, contents, btns, overlay_size, *, contents_align="left", space_between_btns=2, title="", title_align="center",
                 background=urwid.SolidFill("#"), overlay_align=("center", "middle"), overlay_min_size=(None, None), left=0, right=0,
                 top=0, bottom=0):
        # Message part
        texts = [urwid.Text(content, align=contents_align)
                 for content in contents]
        
        # Lower part
        lower_part = [urwid.Divider(" "),
                      urwid.Columns(btns, dividechars=space_between_btns)]
        
        # frame 
        line_box = urwid.LineBox(urwid.Pile(texts + lower_part),
                                 title=title,
                                 title_align=title_align)
        
        # Wrap 'urwid.Overlay'
        super().__init__(urwid.Overlay(urwid.Filler(line_box),
                                       background,
                                       overlay_align[0],
                                       overlay_size[0],
                                       overlay_align[1],
                                       overlay_size[1],
                                       min_width=overlay_min_size[0],
                                       min_height=overlay_min_size[1],
                                       left=left,
                                       right=right,
                                       top=top,
                                       bottom=bottom))


# Demonstration
if __name__ == "__main__":
    # Iterable which holds the individual list entries.
    ENTRIES = [[c + str(i)
                for c in ("a", "b", "c")]
                for i in range(33)]
    
    # Color schemes that specify the appearance.
    PALETTE = [
        ("important",      "light cyan",     ""),
        ("highlight",      "black",          "white"),
        ("text_highlight", "yellow,bold",    ""),
        ("text_esc",       "light red,bold", ""),
    ]
    
    # Defines how to deal with unhandled input.
    def keypress(key):
        if key in ("q", "Q", "esc"):
            raise urwid.ExitMainLoop()
    
    # instructions
    text_arrow_keys = urwid.Text([("text_highlight", "↑"),
                                  " or ",
                                  ("text_highlight", "↓"),
                                  " to move one line."])
    
    text_selection = urwid.Text([("text_highlight", "ENTER"),
                                 " to select an entry."])
    
    text_esc = urwid.Text([("text_esc", "Q"),
                           " or ",
                           ("text_esc", "Esc"),
                           " to quit."])
    
    # Main
    main_widget = urwid.Frame(IndicativeListBox([]),
                              
                              header=urwid.Pile([text_arrow_keys,
                                                 text_selection,
                                                 urwid.Divider("─")]),
                              
                              footer=urwid.Pile([urwid.Divider("─"),
                                                 text_esc]))
    
    loop = urwid.MainLoop(main_widget,
                          palette=PALETTE,
                          unhandled_input=keypress)
    
    # Back to original view
    def show_main(key):
        loop.widget = main_widget
        
    # Show detailed view
    def show_details(row):
        contents = []
        for i,col in enumerate(row.contents):
            contents.append(["column {}:     ".format(i+1),
                             ("important", col)])
        
        btns = [urwid.Button("back", on_press=show_main)]
        
        loop.widget = MessageDialog(contents,
                                    btns,
                                    (30, 7),
                                    title="Detailed View",
                                    background=main_widget)
    
    # The change of views is triggered by the selected list item.
    rows = [SelectableRow(entry, on_select=show_details)
            for entry in ENTRIES]
    
    main_widget.body.set_body([urwid.AttrMap(row, "", "highlight")
                       for row in rows])
    
    loop.run()