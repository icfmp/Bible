#!/bin/sh
set -u
export XDG_DATA_HOME=/validation/xdg-data
export GSK_RENDERER=cairo
cd /tmp
fp() {
  flatpak run --user --unshare=network \
    --env=PYTHONPATH=/app/lib/bible-python:/validation/checkout:/validation/test-tools \
    --env=GSK_RENDERER=cairo --env=LANGUAGE=fr \
    --filesystem=/validation/checkout:ro --filesystem=/evidence \
    --filesystem=/validation/test-tools:ro --filesystem=/validation/resources:ro \
    --filesystem=/validation/package-continuous --filesystem=/validation/package-stabilized \
    --filesystem=/validation/package-action-tests \
    --env=BIBLE_TEST_ISOLATED_CLICK=1 \
    --command=python3 io.github.icfmp.Bible//recovery-24 "$@"
}
gui() {
  # Export shell functions through a tiny generated command script.
  dbus-run-session -- xvfb-run -a -s '-screen 0 1600x1100x24' sh /evidence/run-flatpak-checks.sh --gui "$@"
}
if [ "${1:-}" = --gui ]; then
  shift
  fp "$@"
  exit $?
fi
run_check() {
  label=$1; shift
  printf '%s\n' "Running $label"
  "$@" > "/evidence/flatpak/$label.log" 2>&1
  result=$?
  printf '%s exit=%s\n' "$label" "$result" | tee -a /evidence/flatpak/status.txt
  tail -n 6 "/evidence/flatpak/$label.log"
}
test -d /validation/package-continuous || cp -a /validation/resources /validation/package-continuous
test -d /validation/package-stabilized || cp -a /validation/resources /validation/package-stabilized
mkdir -p /validation/package-action-tests
run_check book-preparation dbus-run-session -- sh /evidence/run-flatpak-checks.sh --gui -m tools.check_book_preparation /validation/resources --require-packaged --output /evidence/flatpak/book-preparation.json
run_check affected-suite gui /evidence/run-packaged-suite.py
run_check isolated-native-click gui -m unittest tests.test_immersion.ImmersionTests.test_native_click_targets_notes_and_context_copy_on_each_page -v
run_check continuous gui -m tools.check_continuous_books /validation/package-continuous --require-packaged --screenshot /evidence/flatpak/continuous.png
run_check stabilized gui -m tools.check_stabilized_ui /validation/package-stabilized /evidence/flatpak/stabilized --require-packaged
run_check native-actions gui -m tools.check_passage_actions /validation/package-action-tests/profile /evidence/flatpak/actions --synthetic
run_check native-reading gui -m tools.check_reading_ui
run_check native-popovers gui -m tools.check_popover_dismissal
