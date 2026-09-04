package main

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type screen int

const (
	sMenu screen = iota
	sDevices
	sTester
	sLighting
	sRemap
)

var views = []string{"caps", "slots", "binds"}

type model struct {
	back   string
	doc    *Export
	th     theme
	screen screen
	menuIx int
	width  int
	height int

	// tester state
	pressed map[int]bool
	viewIx  int
	fnView  bool
	fshift  bool
	lastKey string

	// lighting state
	fxIx  int
	color string
	bri   int
	spd   int
	slp   int
	status string

	// remap state (nil until first visit)
	remap *remapSt

	showHelp bool
}

func newModel(back string, doc *Export) model {
	return model{
		back: back, doc: doc, th: defaultTheme(),
		pressed: map[int]bool{},
		color:   doc.Accent,
		bri:     5, spd: 5, slp: 5,
	}
}

func (m model) Init() tea.Cmd { return nil }

func (m model) binds() map[int]string {
	fwLabel := map[int]string{}
	for _, a := range m.doc.Actions {
		if _, ok := fwLabel[a.Fw]; !ok {
			fwLabel[a.Fw] = a.Label
		}
	}
	out := map[int]string{}
	for slotStr, fw := range m.doc.Defaults {
		var slot int
		fmt.Sscanf(slotStr, "%d", &slot)
		if l, ok := fwLabel[fw]; ok {
			out[slot] = l
		} else {
			out[slot] = fmt.Sprintf("%#x", fw)
		}
	}
	return out
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width, m.height = msg.Width, msg.Height
		return m, nil
	case pushedMsg:
		if m.remap != nil {
			m.remap.confirm = false
			if msg.err != nil {
				m.remap.status = "push failed: " + msg.err.Error()
			} else {
				m.remap.status = "pushed to keyboard"
				m.remap.base = m.remap.fullMap()
				m.remap.pending = map[int]int{}
				m.remap.history = nil
			}
		}
		return m, nil
	case tea.KeyMsg:
		return m.updateKey(msg)
	}
	return m, nil
}

func (m model) updateKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	k := msg.String()
	if m.showHelp {
		m.showHelp = false
		return m, nil
	}
	if k == "ctrl+c" {
		return m, tea.Quit
	}
	// remap filter focus eats everything except ctrl+c (esc exits filter)
	if m.screen == sRemap && m.remap != nil && m.remap.focusFilt {
		return m.updateRemap(k)
	}
	switch k {
	case "q":
		return m, tea.Quit
	case "?":
		m.showHelp = true
		return m, nil
	}
	switch m.screen {
	case sMenu:
		return m.updateMenu(k)
	case sDevices:
		if k == "esc" {
			m.screen = sMenu
		}
		return m, nil
	case sTester:
		return m.updateTester(k)
	case sLighting:
		return m.updateLighting(k, msg)
	case sRemap:
		return m.updateRemap(k)
	}
	return m, nil
}

var menuItems = []string{"Devices", "Key tester", "Lighting", "Remap", "(Macros in Python TUI)", "(Profiles in Python TUI)"}

func (m model) updateMenu(k string) (tea.Model, tea.Cmd) {
	switch k {
	case "up", "k":
		m.menuIx = (m.menuIx + len(menuItems) - 1) % len(menuItems)
	case "down", "j":
		m.menuIx = (m.menuIx + 1) % len(menuItems)
	case "enter":
		switch m.menuIx {
		case 0:
			m.screen = sDevices
		case 1:
			m.screen = sTester
		case 2:
			m.screen = sLighting
		case 3:
			if m.remap == nil {
				m.remap = newRemap(m.doc)
			}
			m.screen = sRemap
		}
	case "esc":
		return m, tea.Quit
	}
	return m, nil
}

func (m model) updateTester(k string) (tea.Model, tea.Cmd) {
	switch k {
	case "esc":
		m.screen = sMenu
		return m, nil
	case "f1":
		m.fnView = !m.fnView
		return m, nil
	case "f2":
		m.fshift = !m.fshift
		return m, nil
	case "tab":
		m.viewIx = (m.viewIx + 1) % len(views)
		return m, nil
	case "C":
		m.pressed = map[int]bool{}
		m.lastKey = ""
		return m, nil
	}
	slots := matchSlots(m.doc.Rows, k)
	for _, s := range slots {
		m.pressed[s] = true
	}
	if k == " " {
		m.lastKey = "space"
	} else {
		m.lastKey = k
	}
	return m, nil
}

func clamp10(v, d int) int {
	v += d
	if v < 0 {
		return 0
	}
	if v > 10 {
		return 10
	}
	return v
}

func (m model) updateLighting(k string, msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch k {
	case "esc":
		m.screen = sMenu
		return m, nil
	case "left", "h":
		m.fxIx = (m.fxIx + len(m.doc.Effects) - 1) % len(m.doc.Effects)
	case "right", "l":
		m.fxIx = (m.fxIx + 1) % len(m.doc.Effects)
	case "1":
		m.bri = clamp10(m.bri, -1)
	case "2":
		m.bri = clamp10(m.bri, 1)
	case "3":
		m.spd = clamp10(m.spd, -1)
	case "4":
		m.spd = clamp10(m.spd, 1)
	case "5":
		m.slp = clamp10(m.slp, -1)
	case "6":
		m.slp = clamp10(m.slp, 1)
	case "enter":
		fx := m.doc.Effects[m.fxIx]
		args := []string{"light", "--effect", fx,
			"--brightness", itoa(m.bri), "--speed", itoa(m.spd),
			"--color", m.color, "--sleep", itoa(m.slp)}
		out, err := runBackend(m.back, args...)
		if err != nil {
			m.status = "push failed: " + err.Error()
		} else {
			m.status = "pushed: " + strings.TrimSpace(out)
		}
	}
	_ = msg
	return m, nil
}

func (m model) View() string {
	var b strings.Builder
	b.WriteString(m.th.title.Render("omakeyfig-go  (python backend: " + m.back + ")") + "\n\n")
	switch m.screen {
	case sMenu:
		b.WriteString(m.viewMenu())
	case sDevices:
		b.WriteString(m.viewDevices())
	case sTester:
		b.WriteString(m.viewTester())
	case sLighting:
		b.WriteString(m.viewLighting())
	case sRemap:
		b.WriteString(m.viewRemap())
	}
	b.WriteString("\n" + m.th.help.Render(m.helpBar()) + "\n")
	if m.showHelp {
		w, h := m.width, m.height
		if w <= 0 {
			w = 80
		}
		if h <= 0 {
			h = 24
		}
		return lipgloss.Place(w, h, lipgloss.Center, lipgloss.Center, m.helpBox())
	}
	return b.String()
}

func (m model) helpBar() string {
	switch m.screen {
	case sMenu:
		return "↑↓/jk navigate · enter select · ? help · q quit"
	case sTester:
		return "press keys to light them · tab view · F1 fn · F2 f-shift · C clear · esc menu"
	case sLighting:
		return "←→ effect · 1/2 bri · 3/4 spd · 5/6 sleep · enter push · esc menu"
	case sRemap:
		return "hjkl move · enter filter · type+enter assign · u undo · ctrl+s push · esc menu"
	default:
		return "esc back · ? help · q quit"
	}
}

func (m model) viewMenu() string {
	var b strings.Builder
	for i, item := range menuItems {
		cursor := "  "
		if i == m.menuIx {
			cursor = m.th.sel.Render("▸ ")
		}
		b.WriteString(cursor + item + "\n")
	}
	return b.String()
}

func (m model) viewDevices() string {
	var b strings.Builder
	if len(m.doc.Devices) == 0 {
		b.WriteString("No Royal Kludge devices found (connect via USB cable).\n")
		return b.String()
	}
	for _, d := range m.doc.Devices {
		b.WriteString(fmt.Sprintf("vid=%#06x pid=%#06x product=%q serial=%q\n",
			d.VendorID, d.ProductID, d.Product, d.Serial))
	}
	return b.String()
}

func (m model) viewTester() string {
	var b strings.Builder
	b.WriteString(fmt.Sprintf("last: %-12s view: %-6s fn:%v fshift:%v pressed:%d\n\n",
		m.lastKey, views[m.viewIx], m.fnView, m.fshift, len(m.pressed)))
	b.WriteString(renderBoard(m.th, m.doc.Rows, views[m.viewIx], m.fnView, m.fshift, m.binds(), m.pressed))
	return b.String()
}

func (m model) viewLighting() string {
	var b strings.Builder
	b.WriteString(fmt.Sprintf("effect: %s\nbrightness: %d (1/2)   speed: %d (3/4)   sleep: %d (5/6)   color: %s\n\n",
		m.doc.Effects[m.fxIx], m.bri, m.spd, m.slp, m.color))
	if m.status != "" {
		b.WriteString(m.status + "\n\n")
	}
	b.WriteString(renderBoard(m.th, m.doc.Rows, "caps", false, false, nil, map[int]bool{}))
	return b.String()
}

var helpText = `omakeyfig-go keybindings

  menu     ↑↓/jk move · enter open · q quit
  tester   any key lights the board · tab cycles caps/slots/binds
           F1 fn layer · F2 f-shift · C clears · esc menu
  lighting ←→ change effect · 1/2 brightness · 3/4 speed
           5/6 sleep · enter pushes to keyboard · esc menu
  remap    hjkl/arrows move cursor · enter focuses filter
           type to filter · enter assigns · u undo
           ctrl+s reviews + confirms the push · esc menu

  Writes always go through the Python backend.`

func (m model) helpBox() string {
	return m.th.box.Render(helpText)
}
