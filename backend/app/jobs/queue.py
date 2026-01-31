import queue
import threading
from typing import Any
from sqlalchemy.orm import Session
from app.database import SessionLocal
import asyncio


class JobQueue:
    """Simple job queue for running lead generation tasks."""

    def __init__(self):
        # Use thread-safe queue instead of asyncio.Queue
        self._queue = queue.Queue()
        print("[JobQueue] Initialized internal queue")
        self._worker_thread = None

    def start_worker(self):
        """Start the background worker."""
        if self._worker_thread is None:
            print("Starting background job queue worker...")
            # Run worker in a new thread with its own event loop
            self._worker_thread = threading.Thread(target=self._run_worker_thread, daemon=True)
            self._worker_thread.start()
            print("Background worker thread started")

    def _run_worker_thread(self):
        """Run worker in a separate thread."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            print("Worker thread started, beginning to process jobs...")
            loop.run_until_complete(self._worker())
        except Exception as e:
            print(f"Worker thread error: {e}")
            import traceback
            traceback.print_exc()

    async def _worker(self):
        """Process jobs from the queue."""
        from app.agents.orchestrator import AgentOrchestrator

        while True:
            try:
                # print("[JobQueue] Worker waiting for job...")
                run_id = self._queue.get(timeout=1)
                print(f"[JobQueue] Worker got job: {run_id}")
            except queue.Empty:
                await asyncio.sleep(0.5)
                continue

            try:
                print(f"Processing run {run_id}")
                db = SessionLocal()
                orchestrator = AgentOrchestrator(db)
                await orchestrator.execute_run(run_id)
                db.close()
                print(f"Completed run {run_id}")
            except Exception as e:
                print(f"Error processing run {run_id}: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self._queue.task_done()

    def enqueue(self, run_id: str):
        """Add a run to the queue (synchronous)."""
        print(f"[JobQueue] Enqueuing run_id: {run_id}")
        self._queue.put(run_id)
        print(f"Enqueued run {run_id}")


# Global job queue instance
job_queue = JobQueue()
