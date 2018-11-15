#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""Represents modifier keys such as 'ctrl', 'shift' and so on.
Not every combination of modifier and input is useful."""


import enum


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
    