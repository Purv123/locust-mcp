from locust import HttpUser, task, between

class PerformanceTest(HttpUser):
    host = ""  # Base URL without path
    wait_time = between(1, 5)

    def on_start(self):
        # Set default headers that will be used for all requests
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "x-sf-token": "hLSs0pMv10B2pz6CfGsPjg",
            "accept-language": "en-US,en;q=0.9",
            "origin": "https://app.mon0.signalfx.com",
            "referer": "https://app.mon0.signalfx.com/"
}

    @task(1)
    def test_get_1(self):
        path = ""
        self.client.get(path, headers=self.headers)