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
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".mkv", ".avi", ".webm", ".flv", ".mpeg", ".mpg", ".wmv", ".3gp"}
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".wma", ".aac"}
ALLOWED_INPUT_EXTENSIONS = ALLOWED_VIDEO_EXTENSIONS | ALLOWED_AUDIO_EXTENSIONS
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


import sys

def _extrair_percentual_linha(linha):
    correspondencias = re.findall(r"(\d{1,3})%", linha or "")
    if not correspondencias:
        return None
    for bruto in reversed(correspondencias):
        try:
            valor = int(bruto)
        except ValueError:
            continue
        if 0 <= valor <= 100:
            return valor
    return None


def _rodar_demucs(input_path, output_dir, final_output_path, job_id, modo):
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    python_exe = sys.executable
    if local_app_data:
        candidato = Path(local_app_data) / "Programs" / "Python" / "Python310" / "python.exe"
        if candidato.exists():
            python_exe = str(candidato)

    cmds = [
        [str(python_exe), "-m", "demucs", "-o", str(output_dir), "--two-stems", "vocals", "--mp3", str(input_path)],
        [str(python_exe), "-m", "demucs", "-o", str(output_dir), "--two-stems=vocals", "--mp3", str(input_path)],
    ]

    processo_env = os.environ.copy()
    processo_env["PYTHONNOUSERSITE"] = "1"

    ultimo_erro = ""
    sucesso = False

    for idx, cmd in enumerate(cmds, 1):
        _atualizar_job(
            job_id,
            status="running",
            progresso=5,
            mensagem=f"Iniciando Demucs (tentativa {idx}/{len(cmds)})..."
        )
        try:
            processo = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
                env=processo_env,
                bufsize=1,
            )
        except Exception as exc:
            ultimo_erro = f"Falha ao iniciar processo: {exc}"
            continue

        ultimo_progresso = 5
        for linha in processo.stdout or []:
            percentual_linha = _extrair_percentual_linha(linha)
            if percentual_linha is not None:
                percent = 5 + int((percentual_linha / 100.0) * 85)
                percent = max(5, min(90, percent))
                if percent - ultimo_progresso >= 1:
                    ultimo_progresso = percent
                    _atualizar_job(
                        job_id,
                        progresso=percent,
                        mensagem=f"Processando com Demucs ({percentual_linha}%)..."
                    )

        retorno = processo.wait()
        if retorno == 0:
            sucesso = True
            break
        else:
            ultimo_erro = f"Demucs terminou com codigo {retorno}."

    if not sucesso:
        _atualizar_job(
            job_id,
            status="failed",
            erro=f"Erro no Demucs: {ultimo_erro}",
            progresso=100,
            mensagem="Falha na extração",
        )
        return False

    audio_exts = {".mp3", ".wav", ".flac", ".m4a"}
    arquivos = [
        f for f in Path(output_dir).rglob("*")
        if f.is_file() and f.suffix.lower() in audio_exts
    ]

    target_name = "vocals.mp3" if modo == "voz" else "no_vocals.mp3"
    alternative_name = "vocals" if modo == "voz" else "no_vocals"

    encontrado = None
    for f in arquivos:
        if f.name.lower() == target_name:
            encontrado = f
            break

    if not encontrado:
        for f in arquivos:
            if alternative_name in f.name.lower():
                encontrado = f
                break

    if not encontrado and arquivos:
        encontrado = arquivos[0]

    if not encontrado or not encontrado.exists():
        _atualizar_job(
            job_id,
            status="failed",
            erro="Arquivo extraido nao encontrado na pasta de saida.",
            progresso=100,
            mensagem="Falha: saida vazia",
        )
        return False

    try:
        shutil.copy2(encontrado, final_output_path)
    except Exception as exc:
        _atualizar_job(
            job_id,
            status="failed",
            erro=f"Falha ao copiar arquivo final: {exc}",
            progresso=100,
            mensagem="Falha ao salvar resultado",
        )
        return False

    _atualizar_job(
        job_id,
        status="completed",
        progresso=100,
        mensagem="Extração concluída com sucesso",
        output_filename=final_output_path.name,
        output_size_bytes=final_output_path.stat().st_size,
        completed_at=time.time(),
    )
    return True


def _processar_job(tipo_conversao, input_path, output_path, job_dir, bitrate, job_id, duracao_total, modo, formato_saida, tempo_inicio=None, tempo_fim=None, input_paths_juntar=None, input_path_audio_novo=None, semitons=None):
    if tipo_conversao == "juntar":
        _rodar_ffmpeg_concat(input_paths_juntar, output_path, bitrate, job_id, formato_saida)
    elif tipo_conversao == "substituir_audio":
        _rodar_ffmpeg_replace_audio(input_path, input_path_audio_novo, output_path, job_id)
    elif tipo_conversao == "tom":
        _rodar_ffmpeg_pitch_shift(input_path, output_path, semitons, bitrate, job_id, formato_saida, duracao_total)
    elif tipo_conversao == "cortar":
        _rodar_ffmpeg(input_path, output_path, bitrate, job_id, duracao_total, formato_saida, tempo_inicio, tempo_fim)
    else: # video_audio or audio_audio
        if modo in {"voz", "instrumental"}:
            demucs_temp = job_dir / "demucs_temp"
            demucs_temp.mkdir(parents=True, exist_ok=True)
            _rodar_demucs(input_path, demucs_temp, output_path, job_id, modo)
        else:
            _rodar_ffmpeg(input_path, output_path, bitrate, job_id, duracao_total, formato_saida)


def _rodar_ffmpeg_pitch_shift(input_path, output_path, semitones, bitrate, job_id, formato_saida, duracao_total):
    ffmpeg = _ffmpeg_binario()
    try:
        n = float(semitones)
    except Exception:
        n = 0.0
        
    f = 2.0 ** (n / 12.0)
    novo_rate = int(44100 * f)
    tempo_scale = 1.0 / f
    
    filter_val = f"asetrate={novo_rate},atempo={tempo_scale},aresample=44100"
    cmd = [
        ffmpeg,
        "-y",
        "-i", str(input_path),
        "-vn",
        "-filter:a", filter_val
    ]
    
    if formato_saida == "wav":
        cmd.extend(["-acodec", "pcm_s16le"])
    elif formato_saida == "ogg":
        cmd.extend(["-acodec", "libvorbis", "-b:a", f"{bitrate}k"])
    else:
        cmd.extend(["-acodec", "libmp3lame", "-b:a", f"{bitrate}k"])
        
    cmd.extend(["-ac", "2", "-ar", "44100", str(output_path)])
    
    _atualizar_job(job_id, status="running", progresso=2, mensagem=f"Alterando tom em {n:+.1f} semitônios...")
    
    try:
        processo = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding="utf-8",
            errors="ignore",
        )
    except Exception as exc:
        _atualizar_job(
            job_id,
            status="failed",
            erro=f"Falha ao iniciar alterador de tom: {exc}",
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
            segundos_ajustados = segundos * f
            percentual = max(2, min(99, (segundos_ajustados / duracao_total) * 100))
            if percentual - ultimo_progresso >= 1:
                ultimo_progresso = percentual
                _atualizar_job(
                    job_id,
                    progresso=percentual,
                    mensagem=f"Alterando tom... {_format_seconds(segundos_ajustados)} / {_format_seconds(duracao_total)}",
                )

    codigo = processo.wait()
    if codigo != 0 or not output_path.exists():
        _atualizar_job(
            job_id,
            status="failed",
            erro=f"ffmpeg terminou com codigo {codigo}.",
            progresso=100,
            mensagem="Falha na alteração de tom",
        )
        return

    _atualizar_job(
        job_id,
        status="completed",
        progresso=100,
        mensagem="Alteração de tom concluída",
        output_filename=output_path.name,
        output_size_bytes=output_path.stat().st_size,
        completed_at=time.time(),
    )


def _rodar_ffmpeg_replace_audio(video_path, audio_path, output_path, job_id):
    ffmpeg = _ffmpeg_binario()
    cmd = [
        ffmpeg,
        "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(output_path)
    ]
    
    _atualizar_job(job_id, status="running", progresso=10, mensagem="Substituindo áudio no vídeo...")
    
    try:
        processo = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding="utf-8",
            errors="ignore",
        )
    except Exception as exc:
        _atualizar_job(
            job_id,
            status="failed",
            erro=f"Falha ao iniciar processo: {exc}",
            progresso=100,
            mensagem="Falha ao iniciar",
        )
        return
        
    for linha in processo.stdout or []:
        pass
        
    codigo = processo.wait()
    if codigo != 0 or not output_path.exists():
        _atualizar_job(
            job_id,
            status="failed",
            erro=f"ffmpeg terminou com codigo {codigo}.",
            progresso=100,
            mensagem="Falha na substituição",
        )
        return

    _atualizar_job(
        job_id,
        status="completed",
        progresso=100,
        mensagem="Substituição concluída",
        output_filename=output_path.name,
        output_size_bytes=output_path.stat().st_size,
        completed_at=time.time(),
    )


def _rodar_ffmpeg_concat(input_paths, output_path, bitrate, job_id, formato_saida):
    ffmpeg = _ffmpeg_binario()
    cmd = [ffmpeg, "-y"]
    for path in input_paths:
        cmd.extend(["-i", str(path)])
        
    n = len(input_paths)
    filter_val = "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1[outa]"
    cmd.extend(["-filter_complex", filter_val, "-map", "[outa]"])
    
    if formato_saida == "wav":
        cmd.extend(["-acodec", "pcm_s16le"])
    elif formato_saida == "ogg":
        cmd.extend(["-acodec", "libvorbis", "-b:a", f"{bitrate}k"])
    else:
        cmd.extend(["-acodec", "libmp3lame", "-b:a", f"{bitrate}k"])
        
    cmd.extend(["-ac", "2", "-ar", "44100", str(output_path)])
    
    _atualizar_job(job_id, status="running", progresso=2, mensagem="Concatenando áudios...")
    
    try:
        processo = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding="utf-8",
            errors="ignore",
        )
    except Exception as exc:
        _atualizar_job(
            job_id,
            status="failed",
            erro=f"Falha ao iniciar concatenação: {exc}",
            progresso=100,
            mensagem="Falha ao iniciar",
        )
        return

    for linha in processo.stdout or []:
        pass
        
    codigo = processo.wait()
    if codigo != 0 or not output_path.exists():
        _atualizar_job(
            job_id,
            status="failed",
            erro=f"ffmpeg terminou com codigo {codigo}.",
            progresso=100,
            mensagem="Falha na mesclagem",
        )
        return

    _atualizar_job(
        job_id,
        status="completed",
        progresso=100,
        mensagem="Mesclagem concluída",
        output_filename=output_path.name,
        output_size_bytes=output_path.stat().st_size,
        completed_at=time.time(),
    )


def _rodar_ffmpeg(input_path, output_path, bitrate, job_id, duracao_total, formato_saida="mp3", tempo_inicio=None, tempo_fim=None):
    ffmpeg = _ffmpeg_binario()
    cmd = [ffmpeg, "-y"]
    
    if tempo_inicio:
        cmd.extend(["-ss", str(tempo_inicio)])
    if tempo_fim:
        cmd.extend(["-to", str(tempo_fim)])
        
    cmd.extend(["-i", str(input_path), "-vn"])
    
    if formato_saida == "wav":
        cmd.extend(["-acodec", "pcm_s16le"])
    elif formato_saida == "ogg":
        cmd.extend(["-acodec", "libvorbis", "-b:a", f"{bitrate}k"])
    else:
        cmd.extend(["-acodec", "libmp3lame", "-b:a", f"{bitrate}k"])
        
    cmd.extend(["-ac", "2", "-ar", "44100", str(output_path)])

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
        tipo_conversao = request.form.get("tipo_conversao", "video_audio")
        bitrate = (request.form.get("bitrate") or "192").strip()
        contexto["bitrate"] = bitrate if bitrate in ALLOWED_AUDIO_BITRATES else "192"
        bitrate_final = contexto["bitrate"]

        formato_saida = request.form.get("formato_saida", "mp3").strip().lower()
        if formato_saida not in {"mp3", "wav", "ogg"}:
            formato_saida = "mp3"

        job_id_orig = request.form.get("job_id_orig", "").strip()
        if job_id_orig and (OUTPUT_ROOT / job_id_orig).exists():
            job_id = job_id_orig
            job_dir = OUTPUT_ROOT / job_id
            input_dir = job_dir / "input"
            output_dir = job_dir / "output"
        else:
            job_id = uuid.uuid4().hex
            job_dir = OUTPUT_ROOT / job_id
            input_dir = job_dir / "input"
            output_dir = job_dir / "output"
            input_dir.mkdir(parents=True, exist_ok=True)
            output_dir.mkdir(parents=True, exist_ok=True)

        modo = "completo"
        input_path = None
        input_paths_juntar = []
        input_path_audio_novo = None
        original_name = ""
        tamanho_original = ""
        duracao = None

        if tipo_conversao == "juntar":
            arquivos = request.files.getlist("arquivos_juntar")
            arquivos = [f for f in arquivos if f and f.filename]
            if len(arquivos) < 2:
                contexto["erro"] = "Selecione pelo menos 2 arquivos de áudio para juntar."
                return render_template("conversor.html", **contexto)
            
            for idx, arquivo in enumerate(arquivos):
                if not _extensao_valida(arquivo.filename):
                    contexto["erro"] = f"Arquivo '{arquivo.filename}' tem extensão inválida."
                    return render_template("conversor.html", **contexto)
                nome_seguro = f"concat_{idx}_{secure_filename(arquivo.filename)}"
                path = input_dir / nome_seguro
                arquivo.save(path)
                input_paths_juntar.append(path)
            
            original_name = " + ".join([Path(f.filename).name for f in arquivos])
            tamanho_original = f"{len(input_paths_juntar)} arquivos"
            duracao = 0.0
            for p in input_paths_juntar:
                d = _detectar_duracao(p)
                if d:
                    duracao += d
            output_filename = f"mesclado_{job_id[:8]}.{formato_saida}"
            output_path = output_dir / output_filename

        elif tipo_conversao == "substituir_audio":
            arq_video = request.files.get("arquivo_video")
            arq_audio = request.files.get("arquivo_audio_novo")
            if not arq_video or not arq_video.filename or not arq_audio or not arq_audio.filename:
                contexto["erro"] = "Selecione o vídeo e o novo arquivo de áudio."
                return render_template("conversor.html", **contexto)
            
            if not _extensao_valida(arq_video.filename) or not _extensao_valida(arq_audio.filename):
                contexto["erro"] = "Um dos arquivos possui extensão inválida."
                return render_template("conversor.html", **contexto)
                
            video_seguro = f"video_{secure_filename(arq_video.filename)}"
            audio_seguro = f"audio_{secure_filename(arq_audio.filename)}"
            
            input_path = input_dir / video_seguro
            input_path_audio_novo = input_dir / audio_seguro
            
            arq_video.save(input_path)
            arq_audio.save(input_path_audio_novo)
            
            original_name = arq_video.filename
            tamanho_original = _tamanho_legivel(input_path)
            duracao = _detectar_duracao(input_path)
            
            base = Path(video_seguro).stem
            ext = Path(video_seguro).suffix
            if not ext:
                ext = ".mp4"
            output_filename = f"{base}_mux{ext}"
            output_path = output_dir / output_filename
            formato_saida = ext[1:].lower()

        else:
            input_files = list(input_dir.glob("*"))
            if job_id_orig and input_files:
                input_path = input_files[0]
                nome_seguro = input_path.name
                original_name = nome_seguro
                tamanho_original = _tamanho_legivel(input_path)
                duracao = _detectar_duracao(input_path)
            else:
                file_key = "arquivo_video"
                if tipo_conversao == "audio_audio":
                    file_key = "arquivo_audio"
                elif tipo_conversao == "cortar":
                    file_key = "arquivo_cortar"
                elif tipo_conversao == "tom":
                    file_key = "arquivo_tom"

                arquivo = request.files.get(file_key)
                if not arquivo or not arquivo.filename:
                    contexto["erro"] = "Selecione um arquivo para converter."
                    return render_template("conversor.html", **contexto)

                if not _extensao_valida(arquivo.filename):
                    contexto["erro"] = "Arquivo inválido ou extensão não suportada."
                    return render_template("conversor.html", **contexto)

                nome_seguro = secure_filename(arquivo.filename) or f"input_{job_id}"
                input_path = input_dir / nome_seguro
                arquivo.save(input_path)

                original_name = arquivo.filename
                tamanho_original = _tamanho_legivel(input_path)
                duracao = _detectar_duracao(input_path)

            base = Path(nome_seguro).stem
            if tipo_conversao == "video_audio":
                modo = (request.form.get("modo") or "completo").strip()
                if modo not in {"voz", "instrumental", "completo"}:
                    modo = "completo"
                
                if modo == "voz":
                    output_filename = f"{base}_vocals.{formato_saida}"
                elif modo == "instrumental":
                    output_filename = f"{base}_instrumental.{formato_saida}"
                else:
                    output_filename = f"{base}.{formato_saida}"
            elif tipo_conversao == "cortar":
                output_filename = f"{base}_corte.{formato_saida}"
            elif tipo_conversao == "tom":
                output_filename = f"{base}_tom.{formato_saida}"
            else:
                output_filename = f"{base}.{formato_saida}"

            output_path = output_dir / output_filename

        tempo_inicio = None
        tempo_fim = None
        semitons = None
        if tipo_conversao == "cortar":
            tempo_inicio = request.form.get("tempo_inicio", "").strip()
            tempo_fim = request.form.get("tempo_fim", "").strip()
            if not tempo_inicio:
                tempo_inicio = None
            if not tempo_fim:
                tempo_fim = None
        elif tipo_conversao == "tom":
            semitons = request.form.get("semitons", "0").strip()

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
                "original_name": original_name,
                "original_size": tamanho_original,
                "original_duration": duracao,
                "created_at": time.time(),
                "updated_at": time.time(),
                "modo": modo,
                "tipo_conversao": tipo_conversao,
                "formato_saida": formato_saida,
                "semitons": semitons,
            }

        thread = threading.Thread(
            target=_processar_job,
            args=(tipo_conversao, input_path, output_path, job_dir, bitrate_final, job_id, duracao, modo, formato_saida, tempo_inicio, tempo_fim, input_paths_juntar, input_path_audio_novo, semitons),
            daemon=True,
        )
        thread.start()

        contexto["job_id"] = job_id
        contexto["processando"] = True
        contexto["arquivo_nome"] = original_name
        contexto["tamanho_original"] = tamanho_original or ""
        contexto["duracao_original"] = _format_seconds(duracao) if duracao else "--:--"
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


@conversor_bp.route("/conversor/upload_temp", methods=["POST"])
def conversor_upload_temp():
    _ensure_dirs()
    arquivo = request.files.get("arquivo")
    if not arquivo or not arquivo.filename:
        return jsonify({"ok": False, "erro": "Nenhum arquivo enviado."}), 400
        
    if not _extensao_valida(arquivo.filename):
        return jsonify({"ok": False, "erro": "Extensão inválida."}), 400
        
    job_id = uuid.uuid4().hex
    job_dir = OUTPUT_ROOT / job_id
    input_dir = job_dir / "input"
    output_dir = job_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    nome_seguro = secure_filename(arquivo.filename)
    input_path = input_dir / nome_seguro
    arquivo.save(input_path)
    
    duracao = _detectar_duracao(input_path)
    tamanho = _tamanho_legivel(input_path)
    
    return jsonify({
        "ok": True,
        "job_id": job_id,
        "filename": arquivo.filename,
        "duration": duracao,
        "size": tamanho
    })


@conversor_bp.route("/conversor/preview", methods=["POST"])
def conversor_preview():
    job_id = request.form.get("job_id")
    semitons = request.form.get("semitons", "0").strip()
    
    if not job_id:
        return jsonify({"ok": False, "erro": "job_id ausente."}), 400
        
    job_dir = OUTPUT_ROOT / job_id
    input_files = list((job_dir / "input").glob("*"))
    if not input_files:
        return jsonify({"ok": False, "erro": "Arquivo original não encontrado."}), 404
        
    input_path = input_files[0]
    preview_output = job_dir / "output" / "preview.mp3"
    
    ffmpeg = _ffmpeg_binario()
    try:
        n = float(semitons)
    except Exception:
        n = 0.0
        
    f = 2.0 ** (n / 12.0)
    novo_rate = int(44100 * f)
    tempo_scale = 1.0 / f
    
    filter_val = f"asetrate={novo_rate},atempo={tempo_scale},aresample=44100"
    
    cmd = [
        ffmpeg,
        "-y",
        "-ss", "00:00:15",
        "-i", str(input_path),
        "-t", "20",
        "-vn",
        "-filter:a", filter_val,
        "-acodec", "libmp3lame",
        "-b:a", "128k",
        "-ac", "2",
        "-ar", "44100",
        str(preview_output)
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
    except Exception as exc:
        cmd_fallback = [
            ffmpeg,
            "-y",
            "-i", str(input_path),
            "-t", "20",
            "-vn",
            "-filter:a", filter_val,
            "-acodec", "libmp3lame",
            "-b:a", "128k",
            "-ac", "2",
            "-ar", "44100",
            str(preview_output)
        ]
        try:
            subprocess.run(cmd_fallback, capture_output=True, check=True)
        except Exception as exc2:
            return jsonify({"ok": False, "erro": f"Falha ao gerar preview: {exc2}"}), 500
        
    download_url = url_for(
        "conversor.conversor_download",
        job_id=job_id,
        filename="preview.mp3"
    )
    
    return jsonify({"ok": True, "preview_url": download_url})
