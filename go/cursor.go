package main

// Board cursor: pure row/col navigation with nearest-x snap across rows.
// Cell center x = X + Cells/2 (mirrors Python move_cursor).

func cellCenter(c Cell) float64 { return float64(c.X) + float64(c.Cells)/2.0 }

func moveCursor(rows [][]Cell, row, col, dx, dy int) (int, int) {
	if len(rows) == 0 {
		return 0, 0
	}
	if row < 0 || row >= len(rows) {
		if dy < 0 {
			return len(rows) - 1, 0
		}
		return 0, 0
	}
	if dy == 0 {
		col += dx
		if col < 0 {
			col = 0
		}
		if col >= len(rows[row]) {
			col = len(rows[row]) - 1
		}
		return row, col
	}
	src := row
	dst := row + dy
	if dst < 0 {
		dst = 0
	}
	if dst >= len(rows) {
		dst = len(rows) - 1
	}
	x := cellCenter(rows[src][col])
	return dst, nearestCol(rows, dst, x)
}

func nearestCol(rows [][]Cell, row int, x float64) int {
	best, bestD := 0, 1e18
	for i, c := range rows[row] {
		d := cellCenter(c) - x
		if d < 0 {
			d = -d
		}
		if d < bestD {
			best, bestD = i, d
		}
	}
	return best
}
