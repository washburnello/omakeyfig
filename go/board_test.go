package main

import (
	tea "github.com/charmbracelet/bubbletea"
	"os"
	"os/exec"
	"strings"
	"testing"
	"time"

	zone "github.com/lrstanley/bubblezone"
)

func strp(s string) *string { return &s }

func testRows() [][]Cell {
	return [][]Cell{
		{
			{Slot: 14, Label: "Q", Cap: "Q", X: 0, Cells: 4, Char: strp("q"), Names: []string{"q"}},
			{Slot: 35, Label: "Space", Cap: "Space", X: 10, Cells: 15, Char: nil, Names: []string{"space"}},
			{Slot: 13, Label: "1", Cap: "1", X: 30, Cells: 4, Char: strp("1"), Names: []string{"1"}, Fn: strp("F1")},
		},
	}
}

func TestMatchSlots(t *testing.T) {
	rows := testRows()
	if got := matchSlots(rows, "q"); !eq(got, []int{14}) {
		t.Fatalf("q -> %v", got)
	}
	if got := matchSlots(rows, "Q"); !eq(got, []int{14}) {
		t.Fatalf("Q -> %v", got)
	}
	if got := matchSlots(rows, "!"); !eq(got, []int{13}) {
		t.Fatalf("! -> %v (want shifted 1)", got)
	}
	if got := matchSlots(rows, " "); !eq(got, []int{35}) {
		t.Fatalf("space -> %v", got)
	}
	if got := matchSlots(rows, "f12"); len(got) != 0 {
		t.Fatalf("f12 should match nothing here, got %v", got)
	}
}

func eq(a, b []int) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func TestLabelFor(t *testing.T) {
	c := Cell{Slot: 13, Label: "1", Cap: "1", Fn: strp("F1")}
	if labelFor(c, "caps", false, nil) != "1" {
		t.Fatal("caps")
	}
	if labelFor(c, "slots", false, nil) != "13" {
		t.Fatal("slots")
	}
	if labelFor(c, "binds", false, map[int]string{13: "F1"}) != "F1" {
		t.Fatal("binds")
	}
	// fn legends render as sub-rows, never as label swaps
	if labelFor(c, "caps", false, nil) != "1" {
		t.Fatal("base label stays under fn view")
	}
}

func TestLegendSubRows(t *testing.T) {
	rows := testRows() // slot 13 has Fn F1
	off := renderBoard(defaultTheme(), rows, "caps", false, false, nil, map[int]bool{})
	on := renderBoard(defaultTheme(), rows, "caps", true, false, nil, map[int]bool{})
	if strings.Count(on, "\n") != strings.Count(off, "\n")+1 {
		t.Fatalf("fn view should add exactly one legend line:\n%s", on)
	}
	if !strings.Contains(on, "F1") {
		t.Fatalf("legend line missing F1:\n%s", on)
	}
}

func TestRenderBoard(t *testing.T) {
	out := renderBoard(defaultTheme(), testRows(), "caps", false, false, nil, map[int]bool{14: true})
	if !strings.Contains(out, "Q") || !strings.Contains(out, "Space") {
		t.Fatalf("missing labels:\n%s", out)
	}
	if !strings.Contains(out, "─") || !strings.Contains(out, "│") {
		t.Fatalf("missing borders:\n%s", out)
	}
	lines := strings.Split(strings.TrimRight(out, "\n"), "\n")
	if len(lines) != 3 {
		t.Fatalf("want 3 lines for 1 bordered row, got %d:\n%s", len(lines), out)
	}
}

// TestLiveExport exercises the real Python backend end to end.
func TestLiveExport(t *testing.T) {
	back, err := exec.LookPath("omakeyfig")
	if err != nil {
		if p := os.Getenv("OMAKEYFIG_BACKEND"); p != "" {
			back = p
		} else {
			t.Skip("no omakeyfig backend on PATH")
		}
	}
	doc, err := loadExport(back)
	if err != nil {
		t.Fatalf("export: %v", err)
	}
	n := 0
	for _, r := range doc.Rows {
		n += len(r)
	}
	if n != 74 {
		t.Fatalf("want 74 cells, got %d", n)
	}
	if got := matchSlots(doc.Rows, "q"); !eq(got, []int{14}) {
		t.Fatalf("live q -> %v", got)
	}
	if got := matchSlots(doc.Rows, " "); !eq(got, []int{35, 53}) {
		t.Fatalf("live space -> %v", got)
	}
	out := renderBoard(defaultTheme(), doc.Rows, "slots", false, false, nil, map[int]bool{})
	// narrow keys truncate ("101" won't fit a 4-cell key); check fittable ones
	for _, want := range []string{"14", "35", "1"} {
		if !strings.Contains(out, want) {
			t.Fatalf("slots view missing %s", want)
		}
	}
}

func TestZoneHelpers(t *testing.T) {
	if s, ok := parseSlotZone("slot-14"); !ok || s != 14 {
		t.Fatalf("parse slot-14 -> %d,%v", s, ok)
	}
	if _, ok := parseSlotZone("menu-2"); ok {
		t.Fatal("menu-2 must not parse as slot")
	}
	rows := testRows()
	if ri, ci, ok := findCell(rows, 35); !ok || ri != 0 || ci != 1 {
		t.Fatalf("findCell 35 -> %d,%d,%v", ri, ci, ok)
	}
	if _, _, ok := findCell(rows, 999); ok {
		t.Fatal("findCell 999 should miss")
	}
	out := renderBoard(defaultTheme(), rows, "caps", false, false, nil, map[int]bool{})
	if !strings.Contains(out, "Q") {
		t.Fatal("rendered board lost labels")
	}
	// Scan registers zones asynchronously; poll until they land.
	zone.Scan(out)
	var zi *zone.ZoneInfo
	for i := 0; i < 200; i++ {
		zi = zone.Get("slot-14")
		if zi != nil && !zi.IsZero() {
			break
		}
		time.Sleep(10 * time.Millisecond)
	}
	if zi == nil || zi.IsZero() {
		t.Fatal("slot-14 zone never registered")
	}
	if zi.EndX <= zi.StartX || zi.EndY < zi.StartY {
		t.Fatalf("bogus zone geometry %+v", zi)
	}
}

func waitZone(t *testing.T, id string) *zone.ZoneInfo {
	t.Helper()
	var zi *zone.ZoneInfo
	for i := 0; i < 200; i++ {
		zi = zone.Get(id)
		if zi != nil && !zi.IsZero() {
			return zi
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Fatalf("zone %s never registered", id)
	return nil
}

func clickAt(zi *zone.ZoneInfo) tea.MouseMsg {
	return tea.MouseMsg{
		X:      (zi.StartX + zi.EndX) / 2,
		Y:      (zi.StartY + zi.EndY) / 2,
		Action: tea.MouseActionPress,
		Button: tea.MouseButtonLeft,
	}
}

func TestMouseClickTester(t *testing.T) {
	doc := fakeDoc()
	m := newModel("true", doc)
	m.screen = sTester
	m.View() // View() scans zones internally; do NOT scan twice (second scan wipes)
	zi := waitZone(t, "slot-14")
	mm, _ := m.updateMouse(clickAt(zi))
	m = mm.(model)
	if !m.pressed[14] {
		t.Fatal("click should light slot 14")
	}
}

func TestMouseClickRemapMovesCursor(t *testing.T) {
	doc := fakeDoc()
	m := newModel("true", doc)
	m.screen = sRemap
	m.remap = newRemap(doc)
	m.View() // View() scans zones internally; do NOT scan twice (second scan wipes)
	zi := waitZone(t, "slot-14")
	mm, _ := m.updateMouse(clickAt(zi))
	m = mm.(model)
	if !m.remap.hasCursor {
		t.Fatal("click should place cursor")
	}
	slot, ok := m.remap.cursorSlot(doc.Rows)
	if !ok || slot != 14 {
		t.Fatalf("cursor -> %d,%v", slot, ok)
	}
}

func TestMouseClickMenu(t *testing.T) {
	doc := fakeDoc()
	m := newModel("true", doc)
	m.screen = sMenu
	m.View() // View() scans zones internally; do NOT scan twice (second scan wipes)
	zi := waitZone(t, "menu-1")
	mm, _ := m.updateMouse(clickAt(zi))
	m = mm.(model)
	if m.screen != sTester {
		t.Fatalf("menu click should open tester, at %v", m.screen)
	}
}
