# additional_urwid_widgets

The python library [`urwid`](http://urwid.org/index.html) contains many basic widgets, but lacks (in my opinion) of "more specialized" widgets, such as a date picker.

This project provides such "more specialized" widgets.  

***

## Installation
The project can be installed via [pip](https://pypi.org/project/additional-urwid-widgets/).

### Options
There are several approaches to install a package via the terminal (as discribed [here](https://github.com/googlesamples/assistant-sdk-python/issues/236#issuecomment-383039470)):
*  Setup a virtual env to install the package (**recommended**):  

        python3 venv env
        source ./env/bin/activate 
        python3 -m pip install additional-urwid-widgets
    
* Install the package to the user folder:  

        python3 -m pip install --user additional-urwid-widgets
    
* Install to the system folder (**not recommended**):  

        python3 -m pip install additional-urwid-widgets

***

## Widgets

See the corresponding wiki entries of the widgets for more information.

* [**DatePicker**](https://github.com/AFoeee/additional_urwid_widgets/wiki/DatePicker)  
A (rudimentary) date picker.

* [**IndicativeListBox**](https://github.com/AFoeee/additional_urwid_widgets/wiki/IndicativeListBox)  
A [`urwid.ListBox`](http://urwid.org/reference/widget.html#listbox) with additional bars to indicate hidden list items.

* [**IntegerPicker**](https://github.com/AFoeee/additional_urwid_widgets/wiki/IntegerPicker)  
A selector for integer numbers.

* [**MessageDialog**](https://github.com/AFoeee/additional_urwid_widgets/wiki/MessageDialog)  
Wraps [`urwid.Overlay`](http://urwid.org/reference/widget.html#overlay) to show a message and expects a reaction from the user.

* [**SelectableRow**](https://github.com/AFoeee/additional_urwid_widgets/wiki/SelectableRow)  
Wraps [`urwid.Columns`](http://urwid.org/reference/widget.html#columns) to make it selectable and adds behavior.
