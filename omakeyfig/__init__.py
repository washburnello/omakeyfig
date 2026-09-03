"""omakeyfig: unofficial TUI customizer for Royal Kludge keyboards (S70-first).

Unofficial project, not affiliated with Royal Kludge or Omarchy.
Protocol knowledge derived from reverse engineering by the Rangoli project
and the KludgeKnight web app (both GPL-licensed); this project is GPL-3.0-or-later.
"""

__version__ = "0.1.0"

VID_ROYAL_KLUDGE = 0x258A
PID_S70 = 0x0220
# S70 regional variants share the layout.
PID_S70_VARIANTS = {0x0220, 0x0229, 0x01D9, 0x00D7}
