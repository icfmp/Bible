"""Daemon futures for disposable metadata work, never GTK or native SWORD.

Unlike concurrent.futures.ThreadPoolExecutor, these workers do not register an
interpreter-exit join. Closing the application must not wait for a remote socket.
Only atomic catalogue-cache writers and pure metadata tasks use this executor;
resource installations retain their existing completion/atomicity policy.
"""
from concurrent.futures import Future
from queue import Queue,Empty
from threading import Thread,Lock,current_thread


class MetadataExecutor:
    def __init__(self,max_workers=1,thread_name_prefix='bible-metadata'):
        self.maximum=max_workers;self.prefix=thread_name_prefix
        self.queue=Queue();self.lock=Lock();self.threads=[];self.closed=False

    def submit(self,function,*args,**kwargs):
        future=Future()
        with self.lock:
            if self.closed:raise RuntimeError('Metadata worker is closed')
            self.queue.put((future,function,args,kwargs))
            if len(self.threads)<self.maximum:
                thread=Thread(target=self.work,name=f'{self.prefix}-{len(self.threads)}',daemon=True)
                self.threads.append(thread);thread.start()
        return future

    def work(self):
        while True:
            item=self.queue.get()
            if item is None:return
            future,function,args,kwargs=item
            if not future.set_running_or_notify_cancel():continue
            try:result=function(*args,**kwargs)
            except BaseException as error:future.set_exception(error)
            else:future.set_result(result)

    def shutdown(self,wait=True,cancel_futures=False):
        with self.lock:
            if not self.closed:
                self.closed=True
                if cancel_futures:
                    while True:
                        try:item=self.queue.get_nowait()
                        except Empty:break
                        if item is not None:item[0].cancel()
                for _ in self.threads:self.queue.put(None)
        if wait:
            for thread in self.threads:
                if thread is not current_thread():thread.join()

    def __enter__(self):return self
    def __exit__(self,*_):self.shutdown()
