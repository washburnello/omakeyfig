# omakeyfig-go — Bubble Tea + Lip Gloss spike (branch: go-frontend)

Alternative frontend for omakeyfig. All protocol/HID work stays in the
Python backend; this binary only shells out to it:

- `omakeyfig export` feeds the UI (layout, catalog, devices, effects).
- `omakeyfig light …` performs lighting writes.
- `omakeyfig write-map --mapping-file …` performs keymap writes.

## Build / run

```bash
go build -o omakeyfig-go .
OMAKEYFIG_BACKEND=/path/to/omakeyfig ./omakeyfig-go   # or omakeyfig on PATH
```

## Status (spike)

Working: menu, devices, key tester (press-to-light, caps/slots/binds,
Fn + F-shift views, `?` overlay, persistent help bar), lighting
(effect cycle, steppers, push). Remap/macros/profiles live in the Python
TUI for now — the `--mapping-file` flag already unblocks a Go remap.

## Tests

`go test ./...` — matcher/label/render unit tests plus a live-backend
integration test (skips without `omakeyfig` on PATH).
