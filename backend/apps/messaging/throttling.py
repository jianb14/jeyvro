"""Messaging throttles (§20.2).

`message` throttles sending inside a thread. Starting a thread is a different
shape of abuse — one request per store, unbounded — so it earns its own
`conversation` bucket.

The subtlety is that the starter and the inbox list are the *same* view and
the *same* URL: the SPA reads the inbox and opens threads through one
endpoint. A plain `ScopedRateThrottle` cannot tell them apart, and throttling
the inbox read at 20/hour would make ordinary use impossible — throttling is
not a speed bump on reading (§10.2). So this subclass enforces its rate only
on the method that actually creates something, and waves safe methods through.
"""
from rest_framework.throttling import ScopedRateThrottle


class WriteOnlyScopedRateThrottle(ScopedRateThrottle):
    """A `ScopedRateThrottle` that ignores safe (read) requests.

    DRF has no `SAFE_METHODS` constant on `Throttle`, so the set is declared
    here: these are the methods that create or change nothing, and they must
    not spend a rate bucket.
    """

    SAFE_METHODS = frozenset({'GET', 'HEAD', 'OPTIONS'})

    def allow_request(self, request, view):
        if request.method in self.SAFE_METHODS:
            return True
        return super().allow_request(request, view)
