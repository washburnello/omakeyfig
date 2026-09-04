package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
)

// Remap screen: cursor the board, filter the action catalog, assign,
// review the diff, undo, and push through the confirm gate.

type undoEntry struct {
	slot int
	prev *int // nil = was base value
}

type remapSt struct {
	hasCursor bool
	row, col  int
	focusFilt bool
	filter    string
	filtered  []Action
	listIx    int
	pending   map[int]int
	history   []undoEntry
	confirm   bool
	status    string
	base      map[int]int
}

func newRemap(doc *Export) *remapSt {
	r := &remapSt{pending: map[int]int{}, base: map[int]int{}}
	for s, fw := range doc.Defaults {
		var slot int
		fmt.Sscanf(s, "%d", &slot)
		r.base[slot] = fw
	}
	r.filtered = doc.Actions
	return r
}

func filterActions(actions []Action, q string) []Action {
	q = strings.ToLower(strings.TrimSpace(q))
	if q == "" {
		return actions
	}
	var out []Action
	for _, a := range actions {
		if strings.Contains(strings.ToLower(a.Label), q) ||
			strings.Contains(strings.ToLower(a.Category), q) {
			out = append(out, a)
		}
	}
	return out
}

func (r *remapSt) cursorSlot(rows [][]Cell) (int, bool) {
	if !r.hasCursor || r.row < 0 || r.row >= len(rows) {
		return 0, false
	}
	if r.col < 0 || r.col >= len(rows[r.row]) {
		return 0, false
	}
	return rows[r.row][r.col].Slot, true
}

func (r *remapSt) effective(slot int) int {
	if fw, ok := r.pending[slot]; ok {
		return fw
	}
	return r.base[slot]
}

func (r *remapSt) assign(slot, fw int) {
	prev, had := r.pending[slot]
	if had {
		cp := prev
		r.history = append(r.history, undoEntry{slot, &cp})
	} else {
		r.history = append(r.history, undoEntry{slot, nil})
	}
	r.pending[slot] = fw
	if r.pending[slot] == r.base[slot] {
		delete(r.pending, slot)
	}
}

func (r *remapSt) undo() {
	if len(r.history) == 0 {
		return
	}
	e := r.history[len(r.history)-1]
	r.history = r.history[:len(r.history)-1]
	if e.prev == nil {
		delete(r.pending, e.slot)
	} else {
		r.pending[e.slot] = *e.prev
	}
	if fw, ok := r.pending[e.slot]; ok && fw == r.base[e.slot] {
		delete(r.pending, e.slot)
	}
}

func (r *remapSt) fullMap() map[int]int {
	out := map[int]int{}
	for s, fw := range r.base {
		out[s] = fw
	}
	for s, fw := range r.pending {
		out[s] = fw
	}
	return out
}

func diffLines(doc *Export, base, pending map[int]int) []string {
	fwLabel := map[int]string{}
	for _, a := range doc.Actions {
		if _, ok := fwLabel[a.Fw]; !ok {
			fwLabel[a.Fw] = a.Label
		}
	}
	lab := func(fw int) string {
		if l, ok := fwLabel[fw]; ok {
			return l
		}
		return fmt.Sprintf("%#x", fw)
	}
	slots := []int{}
	for s := range pending {
		slots = append(slots, s)
	}
	sortInts(slots)
	lines := []string{}
	for _, s := range slots {
		lines = append(lines, fmt.Sprintf("slot %d: %s -> %s", s, lab(base[s]), lab(pending[s])))
	}
	return lines
}

func sortInts(xs []int) {
	for i := 1; i < len(xs); i++ {
		for j := i; j > 0 && xs[j] < xs[j-1]; j-- {
			xs[j], xs[j-1] = xs[j-1], xs[j]
		}
	}
}

func (m *model) updateRemap(k string) (tea.Model, tea.Cmd) {
	r := m.remap
	if r == nil {
		return m, nil
	}
	if r.confirm {
		switch k {
		case "y", "Y", "enter":
			return m, m.pushRemap()
		default:
			r.confirm = false
			return m, nil
		}
	}
	if r.focusFilt {
		switch k {
		case "esc":
			r.focusFilt = false
			return m, nil
		case "backspace":
			if len(r.filter) > 0 {
				r.filter = r.filter[:len(r.filter)-1]
				r.filtered = filterActions(m.doc.Actions, r.filter)
				r.listIx = 0
			}
			return m, nil
		case "enter":
			if len(r.filtered) > 0 && r.listIx < len(r.filtered) {
				if slot, ok := r.cursorSlot(m.doc.Rows); ok {
					r.assign(slot, r.filtered[r.listIx].Fw)
					r.status = fmt.Sprintf("slot %d -> %s (%d pending)",
						slot, r.filtered[r.listIx].Label, len(r.pending))
				} else {
					r.status = "cursor a board key first"
				}
			}
			return m, nil
		case "up":
			if r.listIx > 0 {
				r.listIx--
			}
			return m, nil
		case "down":
			if r.listIx < len(r.filtered)-1 {
				r.listIx++
			}
			return m, nil
		}
		if len(k) == 1 {
			r.filter += k
			r.filtered = filterActions(m.doc.Actions, r.filter)
			r.listIx = 0
		}
		return m, nil
	}
	switch k {
	case "esc":
		m.screen = sMenu
	case "left", "h":
		m.moveRemapCursor(-1, 0)
	case "right", "l":
		m.moveRemapCursor(1, 0)
	case "up", "k":
		m.moveRemapCursor(0, -1)
	case "down", "j":
		m.moveRemapCursor(0, 1)
	case "enter":
		r.focusFilt = true
	case "u":
		r.undo()
		r.status = fmt.Sprintf("undo (%d pending)", len(r.pending))
	case "ctrl+s":
		if len(r.pending) == 0 {
			r.status = "nothing to push"
		} else {
			r.confirm = true
		}
	}
	return m, nil
}

type pushedMsg struct {
	err error
	text string
}

func (m *model) pushRemap() tea.Cmd {
	r := m.remap
	full := r.fullMap()
	payload := map[string]map[string]int{"mappings": {}}
	for s, fw := range full {
		payload["mappings"][itoa(s)] = fw
	}
	data, _ := json.Marshal(payload)
	tmp, err := os.CreateTemp("", "omakeyfig-map-*.json")
	if err != nil {
		r.confirm = false
		r.status = "temp file failed: " + err.Error()
		return nil
	}
	tmpName := tmp.Name()
	tmp.Write(data)
	tmp.Close()
	return func() tea.Msg {
		defer os.Remove(tmpName)
		out, err := runBackend(m.back, "write-map", "--mapping-file", tmpName, "--yes")
		if err != nil {
			return pushedMsg{err, ""}
		}
		return pushedMsg{nil, out}
	}
}

// moveRemapCursor mirrors Python: the first move initializes the cursor
// (row 0, or last row for upward moves) instead of stepping.
func (m *model) moveRemapCursor(dx, dy int) {
	r := m.remap
	if !r.hasCursor {
		if dy < 0 {
			r.row = len(m.doc.Rows) - 1
		} else {
			r.row = 0
		}
		r.col = 0
		r.hasCursor = true
		return
	}
	r.row, r.col = moveCursor(m.doc.Rows, r.row, r.col, dx, dy)
}

func (m *model) viewRemap() string {
	r := m.remap
	var b strings.Builder
	b.WriteString("cursor a key · enter filter · type to filter · enter assigns · u undo · ctrl+s push\n\n")
	sel := map[int]bool{}
	if slot, ok := r.cursorSlot(m.doc.Rows); ok {
		sel[slot] = true
		b.WriteString(fmt.Sprintf("selected slot %d: %s\n\n", slot, bindLabel(m.doc, r.effective(slot))))
	} else {
		b.WriteString("selected: none (move with hjkl/arrows)\n\n")
	}
	binds := map[int]string{}
	full := r.fullMap()
	for s, fw := range full {
		binds[s] = bindLabel(m.doc, fw)
	}
	b.WriteString(renderBoard(m.th, m.doc.Rows, "binds", false, false, binds, sel))
	b.WriteString("\nfilter: " + r.filter + "\n")
	shown := r.filtered
	if len(shown) > 12 {
		shown = shown[:12]
	}
	for i, a := range shown {
		mark := "  "
		if r.focusFilt && i == r.listIx {
			mark = "▸ "
		}
		b.WriteString(fmt.Sprintf("%s%s  [%s]\n", mark, a.Label, a.Category))
	}
	lines := diffLines(m.doc, r.base, r.pending)
	if len(lines) > 0 {
		b.WriteString("\npending:\n")
		for _, l := range lines {
			if len(l) > 200 {
				continue
			}
			b.WriteString("  " + l + "\n")
		}
	}
	if r.status != "" {
		b.WriteString("\n" + r.status + "\n")
	}
	if r.confirm {
		box := "Push " + itoa(len(lines)) + " change(s) to the keyboard?\nFirmware is write-only.\n\n[y] write   [n] cancel"
		return b.String() + "\n" + m.th.box.Render(box) + "\n"
	}
	return b.String()
}

func bindLabel(doc *Export, fw int) string {
	for _, a := range doc.Actions {
		if a.Fw == fw {
			return a.Label
		}
	}
	return fmt.Sprintf("%#x", fw)
}
