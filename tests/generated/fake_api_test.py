from locust import HttpUser, task, between

class FakeApiUser(HttpUser):
    host = "https://fake-json-api.mock.beeceptor.com"
    wait_time = between(1, 2)  # Random wait between requests

    @task
    def get_users(self):
        self.client.get("/users", verify=False)  # Disable SSL verification for testing
