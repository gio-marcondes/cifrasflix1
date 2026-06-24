import time
from pathlib import Path
import numpy as np

from modules.routes_master_state import (
    MASTER_UPLOADS,
    MASTER_PREVIEWS,
    MASTER_ALLOWED_EXT,
    MASTER_EQ_FREQS,
    _master_librosa,
)

def _master_ensure_dirs():
    MASTER_UPLOADS.mkdir(parents=True, exist_ok=True)
    MASTER_PREVIEWS.mkdir(parents=True, exist_ok=True)


def _master_cleanup(max_age_seconds=21600):
    _master_ensure_dirs()
    agora = time.time()
    for pasta in (MASTER_UPLOADS, MASTER_PREVIEWS):
        for f in pasta.glob("*"):
            try:
                if f.is_file() and (agora - f.stat().st_mtime) > max_age_seconds:
                    f.unlink()
            except Exception:
                pass


def _master_is_allowed(filename):
    return Path(filename or "").suffix.lower() in MASTER_ALLOWED_EXT


def _master_normalize_peak(y, peak=0.98):
    pico = float(np.max(np.abs(y))) if y.size else 0.0
    if pico <= 1e-8:
        return y
    return y * (peak / pico)


def _master_saturation(y, drive=1.5):
    return np.tanh(y * drive)


def _master_soft_knee_limiter(y, threshold=0.7, knee=0.1):
    mag = np.abs(y)
    gain = np.ones_like(y, dtype=np.float32)
    mask = mag > (threshold - knee/2)
    if np.any(mask):
        over = mag[mask] - threshold
        gain[mask] = 1.0 / (1.0 + np.maximum(0, over) / (threshold + 1e-8))
    return y * gain


def _master_iir_filter(y, sr, low_hz=None, high_hz=None, type='bandpass'):
    n = len(y)
    if n < 8: return y
    spec = np.fft.rfft(y)
    freqs = np.fft.rfftfreq(n, 1.0 / float(sr))
    if type == 'bandpass':
        mask = (freqs >= float(low_hz)) & (freqs <= float(high_hz))
    elif type == 'lowpass':
        mask = freqs <= float(high_hz)
    elif type == 'highpass':
        mask = freqs >= float(low_hz)
    else:
        return y
    mask = mask.astype(np.float32)
    spec *= mask
    return np.fft.irfft(spec, n=n).astype(np.float32)


def _master_static_compressor(y, threshold=0.58, ratio=3.0):
    mag = np.abs(y)
    gain = np.ones_like(y, dtype=np.float32)
    mask = mag > float(threshold)
    if np.any(mask):
        limited = threshold + (mag[mask] - threshold) / float(ratio)
        gain[mask] = limited / (mag[mask] + 1e-8)
    return y * gain


def _master_delay_reverb_custom(y, sr, mix=0.38, taps=None, feedback_delay_s=0.29, feedback_gain=0.24):
    if y.size < 16:
        return y

    wet = y.astype(np.float32, copy=True)
    taps = taps or (
        (0.034, 0.56),
        (0.061, 0.42),
        (0.093, 0.34),
        (0.127, 0.26),
        (0.181, 0.20),
        (0.247, 0.14),
    )
    for delay_s, gain in taps:
        d = int(float(sr) * delay_s)
        if d > 0 and d < wet.size:
            wet[d:] += gain * y[:-d]

    feedback_delay = int(float(sr) * float(feedback_delay_s))
    if feedback_delay > 0 and feedback_delay < wet.size:
        wet[feedback_delay:] += float(feedback_gain) * wet[:-feedback_delay]

    return (1.0 - mix) * y + mix * wet


def _master_delay_reverb(y, sr, mix=0.38):
    return _master_delay_reverb_custom(y, sr, mix=mix)


def _master_bandpass_fft(y, sr, low_hz, high_hz):
    n = len(y)
    if n < 8:
        return y

    spec = np.fft.rfft(y)
    freqs = np.fft.rfftfreq(n, 1.0 / float(sr))
    mask = (freqs >= float(low_hz)) & (freqs <= float(high_hz))
    spec *= mask.astype(np.float32)
    return np.fft.irfft(spec, n=n).astype(np.float32, copy=False)


def _master_apply_vocal_mode(audio, sr, mode):
    if mode == "vocalverb_extreme":
        low_hz, high_hz, side_mix = 150.0, 7000.0, 0.78
        blend, mix = 1.12, 0.84
        taps = ((0.041, 0.62), (0.078, 0.54), (0.121, 0.46), (0.176, 0.34), (0.251, 0.28), (0.337, 0.20))
        fb_s, fb_g = 0.36, 0.31
    elif mode == "vocalplate":
        low_hz, high_hz, side_mix = 260.0, 5600.0, 0.93
        blend, mix = 0.72, 0.56
        taps = ((0.017, 0.56), (0.026, 0.49), (0.039, 0.38), (0.057, 0.28), (0.082, 0.21), (0.118, 0.15))
        fb_s, fb_g = 0.16, 0.18
    else:
        low_hz, high_hz, side_mix = 180.0, 6200.0, 0.90
        blend, mix = 0.82, 0.66
        taps = None
        fb_s, fb_g = 0.29, 0.24

    if audio.shape[1] >= 2:
        left = audio[:, 0].astype(np.float32, copy=False)
        right = audio[:, 1].astype(np.float32, copy=False)
        mid = 0.5 * (left + right)
        side = 0.5 * (left - right)

        vocal_band = _master_bandpass_fft(mid, sr, low_hz=low_hz, high_hz=high_hz)
        vocal_fx = _master_delay_reverb_custom(vocal_band, sr, mix=mix, taps=taps, feedback_delay_s=fb_s, feedback_gain=fb_g)
        mid_out = mid + (blend * vocal_fx)
        if mode == "vocalverb_extreme":
            mid_out = _master_static_compressor(mid_out, threshold=0.54, ratio=2.6)
        side_out = side_mix * side

        out_l = mid_out + side_out
        out_r = mid_out - side_out
        out = np.stack((out_l, out_r), axis=1)
        return _master_normalize_peak(out, peak=0.98)

    ch = audio[:, 0].astype(np.float32, copy=False)
    ch_vocal = _master_bandpass_fft(ch, sr, low_hz=low_hz, high_hz=high_hz)
    ch_fx = _master_delay_reverb_custom(ch_vocal, sr, mix=mix, taps=taps, feedback_delay_s=fb_s, feedback_gain=fb_g)
    ch_mix = ch + (blend * ch_fx)
    if mode == "vocalverb_extreme":
        ch_mix = _master_static_compressor(ch_mix, threshold=0.54, ratio=2.4)
    ch_mix = _master_normalize_peak(ch_mix, peak=0.98)
    return np.expand_dims(ch_mix, axis=1)


def _master_fft_tone(y, sr, mode):
    n = len(y)
    if n < 8:
        return y

    spec = np.fft.rfft(y)
    freqs = np.fft.rfftfreq(n, 1.0 / float(sr))
    curve = np.ones_like(freqs, dtype=np.float32)

    if mode == "rock":
        curve += 0.28 * np.clip((180.0 - freqs) / 180.0, 0.0, 1.0)
        curve += 0.17 * np.exp(-((freqs - 3400.0) ** 2) / (2.0 * (1700.0 ** 2)))
        curve += 0.15 * np.clip((freqs - 5200.0) / 5200.0, 0.0, 1.0)
    elif mode == "pop":
        curve += 0.10 * np.clip((140.0 - freqs) / 140.0, 0.0, 1.0)
        curve += 0.22 * np.exp(-((freqs - 5200.0) ** 2) / (2.0 * (1900.0 ** 2)))
        curve += 0.08 * np.clip((freqs - 9000.0) / 6000.0, 0.0, 1.0)
    elif mode == "radio":
        curve -= 0.18 * np.clip((220.0 - freqs) / 220.0, 0.0, 1.0)
        curve -= 0.20 * np.clip((freqs - 6500.0) / 6500.0, 0.0, 1.0)
        mid = np.exp(-((freqs - 2200.0) ** 2) / (2.0 * (1100.0 ** 2)))
        curve += 0.28 * mid
    elif mode == "spotify":
        curve += 0.12 * np.exp(-((freqs - 110.0) ** 2) / (2.0 * (85.0 ** 2)))
        curve += 0.10 * np.exp(-((freqs - 4200.0) ** 2) / (2.0 * (2300.0 ** 2)))
        curve += 0.06 * np.clip((freqs - 8500.0) / 8500.0, 0.0, 1.0)
    elif mode == "queen":
        curve += 0.15 * np.exp(-((freqs - 100.0) ** 2) / (2.0 * (50.0 ** 2)))
        curve += 0.25 * np.exp(-((freqs - 3200.0) ** 2) / (2.0 * (1200.0 ** 2)))
        curve += 0.20 * np.clip((freqs - 6000.0) / 6000.0, 0.0, 1.0)
    elif mode == "arctic_monkeys":
        curve += 0.30 * np.clip((200.0 - freqs) / 200.0, 0.0, 1.0)
        curve += 0.18 * np.exp(-((freqs - 1200.0) ** 2) / (2.0 * (600.0 ** 2)))
        curve -= 0.08 * np.clip((freqs - 8000.0) / 8000.0, 0.0, 1.0)
    elif mode == "led_zeppelin":
        curve += 0.25 * np.exp(-((freqs - 80.0) ** 2) / (2.0 * (40.0 ** 2)))
        curve += 0.22 * np.exp(-((freqs - 400.0) ** 2) / (2.0 * (200.0 ** 2)))
        curve -= 0.12 * np.clip((freqs - 7500.0) / 7500.0, 0.0, 1.0)

    spec *= curve
    out = np.fft.irfft(spec, n=n)
    return out.astype(np.float32, copy=False)


def _master_target_dbfs(y, target_db):
    rms = float(np.sqrt(np.mean(np.square(y)))) if y.size else 0.0
    if rms <= 1e-8:
        return y
    current_db = 20.0 * np.log10(rms + 1e-12)
    gain_db = float(target_db) - current_db
    gain = 10.0 ** (gain_db / 20.0)
    return y * gain


def _master_apply_eq_curve(y, sr, eq_gains):
    if not eq_gains:
        return y

    gains = np.array(eq_gains[: len(MASTER_EQ_FREQS)], dtype=np.float32)
    if gains.size < len(MASTER_EQ_FREQS):
        gains = np.pad(gains, (0, len(MASTER_EQ_FREQS) - gains.size), mode="constant")

    if float(np.max(np.abs(gains))) < 1e-4:
        return y

    n = len(y)
    if n < 8:
        return y

    spec = np.fft.rfft(y)
    freqs = np.fft.rfftfreq(n, 1.0 / float(sr))

    work_freqs = np.maximum(freqs, 20.0)
    band_log = np.log10(MASTER_EQ_FREQS)
    work_log = np.log10(work_freqs)
    interp_db = np.interp(work_log, band_log, gains, left=float(gains[0]), right=float(gains[-1]))
    amp = np.power(10.0, interp_db / 20.0).astype(np.float32)

    spec *= amp
    out = np.fft.irfft(spec, n=n)
    return out.astype(np.float32, copy=False)


def _master_apply_no_drums(y, sr):
    """
    Remove a bateria de verdade usando Decomposição Harmônica-Percussiva (HPSS).
    Isola os elementos melódicos/vocais e descarta os transientes de impacto.
    """
    if y.size < 16:
        return y
        
    try:
        librosa = _master_librosa()

        # O librosa quebra o sinal em duas matrizes: 
        # y_harmonic (tudo que é nota, voz, sustentação)
        # y_percussive (tudo que é batida, bumbo, caixa, pratos)
        y_harmonic, y_percussive = librosa.effects.hpss(y, margin=2.0)
        
        # Retornamos apenas a parte harmônica com um leve ganho de compensação
        # para cobrir o buraco deixado pela percussão
        out = y_harmonic * 1.15
        
        return _master_normalize_peak(out, peak=0.98)
        
    except Exception:
        # Caso falhe por falta de memória ou tamanho do buffer, usa o fallback síncrono
        return y

def _master_apply_mix_controls(audio, sr, compression="media", vocal_position="central", no_drums=False):
    out = audio.astype(np.float32, copy=True)

    comp_map = {
        "baixa": (0.72, 1.6),
        "media": (0.60, 2.4),
        "alta": (0.50, 4.6),
    }
    threshold, ratio = comp_map.get(compression, comp_map["media"])
    for ch in range(out.shape[1]):
        out[:, ch] = _master_static_compressor(out[:, ch], threshold=threshold, ratio=ratio)

    if out.shape[1] >= 2:
        left = out[:, 0]
        right = out[:, 1]
        mid = 0.5 * (left + right)
        side = 0.5 * (left - right)
        vocal_band = _master_bandpass_fft(mid, sr, low_hz=180.0, high_hz=5200.0)

        if vocal_position == "frente":
            mid = mid + (0.34 * vocal_band)
            side = 0.90 * side
        elif vocal_position == "tras":
            mid = mid - (0.18 * vocal_band)
            side = 1.08 * side

        out[:, 0] = mid + side
        out[:, 1] = mid - side
    else:
        vocal_band = _master_bandpass_fft(out[:, 0], sr, low_hz=180.0, high_hz=5200.0)
        if vocal_position == "frente":
            out[:, 0] = out[:, 0] + (0.26 * vocal_band)
        elif vocal_position == "tras":
            out[:, 0] = out[:, 0] - (0.14 * vocal_band)

    if no_drums:
        for ch in range(out.shape[1]):
            out[:, ch] = _master_apply_no_drums(out[:, ch], sr)

    return _master_normalize_peak(out, peak=0.98)


def _master_apply_pipeline(audio, sr, mode, compression="media", vocal_position="central", no_drums=False, eq_gains=None, eq_enabled=False):
    if mode in {"vocalverb", "vocalverb_extreme", "vocalplate"}:
        out = _master_apply_vocal_mode(audio, sr, mode)
    elif mode in {"rock", "pop", "radio", "lufs14", "spotify", "queen", "arctic_monkeys", "led_zeppelin"}:
        canais = []
        for ch in range(audio.shape[1]):
            canais.append(_master_apply_mode(audio[:, ch], sr, mode))
        out = np.stack(canais, axis=1)
    else:
        out = audio.astype(np.float32, copy=True)

    out = _master_apply_mix_controls(out, sr, compression=compression, vocal_position=vocal_position, no_drums=no_drums)

    if eq_enabled and eq_gains:
        canais_eq = []
        for ch in range(out.shape[1]):
            canais_eq.append(_master_apply_eq_curve(out[:, ch], sr, eq_gains))
        out = np.stack(canais_eq, axis=1)

    return _master_normalize_peak(out, peak=0.98)


def _master_write_output(output_path, out, sr, export_format="wav"):
    import soundfile as sf

    fmt = (export_format or "wav").strip().lower()
    if fmt == "wav":
        sf.write(str(output_path), out, sr, format="WAV")
        return

    if fmt == "mp3":
        tmp_wav = output_path.with_suffix(".tmp.wav")
        sf.write(str(tmp_wav), out, sr, format="WAV")
        try:
            from pydub import AudioSegment

            segment = AudioSegment.from_wav(str(tmp_wav))
            segment.export(str(output_path), format="mp3", bitrate="320k")
        except Exception as exc:
            raise RuntimeError("Exportar MP3 requer pydub + ffmpeg instalados no sistema.") from exc
        finally:
            try:
                if tmp_wav.exists():
                    tmp_wav.unlink()
            except Exception:
                pass
        return

    raise RuntimeError("Formato de exportacao invalido.")


def _master_apply_mode(y, sr, mode):
    y = y.astype(np.float32, copy=False)
    if mode == "rock":
        out = _master_fft_tone(y, sr, mode="rock")
        out = _master_static_compressor(out, threshold=0.56, ratio=3.2)
        out = np.tanh(1.52 * out)
    elif mode == "queen":
        out = _master_fft_tone(y, sr, mode="queen")
        out = _master_static_compressor(out, threshold=0.58, ratio=2.6)
        out = _master_delay_reverb_custom(out, sr, mix=0.15, feedback_gain=0.10)
        out = np.tanh(1.38 * out)
    elif mode == "arctic_monkeys":
        out = _master_fft_tone(y, sr, mode="arctic_monkeys")
        out = _master_static_compressor(out, threshold=0.50, ratio=3.5)
        out = np.tanh(1.55 * out)
    elif mode == "led_zeppelin":
        out = _master_fft_tone(y, sr, mode="led_zeppelin")
        out = _master_static_compressor(out, threshold=0.54, ratio=2.8)
        out = np.tanh(1.45 * out)
    elif mode == "pop":
        out = _master_fft_tone(y, sr, mode="pop")
        out = _master_static_compressor(out, threshold=0.60, ratio=2.3)
        out = np.tanh(1.34 * out)
    elif mode == "radio":
        out = _master_fft_tone(y, sr, mode="radio")
        out = _master_static_compressor(out, threshold=0.50, ratio=4.6)
        out = np.tanh(1.62 * out)
    elif mode == "lufs14":
        out = _master_static_compressor(y, threshold=0.62, ratio=1.9)
        out = np.tanh(1.24 * out)
        out = _master_target_dbfs(out, target_db=-14.0)
    elif mode == "spotify":
        out = _master_fft_tone(y, sr, mode="spotify")
        out = _master_static_compressor(out, threshold=0.60, ratio=2.2)
        out = np.tanh(1.28 * out)
        out = _master_target_dbfs(out, target_db=-14.0)
    else:
        out = y

    return _master_normalize_peak(out, peak=0.98)


def _master_render_preview(input_path, output_path, mode, compression="media", vocal_position="central", no_drums=False):
    import soundfile as sf

    audio, sr = sf.read(str(input_path), dtype="float32", always_2d=True)
    out = _master_apply_pipeline(
        audio,
        sr,
        mode,
        compression=compression,
        vocal_position=vocal_position,
        no_drums=no_drums,
        eq_gains=None,
        eq_enabled=False,
    )
    sf.write(str(output_path), out, sr)


def _master_render_export(
    input_path,
    output_path,
    mode,
    eq_gains=None,
    eq_enabled=True,
    compression="media",
    vocal_position="central",
    no_drums=False,
    export_format="wav",
):
    import soundfile as sf

    audio, sr = sf.read(str(input_path), dtype="float32", always_2d=True)

    out = _master_apply_pipeline(
        audio,
        sr,
        mode,
        compression=compression,
        vocal_position=vocal_position,
        no_drums=no_drums,
        eq_gains=eq_gains,
        eq_enabled=eq_enabled,
    )
    _master_write_output(output_path, out, sr, export_format=export_format)


def _master_to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "sim", "on"}
    return False


def _master_parse_controls(payload):
    compression = (payload.get("compression") or "media").strip().lower()
    if compression not in {"baixa", "media", "alta"}:
        compression = "media"

    vocal_position = (payload.get("vocal_position") or "central").strip().lower()
    if vocal_position not in {"frente", "central", "tras"}:
        vocal_position = "central"

    no_drums = _master_to_bool(payload.get("no_drums", False))
    return compression, vocal_position, no_drums
