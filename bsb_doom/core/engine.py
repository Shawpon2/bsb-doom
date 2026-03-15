import asyncio
import aiohttp
import threading
import random
import time
import sys
from concurrent.futures import ThreadPoolExecutor
from .attacks import AttackFactory
from .metrics import MetricsCollector
from ..config import ERROR_THRESHOLD, MAX_WORKER_THREADS

# Try to use uvloop on Unix for better performance (optional)
if sys.platform != 'win32':
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        pass

class LoadTestEngine:
    def __init__(self, target, concurrency, attacks):
        self.target = target
        self.base_concurrency = min(concurrency, MAX_WORKER_THREADS * 10)  # Each thread can run many tasks
        self.attacks = attacks
        self.stop_event = threading.Event()
        self.metrics = MetricsCollector()
        self.failure_load = None
        self.start_time = None
        self.loop = None
        self.tasks = []
        self.executor = ThreadPoolExecutor(max_workers=MAX_WORKER_THREADS)

    async def _attack_worker(self, attack_name, session):
        attack = AttackFactory.get_attack(attack_name, self.target)
        while not self.stop_event.is_set():
            try:
                start = time.perf_counter()
                result = await attack.execute(session)
                latency = time.perf_counter() - start
                self.metrics.record_request(result.success, latency, attack_name, result.error)
            except Exception as e:
                self.metrics.record_request(False, 0, attack_name, str(e))
            await asyncio.sleep(0)  # yield

    async def _run_async_tasks(self):
        connector = aiohttp.TCPConnector(limit=0, ttl_dns_cache=300, force_close=True)
        session = aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=30))

        # Create tasks for each attack method (distribute concurrency)
        tasks_per_method = self.base_concurrency // len(self.attacks)
        for attack_name in self.attacks:
            for _ in range(tasks_per_method):
                task = asyncio.create_task(self._attack_worker(attack_name, session))
                self.tasks.append(task)

        # Wait until stop_event is set
        while not self.stop_event.is_set():
            await asyncio.sleep(1)

        # Cancel all tasks and cleanup
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        await session.close()

    def _run_async(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._run_async_tasks())
        self.loop.close()

    def _monitor_health(self):
        """Monitor error rate and set stop_event if threshold exceeded."""
        while not self.stop_event.is_set():
            time.sleep(2)
            if self.metrics.total_requests > 100:
                error_rate = self.metrics.error_rate()
                if error_rate > ERROR_THRESHOLD:
                    self.failure_load = self.metrics.current_rps
                    self.stop_event.set()
                    break

    def start(self):
        self.start_time = time.time()
        # Start async loop in a separate thread
        async_thread = threading.Thread(target=self._run_async, daemon=True)
        async_thread.start()

        # Start health monitor in another thread
        monitor_thread = threading.Thread(target=self._monitor_health, daemon=True)
        monitor_thread.start()

        # Wait for stop event (main thread can continue)
        # We'll keep a reference to threads for cleanup

    def stop(self):
        self.stop_event.set()
        # Allow threads to exit
        time.sleep(1)

    def get_metrics(self):
        return self.metrics
