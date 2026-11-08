import asyncio

_running: set = set()


def spawn(coro) -> None:
    """Run a coroutine in the background (keeping a reference so it is not garbage collected)."""
    task = asyncio.create_task(coro)
    _running.add(task)
    task.add_done_callback(_running.discard)
