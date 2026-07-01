from quant_assistant.data.providers.rate_limiter import SerialRateLimiter


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def test_serial_rate_limiter_waits_between_calls():
    clock = FakeClock()
    limiter = SerialRateLimiter(
        min_interval=1.0,
        jitter=0.0,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    limiter.wait()
    limiter.wait()

    assert clock.sleeps == [1.0]
