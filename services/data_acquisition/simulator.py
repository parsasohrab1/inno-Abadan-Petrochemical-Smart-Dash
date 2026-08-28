"""شبیه‌ساز فیزیکی مجتمع — منبع داده‌ی واقع‌گرایانه برای پایپ‌لاین CBM.

نکته: این شبیه‌ساز جایگزینِ «سنسور واقعی» است نه جایگزین منطق پردازش. کل مسیر
پردازش سیگنال، تشخیص AI، RUL، سلامت سنسور، اقتصاد و Auto Operation روی خروجی
این شبیه‌ساز به‌صورت واقعی اجرا می‌شود. با اتصال سنسور واقعی، فقط این ماژول
با `mqtt_bridge` جایگزین می‌شود.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np

from ml.datagen.acoustic import leak_index, synth_acoustic
from ml.datagen.process import line_flow_tph, power_draw_kw, process_point
from ml.datagen.sensor_health import next_status, synth_health_metrics
from ml.datagen.vibration import WaveformSpec, degrade_severity, synth_waveform
from services.common.bus import EventBus
from services.common.clients import asset_registry
from services.common.config import get_settings
from services.common.domain.enums import FaultType, HealthColor
from services.common.domain.faults import ALL_FAULTS
from services.common.domain.health import evaluate_device_health
from services.common.logging import get_logger
from services.common.tsdb import tsdb

log = get_logger("data-acquisition.sim")
_settings = get_settings()
_RNG = np.random.default_rng(20260828)


@dataclass
class EquipmentSim:
    tag: str
    etype: str
    rpm: float
    rated_kw: float
    line_code: str
    product: str | None
    design_rate_tph: float
    running: bool = True
    fault: FaultType = FaultType.NORMAL
    onset_h: float = 0.0            # ساعت شبیه‌سازی که عیب شروع شد
    ttf_h: float = 0.0             # زمان تا خرابی از لحظه‌ی شروع
    severity: float = 0.0
    sensors: list[dict] = field(default_factory=list)
    health: dict[str, HealthColor] = field(default_factory=dict)

    def step(self, sim_hours: float) -> None:
        if not self.running:
            self.severity = max(self.severity, 0.0)
            return
        # شروع تصادفی عیب
        if self.fault == FaultType.NORMAL and _RNG.random() < 0.0008:
            candidates = [f for f in ALL_FAULTS if f != FaultType.NORMAL]
            self.fault = candidates[int(_RNG.integers(0, len(candidates)))]
            self.onset_h = sim_hours
            self.ttf_h = float(_RNG.uniform(180, 1400))
            log.info("sim.fault.onset", tag=self.tag, fault=self.fault, ttf_h=round(self.ttf_h))
        if self.fault != FaultType.NORMAL:
            self.severity = degrade_severity(sim_hours - self.onset_h, self.ttf_h)


class PlantSimulator:
    def __init__(self, speedup: float = 720.0, frame_interval_s: float = 2.0) -> None:
        # speedup: هر ثانیه‌ی واقعی = speedup ثانیه‌ی شبیه‌سازی (پیش‌فرض ۱۲ دقیقه)
        self.speedup = speedup
        self.frame_interval_s = frame_interval_s
        self.equipment: list[EquipmentSim] = []
        self.bus = EventBus("data-acquisition")
        self._t0 = time.monotonic()

    @property
    def sim_hours(self) -> float:
        return (time.monotonic() - self._t0) * self.speedup / 3600.0

    async def load_assets(self) -> None:
        ar = asset_registry()
        for _ in range(30):
            try:
                equipment = await ar.get("/equipment", params={"limit": 5000})
                break
            except Exception as exc:  # noqa: BLE001
                log.warning("sim.assets.wait", error=str(exc))
                await asyncio.sleep(3)
        else:
            log.error("sim.assets.unavailable")
            await ar.aclose()
            return

        for e in equipment:
            try:
                full = await ar.get(f"/equipment/{e['tag']}/full")
            except Exception:  # noqa: BLE001
                full = {"sensors": []}
            self.equipment.append(
                EquipmentSim(
                    tag=e["tag"],
                    etype=e["etype"],
                    rpm=e.get("rpm_nominal") or 1480.0,
                    rated_kw=e.get("rated_power_kw") or 75.0,
                    line_code="",
                    product=None,
                    design_rate_tph=0.0,
                    running=e.get("run_state") == "running",
                    sensors=full.get("sensors", []),
                    health={s["tag"]: HealthColor(s.get("health", "green")) for s in full.get("sensors", [])},
                )
            )
        await ar.aclose()
        log.info("sim.assets.loaded", equipment=len(self.equipment))

    async def run(self) -> None:
        await self.bus.start()
        await self.load_assets()
        if not self.equipment:
            log.error("sim.no_equipment.abort")
            return
        health_tick = 0
        while True:
            sh = self.sim_hours
            await self._emit_cycle(sh)
            health_tick += 1
            if health_tick % 15 == 0:
                await self._emit_health(sh)
            await asyncio.sleep(self.frame_interval_s)

    async def _emit_cycle(self, sim_hours: float) -> None:
        now = datetime.now(timezone.utc).isoformat()
        # هر چرخه زیرمجموعه‌ای از تجهیزات را نمونه‌برداری می‌کند (شبیه اسکن راند رابین)
        batch = _RNG.choice(self.equipment, size=min(24, len(self.equipment)), replace=False)
        for eq in batch:
            eq.step(sim_hours)
            vib_sensors = [s for s in eq.sensors if s["kind"] == "accelerometer_triax"]
            if not vib_sensors:
                continue
            spec = WaveformSpec(rpm=eq.rpm)
            for s in vib_sensors[:3]:  # سه محور یک یاتاقان کافی است
                wave = synth_waveform(eq.fault, eq.severity, spec, _RNG)
                await self.bus.publish(
                    _settings.kafka_topic_vibration,
                    {
                        "sensor_tag": s["tag"],
                        "equipment_tag": eq.tag,
                        "axis": s.get("axis") or "X",
                        "ts": now,
                        "sample_rate_hz": spec.fs,
                        "unit": "g",
                        "rpm": eq.rpm,
                        "samples": wave.round(5).tolist(),
                    },
                    key=eq.tag,
                )
            # process readings
            load = 0.6 if eq.running else 0.0
            for s in eq.sensors:
                if s["kind"] in {"pressure", "temperature_rtd", "temperature_tc", "level"}:
                    nominal = (s["range"][0] + s["range"][1]) / 2.0
                    val = process_point(s["kind"], nominal, sim_hours * 3600, _RNG)
                    await self.bus.publish(
                        _settings.kafka_topic_process,
                        {"sensor_tag": s["tag"], "equipment_tag": eq.tag, "kind": s["kind"],
                         "ts": now, "value": val, "unit": s["unit"]},
                        key=eq.tag,
                    )
            # acoustic leak index
            us = [s for s in eq.sensors if s["kind"] == "ultrasonic_mic"]
            if us:
                leak_sev = eq.severity if eq.fault == FaultType.CAVITATION else 0.0
                aw = synth_acoustic(leak_severity=leak_sev, friction_severity=0.5 * eq.severity, rng=_RNG)
                await self.bus.publish(
                    _settings.kafka_topic_acoustic,
                    {"sensor_tag": us[0]["tag"], "equipment_tag": eq.tag, "ts": now,
                     "unit": "dB", "leak_index": leak_index(aw, 48000.0),
                     "sample_rate_hz": 48000.0, "samples": aw[:2048].round(5).tolist()},
                    key=eq.tag,
                )
            pwr = power_draw_kw(eq.rated_kw, load, _RNG)
            tsdb.write_reading("equipment_power", {"equipment_tag": eq.tag}, {"kw": pwr})

    async def _emit_health(self, sim_hours: float) -> None:
        now = datetime.now(timezone.utc).isoformat()
        for eq in _RNG.choice(self.equipment, size=min(40, len(self.equipment)), replace=False):
            for s in eq.sensors:
                cur = eq.health.get(s["tag"], HealthColor.GREEN)
                nxt = next_status(cur, _RNG)
                eq.health[s["tag"]] = nxt
                metrics = synth_health_metrics(nxt, _RNG)
                result = evaluate_device_health(metrics)
                await self.bus.publish(
                    "telemetry.device_health",
                    {
                        "device_tag": s["tag"], "device_type": "sensor", "ts": now,
                        "status": result.status, "reasons": result.reasons,
                        "metrics": {
                            "supply_voltage": round(metrics.supply_voltage, 2),
                            "loop_current_ma": round(metrics.loop_current_ma, 2),
                            "snr_db": round(metrics.snr_db, 1),
                            "calibration_drift_pct": round(metrics.calibration_drift_pct, 2),
                            "comm_latency_ms": round(metrics.comm_latency_ms, 1),
                            "device_temp_c": round(metrics.device_temp_c, 1),
                        },
                    },
                    key=s["tag"],
                )
