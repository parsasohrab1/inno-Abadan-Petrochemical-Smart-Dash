"""نقطه‌ی ورود لایه‌ی دریافت داده.

DAQ_SIMULATOR=true  → شبیه‌ساز فیزیکی مجتمع را اجرا می‌کند (پیش‌فرض توسعه)
DAQ_SIMULATOR=false → فقط پل MQTT→Kafka برای سنسورهای واقعی
"""
from __future__ import annotations

import asyncio
import os

from services.common.logging import get_logger
from services.data_acquisition.mqtt_bridge import run as run_bridge
from services.data_acquisition.simulator import PlantSimulator

log = get_logger("data-acquisition")


async def main() -> None:
    use_sim = os.getenv("DAQ_SIMULATOR", "true").lower() == "true"
    tasks = []
    if use_sim:
        sim = PlantSimulator(
            speedup=float(os.getenv("DAQ_SIM_SPEEDUP", "720")),
            frame_interval_s=float(os.getenv("DAQ_SIM_INTERVAL", "2")),
        )
        tasks.append(asyncio.create_task(sim.run()))
        log.info("daq.mode.simulator")
    else:
        log.info("daq.mode.mqtt_bridge")
    tasks.append(asyncio.create_task(_bridge_guarded()))
    await asyncio.gather(*tasks)


async def _bridge_guarded() -> None:
    while True:
        try:
            await run_bridge()
        except Exception as exc:  # noqa: BLE001
            log.warning("daq.bridge.retry", error=str(exc))
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
