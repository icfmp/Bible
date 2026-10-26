#!/bin/sh
set -eu
if [ "$BIBLE_PROFILE_A11Y" = atspi ]; then
    gdbus call --session --dest org.a11y.Bus --object-path /org/a11y/bus --method org.freedesktop.DBus.Properties.Set org.a11y.Status IsEnabled '<true>' > "$BIBLE_PROFILE_A11Y_STATUS"
    gdbus call --session --dest org.a11y.Bus --object-path /org/a11y/bus --method org.freedesktop.DBus.Properties.GetAll org.a11y.Status >> "$BIBLE_PROFILE_A11Y_STATUS"
else
    echo 'GTK_A11Y=none: diagnostic control' > "$BIBLE_PROFILE_A11Y_STATUS"
fi
exec "$@"
