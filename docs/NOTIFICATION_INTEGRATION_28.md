# Immersive reading and desktop notifications (#28)

## Result

No supported public API has been demonstrated that lets Bible's current Flatpak
temporarily suppress other applications' GNOME notifications with process-bound,
crash-safe restoration while preserving the user's concurrent changes. Automatic
suppression is **not implemented**. Keep the existing honest manual Do Not Disturb
guidance; do not change desktop notification settings or sandbox permissions.
Immersive reading is usable independently of this integration.

## Public contracts checked on 21 October 2026

Upstream xdg-desktop-portal commit
`49075617ff70ba2dc793dddb796a0a515fbebd7a`:

- [Notification XML](https://github.com/flatpak/xdg-desktop-portal/blob/49075617ff70ba2dc793dddb796a0a515fbebd7a/data/org.freedesktop.portal.Notification.xml):
  `AddNotification` and `RemoveNotification` send/withdraw the calling app's
  notifications. The contract explicitly says the application cannot learn
  whether its notification was actually presented. Display hints concern that
  notification, not a global Do Not Disturb lease. An error-free call would not
  demonstrate suppression of another application's banner.
- [Inhibit XML](https://github.com/flatpak/xdg-desktop-portal/blob/49075617ff70ba2dc793dddb796a0a515fbebd7a/data/org.freedesktop.portal.Inhibit.xml):
  version 3 flags are logout (1), user switch (2), suspend (4), idle (8).
  Its request/session lifetime does not turn those into notification suppression.
  No notification inhibition flag exists in this contract.

Directly writing GNOME's persistent notification settings would not provide the
required process lifetime or safe ownership of user changes. Saving a boolean
and restoring it on normal exit cannot cover a crash or distinguish intervening
manual changes. Private shell calls and broad host access are not substitutes
for a demonstrated supported contract. No such changes were made.

## Runtime evidence and limits

An introspection attempt from the **actual installed public alpha** sandbox in
the disposable Xvfb/container session returned:

```
GDBus.Error:org.freedesktop.DBus.Error.ServiceUnknown: The name org.freedesktop.portal.Desktop was not provided by any .service files
```

This session lacks a running desktop portal. That is not evidence that the
client's GNOME desktop lacks one. It establishes neither suppression nor failure
of notification delivery on that desktop. No notification was sent or global
setting modified. The public contracts above, rather than this runtime absence,
are the reason no automatic integration is claimed.

## Remaining acceptance

Keep #28 open for target-desktop investigation if a suitable public API appears.
Require observable suppression of a separate test application's ordinary banners,
not merely successful calls; preserve already-active Do Not Disturb and manual
changes; cover normal exit, window close and forced termination. Do not promise
suppression of critical alerts. Until then the client enables/disables GNOME's
Do Not Disturb manually and Bible must continue to describe this honestly.

This documentation-only investigation does not require another application build.
