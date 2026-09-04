package main

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
	zone "github.com/lrstanley/bubblezone"
)

// Board rendering + key matching. Lip Gloss borders sit OUTSIDE the box,
// so inner width = cells-2 to approximate the Python board geometry.

var shifted = map[string]string{
	"!": "1", "@": "2", "#": "3", "$": "4", "%": "5", "^": "6",
	"&": "7", "*": "8", "(": "9", ")": "0", "_": "-", "+": "=",
	"{": "[", "}": "]", "|": "\\", ":": ";", `"`: "'", "<": ",",
	">": ".", "?": "/", "~": "`",
}

func matchSlots(rows [][]Cell, key string) []int {
	var hits []int
	k := key
	if k == " " {
		k = "space"
	}
	if len(k) == 1 {
		ch := strings.ToLower(k)
		if mapped, ok := shifted[ch]; ok {
			ch = mapped
		}
		for _, row := range rows {
			for _, c := range row {
				if c.Char != nil && strings.ToLower(*c.Char) == ch {
					hits = append(hits, c.Slot)
				}
			}
		}
		if len(hits) > 0 {
			return hits
		}
	}
	want := strings.ToLower(k)
	for _, row := range rows {
		for _, c := range row {
			for _, n := range c.Names {
				if n == want {
					hits = append(hits, c.Slot)
					break
				}
			}
		}
	}
	return hits
}

// findCell locates a slot's row/col for cursor jumps (mouse clicks).
func findCell(rows [][]Cell, slot int) (int, int, bool) {
	for ri, row := range rows {
		for ci, c := range row {
			if c.Slot == slot {
				return ri, ci, true
			}
		}
	}
	return 0, 0, false
}

// parseSlotZone extracts a slot from a "slot-N" zone id.
func parseSlotZone(id string) (int, bool) {
	var slot int
	if _, err := fmt.Sscanf(id, "slot-%d", &slot); err != nil {
		return 0, false
	}
	return slot, true
}

func itoa(i int) string {
	if i == 0 {
		return "0"
	}
	neg := i < 0
	if neg {
		i = -i
	}
	var b [16]byte
	p := len(b)
	for i > 0 {
		p--
		b[p] = byte('0' + i%10)
		i /= 10
	}
	if neg {
		p--
		b[p] = '-'
	}
	return string(b[p:])
}

// labelFor resolves what a cell shows under the current view/fn state.
// Plain text only (ANSI would break Lip Gloss width measurement).
func labelFor(c Cell, view string, fnView, fshiftView bool, binds map[int]string) string {
	if fnView {
		if fshiftView && c.FshiftFn != nil {
			return *c.FshiftFn
		}
		if c.Fn != nil {
			return *c.Fn
		}
		return "?"
	}
	if fshiftView && c.Fshift != nil {
		return *c.Fshift
	}
	switch view {
	case "slots":
		return itoa(c.Slot)
	case "binds":
		if b, ok := binds[c.Slot]; ok {
			return b
		}
		return "?"
	default: // caps
		return c.Cap
	}
}

func renderBoard(th theme, rows [][]Cell, view string, fnView, fshiftView bool,
	binds map[int]string, pressed map[int]bool) string {
	var sb strings.Builder
	for _, row := range rows {
		var lines [3]string
		cursor := 0
		for _, c := range row {
			gap := ""
			if c.X > cursor {
				gap = strings.Repeat(" ", c.X-cursor)
			}
			inner := c.Cells - 2
			if inner < 1 {
				inner = 1
			}
			st := th.key
			if pressed[c.Slot] {
				st = th.pressed
			}
			block := zone.Mark(fmt.Sprintf("slot-%d", c.Slot),
				st.Width(inner).Height(1).Render(
					fit(labelFor(c, view, fnView, fshiftView, binds), inner)))
			cell := strings.Split(block, "\n")
			for len(cell) < 3 {
				cell = append(cell, "")
			}
			for i := 0; i < 3; i++ {
				lines[i] += gap + cell[i]
			}
			cursor = c.X + c.Cells
		}
		for i := 0; i < 3; i++ {
			sb.WriteString(strings.TrimRight(lines[i], " ") + "\n")
		}
	}
	return sb.String()
}

// fit centers via Lip Gloss; pre-truncate labels wider than the cell.
func fit(s string, w int) string {
	r := []rune(s)
	if len(r) <= w {
		return s
	}
	return string(r[:w])
}

type theme struct {
	key     lipgloss.Style
	pressed lipgloss.Style
	title   lipgloss.Style
	help    lipgloss.Style
	sel     lipgloss.Style
	box     lipgloss.Style
}

func defaultTheme() theme {
	key := lipgloss.NewStyle().
		Border(lipgloss.NormalBorder(), true, true, true, true).
		BorderForeground(lipgloss.Color("#3f8f8a")).
		Foreground(lipgloss.Color("#f6dcac")).
		Background(lipgloss.Color("#0a2540")).
		Align(lipgloss.Center, lipgloss.Center)
	pressed := key.Copy().
		Background(lipgloss.Color("#ffffff")).
		Foreground(lipgloss.Color("#000000"))
	return theme{
		key:     key,
		pressed: pressed,
		title:   lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#faa968")),
		help:    lipgloss.NewStyle().Foreground(lipgloss.Color("#8cbfb8")),
		sel:     lipgloss.NewStyle().Reverse(true),
		box:     lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(1, 2),
	}
}
