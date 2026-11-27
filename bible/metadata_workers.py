"""Daemon futures for disposable metadata work, never GTK or native SWORD.

Unlike concurrent.futures.ThreadPoolExecutor, these workers do not register an
interpreter-exit join. Closing the application must not wait for a remote socket.
Only atomic catalogue-cache writers and pure metadata tasks use this executor;
resource installations retain their existing completion/atomicity policy.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Self, cast
from concurrent.futures import Future
from queue import Queue, Empty
from threading import Thread, Lock, current_thread


type _Work = tuple[Future[object], Callable[..., object], tuple[object, ...], dict[str, object]]


class MetadataExecutor:
    """Run disposable metadata-only tasks on bounded daemon threads without interpreter-exit socket joins.

    Tasks must not access GTK/native SWORD or own installation transactions.
    Use idle callbacks to marshal results to GTK; running tasks can outlive
    non-waiting shutdown and must tolerate their consumer being closed.
    """

    def __init__(self, max_workers: int = 1, thread_name_prefix: str = "bible-metadata") -> None:
        self.maximum = max_workers
        self.prefix = thread_name_prefix
        self.queue: Queue[_Work | None] = Queue()
        self.lock = Lock()
        self.threads: list[Thread] = []
        self.closed = False

    def submit[**P, R](
        self, function: Callable[P, R], *args: P.args, **kwargs: P.kwargs
    ) -> Future[R]:
        """Queue a callable as a Future and lazily start workers; reject submissions after shutdown."""
        future: Future[R] = Future()
        with self.lock:
            if self.closed:
                raise RuntimeError("Metadata worker is closed")
            # The heterogeneous queue erases R, but the callable and its future
            # stay paired; ParamSpec verifies the submission before that boundary.
            self.queue.put(cast("_Work", (future, function, args, kwargs)))
            if len(self.threads) < self.maximum:
                thread = Thread(
                    target=self.work, name=f"{self.prefix}-{len(self.threads)}", daemon=True
                )
                self.threads.append(thread)
                thread.start()
        return future

    def work(self) -> None:
        """Resolve queued futures, honor cancellation before execution and release retained task objects."""
        future: Future[object] | None
        function: Callable[..., object] | None
        args: tuple[object, ...] | None
        kwargs: dict[str, object] | None
        result: object
        while True:
            item = self.queue.get()
            if item is None:
                return
            future, function, args, kwargs = item
            try:
                if not future.set_running_or_notify_cancel():
                    continue
                try:
                    result = function(*args, **kwargs)
                except BaseException as error:
                    future.set_exception(error)
                else:
                    future.set_result(result)
            finally:
                # queue.get() can wait indefinitely. Do not retain the last
                # callable/arguments/result (including a closed study reader)
                # on this idle thread's stack until another job arrives.
                item = future = function = args = kwargs = result = None

    def shutdown(self, wait: bool = True, cancel_futures: bool = False) -> None:
        """Stop submissions, optionally cancel queued work and join workers only when explicitly requested."""
        with self.lock:
            if not self.closed:
                self.closed = True
                if cancel_futures:
                    while True:
                        try:
                            item = self.queue.get_nowait()
                        except Empty:
                            break
                        if item is not None:
                            item[0].cancel()
                for _ in self.threads:
                    self.queue.put(None)
        if wait:
            for thread in self.threads:
                if thread is not current_thread():
                    thread.join()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.shutdown()
