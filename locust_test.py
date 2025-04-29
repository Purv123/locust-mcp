from locust import HttpUser, task, between

class PerformanceTest(HttpUser):
    host = "https://fake-json-api.mock.beeceptor.com"
    wait_time = between(1, 5)

    @task(1)
    def test_get_1(self):
        self.client.get("/users")
