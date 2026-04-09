from prometheus_client import Counter, Gauge, Histogram

# Counter: total tasks submitted, labeled by task type
tasks_submitted_total = Counter(
    "tasks_submitted_total",
    "Total number of tasks submitted to the queue",
    labelnames=["task_type"],
)

# Counter: total tasks completed, labeled by task type and final status
tasks_completed_total = Counter(
    "tasks_completed_total",
    "Total number of tasks that reached a terminal state",
    labelnames=["task_type", "status"],
)

# Histogram: task execution duration in seconds
task_duration_seconds = Histogram(
    "task_duration_seconds",
    "Time taken to execute a task from start to completion",
    labelnames=["task_type"],
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300, 600),
)

# Gauge: number of tasks currently being processed across all workers
tasks_in_progress = Gauge(
    "tasks_in_progress",
    "Number of tasks currently in the running state",
)