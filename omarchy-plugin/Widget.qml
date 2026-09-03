import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "washburnello.omakeyfig"

  function run(cmd) {
    if (bar) bar.run(cmd)
  }

  implicitWidth: btn.implicitWidth
  implicitHeight: btn.implicitHeight

  BarIconButton {
    id: btn
    bar: root.bar
    text: "󰌌"
    tooltipText: "Omakeyfig — RK keyboard (left: TUI, right: apply theme color)"
    onPressed: function(b) {
      if (b === Qt.RightButton) root.run("omakeyfig apply-theme")
      else root.run("alacritty -e omakeyfig tui")
    }
  }
}
