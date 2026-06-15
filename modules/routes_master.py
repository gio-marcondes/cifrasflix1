@app.route("/masterizacao")
def masterizacao_home():
    return render_template("masterizacao.html", header_html=header("Masterizacao"))


@app.route("/masterizacao/upload", methods=["POST"])
def masterizacao_upload():
    arquivo = request.files.get("audio_file")
    if not arquivo or not (arquivo.filename or "").strip():
        return jsonify({"error": "Selecione um arquivo de audio."}), 400

    if not _master_is_allowed(arquivo.filename):
        return jsonify({"error": "Formato nao suportado. Use mp3, wav, flac, m4a, ogg ou aac."}), 400

    _master_cleanup()
    _master_ensure_dirs()

    job_id = uuid.uuid4().hex
    nome_seguro = secure_filename(arquivo.filename or "audio")
    ext = Path(nome_seguro).suffix.lower() or ".wav"
    input_name = f"{job_id}_orig{ext}"
    input_path = MASTER_UPLOADS / input_name
    arquivo.save(str(input_path))

    with MASTER_LOCK:
        MASTER_JOBS[job_id] = {
            "created_at": int(time.time()),
            "input_path": str(input_path),
        }

    return jsonify(
        {
            "job_id": job_id,
            "original_url": f"/masterizacao/audio/{input_name}",
        }
    )


@app.route("/masterizacao/preview", methods=["POST"])
def masterizacao_preview():
    payload = request.get_json(silent=True) or {}
    job_id = (payload.get("job_id") or "").strip()
    mode = (payload.get("mode") or "rock").strip().lower()
    compression, vocal_position, no_drums = _master_parse_controls(payload)

    mode_map = {
        "original": "Original",
        "rock": "Rock",
        "pop": "Pop",
        "radio": "Radio",
        "lufs14": "14 LUFS",
        "spotify": "Spotify",
        "vocalverb": "Voz Reverb",
        "vocalverb_extreme": "Voz Reverb Extreme",
        "vocalplate": "Voz Plate",
        "queen": "Vibe Queen",
        "arctic_monkeys": "Vibe Arctic Monkeys",
        "led_zeppelin": "Vibe Led Zeppelin"
    }

    if mode not in mode_map:
        return jsonify({"error": "Modo invalido."}), 400

    with MASTER_LOCK:
        job = MASTER_JOBS.get(job_id)

    if not job:
        return jsonify({"error": "Sessao nao encontrada. Envie o arquivo novamente."}), 404

    input_path = Path(job.get("input_path") or "")
    if not input_path.exists() or not input_path.is_file():
        return jsonify({"error": "Arquivo original nao encontrado."}), 404

    try:
        control_key = f"{compression}_{vocal_position}_{'nodrums' if no_drums else 'drums'}"
        output_name = f"{job_id}_{mode}_{control_key}.wav"
        output_path = MASTER_PREVIEWS / output_name
        _master_render_preview(
            input_path,
            output_path,
            mode,
            compression=compression,
            vocal_position=vocal_position,
            no_drums=no_drums,
        )
        return jsonify(
            {
                "preview_url": f"/masterizacao/audio/{output_name}",
                "mode": mode,
                "mode_label": mode_map[mode],
            }
        )
    except ImportError:
        return jsonify({"error": "Dependencia ausente: instale soundfile para gerar previews."}), 500
    except Exception:
        return jsonify({"error": "Falha ao processar o audio."}), 500


@app.route("/masterizacao/audio/<path:filename>")
def masterizacao_audio(filename):
    _master_ensure_dirs()
    nome = Path(filename).name

    for pasta in (MASTER_UPLOADS, MASTER_PREVIEWS):
        caminho = pasta / nome
        if caminho.exists() and caminho.is_file():
            return send_file(str(caminho), as_attachment=False, conditional=True)

    return jsonify({"error": "Arquivo nao encontrado."}), 404


@app.route('/masterizacao/detectar_tom/<job_id>')
def detectar_tom_e_pitch(job_id):
    with MASTER_LOCK:
        job = MASTER_JOBS.get(job_id)
    
    if not job:
        return jsonify({"error": "Job não encontrado"}), 404

    input_path = job["input_path"]
    
    try:
        librosa = _master_librosa()

        # Carrega os primeiros 30 segundos para precisão na detecção de tempo e tom
        y, sr = librosa.load(input_path, duration=30)
        
        if len(y) == 0:
            return jsonify({"error": "Arquivo de áudio vazio ou inválido."}), 400

        # 1. DETECÇÃO DE BPM (Batidas por Minuto)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm_final = float(tempo[0]) if isinstance(tempo, (np.ndarray, list)) else float(tempo)
        
        # Correção para evitar leituras de meio-tempo ou double-time bizarros
        if bpm_final < 65: bpm_final *= 2
        if bpm_final > 180: bpm_final /= 2

        # 2. DETECÇÃO DE TOM MUSICAL AVANÇADA (Chroma CQT)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        mean_chroma = np.mean(chroma, axis=1)
        
        # Escala em Bemóis (Bb), padrão universal de DJs e produção comercial
        notas = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
        
        key_idx = int(np.argmax(mean_chroma))
        nota_tonica = notas[key_idx]

        # Desempate harmônico para Escala Maior vs Menor
        terca_menor_idx = (key_idx + 3) % 12
        terca_maior_idx = (key_idx + 4) % 12
        
        if mean_chroma[terca_maior_idx] >= mean_chroma[terca_menor_idx]:
            escala = "Major"
        else:
            escala = "Minor"

        tom_americano = f"{nota_tonica} {escala}"

        # Preferência para a perspectiva menor em caso de Bb Major / G Minor (Alinhamento de Mercado)
        if tom_americano == "Bb Major":
            tom_americano = "G Minor"

        camelot_map = {
            "C Major": "8B",  "C Minor": "5A",   "Db Major": "3B", "Db Minor": "12A",
            "D Major": "10B", "D Minor": "7A",   "Eb Major": "5B", "Eb Minor": "2A",
            "E Major": "12B", "E Minor": "9A",   "F Major": "7B",  "F Minor": "4A",
            "F# Major": "2B", "F# Minor": "11A", "G Major": "9B",  "G Minor": "6A",
            "Ab Major": "4B", "Ab Minor": "1A",  "A Major": "11B", "A Minor": "8A",
            "Bb Major": "6B", "Bb Minor": "3A",  "B Major": "1B",  "B Minor": "10A"
        }
        codigo_camelot = camelot_map.get(tom_americano, "6A")

        # --- GERADOR DE TONS SEMELHANTES (REGRAS DA RODA DE CAMELOT) ---
        num = int(codigo_camelot[:-1])
        letra = codigo_camelot[-1]
        outra_letra = "B" if letra == "A" else "A"
        
        num_menos = 12 if num == 1 else num - 1
        num_mais = 1 if num == 12 else num + 1

        inv_camelot = {v: k for k, v in camelot_map.items()}
        
        tons_semelhantes = [
            f"• Relativo Direto ({num}{outra_letra}): {inv_camelot.get(f'{num}{outra_letra}', 'N/A')}",
            f"• Subdominante ({num_menos}{letra}): {inv_camelot.get(f'{num_menos}{letra}', 'N/A')}",
            f"• Dominante ({num_mais}{letra}): {inv_camelot.get(f'{num_mais}{letra}', 'N/A')}"
        ]

        # --- GERADOR DE ACORDES POSSÍVEIS (CAMPO HARMÔNICO) ---
        if escala == "Major":
            acordes = [
                f"{notas[key_idx]}", f"{notas[(key_idx+2)%12]}m", f"{notas[(key_idx+4)%12]}m",
                f"{notas[(key_idx+5)%12]}", f"{notas[(key_idx+7)%12]}", f"{notas[(key_idx+9)%12]}m"
            ]
        else:
            acordes = [
                f"{notas[key_idx]}m", f"{notas[(key_idx+3)%12]}", f"{notas[(key_idx+5)%12]}m",
                f"{notas[(key_idx+7)%12]}m", f"{notas[(key_idx+8)%12]}", f"{notas[(key_idx+10)%12]}"
            ]

        # Retorno completo exigido pelo teu JavaScript
        return jsonify({
            "bpm": round(bpm_final, 1),
            "tom": tom_americano,
            "camelot": codigo_camelot,
            "tons_semelhantes": tons_semelhantes,
            "acordes": acordes
        })
        
    except Exception as e:
        return jsonify({"error": f"Falha na análise harmônica: {str(e)}"}), 500

@app.route("/masterizacao/export", methods=["POST"])
def masterizacao_export():
    payload = request.get_json(silent=True) or {}
    job_id = (payload.get("job_id") or "").strip()
    mode = (payload.get("mode") or "original").strip().lower()
    eq_enabled = _master_to_bool(payload.get("eq_enabled", True))
    eq_gains_raw = payload.get("eq_gains") or []
    compression, vocal_position, no_drums = _master_parse_controls(payload)
    export_format = (payload.get("export_format") or "wav").strip().lower()

    mode_map = {
        "original": "Original",
        "rock": "Rock",
        "pop": "Pop",
        "radio": "Radio",
        "lufs14": "14 LUFS",
        "spotify": "Spotify",
        "vocalverb": "Voz Reverb",
        "vocalverb_extreme": "Voz Reverb Extreme",
        "vocalplate": "Voz Plate",
        "queen": "Vibe Queen",
        "arctic_monkeys": "Vibe Arctic Monkeys",
        "led_zeppelin": "Vibe Led Zeppelin"
    }

    if mode not in mode_map:
        return jsonify({"error": "Modo invalido para exportacao."}), 400

    if export_format not in {"wav", "mp3"}:
        return jsonify({"error": "Formato invalido. Use wav ou mp3."}), 400

    eq_gains = []
    if isinstance(eq_gains_raw, list):
        for v in eq_gains_raw[: len(MASTER_EQ_FREQS)]:
            try:
                eq_gains.append(float(v))
            except (TypeError, ValueError):
                eq_gains.append(0.0)

    with MASTER_LOCK:
        job = MASTER_JOBS.get(job_id)

    if not job:
        return jsonify({"error": "Sessao nao encontrada. Envie o arquivo novamente."}), 404

    input_path = Path(job.get("input_path") or "")
    if not input_path.exists() or not input_path.is_file():
        return jsonify({"error": "Arquivo original nao encontrado."}), 404

    try:
        suffix = mode if mode != "original" else "orig"
        output_name = f"{job_id}_{suffix}_export.{export_format}"
        output_path = MASTER_PREVIEWS / output_name
        _master_render_export(
            input_path,
            output_path,
            mode,
            eq_gains=eq_gains,
            eq_enabled=eq_enabled,
            compression=compression,
            vocal_position=vocal_position,
            no_drums=no_drums,
            export_format=export_format,
        )
        return jsonify(
            {
                "download_url": f"/masterizacao/audio/{output_name}",
                "filename": output_name,
                "mode": mode,
                "mode_label": mode_map[mode],
            }
        )
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 400
    except ImportError:
        return jsonify({"error": "Dependencia ausente: instale soundfile para exportar."}), 500
    except Exception:
        return jsonify({"error": "Falha ao gerar exportacao."}), 500
