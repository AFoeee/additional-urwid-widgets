#! /usr/bin/env python3
# -*- coding: utf-8 -*-


from additional_urwid_widgets.assisting_modules.modifier_key import MODIFIER_KEY
from additional_urwid_widgets.widgets.indicative_listbox import IndicativeListBox

import urwid 


# Iterable which holds the labels for the individual list entries.
ENTRIES = [str(i) for i in range(33)]

# Color schemes that specify the appearance off focus and on focus.
PALETTE = [("default",                   "",                 "black"),
           ("reveal_focus",              "black",            "light cyan",   "standout"),
           ("ilb_barActive_focus",       "dark cyan",        "light gray"),
           ("ilb_barActive_offFocus",    "light gray",       "dark gray"),
           ("ilb_barInactive_focus",     "light cyan",       "dark gray"),
           ("ilb_barInactive_offFocus",  "black",            "dark gray"),
           ("ilb_highlight_offFocus",    "black",            "dark cyan"),
           ("text_highlight",            "yellow,bold",      ""),
           ("text_bold",                 "bold",             ""),
           ("text_challenge",            "light green,bold", ""),
           ("text_esc",                  "light red,bold",   "")]

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

# Left column
left_heading = "default:"

left_list_body = urwid.SimpleListWalker([urwid.Button(entry)
                                         for entry in ENTRIES])

left_column = urwid.Pile([urwid.AttrMap(urwid.Text(left_heading, align="center"),
                                        "text_bold"),
                          
                          urwid.Text("▔" * len(left_heading),
                                     align="center"),
                          
                          urwid.Text("The default is impractical in a pile, because you also navigate with the arrow keys" 
                                     + " between the widgets."),
                          
                          urwid.Divider(" "),
                          
                          urwid.Button("some button"),
                          
                          # Left list box, wrapped in a 'urwid.BoxAdapter' to limit the extent.
                          urwid.BoxAdapter(IndicativeListBox(left_list_body),
                                           6),
                          
                          urwid.Button("another button")])

# Right column
right_heading = "with additional parameters:"

right_list_body = urwid.SimpleListWalker([urwid.AttrMap(urwid.Button(entry), "default", "reveal_focus")
                                          for entry in ENTRIES])

right_column = urwid.Pile([urwid.AttrMap(urwid.Text(right_heading, align="center"),
                                         "text_bold"),
                          
                           urwid.Text("▔" * len(right_heading),
                                      align="center"),
                          
                           urwid.Text(["This list box responds only if you additionally press ",
                                       ("text_highlight", "ctrl"),
                                       "."]),
                          
                            urwid.Divider(" "),
                          
                            urwid.Button("some button"),
                          
                            # Right list box, wrapped in a 'urwid.BoxAdapter' to limit the extent.
                            urwid.BoxAdapter(IndicativeListBox(right_list_body,
                                                               modifier_key=MODIFIER_KEY.CTRL,
                                                               return_unused_navigation_input=False,
                                                               topBar_endCovered_prop=("{} more",
                                                                                       "ilb_barActive_focus",
                                                                                       "ilb_barActive_offFocus"),
                                                               topBar_endExposed_prop=("───",
                                                                                       "ilb_barInactive_focus",
                                                                                       "ilb_barInactive_offFocus"),
                                                               bottomBar_endCovered_prop=("{} more",
                                                                                          "ilb_barActive_focus",
                                                                                          "ilb_barActive_offFocus"), 
                                                               bottomBar_endExposed_prop=("───",
                                                                                          "ilb_barInactive_focus",
                                                                                          "ilb_barInactive_offFocus"),
                                                               highlight_offFocus="ilb_highlight_offFocus"),
                                             6),
                            
                            urwid.Button("another button")])

# Both columns
columns = urwid.Columns([left_column, right_column],
                        dividechars=5)

# Emphasize why 'MODIFIER_KEY' is needed.
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

def keypress(key):
    if key in ('q', 'Q', 'esc'):
        raise urwid.ExitMainLoop()

loop = urwid.MainLoop(main_widget,
                      PALETTE,
                      unhandled_input=keypress)
loop.run()
