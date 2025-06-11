from services.rate_limiter import RateLimiter


def test_rate_limiter():
    rate_limiter = RateLimiter(sustained_rate=1.0, burst_size=10)

    watermark = None
    for i in range(10):
        allowed, new_watermark = rate_limiter.try_make_request(watermark)
        assert allowed
        assert new_watermark > watermark if watermark is not None else True
        watermark = new_watermark

    allowed, watermark = rate_limiter.try_make_request(watermark)
    assert not allowed

    watermark = watermark - rate_limiter._request_cost

    allowed, watermark = rate_limiter.try_make_request(watermark)
    assert allowed
