import asyncio
import contextlib
import unittest
import stubs

stubs.install()
from core.helpers import cancel_and_wait  # noqa: E402


async def _sleeper():
    await asyncio.sleep(3600)          # как autoupdate_loop: CancelledError уходит наружу


async def _swallower():
    try:
        await asyncio.sleep(3600)
    except asyncio.CancelledError:     # как autosave_loop: гасит отмену
        return


class Shutdown(unittest.TestCase):
    def test_old_pattern_loses_the_rest_of_finally(self):
        """Воспроизводим баг: suppress(Exception) не ловит CancelledError задачи."""
        async def run():
            reached = []
            t = asyncio.create_task(_sleeper())
            await asyncio.sleep(0)
            try:
                try:
                    t.cancel()
                    with contextlib.suppress(Exception):
                        await t
                    reached.append("stop-message")
                except asyncio.CancelledError:
                    pass
            finally:
                pass
            return reached
        self.assertEqual(asyncio.run(run()), [])   # до «сообщения» не дошли

    def test_cancel_and_wait_lets_shutdown_continue(self):
        async def run():
            reached = []
            tasks = [asyncio.create_task(_swallower()), None, asyncio.create_task(_sleeper())]
            await asyncio.sleep(0)
            await cancel_and_wait(tasks)
            reached.append("stop-message")
            return reached, [t.done() for t in tasks if t]
        reached, done = asyncio.run(run())
        self.assertEqual(reached, ["stop-message"])
        self.assertTrue(all(done))

    def test_already_finished_tasks_are_fine(self):
        async def run():
            t = asyncio.create_task(asyncio.sleep(0))
            await t
            await cancel_and_wait([t])
            return True
        self.assertTrue(asyncio.run(run()))


if __name__ == "__main__":
    unittest.main()


class LogWorkerStop(unittest.TestCase):
    def test_stop_log_worker_does_not_leak_cancelled_error(self):
        from core import logging_channel as lc

        async def run():
            lc._log_worker_task = asyncio.create_task(_sleeper())
            await asyncio.sleep(0)
            await lc.stop_log_worker()          # раньше бросал CancelledError и обрывал остановку
            return lc._log_worker_task.done()
        self.assertTrue(asyncio.run(run()))
