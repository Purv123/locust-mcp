from locust import HttpUser, task, between
import random

class JsonPlaceholderUser(HttpUser):
    wait_time = between(1, 2)  # Random wait between requests

    @task
    def get_posts(self):
        self.client.get("/posts")

    @task
    def get_single_post(self):
        # Get a random post between 1 and 100
        post_id = random.randint(1, 100)
        self.client.get(f"/posts/{post_id}")

    @task
    def create_post(self):
        payload = {
            "title": "Test post",
            "body": "This is a test post",
            "userId": random.randint(1, 10)
        }
        self.client.post("/posts", json=payload)
