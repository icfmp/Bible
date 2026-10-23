set -eu
export XDG_RUNTIME_DIR=$(mktemp -d /validation/focus70-runtime-XXXXXX)
chmod 700 "$XDG_RUNTIME_DIR"
export LIBGL_ALWAYS_SOFTWARE=1 GSK_RENDERER=cairo
mutter --nested --wayland --no-x11 --wayland-display=bible-focus-70 > /validation/focus70-mutter.log 2>&1 &
compositor=$!
trap 'kill "$compositor" 2>/dev/null || true' EXIT
for i in $(seq 1 100); do [ -S "$XDG_RUNTIME_DIR/bible-focus-70" ] && break; sleep .05; done
export WAYLAND_DISPLAY=bible-focus-70 GDK_BACKEND=wayland
python3 -c 'import gi;gi.require_version("Gtk","4.0");from gi.repository import Gtk; a=Gtk.Application(application_id="io.github.icfmp.Focus70SwitchTarget");a.connect("activate",lambda app:Gtk.ApplicationWindow(application=app,title="Switch target",default_width=300,default_height=200).present());a.run([])' > /validation/focus70-dummy.log 2>&1 &
dummy=$!
# Wait for the nested compositor's native outer X11 surface.
for i in $(seq 1 100); do
 MUTTER_XID=$(xdotool search --onlyvisible --name '.*' | tail -1) || true
 [ "$(xdotool search --onlyvisible --name '.*' | wc -l)" -gt 1 ] && break
 sleep .05
done
export MUTTER_XID
cd /src
flatpak run --user --unshare=network --socket=wayland --nosocket=fallback-x11 --socket=x11 --env=DISPLAY="$DISPLAY" --env=GDK_BACKEND=wayland --env=WAYLAND_DISPLAY=bible-focus-70 --env=MUTTER_XID="$MUTTER_XID" --env=GSK_RENDERER=cairo --env=LANGUAGE=fr --env=PYTHONPATH=/app/lib/bible-python:/validation/checkout70:/validation/test-tools --filesystem=/validation/focus70-input:ro --filesystem=/validation/checkout70:ro --filesystem=/validation/test-tools:ro --filesystem=/validation/focus70-profile --filesystem=/validation/focus70-output --command=python3 io.github.icfmp.Bible//alpha /validation/checkout70/tools/check_reader_focus_switch.py /validation/focus70-profile /validation/focus70-output --require-packaged --legacy --offline
kill "$dummy" 2>/dev/null || true
