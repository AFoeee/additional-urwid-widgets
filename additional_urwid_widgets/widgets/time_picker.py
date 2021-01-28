#! /usr/bin/env python3
# -*- coding: utf-8 -*-


# pylint: disable=unused-import
from ..assisting_modules.modifier_key import MODIFIER_KEY
from ..assisting_modules.useful_functions import recursively_replace
from .indicative_listbox import IndicativeListBox
from .integer_picker import IntegerPicker
from .selectable_row import SelectableRow

import calendar
from datetime import datetime
import enum
import urwid


class TimePicker(urwid.WidgetWrap):
    """Serves as a selector for time."""
    
    _TYPE_ERR_MSG = "type {} was expected for {}, but found: {}."
    _VALUE_ERR_MSG = "unrecognized value: {}."

    # These values are interpreted during the initialization and define
    # the arrangement of the pickers.
    class PICKER(enum.Enum):
        HOUR = 1
        MINUTE = 2
        SECOND = 3

    # Specifies which timestamps are selectable.
    class RANGE(enum.Enum):
        ALL = 1
        ONLY_PAST = 2
        ONLY_FUTURE = 3

    def __init__(self, initial_time=datetime.today(), *, time_range=RANGE.ALL,
                 columns=(PICKER.HOUR, PICKER.MINUTE, PICKER.SECOND),
                 return_unused_navigation_input=False,
                 modifier_key=MODIFIER_KEY.CTRL, hour_jump_len=2,
                 space_between=2, min_width_each_picker=9, hour_align="center",
                 minute_align="center", second_align="center",
                 topBar_align="center", bottomBar_align="center",
                 topBar_endCovered_prop=("▲", None, None),
                 topBar_endExposed_prop=("───", None, None),
                 bottomBar_endCovered_prop=("▼", None, None),
                 bottomBar_endExposed_prop=("───", None, None),
                 highlight_prop=(None, None)):

        assert (type(time_range) == self.__class__.RANGE), (
          self.__class__._TYPE_ERR_MSG.format("<enum 'TimePicker.RANGE'>",
                                              "'time_range'", type(time_range))
          )

        # Relevant for 'RANGE.ONLY_PAST' and 'RANGE.ONLY_FUTURE' to limit
        # the respective choices.
        self._initial_hour = initial_time.hour
        self._initial_minute = initial_time.minute
        self._initial_second = initial_time.second
        
        # The time pool can be limited, so that only past or future times
        # are selectable. The initial time is included in the pool.
        self._time_range = time_range

        # Specifies the text alignment of the individual pickers. The hour
        # alignment is passed directly to the hour picker.
        self._minute_align = minute_align
        self._second_align = second_align
        
        # The default style of a list entry. Since only one list entry will
        # be visible at a time and there is also off focus  highlighting,
        # the normal value can be 'None' (it is never shown).
        self._item_attr = (None, highlight_prop[0])
        
        # A full list of minutes. (From '0' to '59'.)
        self._minute_list = self._generate_minutes()
        
        # Set the respective values depending on the time range.
        min_hour = 0
        max_hour = 23
        
        minute_position = self._initial_minute
        second_position = self._initial_second
        
        if time_range == self.__class__.RANGE.ALL:
            initial_minute_list = self._minute_list
            
        elif time_range == self.__class__.RANGE.ONLY_PAST:
            max_hour = self._initial_hour
            
            # The minutes of the very last hour may be shorten.
            self._shortened_minute_list = self._generate_minutes(
              end=self._initial_minute
            )
            initial_minute_list = self._shortened_minute_list
            
        elif time_range == self.__class__.RANGE.ONLY_FUTURE:
            min_hour = self._initial_hour
            
            # The minutes of the very first hour may be shorten.
            self._shortened_minute_list = self._generate_minutes(
              start=self._initial_minute
            )
            initial_minute_list = self._shortened_minute_list
            
            # The list may not start at 1 but some other second of
            # minute, therefore use the first list item.
            minute_position = 0
            second_position = 0
            
        else:
            raise ValueError(self.__class__._VALUE_ERR_MSG.format(time_range))
        
        # Create pickers.
        self._hour_picker = IntegerPicker(
          self._initial_hour,
          min_v=min_hour,
          max_v=max_hour,
          jump_len=hour_jump_len,
          modifier_key=modifier_key,
          return_unused_navigation_input=return_unused_navigation_input,
          topBar_align=topBar_align,
          topBar_endCovered_prop=topBar_endCovered_prop,
          topBar_endExposed_prop=topBar_endExposed_prop,
          bottomBar_align=bottomBar_align,
          bottomBar_endCovered_prop=bottomBar_endCovered_prop,
          bottomBar_endExposed_prop=bottomBar_endExposed_prop,
          display_syntax="{:02}",
          display_align=hour_align,
          display_prop=highlight_prop
        )
        
        self._minute_picker = IndicativeListBox(
          initial_minute_list,
          position=minute_position,
          modifier_key=modifier_key,
          return_unused_navigation_input=return_unused_navigation_input,
          topBar_align=topBar_align,
          topBar_endCovered_prop=topBar_endCovered_prop,
          topBar_endExposed_prop=topBar_endExposed_prop,
          bottomBar_align=bottomBar_align,
          bottomBar_endCovered_prop=bottomBar_endCovered_prop,
          bottomBar_endExposed_prop=bottomBar_endExposed_prop,
          highlight_offFocus=highlight_prop[1]
        )
        
        self._second_picker = IndicativeListBox(
          self._generate_seconds(self._initial_hour, self._initial_minute),
          position=second_position,
          modifier_key=modifier_key,
          return_unused_navigation_input=return_unused_navigation_input,
          topBar_align=topBar_align,
          topBar_endCovered_prop=topBar_endCovered_prop,
          topBar_endExposed_prop=topBar_endExposed_prop,
          bottomBar_align=bottomBar_align,
          bottomBar_endCovered_prop=bottomBar_endCovered_prop,
          bottomBar_endExposed_prop=bottomBar_endExposed_prop,
          highlight_offFocus=highlight_prop[1]
        )
        
        # To mimic a selection widget, 'IndicativeListbox' is wrapped
        # in a 'urwid.BoxAdapter'. Since two rows are used for the bars,
        # size 3 makes exactly one list item visible.
        boxed_minute_picker = urwid.BoxAdapter(self._minute_picker, 3)
        boxed_second_picker = urwid.BoxAdapter(self._second_picker, 3)
        
        # Replace the 'TimePicker.PICKER' elements of the parameter
        # 'columns' with the corresponding pickers.
        replacements = {self.__class__.PICKER.HOUR   : self._hour_picker,
                        self.__class__.PICKER.MINUTE : boxed_minute_picker,
                        self.__class__.PICKER.SECOND : boxed_second_picker}
        
        columns = recursively_replace(columns, replacements)
        
        # wrap 'urwid.Columns'
        super().__init__(urwid.Columns(columns,
                                       min_width=min_width_each_picker,
                                       dividechars=space_between))
    
    def __repr__(self):
        return (
          "{}(time='{}', time_range='{}', initial_time='{:02}-{:02}-{:02}',"\
          " selected_time='{}')".format(self.__class__.__name__,
                                        self.get_time(),
                                        self._time_range,
                                        self._initial_hour,
                                        self._initial_minute,
                                        self._initial_second,
                                        self.get_time())
        )
    
    # The returned widget is used for all list entries.
    def _generate_item(self, cols, *, align="center"):
        return urwid.AttrMap(SelectableRow(cols, align=align),
                             self._item_attr[0],
                             self._item_attr[1])
    
    def _generate_minutes(self, start=0, end=59):
        minutes = []
        
        for minute in range(start, end+1):
            item = self._generate_item([str(minute)], align=self._minute_align)
            
            # Add a new instance variable which holds the numerical value.
            # This makes it easier to get the displayed value.
            item._numerical_value = minute

            minutes.append(item)

        return minutes
    
    def _generate_seconds(self, hour, minute):
        start, end = 0, 59

        # If the time range is 'ONLY_PAST', the last minute does not end as
        # usual but on the specified second.
        if ((self._time_range == self.__class__.RANGE.ONLY_PAST) and
            (hour == self._initial_hour) and
            (minute == self._initial_minute)):
            end = self._initial_second
        
        # If the time range is 'ONLY_FUTURE', the first minute does not start
        # as usual but on the specified second.
        elif ((self._time_range == self.__class__.RANGE.ONLY_FUTURE) and
              (hour == self._initial_hour) and
              (minute == self._initial_minute)):
            start = self._initial_second
        
        seconds = []
        
        for second in range(start, end+1):
            item = self._generate_item([str(second)], align=self._second_align)
            
            # Add a new instance variable which holds the numerical value. This
            # makes it easier to get the displayed value.
            item._numerical_value = second
            
            seconds.append(item)
        
        return seconds
        
    def get_time(self):
        return datetime.time(datetime(*[
          datetime.today().year,
          datetime.today().month,
          datetime.today().day,
          self._hour_picker.get_value(),
          self._minute_picker.get_selected_item()._numerical_value,
          self._second_picker.get_selected_item()._numerical_value,
        ]))

    def set_time(self, time):
        # If the time range is limited, test for the new limit.
        if self._time_range != self.__class__.RANGE.ALL:
            limit = datetime.time(datetime(*[
              datetime.today().year,
              datetime.today().month,
              datetime.today().day,
              self._initial_hour,
              self._initial_minute,
              self._initial_second,
            ]))
            
            if ((self._time_range == self.__class__.RANGE.ONLY_PAST) and
                (time > limit)):
                raise ValueError("The passed time is outside the upper bound "\
                                 "of the time range.")
            
            elif ((self._time_range == self.__class__.RANGE.ONLY_FUTURE) and
                  (time < limit)):
                raise ValueError("The passed time is outside the lower bound "\
                                 "of the time range.")
            
        hour = time.hour
        minute = time.minute
        second = time.second
        
        # Set the new values, if needed.
        if hour != self._hour_picker.get_value():
            self._hour_picker.set_value(hour)
        
        if minute != self._minute_picker.get_selected_item()._numerical_value:
            minute_position = minute - 1          # '-1' because it's an index.
            
            if ((self._time_range == self.__class__.RANGE.ONLY_FUTURE) and
                (hour == self._initial_hour)):
                # If the value should be negative, the behavior of 
                # 'IndicativeListBox' shows effect and position 0 is selected.
                minute_position = minute_position - (self._initial_minute - 1)
            
            self._minute_picker.select_item(minute_position)
        
        if second != self._second_picker.get_selected_item()._numerical_value:
            second_position = second - 1          # '-1' because it's an index.
            
            if ((self._time_range == self.__class__.RANGE.ONLY_FUTURE) and
                (hour == self._initial_hour) and
                (minute == self._initial_minute)):
                second_position = second_position - (self._initial_second - 1)
            
            self._second_picker.select_item(second_position)
