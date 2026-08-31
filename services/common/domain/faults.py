"""امضای فیزیکی ۱۶ عیب تجهیزات دوار (FR-09) — منبع حقیقت مشترک.

از این جدول هم مولّد داده‌ی سنتتیک (`ml/datagen/vibration.py`) و هم استخراج‌کننده‌ی
ویژگی (`ml/features/extract.py`) و هم موتور تشخیص مبتنی بر قاعده استفاده می‌کنند.

مضارب (`*_orders`) بر حسب فرکانس چرخش شفت (1X = rpm/60). فرکانس‌های مطلق بر حسب هرتز.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from services.common.domain.enums import FaultType

# ---- فرکانس‌های مشخصه‌ی یاتاقان (× rpm/60) برای یاتاقان نمونه با ۸ ساچمه ----
BEARING_BPFO = 3.05   # Ball Pass Frequency, Outer race
BEARING_BPFI = 4.95   # Ball Pass Frequency, Inner race
BEARING_BSF = 2.35    # Ball Spin Frequency
BEARING_FTF = 0.38    # Fundamental Train Frequency (cage)

LINE_FREQ_HZ = 50.0   # فرکانس شبکه (ایران)


@dataclass(frozen=True)
class FaultSignature:
    fault: FaultType
    fa_name: str
    # تن‌های گسسته در طیف خام ارتعاش (× 1X)
    spectral_orders: tuple[float, ...] = ()
    # وزن نسبی هر تن (هم‌طول با spectral_orders؛ خالی = یکنواخت)
    spectral_weights: tuple[float, ...] = ()
    # قله‌های طیف پاکت (envelope spectrum) — مشخصه‌ی عیوب ضربه‌ای/یاتاقان (× 1X)
    envelope_orders: tuple[float, ...] = ()
    # فاصله‌ی نوارهای کناری مدولاسیون دامنه (× 1X)؛ None = بدون مدولاسیون
    modulation_order: float | None = None
    modulation_depth: float = 0.0
    # فرکانس رزونانس سازه‌ای که ضربه‌ها آن را تحریک می‌کنند (Hz)
    carrier_hz: float | None = None
    # باند انرژی تصادفی افزوده (lo_hz, hi_hz)
    broadband_hz: tuple[float, float] | None = None
    # تن‌های مستقل از دور (Hz) — عیوب الکتریکی
    fixed_hz: tuple[float, ...] = ()
    # نوار کناری مطلق حول 1X (Hz) — شکستگی میله‌ی روتور (pole-pass)
    sideband_hz: float | None = None
    # شکل موج غالب: sine | impulse | clipped | chaotic | tone
    waveform_shape: str = "sine"
    typical_features: tuple[str, ...] = field(default_factory=tuple)


_S = FaultSignature
SIGNATURES: dict[FaultType, FaultSignature] = {
    FaultType.NORMAL: _S(
        FaultType.NORMAL, "سالم",
        spectral_orders=(1.0, 2.0, 3.0), spectral_weights=(1.0, 0.35, 0.15),
        waveform_shape="sine", typical_features=("rms_low", "crest~1.4"),
    ),
    FaultType.UNBALANCE: _S(
        FaultType.UNBALANCE, "نابالانسی",
        spectral_orders=(1.0, 2.0), spectral_weights=(1.0, 0.08),
        waveform_shape="sine", typical_features=("1x_dominant", "clean_spectrum"),
    ),
    FaultType.MISALIGNMENT: _S(
        FaultType.MISALIGNMENT, "ناهم‌محوری",
        spectral_orders=(1.0, 2.0, 3.0, 4.0), spectral_weights=(0.7, 1.0, 0.6, 0.3),
        waveform_shape="sine", typical_features=("2x>1x", "3x_present"),
    ),
    FaultType.MECHANICAL_LOOSENESS: _S(
        FaultType.MECHANICAL_LOOSENESS, "لقی مکانیکی",
        spectral_orders=(0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0),
        spectral_weights=(0.5, 1.0, 0.6, 0.8, 0.5, 0.6, 0.4, 0.5, 0.3, 0.35),
        broadband_hz=(20.0, 2500.0), waveform_shape="clipped",
        typical_features=("many_harmonics", "half_orders", "raised_floor", "high_crest"),
    ),
    FaultType.BEARING_OUTER_RACE: _S(
        FaultType.BEARING_OUTER_RACE, "عیب رینگ بیرونی یاتاقان",
        envelope_orders=(BEARING_BPFO, 2 * BEARING_BPFO, 3 * BEARING_BPFO),
        modulation_order=None, carrier_hz=3600.0, broadband_hz=(2800.0, 4600.0),
        waveform_shape="impulse", typical_features=("bpfo_env", "no_1x_modulation", "kurtosis_high"),
    ),
    FaultType.BEARING_INNER_RACE: _S(
        FaultType.BEARING_INNER_RACE, "عیب رینگ داخلی یاتاقان",
        envelope_orders=(BEARING_BPFI, 2 * BEARING_BPFI),
        modulation_order=1.0, modulation_depth=0.7, carrier_hz=4200.0,
        broadband_hz=(3400.0, 5200.0), waveform_shape="impulse",
        typical_features=("bpfi_env", "1x_sidebands", "kurtosis_high"),
    ),
    FaultType.BEARING_BALL: _S(
        FaultType.BEARING_BALL, "عیب ساچمه یاتاقان",
        envelope_orders=(2 * BEARING_BSF, 4 * BEARING_BSF, BEARING_BSF),
        modulation_order=BEARING_FTF, modulation_depth=0.6, carrier_hz=4800.0,
        broadband_hz=(3800.0, 6000.0), waveform_shape="impulse",
        typical_features=("2xbsf_env", "ftf_sidebands"),
    ),
    FaultType.BEARING_CAGE: _S(
        FaultType.BEARING_CAGE, "عیب قفسه یاتاقان",
        envelope_orders=(BEARING_FTF, 2 * BEARING_FTF, 3 * BEARING_FTF),
        modulation_order=None, carrier_hz=1400.0, broadband_hz=(900.0, 2200.0),
        waveform_shape="impulse", typical_features=("ftf_env", "subsync_low_carrier"),
    ),
    FaultType.ROTOR_RUB: _S(
        FaultType.ROTOR_RUB, "سایش روتور",
        spectral_orders=(0.333, 0.5, 1.0, 1.5, 2.0, 3.0),
        spectral_weights=(0.5, 0.7, 1.0, 0.5, 0.6, 0.4),
        broadband_hz=(800.0, 9000.0), waveform_shape="clipped",
        typical_features=("integer_fractions", "truncated_waveform", "wide_broadband"),
    ),
    FaultType.BENT_SHAFT: _S(
        FaultType.BENT_SHAFT, "خمیدگی شفت",
        spectral_orders=(1.0, 2.0), spectral_weights=(1.0, 0.55),
        waveform_shape="sine", typical_features=("strong_1x_and_2x", "low_higher_orders"),
    ),
    FaultType.GEAR_MESH_WEAR: _S(
        FaultType.GEAR_MESH_WEAR, "سایش دنده",
        spectral_orders=(1.0, 18.0, 36.0), spectral_weights=(0.4, 1.0, 0.5),
        modulation_order=1.0, modulation_depth=0.5, carrier_hz=None,
        waveform_shape="sine", typical_features=("gmf_18x", "1x_sidebands_on_gmf"),
    ),
    FaultType.BROKEN_ROTOR_BAR: _S(
        FaultType.BROKEN_ROTOR_BAR, "شکستگی میله‌ی روتور",
        spectral_orders=(1.0,), spectral_weights=(1.0,),
        sideband_hz=1.6, waveform_shape="sine",
        typical_features=("pole_pass_sidebands_~1.6hz", "1x_amplitude_modulation_slow"),
    ),
    FaultType.OIL_WHIRL: _S(
        FaultType.OIL_WHIRL, "چرخش روغن",
        spectral_orders=(0.45,), spectral_weights=(1.0,),
        broadband_hz=(0.0, 0.0), waveform_shape="tone",
        typical_features=("single_tone_0.42_0.48x", "no_harmonics"),
    ),
    FaultType.CAVITATION: _S(
        FaultType.CAVITATION, "کاویتاسیون",
        spectral_orders=(1.0,), spectral_weights=(0.25,),
        broadband_hz=(2000.0, 12000.0), waveform_shape="chaotic",
        typical_features=("white_broadband_hf", "no_discrete_peaks", "high_spectral_flatness"),
    ),
    FaultType.RESONANCE: _S(
        FaultType.RESONANCE, "تشدید",
        spectral_orders=(1.0,), spectral_weights=(0.3,),
        carrier_hz=1850.0, waveform_shape="tone",
        typical_features=("high_Q_peak_fixed_freq", "narrowband", "not_rpm_locked"),
    ),
    FaultType.BELT_DEFECT: _S(
        FaultType.BELT_DEFECT, "عیب تسمه",
        spectral_orders=(0.42, 0.84, 1.26, 1.68), spectral_weights=(1.0, 0.7, 0.45, 0.3),
        waveform_shape="sine", typical_features=("belt_freq_0.42x_and_harmonics",),
    ),
    FaultType.ELECTRICAL_STATOR: _S(
        FaultType.ELECTRICAL_STATOR, "عیب استاتور برقی",
        spectral_orders=(2.0,), spectral_weights=(0.2,),
        fixed_hz=(2 * LINE_FREQ_HZ,), waveform_shape="sine",
        typical_features=("2x_line_freq_100hz", "rpm_independent_tone"),
    ),
}

_non_normal = [f for f in SIGNATURES if f is not FaultType.NORMAL]
assert len(_non_normal) == 16, "باید دقیقاً ۱۶ نوع عیب (به‌جز حالت سالم) تعریف شود (FR-09)"
assert set(SIGNATURES) == set(FaultType)

ALL_FAULTS: list[FaultType] = list(SIGNATURES.keys())
