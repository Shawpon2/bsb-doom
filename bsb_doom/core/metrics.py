import time
import statistics
from collections import defaultdict

class MetricsCollector:
    def __init__(self):
        self.total_requests = 0
        self.error_count = 0
        self.latencies = []
        self.attack_stats = defaultdict(lambda: {'total': 0, 'errors': 0})
        self.start_time = time.time()
        self.peak_rps = 0

    def record_request(self, success, latency, attack, error=None):
        self.total_requests += 1
        if not success:
            self.error_count += 1
        self.latencies.append(latency)
        self.attack_stats[attack]['total'] += 1
        if not success:
            self.attack_stats[attack]['errors'] += 1

        # Update peak RPS
        elapsed = time.time() - self.start_time
        if elapsed > 0:
            current_rps = self.total_requests / elapsed
            if current_rps > self.peak_rps:
                self.peak_rps = current_rps

    def error_rate(self):
        return self.error_count / self.total_requests if self.total_requests else 0

    def requests_per_second(self):
        elapsed = time.time() - self.start_time
        return self.total_requests / elapsed if elapsed else 0

    def avg_latency(self):
        return statistics.mean(self.latencies) if self.latencies else 0

    def percentile(self, p):
        if not self.latencies:
            return 0
        return statistics.quantiles(self.latencies, n=100)[p-1]

    @property
    def current_rps(self):
        return self.requests_per_second()
