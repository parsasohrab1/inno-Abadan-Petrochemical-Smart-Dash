"""امضای فرکانسی ۱۶ عیب تجهیزات دوار (FR-09).

از این جدول هم مولّد داده‌ی سنتتیک (`ml/datagen/vibration.py`) و هم موتور تشخیص
مبتنی بر قاعده در `services/ai_engine` استفاده می‌کنند. مضارب بر حسب فرکانس چرخش (1X).
"""
from __future__ import annotations

from dataclasses import dataclass

from services.common.domain.enums import FaultType


@dataclass(frozen=True)
class FaultSignature:
    fault: FaultType
    fa_name: str                       # نام فارسی
    dominant_orders: tuple[float, ...]  # مضارب فرکانس چرخش که دامنه در آن‌ها بالا می‌رود
    broadband: bool = False            # افزایش انرژی پهن‌باند (مثل کاویتاسیون)
    directionality: str = "radial"     # radial | axial | both
    typical_features: tuple[str, ...] = ()


# ضرایب هندسی فرضی یاتاقان برای محاسبه‌ی فرکانس‌های مشخصه (تعداد ساچمه ۸)
BEARING_BPFO = 3.05   # Ball Pass Frequency Outer  (× rpm/60)
BEARING_BPFI = 4.95   # Ball Pass Frequency Inner
BEARING_BSF = 2.35    # Ball Spin Frequency
BEARING_FTF = 0.38    # Fundamental Train Frequency (cage)

SIGNATURES: dict[FaultType, FaultSignature] = {
    FaultType.NORMAL: FaultSignature(
        FaultType.NORMAL, "سالم", (1.0,), typical_features=("rms_low", "crest_~1.4")
    ),
    FaultType.UNBALANCE: FaultSignature(
        FaultType.UNBALANCE, "نابالانسی", (1.0,), directionality="radial",
        typical_features=("1x_high", "phase_stable"),
    ),
    FaultType.MISALIGNMENT: FaultSignature(
        FaultType.MISALIGNMENT, "ناهم‌محوری", (1.0, 2.0, 3.0), directionality="both",
        typical_features=("2x_high", "axial_1x_high"),
    ),
    FaultType.MECHANICAL_LOOSENESS: FaultSignature(
        FaultType.MECHANICAL_LOOSENESS, "لقی مکانیکی", (0.5, 1.0, 2.0, 3.0, 4.0, 5.0),
        typical_features=("many_harmonics", "half_orders", "high_crest"),
    ),
    FaultType.BEARING_OUTER_RACE: FaultSignature(
        FaultType.BEARING_OUTER_RACE, "عیب رینگ بیرونی یاتاقان", (BEARING_BPFO,),
        broadband=True, typical_features=("bpfo_sidebands", "kurtosis_high", "hf_energy"),
    ),
    FaultType.BEARING_INNER_RACE: FaultSignature(
        FaultType.BEARING_INNER_RACE, "عیب رینگ داخلی یاتاقان", (BEARING_BPFI,),
        broadband=True, typical_features=("bpfi_sidebands_1x", "kurtosis_high"),
    ),
    FaultType.BEARING_BALL: FaultSignature(
        FaultType.BEARING_BALL, "عیب ساچمه یاتاقان", (BEARING_BSF,), broadband=True,
        typical_features=("bsf_modulation_ftf", "kurtosis_high"),
    ),
    FaultType.BEARING_CAGE: FaultSignature(
        FaultType.BEARING_CAGE, "عیب قفسه یاتاقان", (BEARING_FTF,), broadband=True,
        typical_features=("subsync_ftf",),
    ),
    FaultType.ROTOR_RUB: FaultSignature(
        FaultType.ROTOR_RUB, "سایش روتور", (0.5, 1.0, 1.5, 2.0, 3.0), broadband=True,
        typical_features=("subharmonics", "truncated_waveform"),
    ),
    FaultType.BENT_SHAFT: FaultSignature(
        FaultType.BENT_SHAFT, "خمیدگی شفت", (1.0, 2.0), directionality="axial",
        typical_features=("axial_1x_dominant", "phase_180_across"),
    ),
    FaultType.GEAR_MESH_WEAR: FaultSignature(
        FaultType.GEAR_MESH_WEAR, "سایش دنده", (20.0, 40.0), typical_features=("gmf_sidebands",),
    ),
    FaultType.BROKEN_ROTOR_BAR: FaultSignature(
        FaultType.BROKEN_ROTOR_BAR, "شکستگی میله‌ی روتور", (1.0,),
        typical_features=("pole_pass_sidebands_1x", "current_signature"),
    ),
    FaultType.OIL_WHIRL: FaultSignature(
        FaultType.OIL_WHIRL, "چرخش روغن", (0.42, 0.48), typical_features=("subsync_0.4_0.48x",),
    ),
    FaultType.CAVITATION: FaultSignature(
        FaultType.CAVITATION, "کاویتاسیون", (), broadband=True,
        typical_features=("random_broadband_hf", "bpf_modulated"),
    ),
    FaultType.RESONANCE: FaultSignature(
        FaultType.RESONANCE, "تشدید", (1.0,), typical_features=("high_amp_at_natural_freq", "phase_shift_90"),
    ),
    FaultType.BELT_DEFECT: FaultSignature(
        FaultType.BELT_DEFECT, "عیب تسمه", (0.5, 1.0, 2.0), typical_features=("belt_freq_harmonics",),
    ),
    FaultType.ELECTRICAL_STATOR: FaultSignature(
        FaultType.ELECTRICAL_STATOR, "عیب استاتور برقی", (2.0,),
        typical_features=("2x_line_freq_120hz", "vanishes_on_power_off"),
    ),
}

_non_normal = [f for f in SIGNATURES if f is not FaultType.NORMAL]
assert len(_non_normal) == 16, "باید دقیقاً ۱۶ نوع عیب (به‌جز حالت سالم) تعریف شود (FR-09)"

ALL_FAULTS: list[FaultType] = list(SIGNATURES.keys())
