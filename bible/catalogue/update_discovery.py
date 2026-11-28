"""Application-scoped metadata discovery; installation stays in Library's queue."""

from __future__ import annotations

import time
from gi.repository import Adw, Gtk, GLib
from .catalogue_session import CatalogueSession
from .module_management import checked_modules, SUPPORTED
from ..providers import BY_ID
from ..i18n import tr


def discovery(owner):
    """Return the application/profile-scoped update manager shared by its windows."""
    app = owner.get_application()
    key = owner.library.root.resolve()
    if not hasattr(app, "_resource_updates"):
        app._resource_updates = {}
    manager = app._resource_updates.get(key)
    if manager is None or manager.session.closed:
        manager = ResourceUpdates(owner.library, session=getattr(owner, "catalogue_session", None))
        app._resource_updates[key] = manager
    owner.catalogue_session = manager.session
    return manager


class ResourceUpdates:
    """Discover metadata-only update offers; installations use the existing Library queue."""

    def __init__(self, library, session=None) -> None:
        self.library = library
        self.session = session if session and not session.closed else CatalogueSession(library)
        self.reports = {}
        self.checking = False
        self.started = False
        self.state = "not-checked"
        self.error = ""
        self.listeners = []
        self.inventory = None
        self.session.subscribe(self.snapshot_ready)

    def subscribe(self, callback) -> None:
        """Register a weak bound-method listener and immediately deliver current state."""
        from weakref import WeakMethod

        self.listeners.append(WeakMethod(callback))
        callback()

    def notify(self) -> bool:
        """Notify live listeners on the caller's thread unless the shared session is closed."""
        if self.session.closed:
            return False
        self.listeners = [ref for ref in self.listeners if ref() is not None]
        for ref in self.listeners:
            ref()()
        return False

    def snapshot_ready(self, snapshot) -> None:
        # Module switches publish a new inventory; never keep an offer for a
        # deleted/already replaced edition. No network check is repeated here.
        """Invalidate offers after an inventory change without starting another network check."""
        previous = self.inventory
        self.inventory = (snapshot.installed, snapshot.study_installed, snapshot.study_current)
        if (
            previous is not None
            and previous != self.inventory
            and not self.checking
            and self.state != "not-checked"
        ):
            self.session.schedule(self.reassess)

    def reassess(self) -> None:
        """Recompute offers from shared catalogues/inventory and marshal acceptance to GTK."""
        with self.session.lock:
            resources = tuple(r for rows in self.session.providers.values() for r in rows)
            errors = dict(self.session.errors)
        for key in {r.provider_id for r in self.session.installed.values()} & SUPPORTED:
            record = self.session.cache.read(BY_ID[key])
            if key not in self.session.verified_providers and (
                not record or time.time() - record[1] >= 15 * 60
            ):
                errors.setdefault(BY_ID[key].name, "Source catalogue has not been checked recently")
        inventory = self.inventory
        reports = checked_modules(self.library, resources, errors)
        self.add_study(reports, errors)
        GLib.idle_add(self.accept, reports, inventory)

    def add_study(self, reports, errors) -> None:
        """Add installed study-tool revision states, preserving unavailable metadata as errors."""
        study = self.session.study
        for identifier in study.installed():
            try:
                old = study.installed_resource(identifier)
                new = study.resource(identifier)
                state = (
                    "offline"
                    if "Study tools" in errors
                    else "available"
                    if old.revision != new.revision
                    else "current"
                )
                reports[identifier] = dict(
                    state=state, available=new, installed=old, error=errors.get("Study tools", "")
                )
            except (OSError, ValueError, KeyError) as error:
                reports[identifier] = dict(
                    state="local-unverified", available=None, error=str(error)
                )

    def accept(self, reports, inventory=None) -> bool:
        """Accept worker reports on GTK's thread only for the matching current inventory."""
        if self.session.closed:
            return False
        if inventory is not None and inventory != self.inventory:
            if not self.checking:
                self.session.schedule(self.reassess)
            return False
        self.reports.clear()
        self.reports.update(reports)
        self.notify()
        return False

    def start(self, automatic) -> bool:
        """Start the one-time automatic check only when the saved preference enables it."""
        if not automatic or self.started:
            return False
        self.started = True
        self.check()
        return False

    def check(self, force: bool = False) -> None:
        """Schedule metadata discovery without blocking the GTK caller or installing resources.

        The existing serial worker waits for bootstrap, refreshes eligible source
        metadata and posts results through GLib. Repeated active checks coalesce;
        fresh cache results may be shown while network work finishes.
        """
        if self.checking or self.session.closed:
            return
        if (
            self.session.bootstrap_future.done()
            and self.session.bootstrap_future.exception() is not None
        ):
            self.session.bootstrap_future = self.session.schedule(self.session.bootstrap)
        self.checking = True
        self.state = "checking"
        self.error = ""
        self.notify()

        def work() -> None:
            try:
                self.session.bootstrap_future.result()
                if not self.session.installed and not self.session.study_installed:
                    self.state = "checked"
                    GLib.idle_add(self.accept, {})
                    return
                providers = tuple(
                    BY_ID[k]
                    for k in sorted(
                        {r.provider_id for r in self.session.installed.values()} & SUPPORTED
                    )
                )
                # Only fresh, validated provider caches are eligible at startup.
                fresh = {
                    p.id
                    for p in providers
                    if (record := self.session.cache.read(p)) and time.time() - record[1] < 15 * 60
                }
                if fresh:
                    rows = tuple(
                        r
                        for p in providers
                        if p.id in fresh
                        for r in self.session.providers.get(p.id, ())
                    )
                    errors = {
                        p.name: "Saved catalogue expired" for p in providers if p.id not in fresh
                    }
                    GLib.idle_add(
                        self.accept, checked_modules(self.library, rows, errors), self.inventory
                    )
                if providers:
                    from ..library import catalogues

                    future = self.session.refresh(catalogues, force, providers)
                    if future:
                        future.result()
                if self.session.closed:
                    return
                study = self.session.study
                if study.installed():
                    path = study.catalogue.path
                    if force or not path.exists() or time.time() - path.stat().st_mtime > 15 * 60:
                        try:
                            study.catalogue.refresh()
                            self.session.errors.pop("Study tools", None)
                        except (OSError, ValueError) as error:
                            self.session.errors["Study tools"] = str(error)
                # Remote study revisions can change what 'current' means.
                # Re-read inventory after metadata completes, also covering
                # installs/removals that occurred while the check was running.
                self.session.scan_installed()
                self.session.publish()
                self.reassess()
                self.state = "offline" if self.session.errors else "checked"
                self.error = ""
            except Exception as error:
                self.state = "failed"
                self.error = str(error)
            finally:
                self.checking = False
                GLib.idle_add(self.notify)

        # The existing serial metadata worker has already queued bootstrap.
        # Waiting for network work here never runs GTK/SWORD on that worker.
        self.session.schedule(work)

    def eligible(self):
        """Return current available offers whose installed identity still matches the report."""

        def present(identifier, report):
            resource = report.get("available")
            if not resource or report["state"] != "available":
                return False
            if resource.kind == "study":
                return (
                    identifier in self.session.study_installed
                    and identifier not in self.session.study_current
                )
            return (
                report.get("installed") == self.session.installed.get(identifier)
                and identifier in self.session.installed
            )

        return [
            (identifier, report)
            for identifier, report in self.reports.items()
            if present(identifier, report)
        ]

    def queue_all(self, owner):
        """Open Library and submit eligible offers to its shared serial operation queue."""
        dialog = owner.open_library()
        # Reuse the shared service's current snapshot, then the existing serial
        # queue, permission checks and atomic lifecycle for every installation.
        if self.session.snapshot:
            dialog.apply_snapshot(self.session.snapshot)
        dialog.modules.reports.update(
            {
                k: v
                for k, v in self.reports.items()
                if v.get("available") and v["available"].kind != "study"
            }
        )
        for identifier, report in self.eligible():
            self.queue_one(dialog, identifier)
        return dialog

    def queue_one(self, dialog, identifier) -> None:
        # Recheck the current shared inventory at activation, not the recycled
        # row's old catalogue record. Both entry points use the same queue.
        """Recheck current eligibility before queuing one install/update request."""
        report = dict(self.eligible()).get(identifier)
        if report is None:
            return
        resource = report["available"]
        dialog.queue_request(
            resource, operation="install" if resource.kind == "study" else "update"
        )

    def show(self, owner):
        """Present current update details on GTK's thread; confirmation reuses Library's queue."""
        window = Adw.Window(
            transient_for=owner,
            modal=True,
            title=tr("Resource updates"),
            default_width=480,
            default_height=min(560, 170 + 90 * len(self.eligible())),
        )
        from ..application_surfaces import secondary_dialog

        secondary_dialog(window, owner)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(Adw.HeaderBar())
        rows = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, valign=Gtk.Align.START)
        rows.add_css_class("boxed-list")
        scroll = Gtk.ScrolledWindow(
            vexpand=True,
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            margin_start=12,
            margin_end=12,
            margin_top=12,
        )
        scroll.set_child(rows)
        box.append(scroll)
        for identifier, report in self.eligible():
            resource = report["available"]
            old = report.get("installed") or self.session.installed.get(identifier)
            if old is None:
                continue
            versions = (
                old.revision + " → " + resource.revision
                if resource.kind == "study"
                else old.version + " → " + resource.version
            )
            from ..resource_details import plain

            summary = resource.source + " · " + versions
            if resource.kind != "study" and resource.release_notes:
                summary += "\n" + plain(resource.release_notes)
            if resource.provider_id == "bible-resources":
                from ..curated_catalogue import package_record

                summary += (
                    "\n"
                    + tr("Download size")
                    + ": "
                    + f"{package_record(resource)['download']['size_bytes'] / 1024 / 1024:.1f} MiB"
                )
            row = Adw.ActionRow(
                title=plain(resource.description), subtitle=summary, use_markup=False
            )
            row.set_subtitle_lines(3)
            rows.append(row)
        label = Gtk.Label(
            label=tr("Previously checked catalogue")
            if self.checking
            else tr("Verified resource updates"),
            wrap=True,
            margin_top=12,
            margin_bottom=8,
        )
        label.set_tooltip_text(self.error or None)
        box.append(label)
        button = Gtk.Button(
            label=tr("Update all"), halign=Gtk.Align.END, margin_end=12, margin_bottom=12
        )
        button.add_css_class("suggested-action")
        button.set_sensitive(bool(self.eligible()))
        button.connect("clicked", lambda *_: (window.close(), self.queue_all(owner)))
        box.append(button)
        window.set_content(box)
        window.present()
        return window


class UpdateButton(Gtk.Button):
    """A contextual GTK indicator observing shared metadata discovery, without an installer."""

    def __init__(self, owner) -> None:
        super().__init__(icon_name="view-refresh-symbolic", visible=False)
        self.add_css_class("flat")
        self.add_css_class("resource-updates")
        self.owner = owner
        self.manager = None
        self._start_pending = False
        self.connect("clicked", lambda *_: self.manager.show(owner) if self.manager else None)
        owner.connect("map", self.mapped)

    def mapped(self, *_: object) -> None:
        """Defer initial discovery until mapping, honoring window lifetime and refresh preference."""
        if self.manager or self._start_pending:
            return
        self._start_pending = True

        def start() -> bool:
            self._start_pending = False
            if self.owner.closed:
                return False
            self.manager = discovery(self.owner)
            self.manager.subscribe(self.changed)
            self.manager.start(self.owner.application_settings.value["automatic_catalogue_refresh"])
            return False

        GLib.idle_add(start, priority=GLib.PRIORITY_LOW)

    def changed(self) -> None:
        """Reflect the current eligible count without starting discovery from a repaint."""
        if self.owner.closed:
            return
        count = len(self.manager.eligible())
        self.set_visible(bool(count))
        text = tr("Resource updates") + f" ({count})"
        self.set_tooltip_text(text)
        self.update_property([Gtk.AccessibleProperty.LABEL], [text])
