"""Keep CPU model calls serialized even when their awaiting request is cancelled."""

from threading import Lock


def locked_call(lock: Lock, function, *args, **kwargs):
    # Cancelling asyncio.to_thread cannot stop a running native call. The lock must
    # live in that thread, rather than be released by cancellation of the awaiter.
    with lock:
        return function(*args, **kwargs)
