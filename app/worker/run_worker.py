"""Run the arq worker. Usage: python -m app.worker.run_worker"""

import logging

from arq import run_worker

from app.worker.worker_settings import WorkerSettings

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    try:
        run_worker(WorkerSettings)
    except KeyboardInterrupt:
        print("\nWorker stopped.")
