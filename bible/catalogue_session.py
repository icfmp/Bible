"""Plain-data Library preparation shared across close/reopen, without GTK/SWORD."""

from dataclasses import dataclass, replace
from threading import RLock
import time
from weakref import WeakMethod
from .metadata_workers import MetadataExecutor
from .catalogue_cache import CatalogueCache
from .providers import PROVIDERS, DEFAULT_PROVIDERS
from .languages import language_info, search_terms
from .book_names import normalized
from .study_resources import StudyResources


@dataclass(frozen=True)
class CatalogueSnapshot:
    """Plain-data Library inventory/search metadata snapshot for subscribed views."""

    resources: tuple
    installed: dict
    study_installed: frozenset
    study_current: frozenset
    languages: dict
    search: dict
    timings: dict
    errors: dict
    refreshing: bool
    generation: int
    covered_providers: frozenset = frozenset()
    removed_resources: frozenset = frozenset()
    archived_resources: frozenset = frozenset()
    available_languages: frozenset = frozenset()
    candidate_languages: frozenset = frozenset()


class CatalogueSession:
    """Share serialized metadata preparation and network refresh across Library reopenings.

    Workers publish plain data; subscribers are responsible for GTK marshalling.
    Cached catalogues are distinct from freshly verified providers. Closing
    the session prevents later worker results from becoming current snapshots.
    """

    def __init__(self, library):
        self.library = library
        self.cache = CatalogueCache(library.root.parent / "catalogue-cache")
        self.study = StudyResources(library.root.parent / "study-data")
        self.prepare = MetadataExecutor(thread_name_prefix="bible-library-metadata")
        self.network = MetadataExecutor(thread_name_prefix="bible-library-refresh")
        self.lock = RLock()
        self.closed = False
        self.listeners = []
        self.snapshot = None
        self.providers = {}
        self.installed = {}
        self.removed = {}
        self.verified_providers = set()
        self.study_installed = frozenset()
        self.study_current = frozenset()
        self.language_records = {}
        self.metrics = {}
        self.errors = {}
        self.refreshing = False
        self.youversion_languages = {}
        self.youversion_loaded = {}
        self.youversion_future = None
        self.youversion_loading = False
        self.youversion_request = 0
        self.language_future = None
        self.refresh_future = None
        self.installed_future = None
        self.revision = 0
        self.generation = 0
        self.bootstrap_future = self.schedule(self.bootstrap)

    def schedule(self, function, *args):
        future = self.prepare.submit(function, *args)
        future.add_done_callback(self.preparation_failed)
        return future

    def preparation_failed(self, future):
        """Publish a recoverable preparation error to live subscribers without discarding known state."""
        if future.cancelled():
            return
        error = future.exception()
        if error is None:
            return
        with self.lock:
            if self.closed:
                return
            base = self.snapshot or CatalogueSnapshot(
                (), {}, frozenset(), frozenset(), {}, {}, {}, {}, False, self.generation
            )
            snapshot = replace(
                base,
                errors={**base.errors, "Library": str(error)},
                refreshing=False,
                generation=self.generation,
            )
            self.snapshot = snapshot
            listeners = [r() for r in self.listeners if r() is not None]
        for callback in listeners:
            callback(snapshot)

    def subscribe(self, callback):
        reference = WeakMethod(callback)
        with self.lock:
            self.listeners.append(reference)
            snapshot = self.snapshot
        if snapshot:
            callback(snapshot)

    def unsubscribe(self, callback):
        with self.lock:
            self.listeners = [r for r in self.listeners if r() is not None and r() != callback]

    def scan_installed(self):
        """Refresh resource/study inventories and record per-resource validation failures."""
        start = time.monotonic()
        installed = {}
        errors = {}
        for name in self.library.installed():
            if self.closed:
                return
            try:
                installed[name] = self.library.resource(name)
            except Exception as error:
                errors[name] = str(error)
        from .module_lifecycle import ModuleLifecycle

        removed = ModuleLifecycle(self.library).removed_resources()
        study_installed = frozenset(self.study.installed())
        study_current = frozenset(name for name in study_installed if self.study.current(name))
        with self.lock:
            self.installed = installed
            self.removed = removed
            self.study_installed = study_installed
            self.study_current = study_current
            self.metrics["installed_scan_seconds"] = time.monotonic() - start
            if errors:
                self.metrics["installed_metadata_errors"] = errors

    def bootstrap(self):
        """Load saved metadata/languages and installed inventory without a provider network refresh."""
        start = time.monotonic()
        providers = {}
        for provider in PROVIDERS:
            if self.closed:
                return
            value = self.cache.read(provider)
            if value is not None:
                providers[provider.id] = value[0]
        with self.lock:
            self.providers = providers
            self.metrics["cache_read_seconds"] = time.monotonic() - start
        from .youversion_catalogue import saved_languages

        self.youversion_languages = saved_languages(self.cache.root / "youversion-languages")
        self.scan_installed()
        self.publish()

    def load_youversion_language(self, choice, force=False):
        """One language at a time; retain cached results, never acquire a Bible."""
        from .languages import canonical_language
        from .providers import YOUVERSION

        if not choice:
            return None
        key = canonical_language(choice)
        with self.lock:
            if self.closed:
                return None
            if time.monotonic() - self.youversion_loaded.get(key, -10000) < 15 * 60 and not force:
                return self.youversion_future
            if (
                self.youversion_loading
                and getattr(self, "_youversion_choice", None) == key
                and not force
            ):
                return self.youversion_future
            if self.youversion_future:
                self.youversion_future.cancel()
            self.youversion_request += 1
            request = self.youversion_request
            self._youversion_choice = key
            self.youversion_loading = True

        def work():
            from .youversion_catalogue import languages, editions, tags_for_language

            root = self.cache.root / "youversion-languages"
            try:
                self.bootstrap_future.result()
                with self.lock:
                    if self.closed or request != self.youversion_request:
                        return
                    records = dict(self.youversion_languages)
                if not records or force:
                    records = languages(root, force)
                tags = tags_for_language(choice, records)
                resources = []
                for tag in tags:
                    with self.lock:
                        if self.closed or request != self.youversion_request:
                            return
                    resources.extend(editions(tag, root, force))
                with self.lock:
                    if self.closed:
                        return
                    self.youversion_languages = records
                    old = [
                        r for r in self.providers.get(YOUVERSION.id, ()) if r.language not in tags
                    ]
                    self.providers[YOUVERSION.id] = tuple(
                        {r.id: r for r in (*old, *resources)}.values()
                    )
                    self.youversion_loaded[key] = time.monotonic()
                    self.errors.pop(YOUVERSION.name, None)
                    saved = self.providers[YOUVERSION.id]
                self.cache.write(YOUVERSION, saved)
            except Exception as error:
                with self.lock:
                    if not self.closed:
                        self.errors[YOUVERSION.name] = str(error)
            finally:
                with self.lock:
                    if request == self.youversion_request:
                        self.youversion_loading = False
                self.schedule(self.publish) if not self.closed else None

        with self.lock:
            self.youversion_future = self.network.submit(work)
        self.schedule(self.publish)
        return self.youversion_future

    def load_languages(self):
        """Prepare only source-backed choices; selecting one loads its editions."""
        with self.lock:
            if self.closed or self.language_future:
                return self.language_future

            def prepare():
                self.publish()

            self.language_future = self.schedule(prepare)
            return self.language_future

    def reload_installed(self):
        """Coalesce an asynchronous inventory scan on the shared preparation worker."""

        def work():
            self.scan_installed()
            self.publish()

        with self.lock:
            if self.closed:
                return None
            if self.installed_future and not self.installed_future.done():
                return self.installed_future
            self.installed_future = self.schedule(work)
            return self.installed_future

    def refresh_study(self):
        """Refresh only checked resource metadata; never fetch a dataset here."""

        def finish():
            self.scan_installed()
            self.publish()

        def work():
            try:
                self.bootstrap_future.result()
                self.study.catalogue.refresh()
                with self.lock:
                    self.errors.pop("Study tools", None)
            except Exception as error:
                with self.lock:
                    self.errors["Study tools"] = str(error)
            finally:
                with self.lock:
                    self.refreshing = False
                    if not self.closed:
                        self.schedule(finish)

        with self.lock:
            if self.closed:
                return None
            if self.refresh_future and not self.refresh_future.done():
                return self.refresh_future
            self.refreshing = True
            self.generation += 1
            self.refresh_future = self.network.submit(work)
            return self.refresh_future

    def refresh(self, fetch, force, providers=DEFAULT_PROVIDERS):
        """Coalesce network refresh requests, clear verification for requested sources and return its future."""
        with self.lock:
            if self.closed:
                return None
            if self.refresh_future and not self.refresh_future.done():
                return self.refresh_future
            if self.bootstrap_future.done() and self.bootstrap_future.exception() is not None:
                self.bootstrap_future = self.schedule(self.bootstrap)
            self.refreshing = True
            self.errors = {}
            self.generation += 1
            self.verified_providers.difference_update(p.id for p in providers)
            self.refresh_future = self.network.submit(self.fetch, fetch, force, tuple(providers))
            return self.refresh_future

    def fetch(self, fetch, force, providers):
        """Merge incremental provider results without replacing unloaded YouVersion language inventories."""

        def provider_ready(provider, items, error, timings):
            records = timings.get("source_languages", {}) if provider.id == "youversion" else {}
            if records:
                from .youversion_catalogue import remember
                from .youversion_editions import CONFIGURATION_URL

                try:
                    remember(
                        self.cache.root / "youversion-languages/languages.json",
                        CONFIGURATION_URL,
                        dict(default_versions=list(records.values())),
                    )
                except OSError:
                    pass
            with self.lock:
                if self.closed:
                    return
                if provider.id == "youversion":
                    if records:
                        self.youversion_languages = records
                    tags = set(timings.get("source_loaded_tags", ()))
                    items = tuple(
                        {
                            r.id: r
                            for r in (
                                *[
                                    r
                                    for r in self.providers.get(provider.id, ())
                                    if r.language not in tags
                                ],
                                *items,
                            )
                        }.values()
                    )
                if not error or items:
                    self.providers[provider.id] = tuple(items)
                if not error and not timings.get("cached"):
                    self.verified_providers.add(provider.id)
                if error:
                    self.errors[provider.name] = str(error)
                self.metrics[provider.id] = {
                    k: v for k, v in timings.items() if k != "source_languages"
                }
                self.revision += 1
                revision = self.revision
            self.schedule(self.publish, revision)

        try:
            self.bootstrap_future.result()
            if self.closed:
                return
            result = fetch(
                providers=providers, on_provider=provider_ready, cache=self.cache, force=force
            )
            resources = getattr(result, "resources", result)
            with self.lock:
                if self.closed:
                    return
                self.errors = dict(getattr(result, "errors", {}))
                self.providers.update(
                    {
                        p.id: tuple(r for r in resources if r.provider_id == p.id)
                        for p in providers
                        if p.name not in self.errors
                        and (p.id != "youversion" or p.id not in self.providers)
                    }
                )
                # Custom refresh callers may return a complete result without
                # incremental callbacks. Only an actual successful forced
                # refresh verifies availability; bootstrap caches do not.
                if force:
                    self.verified_providers.update(
                        p.id for p in providers if p.name not in self.errors
                    )
                saved = self.providers.get("youversion")
            if saved is not None:
                from .providers import YOUVERSION

                try:
                    self.cache.write(YOUVERSION, saved)
                except OSError:
                    pass
        except Exception as error:
            with self.lock:
                self.errors = {"Library": str(error)}
        finally:
            with self.lock:
                self.refreshing = False
                if not self.closed:
                    self.schedule(self.publish)

    def publish(self, revision=None):
        """Build a current plain-data snapshot, rejecting stale revisions and retaining offline source context."""
        with self.lock:
            if self.closed or revision is not None and revision != self.revision:
                return
            known = {r.id: r for rows in self.providers.values() for r in rows}
            catalogued = set(known)
            archived = set()
            for identifier, resource in self.removed.items():
                if (
                    resource.provider_id != "youversion"
                    and resource.provider_id in self.providers
                    and identifier not in known
                ):
                    # A complete provider catalogue supersedes historical
                    # transaction metadata, including after an offline reopen.
                    continue
                known.setdefault(identifier, resource)
                if (
                    resource.provider_id not in self.verified_providers
                    or identifier not in catalogued
                ) and identifier not in self.installed:
                    archived.add(identifier)
            resources = tuple(
                sorted(known.values(), key=lambda r: (r.language, r.name, r.provider_id))
            )
            removed_resources = frozenset(self.removed)
            installed = dict(self.installed)
            study_installed = self.study_installed
            study_current = self.study_current
            metrics = dict(self.metrics)
            errors = dict(self.errors)
            refreshing = self.refreshing or self.youversion_loading
            generation = self.generation
            covered = frozenset(self.providers)
            from .languages import canonical_language

            source_languages = {
                code
                for code in self.youversion_languages
                if canonical_language(code) not in self.youversion_loaded
            }
        start = time.monotonic()
        all_resources = (*resources, *installed.values(), *self.study.available())
        languages = {r.language for r in all_resources} | source_languages
        for code in languages:
            if self.closed:
                return
            if code not in self.language_records:
                name, native = language_info(code)
                name = name[:1].upper() + name[1:]
                native = native[:1].upper() + native[1:]
                display = (
                    name
                    + ((" — " + native) if native and native.casefold() != name.casefold() else "")
                    + f" ({code})"
                )
                self.language_records[code] = (name, display, normalized(search_terms(code)))
        records = {code: self.language_records[code] for code in languages}
        terms = {
            r.id: normalized(" ".join((r.name, r.description, r.language, records[r.language][2])))
            for r in all_resources
        }
        metrics["language_and_search_seconds"] = time.monotonic() - start
        snapshot = CatalogueSnapshot(
            resources,
            installed,
            study_installed,
            study_current,
            records,
            terms,
            metrics,
            errors,
            refreshing,
            generation,
            covered,
            removed_resources,
            frozenset(archived),
        )
        snapshot = replace(
            snapshot,
            available_languages=frozenset(
                {r.language for r in all_resources if r.id not in archived or r.id in installed}
            ),
            candidate_languages=frozenset(source_languages),
        )
        with self.lock:
            if self.closed:
                return
            self.snapshot = snapshot
            listeners = [ref() for ref in self.listeners if ref() is not None]
        for callback in listeners:
            callback(snapshot)

    def close(self):
        with self.lock:
            self.closed = True
            self.listeners = []
        self.prepare.shutdown(wait=False, cancel_futures=True)
        self.network.shutdown(wait=False, cancel_futures=True)
