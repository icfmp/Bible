# Immersive reading and desktop notifications (#28)

## Result

No supported public API has been demonstrated that lets Bible's current Flatpak
temporarily suppress other applications' GNOME notifications with process-bound,
crash-safe restoration while preserving the user's concurrent changes. Automatic
suppression is **not implemented**. Keep the existing honest manual Do Not Disturb
guidance; do not change desktop notification settings or sandbox permissions.
Immersive reading is usable independently of this integration.

## Public contracts rechecked on 4 November 2026

Upstream xdg-desktop-portal commit
`8c3efadd0f3d619847c97965865c7a22c844a3c9` (30 October):

- [Notification XML](https://github.com/flatpak/xdg-desktop-portal/blob/8c3efadd0f3d619847c97965865c7a22c844a3c9/data/org.freedesktop.portal.Notification.xml):
  `AddNotification` and `RemoveNotification` send/withdraw the calling app's
  notifications. The contract explicitly says the application cannot learn
  whether its notification was actually presented. Display hints concern that
  notification, not a global Do Not Disturb lease. An error-free call would not
  demonstrate suppression of another application's banner.
- [Inhibit XML](https://github.com/flatpak/xdg-desktop-portal/blob/8c3efadd0f3d619847c97965865c7a22c844a3c9/data/org.freedesktop.portal.Inhibit.xml):
  version 3 flags are logout (1), user switch (2), suspend (4), idle (8).
  Its request/session lifetime does not turn those into notification suppression.
  No notification inhibition flag exists in this contract.

The recheck used pinned upstream source files, not an inference from the absence
of a desktop service in a test container. SHA-256 of the Notification XML:
`bf21b267c01cc5629b847f513796e1d0626e1a887ede86f73b2d7ff75f36417d`;
Inhibit XML:
`0adf7c8dff228557d4528c90bc9cbd7ee6bf162ccc99889be18108e7eee14627`.

Additional GNOME paths were checked:

- GNOME Shell [freedesktop notification interface](https://github.com/GNOME/gnome-shell/blob/7904014f5b1a104c003aa481d1e4d0b9c7fe7f79/data/dbus-interfaces/org.freedesktop.Notifications.xml)
  at `7904014f5b1a104c003aa481d1e4d0b9c7fe7f79` (2 November) exposes
  `Notify`, `CloseNotification`, `GetCapabilities`, `GetServerInformation`.
  It provides no application-owned global suppression lease.
- GNOME Session's [presence setter](https://github.com/GNOME/gnome-session/blob/0cfee2253b53f71343f2db6a4fc9a8cd2ad1e6c0/gnome-session/gsm-presence.c)
  at `0cfee2253b53f71343f2db6a4fc9a8cd2ad1e6c0` (30 October),
  `gsm_presence_set_status_dbus`, changes shared presence directly. The setter
  does not tie the value to the caller's bus lifetime or return an owned lease.
  Setting BUSY and saving/restoring a status would not meet crash and concurrent
  user-change requirements, even if a sandbox permission allowed the call.

## Fullscreen policy is separate from Do Not Disturb

GNOME Shell's pinned [message tray implementation](https://github.com/GNOME/gnome-shell/blob/7904014f5b1a104c003aa481d1e4d0b9c7fe7f79/js/ui/messageTray.js)
limits ordinary banners when the **primary monitor** is fullscreen, or presence
is busy. Its `showNextNotification` condition still permits feedback and critical
notifications. This is desktop policy, not a public suppression contract granted
to Bible. It does not justify a promise about other monitors, desktop versions,
queued notifications or critical alerts.

Bible already requests fullscreen through GTK for immersion. No new desktop
settings, presence setter, private Shell API, timers or sandbox permissions are
needed for that existing behavior. We have **not measured notification delivery
in a real GNOME session** in this investigation; the source condition above is
not runtime evidence of an effect. Immersive reading must remain usable without
claiming automatic Do Not Disturb. The manual banner remains accurate.

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

The #28 investigation changes documentation only. The accompanying #163 picker
change receives its own application checks and signed alpha delivery; that build
must not be reported as validation of GNOME notification suppression.
