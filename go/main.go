// Command omakeyfig-go is a Bubble Tea + Lip Gloss frontend for omakeyfig.
//
// It shells out to the Python backend (`omakeyfig` on PATH, or
// OMAKEYFIG_BACKEND) for all protocol work: `export` feeds the UI,
// `light`/`write-map`/profiles commands perform writes. No HID code lives
// here by design — see field-guide.md in the repo root.
package main

import (
	"fmt"
	"os"
	"os/exec"

	tea "github.com/charmbracelet/bubbletea"
	zone "github.com/lrstanley/bubblezone"
)

func backendPath() (string, error) {
	if p := os.Getenv("OMAKEYFIG_BACKEND"); p != "" {
		return p, nil
	}
	if p, err := exec.LookPath("omakeyfig"); err == nil {
		return p, nil
	}
	return "", fmt.Errorf("no omakeyfig backend found (set OMAKEYFIG_BACKEND or put omakeyfig on PATH)")
}

func main() {
	back, err := backendPath()
	if err != nil {
		fmt.Fprintln(os.Stderr, "omakeyfig-go:", err)
		os.Exit(2)
	}
	doc, err := loadExport(back)
	if err != nil {
		fmt.Fprintln(os.Stderr, "omakeyfig-go: backend export failed:", err)
		os.Exit(1)
	}
	m := newModel(back, doc)
	zone.NewGlobal()
	p := tea.NewProgram(m, tea.WithAltScreen(), tea.WithMouseCellMotion())
	if _, err := p.Run(); err != nil {
		fmt.Fprintln(os.Stderr, "omakeyfig-go:", err)
		os.Exit(1)
	}
}
