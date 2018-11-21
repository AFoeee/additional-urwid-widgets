#! /usr/bin/env python3
# -*- coding: utf-8 -*-


from additional_urwid_widgets.widgets.date_picker import DatePicker
from additional_urwid_widgets.widgets.selectable_row import SelectableRow

import datetime
import urwid


# Color schemes that specify the appearance off focus and on focus.
PALETTE = [("reveal_focus",             "black",            "white"),
           ("dp_barActive_focus",       "light gray",       ""),
           ("dp_barActive_offFocus",    "black",            ""),
           ("dp_barInactive_focus",     "dark gray",        ""),
           ("dp_barInactive_offFocus",  "black",            ""),
           ("dp_highlight_focus",       "black",            "brown",   "standout"),
           ("dp_highlight_offFocus",    "white",            "black"),
           ("text_highlight",           "yellow,bold",      ""),
           ("text_bold",                "bold",             ""),
           ("text_esc",                 "light red,bold",   "")]

date = datetime.date(2018, 11, 15)

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

# Left column
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

# Right column
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

# Both columns
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
            