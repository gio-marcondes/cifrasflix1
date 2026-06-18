// ==========================================
// MÓDULO DE ANÁLISE ESPECTRAL E VISUALIZAÇÃO
// ==========================================

let modoEspectroAtivo = 'bars';
let waterfallCanvasAux = null;
let peakHoldArray = null; // Guarda os maiores picos para a linha vermelha

function mudarModoEspectro(modo) {
    modoEspectroAtivo = modo;
    
    // Atualiza o select nativo do painel de baixo
    const selectMode = document.getElementById('settingSelectMode');
    if (selectMode) selectMode.value = modo;

    const botoes = document.querySelectorAll('[onclick^="mudarModoEspectro"]');
    botoes.forEach(btn => {
        btn.classList.toggle('is-on', btn.getAttribute('onclick').includes(modo));
    });
}

function atualizarInformacoesFFT() {
    const analyser = typeof masterEqState !== 'undefined' ? masterEqState.analyser : null;
    const hzBadge = document.getElementById('hzBinBadge');
    const fftSelect = document.getElementById('settingFftSize');
    
    if (!hzBadge || !fftSelect) return;

    const sampleRate = (typeof masterEqState !== 'undefined' && masterEqState.context) ? masterEqState.context.sampleRate : 44100;
    const currentFftSize = parseInt(fftSelect.value);

    const hzPerBin = sampleRate / currentFftSize;
    hzBadge.textContent = hzPerBin.toFixed(1) + ' Hz/bin';

    if (analyser) {
        if (analyser.fftSize !== currentFftSize) {
            analyser.fftSize = currentFftSize;
        }
        
        const smoothingSlider = document.getElementById('settingSmoothing');
        if (smoothingSlider) {
            analyser.smoothingTimeConstant = parseFloat(smoothingSlider.value);
        }
    }
}

function bindConfiguracoesVisualizacao() {
    const fftSelect = document.getElementById('settingFftSize');
    const smoothingSlider = document.getElementById('settingSmoothing');
    const smoothingBadge = document.getElementById('smoothingValueBadge');

    if (fftSelect) {
        fftSelect.addEventListener('change', () => {
            atualizarInformacoesFFT();
        });
    }

    if (smoothingSlider) {
        smoothingSlider.addEventListener('input', () => {
            const val = parseFloat(smoothingSlider.value);
            if (smoothingBadge) smoothingBadge.textContent = val.toFixed(2);
            
            if (typeof masterEqState !== 'undefined' && masterEqState.analyser) {
                masterEqState.analyser.smoothingTimeConstant = val;
            }
        });
    }
}

const NOTAS_PITCH = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
let lastPitchUpdateTime = 0;
let notaEstavelAtual = "";
let historicoNotas = [];

function resetVisualAfinador() {
    const lblPitchNota = document.getElementById('lblPitchNota');
    if (!lblPitchNota) return;
    lblPitchNota.textContent = "--";
    document.getElementById('lblPitchHz').textContent = "0.00 Hz";
    document.getElementById('pitchConfidenceText').textContent = "0%";
    document.getElementById('pitchConfidenceBar').style.width = "0%";
    document.getElementById('pitchCentsPointer').style.left = "50%";
    notaEstavelAtual = "";
    historicoNotas = [];
    document.querySelectorAll('.piano-key').forEach(key => {
        if (key.classList.contains('white-key')) key.style.background = '#fff';
        else key.style.background = '#1f2937';
    });
}

function calcularAutocorrelacaoMusica(buffer, sampleRate) {
    let maxSamples = Math.floor(buffer.length / 2);
    let melhorPeriodo = -1;
    let melhorCorrelacao = -1;

    for (let periodo = 20; periodo < maxSamples; periodo++) {
        let correlacao = 0;
        for (let i = 0; i < maxSamples; i++) {
            correlacao += buffer[i] * buffer[i + periodo];
        }
        if (correlacao > melhorCorrelacao) {
            melhorCorrelacao = correlacao;
            melhorPeriodo = periodo;
        }
    }
    if (melhorPeriodo > 0) return sampleRate / melhorPeriodo;
    return -1;
}

function startSpectrum() {
    const canvas = document.getElementById('spectrumCanvas');
    if(!canvas) return;
    const ctx = canvas.getContext('2d');
    const tooltip = document.getElementById('spectrumTooltip');

    waterfallCanvasAux = document.createElement('canvas');
    waterfallCanvasAux.width = canvas.width;
    waterfallCanvasAux.height = canvas.height;
    const ctxAux = waterfallCanvasAux.getContext('2d');

    const dbLines = [0, -20, -40, -60, -80];
    const freqLinesLog = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000];

    function drawGrid() {
        ctx.lineWidth = 1;
        ctx.font = '10px monospace';

        dbLines.forEach(db => {
            const y = ctx.lineWidth + ((db / -100) * (canvas.height - 25));
            
            ctx.strokeStyle = 'rgba(148, 163, 184, 0.08)';
            ctx.beginPath();
            ctx.moveTo(40, y);
            ctx.lineTo(canvas.width, y);
            ctx.stroke();

            ctx.fillStyle = '#8fa5b7';
            ctx.fillText(db + ' dB', 5, y + 3);
        });

        freqLinesLog.forEach(freq => {
            const logMin = Math.log10(20);
            const logMax = Math.log10(20000);
            const percent = (Math.log10(freq) - logMin) / (logMax - logMin);
            const x = 40 + percent * (canvas.width - 50);

            if (x >= 40 && x <= canvas.width) {
                ctx.strokeStyle = 'rgba(148, 163, 184, 0.08)';
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, canvas.height - 20);
                ctx.stroke();

                const label = freq >= 1000 ? (freq / 1000) + 'k' : freq;
                ctx.fillStyle = '#8fa5b7';
                ctx.fillText(label, x - 8, canvas.height - 5);
            }
        });
        
        ctx.strokeStyle = 'rgba(57, 215, 230, 0.2)';
        ctx.beginPath();
        ctx.moveTo(40, 0);
        ctx.lineTo(40, canvas.height - 20);
        ctx.lineTo(canvas.width, canvas.height - 20);
        ctx.stroke();
    }

    if (canvas) {
        canvas.addEventListener('mousemove', (e) => {
            const analyser = typeof masterEqState !== 'undefined' ? masterEqState.analyser : null;
            if (!analyser || !tooltip) return;

            const rect = canvas.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            if (mouseX < 40 || mouseX > canvas.width || mouseY > canvas.height - 20) {
                tooltip.style.display = 'none';
                return;
            }

            const sampleRate = masterEqState.context.sampleRate;
            const logMin = Math.log10(20);
            const logMax = Math.log10(20000);
            const percent = (mouseX - 40) / (canvas.width - 50);
            const freq = Math.pow(10, logMin + percent * (logMax - logMin));
            const dbVal = -((mouseY / (canvas.height - 25)) * 100);

            if (freq > 0 && freq <= 22000) {
                tooltip.style.display = 'block';
                tooltip.style.left = (mouseX + 15) + 'px';
                tooltip.style.top = (mouseY - 15) + 'px';
                
                const freqText = freq >= 1000 ? (freq / 1000).toFixed(2) + ' kHz' : Math.floor(freq) + ' Hz';
                tooltip.innerHTML = `<strong>${freqText}</strong><br><span style="color:#39d7e6">${dbVal.toFixed(1)} dBFS</span>`;
            }
        });

        canvas.addEventListener('mouseleave', () => {
            if (tooltip) tooltip.style.display = 'none';
        });
    }

    function draw() {
        requestAnimationFrame(draw);
        const analyser = typeof masterEqState !== 'undefined' ? masterEqState.analyser : null;
        const audioPlayer = document.getElementById("masterAudio");
        
        if (!analyser || !audioPlayer) {
            ctx.fillStyle = '#05070a';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            drawGrid();
            resetVisualAfinador(); 
            return;
        }

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        analyser.getByteFrequencyData(dataArray);

        const tempoAgora = performance.now();
        if (tempoAgora - lastPitchUpdateTime > 130) {
            lastPitchUpdateTime = tempoAgora;

            const timeBuffer = new Float32Array(analyser.fftSize);
            analyser.getFloatTimeDomainData(timeBuffer);
            
            const sampleRate = masterEqState.context.sampleRate;
            const currentF0 = calcularAutocorrelacaoMusica(timeBuffer, sampleRate);

            if (currentF0 > 40 && currentF0 < 2000 && !audioPlayer.paused) {
                const notaInMidi = 12 * Math.log2(currentF0 / 440) + 69;
                const midiArredondado = Math.round(notaInMidi);
                const oitava = Math.floor(midiArredondado / 12) - 1;
                const notaNome = NOTAS_PITCH[midiArredondado % 12];
                const centsDesvio = (notaInMidi - midiArredondado) * 100;

                let sumSquare = 0;
                for (let i = 0; i < timeBuffer.length; i++) sumSquare += timeBuffer[i] * timeBuffer[i];
                const rms = Math.sqrt(sumSquare / timeBuffer.length);
                const confianca = Math.min(100, Math.floor(rms * 450));

                if (confianca > 12) {
                    historicoNotas.push(notaNome);
                    if (historicoNotas.length > 3) historicoNotas.shift();

                    const contagem = {};
                    let notaMaisFrequente = notaNome;
                    let maxVotos = 0;
                    
                    historicoNotas.forEach(n => {
                        contagem[n] = (contagem[n] || 0) + 1;
                        if (contagem[n] > maxVotos) {
                            maxVotos = contagem[n];
                            notaMaisFrequente = n;
                        }
                    });

                    if (maxVotos >= 2) {
                        notaEstavelAtual = notaMaisFrequente;
                        
                        document.getElementById('lblPitchNota').textContent = `${notaEstavelAtual}${oitava}`;
                        document.getElementById('lblPitchHz').textContent = `${currentF0.toFixed(2)} Hz`;
                        document.getElementById('pitchConfidenceText').textContent = `${confianca}%`;
                        document.getElementById('pitchConfidenceBar').style.width = `${confianca}%`;

                        const ponteiroPercent = 50 + (centsDesvio / 50) * 50;
                        document.getElementById('pitchCentsPointer').style.left = `${Math.max(0, Math.min(100, ponteiroPercent))}%`;

                        document.querySelectorAll('.piano-key').forEach(key => {
                            if (key.getAttribute('data-note') === notaEstavelAtual) {
                                key.style.background = '#ffaa00'; 
                            } else {
                                if (key.classList.contains('white-key')) key.style.background = '#fff';
                                else key.style.background = '#1f2937';
                            }
                        });
                    }
                }
            } else if (audioPlayer.paused) {
                resetVisualAfinador();
            }
        }

        if (audioPlayer.paused) {
            resetVisualAfinador();
        }

        const graphWidth = canvas.width - 50;
        const logMin = Math.log10(20);
        const logMax = Math.log10(20000);
        const sampleRate = masterEqState.context.sampleRate;

        if (!peakHoldArray || peakHoldArray.length !== 60) {
            peakHoldArray = new Float32Array(60).fill(0);
        }

        if (modoEspectroAtivo === 'bars') {
            ctx.fillStyle = '#05070a';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            drawGrid();

            const totalBars = 45; 
            const barWidth = graphWidth / totalBars;

            for(let i = 0; i < totalBars; i++) {
                const percent = i / totalBars;
                const freq = Math.pow(10, logMin + percent * (logMax - logMin));
                
                const sampleIndex = Math.floor((freq / (sampleRate / 2)) * bufferLength);
                const value = dataArray[Math.min(sampleIndex, bufferLength - 1)];
                
                if (value > peakHoldArray[i]) {
                    peakHoldArray[i] = value;
                } else {
                    peakHoldArray[i] -= 0.4;
                }

                const barHeight = (value / 255) * (canvas.height - 25);
                const xPos = 40 + (i * barWidth);

                if (barHeight > 0) {
                    const gradient = ctx.createLinearGradient(0, canvas.height - 20, 0, canvas.height - 20 - barHeight);
                    gradient.addColorStop(0, '#39d7e6');
                    if (value > 210) {
                        gradient.addColorStop(0.6, '#ffaa00');
                        gradient.addColorStop(1, '#ff1a1a');
                    } else {
                        gradient.addColorStop(1, '#5b6bf5');
                    }
                    
                    ctx.fillStyle = gradient;
                    ctx.beginPath();
                    ctx.roundRect(xPos, canvas.height - 20 - barHeight, barWidth - 3, barHeight, [2, 2, 0, 0]);
                    ctx.fill();
                }

                const peakHeight = (Math.max(0, peakHoldArray[i]) / 255) * (canvas.height - 25);
                ctx.fillStyle = 'rgba(255, 30, 30, 0.8)';
                ctx.fillRect(xPos, canvas.height - 20 - peakHeight, barWidth - 3, 1.5);
            }
        } else if (modoEspectroAtivo === 'line') {
            ctx.fillStyle = '#05070a';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            drawGrid();

            ctx.lineWidth = 2.5;
            const gradientLine = ctx.createLinearGradient(40, 0, canvas.width, 0);
            gradientLine.addColorStop(0, '#39d7e6');
            gradientLine.addColorStop(0.5, '#7c3aed');
            gradientLine.addColorStop(1, '#ff2a85');
            ctx.strokeStyle = gradientLine;
            
            ctx.beginPath();
            
            for (let x = 0; x < graphWidth; x++) {
                const percent = x / graphWidth;
                const freq = Math.pow(10, logMin + percent * (logMax - logMin));
                const bin = Math.floor((freq / (sampleRate / 2)) * bufferLength);
                const value = dataArray[Math.min(bin, bufferLength - 1)];

                const y = (canvas.height - 20) - ((value / 255) * (canvas.height - 25));
                const xPos = 40 + x;

                if (x === 0) ctx.moveTo(xPos, y);
                else ctx.lineTo(xPos, y);
            }
            ctx.stroke();
        } else if (modoEspectroAtivo === 'spectrogram') {
            ctx.fillStyle = '#05070a';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            drawGrid();
            
            const numBands = 55;
            const bandWidth = graphWidth / numBands;
            const numSegments = 14;
            const segmentHeight = (canvas.height - 25) / numSegments;

            for (let i = 0; i < numBands; i++) {
                const percent = i / numBands;
                const freq = Math.pow(10, logMin + percent * (logMax - logMin));
                
                const sampleIndex = Math.floor((freq / (sampleRate / 2)) * bufferLength);
                const value = dataArray[Math.min(sampleIndex, bufferLength - 1)];
                const activeSegments = Math.floor((value / 255) * numSegments);
                const xPos = 40 + (i * bandWidth);

                for (let j = 0; j < activeSegments; j++) {
                    const yPos = (canvas.height - 20) - (j * segmentHeight) - segmentHeight;
                    
                    if (j > numSegments * 0.8) ctx.fillStyle = '#ff1a1a';
                    else if (j > numSegments * 0.5) ctx.fillStyle = '#ffaa00';
                    else ctx.fillStyle = '#39d7e6';

                    ctx.fillRect(xPos + 1, yPos + 1, bandWidth - 2, segmentHeight - 2);
                }
            }
        } else if (modoEspectroAtivo === 'waterfall') {
            ctxAux.clearRect(0, 0, canvas.width, canvas.height);
            ctxAux.drawImage(canvas, 0, 0);
            
            ctx.fillStyle = '#05070a';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(waterfallCanvasAux, 0, 1.2); 

            const imgData = ctx.createImageData(graphWidth, 1);

            for (let x = 0; x < graphWidth; x++) {
                const percent = x / graphWidth;
                const freq = Math.pow(10, logMin + percent * (logMax - logMin));
                const bin = Math.floor((freq / (sampleRate / 2)) * bufferLength);
                const value = dataArray[Math.min(bin, bufferLength - 1)];

                let r = 0, g = 0, b = 0;
                if (value > 0) {
                    const v = value / 255;
                    r = Math.floor(Math.max(0, Math.min(255, (v * 1.6) * 255)));
                    g = Math.floor(Math.max(0, Math.min(255, (v * v * 1.3) * 255)));
                    b = Math.floor(Math.max(0, Math.min(255, Math.sin(v * Math.PI) * 190)));
                }

                const pixelIdx = x * 4;
                imgData.data[pixelIdx] = r;
                imgData.data[pixelIdx + 1] = g;
                imgData.data[pixelIdx + 2] = b;
                imgData.data[pixelIdx + 3] = value > 10 ? 255 : value * 25;
            }
            ctx.putImageData(imgData, 40, 0);
            drawGrid();
        }
    }
    draw();
}

function totalBarsCalculated(mode) {
    if (mode === 'spectrogram') return 55;
    return 45;
}

let lastMeterUpdate = 0;
function startLufsMeter() {
    function update() {
        const now = performance.now();
        if(now - lastMeterUpdate < 250){
            requestAnimationFrame(update);
            return;
        }
        lastMeterUpdate = now;
        requestAnimationFrame(update);

        const analyser = typeof masterEqState !== 'undefined' ? masterEqState.analyser : null;
        if(!analyser) return;
        const data = new Float32Array(analyser.fftSize);
        analyser.getFloatTimeDomainData(data);

        let sum = 0;
        let peak = 0;
        for(let i=0; i<data.length; i++){
            const sample = data[i];
            sum += sample * sample;
            peak = Math.max(peak, Math.abs(sample));
        }

        const rms = Math.sqrt(sum / data.length);
        const rmsDb = 20 * Math.log10(rms + 0.000001);
        const peakDb = 20 * Math.log10(peak + 0.000001);

        if (!window.lufsSmooth) window.lufsSmooth = -14;
        const lufsApprox = rmsDb - 3;
        window.lufsSmooth = window.lufsSmooth * 0.9 + lufsApprox * 0.1;
        const lufsEl = document.getElementById('lufsValue');

        if (lufsEl) {
            if (window.lufsSmooth <= -13 && window.lufsSmooth >= -15) {
                lufsEl.style.color = '#00ff88';
            } else if (window.lufsSmooth > -10) {
                lufsEl.style.color = '#ff4444';
            } else {
                lufsEl.style.color = '#ffaa00';
            }
            lufsEl.textContent = window.lufsSmooth.toFixed(1);
        }

        const peakEl = document.getElementById('peakValue');
        if (peakEl) peakEl.textContent = peakDb.toFixed(1) + ' dB';
    }
    update();
}