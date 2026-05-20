from locust import HttpUser, task, between


class ApiUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(3)
    def trips(self):
        self.client.get("/api/trips/daily")

    @task(3)
    def weather(self):
        self.client.get("/api/weather/daily")

    @task(2)
    def correlation(self):
        self.client.get("/api/correlation/")

    @task(1)
    def health(self):
        self.client.get("/api/health")
