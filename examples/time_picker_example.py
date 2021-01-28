#! /usr/bin/env python3
# -*- coding: utf-8 -*-


from additional_urwid_widgets.widgets.time_picker import TimePicker
from additional_urwid_widgets.widgets.selectable_row import SelectableRow

from datetime import datetime
import urwid


# Color schemes that specify the appearance off focus and on focus.
PALETTE = [("reveal_focus",             "black",            "white"),
           ("tp_barActive_focus",       "light gray",       ""),
           ("tp_barActive_offFocus",    "black",            ""),
           ("tp_barInactive_focus",     "dark gray",        ""),
           ("tp_barInactive_offFocus",  "black",            ""),
           ("tp_highlight_focus",       "black",            "brown",
            "standout"),
           ("tp_highlight_offFocus",    "white",            "black"),
           ("text_highlight",           "yellow,bold",      ""),
           ("text_bold",                "bold",             ""),
           ("text_esc",                 "light red,bold",   "")]

time = datetime.time(datetime(*[2021, 1, 28, 1, 2, 3]))

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

pickers["left"].append(TimePicker(time,
                                  highlight_prop=("reveal_focus", None)))

pickers["left"].append(TimePicker(time,
                                  time_range=TimePicker.RANGE.ONLY_PAST,
                                  highlight_prop=("reveal_focus", None)))

pickers["left"].append(TimePicker(time,
                                  time_range=TimePicker.RANGE.ONLY_FUTURE,
                                  highlight_prop=("reveal_focus", None)))

left_column = urwid.Pile([urwid.AttrMap(urwid.Text(left_heading, align="center"),
                                        "text_bold"),
                                        
                          urwid.Text("▔" * len(left_heading), align="center"),
                          
                          urwid.Text("all times:"),
                          pickers["left"][0],
                          
                          urwid.Divider(" "),
                          
                          urwid.Text("only past:"),
                          pickers["left"][1],
                          
                          urwid.Divider(" "),
                          
                          urwid.Text("only future:"),
                          pickers["left"][2]])

# Right column
right_heading = "additional parameters:"

pickers["right"].append(TimePicker(time,
                                   topBar_endCovered_prop=(
                                    "ᐃ", "tp_barActive_focus",
                                    "tp_barActive_off_focus"),
                                   topBar_endExposed_prop=(
                                    "───", "tp_barInactive_focus",
                                    "tp_barInactive_off_focus"),
                                   bottomBar_endCovered_prop=(
                                    "ᐁ", "tp_barActive_focus",
                                    "tp_barActive_off_focus"),
                                   bottomBar_endExposed_prop=(
                                    "───", "tp_barInactive_focus",
                                    "tp_barInactive_off_focus"),
                                   highlight_prop=(
                                    "tp_highlight_focus",
                                    "tp_highlight_off_focus")))

pickers["right"].append(TimePicker(time,
                                   time_range=TimePicker.RANGE.ONLY_PAST,
                                   columns=(TimePicker.PICKER.MINUTE,
                                            TimePicker.PICKER.SECOND,
                                            TimePicker.PICKER.HOUR),
                                   topBar_endCovered_prop=(
                                    "ᐃ", "tp_barActive_focus",
                                    "tp_barActive_off_focus"),
                                   topBar_endExposed_prop=(
                                    "───", "tp_barInactive_focus",
                                    "tp_barInactive_off_focus"),
                                   bottomBar_endCovered_prop=(
                                    "ᐁ", "tp_barActive_focus",
                                    "tp_barActive_off_focus"),
                                   bottomBar_endExposed_prop=(
                                    "───", "tp_barInactive_focus",
                                    "tp_barInactive_off_focus"),
                                   highlight_prop=(
                                    "tp_highlight_focus",
                                    "tp_highlight_off_focus")))

pickers["right"].append(TimePicker(time,
                                   time_range=TimePicker.RANGE.ONLY_FUTURE,
                                   columns=((4, TimePicker.PICKER.HOUR),
                                            (4, TimePicker.PICKER.MINUTE),
                                            (4, TimePicker.PICKER.SECOND)),
                                   space_between=1,
                                   min_width_each_picker=4,
                                   topBar_endCovered_prop=(
                                    "ᐃ", "tp_barActive_focus",
                                    "tp_barActive_off_focus"),
                                   topBar_endExposed_prop=(
                                    "───", "tp_barInactive_focus",
                                    "tp_barInactive_off_focus"),
                                   bottomBar_endCovered_prop=(
                                    "ᐁ", "tp_barActive_focus",
                                    "tp_barActive_off_focus"),
                                   bottomBar_endExposed_prop=(
                                    "───", "tp_barInactive_focus",
                                    "tp_barInactive_off_focus"),
                                   highlight_prop=(
                                    "tp_highlight_focus",
                                    "tp_highlight_off_focus")))

right_column = urwid.Pile([urwid.AttrMap(urwid.Text(right_heading, align="center"),
                                         "text_bold"),
                                         
                           urwid.Text("▔" * len(right_heading), align="center"),
                           
                           urwid.Text("h-m-s, all times:"),       
                           pickers["right"][0],
                           
                           urwid.Divider(" "),
                           
                           urwid.Text("m-s-h, only past:"),
                           pickers["right"][1],
                           
                           urwid.Divider(" "),
                           
                           urwid.Text("h-m-s, numerical, only future:"),
                           pickers["right"][2]])

# Both columns
columns = urwid.Columns([left_column, right_column],
                        dividechars=10)

# Reset button
def reset(btn):
    for col in pickers:
        for picker in pickers[col]:
            picker.set_time(time)

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
        print("{} picker {}: {}".format(col, i+1, picker.get_time()))
