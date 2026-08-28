"""ساخت سلسله‌مراتب دارایی پتروشیمی آبادان و نگاشت کامل سنسور/دوربین.

طبق README §۱-۳ و §۸-۱ و الزام کاربر:
«تمامی تجهیزات و خط تولید زیر سنسور و دوربین مرتبط باشند».

هر تجهیز دوار: شتاب‌سنج سه‌محوره روی یاتاقان DE و NDE + velometer + (برای کمپرسور/توربین)
proximity probe + سنسورهای فرآیندی (فشار/دما/دبی) + پوشش دوربین حرارتی و CCTV.
هر خط تولید: فلومتر خوراک/محصول + دوربین حرارتی + دوربین AI-CCTV + گازسنج واحد.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from services.common.domain.enums import (
    CameraKind,
    Criticality,
    EquipmentRunState,
    EquipmentType,
    SensorKind,
)
from services.common.domain.enums import DEFAULT_UNIT
from services.common.domain.models import (
    Camera,
    CameraCoverage,
    Component,
    Equipment,
    Plant,
    ProductionLine,
    Sensor,
    SensorMount,
    Unit,
)

RNG = random.Random(1346)  # سال تأسیس مجتمع — تکرارپذیری

# (کد واحد، عنوان، [(کد خط, عنوان, محصول, ظرفیت t/h)])
PLANT_LAYOUT: list[tuple[str, str, list[tuple[str, str, str, float]]]] = [
    ("200-300", "واحد ۲۰۰/۳۰۰ — کلر-آلکالی و EDC", [
        ("CA-EL", "سلول‌های الکترولیز کلر-آلکالی", "Caustic", 3.8),
        ("EDC-01", "تولید EDC", "EDC", 4.5),
    ]),
    ("400-500", "واحد ۴۰۰/۵۰۰ — VCM", [
        ("VCM-01", "کراکینگ EDC به VCM", "VCM", 3.2),
        ("VCM-REC", "بازیافت HCl و VCM", "VCM", 1.1),
    ]),
    ("600-700", "واحد ۶۰۰/۷۰۰ — پلیمریزاسیون PVC", [
        ("PVC-A", "خط پلیمریزاسیون PVC A", "PVC", 3.5),
        ("PVC-B", "خط پلیمریزاسیون PVC B", "PVC", 3.5),
    ]),
    ("800-900", "واحد ۸۰۰/۹۰۰ — خشک‌کن و بسته‌بندی PVC", [
        ("PVC-DRY", "خشک‌کن بستر سیال PVC", "PVC", 7.0),
    ]),
    ("1000", "واحد ۱۰۰۰ — سرویس‌های جانبی (Utilities)", [
        ("UTIL-AIR", "هوای فشرده و ابزار دقیق", "", 0.0),
        ("UTIL-CW", "آب خنک‌کننده", "", 0.0),
        ("UTIL-STM", "بویلر و بخار", "", 0.0),
    ]),
    ("PVC-NEW", "واحد جدید تولید PVC", [
        ("PVC-N1", "راکتور جدید PVC", "PVC", 6.2),
    ]),
    ("TETRAMER", "واحد تترامر", [
        ("TET-01", "پلیمریزاسیون تترامر پروپیلن", "Tetramer", 1.3),
    ]),
    ("DDB-NEW", "واحد دودسیل‌بنزن", [
        ("DDB-01", "آلکیلاسیون بنزن", "DDB", 1.2),
    ]),
    ("TANKFARM", "مخازن ذخیره و خطوط لوله", [
        ("TF-EDC", "مخازن EDC/VCM", "", 0.0),
        ("TF-PROD", "مخازن محصول و بارگیری", "", 0.0),
    ]),
]

# انواع تجهیز به‌ازای هر خط (نمونه‌ی معرف)
LINE_EQUIPMENT_TEMPLATE: list[tuple[str, EquipmentType, Criticality, bool]] = [
    ("Feed Pump", EquipmentType.PUMP, Criticality.HIGH, True),
    ("Transfer Pump", EquipmentType.PUMP, Criticality.MEDIUM, True),
    ("Reflux Pump", EquipmentType.PUMP, Criticality.MEDIUM, False),
    ("Process Compressor", EquipmentType.COMPRESSOR, Criticality.SAFETY_CRITICAL, True),
    ("Recycle Compressor", EquipmentType.COMPRESSOR, Criticality.HIGH, False),
    ("Cooling Fan", EquipmentType.FAN, Criticality.MEDIUM, False),
    ("Induced Draft Fan", EquipmentType.FAN, Criticality.MEDIUM, True),
    ("Agitator Motor", EquipmentType.MOTOR, Criticality.HIGH, False),
    ("Vacuum Pump", EquipmentType.PUMP, Criticality.LOW, True),
    ("Charge Turbine", EquipmentType.TURBINE, Criticality.SAFETY_CRITICAL, False),
]


def _tag(unit: str, line: str, i: int, etype: EquipmentType) -> str:
    prefix = {
        EquipmentType.PUMP: "P", EquipmentType.COMPRESSOR: "K", EquipmentType.FAN: "F",
        EquipmentType.MOTOR: "M", EquipmentType.TURBINE: "T", EquipmentType.REACTOR: "R",
        EquipmentType.HEAT_EXCHANGER: "E", EquipmentType.COLUMN: "C", EquipmentType.VESSEL: "V",
    }[etype]
    return f"{prefix}-{line}-{i:02d}"


def _mk_sensor(
    tag: str, kind: SensorKind, rmin: float, rmax: float, rate: float, proto: str = "MQTT"
) -> Sensor:
    return Sensor(
        tag=tag,
        kind=kind,
        unit_of_measure=DEFAULT_UNIT[kind],
        range_min=rmin,
        range_max=rmax,
        sample_rate_hz=rate,
        protocol=proto,
        installed_at=datetime.now(timezone.utc) - timedelta(days=RNG.randint(30, 3000)),
        last_calibration=datetime.now(timezone.utc) - timedelta(days=RNG.randint(0, 120)),
    )


def build(session: Session) -> dict[str, int]:
    if session.exec(select(Plant)).first():
        return {"skipped": 1}

    plant = Plant()
    session.add(plant)
    session.flush()

    n_eq = n_sensor = n_camera = 0

    for u_code, u_title, lines in PLANT_LAYOUT:
        unit = Unit(
            plant_id=plant.id,
            code=u_code,
            title=u_title,
            criticality=Criticality.HIGH if u_code in {"400-500", "PVC-NEW"} else Criticality.MEDIUM,
        )
        session.add(unit)
        session.flush()

        # گازسنج‌های واحد (README §۳-۴)
        for g in range(RNG.randint(3, 6)):
            gs = _mk_sensor(f"GD-{u_code}-{g:02d}", SensorKind.GAS_DETECTOR, 0, 100, 1.0, "OPC-UA")
            session.add(gs)
            session.flush()
            session.add(SensorMount(sensor_id=gs.id, unit_id=unit.id, measured_quantity="gas_ppm"))
            n_sensor += 1

        for l_code, l_title, product, rate in lines:
            line = ProductionLine(
                unit_id=unit.id, code=l_code, title=l_title,
                product=product or None, design_rate_tph=rate or None,
            )
            session.add(line)
            session.flush()

            # ---- دوربین‌ها و فلومتر سطح خط (الزام: هر خط زیر دوربین/سنسور) ----
            for cam_kind, purpose in [
                (CameraKind.THERMAL, "thermal"),
                (CameraKind.AI_CCTV, "flame,smoke,leak,intrusion"),
            ]:
                cam = Camera(
                    tag=f"CAM-{l_code}-{cam_kind.value[:3].upper()}",
                    kind=cam_kind,
                    unit_of_measure=DEFAULT_UNIT[cam_kind],
                    resolution="640x480" if cam_kind == CameraKind.THERMAL else "1920x1080",
                    fps=9.0 if cam_kind == CameraKind.THERMAL else 25.0,
                )
                session.add(cam)
                session.flush()
                session.add(CameraCoverage(camera_id=cam.id, unit_id=unit.id, line_id=line.id, purpose=purpose))
                n_camera += 1

            if product:
                for q, kind, rng in [
                    ("feed", SensorKind.FLOW_METER, (0, rate * 1.5 or 10)),
                    ("product", SensorKind.FLOW_METER, (0, rate * 1.5 or 10)),
                ]:
                    fm = _mk_sensor(f"FT-{l_code}-{q}", kind, rng[0], rng[1], 1.0, "OPC-UA")
                    session.add(fm)
                    session.flush()
                    session.add(SensorMount(
                        sensor_id=fm.id, unit_id=unit.id, line_id=line.id,
                        measured_quantity=f"{q}_flow",
                    ))
                    n_sensor += 1

            # ---- تجهیزات خط ----
            spares: list[Equipment] = []
            for i, (name, etype, crit, has_spare) in enumerate(LINE_EQUIPMENT_TEMPLATE, start=1):
                if RNG.random() < 0.25 and etype in {EquipmentType.TURBINE}:
                    continue  # همه‌ی خطوط توربین ندارند
                rpm = {
                    EquipmentType.PUMP: RNG.choice([1480, 2960, 3560]),
                    EquipmentType.COMPRESSOR: RNG.choice([6300, 8200, 11000]),
                    EquipmentType.FAN: RNG.choice([740, 990, 1480]),
                    EquipmentType.MOTOR: RNG.choice([990, 1480, 2960]),
                    EquipmentType.TURBINE: RNG.choice([8000, 10500]),
                }.get(etype, 1480)
                eq = Equipment(
                    line_id=line.id,
                    tag=_tag(u_code, l_code, i, etype),
                    name=name,
                    etype=etype,
                    manufacturer=RNG.choice(["Siemens", "Sulzer", "MAN", "Flowserve", "Ebara", "MHI"]),
                    install_year=RNG.randint(1968, 2022),
                    rpm_nominal=rpm,
                    rated_power_kw=RNG.choice([37, 75, 160, 355, 800, 2500]),
                    criticality=crit,
                    has_spare=has_spare,
                    run_state=EquipmentRunState.RUNNING,
                )
                session.add(eq)
                session.flush()
                n_eq += 1

                # اجزا: یاتاقان DE/NDE + شفت + محرک
                comp_ids: dict[str, int] = {}
                for ctype, pos in [("bearing", "DE"), ("bearing", "NDE"), ("shaft", None), ("motor", None)]:
                    c = Component(equipment_id=eq.id, ctype=ctype, position=pos)
                    session.add(c)
                    session.flush()
                    comp_ids[f"{ctype}-{pos}"] = c.id

                # شتاب‌سنج سه‌محوره روی هر یاتاقان
                for pos in ("DE", "NDE"):
                    for axis in ("X", "Y", "Z"):
                        s = _mk_sensor(
                            f"{eq.tag}-VIB-{pos}-{axis}", SensorKind.ACCELEROMETER_TRIAX,
                            0, 50, 25600.0, "IEPE",
                        )
                        session.add(s)
                        session.flush()
                        session.add(SensorMount(
                            sensor_id=s.id, equipment_id=eq.id,
                            component_id=comp_ids[f"bearing-{pos}"], axis=axis,
                            measured_quantity="vibration_acceleration",
                        ))
                        n_sensor += 1
                # velometer بدنه
                v = _mk_sensor(f"{eq.tag}-VEL", SensorKind.VELOMETER, 0, 100, 1000.0)
                session.add(v)
                session.flush()
                session.add(SensorMount(sensor_id=v.id, equipment_id=eq.id, measured_quantity="vibration_velocity"))
                n_sensor += 1

                # proximity probe برای کمپرسور/توربین
                if etype in {EquipmentType.COMPRESSOR, EquipmentType.TURBINE}:
                    for axis in ("X", "Y"):
                        pp = _mk_sensor(f"{eq.tag}-PRX-{axis}", SensorKind.PROXIMITY_PROBE, 0, 2000, 10000.0)
                        session.add(pp)
                        session.flush()
                        session.add(SensorMount(
                            sensor_id=pp.id, equipment_id=eq.id, axis=axis,
                            measured_quantity="shaft_displacement",
                        ))
                        n_sensor += 1

                # سنسورهای فرآیندی روی تجهیز
                for kind, rng, mq in [
                    (SensorKind.PRESSURE, (0, 40), "discharge_pressure"),
                    (SensorKind.PRESSURE, (0, 10), "suction_pressure"),
                    (SensorKind.TEMPERATURE_RTD, (-10, 200), "bearing_temp"),
                    (SensorKind.TEMPERATURE_RTD, (-10, 150), "process_temp"),
                ]:
                    ps = _mk_sensor(f"{eq.tag}-{kind.value[:2].upper()}-{mq[:4]}", kind, rng[0], rng[1], 1.0, "OPC-UA")
                    session.add(ps)
                    session.flush()
                    session.add(SensorMount(sensor_id=ps.id, equipment_id=eq.id, measured_quantity=mq))
                    n_sensor += 1

                # ultrasonic mic نزدیک یاتاقان/شیر
                um = _mk_sensor(f"{eq.tag}-US", SensorKind.ULTRASONIC_MIC, 0, 120, 44100.0)
                session.add(um)
                session.flush()
                session.add(SensorMount(sensor_id=um.id, equipment_id=eq.id, measured_quantity="ultrasonic_level"))
                n_sensor += 1

                # پوشش دوربین حرارتی اختصاصی برای تجهیزات بحرانی
                if crit in {Criticality.HIGH, Criticality.SAFETY_CRITICAL}:
                    tcam = Camera(
                        tag=f"CAM-{eq.tag}-TH", kind=CameraKind.THERMAL,
                        unit_of_measure=DEFAULT_UNIT[CameraKind.THERMAL], fps=9.0,
                    )
                    session.add(tcam)
                    session.flush()
                    session.add(CameraCoverage(
                        camera_id=tcam.id, unit_id=unit.id, line_id=line.id,
                        equipment_id=eq.id, purpose="thermal_hotspot",
                    ))
                    n_camera += 1

                if has_spare:
                    spares.append(eq)

            # ثبت رابطه‌ی زاپاس: زوج‌های هم‌نوع، یکی standby
            by_type: dict[EquipmentType, list[Equipment]] = {}
            for eq in session.exec(select(Equipment).where(Equipment.line_id == line.id)).all():
                by_type.setdefault(eq.etype, []).append(eq)
            for _etype, group in by_type.items():
                if len(group) >= 2:
                    main_eq, spare_eq = group[0], group[1]
                    spare_eq.spare_of_id = main_eq.id
                    spare_eq.run_state = EquipmentRunState.STANDBY
                    main_eq.has_spare = True
                    session.add(spare_eq)
                    session.add(main_eq)

    # گازسنج‌های سطح مجتمع (hyperspectral) روی واحدهای کلیدی
    for u in session.exec(select(Unit)).all():
        if u.code in {"400-500", "600-700", "PVC-NEW", "TANKFARM", "200-300"}:
            hc = Camera(tag=f"CAM-{u.code}-HS", kind=CameraKind.HYPERSPECTRAL,
                       unit_of_measure=DEFAULT_UNIT[CameraKind.HYPERSPECTRAL], fps=2.0)
            session.add(hc)
            session.flush()
            session.add(CameraCoverage(camera_id=hc.id, unit_id=u.id, purpose="gas_leak"))
            n_camera += 1

    session.commit()
    return {"equipment": n_eq, "sensors": n_sensor, "cameras": n_camera}
