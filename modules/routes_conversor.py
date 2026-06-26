import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request, send_from_directory, url_for, abort
from werkzeug.utils import secure_filename

conversor_bp = Blueprint('conversor', __name__)

CONVERSOR_ROOT = Path("static") / "conversor"
UPLOAD_ROOT = CONVERSOR_ROOT / "uploads"
OUTPUT_ROOT = CONVERSOR_ROOT / "jobs"
ALLOWED_INPUT_EXTENSIONS = {".mp4", ".m4v", ".mov", ".mkv", ".avi", ".webm", ".flv", ".mpeg", ".mpg", ".wmv", ".3gp"}
ALLOWED_AUDIO_BITRATES = {"128", "192", "256", "320"}

JOBS = {}
JOBS_LOCK = threading.Lock()


def _ensure_dirs():
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def _extensao_valida(nome):
    return Path(nome).suffix.lower() in ALLOWED_INPUT_EXTENSIONS


def _ffmpeg_binario():
    caminho = shutil.which("ffmpeg")
    if caminho:
        return caminho

    candidatos = [
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/ProgramData/chocolatey/bin/ffmpeg.exe"),
    ]
    for item in candidatos:
        if item.exists():
            return str(item)

    return "ffmpeg"


def _ffprobe_binario():
    caminho = shutil.which("ffprobe")
    if caminho:
        return caminho

    candidatos = [
        Path("C:/ffmpeg/bin/ffprobe.exe"),
        Path("C:/Program Files/ffmpeg/bin/ffprobe.exe"),
        Path("C:/ProgramData/chocolatey/bin/ffprobe.exe"),
    ]
    for item in candidatos:
        if item.exists():
            return str(item)

    return "ffprobe"


def _format_seconds(valor):
    if valor is None:
        return "--:--"
    total = int(round(float(valor)))
    h, resto = divmod(total, 3600)
    m, s = divmod(resto, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _tamanho_legivel(caminho):
    try:
        bytes_ = Path(caminho).stat().st_size
    except Exception:
        return None
    unidades = ["B", "KB", "MB", "GB"]
    valor = float(bytes_)
    for unidade in unidades:
        if valor < 1024 or unidade == unidades[-1]:
            return f"{valor:.1f} {unidade}" if unidade != "B" else f"{int(valor)} {unidade}"
        valor /= 1024
    return f"{valor:.1f} GB"


def _obter_job(job_id):
    with JOBS_LOCK:
        info = JOBS.get(job_id)
        if not info:
            return None
        return dict(info)


def _atualizar_job(job_id, **kwargs):
    with JOBS_LOCK:
        info = JOBS.get(job_id)
        if not info:
            return
        info.update(kwargs)
        info["updated_at"] = time.time()


def _rodar_ffmpeg(input_path, output_path, bitrate, job_id, duracao_total):
    ffmpeg = _ffmpeg_binario()
    cmd = [
        ffmpeg,
        "-y",
        "-i", str(input_path),
        "-vn",
        "-acodec", "libmp3lame",
        "-b:a", f"{bitrate}k",
        "-ac", "2",
        "-ar", "44100",
        str(output_path),
    ]

    _atualizar_job(job_id, status="running", progresso=2, mensagem="Iniciando ffmpeg...")

    try:
        processo = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding="utf-8",
            errors="ignore",
        )
    except FileNotFoundError:
        _atualizar_job(
            job_id,
            status="failed",
            erro="ffmpeg nao encontrado. Instale o ffmpeg ou adicione-o ao PATH.",
            progresso=100,
            mensagem="Falha: ffmpeg indisponivel",
        )
        return
    except Exception as exc:
        _atualizar_job(
            job_id,
            status="failed",
            erro=f"Falha ao iniciar ffmpeg: {exc}",
            progresso=100,
            mensagem="Falha ao iniciar",
        )
        return

    regex_tempo = re.compile(r"time=(\d+):(\d{1,2}):(\d{1,2})(?:\.(\d+))?")
    ultimo_progresso = 2

    for linha in processo.stdout or []:
        match = regex_tempo.search(linha)
        if match and duracao_total:
            h, m, s, frac = match.groups()
            segundos = int(h) * 3600 + int(m) * 60 + int(s)
            if frac:
                segundos += float(f"0.{frac}")
            percentual = max(2, min(99, (segundos / duracao_total) * 100))
            if percentual - ultimo_progresso >= 1:
                ultimo_progresso = percentual
                _atualizar_job(
                    job_id,
                    progresso=percentual,
                    mensagem=f"Convertendo... {_format_seconds(segundos)} / {_format_seconds(duracao_total)}",
                )

    codigo = processo.wait()

    if codigo != 0 or not output_path.exists():
        _atualizar_job(
            job_id,
            status="failed",
            erro=f"ffmpeg terminou com codigo {codigo}.",
            progresso=100,
            mensagem="Falha na conversao",
        )
        return

    _atualizar_job(
        job_id,
        status="completed",
        progresso=100,
        mensagem="Conversao concluida",
        output_filename=output_path.name,
        output_size_bytes=output_path.stat().st_size,
        completed_at=time.time(),
    )


def _detectar_duracao(input_path):
    ffprobe = _ffprobe_binario()
    try:
        resultado = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(input_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception:
        return None

    saida = (resultado.stdout or "").strip()
    if not saida:
        return None
    try:
        return float(saida)
    except ValueError:
        return None


@conversor_bp.route("/conversor", methods=["GET", "POST"])
def conversor_route():
    _ensure_dirs()

    contexto = {
        "erro": "",
        "resultado": None,
        "processando": False,
        "job_id": "",
        "progresso": 0,
        "mensagem_status": "Aguardando arquivo",
        "bitrate": "192",
        "arquivo_nome": "",
        "tamanho_original": "",
        "duracao_original": "--:--",
    }

    if request.method == "POST":
        arquivo = request.files.get("arquivo_video")
        bitrate = (request.form.get("bitrate") or "192").strip()

        contexto["bitrate"] = bitrate if bitrate in ALLOWED_AUDIO_BITRATES else "192"

        if not arquivo or not arquivo.filename:
            contexto["erro"] = "Selecione um arquivo de video para converter."
            return render_template("conversor.html", **contexto)

        if not _extensao_valida(arquivo.filename):
            contexto["erro"] = "Use um arquivo MP4, MOV, MKV, AVI, WEBM ou outro formato de video."
            return render_template("conversor.html", **contexto)

        bitrate_final = contexto["bitrate"]
        job_id = uuid.uuid4().hex
        job_dir = OUTPUT_ROOT / job_id
        input_dir = job_dir / "input"
        output_dir = job_dir / "output"
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        nome_seguro = secure_filename(arquivo.filename) or f"video_{job_id}.mp4"
        if not _extensao_valida(nome_seguro):
            nome_seguro = f"video_{job_id}.mp4"

        input_path = input_dir / nome_seguro
        arquivo.save(input_path)

        base = Path(nome_seguro).stem
        output_filename = f"{base}.mp3"
        output_path = output_dir / output_filename

        tamanho_original = _tamanho_legivel(input_path)
        duracao = _detectar_duracao(input_path)

        with JOBS_LOCK:
            JOBS[job_id] = {
                "status": "queued",
                "progresso": 0,
                "mensagem": "Job criado. Aguardando processamento...",
                "erro": "",
                "output_filename": "",
                "output_size_bytes": 0,
                "download_url": "",
                "bitrate": bitrate_final,
                "original_name": arquivo.filename,
                "original_size": tamanho_original,
                "original_duration": duracao,
                "created_at": time.time(),
                "updated_at": time.time(),
            }

        thread = threading.Thread(
            target=_rodar_ffmpeg,
            args=(input_path, output_path, bitrate_final, job_id, duracao),
            daemon=True,
        )
        thread.start()

        contexto["job_id"] = job_id
        contexto["processando"] = True
        contexto["arquivo_nome"] = arquivo.filename
        contexto["tamanho_original"] = tamanho_original or ""
        contexto["duracao_original"] = _format_seconds(duracao)
        contexto["progresso"] = 0
        contexto["mensagem_status"] = "Processamento iniciado..."

    return render_template("conversor.html", **contexto)


@conversor_bp.route("/conversor/status/<job_id>", methods=["GET"])
def conversor_status(job_id):
    job = _obter_job(job_id)
    if not job:
        return jsonify({"ok": False, "erro": "Job nao encontrado."}), 404

    output_filename = job.get("output_filename", "")
    download_url = ""
    if job.get("status") == "completed" and output_filename:
        download_url = url_for(
            "conversor.conversor_download",
            job_id=job_id,
            filename=output_filename,
        )

    return jsonify({
        "ok": True,
        "job_id": job_id,
        "status": job.get("status"),
        "progresso": job.get("progresso", 0),
        "mensagem": job.get("mensagem", ""),
        "erro": job.get("erro", ""),
        "download_url": download_url,
        "output_filename": output_filename,
        "original_name": job.get("original_name", ""),
        "original_size": job.get("original_size", ""),
        "original_duration": job.get("original_duration"),
        "bitrate": job.get("bitrate", "192"),
        "completed": job.get("status") == "completed",
        "failed": job.get("status") == "failed",
    })


@conversor_bp.route("/conversor/download/<job_id>/<path:filename>", methods=["GET"])
def conversor_download(job_id, filename):
    pasta = OUTPUT_ROOT / job_id / "output"
    if not pasta.exists():
        abort(404)

    return send_from_directory(
        str(pasta),
        filename,
        as_attachment=True,
        download_name=filename,
    )


@conversor_bp.route("/conversor/api/limpar/<job_id>", methods=["POST", "DELETE"])
def conversor_limpar(job_id):
    pasta = OUTPUT_ROOT / job_id
    if pasta.exists():
        try:
            shutil.rmtree(pasta)
        except Exception:
            pass
    with JOBS_LOCK:
        JOBS.pop(job_id, None)
    return jsonify({"ok": True})
