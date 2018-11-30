#! /usr/bin/env python3
# -*- coding: utf-8 -*-


from additional_urwid_widgets.widgets.indicative_listbox import IndicativeListBox
from additional_urwid_widgets.widgets.message_dialog import MessageDialog
from additional_urwid_widgets.widgets.selectable_row import SelectableRow

import urwid 


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
