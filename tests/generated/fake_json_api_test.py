from locust import HttpUser, task, between

class FakeJsonApiUser(HttpUser):
    host = "https://fake-json-api.mock.beeceptor.com"
    wait_time = between(1, 2)

    @task
    def get_users(self):
        self.client.get("/users")
