from flask import Blueprint
from modules.layout import header

afinador_bp = Blueprint('afinador', __name__)

@afinador_bp.route("/afinador")
def afinador_digital():
    html = header("CifrasFlix - Afinador Digital")
    
    html += """
    <style>
        .afinadorContainer {
            max-width: 1000px;
            margin: 20px auto;
            padding: 0 15px 40px;
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            color: var(--text);
        }
        
        .afinadorHeader {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--line);
        }
        
        .afinadorHeader h1 {
            font-size: 28px;
            font-weight: 700;
            margin: 0;
            background: linear-gradient(135deg, var(--teal) 0%, var(--blue) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .afinadorHeader p {
            margin: 5px 0 0;
            color: var(--muted);
            font-size: 14px;
        }

        .afinadorGrid {
            display: grid;
            grid-template-columns: 1fr 340px;
            gap: 24px;
        }

        @media (max-width: 920px) {
            .afinadorGrid {
                grid-template-columns: 1fr;
            }
        }

        .afinadorCard {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
            display: flex;
            flex-direction: column;
            gap: 20px;
            align-items: center;
        }

        body.theme-dark .afinadorCard {
            background: var(--surface-2);
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
        }

        .selectorGroup {
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .selectorGroup label {
            font-size: 12px;
            font-weight: 700;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .instrumentSelect, .tuningSelect {
            width: 100%;
            min-height: 42px;
            padding: 0 12px;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--surface-2);
            color: var(--text);
            font-weight: 600;
            outline: none;
            cursor: pointer;
        }

        body.theme-dark .instrumentSelect, body.theme-dark .tuningSelect {
            background: var(--surface);
        }

        /* Ponteiro e Gauge */
        .gaugeWrapper {
            width: 100%;
            height: 220px;
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: var(--surface-2);
            border: 1px solid var(--line);
            border-radius: 16px;
            overflow: hidden;
        }

        body.theme-dark .gaugeWrapper {
            background: var(--surface);
        }

        .gaugeCanvas {
            position: absolute;
            width: 100%;
            height: 100%;
            top: 0;
            left: 0;
        }

        .gaugeInfo {
            z-index: 2;
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        .bigNoteDisplay {
            font-size: 78px;
            font-weight: 900;
            line-height: 1;
            margin: 0;
            color: var(--text);
            transition: color 0.2s ease;
        }

        .bigNoteDisplay.inTune {
            color: #10b981;
            text-shadow: 0 0 20px rgba(16, 185, 129, 0.4);
        }

        .tunerInstruction {
            font-size: 16px;
            font-weight: 700;
            margin-top: 10px;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .tunerInstruction.inTune {
            color: #10b981;
        }

        .tunerInstruction.tighten {
            color: var(--teal);
        }

        .tunerInstruction.loosen {
            color: var(--blue);
        }

        .freqValue {
            font-size: 13px;
            color: var(--muted);
            margin-top: 4px;
        }

        /* Layout das Cordas */
        .stringsLayoutCard {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        body.theme-dark .stringsLayoutCard {
            background: var(--surface-2);
        }

        .stringsTitle {
            font-size: 15px;
            font-weight: 700;
            margin: 0;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--muted);
            border-bottom: 1px solid var(--line);
            padding-bottom: 10px;
        }

        .stringsList {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .instrumentStringRow {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 14px;
            background: var(--surface-2);
            border: 1px solid var(--line);
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.2s ease;
            position: relative;
            overflow: hidden;
        }

        body.theme-dark .instrumentStringRow {
            background: var(--surface);
        }

        .instrumentStringRow:hover {
            border-color: var(--teal);
            transform: translateX(4px);
        }

        .instrumentStringRow.active {
            border-color: #10b981;
            background: rgba(16, 185, 129, 0.05);
            box-shadow: 0 0 10px rgba(16, 185, 129, 0.15);
        }

        .stringNumBadge {
            width: 26px;
            height: 26px;
            background: var(--line);
            color: var(--text);
            border-radius: 50%;
            display: grid;
            place-items: center;
            font-size: 12px;
            font-weight: 700;
        }

        .instrumentStringRow.active .stringNumBadge {
            background: #10b981;
            color: #000;
        }

        .stringNoteName {
            font-size: 18px;
            font-weight: 800;
            flex: 1;
        }

        .stringFreqLabel {
            font-size: 12px;
            color: var(--muted);
        }

        .stringVibrationLine {
            position: absolute;
            left: 0;
            bottom: 0;
            width: 100%;
            height: 3px;
            background: transparent;
        }

        .instrumentStringRow.active .stringVibrationLine {
            background: #10b981;
            animation: vibrateLine 0.2s infinite alternate;
        }

        @keyframes vibrateLine {
            0% { transform: translateY(-1px); opacity: 0.6; }
            100% { transform: translateY(1px); opacity: 1; }
        }

        /* Botão liga/desliga microfone */
        .micBtn {
            width: 100%;
            min-height: 48px;
            font-size: 15px;
            font-weight: 700;
            border-radius: 10px;
            border: 1px solid var(--line);
            background: var(--surface-2);
            color: var(--text);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: all 0.2s ease;
        }

        body.theme-dark .micBtn {
            background: var(--surface);
        }

        .micBtn.active {
            background: rgba(239, 68, 68, 0.15);
            border-color: var(--rose);
            color: var(--rose);
            box-shadow: 0 0 10px rgba(239, 68, 68, 0.18);
        }

        /* Instruções de Uso */
        .instructionsCard {
            width: 100%;
            padding: 16px;
            background: rgba(255, 122, 0, 0.04);
            border: 1px solid rgba(255, 122, 0, 0.2);
            border-radius: 12px;
            font-size: 13px;
            color: var(--text);
            line-height: 1.5;
        }

        body.theme-dark .instructionsCard {
            background: rgba(30, 224, 198, 0.04);
            border-color: rgba(30, 224, 198, 0.2);
        }
    </style>

    <div class="afinadorContainer">
        <section class="afinadorHeader">
            <div>
                <h1>Afinador Digital</h1>
                <p>Afine seu instrumento em tempo real usando o microfone ou ouvindo as notas de referência.</p>
            </div>
            <a class="clearHistoryBtn" href="/" style="align-self: center;">Voltar à Central</a>
        </section>

        <div class="afinadorGrid">
            <!-- PAINEL DO AFINADOR (GAUGE) -->
            <div class="afinadorCard">
                <!-- Instrumento & Afinação -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; width: 100%;">
                    <div class="selectorGroup">
                        <label>Instrumento</label>
                        <select class="instrumentSelect" id="instrumentSelect" onchange="changeInstrument(this.value)">
                            <option value="guitar">Violão / Guitarra (6 cordas)</option>
                            <option value="bass">Baixo (4 cordas)</option>
                            <option value="ukulele">Ukulele (4 cordas)</option>
                        </select>
                    </div>
                    <div class="selectorGroup">
                        <label>Afinação</label>
                        <select class="tuningSelect" id="tuningSelect" onchange="changeTuning(this.value)">
                            <!-- Opções carregadas dinamicamente -->
                        </select>
                    </div>
                </div>

                <!-- Visão do Afinador (Ponteiro) -->
                <div class="gaugeWrapper">
                    <canvas class="gaugeCanvas" id="gaugeCanvas"></canvas>
                    <div class="gaugeInfo">
                        <p class="bigNoteDisplay" id="bigNote">-</p>
                        <span class="tunerInstruction" id="tunerInstruction">Aguardando som...</span>
                        <span class="freqValue" id="freqValue">-- Hz</span>
                    </div>
                </div>

                <!-- Botão de Microfone -->
                <button type="button" class="micBtn" id="tunerMicBtn" onclick="toggleTunerMic()">
                    <span id="micIcon">🎤</span>
                    <span id="micText">Ativar Microfone</span>
                </button>

                <!-- Box Informativa -->
                <div class="instructionsCard">
                    💡 <strong>Como usar:</strong> Clique em "Ativar Microfone" e toque uma corda do seu instrumento. O afinador detectará a nota automaticamente. Se preferir afinar de ouvido, clique em qualquer corda no painel lateral para escutar a nota de referência exata.
                </div>
            </div>

            <!-- PAINEL DAS CORDAS DO INSTRUMENTO -->
            <div class="stringsLayoutCard">
                <h2 class="stringsTitle" id="stringsTitle">Cordas de Referência</h2>
                <div class="stringsList" id="stringsList">
                    <!-- Cordas renderizadas via JS -->
                </div>
            </div>
        </div>
    </div>

    <script>
        // --- 1. CONFIGURAÇÕES DAS AFINAÇÕES ---
        const instrumentsData = {
            guitar: {
                name: "Violão / Guitarra",
                tunings: {
                    standard: {
                        name: "Padrão (EADGBE)",
                        notes: [
                            { note: "E", octave: 4, freq: 329.63, label: "1ª Corda (Mi)" },
                            { note: "B", octave: 3, freq: 246.94, label: "2ª Corda (Si)" },
                            { note: "G", octave: 3, freq: 196.00, label: "3ª Corda (Sol)" },
                            { note: "D", octave: 3, freq: 146.83, label: "4ª Corda (Ré)" },
                            { note: "A", octave: 2, freq: 110.00, label: "5ª Corda (Lá)" },
                            { note: "E", octave: 2, freq: 82.41,  label: "6ª Corda (Mi)" }
                        ]
                    },
                    dropD: {
                        name: "Drop D (DADGBE)",
                        notes: [
                            { note: "E", octave: 4, freq: 329.63, label: "1ª Corda (Mi)" },
                            { note: "B", octave: 3, freq: 246.94, label: "2ª Corda (Si)" },
                            { note: "G", octave: 3, freq: 196.00, label: "3ª Corda (Sol)" },
                            { note: "D", octave: 3, freq: 146.83, label: "4ª Corda (Ré)" },
                            { note: "A", octave: 2, freq: 110.00, label: "5ª Corda (Lá)" },
                            { note: "D", octave: 2, freq: 73.42,  label: "6ª Corda (Ré)" }
                        ]
                    },
                    dadgad: {
                        name: "DADGAD",
                        notes: [
                            { note: "D", octave: 4, freq: 293.66, label: "1ª Corda (Ré)" },
                            { note: "A", octave: 3, freq: 220.00, label: "2ª Corda (Lá)" },
                            { note: "G", octave: 3, freq: 196.00, label: "3ª Corda (Sol)" },
                            { note: "D", octave: 3, freq: 146.83, label: "4ª Corda (Ré)" },
                            { note: "A", octave: 2, freq: 110.00, label: "5ª Corda (Lá)" },
                            { note: "D", octave: 2, freq: 73.42,  label: "6ª Corda (Ré)" }
                        ]
                    }
                }
            },
            bass: {
                name: "Baixo",
                tunings: {
                    standard: {
                        name: "Padrão (EADG)",
                        notes: [
                            { note: "G", octave: 2, freq: 98.00, label: "1ª Corda (Sol)" },
                            { note: "D", octave: 2, freq: 73.42, label: "2ª Corda (Ré)" },
                            { note: "A", octave: 1, freq: 55.00, label: "3ª Corda (Lá)" },
                            { note: "E", octave: 1, freq: 41.20, label: "4ª Corda (Mi)" }
                        ]
                    }
                }
            },
            ukulele: {
                name: "Ukulele",
                tunings: {
                    standard: {
                        name: "Padrão (GCEA)",
                        notes: [
                            { note: "A", octave: 4, freq: 440.00, label: "1ª Corda (Lá)" },
                            { note: "E", octave: 4, freq: 329.63, label: "2ª Corda (Mi)" },
                            { note: "C", octave: 4, freq: 261.63, label: "3ª Corda (Dó)" },
                            { note: "G", octave: 4, freq: 392.00, label: "4ª Corda (Sol)" }
                        ]
                    }
                }
            }
        };

        let currentInstrument = "guitar";
        let currentTuning = "standard";
        let activeTuningNotes = [];
        
        // --- 2. ENGINE DE ÁUDIO ---
        let tunerAudioCtx = null;
        let tunerMicStream = null;
        let tunerMicSource = null;
        let tunerAnalyser = null;
        let isTunerMicActive = false;
        let tunerIntervalId = null;
        
        // Cents atuais e nota detectada
        let currentCentsDeviation = 0;
        let detectedNoteStringIndex = -1; // índice da corda detectada (-1 se nenhuma)
        let lastDetectedFreq = 0;
        
        // Animação Gauge
        let gaugeAnimationId = null;

        function initTuner() {
            changeInstrument("guitar");
            drawTunerGauge();
        }

        function changeInstrument(inst) {
            currentInstrument = inst;
            
            // Popular select de afinações
            let select = document.getElementById("tuningSelect");
            select.innerHTML = "";
            
            let tunings = instrumentsData[inst].tunings;
            for (let tKey in tunings) {
                let opt = document.createElement("option");
                opt.value = tKey;
                opt.innerText = tunings[tKey].name;
                select.appendChild(opt);
            }
            
            changeTuning(select.value);
        }

        function changeTuning(tuning) {
            currentTuning = tuning;
            activeTuningNotes = instrumentsData[currentInstrument].tunings[tuning].notes;
            renderStringsPanel();
        }

        function renderStringsPanel() {
            let container = document.getElementById("stringsList");
            container.innerHTML = "";
            
            activeTuningNotes.forEach((noteInfo, idx) => {
                let row = document.createElement("div");
                row.className = "instrumentStringRow";
                row.id = "stringRow_" + idx;
                row.onclick = () => playReferenceTone(noteInfo.freq, idx);
                
                let numBadge = document.createElement("span");
                numBadge.className = "stringNumBadge";
                numBadge.innerText = activeTuningNotes.length - idx; // numeração de baixo pra cima
                
                let noteName = document.createElement("span");
                noteName.className = "stringNoteName";
                noteName.innerText = noteInfo.note + noteInfo.octave;
                
                let freqLabel = document.createElement("span");
                freqLabel.className = "stringFreqLabel";
                freqLabel.innerText = noteInfo.freq.toFixed(1) + " Hz";
                
                let vibLine = document.createElement("div");
                vibLine.className = "stringVibrationLine";
                
                row.appendChild(numBadge);
                row.appendChild(noteName);
                row.appendChild(freqLabel);
                row.appendChild(vibLine);
                
                container.appendChild(row);
            });
        }

        // Tocar Tom de Referência
        function playReferenceTone(freq, idx) {
            // Inicializar AudioContext se não existir
            initTunerAudioContext();
            if (tunerAudioCtx.state === "suspended") {
                tunerAudioCtx.resume();
            }
            
            // Destacar corda clicada na UI temporariamente
            document.querySelectorAll(".instrumentStringRow").forEach(r => r.classList.remove("active"));
            let row = document.getElementById("stringRow_" + idx);
            row.classList.add("active");
            
            // Disparar onda senoidal (som de diapasão puro)
            let osc = tunerAudioCtx.createOscillator();
            let gain = tunerAudioCtx.createGain();
            
            osc.type = "sine";
            osc.connect(gain);
            gain.connect(tunerAudioCtx.destination);
            
            osc.frequency.setValueAtTime(freq, tunerAudioCtx.currentTime);
            
            // Envelope de volume (decay linear de 2 segundos)
            gain.gain.setValueAtTime(0.0, tunerAudioCtx.currentTime);
            gain.gain.linearRampToValueAtTime(0.4, tunerAudioCtx.currentTime + 0.05); // ataque rápido
            gain.gain.setValueAtTime(0.4, tunerAudioCtx.currentTime + 0.5);
            gain.gain.exponentialRampToValueAtTime(0.001, tunerAudioCtx.currentTime + 2.2); // fade out longo
            
            osc.start();
            osc.stop(tunerAudioCtx.currentTime + 2.3);
            
            setTimeout(() => {
                row.classList.remove("active");
            }, 2200);
        }

        function initTunerAudioContext() {
            if (tunerAudioCtx) return;
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            tunerAudioCtx = new AudioCtx();
        }

        // --- 3. LOGICA DO MICROFONE DO AFINADOR ---
        
        function toggleTunerMic() {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                alert("Segurança do Navegador: O acesso ao microfone foi bloqueado.\\n\\nComo corrigir:\\n1. Certifique-se de acessar usando o endereço local: http://localhost:5000 ou http://127.0.0.1:5000\\n2. Se estiver acessando de outro computador na rede, o navegador exige conexão segura HTTPS para liberar o microfone.");
                isTunerMicActive = false;
                return;
            }

            isTunerMicActive = !isTunerMicActive;
            let btn = document.getElementById("tunerMicBtn");
            let icon = document.getElementById("micIcon");
            let text = document.getElementById("micText");
            
            if (isTunerMicActive) {
                navigator.mediaDevices.getUserMedia({ audio: true, video: false })
                .then(stream => {
                    tunerMicStream = stream;
                    initTunerAudioContext();
                    if (tunerAudioCtx.state === "suspended") {
                        tunerAudioCtx.resume();
                    }
                    
                    tunerMicSource = tunerAudioCtx.createMediaStreamSource(stream);
                    tunerAnalyser = tunerAudioCtx.createAnalyser();
                    tunerAnalyser.fftSize = 2048;
                    tunerMicSource.connect(tunerAnalyser);
                    
                    // Conexão para manter o stream ativo no Chrome
                    let silentGain = tunerAudioCtx.createGain();
                    silentGain.gain.setValueAtTime(0.0, tunerAudioCtx.currentTime);
                    tunerAnalyser.connect(silentGain);
                    silentGain.connect(tunerAudioCtx.destination);
                    
                    btn.classList.add("active");
                    icon.innerText = "🛑";
                    text.innerText = "Desativar Microfone";
                    
                    // Iniciar análise de pitch
                    tunerPitchLoop();
                })
                .catch(err => {
                    console.error("Erro ao abrir microfone: ", err);
                    alert("Acesso ao microfone recusado!\\n\\nVerifique se o navegador não bloqueou o microfone no ícone de cadeado/configurações ao lado da barra de endereços e tente novamente.");
                    isTunerMicActive = false;
                });
            } else {
                stopTunerMic();
            }
        }
        
        function stopTunerMic() {
            isTunerMicActive = false;
            let btn = document.getElementById("tunerMicBtn");
            let icon = document.getElementById("micIcon");
            let text = document.getElementById("micText");
            
            btn.classList.remove("active");
            icon.innerText = "🎤";
            text.innerText = "Ativar Microfone";
            
            if (tunerIntervalId) {
                cancelAnimationFrame(tunerIntervalId);
                tunerIntervalId = null;
            }
            
            if (tunerMicStream) {
                tunerMicStream.getTracks().forEach(track => track.stop());
                tunerMicStream = null;
            }
            
            // Resetar UI
            document.getElementById("bigNote").innerText = "-";
            document.getElementById("bigNote").classList.remove("inTune");
            document.getElementById("tunerInstruction").innerText = "Aguardando som...";
            document.getElementById("tunerInstruction").className = "tunerInstruction";
            document.getElementById("freqValue").innerText = "-- Hz";
            
            currentCentsDeviation = 0;
            detectedNoteStringIndex = -1;
            document.querySelectorAll(".instrumentStringRow").forEach(r => r.classList.remove("active"));
        }

        function tunerPitchLoop() {
            if (!isTunerMicActive) return;
            tunerIntervalId = requestAnimationFrame(tunerPitchLoop);
            
            let bufferLength = tunerAnalyser.fftSize;
            let buffer = new Float32Array(bufferLength);
            if (typeof tunerAnalyser.getFloat32TimeDomainData === "function") {
                tunerAnalyser.getFloat32TimeDomainData(buffer);
            } else {
                let byteBuffer = new Uint8Array(bufferLength);
                tunerAnalyser.getByteTimeDomainData(byteBuffer);
                for (let i = 0; i < bufferLength; i++) {
                    buffer[i] = (byteBuffer[i] - 128) / 128.0;
                }
            }
            
            // Detecção de frequência fundamental
            let freq = autoCorrelateTuner(buffer, tunerAudioCtx.sampleRate);
            
            if (freq !== -1) {
                lastDetectedFreq = freq;
                document.getElementById("freqValue").innerText = freq.toFixed(1) + " Hz";
                
                // Encontrar qual corda da afinação ativa está mais perto da frequência detectada
                let closestIndex = -1;
                let minDiff = Infinity;
                
                activeTuningNotes.forEach((noteInfo, idx) => {
                    let diff = Math.abs(freq - noteInfo.freq);
                    if (diff < minDiff) {
                        minDiff = diff;
                        closestIndex = idx;
                    }
                });
                
                if (closestIndex !== -1) {
                    let targetNote = activeTuningNotes[closestIndex];
                    
                    // Exibir nota grande na UI
                    document.getElementById("bigNote").innerText = targetNote.note;
                    
                    // Calcular desvio em cents em relação à nota alvo exata
                    let cents = Math.round(1200 * Math.log2(freq / targetNote.freq));
                    currentCentsDeviation = cents;
                    detectedNoteStringIndex = closestIndex;
                    
                    // Destacar corda ativa no painel lateral
                    document.querySelectorAll(".instrumentStringRow").forEach((r, idx) => {
                        r.classList.toggle("active", idx === closestIndex);
                    });
                    
                    // Instrução de ajuste
                    let inst = document.getElementById("tunerInstruction");
                    if (cents < -4) {
                        inst.innerText = "APERTAR CORDA (Muito baixo)";
                        inst.className = "tunerInstruction tighten";
                        document.getElementById("bigNote").classList.remove("inTune");
                    } else if (cents > 4) {
                        inst.innerText = "SOLTAR CORDA (Muito alto)";
                        inst.className = "tunerInstruction loosen";
                        document.getElementById("bigNote").classList.remove("inTune");
                    } else {
                        inst.innerText = "AFINADO!";
                        inst.className = "tunerInstruction inTune";
                        document.getElementById("bigNote").classList.add("inTune");
                    }
                }
            } else {
                // Silêncio / sem sinal coerente
                document.getElementById("tunerInstruction").innerText = "Ouvindo...";
                document.getElementById("tunerInstruction").className = "tunerInstruction";
                currentCentsDeviation = 0;
            }
        }
        
        function autoCorrelateTuner(buf, sampleRate) {
            let SIZE = buf.length;
            let rms = 0;

            for (let i = 0; i < SIZE; i++) {
                let val = buf[i];
                rms += val * val;
            }
            rms = Math.sqrt(rms / SIZE);
            
            // Lower threshold to be more sensitive to acoustic guitar sound
            if (rms < 0.0015) return -1; 

            // Limit autocorrelation calculations to our target frequency range (35Hz to 800Hz)
            // This reduces the calculations from SIZE (2048) to maxLag (around 1260)
            let maxLag = Math.min(SIZE, Math.floor(sampleRate / 35));
            let minLag = Math.floor(sampleRate / 800);
            
            let c = new Float32Array(maxLag);
            for (let i = 0; i < maxLag; i++) {
                let sum = 0;
                for (let j = 0; j < SIZE - i; j++) {
                    sum += buf[j] * buf[j + i];
                }
                c[i] = sum;
            }

            // Find the local minimum/zero crossing lag
            let d = 0;
            while (d < maxLag - 1 && c[d] > c[d + 1]) {
                d++;
            }
            
            // Find maximum peak after zero crossing
            let maxval = -1;
            let maxpos = -1;
            for (let i = d; i < maxLag; i++) {
                if (c[i] > maxval) {
                    maxval = c[i];
                    maxpos = i;
                }
            }
            
            let T0 = maxpos;

            if (T0 > minLag && T0 < maxLag) {
                // Parabolic interpolation for sub-sample accuracy
                if (T0 > 0 && T0 < maxLag - 1) {
                    let x1 = c[T0 - 1], x2 = c[T0], x3 = c[T0 + 1];
                    let a = (x1 + x3 - 2 * x2) / 2;
                    let b = (x3 - x1) / 2;
                    if (a !== 0) T0 = T0 - b / (2 * a);
                }
                let calculatedFreq = sampleRate / T0;
                if (calculatedFreq > 35 && calculatedFreq < 800) {
                    return calculatedFreq;
                }
            }
            return -1;
        }

        // --- 4. ANIMACAO DO PONTEIRO GAUGE ---
        function drawTunerGauge() {
            let canvas = document.getElementById("gaugeCanvas");
            let ctx = canvas.getContext("2d");
            
            function renderLoop() {
                requestAnimationFrame(renderLoop);
                
                let width = canvas.width = canvas.parentElement.clientWidth;
                let height = canvas.height = canvas.parentElement.clientHeight;
                
                ctx.clearRect(0, 0, width, height);
                
                // Centro do gauge
                let cx = width / 2;
                let cy = height - 30;
                let radius = height * 0.7;
                
                // Desenhar arco de fundo
                ctx.beginPath();
                ctx.arc(cx, cy, radius, Math.PI * 1.15, Math.PI * 1.85);
                ctx.lineWidth = 10;
                ctx.strokeStyle = "rgba(107, 114, 128, 0.15)";
                ctx.stroke();
                
                // Desenhar faixas coloridas (Esquerda: bemol, Centro: afinado, Direita: sustenido)
                // Esquerda (azul/laranja)
                ctx.beginPath();
                ctx.arc(cx, cy, radius, Math.PI * 1.15, Math.PI * 1.48);
                ctx.lineWidth = 10;
                ctx.strokeStyle = "rgba(37, 99, 235, 0.25)";
                ctx.stroke();
                
                // Centro (Verde afinado)
                ctx.beginPath();
                ctx.arc(cx, cy, radius, Math.PI * 1.48, Math.PI * 1.52);
                ctx.lineWidth = 12;
                ctx.strokeStyle = "#10b981";
                ctx.stroke();
                
                // Direita (sustenido)
                ctx.beginPath();
                ctx.arc(cx, cy, radius, Math.PI * 1.52, Math.PI * 1.85);
                ctx.lineWidth = 10;
                ctx.strokeStyle = "rgba(255, 122, 0, 0.25)";
                ctx.stroke();
                
                // Adicionar linhas graduais (Ticks)
                ctx.lineWidth = 2;
                for (let i = -50; i <= 50; i += 10) {
                    let angle = Math.PI * 1.5 + (i * (Math.PI * 0.35) / 50);
                    let startX = cx + (radius - 12) * Math.cos(angle);
                    let startY = cy + (radius - 12) * Math.sin(angle);
                    let endX = cx + (radius + 2) * Math.cos(angle);
                    let endY = cy + (radius + 2) * Math.sin(angle);
                    
                    ctx.beginPath();
                    ctx.moveTo(startX, startY);
                    ctx.lineTo(endX, endY);
                    ctx.strokeStyle = (i === 0) ? "#10b981" : "rgba(107, 114, 128, 0.3)";
                    ctx.stroke();
                }
                
                // Agulha com suavização exponencial para amortecer o movimento do ponteiro
                if (typeof window.smoothedCents === "undefined") {
                    window.smoothedCents = 0;
                }
                let rawCents = isTunerMicActive ? currentCentsDeviation : 0;
                window.smoothedCents = (0.08 * rawCents) + (0.92 * window.smoothedCents);
                let cents = Math.max(-50, Math.min(50, window.smoothedCents));
                
                // Converter cents para ângulo
                let targetAngle = Math.PI * 1.5 + (cents * (Math.PI * 0.33) / 50);
                
                // 1. Desenhar o indicador triangular deslizante (▼) no topo do arco apontando para baixo
                let indicatorRadius = radius + 4;
                let indX = cx + indicatorRadius * Math.cos(targetAngle);
                let indY = cy + indicatorRadius * Math.sin(targetAngle);
                
                ctx.save();
                ctx.translate(indX, indY);
                ctx.rotate(targetAngle + Math.PI / 2); // Alinha apontando para o centro (cy, cx)
                
                // Se estiver afinado, fica verde. Caso contrário, azul do tema.
                if (Math.abs(cents) <= 4 && detectedNoteStringIndex !== -1) {
                    ctx.fillStyle = "#10b981";
                } else {
                    ctx.fillStyle = "#3a7097"; // Cor azul escura igual a do print
                }
                
                ctx.beginPath();
                ctx.moveTo(0, 0); // Ponta do triângulo
                ctx.lineTo(-14, -20);
                ctx.lineTo(14, -20);
                ctx.closePath();
                ctx.fill();
                ctx.restore();
                
                // 2. Desenhar as notas cromáticas ao redor do arco para guiar o músico
                let chroma = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
                let activeNoteStr = "-";
                if (detectedNoteStringIndex !== -1 && activeTuningNotes[detectedNoteStringIndex]) {
                    activeNoteStr = activeTuningNotes[detectedNoteStringIndex].note;
                }
                
                if (activeNoteStr !== "-") {
                    let baseIdx = chroma.indexOf(activeNoteStr);
                    if (baseIdx !== -1) {
                        ctx.textAlign = "center";
                        ctx.textBaseline = "middle";
                        
                        // Desenhar 5 notas cromáticas ao longo do arco
                        for (let offset = -2; offset <= 2; offset++) {
                            let noteIdx = (baseIdx + offset + 12) % 12;
                            let noteText = chroma[noteIdx];
                            
                            // Espaçamento angular entre as notas no arco
                            let angle = Math.PI * 1.5 + (offset * (Math.PI * 0.155));
                            
                            if (offset === 0) {
                                ctx.font = "bold 38px 'Inter', sans-serif";
                                // Azul escuro destacado para a nota atual
                                ctx.fillStyle = "#3a7097";
                            } else {
                                ctx.font = "bold 24px 'Inter', sans-serif";
                                // Cinza desbotado para as notas vizinhas
                                ctx.fillStyle = "rgba(148, 163, 184, 0.4)";
                            }
                            
                            let textX = cx + (radius - 40) * Math.cos(angle);
                            let textY = cy + (radius - 40) * Math.sin(angle);
                            ctx.fillText(noteText, textX, textY);
                        }
                    }
                }
            }
            renderLoop();
        }

        // Inicializar na carga da página
        window.addEventListener("DOMContentLoaded", initTuner);
    </script>
    """
    
    html += "</main></body></html>"
    return html
