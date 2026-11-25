# Debugging Physics Models in Docker

> **✅ RESOLVED (2026-10-19)** — The fix below (Option 1) was implemented in `runner.py`:
> signal handling moved out of `__init__` into `_install_signal_handlers()`, which uses
> `asyncio.get_running_loop().add_signal_handler()` called from inside `run()`. The Docker
> container now starts and produces to Kafka at 1 Hz. This document is kept as a debugging
> reference for the record.

## Problem Summary

Running `physics_models.runner` inside Docker container works for manual single-tick tests but hangs when calling `runner.run()` (the main async loop).

## Working Scenarios

1. **Manual single tick** - Works perfectly:
   ```python
   runner = SimulatorRunner(config)
   state = runner._tick_state_engine(current_tick, met)
   thermal = runner._tick_thermal(current_tick, met)
   # ... all model ticks work
   runner._send_to_kafka(...)
   runner.producer.flush()
   ```

2. **Manual async loop with explicit stop after N ticks** - Works:
   ```python
   async def test():
       runner.running = True
       runner._start_time = datetime.now(UTC)
       runner._tick_count = 0
       while runner.running and runner._tick_count < 2:
           # ... tick logic ...
           runner._tick_count += 1
           await asyncio.sleep(sleep_time)
   asyncio.run(test())
   ```

## Failing Scenario

**Calling `runner.run()` directly** - Hangs indefinitely (no output, no error):
```python
runner = SimulatorRunner(config)
asyncio.run(runner.run())  # Never returns, no prints appear
```

## Key Observations

### Signal Handlers
The `SimulatorRunner.__init__` sets up signal handlers:
```python
signal.signal(signal.SIGINT, self._signal_handler)
signal.signal(signal.SIGTERM, self._signal_handler)
```

When running inside Docker with `timeout` command, the timeout sends SIGTERM which triggers the handler and sets `self.running = False`. However, this should only stop the loop, not prevent it from starting.

### The Hanging Point
The `run()` method starts with:
```python
async def run(self) -> None:
    self.running = True
    self._start_time = datetime.now(UTC)
    print(f"Starting physics models simulation at {self.config.tick_hz} Hz")
    print(f"Liftoff: {self.liftoff_utc.isoformat()}")
    print(f"Kafka: {self.config.kafka.bootstrap_servers}")
    while self.running:
        # ... tick logic ...
```

The print statements at the start of `run()` NEVER appear when calling `asyncio.run(runner.run())`, suggesting the coroutine never actually starts executing.

### Asyncio Event Loop Issue
When calling `asyncio.run(runner.run())`:
- The coroutine is created but may not be scheduled properly
- The signal handlers might interfere with the event loop setup
- Docker's signal handling might be causing issues

## Root Cause Hypothesis

The issue is likely related to **signal handling in Docker combined with asyncio**:

1. `signal.signal()` in `__init__` sets up handlers BEFORE the event loop exists
2. When `asyncio.run()` creates the event loop, it may conflict with existing signal handlers
3. Docker's PID 1 process handling may interfere with signal delivery
4. The `timeout` command sends SIGTERM which triggers the handler immediately

## Workarounds Tested

| Approach | Result |
|----------|--------|
| Disable signal handlers (`signal.signal = lambda *args: None`) | Still hangs |
| Manual async loop with `await asyncio.sleep()` | Works |
| Running inside `docker exec` with `timeout` | Times out |

## Recommended Fix

### Option 1: Remove signal handlers from `__init__`
Move signal handling to the `run()` method or use asyncio's signal handling:

```python
async def run(self) -> None:
    # Set up signal handlers inside the async context
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, self._signal_handler)
    
    self.running = True
    # ... rest of run ...
```

### Option 2: Use a simpler shutdown mechanism
Use a shared event/flag instead of signals for Docker environments:

```python
def __init__(self, config):
    # ... 
    self._shutdown_event = asyncio.Event()
    # Remove signal.signal() calls

async def run(self):
    self.running = True
    while self.running and not self._shutdown_event.is_set():
        # ...
```

### Option 3: Entry point wrapper
Create a separate entry point that handles signals properly:

```python
# docker_entrypoint.py
import asyncio
import signal
from physics_models.runner import SimulatorRunner
from physics_models.config import load_config

async def main():
    config = load_config(...)
    runner = SimulatorRunner(config)
    
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: setattr(runner, 'running', False))
    
    await runner.run()

if __name__ == "__main__":
    asyncio.run(main())
```

## Test Results Summary

| Test | Command | Result |
|------|---------|--------|
| Single tick manual | `docker exec ... python -c "runner._tick_state_engine(...)"` | ✅ Works |
| Full tick cycle manual | `docker exec ... python -c "runner._tick_thermal... runner._send_to_kafka"` | ✅ Works |
| Manual async loop (2 ticks) | `docker exec ... python -c "async def test(): ... asyncio.run(test())"` | ✅ Works |
| `runner.run()` via asyncio.run | `docker exec ... python -c "asyncio.run(runner.run())"` | ❌ Hangs |
| Container CMD | `docker compose up physics_models` | ❌ Hangs (only warning prints) |

## Next Steps

1. **Immediate**: Modify `runner.py` to use `asyncio.get_running_loop().add_signal_handler()` inside `run()` method instead of `signal.signal()` in `__init__`
2. **Alternative**: Create a Docker-specific entry point that properly sets up asyncio signal handling
3. **Test**: Verify the fix works with `docker compose up physics_models`

## Current Docker Configuration

- `docker-compose.yml`: physics_models service depends on redpanda (healthy) and timescaledb (healthy)
- Config: `packages/physics_models/configs/docker.yaml` with `bootstrap_servers: "redpanda:9092"`
- Redpanda advertises `redpanda:9092` (not localhost)
- Image builds with pip install of contracts and physics_models packages