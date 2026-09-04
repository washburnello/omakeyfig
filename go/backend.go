package main

import (
	"encoding/json"
	"fmt"
	"os/exec"
)

// Export mirrors `omakeyfig export` JSON.
type Cell struct {
	Slot      int      `json:"slot"`
	Label     string   `json:"label"`
	Cap       string   `json:"cap"`
	X         int      `json:"x"`
	Cells     int      `json:"cells"`
	Char      *string  `json:"char"`
	Names     []string `json:"names"`
	Fn        *string  `json:"fn"`
	Fshift    *string  `json:"fshift"`
	FshiftFn  *string  `json:"fshift_fn"`
}

type Device struct {
	VendorID  int    `json:"vendor_id"`
	ProductID int    `json:"product_id"`
	Serial    string `json:"serial"`
	Product   string `json:"product"`
}

type Action struct {
	Aid      int    `json:"aid"`
	Label    string `json:"label"`
	Category string `json:"category"`
	Fw       int    `json:"fw"`
}

type Export struct {
	Pid      int               `json:"pid"`
	NKeys    int               `json:"n_keys"`
	Devices  []Device          `json:"devices"`
	Rows     [][]Cell          `json:"rows"`
	Defaults map[string]int    `json:"defaults"`
	Actions  []Action          `json:"actions"`
	Effects  []string          `json:"effects"`
	Accent   string            `json:"accent"`
}

func runBackend(back string, args ...string) (string, error) {
	cmd := exec.Command(back, args...)
	out, err := cmd.Output()
	if err != nil {
		if ee, ok := err.(*exec.ExitError); ok {
			return "", fmt.Errorf("%s: %s", err, string(ee.Stderr))
		}
		return "", err
	}
	return string(out), nil
}

func loadExport(back string) (*Export, error) {
	out, err := runBackend(back, "export", "--pid", "0x220")
	if err != nil {
		return nil, err
	}
	var doc Export
	if err := json.Unmarshal([]byte(out), &doc); err != nil {
		return nil, err
	}
	return &doc, nil
}
