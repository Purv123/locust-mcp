from locust import HttpUser, task, between

class PerformanceTest(HttpUser):
    host = ""  # Base URL without path
    wait_time = between(1, 5)

    def on_start(self):
        # Set default headers that will be used for all requests
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "x-sf-token": "hLSs0pMv10B2pz6CfGsPjg"
}

    @task(1)
    def test_get_1(self):
        path = ""
        self.client.get(path, headers=self.headers)