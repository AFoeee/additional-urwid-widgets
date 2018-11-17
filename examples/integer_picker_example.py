#! /usr/bin/env python3
# -*- coding: utf-8 -*-


from additional_urwid_widgets.assisting_modules.modifier_key import MODIFIER_KEY
from additional_urwid_widgets.widgets.integer_picker import IntegerPicker

import urwid 


# Color schemes that specify the appearance off focus and on focus.
PALETTE = [("reveal_focus",              "black",             "white"),
           ("ip_display_focus",          "black",             "brown",   "standout"),
           ("ip_display_offFocus",       "white",             "black"),
           ("ip_barActive_focus",        "light gray",        ""),
           ("ip_barActive_offFocus",     "black",             ""),
           ("ip_barInactive_focus",      "dark gray",         ""),
           ("ip_barInactive_offFocus",   "black",             ""),
           ("text_highlight",            "yellow,bold",       ""),
           ("text_lowlight",             "dark gray",         ""),
           ("text_bold",                 "bold",              ""),
           ("text_note",                 "light green,bold",  ""),
           ("text_esc",                  "light red,bold",    "")]

# Navigation instructions
text_arrow_keys = urwid.Text([("text_highlight", "↑"),
                              " or ",
                              ("text_highlight", "↓"),
                              " to move one step_len."])

text_pages = urwid.Text([("text_highlight", "page up"),
                         " or ",
                         ("text_highlight", "page down"),
                         " to move one jump_len."])

text_home_end = urwid.Text([("text_highlight", "home"),
                            " or ",
                            ("text_highlight", "end"),
                            " to jump to the corresponding end."])

# Left Column
left_heading = "default:"

left_col = urwid.Pile([urwid.AttrMap(urwid.Text(left_heading, align="center"),
                                     "text_bold"),
                       
                       urwid.Text("▔" * len(left_heading), align="center"),
                       
                       IntegerPicker(0,
                                     display_prop=("reveal_focus", None)),
                       
                       urwid.AttrMap(urwid.Button("Try to reach this button..."),
                                     "",
                                     "reveal_focus")])

# Middle Column
middle_heading = "descending:"

middle_col = urwid.Pile([urwid.AttrMap(urwid.Text(middle_heading, align="center"),
                                      "text_bold"),
                         
                         urwid.Text("▔" * len(middle_heading), align="center"),
                         
                         IntegerPicker(0,
                                       step_len=5,
                                       jump_len=33,
                                       ascending=False,
                                       display_syntax="{:,}",
                                       display_prop=("reveal_focus", None)),
                         
                         urwid.AttrMap(urwid.Button("Button"),
                                       "",
                                       "reveal_focus"),
                         
                         urwid.Divider(" "),
                         
                         urwid.AttrMap(urwid.Text("step_len=5, jump_len=33"),
                                       "text_lowlight")])

# Right Column
right_heading = "additional parameters:"

right_button = urwid.AttrMap(urwid.Button("Button"),
                             "",
                             "reveal_focus")

right_additional_text = urwid.AttrMap(urwid.Text("press additionally 'ctrl'"),
                                      "text_lowlight")

right_col = urwid.Pile([urwid.AttrMap(urwid.Text(right_heading, align="center"),
                                      "text_bold"),
                                      
                        urwid.Text("▔" * len(right_heading), align="center"),
                        
                        IntegerPicker(2018,
                                      min_v=1,
                                      max_v=9999,
                                      modifier_key=MODIFIER_KEY.CTRL,
                                      return_unused_navigation_input=False,
                                      topBar_endCovered_prop=("ᐃ", "ip_barActive_focus", "ip_barActive_offFocus"),
                                      topBar_endExposed_prop=("───", "ip_barInactive_focus", "ip_barInactive_offFocus"),
                                      bottomBar_endCovered_prop=("ᐁ", "ip_barActive_focus", "ip_barActive_offFocus"),
                                      bottomBar_endExposed_prop=("───", "ip_barInactive_focus", "ip_barInactive_offFocus"),
                                      display_prop=("ip_display_focus", "ip_display_offFocus")),
                        
                        right_button,
                        
                        urwid.Divider(" "),
                        
                        right_additional_text])

# All Columns
columns = urwid.Columns([left_col, middle_col, right_col],
                        dividechars=2)

# Explain the behavior of the widgets.
text_note = urwid.Text("The first two pickers do not use a 'MODIFIER_KEY'. In the examples above, the arrow keys are used for"
                       + " two things: to select the values and to navigate between the widgets. This means that the button"
                       + " below the picker can only be selected when the picker does pass the keystroke on (after the"
                       + " minimum/maximum is reached). \nThe right picker escapes that by only responding to modified navigation"
                       + " input.")

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
                
                   urwid.AttrMap(text_note, "text_note"),
                
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
