import time

from locust import HttpUser, between, task


class TaskQueueUser(HttpUser):
    """
    Simulates a typical API consumer: submits tasks, polls for
    results, and occasionally lists recent tasks.
    """

    wait_time = between(0.5, 2.0)

    @task(3)
    def submit_and_poll(self):
        """Submit a task, then poll until it completes or times out."""
        resp = self.client.post(
            "/api/v1/tasks",
            json={
                "task_type": "load_test",
                "payload": {"batch": "perf_run"},
                "priority": "normal",
                "max_retries": 1,
            },
        )
        if resp.status_code != 202:
            return

        task_id = resp.json()["task_id"]

        # Poll for completion, up to 30 seconds
        deadline = time.time() + 30
        while time.time() < deadline:
            status_resp = self.client.get(
                f"/api/v1/tasks/{task_id}",
                name="/api/v1/tasks/[id]",
            )
            if status_resp.status_code != 200:
                break

            status = status_resp.json()["status"]
            if status in ("completed", "failed"):
                break

            time.sleep(1)

    @task(2)
    def get_single_task(self):
        """Read a recently submitted task to exercise the cache."""
        # Submit a task to get a valid ID
        resp = self.client.post(
            "/api/v1/tasks",
            json={"task_type": "cache_hit_test"},
        )
        if resp.status_code != 202:
            return

        task_id = resp.json()["task_id"]

        # Read it twice: first populates cache, second hits cache
        self.client.get(
            f"/api/v1/tasks/{task_id}",
            name="/api/v1/tasks/[id]",
        )
        self.client.get(
            f"/api/v1/tasks/{task_id}",
            name="/api/v1/tasks/[id]",
        )

    @task(1)
    def list_tasks(self):
        """List tasks with filtering and pagination."""
        self.client.get("/api/v1/tasks?status=completed&per_page=10&page=1")