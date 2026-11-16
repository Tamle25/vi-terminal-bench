"""Process-local runtime clock adapter, versioned outside the frozen model harness.

WSL wall time can step backwards between capture and gate validation. UTC is
anchored once to CLOCK_BOOTTIME, which includes suspended time. The existing
validator still enforces its unchanged validity window, identity and policy.
No system clock, provider client, prompt, budget or dataset is modified.
"""
from contextlib import contextmanager
import datetime as dt
import hashlib
import os
from pathlib import Path
import time
from types import SimpleNamespace

POLICY = 'dashboard-boottime-utc-v1'


class RuntimeClock:
    def __init__(self, wall=None, elapsed=None):
        if elapsed is None:
            if not hasattr(time, 'CLOCK_BOOTTIME'):
                raise ValueError('SUSPEND_AWARE_CLOCK_REQUIRED')
            elapsed = lambda: time.clock_gettime_ns(time.CLOCK_BOOTTIME)
        self.elapsed = elapsed
        before = elapsed()
        self.utc_anchor = (wall or (lambda: dt.datetime.now(dt.timezone.utc)))()
        self.elapsed_anchor = elapsed()
        if self.elapsed_anchor < before or self.utc_anchor.tzinfo is None:
            raise ValueError('INVALID_RUNTIME_CLOCK_ANCHOR')
        self.last = self.elapsed_anchor
        self.owner = os.getpid()

    def now(self, tz=None):
        current = self.elapsed()
        if os.getpid() != self.owner or current < self.last:
            raise ValueError('RUNTIME_CLOCK_REGRESSED_OR_PROCESS_CHANGED')
        self.last = current
        value = self.utc_anchor + dt.timedelta(microseconds=(current - self.elapsed_anchor) // 1000)
        return value.astimezone(tz) if tz is not None else value.astimezone().replace(tzinfo=None)

    def receipt(self):
        boot = Path('/proc/sys/kernel/random/boot_id')
        return {'policy': POLICY, 'scope': 'process-local-runtime-capture-and-validation',
                'utc_anchor': self.utc_anchor.isoformat(), 'boottime_anchor_ns': self.elapsed_anchor,
                'clock': 'CLOCK_BOOTTIME', 'includes_suspend': True, 'pid': self.owner,
                'boot_id': boot.read_text(encoding='ascii').strip() if boot.is_file() else None,
                'adapter_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'original_validator_and_ttl_unchanged': True, 'system_clock_modified': False}


@contextmanager
def stable_runtime_clock(dev, clock=None):
    import pilot_contracts
    import capture_runtime_development
    clock = clock or RuntimeClock()
    class RuntimeDateTime(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return clock.now(tz)
    facade = SimpleNamespace(datetime=RuntimeDateTime, timezone=dt.timezone, timedelta=dt.timedelta)
    original_validator_dt = pilot_contracts.dt
    original_capture_dt = capture_runtime_development.dt
    original_capture = dev.capture
    def capture(*args, **kwargs):
        report = original_capture(*args, **kwargs)
        report['runtime_clock'] = clock.receipt()
        report['observed_system_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
        return report
    try:
        pilot_contracts.dt = facade
        capture_runtime_development.dt = facade
        dev.capture = capture
        yield clock
    finally:
        dev.capture = original_capture
        capture_runtime_development.dt = original_capture_dt
        pilot_contracts.dt = original_validator_dt
