package main

import (
	"os"
	"os/exec"
	"strings"
	"testing"
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
	if labelFor(c, "caps", false, false, nil) != "1" {
		t.Fatal("caps")
	}
	if labelFor(c, "slots", false, false, nil) != "13" {
		t.Fatal("slots")
	}
	if labelFor(c, "binds", false, false, map[int]string{13: "F1"}) != "F1" {
		t.Fatal("binds")
	}
	if labelFor(c, "caps", true, false, nil) != "F1" {
		t.Fatal("fn legend")
	}
	q := Cell{Slot: 14, Cap: "Q"}
	if labelFor(q, "caps", true, false, nil) != "?" {
		t.Fatal("unknown fn should be ?")
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
