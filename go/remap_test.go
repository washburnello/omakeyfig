package main

import (
	"testing"

	tea "github.com/charmbracelet/bubbletea"
)

func remapTestRows() [][]Cell {
	return [][]Cell{
		{
			{Slot: 1, X: 0, Cells: 4, Names: []string{"m1"}},
			{Slot: 7, X: 5, Cells: 4, Names: []string{"esc", "escape"}},
			{Slot: 13, X: 10, Cells: 4, Char: strp("1"), Names: []string{"1"}, Fn: strp("F1")},
		},
		{
			{Slot: 2, X: 0, Cells: 4, Names: []string{"m2"}},
			{Slot: 8, X: 5, Cells: 8, Names: []string{"tab"}},
			{Slot: 14, X: 14, Cells: 4, Char: strp("q"), Names: []string{"q"}},
		},
	}
}

func TestMoveCursor(t *testing.T) {
	rows := remapTestRows()
	r, c := moveCursor(rows, -1, 0, 0, 1)
	if r != 0 || c != 0 {
		t.Fatalf("init down -> %d,%d", r, c)
	}
	r, c = moveCursor(rows, 0, 0, 1, 0)
	if r != 0 || c != 1 {
		t.Fatalf("right -> %d,%d", r, c)
	}
	r, c = moveCursor(rows, 0, 2, -100, 0)
	if r != 0 || c != 0 {
		t.Fatalf("clamp left -> %d,%d", r, c)
	}
	// from slot 13 (x-center 12) move down: row1 centers 2, 9, 16 -> nearest 9 (slot 8)
	r, c = moveCursor(rows, 0, 2, 0, 1)
	if r != 1 || c != 1 {
		t.Fatalf("down snap -> %d,%d want 1,1", r, c)
	}
	// from slot 7 (x-center 7) move down -> nearest row1 center 9 (slot 8)
	r, c = moveCursor(rows, 0, 1, 0, 1)
	if r != 1 || c != 1 {
		t.Fatalf("down snap2 -> %d,%d want 1,1", r, c)
	}
	r, c = moveCursor(rows, 1, 0, 0, 1)
	if r != 1 || c != 0 {
		t.Fatalf("clamp bottom -> %d,%d", r, c)
	}
}

func fakeDoc() *Export {
	return &Export{
		Rows: remapTestRows(),
		Actions: []Action{
			{Aid: 0x51, Label: "Q", Category: "Letters", Fw: 0x1400},
			{Aid: 0xAF, Label: "Volume Up", Category: "Media", Fw: 0x010000E9},
		},
		Defaults: map[string]int{"14": 0x1400, "13": 0x1E00},
	}
}

func TestFilterAssignUndo(t *testing.T) {
	doc := fakeDoc()
	r := newRemap(doc)
	if got := filterActions(doc.Actions, "vol"); len(got) != 1 || got[0].Label != "Volume Up" {
		t.Fatalf("filter vol -> %v", got)
	}
	if got := filterActions(doc.Actions, ""); len(got) != 2 {
		t.Fatalf("empty filter -> %d", len(got))
	}
	r.row, r.col, r.hasCursor = 1, 2, true
	slot, ok := r.cursorSlot(doc.Rows)
	if !ok || slot != 14 {
		t.Fatalf("cursor -> %d,%v", slot, ok)
	}
	r.assign(14, 0x010000E9)
	if r.pending[14] != 0x010000E9 {
		t.Fatalf("pending %v", r.pending)
	}
	lines := diffLines(doc, r.base, r.pending)
	if len(lines) != 1 || lines[0] != "slot 14: Q -> Volume Up" {
		t.Fatalf("diff %v", lines)
	}
	r.undo()
	if len(r.pending) != 0 {
		t.Fatalf("after undo %v", r.pending)
	}
	// assigning the base value is a no-op
	r.assign(14, 0x1400)
	if len(r.pending) != 0 {
		t.Fatalf("base assign should clear, got %v", r.pending)
	}
}

func TestFullMap(t *testing.T) {
	doc := fakeDoc()
	r := newRemap(doc)
	r.assign(14, 0x010000E9)
	full := r.fullMap()
	if full[14] != 0x010000E9 || full[13] != 0x1E00 {
		t.Fatalf("full %v", full)
	}
}

func keyMsg(s string) tea.KeyMsg {
	// Bubble Tea key messages in tests: construct via KeyMsg struct.
	return tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune(s)}
}

func TestRemapScreenFlow(t *testing.T) {
	doc := fakeDoc()
	m := newModel("true", doc)
	m.screen = sRemap
	m.remap = newRemap(doc)
	// move cursor right onto slot 7 via keys
	mm, _ := m.updateRemap("l")
	m = *mm.(*model)
	if m.remap.row != 0 || m.remap.col != 0 {
		t.Fatalf("first move should init cursor, got %d,%d", m.remap.row, m.remap.col)
	}
	// filter + assign through the UI path
	mm, _ = m.updateRemap("enter") // focus filter
	m = *mm.(*model)
	if !m.remap.focusFilt {
		t.Fatal("filter not focused")
	}
	for _, ch := range []string{"v", "o", "l"} {
		mm, _ = m.updateRemap(ch)
		m = *mm.(*model)
	}
	if len(m.remap.filtered) != 1 {
		t.Fatalf("filtered %v", m.remap.filtered)
	}
}
