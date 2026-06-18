import numpy as np

@app.route('/masterizacao/analise_data/<job_id>')
def get_analysis_data(job_id):
    librosa = _master_librosa()

    with MASTER_LOCK:
        job = MASTER_JOBS.get(job_id)
    
    if not job:
        return jsonify({"error": "Job não encontrado"}), 404

    input_path = job["input_path"]
    y, sr = librosa.load(input_path, duration=30, mono=True) # Carrega para performance

    # 1. FFT (Barras)
    fft_vals = np.abs(np.fft.rfft(y[:2048]))
    
    # 2. STFT (Espectrograma / Waterfall)
    stft_matrix = np.abs(librosa.stft(y))
    db_spectrogram = librosa.amplitude_to_db(stft_matrix, ref=np.max)

    return jsonify({
        "fft": fft_vals.tolist(),
        "spectrogram": db_spectrogram.tolist(),
        "sr": sr
    })


@app.route('/masterizacao/analise_ia/<job_id>')
def analisar_musica_ia(job_id):
    librosa = _master_librosa()

    with MASTER_LOCK:
        job = MASTER_JOBS.get(job_id)
    
    if not job:
        return jsonify({"error": "Job não encontrado"}), 404

    input_path = job["input_path"]
    
    try:
        # Carrega 15 segundos do meio da música para análise
        y, sr = librosa.load(input_path, duration=15, offset=10)
        
        if len(y) == 0:
            return jsonify({"genero_label": "Desconhecido", "preset_aplicado": "lufs14", "vocal_info": None})

        # 1. Extração de Features Espectrais Básicas
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)[0]
        rms = librosa.feature.rms(y=y)[0]
        
        # Medição de Dinâmica (Crest Factor aproximado em dB)
        peak = np.max(np.abs(y))
        avg_rms = np.mean(rms)
        crest_factor = 20 * np.log10(peak / (avg_rms + 1e-6))

        zero_crossing_rate = librosa.feature.zero_crossing_rate(y)[0]
        
        mean_centroid = float(np.mean(spectral_centroids))
        mean_rolloff = float(np.mean(spectral_rolloff))
        mean_zcr = float(np.mean(zero_crossing_rate))
        

        # HISTOGRAMA DE FREQUÊNCIAS

        S = np.abs(librosa.stft(y))
        freqs = librosa.fft_frequencies(sr=sr)

        graves = float(
            np.sum(
                S[(freqs >= 20) & (freqs < 250)]
            )
        )

        medios = float(
            np.sum(
                S[(freqs >= 250) & (freqs < 4000)]
            )
        )

        agudos = float(
            np.sum(
                S[(freqs >= 4000)]
            )
        )

        total = graves + medios + agudos

        if total <= 0:
            total = 1

        graves_pct = round((graves / total) * 100, 1)
        medios_pct = round((medios / total) * 100, 1)
        agudos_pct = round((agudos / total) * 100, 1)

        diagnostico = []

        if graves_pct > 50:
            diagnostico.append("Excesso de graves")

        elif graves_pct < 20:
            diagnostico.append("Pouco peso nos graves")

        else:
            diagnostico.append("Graves equilibrados")

        if medios_pct > 60:
            diagnostico.append("Médios excessivos")

        elif medios_pct < 25:
            diagnostico.append("Pouca presença nos médios")

        else:
            diagnostico.append("Médios equilibrados")

        if agudos_pct > 30:
            diagnostico.append("Agudos agressivos")

        elif agudos_pct < 10:
            diagnostico.append("Pouco brilho")

        else:
            diagnostico.append("Agudos equilibrados")


        mix_score = 100

        mix_score -= abs(graves_pct - 35) * 0.8
        mix_score -= abs(medios_pct - 45) * 0.6
        mix_score -= abs(agudos_pct - 20) * 0.8

        mix_score = max(0, min(100, round(mix_score)))


        master_score = mix_score

        # Penaliza se a dinâmica estiver muito "achatada" (over-mastered)
        if crest_factor < 8:
            master_score -= 10
            diagnostico.append("Dinâmica muito comprimida (Brickwall)")

        if mean_rolloff > 7000:
            master_score += 5

        if mean_centroid > 1800:
            master_score += 5

        master_score = min(100, round(master_score))
        spotify_score = 100

        if graves_pct > 55:
            spotify_score -= 15

        if agudos_pct < 10:
            spotify_score -= 10

        spotify_score = max(0, spotify_score)


        # --- ALGORITMO DETECTOR DE VOZ E EXTRACTOR DE F0 (PYIN) ---
        # Limitamos a busca entre 65Hz (Grave Masculino) e 500Hz (Agudo Feminino) para focar na voz humana
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y, 
            fmin=librosa.note_to_hz('C2'),  # ~65 Hz
            fmax=librosa.note_to_hz('B4'),  # ~494 Hz
            sr=sr
        )
        
        # Filtra apenas os frames onde a IA tem certeza que há voz cantada/falada (rejeita silêncio e ruído)
        vocal_frequencies = f0[~np.isnan(f0)]
        
        vocal_info = None
        if len(vocal_frequencies) > 15: # Se detectou voz contínua por tempo suficiente
            mean_f0 = float(np.mean(vocal_frequencies))
            
            # Classificação Lógica Baseada em Frequência Biológica
            if mean_f0 > 165:
                genero_voz = "Feminino"
                if mean_f0 > 240: classificacao = "Soprano (Aguda)"
                elif mean_f0 > 200: classificacao = "Mezzo-Soprano (Média)"
                else: classificacao = "Contralto (Grave)"
            else:
                genero_voz = "Masculino"
                if mean_f0 > 130: classificacao = "Tenor (Aguda)"
                elif mean_f0 > 100: classificacao = "Barítono (Média)"
                else: classificacao = "Baixo (Grave)"
                
            vocal_info = {
                "f0_media_hz": round(mean_f0, 1),
                "genero_voz": genero_voz,
                "classificacao": classificacao
            }

        # 2. Árvore de Decisão de Gênero Musical Geral
        preset = "pop"
        if mean_centroid < 1300 and mean_rolloff < 2500:
            genero = "Podcast / Voz"
            preset = "radio"
        elif vocal_info and vocal_info["genero_voz"] == "Feminino" and mean_zcr < 0.06:
            genero = "Acústico (Voz Feminina)"
            preset = "spotify"
        elif vocal_info and vocal_info["genero_voz"] == "Masculino" and mean_zcr < 0.06:
            genero = "Acústico (Voz Masculina)"
            preset = "spotify"
        elif mean_zcr > 0.11 or (mean_centroid > 2900 and mean_rolloff > 6000):
            genero = "Heavy Metal / Hardcore"
            preset = "led_zeppelin"
        elif mean_centroid >= 2100 and mean_centroid < 2900:
            genero = "Rock"
            preset = "rock"
        else:
            genero = "Pop / Eletrônica"
            preset = "pop"

        return jsonify({
            "genero_detected": preset,
            "genero_label": genero,
            "preset_aplicado": preset,
            "vocal_info": vocal_info,

            "histograma": {
                "graves": graves_pct,
                "medios": medios_pct,
                "agudos": agudos_pct
            },

            "diagnostico": diagnostico,

            "scores": {
                "mix_score": mix_score,
                "master_score": master_score,
                "spotify_score": spotify_score
            },

            "metrics": {
                "centroid": round(mean_centroid, 1),
                "rolloff": round(mean_rolloff, 1),
                "zcr": round(mean_zcr, 4),
                "crest_factor_db": round(float(crest_factor), 2)
            }
        })
        
    except Exception as e:
        return jsonify({"error": f"Falha na análise interna da IA: {str(e)}"}), 500
