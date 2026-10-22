#!/bin/sh
set -u
mkdir -p /evidence/source
cd /src
run_check() {
  label=$1
  shift
  printf '%s\n' "Running $label"
  "$@" > "/evidence/source/$label.log" 2>&1
  result=$?
  printf '%s exit=%s\n' "$label" "$result" | tee -a /evidence/source/status.txt
  tail -n 6 "/evidence/source/$label.log"
}
run_check full-suite dbus-run-session -- xvfb-run -a -s '-screen 0 1600x1100x24' /usr/bin/python3 -m unittest discover -v
run_check french-suite env LANGUAGE=fr dbus-run-session -- xvfb-run -a -s '-screen 0 1600x1100x24' /usr/bin/python3 -m unittest tests.test_ui tests.test_alpha_ui tests.test_provider_ui tests.test_workspace_features tests.test_appearance tests.test_immersion tests.test_reading_sync tests.test_pagination tests.test_reading_direction tests.test_book_preparation tests.test_book_stream -v
run_check native-reading dbus-run-session -- xvfb-run -a -s '-screen 0 1600x1100x24' /usr/bin/python3 -m tools.check_reading_ui
run_check native-actions dbus-run-session -- xvfb-run -a -s '-screen 0 1600x1100x24' /usr/bin/python3 -m tools.check_passage_actions /validation/actions-source /evidence/source/actions --synthetic
run_check native-popovers dbus-run-session -- xvfb-run -a -s '-screen 0 1600x1100x24' /usr/bin/python3 -m tools.check_popover_dismissal
