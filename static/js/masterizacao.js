let histogramaChart = null;
        let masterJobId = '';
        let masterOriginalUrl = '';
        let masterActiveMode = 'original';
        const masterPreviewCache = {};
        let arquivoAtual = null;
        let masterCompression = 'media';
        let currentWorkflow = null; // 'mix' ou 'master'
        let masterVoicePosition = 'central';
        let masterNoDrums = false;
        const masterEqFreqs = [31, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000];
        
        // Estados unificados para Web Audio API
        const masterEqState = {
            context: null,
            source: null,
            gainNode: null,
            filters: [],
            analyser: null,
            enabled: true,
        };
        const masterStemState = {
            context: null,
            masterGain: null,
            tracks: [],
            waveformCache: new Map(),
            syncing: false,
            timelineDuration: 0,
        };

        // Função para inicializar um AudioContext e Analyser únicos e compartilhados
        function initSharedAudioContext() {
            if (masterEqState.context) return; // Já inicializado

            const Ctx = window.AudioContext || window.webkitAudioContext;
            const context = new Ctx();
            
            const analyser = context.createAnalyser();
            analyser.fftSize = 2048;
            analyser.smoothingTimeConstant = 0.75;
            analyser.connect(context.destination); // Conecta o analisador à saída final de áudio

            // Armazena o contexto e o analisador em ambos os estados para referência
            masterEqState.context = context;
            masterEqState.analyser = analyser;
            masterStemState.context = context;
        }

        // Função disparada pelos botões iniciais
        window.selecionarWorkflow = function(workflow) {
            currentWorkflow = workflow;
            const selector = document.getElementById('workflowSelector');
            const dropZone = document.getElementById('fileDropZone');
            if (selector) selector.classList.add('fade-out');
            setTimeout(() => {
                if (selector) selector.style.display = 'none';
                if (dropZone) dropZone.style.display = 'flex';
                if (dropZone) dropZone.classList.add('fade-in');
            }, 400);
            setMasterStatus('Aguardando arquivo para ' + (workflow === 'mix' ? 'mixagem' : 'masterização'));
        };
        
        // ==========================================
        // FERRAMENTA DE CORTE E EDIÇÃO DE ÁUDIO
        // ==========================================
        let masterCutMode = false;
        let cutSelection = null;
        const masterCutUndoStack = [];

        function formatarTempoCorte(segundos) {
            if (!Number.isFinite(segundos) || segundos < 0) return '00:00.00';
            const min = Math.floor(segundos / 60);
            const seg = Math.floor(segundos % 60);
            const cent = Math.floor((segundos - Math.floor(segundos)) * 100);
            return `${String(min).padStart(2, '0')}:${String(seg).padStart(2, '0')}.${String(cent).padStart(2, '0')}`;
        }

        function alternarModoCorteStems(btn) {
            masterCutMode = !masterCutMode;
            if (masterCutMode) {
                removerSelecaoCorte();
            }
            document.body.classList.toggle('stem-cut-mode', masterCutMode);
            if (btn) {
                btn.classList.toggle('is-on', masterCutMode);
                btn.setAttribute('aria-pressed', masterCutMode ? 'true' : 'false');
                btn.innerHTML = masterCutMode ? '✂️ Modo Corte: ON' : '✂️ Modo Corte: OFF';
            }
            setMasterStatus(masterCutMode
                ? 'Modo Corte: arraste em uma waveform e escolha cortar uma stem ou todas.'
                : 'Modo Corte desativado. Clique na waveform volta a buscar tempo.');
        }

        function atualizarBotaoDesfazerCorte(){
            const btn = document.getElementById('stemUndoCutBtn');
            if (!btn) return;
            const podeDesfazer = masterCutUndoStack.length > 0;
            btn.disabled = !podeDesfazer;
            btn.title = podeDesfazer ? 'Desfazer último corte' : 'Nenhum corte para desfazer';
        }

        function criarSnapshotCorte(track){
            return {
                track,
                url: track?.row?.dataset.src || track?.player?.src || '',
                duration: obterDuracaoStem(track),
                trimStart: track.trimStart || 0,
                trimEnd: track.trimEnd !== undefined ? track.trimEnd : 1,
                fadeIn: track.fadeIn || 0,
                fadeOut: track.fadeOut || 0,
                mutes: track.mutes ? JSON.parse(JSON.stringify(track.mutes)) : [],
                volume: track.volume ? track.volume.value : 100,
                panValue: track.panValue || 0,
                fxState: track.fxState ? JSON.parse(JSON.stringify(track.fxState)) : null,
                eqGains: track.eqGains ? [...track.eqGains] : null
            };
        }

        function registrarUndoCorte({ tracks, masterAudio, masterTrackUrls, timelineDuration, label }){
            masterCutUndoStack.push({
                label,
                timelineDuration,
                tracks: tracks.map(criarSnapshotCorte),
                masterAudio: masterAudio ? {
                    url: masterAudio.src || '',
                    currentTime: Number(masterAudio.currentTime || 0),
                    duration: Number(masterAudio.duration || 0),
                } : null,
                masterTrackUrls: masterTrackUrls ? { ...masterTrackUrls } : null,
            });
            if (masterCutUndoStack.length > 30) masterCutUndoStack.shift();
            atualizarBotaoDesfazerCorte();
        }

        function registrarUndoEstadoStems(label) {
            masterCutUndoStack.push({
                label: label || 'Ação visual',
                timelineDuration: masterStemState.timelineDuration,
                tracks: masterStemState.tracks.map(criarSnapshotCorte),
                isStateOnly: true
            });
            if (masterCutUndoStack.length > 30) masterCutUndoStack.shift();
            atualizarBotaoDesfazerCorte();
        }

        async function restaurarSnapshotStem(snapshot){
            const track = snapshot?.track;
            if (!track?.row || !snapshot?.url) return;
            
            if (snapshot.url && snapshot.url !== (track.row.dataset.src || track.player?.src)) {
                const urlAtual = track.row.dataset.src || track.player?.src || '';
                track.row.dataset.src = snapshot.url;
                track.row.dataset.duration = `${snapshot.duration || 0}`;
                track.duration = snapshot.duration || 0;
                track.player.src = snapshot.url;
                track.player.load();
                const canvas = track.row.querySelector('.stem-wave');
                if (canvas) {
                    canvas.dataset.src = snapshot.url;
                    if (urlAtual) masterStemState.waveformCache.delete(urlAtual);
                    try {
                        const picos = await gerarPicosStem(snapshot.url);
                        desenharPicosStem(canvas, picos);
                    } catch(e) {
                        desenharPicosStem(canvas, new Float32Array(200).fill(.08));
                    }
                }
            }

            track.trimStart = snapshot.trimStart;
            track.trimEnd = snapshot.trimEnd;
            track.fadeIn = snapshot.fadeIn;
            track.fadeOut = snapshot.fadeOut;
            track.mutes = snapshot.mutes ? JSON.parse(JSON.stringify(snapshot.mutes)) : [];
            if (track.volume && snapshot.volume !== undefined) {
                track.volume.value = snapshot.volume;
                track.volume.dispatchEvent(new Event('input'));
            }
            if (snapshot.panValue !== undefined) {
                track.panValue = snapshot.panValue;
                const panKnob = track.row.querySelector('.stem-pan-knob');
                const panOut = track.row.querySelector('.stem-pan-value');
                if (panKnob) {
                    panKnob.style.setProperty('--angle', `${(track.panValue / 100) * 135}deg`);
                    panKnob.setAttribute('aria-valuenow', `${Math.round(track.panValue)}`);
                }
                if (panOut) panOut.textContent = formatPanStem(track.panValue);
            }
            if (snapshot.fxState) track.fxState = JSON.parse(JSON.stringify(snapshot.fxState));
            if (snapshot.eqGains) track.eqGains = [...snapshot.eqGains];
            
            aplicarFxStem(track);
            aplicarEqStem(track);
            renderTrimMutes(track);
            atualizarTrimMuteStems();
        }

        async function desfazerUltimoCorteStem(){
            const snapshot = masterCutUndoStack.pop();
            if (!snapshot) {
                atualizarBotaoDesfazerCorte();
                setMasterStatus('Nada para desfazer.');
                return;
            }
            removerSelecaoCorte();
            pausarTodasStems();
            const masterAudio = document.getElementById('masterAudio');
            if (masterAudio) masterAudio.pause();
            setMasterStatus(`Desfazendo: ${snapshot.label || 'Ação'}...`);
            for (const stemSnapshot of snapshot.tracks) {
                await restaurarSnapshotStem(stemSnapshot);
            }
            
            if (!snapshot.isStateOnly) {
                if (snapshot.masterTrackUrls && window.masterTrackUrls) {
                    window.masterTrackUrls = { ...window.masterTrackUrls, ...snapshot.masterTrackUrls };
                }
                if (masterAudio && snapshot.masterAudio?.url) {
                    if (masterAudio.src !== snapshot.masterAudio.url) {
                        masterAudio.src = snapshot.masterAudio.url;
                        masterAudio.load();
                    }
                    try { masterAudio.currentTime = snapshot.masterAudio.currentTime || 0; } catch(e) {}
                }
            }
            masterStemState.timelineDuration = snapshot.timelineDuration || snapshot.masterAudio?.duration || masterStemState.timelineDuration;
            atualizarLargurasClipStems();
            atualizarPlayheadStems();
            atualizarBotaoDesfazerCorte();
            setMasterStatus(`Desfeito: ${snapshot.label || 'Ação'}.`);
        }

        function audioBufferToWav(buffer, onProgress) {
            return new Promise((resolve) => {
                let numOfChan = buffer.numberOfChannels,
                    length = buffer.length * numOfChan * 2 + 44,
                    bufferArray = new ArrayBuffer(length),
                    view = new DataView(bufferArray),
                    channels = [], i, sample,
                    offset = 0,
                    pos = 0;

                function setUint16(data) { view.setUint16(pos, data, true); pos += 2; }
                function setUint32(data) { view.setUint32(pos, data, true); pos += 4; }

                setUint32(0x46464952);
                setUint32(length - 8);
                setUint32(0x45564157);
                setUint32(0x20746d66);
                setUint32(16);
                setUint16(1);
                setUint16(numOfChan);
                setUint32(buffer.sampleRate);
                setUint32(buffer.sampleRate * 2 * numOfChan);
                setUint16(numOfChan * 2);
                setUint16(16);
                setUint32(0x61746164);
                setUint32(length - pos - 4);

                for(i = 0; i < buffer.numberOfChannels; i++) channels.push(buffer.getChannelData(i));

                function processarFatia() {
                    let end = Math.min(offset + (buffer.sampleRate * 2), buffer.length);
                    while(offset < end) {
                        for(i = 0; i < numOfChan; i++) {
                            sample = channels[i][offset];
                            sample = sample < -1 ? -1 : (sample > 1 ? 1 : sample);
                            view.setInt16(pos, sample < 0 ? sample * 32768 : sample * 32767, true);
                            pos += 2;
                        }
                        offset++;
                    }

                    if (onProgress) onProgress(offset / buffer.length);

                    if (offset < buffer.length) {
                        requestAnimationFrame(processarFatia);
                    } else {
                        resolve(new Blob([bufferArray], {type: "audio/wav"}));
                    }
                }

                processarFatia();
            });
        }

        async function loadLamejs() {
            if (window.lamejs) return;
            return new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/lamejs/1.2.1/lame.min.js';
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            });
        }

        async function audioBufferToMp3(buffer, kbps, onProgress) {
            await loadLamejs();
            return new Promise((resolve) => {
                const channels = buffer.numberOfChannels;
                const sampleRate = buffer.sampleRate;
                const mp3encoder = new lamejs.Mp3Encoder(channels, sampleRate, kbps || 320);
                const mp3Data = [];
                const left = buffer.getChannelData(0);
                const right = channels > 1 ? buffer.getChannelData(1) : left;
                const sampleBlockSize = 1152;
                const leftInt = new Int16Array(left.length);
                const rightInt = new Int16Array(right.length);
                for (let i = 0; i < left.length; i++) {
                    leftInt[i] = left[i] < 0 ? left[i] * 32768 : left[i] * 32767;
                    if (channels > 1) rightInt[i] = right[i] < 0 ? right[i] * 32768 : right[i] * 32767;
                }
                let offset = 0;
                function processFatia() {
                    let end = Math.min(offset + sampleBlockSize * 10, left.length);
                    while (offset < end) {
                        const lChunk = leftInt.subarray(offset, offset + sampleBlockSize);
                        const rChunk = rightInt.subarray(offset, offset + sampleBlockSize);
                        let mp3buf = channels === 1 ? mp3encoder.encodeBuffer(lChunk) : mp3encoder.encodeBuffer(lChunk, rChunk);
                        if (mp3buf.length > 0) mp3Data.push(mp3buf);
                        offset += sampleBlockSize;
                    }
                    if (onProgress) onProgress(offset / left.length);
                    if (offset < left.length) requestAnimationFrame(processFatia);
                    else {
                        const mp3buf = mp3encoder.flush();
                        if (mp3buf.length > 0) mp3Data.push(mp3buf);
                        resolve(new Blob(mp3Data, { type: 'audio/mp3' }));
                    }
                }
                processFatia();
            });
        }

        async function processarCorteBuffer(url, startPct, endPct, acao, onProgress) {
            return null;
        }

        function salvarConfiguracoesStems() {
            const config = {
                masterVolume: document.getElementById('masterVolume')?.value,
                tracks: masterStemState.tracks.map(t => ({
                    title: t.row.dataset.title,
                    volume: t.volume.value,
                    panValue: t.panValue,
                    muted: t.row.classList.contains('is-muted'),
                    solo: t.row.classList.contains('is-solo'),
                    trimStart: t.trimStart,
                    trimEnd: t.trimEnd,
                    fadeIn: t.fadeIn,
                    fadeOut: t.fadeOut,
                    mutes: t.mutes,
                    fxState: t.fxState,
                    eqGains: t.eqGains
                }))
            };

            const blob = new Blob([JSON.stringify(config, null, 2)], {type: 'application/json'});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'cifrasflix_mix_setup.json';
            a.click();
            setMasterStatus('Configurações salvas!');
        }

        function carregarConfiguracoesStems() {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'application/json';
            input.onchange = e => {
                const file = e.target.files[0];
                if (!file) return;
                const reader = new FileReader();
                reader.onload = (ev) => {
                    try {
                        const config = JSON.parse(ev.target.result);
                        if (config.masterVolume) {
                            const mv = document.getElementById('masterVolume');
                            if (mv) {
                                mv.value = config.masterVolume;
                                mv.dispatchEvent(new Event('input'));
                            }
                        }
                        
                        config.tracks.forEach(cTrack => {
                            const track = masterStemState.tracks.find(t => t.row.dataset.title === cTrack.title);
                            if (track) {
                                track.volume.value = cTrack.volume;
                                track.volume.dispatchEvent(new Event('input'));
                                
                                track.panValue = cTrack.panValue;
                                const panKnob = track.row.querySelector('.stem-pan-knob');
                                const panOut = track.row.querySelector('.stem-pan-value');
                                if (panKnob) {
                                    panKnob.style.setProperty('--angle', `${(track.panValue / 100) * 135}deg`);
                                    panKnob.setAttribute('aria-valuenow', `${Math.round(track.panValue)}`);
                                }
                                if (panOut) panOut.textContent = formatPanStem(track.panValue);

                                if (cTrack.muted) {
                                    track.row.classList.add('is-muted');
                                    const muteBtn = track.row.querySelector('.stem-mute');
                                    if(muteBtn) muteBtn.classList.add('is-active');
                                } else {
                                    track.row.classList.remove('is-muted');
                                    const muteBtn = track.row.querySelector('.stem-mute');
                                    if(muteBtn) muteBtn.classList.remove('is-active');
                                }

                                if (cTrack.solo) {
                                    track.row.classList.add('is-solo');
                                    const soloBtn = track.row.querySelector('.stem-solo');
                                    if(soloBtn) soloBtn.classList.add('is-active');
                                } else {
                                    track.row.classList.remove('is-solo');
                                    const soloBtn = track.row.querySelector('.stem-solo');
                                    if(soloBtn) soloBtn.classList.remove('is-active');
                                }

                                track.trimStart = cTrack.trimStart || 0;
                                track.trimEnd = cTrack.trimEnd !== undefined ? cTrack.trimEnd : 1;
                                track.fadeIn = cTrack.fadeIn || 0;
                                track.fadeOut = cTrack.fadeOut || 0;
                                track.mutes = cTrack.mutes || [];
                                
                                track.fxState = cTrack.fxState || track.fxState;
                                track.eqGains = cTrack.eqGains || track.eqGains;

                                aplicarFxStem(track);
                                aplicarEqStem(track);
                                renderTrimMutes(track);
                            }
                        });
                        aplicarEstadosMixerStems();
                        setMasterStatus('Configurações carregadas com sucesso!');
                    } catch (err) {
                        alert('Erro ao carregar configurações.');
                    }
                };
                reader.readAsText(file);
            };
            input.click();
        }

        function abrirModalExportacaoStems() {
            let modal = document.getElementById('exportMixModal');
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'exportMixModal';
                modal.style.position = 'fixed'; modal.style.top = '0'; modal.style.left = '0'; modal.style.right = '0'; modal.style.bottom = '0';
                modal.style.background = 'rgba(0,0,0,0.85)'; modal.style.display = 'flex'; modal.style.alignItems = 'center'; modal.style.justifyContent = 'center'; modal.style.zIndex = '999999';
                modal.innerHTML = `
                    <div style="background:var(--card); padding:24px; border-radius:12px; width:320px; box-shadow:0 10px 25px rgba(0,0,0,0.5);">
                        <h3 style="margin-top:0; margin-bottom:16px;">Exportar Mixagem</h3>
                        <label style="display:block; margin-bottom:12px;">
                            <span style="display:block; margin-bottom:4px; font-size:14px; font-weight:bold;">Formato</span>
                            <select id="exportFormatSel" class="presetBtn" style="width:100%; text-align:left;">
                                <option value="wav">WAV (Alta Qualidade)</option>
                                <option value="mp3">MP3 (Comprimido)</option>
                            </select>
                        </label>
                        <label id="exportMp3QualGroup" style="display:none; margin-bottom:16px;">
                            <span style="display:block; margin-bottom:4px; font-size:14px; font-weight:bold;">Qualidade MP3</span>
                            <select id="exportMp3QualSel" class="presetBtn" style="width:100%; text-align:left;">
                                <option value="320">320 kbps</option>
                                <option value="256">256 kbps</option>
                                <option value="192">192 kbps</option>
                                <option value="128">128 kbps</option>
                            </select>
                        </label>
                        <div style="display:flex; gap:12px; margin-top:24px;">
                            <button id="btnCancelExport" class="presetBtn" style="flex:1;">Cancelar</button>
                            <button id="btnConfirmExport" class="presetBtn" style="flex:1; background:#16a34a; color:white;">Exportar</button>
                        </div>
                    </div>
                `;
                document.body.appendChild(modal);
                document.getElementById('exportFormatSel').addEventListener('change', (e) => {
                    document.getElementById('exportMp3QualGroup').style.display = e.target.value === 'mp3' ? 'block' : 'none';
                });
                document.getElementById('btnCancelExport').onclick = () => modal.style.display = 'none';
                document.getElementById('btnConfirmExport').onclick = () => {
                    modal.style.display = 'none';
                    exportarMixagemStems(document.getElementById('exportFormatSel').value, parseInt(document.getElementById('exportMp3QualSel').value, 10));
                };
            }
            modal.style.display = 'flex';
        }

        async function exportarMixagemStems(format = 'wav', kbps = 320) {
            const btn = document.getElementById('stemExportMixBtn');
            if (!btn) return;

            if (!masterStemState.tracks.length) {
                alert('Nenhuma faixa para exportar.');
                return;
            }

            const duracao = masterStemState.timelineDuration;
            if (duracao <= 0) {
                alert('Duração inválida para exportação.');
                return;
            }

            btn.disabled = true;
            btn.innerHTML = '⏳ Renderizando...';
            setMasterStatus('Preparando renderização offline (isso pode levar um tempo)...');

            try {
                const sampleRate = masterStemState.context.sampleRate || 44100;
                const offlineCtx = new (window.OfflineAudioContext || window.webkitOfflineAudioContext)(2, sampleRate * duracao, sampleRate);

                const masterVolNode = offlineCtx.createGain();
                masterVolNode.gain.value = masterStemState.masterGain.gain.value;
                masterVolNode.connect(offlineCtx.destination);

                const progContainer = document.getElementById('masterProgressContainer');
                const progBar = document.getElementById('masterProgressBar');
                if (progContainer) progContainer.style.display = 'block';
                if (progBar) progBar.style.width = '10%';

                let processed = 0;
                for (const track of masterStemState.tracks) {
                    const srcUrl = track.row.dataset.src || track.player.src;
                    if (!srcUrl) continue;

                    const res = await fetch(srcUrl);
                    const arrayBuf = await res.arrayBuffer();
                    const audioBuffer = await offlineCtx.decodeAudioData(arrayBuf);

                    const sourceNode = offlineCtx.createBufferSource();
                    sourceNode.buffer = audioBuffer;

                    const trimGainNode = offlineCtx.createGain();
                    const gainNode = offlineCtx.createGain();
                    const pannerNode = typeof offlineCtx.createStereoPanner === 'function' ? offlineCtx.createStereoPanner() : null;
                    const fxNodes = criarFxNodesStem(offlineCtx, track.fxState);

                    const eqFilters = masterEqFreqs.map((freq) => {
                        const f = offlineCtx.createBiquadFilter();
                        f.type = 'peaking';
                        f.frequency.value = freq;
                        f.Q.value = 1;
                        f.gain.value = 0;
                        return f;
                    });

                    sourceNode.connect(eqFilters[0]);
                    for (let i = 0; i < eqFilters.length - 1; i++) {
                        eqFilters[i].connect(eqFilters[i + 1]);
                    }
                    eqFilters[eqFilters.length - 1].connect(fxNodes.input);
                    fxNodes.output.connect(pannerNode ? pannerNode : trimGainNode);
                    if (pannerNode) fxNodes.autopanDepth.connect(pannerNode.pan);
                    if (pannerNode) pannerNode.connect(trimGainNode);
                    trimGainNode.connect(gainNode);
                    gainNode.connect(masterVolNode);

                    if (track.eqFilters && track.eqFilters.length === eqFilters.length) {
                        track.eqFilters.forEach((origF, idx) => {
                            eqFilters[idx].gain.value = origF.gain.value;
                        });
                    }

                    gainNode.gain.value = track.gainNode.gain.value;
                    if (pannerNode && track.pannerNode) pannerNode.pan.value = track.pannerNode.pan.value;

                    const stemDur = audioBuffer.duration;
                    const curveLength = Math.max(2, Math.ceil(stemDur * 100));
                    const curve = new Float32Array(curveLength);

                    const startPct = track.trimStart || 0;
                    const endPct = track.trimEnd !== undefined ? track.trimEnd : 1;
                    const fadeInPct = track.fadeIn || 0;
                    const fadeOutPct = track.fadeOut || 0;
                    const mutes = track.mutes || [];

                    for (let i = 0; i < curveLength; i++) {
                        const pct = i / (curveLength - 1);
                        let outsideTrim = pct < startPct || pct > endPct;

                        if (!outsideTrim) {
                            for (let j = 0; j < mutes.length; j++) {
                                if (pct >= mutes[j].startPct && pct <= mutes[j].endPct) {
                                    outsideTrim = true;
                                    break;
                                }
                            }
                        }

                        let targetGain = outsideTrim ? 0 : 1;

                        if (!outsideTrim) {
                            if (fadeInPct > 0 && pct < startPct + fadeInPct) {
                                targetGain = (pct - startPct) / fadeInPct;
                            } else if (fadeOutPct > 0 && pct > endPct - fadeOutPct) {
                                targetGain = (endPct - pct) / fadeOutPct;
                            }

                            for (let j = 0; j < mutes.length; j++) {
                                const m = mutes[j];
                                const mFO = m.fadeOut || 0;
                                const mFI = m.fadeIn || 0;

                                if (mFO > 0 && pct <= m.startPct && pct > m.startPct - mFO) {
                                    const localGain = (m.startPct - pct) / mFO;
                                    targetGain = Math.min(targetGain, localGain);
                                }

                                if (mFI > 0 && pct >= m.endPct && pct < m.endPct + mFI) {
                                    const localGain = (pct - m.endPct) / mFI;
                                    targetGain = Math.min(targetGain, localGain);
                                }
                            }
                        }
                        curve[i] = targetGain;
                    }

                    trimGainNode.gain.setValueCurveAtTime(curve, 0, stemDur);
                    sourceNode.start(0);

                    processed++;
                    if (progBar) progBar.style.width = `${10 + (processed / masterStemState.tracks.length) * 40}%`;
                }

                setMasterStatus('Processando mixagem final (aguarde)...');
                const renderedBuffer = await offlineCtx.startRendering();

                setMasterStatus(`Convertendo áudio para ${format.toUpperCase()}...`);
                let finalBlob;
                if (format === 'mp3') {
                    finalBlob = await audioBufferToMp3(renderedBuffer, kbps, (p) => { if (progBar) progBar.style.width = `${50 + (p * 50)}%`; });
                } else {
                    finalBlob = await audioBufferToWav(renderedBuffer, (p) => { if (progBar) progBar.style.width = `${50 + (p * 50)}%`; });
                }

                const url = URL.createObjectURL(finalBlob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `CifrasFlix_Mix_Master.${format}`;
                document.body.appendChild(a);
                a.click();
                a.remove();

                setMasterStatus(`Exportação ${format.toUpperCase()} concluída com sucesso!`);
                setTimeout(() => { if (progContainer) progContainer.style.display = 'none'; }, 1000);
            } catch (err) {
                console.error(err);
                setMasterStatus('Erro ao exportar: ' + err.message);
                alert('Erro ao exportar: ' + err.message);
                const progContainer = document.getElementById('masterProgressContainer');
                if (progContainer) progContainer.style.display = 'none';
            } finally {
                btn.disabled = false;
                btn.innerHTML = '⬇️ Exportar Mix';
            }
        }

        function abrirModalExportacaoSingleStem(track) {
            let modal = document.getElementById('exportSingleStemModal');
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'exportSingleStemModal';
                modal.style.position = 'fixed'; modal.style.top = '0'; modal.style.left = '0'; modal.style.right = '0'; modal.style.bottom = '0';
                modal.style.background = 'rgba(0,0,0,0.85)'; modal.style.display = 'flex'; modal.style.alignItems = 'center'; modal.style.justifyContent = 'center'; modal.style.zIndex = '999999';
                modal.innerHTML = `
                    <div style="background:var(--card); padding:24px; border-radius:12px; width:320px; box-shadow:0 10px 25px rgba(0,0,0,0.5);">
                        <h3 id="exportSingleTitle" style="margin-top:0; margin-bottom:16px;">Exportar Faixa</h3>
                        <label style="display:block; margin-bottom:12px;">
                            <span style="display:block; margin-bottom:4px; font-size:14px; font-weight:bold;">Formato</span>
                            <select id="exportSingleFormatSel" class="presetBtn" style="width:100%; text-align:left;">
                                <option value="wav">WAV (Alta Qualidade)</option>
                                <option value="mp3">MP3 (Comprimido)</option>
                            </select>
                        </label>
                        <label id="exportSingleMp3QualGroup" style="display:none; margin-bottom:16px;">
                            <span style="display:block; margin-bottom:4px; font-size:14px; font-weight:bold;">Qualidade MP3</span>
                            <select id="exportSingleMp3QualSel" class="presetBtn" style="width:100%; text-align:left;">
                                <option value="320">320 kbps</option>
                                <option value="256">256 kbps</option>
                                <option value="192">192 kbps</option>
                                <option value="128">128 kbps</option>
                            </select>
                        </label>
                        <div style="display:flex; gap:12px; margin-top:24px;">
                            <button id="btnCancelSingleExport" class="presetBtn" style="flex:1;">Cancelar</button>
                            <button id="btnConfirmSingleExport" class="presetBtn" style="flex:1; background:#16a34a; color:white;">Exportar</button>
                        </div>
                    </div>
                `;
                document.body.appendChild(modal);
                document.getElementById('exportSingleFormatSel').addEventListener('change', (e) => {
                    document.getElementById('exportSingleMp3QualGroup').style.display = e.target.value === 'mp3' ? 'block' : 'none';
                });
                document.getElementById('btnCancelSingleExport').onclick = () => modal.style.display = 'none';
            }
            
            const titleEl = document.getElementById('exportSingleTitle');
            if (titleEl) {
                titleEl.textContent = `Exportar: ${track.row.dataset.title}`;
            }

            document.getElementById('btnConfirmSingleExport').onclick = () => {
                modal.style.display = 'none';
                const format = document.getElementById('exportSingleFormatSel').value;
                const kbps = parseInt(document.getElementById('exportSingleMp3QualSel').value, 10);
                exportarSingleStem(track, format, kbps);
            };

            modal.style.display = 'flex';
        }

        async function exportarSingleStem(track, format = 'wav', kbps = 320) {
            if (!track) return;
            const srcUrl = track.row.dataset.src || track.player.src;
            if (!srcUrl) {
                alert('URL da faixa inválida.');
                return;
            }

            const title = track.row.dataset.title || 'stem';
            
            setMasterStatus(`Renderizando stem: ${title}...`);
            
            const progContainer = document.getElementById('masterProgressContainer');
            const progBar = document.getElementById('masterProgressBar');
            if (progContainer) progContainer.style.display = 'block';
            if (progBar) progBar.style.width = '10%';

            try {
                const res = await fetch(srcUrl);
                const arrayBuf = await res.arrayBuffer();
                
                const sampleRate = masterStemState.context.sampleRate || 44100;
                
                const tempCtx = new (window.AudioContext || window.webkitAudioContext)();
                const audioBuffer = await tempCtx.decodeAudioData(arrayBuf);
                tempCtx.close().catch(() => {});
                
                const stemDur = audioBuffer.duration;
                if (stemDur <= 0) {
                    alert('Duração inválida para renderização.');
                    return;
                }

                const offlineCtx = new (window.OfflineAudioContext || window.webkitOfflineAudioContext)(2, sampleRate * stemDur, sampleRate);

                const masterVolNode = offlineCtx.createGain();
                masterVolNode.gain.value = masterStemState.masterGain ? masterStemState.masterGain.gain.value : 1;
                masterVolNode.connect(offlineCtx.destination);

                const sourceNode = offlineCtx.createBufferSource();
                sourceNode.buffer = audioBuffer;

                const trimGainNode = offlineCtx.createGain();
                const gainNode = offlineCtx.createGain();
                const pannerNode = typeof offlineCtx.createStereoPanner === 'function' ? offlineCtx.createStereoPanner() : null;
                const fxNodes = criarFxNodesStem(offlineCtx, track.fxState);

                const eqFilters = masterEqFreqs.map((freq) => {
                    const f = offlineCtx.createBiquadFilter();
                    f.type = 'peaking';
                    f.frequency.value = freq;
                    f.Q.value = 1;
                    f.gain.value = 0;
                    return f;
                });

                sourceNode.connect(eqFilters[0]);
                for (let i = 0; i < eqFilters.length - 1; i++) {
                    eqFilters[i].connect(eqFilters[i + 1]);
                }
                eqFilters[eqFilters.length - 1].connect(fxNodes.input);
                fxNodes.output.connect(pannerNode ? pannerNode : trimGainNode);
                if (pannerNode) fxNodes.autopanDepth.connect(pannerNode.pan);
                if (pannerNode) pannerNode.connect(trimGainNode);
                trimGainNode.connect(gainNode);
                gainNode.connect(masterVolNode);

                if (track.eqFilters && track.eqFilters.length === eqFilters.length) {
                    track.eqFilters.forEach((origF, idx) => {
                        eqFilters[idx].gain.value = origF.gain.value;
                    });
                } else if (track.eqGains && track.eqGains.length === eqFilters.length) {
                    track.eqGains.forEach((gainVal, idx) => {
                        eqFilters[idx].gain.value = gainVal;
                    });
                }

                gainNode.gain.value = track.gainNode ? track.gainNode.gain.value : (Number(track.volume?.value || 100) / 100);
                if (pannerNode) {
                    if (track.pannerNode) {
                        pannerNode.pan.value = track.pannerNode.pan.value;
                    } else if (track.panValue !== undefined) {
                        pannerNode.pan.value = clampStemPan(track.panValue) / 100;
                    }
                }

                const curveLength = Math.max(2, Math.ceil(stemDur * 100));
                const curve = new Float32Array(curveLength);

                const startPct = track.trimStart || 0;
                const endPct = track.trimEnd !== undefined ? track.trimEnd : 1;
                const fadeInPct = track.fadeIn || 0;
                const fadeOutPct = track.fadeOut || 0;
                const mutes = track.mutes || [];

                for (let i = 0; i < curveLength; i++) {
                    const pct = i / (curveLength - 1);
                    let outsideTrim = pct < startPct || pct > endPct;

                    if (!outsideTrim) {
                        for (let j = 0; j < mutes.length; j++) {
                            if (pct >= mutes[j].startPct && pct <= mutes[j].endPct) {
                                outsideTrim = true;
                                break;
                            }
                        }
                    }

                    let targetGain = outsideTrim ? 0 : 1;

                    if (!outsideTrim) {
                        if (fadeInPct > 0 && pct < startPct + fadeInPct) {
                            targetGain = (pct - startPct) / fadeInPct;
                        } else if (fadeOutPct > 0 && pct > endPct - fadeOutPct) {
                            targetGain = (endPct - pct) / fadeOutPct;
                        }

                        for (let j = 0; j < mutes.length; j++) {
                            const m = mutes[j];
                            const mFO = m.fadeOut || 0;
                            const mFI = m.fadeIn || 0;

                            if (mFO > 0 && pct <= m.startPct && pct > m.startPct - mFO) {
                                const localGain = (m.startPct - pct) / mFO;
                                targetGain = Math.min(targetGain, localGain);
                            }

                            if (mFI > 0 && pct >= m.endPct && pct < m.endPct + mFI) {
                                const localGain = (pct - m.endPct) / mFI;
                                targetGain = Math.min(targetGain, localGain);
                            }
                        }
                    }
                    curve[i] = targetGain;
                }

                trimGainNode.gain.setValueCurveAtTime(curve, 0, stemDur);
                sourceNode.start(0);

                if (progBar) progBar.style.width = '30%';

                setMasterStatus('Processando renderização final da stem...');
                const renderedBuffer = await offlineCtx.startRendering();

                if (progBar) progBar.style.width = '60%';

                setMasterStatus(`Convertendo stem para ${format.toUpperCase()}...`);
                let finalBlob;
                if (format === 'mp3') {
                    finalBlob = await audioBufferToMp3(renderedBuffer, kbps, (p) => { 
                        if (progBar) progBar.style.width = `${60 + (p * 40)}%`; 
                    });
                } else {
                    finalBlob = await audioBufferToWav(renderedBuffer, (p) => { 
                        if (progBar) progBar.style.width = `${60 + (p * 40)}%`; 
                    });
                }

                const url = URL.createObjectURL(finalBlob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${title}.${format}`;
                document.body.appendChild(a);
                a.click();
                a.remove();

                setMasterStatus(`Download de "${title}" em ${format.toUpperCase()} concluído!`);
                setTimeout(() => { 
                    if (progContainer) progContainer.style.display = 'none'; 
                }, 1000);
            } catch (err) {
                console.error(err);
                setMasterStatus('Erro ao exportar stem: ' + err.message);
                alert('Erro ao exportar stem: ' + err.message);
                if (progContainer) progContainer.style.display = 'none';
            }
        }

        function mostrarMenuCorte(x, y) {
            let menu = document.getElementById('cutContextMenu');
            if (!menu) {
                menu = document.createElement('div');
                menu.id = 'cutContextMenu';
                menu.style.position = 'fixed';
                menu.style.background = 'var(--card)';
                menu.style.border = '1px solid var(--border)';
                menu.style.padding = '12px';
                menu.style.borderRadius = '8px';
                menu.style.zIndex = '100000';
                menu.style.boxShadow = '0 10px 25px rgba(0,0,0,0.5)';
                document.body.appendChild(menu);
            }
            const duracao = Number(cutSelection?.track?.player?.duration || 0);
            const inicio = duracao ? formatarTempoCorte(cutSelection.startPct * duracao) : `${Math.round(cutSelection.startPct * 100)}%`;
            const fim = duracao ? formatarTempoCorte(cutSelection.endPct * duracao) : `${Math.round(cutSelection.endPct * 100)}%`;
            
            menu.innerHTML = `
                <div style="font-weight:bold; margin-bottom:4px; color:var(--text);">Ação de Corte</div>
                <div style="margin-bottom:10px; color:var(--muted); font-size:12px;">Trecho: ${inicio} - ${fim}</div>
                <button id="btnCutSilence" class="presetBtn" style="width:100%; margin-bottom:6px; display:block;">Silenciar Seleção (Mute)</button>
                <button id="btnCutRemove" class="presetBtn" style="width:100%; margin-bottom:6px; display:block;">Deletar (Remover Trecho)</button>
                <button id="btnCutCrop" class="presetBtn" style="width:100%; margin-bottom:12px; display:block;">Crop (Manter Só Seleção)</button>
                <label style="display:flex; align-items:center; color:var(--muted); font-size:13px; cursor:pointer;">
                    <input type="checkbox" id="chkCutAll" style="margin-right:8px;">
                    Aplicar a todas as faixas
                </label>
            `;
            
            const menuWidth = 260;
            let finalX = x;
            if (x + menuWidth > window.innerWidth) finalX = window.innerWidth - menuWidth - 20;
            
            menu.style.left = finalX + 'px';
            menu.style.top = y + 'px';
            menu.style.display = 'block';
            
            const fechar = () => { menu.style.display = 'none'; };
            
            document.getElementById('btnCutSilence').onclick = () => { fechar(); executarCorte('silence'); };
            document.getElementById('btnCutRemove').onclick = () => { fechar(); executarCorte('remove'); };
            document.getElementById('btnCutCrop').onclick = () => { fechar(); executarCorte('crop'); };
            
            setTimeout(() => {
                const outsideClick = (e) => {
                    if (!menu.contains(e.target)) {
                        fechar();
                        document.removeEventListener('click', outsideClick);
                    }
                };
                document.addEventListener('click', outsideClick);
            }, 10);
        }

        function removerSelecaoCorte() {
            if (cutSelection && cutSelection.el) {
                cutSelection.el.remove();
            }
            cutSelection = null;
            const menu = document.getElementById('cutContextMenu');
            if (menu) menu.style.display = 'none';
        }

        async function executarCorte(acao) {
            if (!cutSelection) return;
            
            const aplicarTudo = document.getElementById('chkCutAll')?.checked;
            const sStart = cutSelection.startPct;
            const sEnd = cutSelection.endPct;
            const trackAlvo = cutSelection.track;
            
            removerSelecaoCorte();
            registrarUndoEstadoStems(
                acao === 'remove' ? 'Deletar Trecho' : 
                acao === 'crop' ? 'Crop' : 'Silenciar Seleção'
            );

            if (acao === 'silence' || acao === 'remove') {
                const addCut = (trk) => {
                    if (!trk.mutes) trk.mutes = [];
                    trk.mutes.push({
                        id: Math.random().toString(36).substr(2, 9),
                        startPct: sStart,
                        endPct: sEnd,
                        type: acao,
                        fadeOut: 0,
                        fadeIn: 0
                    });
                    renderTrimMutes(trk);
                };
                
                if (aplicarTudo) masterStemState.tracks.forEach(addCut);
                else addCut(trackAlvo);
                
                setMasterStatus('Corte aplicado (arraste as bordas do buraco para ajustar, e as bolinhas para fade).');
            } else if (acao === 'crop') {
                const applyCrop = (trk) => {
                    trk.trimStart = sStart;
                    trk.trimEnd = sEnd;
                    renderTrimMutes(trk);
                };
                
                if (aplicarTudo) masterStemState.tracks.forEach(applyCrop);
                else applyCrop(trackAlvo);
                
                setMasterStatus('Crop aplicado (você pode esticar as bordas da faixa novamente se precisar).');
            }
        }

        async function separarStems(){
            const overlay = document.getElementById('stemsLoadingOverlay');
            if (overlay) {
                overlay.style.display = 'none';
            }

            const progContainer =
                document.getElementById('masterProgressContainer');

            const progBar =
                document.getElementById('masterProgressBar');

            if(progContainer && progBar){
                progContainer.style.display = 'block';
                progBar.style.width = '0%';
            }
            if (!arquivoAtual) {
                alert("Selecione um áudio");
                return;
            }
            const fd = new FormData();
            fd.append("arquivo", arquivoAtual);

            setMasterStatus('Iniciando separação de stems...');

            const r = await fetch(
                "/api/separar-stems",
                {
                    method:"POST",
                    body:fd
                }
            );
            const data = await r.json();

            await acompanharStems(data.job_id);
        }
        async function acompanharStems(jobId){
            const timer = setInterval(
                async()=>{
                    const progContainer =
                        document.getElementById('masterProgressContainer');

                    const progBar =
                        document.getElementById('masterProgressBar');

                    const r = await fetch(
                        `/api/separar-stems/${jobId}`
                    );

                    const data = await r.json();
                    const prog = data.progresso || 0;

                    if (progBar) progBar.style.width = prog + '%';
                    
                    setMasterStatus(`Separando stems com IA... ${Math.round(prog)}%`);

                    if(
                        data.status === "completed"
                    ) {
                        const overlay = document.getElementById('stemsLoadingOverlay');
                        if (overlay) overlay.style.display = 'none';

                        if (progBar) {
                            progBar.style.width = '100%';
                        }
                            setTimeout(()=>{

                                if(progContainer){

                                    progContainer.style.display = 'none';

                                }

                            },800);
                        clearInterval(timer);

                        await renderizarStems(data.resultado);
                    }

                    if (data.status === "failed") {

                        clearInterval(timer);

                        alert(data.erro);
                    }

                },
                2000
            );
        }
        function normalizarNomeStem(faixa){
            const texto = `${faixa?.titulo || ''} ${faixa?.nome || ''}`.toLowerCase();
            if (texto.includes('vocal')) return 'Vocais';
            if (texto.includes('drum') || texto.includes('bateria')) return 'Bateria';
            if (texto.includes('bass') || texto.includes('baixo')) return 'Baixo';
            if (texto.includes('other') || texto.includes('outro')) return 'Outros';
            return faixa?.titulo || faixa?.nome || 'Stem';
        }

        function formatPanStem(valor){
            const pan = Math.round(Number(valor) || 0);
            if (pan === 0) return 'C';
            return pan < 0 ? `L${Math.abs(pan)}` : `R${pan}`;
        }

        function clampStemPan(valor){
            return Math.max(-100, Math.min(100, Number(valor) || 0));
        }

        function clampStemValue(valor, min, max){
            return Math.max(min, Math.min(max, Number(valor) || 0));
        }

        function criarEstadoFxStem(){
            return {
                activeTab: 'eq',
                eq: { inserted: true, enabled: true },
                compressor: { inserted: false, enabled: false, threshold: -24, ratio: 3, attack: 0.01, release: 0.25 },
                chorus: { inserted: false, enabled: false, mix: 25, rate: 1.2, depth: 0.012 },
                delay: { inserted: false, enabled: false, mix: 20, time: 0.28, feedback: 35 },
                reverb: { inserted: false, enabled: false, mix: 18, decay: 1.8 },
                gate: { inserted: false, enabled: false, threshold: -45, reduction: 90, attack: 0.015, release: 0.16 },
                saturation: { inserted: false, enabled: false, drive: 18, mix: 35 },
                limiter: { inserted: false, enabled: false, threshold: -3, release: 0.08 },
                deesser: { inserted: false, enabled: false, frequency: 6500, amount: 6 },
                filter: { inserted: false, enabled: false, highpass: 30, lowpass: 18000 },
                tremolo: { inserted: false, enabled: false, rate: 4, depth: 35 },
                autopan: { inserted: false, enabled: false, rate: 0.6, depth: 55 },
            };
        }

        function aplicarEqStem(track){
            if (!track?.eqFilters) return;
            const eqOn = track.fxState?.eq?.enabled !== false;
            track.eqFilters.forEach((filter, idx) => {
                filter.gain.value = eqOn ? (track.eqGains[idx] || 0) : 0;
            });
        }

        function criarCurvaSaturacaoStem(drive = 0){
            const amount = clampStemValue(drive, 0, 100);
            const samples = 44100;
            const curve = new Float32Array(samples);
            const k = amount * 8;
            for (let i = 0; i < samples; i += 1) {
                const x = (i * 2 / samples) - 1;
                curve[i] = ((1 + k) * x) / (1 + k * Math.abs(x));
            }
            return curve;
        }

        function criarImpulseReverbStem(ctx, seconds = 1.8){
            const length = Math.max(1, Math.floor(ctx.sampleRate * seconds));
            const impulse = ctx.createBuffer(2, length, ctx.sampleRate);
            for (let channel = 0; channel < 2; channel += 1) {
                const data = impulse.getChannelData(channel);
                for (let i = 0; i < length; i += 1) {
                    const fade = Math.pow(1 - (i / length), 2.4);
                    data[i] = (Math.random() * 2 - 1) * fade;
                }
            }
            return impulse;
        }

        function criarFxNodesStem(ctx, state){
            const input = ctx.createGain();
            const output = ctx.createGain();
            const highpass = ctx.createBiquadFilter();
            const lowpass = ctx.createBiquadFilter();
            const deesser = ctx.createBiquadFilter();
            const gateNode = ctx.createScriptProcessor(1024, 2, 2);
            const saturationInput = ctx.createGain();
            const saturationDry = ctx.createGain();
            const saturationShaper = ctx.createWaveShaper();
            const saturationWet = ctx.createGain();
            const saturationOutput = ctx.createGain();
            const compressor = ctx.createDynamicsCompressor();
            const limiter = ctx.createDynamicsCompressor();
            const tremoloGain = ctx.createGain();
            const tremoloLfo = ctx.createOscillator();
            const tremoloDepth = ctx.createGain();
            const chorusInput = ctx.createGain();
            const chorusDry = ctx.createGain();
            const chorusDelay = ctx.createDelay(0.05);
            const chorusWet = ctx.createGain();
            const chorusOutput = ctx.createGain();
            const chorusLfo = ctx.createOscillator();
            const chorusDepth = ctx.createGain();
            const autopanLfo = ctx.createOscillator();
            const autopanDepth = ctx.createGain();
            const delaySend = ctx.createGain();
            const delayNode = ctx.createDelay(1.5);
            const delayFeedback = ctx.createGain();
            const delayReturn = ctx.createGain();
            const reverbSend = ctx.createGain();
            const reverbNode = ctx.createConvolver();
            const reverbReturn = ctx.createGain();

            highpass.type = 'highpass';
            lowpass.type = 'lowpass';
            deesser.type = 'highshelf';
            saturationShaper.oversample = '4x';

            gateNode._stemGateGain = 1;
            gateNode.onaudioprocess = (event) => {
                const gate = state.gate || {};
                const inputBuffer = event.inputBuffer;
                const outputBuffer = event.outputBuffer;
                const threshold = Math.pow(10, (gate.threshold || -45) / 20);
                const floor = 1 - (clampStemValue(gate.reduction, 0, 100) / 100);
                const attack = Math.max(0.001, gate.attack || 0.015);
                const release = Math.max(0.01, gate.release || 0.16);
                const attackCoef = Math.exp(-1 / (ctx.sampleRate * attack));
                const releaseCoef = Math.exp(-1 / (ctx.sampleRate * release));
                let gain = gateNode._stemGateGain || 1;
                for (let channel = 0; channel < outputBuffer.numberOfChannels; channel += 1) {
                    const source = inputBuffer.getChannelData(Math.min(channel, inputBuffer.numberOfChannels - 1));
                    const target = outputBuffer.getChannelData(channel);
                    for (let i = 0; i < target.length; i += 1) {
                        if (!gate.enabled) {
                            target[i] = source[i];
                            continue;
                        }
                        const wanted = Math.abs(source[i]) < threshold ? floor : 1;
                        const coef = wanted > gain ? attackCoef : releaseCoef;
                        gain = wanted + coef * (gain - wanted);
                        target[i] = source[i] * gain;
                    }
                }
                gateNode._stemGateGain = gain;
            };

            input.connect(highpass);
            highpass.connect(lowpass);
            lowpass.connect(deesser);
            deesser.connect(gateNode);
            gateNode.connect(saturationInput);
            saturationInput.connect(saturationDry);
            saturationInput.connect(saturationShaper);
            saturationDry.connect(saturationOutput);
            saturationShaper.connect(saturationWet);
            saturationWet.connect(saturationOutput);
            saturationOutput.connect(compressor);
            compressor.connect(limiter);
            limiter.connect(tremoloGain);
            tremoloLfo.connect(tremoloDepth);
            tremoloDepth.connect(tremoloGain.gain);
            tremoloGain.connect(chorusInput);
            chorusInput.connect(chorusDry);
            chorusInput.connect(chorusDelay);
            chorusDry.connect(chorusOutput);
            chorusDelay.connect(chorusWet);
            chorusWet.connect(chorusOutput);
            chorusLfo.connect(chorusDepth);
            chorusDepth.connect(chorusDelay.delayTime);
            autopanLfo.connect(autopanDepth);
            chorusOutput.connect(output);
            chorusOutput.connect(delaySend);
            delaySend.connect(delayNode);
            delayNode.connect(delayFeedback);
            delayFeedback.connect(delayNode);
            delayNode.connect(delayReturn);
            delayReturn.connect(output);
            chorusOutput.connect(reverbSend);
            reverbSend.connect(reverbNode);
            reverbNode.connect(reverbReturn);
            reverbReturn.connect(output);

            chorusLfo.start();
            tremoloLfo.start();
            autopanLfo.start();

            const nodes = {
                input,
                output,
                highpass,
                lowpass,
                deesser,
                gateNode,
                saturationInput,
                saturationDry,
                saturationShaper,
                saturationWet,
                saturationOutput,
                compressor,
                limiter,
                tremoloGain,
                tremoloLfo,
                tremoloDepth,
                chorusInput,
                chorusDry,
                chorusDelay,
                chorusWet,
                chorusOutput,
                chorusLfo,
                chorusDepth,
                autopanLfo,
                autopanDepth,
                delaySend,
                delayNode,
                delayFeedback,
                delayReturn,
                reverbSend,
                reverbNode,
                reverbReturn,
            };
            aplicarFxStem({ fxNodes: nodes, fxState: state });
            return nodes;
        }

        function aplicarFxStem(track){
            const fx = track.fxNodes;
            const state = track.fxState;
            if (!fx || !state) return;

            const compOn = !!state.compressor.enabled;
            fx.compressor.threshold.value = compOn ? state.compressor.threshold : 0;
            fx.compressor.ratio.value = compOn ? state.compressor.ratio : 1;
            fx.compressor.attack.value = compOn ? state.compressor.attack : 0.003;
            fx.compressor.release.value = compOn ? state.compressor.release : 0.25;
            fx.compressor.knee.value = compOn ? 18 : 0;

            const gateOn = !!state.gate.enabled;
            fx.gateNode._stemGateGain = gateOn ? (fx.gateNode._stemGateGain || 1) : 1;

            const filterOn = !!state.filter.enabled;
            fx.highpass.frequency.value = filterOn ? clampStemValue(state.filter.highpass, 20, 1000) : 20;
            fx.highpass.Q.value = 0.707;
            fx.lowpass.frequency.value = filterOn ? clampStemValue(state.filter.lowpass, 3000, 20000) : 20000;
            fx.lowpass.Q.value = 0.707;

            const deesserOn = !!state.deesser.enabled;
            fx.deesser.frequency.value = clampStemValue(state.deesser.frequency, 3500, 12000);
            fx.deesser.gain.value = deesserOn ? -clampStemValue(state.deesser.amount, 0, 18) : 0;

            const satOn = !!state.saturation.enabled;
            const satMix = satOn ? clampStemValue(state.saturation.mix, 0, 100) / 100 : 0;
            fx.saturationDry.gain.value = 1 - satMix;
            fx.saturationWet.gain.value = satMix;
            fx.saturationShaper.curve = criarCurvaSaturacaoStem(satOn ? state.saturation.drive : 0);

            const limiterOn = !!state.limiter.enabled;
            fx.limiter.threshold.value = limiterOn ? state.limiter.threshold : 0;
            fx.limiter.knee.value = limiterOn ? 0 : 30;
            fx.limiter.ratio.value = limiterOn ? 20 : 1;
            fx.limiter.attack.value = 0.001;
            fx.limiter.release.value = limiterOn ? state.limiter.release : 0.25;

            const tremoloOn = !!state.tremolo.enabled;
            const tremDepth = tremoloOn ? clampStemValue(state.tremolo.depth, 0, 100) / 200 : 0;
            fx.tremoloGain.gain.value = 1 - tremDepth;
            fx.tremoloLfo.frequency.value = clampStemValue(state.tremolo.rate, 0.1, 12);
            fx.tremoloDepth.gain.value = tremDepth;

            const chorusOn = !!state.chorus.enabled;
            fx.chorusDry.gain.value = 1;
            fx.chorusWet.gain.value = chorusOn ? clampStemValue(state.chorus.mix, 0, 100) / 100 : 0;
            fx.chorusLfo.frequency.value = clampStemValue(state.chorus.rate, 0.05, 8);
            fx.chorusDepth.gain.value = chorusOn ? clampStemValue(state.chorus.depth, 0.001, 0.03) : 0;
            fx.chorusDelay.delayTime.value = 0.018;

            const delayOn = !!state.delay.enabled;
            fx.delaySend.gain.value = delayOn ? clampStemValue(state.delay.mix, 0, 100) / 100 : 0;
            fx.delayNode.delayTime.value = clampStemValue(state.delay.time, 0.05, 1.2);
            fx.delayFeedback.gain.value = delayOn ? clampStemValue(state.delay.feedback, 0, 85) / 100 : 0;
            fx.delayReturn.gain.value = 0.85;

            const reverbOn = !!state.reverb.enabled;
            fx.reverbSend.gain.value = reverbOn ? clampStemValue(state.reverb.mix, 0, 100) / 100 : 0;
            fx.reverbReturn.gain.value = 0.8;
            const decay = clampStemValue(state.reverb.decay, 0.3, 6);
            if (!fx.reverbNode.buffer || Math.abs((fx.reverbDecay || 0) - decay) > 0.05) {
                fx.reverbNode.buffer = criarImpulseReverbStem(masterStemState.context, decay);
                fx.reverbDecay = decay;
            }

            const autopanOn = !!state.autopan.enabled;
            fx.autopanLfo.frequency.value = clampStemValue(state.autopan.rate, 0.05, 6);
            fx.autopanDepth.gain.value = autopanOn ? clampStemValue(state.autopan.depth, 0, 100) / 100 : 0;
        }

        async function ensureStemAudioContext() {
            initSharedAudioContext(); 
            masterStemState.context = masterEqState.context;

            if (!masterStemState.masterGain) {
                masterStemState.masterGain = masterStemState.context.createGain();
                const volume = Number(document.getElementById('masterVolume')?.value || 100) / 100;
                masterStemState.masterGain.gain.value = volume;

                if (masterEqState.analyser) {
                    masterStemState.masterGain.connect(masterEqState.analyser);
                } else {
                    masterStemState.masterGain.connect(masterStemState.context.destination);
                }
            }

            if (masterStemState.context.state === 'suspended') {
                await masterStemState.context.resume().catch(() => {});
            }
        }

        function destruirMixerStems(){
            pausarTodasStems();
            masterStemState.tracks.forEach((track) => {
                try { track.player.pause(); } catch(e) {}
                try { track.sourceNode.disconnect(); } catch(e) {}
                try { track.trimGainNode?.disconnect(); } catch(e) {}
                try { track.gainNode.disconnect(); } catch(e) {}
                try { track.pannerNode?.disconnect(); } catch(e) {}
                if (track.fxNodes) {
                    Object.values(track.fxNodes).forEach((node) => {
                        try { node.disconnect?.(); } catch(e) {}
                    });
                    try { track.fxNodes.chorusLfo.stop(); } catch(e) {}
                    try { track.fxNodes.tremoloLfo.stop(); } catch(e) {}
                    try { track.fxNodes.autopanLfo.stop(); } catch(e) {}
                }
                if (track.eqFilters) {
                    track.eqFilters.forEach(f => { try { f.disconnect(); } catch(e) {} });
                }
            });
            masterStemState.tracks = [];
            masterStemState.timelineDuration = Number(document.getElementById('masterAudio')?.duration || 0);
            masterCutUndoStack.length = 0;
            atualizarBotaoDesfazerCorte();
        }

        function criarLinhaStem(faixa, index){
            const row = document.createElement('div');
            row.className = `stem-row${index === 0 ? ' active' : ''}`;
            row.dataset.src = faixa.url || '';
            row.dataset.title = normalizarNomeStem(faixa);
            row.dataset.file = faixa.nome || '';
            row.innerHTML = `
                <div class="stem-meta">
                    <div class="stem-name-container" style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
                        <p class="stem-name" style="margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"></p>
                        <button class="stem-download-btn" type="button" title="Baixar esta stem" style="background: transparent; border: none; cursor: pointer; padding: 2px; font-size: 16px; color: var(--accent, #39d7e6); transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.15)'" onmouseout="this.style.transform='scale(1)'">
                            📥
                        </button>
                    </div>
                    <div class="stem-controls">
                        <button class="stem-toggle stem-mute" type="button" title="Mute">M</button>
                        <button class="stem-toggle stem-solo" type="button" title="Solo">S</button>
                        <button class="stem-toggle stem-fx-btn" type="button" title="FX da stem">FX</button>
                        <div class="stem-pan-control">
                            <button class="stem-pan-knob" type="button" title="Pan da stem" aria-label="Pan da stem" aria-valuemin="-100" aria-valuemax="100" aria-valuenow="0"></button>
                            <output class="stem-pan-value">C</output>
                        </div>
                    </div>
                    <div class="stem-mix">
                        <label class="stem-fader">
                            <span>Vol</span>
                            <input class="stem-volume" type="range" min="0" max="100" step="1" value="100" title="Volume da stem">
                            <output class="stem-volume-value">100</output>
                        </label>
                    </div>
                </div>
                <button class="stem-wave-hit" type="button" title="Selecionar stem">
                    <div class="stem-wave-wrap" style="position: relative; overflow: hidden; border-radius: 6px; touch-action: none;">
                        <canvas class="stem-wave"></canvas>
                        <div class="stem-trim-overlay stem-trim-overlay-left"></div>
                        <div class="stem-trim-overlay stem-trim-overlay-right"></div>
                        <div class="stem-fade-overlay stem-fade-overlay-in"></div>
                        <div class="stem-fade-overlay stem-fade-overlay-out"></div>
                        <div class="stem-playhead" style="position: absolute; top: 0; bottom: 0; left: 0%; width: 2px; background: #E50914; box-shadow: 0 0 10px #E50914; pointer-events: none; z-index: 10;"></div>
                        <div class="stem-trim-handle stem-trim-start" data-trim-side="start" title="Encurtar início"></div>
                        <div class="stem-trim-handle stem-trim-end" data-trim-side="end" title="Encurtar final"></div>
                        <div class="stem-fade-handle stem-fade-in" title="Fade In"></div>
                        <div class="stem-fade-handle stem-fade-out" title="Fade Out"></div>
                    </div>
                </button>
            `;
            row.querySelector('.stem-name').textContent = row.dataset.title;
            const canvas = row.querySelector('.stem-wave');
            if (canvas) {
                canvas.dataset.src = faixa.url || '';
                canvas.setAttribute('aria-label', `Waveform de ${row.dataset.title}`);
            }
            return row;
        }

        function desenharPicosStem(canvas, picos){
            const ctx = canvas.getContext('2d');
            if (!ctx) return;

            const dpr = window.devicePixelRatio || 1;
            const largura = Math.max(10, canvas.clientWidth);
            const altura = Math.max(10, canvas.clientHeight);
            canvas.width = Math.floor(largura * dpr);
            canvas.height = Math.floor(altura * dpr);
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            ctx.clearRect(0, 0, largura, altura);

            const centro = altura / 2;
            const escala = centro * .92;
            const passo = largura / Math.max(1, picos.length);
            const grad = ctx.createLinearGradient(0, 0, largura, 0);
            grad.addColorStop(0, '#39d7e6');
            grad.addColorStop(.55, '#7c3aed');
            grad.addColorStop(1, '#a7fbff');
            ctx.fillStyle = grad;

            ctx.beginPath();
            ctx.moveTo(0, centro);
            for (let i = 0; i < picos.length; i += 1) {
                ctx.lineTo(i * passo, centro - (picos[i] * escala));
            }
            for (let i = picos.length - 1; i >= 0; i -= 1) {
                ctx.lineTo(i * passo, centro + (picos[i] * escala));
            }
            ctx.closePath();
            ctx.fill();

            ctx.strokeStyle = 'rgba(255,255,255,.2)';
            ctx.beginPath();
            ctx.moveTo(0, centro);
            ctx.lineTo(largura, centro);
            ctx.stroke();
        }

        async function gerarPicosStem(src, quantidade = 900){
            if (masterStemState.waveformCache.has(src)) {
                return masterStemState.waveformCache.get(src);
            }
            const resposta = await fetch(src, { cache: 'force-cache' });
            if (!resposta.ok) throw new Error('Falha ao carregar waveform');
            const buffer = await resposta.arrayBuffer();
            const Ctx = window.AudioContext || window.webkitAudioContext;
            const ctx = new Ctx();
            const decoded = await ctx.decodeAudioData(buffer);
            const canal = decoded.getChannelData(0);
            const bloco = Math.max(1, Math.floor(canal.length / quantidade));
            const picos = new Float32Array(quantidade);
            for (let i = 0; i < quantidade; i += 1) {
                const ini = i * bloco;
                const fim = Math.min(canal.length, ini + bloco);
                let maximo = 0;
                for (let j = ini; j < fim; j += 1) {
                    const valor = Math.abs(canal[j]);
                    if (valor > maximo) maximo = valor;
                }
                picos[i] = maximo;
            }
            masterStemState.waveformCache.set(src, picos);
            ctx.close?.().catch(() => {});
            return picos;
        }

        async function renderizarWaveformsMaster(){
            const canvases = Array.from(document.querySelectorAll('#masterStemGrid .stem-wave'));
            for (const canvas of canvases) {
                const src = canvas.dataset.src || '';
                try {
                    const picos = await gerarPicosStem(src);
                    desenharPicosStem(canvas, picos);
                } catch(e) {
                    desenharPicosStem(canvas, new Float32Array(200).fill(.08));
                }
            }
        }

        function obterDuracaoStem(track){
            return Number(track?.duration || track?.row?.dataset.duration || track?.player?.duration || 0);
        }

        function atualizarDuracaoTimelineStems(){
            const audio = document.getElementById('masterAudio');
            const duracaoMaster = Number(audio?.duration || 0);
            const maiorStem = masterStemState.tracks.reduce((maior, track) => Math.max(maior, obterDuracaoStem(track)), 0);
            masterStemState.timelineDuration = Math.max(masterStemState.timelineDuration || 0, duracaoMaster, maiorStem);
        }

        function atualizarLarguraClipStem(track){
            if (!track?.row) return;
            const waveHit = track.row.querySelector('.stem-wave-hit');
            if (!waveHit) return;
            const timeline = Number(masterStemState.timelineDuration || 0);
            const duracao = obterDuracaoStem(track);
            const pct = timeline > 0 && duracao > 0 ? Math.max(1, Math.min(100, (duracao / timeline) * 100)) : 100;
            waveHit.style.width = `${pct}%`;
            waveHit.title = pct < 99.5 ? `Clip encurtado: ${formatarTempoCorte(duracao)}` : 'Selecionar stem';
        }

        function atualizarLargurasClipStems(){
            atualizarDuracaoTimelineStems();
            masterStemState.tracks.forEach(atualizarLarguraClipStem);
        }

        function atualizarPlayheadStems(){
            const audio = document.getElementById('masterAudio');
            const playhead = document.getElementById('masterStemPlayhead');
            if (!audio) return;
            const total = Number(audio.duration || masterStemState.timelineDuration || 0);
            const tempo = Number(audio.currentTime || 0);
            const pct = total > 0 ? Math.max(0, Math.min(100, (tempo / total) * 100)) : 0;
            if (playhead) playhead.style.setProperty('--playhead-pct', `${pct}%`);
            
            masterStemState.tracks.forEach((track) => {
                const stemPlayhead = track.row?.querySelector('.stem-playhead');
                if (!stemPlayhead) return;
                const stemTotal = obterDuracaoStem(track);
                const stemPct = stemTotal > 0 ? Math.max(0, Math.min(100, (tempo / stemTotal) * 100)) : pct;
                stemPlayhead.style.left = `${stemPct}%`;
            });
        }

        function atualizarTrimMuteStems() {
            const audio = document.getElementById('masterAudio');
            if (!audio) return;
            const tempo = Number(audio.currentTime || 0);
            
            masterStemState.tracks.forEach((track) => {
                if (!track.trimGainNode) return;
                const stemTotal = obterDuracaoStem(track);
                const pct = stemTotal > 0 ? (tempo / stemTotal) : 0;
                
                const start = track.trimStart || 0;
                const end = track.trimEnd !== undefined ? track.trimEnd : 1;
                let outsideTrim = pct < start || pct > end;
                
                if (!outsideTrim && track.mutes) {
                    for (let i = 0; i < track.mutes.length; i++) {
                        const m = track.mutes[i];
                        if (pct >= m.startPct && pct <= m.endPct) {
                            outsideTrim = true;
                            break;
                        }
                    }
                }
                
                let targetGain = outsideTrim ? 0 : 1;
                let inFade = false;

                if (!outsideTrim) {
                    const fadeInPct = track.fadeIn || 0;
                    const fadeOutPct = track.fadeOut || 0;

                    if (fadeInPct > 0 && pct < start + fadeInPct) {
                        targetGain = (pct - start) / fadeInPct;
                        inFade = true;
                    } else if (fadeOutPct > 0 && pct > end - fadeOutPct) {
                        targetGain = (end - pct) / fadeOutPct;
                        inFade = true;
                    }

                    if (track.mutes) {
                        for (let i = 0; i < track.mutes.length; i++) {
                            const m = track.mutes[i];
                            const mFO = m.fadeOut || 0;
                            const mFI = m.fadeIn || 0;

                            if (mFO > 0 && pct <= m.startPct && pct > m.startPct - mFO) {
                                const localGain = (m.startPct - pct) / mFO;
                                targetGain = Math.min(targetGain, localGain);
                                inFade = true;
                            }

                            if (mFI > 0 && pct >= m.endPct && pct < m.endPct + mFI) {
                                const localGain = (pct - m.endPct) / mFI;
                                targetGain = Math.min(targetGain, localGain);
                                inFade = true;
                            }
                        }
                    }
                }
                
                if (inFade) {
                    track._currentTrimTarget = targetGain;
                    try { track.trimGainNode.gain.setTargetAtTime(targetGain, masterStemState.context.currentTime, 0.015); } catch(e) { track.trimGainNode.gain.value = targetGain; }
                } else if (track._currentTrimTarget !== targetGain) {
                    track._currentTrimTarget = targetGain;
                    try { track.trimGainNode.gain.setTargetAtTime(targetGain, masterStemState.context.currentTime, 0.015); } catch(e) { track.trimGainNode.gain.value = targetGain; }
                }
            });
        }

        function sincronizarStemsComMaster(forcar = false){
            const audio = document.getElementById('masterAudio');
            if (!audio || masterStemState.syncing) return;
            const tempo = Number(audio.currentTime || 0);
            masterStemState.tracks.forEach(({ player }) => {
                try {
                    const duracao = Number(player.duration || 0);
                    const tempoStem = duracao > 0 ? Math.min(tempo, Math.max(0, duracao - 0.001)) : tempo;
                    if (forcar || Math.abs(Number(player.currentTime || 0) - tempoStem) > .08) {
                        player.currentTime = tempoStem;
                    }
                } catch(e) {}
            });
            atualizarPlayheadStems();
            atualizarTrimMuteStems();
        }

        function aplicarEstadosMixerStems(){
            const soloAtivo = masterStemState.tracks.some(({ row }) => row.classList.contains('is-solo'));
            masterStemState.tracks.forEach((track) => {
                const muted = track.row.classList.contains('is-muted');
                const solo = track.row.classList.contains('is-solo');
                const deveTocar = soloAtivo ? solo : !muted;
                const vol = Number(track.volume?.value || 100) / 100;
                const pan = clampStemPan(track.panValue) / 100;
                track.row.classList.toggle('is-dim', soloAtivo && !solo);
                track.gainNode.gain.value = deveTocar ? Math.max(0, Math.min(1, vol)) : 0;
                if (track.pannerNode) track.pannerNode.pan.value = Math.max(-1, Math.min(1, pan));
            });
        }

        function atualizarContadorStems(){
            const badge = document.getElementById('stemsCountBadge');
            if (badge) badge.textContent = `${masterStemState.tracks.length} faixas`;
        }

        function tocarTodasStems(){
            const audio = document.getElementById('masterAudio');
            if (!audio || !masterStemState.tracks.length) return;
            ensureStemAudioContext();
            sincronizarStemsComMaster(true);
            aplicarEstadosMixerStems();
            masterStemState.tracks.forEach(({ player }) => {
                const p = player.play();
                if (p?.catch) p.catch(() => {});
            });
            audio.muted = true;
        }

        function pausarTodasStems(){
            masterStemState.tracks.forEach(({ player }) => {
                try { player.pause(); } catch(e) {}
            });
        }

        function renderTrimMutes(track) {
            const wrap = track.row.querySelector('.stem-wave-wrap');
            if (!wrap) return;
            
            if (!document.getElementById('stem-trim-styles')) {
                const style = document.createElement('style');
                style.id = 'stem-trim-styles';
                style.innerHTML = `
                    .stem-trim-overlay { position: absolute; top: 0; bottom: 0; background: rgba(0, 0, 0, 0.65); pointer-events: none; z-index: 4; }
                    .stem-trim-overlay-left { left: 0; }
                    .stem-trim-overlay-right { right: 0; }
                    .stem-trim-handle {
                        position: absolute; top: 0; bottom: 0; width: 14px;
                        background: rgba(255, 255, 255, 0.2); border-left: 1px solid #fff; border-right: 1px solid #fff;
                        cursor: ew-resize; z-index: 6; transition: background 0.2s;
                    }
                    .stem-trim-handle:hover { background: rgba(255, 255, 255, 0.5); }
                    .stem-trim-start { transform: translateX(-50%); }
                    .stem-trim-end { transform: translateX(-50%); }
                    
                    .stem-fade-handle {
                        position: absolute; top: 2px; width: 12px; height: 12px;
                        background: #a855f7; border-radius: 50%; border: 1px solid #fff;
                        cursor: ew-resize; z-index: 7; opacity: 0.8; transition: transform 0.2s;
                    }
                    .stem-fade-handle:hover { opacity: 1; transform: scale(1.2); }
                    .stem-fade-in { transform: translateX(-50%); }
                    .stem-fade-out { transform: translateX(50%); }
                    
                    .stem-fade-overlay { position: absolute; top: 0; bottom: 0; pointer-events: none; z-index: 5; }
                    .stem-fade-overlay-in { background: linear-gradient(to right, rgba(168, 85, 247, 0.25), transparent); }
                    .stem-fade-overlay-out { background: linear-gradient(to left, rgba(168, 85, 247, 0.25), transparent); }
                    
                    .stem-mute-region {
                        position: absolute; top: 0; bottom: 0;
                        background: rgba(229, 9, 20, 0.35); z-index: 4;
                        border-left: 2px solid #E50914; border-right: 2px solid #E50914;
                    }
                    .stem-remove-region {
                        background: rgba(0, 0, 0, 0.8);
                        border-left: 2px solid #9ca3af; border-right: 2px solid #9ca3af;
                    }
                    .mute-handle {
                        position: absolute; top: 0; bottom: 0; width: 14px;
                        cursor: ew-resize; z-index: 6; background: rgba(255,255,255,0.01);
                    }
                    .mute-handle-left { left: -7px; }
                    .mute-handle-right { right: -7px; }
                    .mute-handle:hover { background: rgba(255,255,255,0.3); }
                    
                    .mute-delete-btn {
                        position: absolute; top: 4px; right: 4px;
                        background: #E50914; color: white; border: none; border-radius: 4px;
                        font-size: 11px; cursor: pointer; z-index: 7; padding: 2px 6px; display: none; font-weight: bold;
                    }
                    .stem-mute-region:hover .mute-delete-btn { display: block; }
                `;
                document.head.appendChild(style);
            }

            let trimStart = wrap.querySelector('.stem-trim-start');
            let trimEnd = wrap.querySelector('.stem-trim-end');
            let overlayLeft = wrap.querySelector('.stem-trim-overlay-left');
            let overlayRight = wrap.querySelector('.stem-trim-overlay-right');
            let fadeInHandle = wrap.querySelector('.stem-fade-in');
            let fadeOutHandle = wrap.querySelector('.stem-fade-out');
            let fadeOverlayIn = wrap.querySelector('.stem-fade-overlay-in');
            let fadeOverlayOut = wrap.querySelector('.stem-fade-overlay-out');

            const startPct = track.trimStart || 0;
            const endPct = track.trimEnd !== undefined ? track.trimEnd : 1;
            const fadeInPct = track.fadeIn || 0;
            const fadeOutPct = track.fadeOut || 0;
            
            if (trimStart && overlayLeft) {
                trimStart.style.left = `${startPct * 100}%`;
                overlayLeft.style.width = `${startPct * 100}%`;
            }
            if (trimEnd && overlayRight) {
                trimEnd.style.left = `${endPct * 100}%`;
                overlayRight.style.width = `${(1 - endPct) * 100}%`;
            }
            
            if (fadeInHandle && fadeOverlayIn) {
                fadeInHandle.style.left = `${(startPct + fadeInPct) * 100}%`;
                fadeOverlayIn.style.left = `${startPct * 100}%`;
                fadeOverlayIn.style.width = `${fadeInPct * 100}%`;
            }
            if (fadeOutHandle && fadeOverlayOut) {
                fadeOutHandle.style.right = `${(1 - (endPct - fadeOutPct)) * 100}%`;
                fadeOverlayOut.style.right = `${(1 - endPct) * 100}%`;
                fadeOverlayOut.style.width = `${fadeOutPct * 100}%`;
            }
            
            wrap.querySelectorAll('.stem-mute-region').forEach(el => el.remove());
            wrap.querySelectorAll('.mute-dynamic').forEach(el => el.remove());

            if (track.mutes) {
                track.mutes.forEach((mute, index) => {
                    mute.fadeOut = mute.fadeOut || 0;
                    mute.fadeIn = mute.fadeIn || 0;

                    const el = document.createElement('div');
                    el.className = mute.type === 'remove' ? 'stem-mute-region stem-remove-region' : 'stem-mute-region';
                    el.style.left = `${mute.startPct * 100}%`;
                    el.style.width = `${(mute.endPct - mute.startPct) * 100}%`;
                    
                    const handleL = document.createElement('div');
                    handleL.className = 'mute-handle mute-handle-left';
                    const handleR = document.createElement('div');
                    handleR.className = 'mute-handle mute-handle-right';
                    
                    const delBtn = document.createElement('button');
                    delBtn.className = 'mute-delete-btn';
                    delBtn.textContent = 'X';
                    delBtn.title = 'Remover corte';
                    delBtn.onclick = (e) => {
                        e.stopPropagation();
                        registrarUndoEstadoStems('Remover corte');
                        track.mutes.splice(index, 1);
                        renderTrimMutes(track);
                    };

                    el.appendChild(handleL);
                    el.appendChild(handleR);
                    el.appendChild(delBtn);
                    wrap.appendChild(el);

                    if (mute.fadeOut > 0) {
                        const fo = document.createElement('div');
                        fo.className = 'stem-fade-overlay stem-fade-overlay-out mute-dynamic';
                        fo.style.right = `${(1 - mute.startPct) * 100}%`;
                        fo.style.width = `${mute.fadeOut * 100}%`;
                        wrap.appendChild(fo);
                    }

                    if (mute.fadeIn > 0) {
                        const fi = document.createElement('div');
                        fi.className = 'stem-fade-overlay stem-fade-overlay-in mute-dynamic';
                        fi.style.left = `${mute.endPct * 100}%`;
                        fi.style.width = `${mute.fadeIn * 100}%`;
                        wrap.appendChild(fi);
                    }

                    const fadeL = document.createElement('div');
                    fadeL.className = 'stem-fade-handle stem-fade-out mute-dynamic';
                    fadeL.style.right = `${(1 - (mute.startPct - mute.fadeOut)) * 100}%`;
                    fadeL.title = 'Fade Out antes do corte';

                    const fadeR = document.createElement('div');
                    fadeR.className = 'stem-fade-handle stem-fade-in mute-dynamic';
                    fadeR.style.left = `${(mute.endPct + mute.fadeIn) * 100}%`;
                    fadeR.title = 'Fade In após o corte';

                    wrap.appendChild(fadeL);
                    wrap.appendChild(fadeR);

                    const setupDrag = (handle, isLeft) => {
                        handle.addEventListener('pointerdown', (e) => {
                            e.preventDefault(); e.stopPropagation();
                            registrarUndoEstadoStems('Ajustar área do corte');
                            const rect = wrap.getBoundingClientRect();
                            let isDragging = true;
                            
                            const onMove = (ev) => {
                                if (!isDragging) return;
                                let pct = (ev.clientX - rect.left) / rect.width;
                                pct = Math.max(0, Math.min(1, pct));
                                
                                if (isLeft) {
                                    mute.startPct = Math.min(pct, mute.endPct - 0.005);
                                    mute.fadeOut = Math.min(mute.fadeOut, mute.startPct);
                                } else {
                                    mute.endPct = Math.max(pct, mute.startPct + 0.005);
                                    mute.fadeIn = Math.min(mute.fadeIn, 1 - mute.endPct);
                                }
                                
                                renderTrimMutes(track);
                            };
                            
                            const onUp = () => {
                                isDragging = false;
                                window.removeEventListener('pointermove', onMove);
                                window.removeEventListener('pointerup', onUp);
                            };
                            
                            window.addEventListener('pointermove', onMove);
                            window.addEventListener('pointerup', onUp);
                        });
                        handle.addEventListener('click', e => { e.stopPropagation(); e.preventDefault(); });
                    };

                    setupDrag(handleL, true);
                    setupDrag(handleR, false);

                    const setupFadeDrag = (handle, isLeft) => {
                        handle.addEventListener('pointerdown', (e) => {
                            e.preventDefault(); e.stopPropagation();
                            registrarUndoEstadoStems('Ajustar fade do corte');
                            const rect = wrap.getBoundingClientRect();
                            let isDragging = true;
                            
                            const onMove = (ev) => {
                                if (!isDragging) return;
                                let pct = (ev.clientX - rect.left) / rect.width;
                                pct = Math.max(0, Math.min(1, pct));
                                
                                if (isLeft) {
                                    mute.fadeOut = Math.max(0, Math.min(mute.startPct - pct, mute.startPct));
                                } else {
                                    mute.fadeIn = Math.max(0, Math.min(pct - mute.endPct, 1 - mute.endPct));
                                }
                                
                                renderTrimMutes(track);
                            };
                            
                            const onUp = () => {
                                isDragging = false;
                                window.removeEventListener('pointermove', onMove);
                                window.removeEventListener('pointerup', onUp);
                            };
                            
                            window.addEventListener('pointermove', onMove);
                            window.addEventListener('pointerup', onUp);
                        });
                        handle.addEventListener('click', e => { e.stopPropagation(); e.preventDefault(); });
                    };

                    setupFadeDrag(fadeL, true);
                    setupFadeDrag(fadeR, false);
                });
            }

            atualizarTrimMuteStems();
        }

        function conectarEventosStem(row, track){
            const mute = row.querySelector('.stem-mute');
            const solo = row.querySelector('.stem-solo');
            const fxBtn = row.querySelector('.stem-fx-btn');
            const waveHit = row.querySelector('.stem-wave-hit');
            const volume = row.querySelector('.stem-volume');
            const volOut = row.querySelector('.stem-volume-value');
            const panKnob = row.querySelector('.stem-pan-knob');
            const panOut = row.querySelector('.stem-pan-value');
            const downloadBtn = row.querySelector('.stem-download-btn');

            if (downloadBtn) {
                downloadBtn.addEventListener('click', (event) => {
                    event.stopPropagation();
                    abrirModalExportacaoSingleStem(track);
                });
            }

            if (mute) {
                mute.addEventListener('click', (event) => {
                    event.stopPropagation();
                    row.classList.toggle('is-muted');
                    mute.classList.toggle('is-active', row.classList.contains('is-muted'));
                    aplicarEstadosMixerStems();
                });
            }
            if (solo) {
                solo.addEventListener('click', (event) => {
                    event.stopPropagation();
                    row.classList.toggle('is-solo');
                    solo.classList.toggle('is-active', row.classList.contains('is-solo'));
                    aplicarEstadosMixerStems();
                });
            }
            if (fxBtn) {
                fxBtn.addEventListener('click', (event) => {
                    event.stopPropagation();
                    abrirModalFxStem(track);
                });
            }
            if (volume) {
                volume.addEventListener('input', () => {
                    if (volOut) volOut.textContent = volume.value;
                    aplicarEstadosMixerStems();
                });
            }
            const atualizarPan = (valor) => {
                track.panValue = clampStemPan(valor);
                if (panKnob) {
                    panKnob.style.setProperty('--angle', `${(track.panValue / 100) * 135}deg`);
                    panKnob.setAttribute('aria-valuenow', `${Math.round(track.panValue)}`);
                }
                if (panOut) panOut.textContent = formatPanStem(track.panValue);
                aplicarEstadosMixerStems();
            };
            if (panKnob) {
                panKnob.addEventListener('wheel', (event) => {
                    event.preventDefault();
                    atualizarPan(track.panValue + (event.deltaY > 0 ? -2 : 2));
                }, { passive: false });
                panKnob.addEventListener('dblclick', (event) => {
                    event.preventDefault();
                    atualizarPan(0);
                });
                panKnob.addEventListener('pointerdown', (event) => {
                    event.preventDefault();
                    const inicial = track.panValue;
                    const y = event.clientY;
                    const mover = (moveEvent) => atualizarPan(inicial + (y - moveEvent.clientY));
                    const finalizar = () => {
                        window.removeEventListener('pointermove', mover);
                        window.removeEventListener('pointerup', finalizar);
                    };
                    window.addEventListener('pointermove', mover);
                    window.addEventListener('pointerup', finalizar);
                });
            }
            if (waveHit) {
                // Adicionando trim handles
                const trimStart = row.querySelector('.stem-trim-start');
                const trimEnd = row.querySelector('.stem-trim-end');
                const overlayLeft = row.querySelector('.stem-trim-overlay-left');
                const overlayRight = row.querySelector('.stem-trim-overlay-right');
                const fadeInHandle = row.querySelector('.stem-fade-in');
                const fadeOutHandle = row.querySelector('.stem-fade-out');
                const wrap = row.querySelector('.stem-wave-wrap');

                const dragHandle = (handle, side) => {
                    if (!handle) return;
                    handle.addEventListener('click', (e) => {
                        e.stopPropagation(); e.preventDefault();
                    });
                    handle.addEventListener('pointerdown', (e) => {
                        e.preventDefault(); e.stopPropagation();
                        registrarUndoEstadoStems('Ajustar corte/fade');

                        const rect = wrap.getBoundingClientRect();
                        let isDragging = true;

                        let tooltip = document.createElement('div');
                        tooltip.style.position = 'fixed';
                        tooltip.style.background = 'rgba(0,0,0,0.85)';
                        tooltip.style.color = '#fff';
                        tooltip.style.padding = '4px 8px';
                        tooltip.style.borderRadius = '6px';
                        tooltip.style.fontSize = '12px';
                        tooltip.style.fontWeight = 'bold';
                        tooltip.style.zIndex = '999999';
                        tooltip.style.pointerEvents = 'none';
                        tooltip.style.transform = 'translate(-50%, -140%)';
                        tooltip.style.boxShadow = '0 2px 8px rgba(0,0,0,0.3)';
                        document.body.appendChild(tooltip);

                        const updateTooltip = (ev, text) => {
                            tooltip.style.left = ev.clientX + 'px';
                            tooltip.style.top = ev.clientY + 'px';
                            tooltip.textContent = text;
                        };

                        const onMove = (ev) => {
                            if (!isDragging) return;
                            let pct = (ev.clientX - rect.left) / rect.width;
                            pct = Math.max(0, Math.min(1, pct));

                            const stemTotal = obterDuracaoStem(track);

                            if (side === 'start') {
                                track.trimStart = Math.min(pct, (track.trimEnd || 1) - 0.005);
                                track.fadeIn = Math.min(track.fadeIn || 0, (track.trimEnd || 1) - track.trimStart - (track.fadeOut || 0));
                                updateTooltip(ev, `Início: ${formatarTempoCorte(track.trimStart * stemTotal)}`);
                            } else if (side === 'end') {
                                track.trimEnd = Math.max(pct, (track.trimStart || 0) + 0.005);
                                track.fadeOut = Math.min(track.fadeOut || 0, track.trimEnd - (track.trimStart || 0) - (track.fadeIn || 0));
                                updateTooltip(ev, `Fim: ${formatarTempoCorte(track.trimEnd * stemTotal)}`);
                            } else if (side === 'fade-in') {
                                const start = track.trimStart || 0;
                                const end = track.trimEnd !== undefined ? track.trimEnd : 1;
                                track.fadeIn = Math.max(0, Math.min(pct - start, end - start - (track.fadeOut || 0)));
                                updateTooltip(ev, `Fade In: ${(track.fadeIn * stemTotal).toFixed(2)}s`);
                            } else if (side === 'fade-out') {
                                const start = track.trimStart || 0;
                                const end = track.trimEnd !== undefined ? track.trimEnd : 1;
                                track.fadeOut = Math.max(0, Math.min(end - pct, end - start - (track.fadeIn || 0)));
                                updateTooltip(ev, `Fade Out: ${(track.fadeOut * stemTotal).toFixed(2)}s`);
                            }
                            renderTrimMutes(track);
                        };

                        const onUp = () => {
                            isDragging = false;
                            if (tooltip) tooltip.remove();
                            window.removeEventListener('pointermove', onMove);
                            window.removeEventListener('pointerup', onUp);
                        };

                        window.addEventListener('pointermove', onMove);
                        window.addEventListener('pointerup', onUp);
                        onMove(e);
                    });
                };

                dragHandle(trimStart, 'start');
                dragHandle(trimEnd, 'end');
                dragHandle(fadeInHandle, 'fade-in');
                dragHandle(fadeOutHandle, 'fade-out');
                renderTrimMutes(track);

                waveHit.addEventListener('click', (event) => {
                    if (masterCutMode) return; // Ignora o clique de buscar tempo se estiver recortando
                    const audio = document.getElementById('masterAudio');
                    if (!audio || !wrap) return;
                    const rect = wrap.getBoundingClientRect();
                    if (rect.width && Number(audio.duration || 0) > 0) {
                        audio.currentTime = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)) * audio.duration;
                        sincronizarStemsComMaster(true);
                    }
                    document.querySelectorAll('#masterStemGrid .stem-row').forEach((item) => item.classList.remove('active'));
                    row.classList.add('active');
                    atualizarPlayheadStems();
                });

                if (wrap) {
                    let isDragging = false;
                    let startX = 0;

                    wrap.addEventListener('pointerdown', (e) => {
                        if (!masterCutMode) return;
                        e.preventDefault();
                        e.stopPropagation();

                        const rect = wrap.getBoundingClientRect();
                        startX = (e.clientX - rect.left) / rect.width;
                        isDragging = true;

                        removerSelecaoCorte();

                        const selEl = document.createElement('div');
                        selEl.className = 'stem-selection-box';
                        selEl.style.position = 'absolute';
                        selEl.style.top = '0';
                        selEl.style.bottom = '0';
                        selEl.style.backgroundColor = 'rgba(229, 9, 20, 0.3)';
                        selEl.style.borderLeft = '1px solid #E50914';
                        selEl.style.borderRight = '1px solid #E50914';
                        selEl.style.zIndex = '5';
                        selEl.style.pointerEvents = 'none';
                        wrap.appendChild(selEl);

                        const updateSelection = (ev) => {
                            if (!isDragging) return;
                            let currentX = (ev.clientX - rect.left) / rect.width;
                            currentX = Math.max(0, Math.min(1, currentX));
                            const left = Math.min(startX, currentX);
                            const width = Math.abs(startX - currentX);

                            selEl.style.left = (left * 100) + '%';
                            selEl.style.width = (width * 100) + '%';

                            cutSelection = {
                                track: track,
                                waveWrap: wrap,
                                startPct: left,
                                endPct: left + width,
                                el: selEl
                            };
                        };

                        const onUp = (ev) => {
                            if (!isDragging) return;
                            isDragging = false;
                            window.removeEventListener('pointermove', updateSelection);
                            window.removeEventListener('pointerup', onUp);

                            if (cutSelection && cutSelection.endPct > cutSelection.startPct + 0.002) {
                                mostrarMenuCorte(ev.clientX, ev.clientY);
                            } else {
                                removerSelecaoCorte();
                            }
                        };

                        window.addEventListener('pointermove', updateSelection);
                        window.addEventListener('pointerup', onUp);
                    });
                }
            }
            atualizarPan(0);
        }

        function renderStemSlider(label, value, min, max, step, suffix, onInput){
            const wrap = document.createElement('label');
            wrap.className = 'stem-fx-control';
            const header = document.createElement('span');
            header.innerHTML = `<span>${label}</span><strong>${value}${suffix}</strong>`;
            const slider = document.createElement('input');
            slider.type = 'range';
            slider.min = min;
            slider.max = max;
            slider.step = step;
            slider.value = value;
            slider.addEventListener('input', () => {
                const raw = Number(slider.value);
                const shown = Number.isInteger(raw) ? raw : raw.toFixed(step < 0.1 ? 3 : 2).replace(/0+$/, '').replace(/\.$/, '');
                header.querySelector('strong').textContent = `${shown}${suffix}`;
                onInput(raw);
            });
            wrap.appendChild(header);
            wrap.appendChild(slider);
            return wrap;
        }

        function abrirModalFxStem(track) {
            let modal = document.getElementById('stemFxModal');
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'stemFxModal';
                modal.className = 'stem-fx-modal';

                const content = document.createElement('div');
                content.id = 'stemFxModalContent';
                content.className = 'stem-fx-modal-content';

                modal.appendChild(content);
                document.body.appendChild(modal);

                modal.addEventListener('click', (e) => {
                    if (e.target === modal) modal.style.display = 'none';
                });
            }

            const content = document.getElementById('stemFxModalContent');
            content.innerHTML = `
                <div class="stem-fx-head">
                    <h3 id="stemFxTitle"></h3>
                    <button id="closeStemFxBtn" class="stem-fx-close" type="button" aria-label="Fechar">&times;</button>
                </div>
                <div class="stem-fx-rack-shell">
                    <div class="stem-fx-rack">
                        <div class="stem-fx-rack-top">
                            <span>Rack FX</span>
                            <button id="addStemFxBtn" class="stem-fx-add" type="button">+ FX</button>
                        </div>
                        <div id="stemFxRackList" class="stem-fx-rack-list"></div>
                    </div>
                    <div class="stem-fx-editor">
                        <div class="stem-fx-editor-head">
                            <div>
                                <span>Modulo</span>
                                <strong id="stemFxModuleName"></strong>
                            </div>
                            <button id="stemFxPowerBtn" class="stem-fx-power" type="button">Power</button>
                        </div>
                        <div id="stemFxBody" class="stem-fx-body"></div>
                    </div>
                </div>
                <div class="stem-fx-footer">
                    <button id="resetStemFxBtn" class="presetBtn" type="button">Resetar modulo</button>
                </div>
            `;
            const title = document.getElementById('stemFxTitle');
            if (title) title.textContent = `FX: ${track.row.dataset.title}`;

            const renderRack = () => {
                const rackList = document.getElementById('stemFxRackList');
                rackList.innerHTML = '';
                stemFxCatalog.forEach(([tab, label]) => {
                    const fxData = track.fxState[tab];
                    const isInserted = tab === 'eq' ? (fxData?.inserted !== false) : !!fxData?.inserted;

                    if (isInserted) {
                        const item = document.createElement('div');
                        item.className = 'stem-fx-rack-item' + (track.fxState.activeTab === tab ? ' is-active' : '');
                        item.dataset.tab = tab;

                        const isEnabled = fxData?.enabled !== false;

                        item.innerHTML = `
                            <button type="button" class="stem-fx-rack-power ${isEnabled ? 'is-on' : ''}" title="Power">&#x23FB;</button>
                            <span class="stem-fx-rack-name">${label}</span>
                            <button type="button" class="stem-fx-rack-remove" title="Remover">&times;</button>
                        `;

                        item.querySelector('.stem-fx-rack-name').addEventListener('click', () => {
                            track.fxState.activeTab = tab;
                            renderRack();
                            renderTab(tab);
                        });

                        item.querySelector('.stem-fx-rack-power').addEventListener('click', (e) => {
                            e.stopPropagation();
                            fxData.enabled = !isEnabled;
                            if (tab === 'eq') aplicarEqStem(track);
                            else aplicarFxStem(track);
                            renderRack();
                            if (track.fxState.activeTab === tab) renderTab(tab);
                        });

                        item.querySelector('.stem-fx-rack-remove').addEventListener('click', (e) => {
                            e.stopPropagation();
                            fxData.inserted = false;
                            fxData.enabled = false;
                            if (tab === 'eq') {
                                track.eqGains.fill(0);
                                aplicarEqStem(track);
                            } else {
                                aplicarFxStem(track);
                            }
                            if (track.fxState.activeTab === tab) {
                                const nextTab = stemFxCatalog.find(([t]) => t === 'eq' ? track.fxState[t]?.inserted !== false : track.fxState[t]?.inserted)?.[0];
                                track.fxState.activeTab = nextTab || null;
                                renderRack();
                                renderTab(nextTab);
                            } else {
                                renderRack();
                            }
                        });

                        rackList.appendChild(item);
                    }
                });
            };

            const renderTab = (tab) => {
                const body = document.getElementById('stemFxBody');
                const moduleName = document.getElementById('stemFxModuleName');
                const power = document.getElementById('stemFxPowerBtn');
                const resetBtn = document.getElementById('resetStemFxBtn');

                if (!tab) {
                    moduleName.textContent = 'Nenhum efeito';
                    power.style.display = 'none';
                    resetBtn.style.display = 'none';
                    body.innerHTML = '<p class="stem-fx-note">Nenhum efeito selecionado.</p>';
                    return;
                }

                power.style.display = 'inline-block';
                resetBtn.style.display = 'inline-block';

                const label = stemFxCatalog.find(([id]) => id === tab)?.[1] || tab;
                moduleName.textContent = label;

                const current = track.fxState[tab];
                power.classList.toggle('is-on', current?.enabled !== false);
                power.textContent = current?.enabled === false ? 'Bypass' : 'Ligado';

                body.innerHTML = '';

                if (tab === 'eq') {
                    const grid = document.createElement('div');
                    grid.className = 'stem-fx-eq-grid';
                    masterEqFreqs.forEach((freq, idx) => {
                        const band = document.createElement('div');
                        band.className = 'eqBand';
                        const val = document.createElement('div');
                        val.className = 'eqVal';
                        val.textContent = (track.eqGains[idx] || 0).toFixed(1) + ' dB';
                        const slider = document.createElement('input');
                        slider.className = 'eqSlider';
                        slider.type = 'range';
                        slider.min = '-18';
                        slider.max = '18';
                        slider.step = '0.1';
                        slider.value = track.eqGains[idx] || 0;
                        const label = document.createElement('div');
                        label.className = 'eqLabel';
                        label.textContent = freq >= 1000 ? (freq / 1000) + 'k' : freq;
                        slider.addEventListener('input', () => {
                            const gain = Number(slider.value);
                            val.textContent = gain.toFixed(1) + ' dB';
                            track.eqGains[idx] = gain;
                            aplicarEqStem(track);
                            atualizarRackFxStem(content, track);
                        });
                        band.appendChild(val);
                        band.appendChild(slider);
                        band.appendChild(label);
                        grid.appendChild(band);
                    });
                    body.appendChild(grid);
                    return;
                }

                const panel = document.createElement('div');
                panel.className = 'stem-fx-panel';
                const effect = track.fxState[tab];

                if (tab === 'compressor') {
                    panel.appendChild(renderStemSlider('Threshold', effect.threshold, -60, 0, 1, ' dB', (value) => { effect.threshold = value; aplicarFxStem(track); }));
                    panel.appendChild(renderStemSlider('Ratio', effect.ratio, 1, 12, 0.1, ':1', (value) => { effect.ratio = value; aplicarFxStem(track); }));
                    panel.appendChild(renderStemSlider('Attack', effect.attack, 0.001, 0.1, 0.001, ' s', (value) => { effect.attack = value; aplicarFxStem(track); }));
                    panel.appendChild(renderStemSlider('Release', effect.release, 0.05, 1, 0.01, ' s', (value) => { effect.release = value; aplicarFxStem(track); }));
                } else if (tab === 'gate') {
                    panel.appendChild(renderStemSlider('Threshold', effect.threshold, -80, -10, 1, ' dB', (value) => { effect.threshold = value; aplicarFxStem(track); }));
                    panel.appendChild(renderStemSlider('Reducao', effect.reduction, 0, 100, 1, '%', (value) => { effect.reduction = value; aplicarFxStem(track); }));
                    panel.appendChild(renderStemSlider('Attack', effect.attack, 0.001, 0.12, 0.001, ' s', (value) => { effect.attack = value; aplicarFxStem(track); }));
                    panel.appendChild(renderStemSlider('Release', effect.release, 0.02, 1, 0.01, ' s', (value) => { effect.release = value; aplicarFxStem(track); }));
                } else if (tab === 'saturation') {
                    panel.appendChild(renderStemSlider('Drive', effect.drive, 0, 100, 1, '%', (value) => { effect.drive = value; aplicarFxStem(track); }));
                    panel.appendChild(renderStemSlider('Mix', effect.mix, 0, 100, 1, '%', (value) => { effect.mix = value; aplicarFxStem(track); }));
                } else if (tab === 'limiter') {
                    panel.appendChild(renderStemSlider('Ceiling', effect.threshold, -18, 0, 0.5, ' dB', (value) => { effect.threshold = value; aplicarFxStem(track); }));
                    panel.appendChild(renderStemSlider('Release', effect.release, 0.01, 0.5, 0.01, ' s', (value) => { effect.release = value; aplicarFxStem(track); }));
                } else if (tab === 'deesser') {
                    panel.appendChild(renderStemSlider('Frequencia', effect.frequency, 3500, 12000, 100, ' Hz', (value) => { effect.frequency = value; aplicarFxStem(track); }));
                    panel.appendChild(renderStemSlider('Reducao', effect.amount, 0, 18, 0.5, ' dB', (value) => { effect.amount = value; aplicarFxStem(track); }));
                } else if (tab === 'filter') {
                    panel.appendChild(renderStemSlider('High-pass', effect.highpass, 20, 1000, 1, ' Hz', (value) => { effect.highpass = value; aplicarFxStem(track); }));
                    panel.appendChild(renderStemSlider('Low-pass', effect.lowpass, 3000, 20000, 100, ' Hz', (value) => { effect.lowpass = value; aplicarFxStem(track); }));
                } else if (tab === 'reverb') {
                    panel.appendChild(renderStemSlider('Mix', effect.mix, 0, 100, 1, '%', (value) => { effect.mix = value; aplicarFxStem(track); }));
                    panel.appendChild(renderStemSlider('Decay', effect.decay, 0.3, 6, 0.1, ' s', (value) => { effect.decay = value; aplicarFxStem(track); }));
                } else if (tab === 'delay') {
                    panel.appendChild(renderStemSlider('Mix', effect.mix, 0, 100, 1, '%', (value) => { effect.mix = value; aplicarFxStem(track); }));
                    panel.appendChild(renderStemSlider('Tempo', effect.time, 0.05, 1.2, 0.01, ' s', (value) => { effect.time = value; aplicarFxStem(track); }));
                    panel.appendChild(renderStemSlider('Feedback', effect.feedback, 0, 85, 1, '%', (value) => { effect.feedback = value; aplicarFxStem(track); }));
                } else if (tab === 'chorus') {
                    panel.appendChild(renderStemSlider('Mix', effect.mix, 0, 100, 1, '%', (value) => { effect.mix = value; aplicarFxStem(track); }));
                    panel.appendChild(renderStemSlider('Rate', effect.rate, 0.05, 8, 0.05, ' Hz', (value) => { effect.rate = value; aplicarFxStem(track); }));
                    panel.appendChild(renderStemSlider('Depth', effect.depth, 0.001, 0.03, 0.001, ' s', (value) => { effect.depth = value; aplicarFxStem(track); }));
                } else if (tab === 'tremolo') {
                    panel.appendChild(renderStemSlider('Rate', effect.rate, 0.1, 12, 0.1, ' Hz', (value) => { effect.rate = value; aplicarFxStem(track); }));
                    panel.appendChild(renderStemSlider('Depth', effect.depth, 0, 100, 1, '%', (value) => { effect.depth = value; aplicarFxStem(track); }));
                } else if (tab === 'autopan') {
                    if (!track.pannerNode) {
                        const note = document.createElement('p');
                        note.className = 'stem-fx-note';
                        note.textContent = 'Auto-pan indisponivel neste navegador.';
                        panel.appendChild(note);
                    }
                    panel.appendChild(renderStemSlider('Rate', effect.rate, 0.05, 6, 0.05, ' Hz', (value) => { effect.rate = value; aplicarFxStem(track); }));
                    panel.appendChild(renderStemSlider('Depth', effect.depth, 0, 100, 1, '%', (value) => { effect.depth = value; aplicarFxStem(track); }));
                }
                body.appendChild(panel);
            };

            document.getElementById('closeStemFxBtn').addEventListener('click', () => {
                modal.style.display = 'none';
            });

            document.getElementById('stemFxPowerBtn').addEventListener('click', () => {
                const tab = track.fxState.activeTab;
                if (!tab) return;
                const current = track.fxState[tab];
                if (!current) return;
                current.enabled = current.enabled === false;
                if (tab === 'eq') aplicarEqStem(track);
                else aplicarFxStem(track);
                renderRack();
                renderTab(tab);
            });

            document.getElementById('addStemFxBtn').addEventListener('click', (e) => {
                e.stopPropagation();
                let menu = document.getElementById('stemFxAddMenu');

                if (menu && menu.style.display === 'flex') {
                    menu.style.display = 'none';
                    return;
                }

                if (!menu) {
                    menu = document.createElement('div');
                    menu.id = 'stemFxAddMenu';
                    menu.className = 'stem-fx-add-menu';
                    menu.style.zIndex = '999999';
                    document.body.appendChild(menu);

                    document.addEventListener('click', () => {
                        if (menu) menu.style.display = 'none';
                    });
                }

                menu.innerHTML = '';
                let hasAvailable = false;
                stemFxCatalog.forEach(([tab, label]) => {
                    const fxData = track.fxState[tab];
                    const isInserted = tab === 'eq' ? (fxData?.inserted !== false) : !!fxData?.inserted;
                    if (!isInserted) {
                        hasAvailable = true;
                        const btn = document.createElement('button');
                        btn.type = 'button';
                        btn.className = 'stem-fx-add-item';
                        btn.textContent = label;
                        btn.addEventListener('click', () => {
                            if(!track.fxState[tab]) track.fxState[tab] = criarEstadoFxStem()[tab];
                            track.fxState[tab].inserted = true;
                            track.fxState[tab].enabled = true;
                            track.fxState.activeTab = tab;
                            if (tab === 'eq') aplicarEqStem(track);
                            else aplicarFxStem(track);
                            renderRack();
                            renderTab(tab);
                            menu.style.display = 'none';
                        });
                        menu.appendChild(btn);
                    }
                });

                if (!hasAvailable) {
                    menu.innerHTML = '<div class="stem-fx-add-empty">Nenhum efeito disponivel</div>';
                }

                const rect = e.target.getBoundingClientRect();
                menu.style.display = 'flex';
                menu.style.top = (rect.bottom + window.scrollY + 4) + 'px';
                menu.style.left = (rect.left + window.scrollX) + 'px';
            });

            document.getElementById('resetStemFxBtn').addEventListener('click', () => {
                const tab = track.fxState.activeTab;
                if (!tab) return;
                if (tab === 'eq') {
                    track.eqGains.fill(0);
                    track.fxState.eq.enabled = true;
                    aplicarEqStem(track);
                } else {
                    const defaults = criarEstadoFxStem()[tab];
                    track.fxState[tab] = { ...defaults, inserted: true };
                    aplicarFxStem(track);
                }
                renderRack();
                renderTab(tab);
            });

            const currActive = track.fxState.activeTab;
            const isCurrActiveInserted = currActive === 'eq' ? (track.fxState[currActive]?.inserted !== false) : !!track.fxState[currActive]?.inserted;

            if (!isCurrActiveInserted) {
                const nextTab = stemFxCatalog.find(([t]) => t === 'eq' ? track.fxState[t]?.inserted !== false : track.fxState[t]?.inserted)?.[0];
                track.fxState.activeTab = nextTab || null;
            }

            renderRack();
            renderTab(track.fxState.activeTab);
            modal.style.display = 'flex';
        }

        async function adicionarFaixaStem(faixa, index = masterStemState.tracks.length){
            const grid = document.getElementById('masterStemGrid');
            if (!grid || !faixa?.url) return null;
            await ensureStemAudioContext();

            const playheadHit = document.getElementById('masterStemPlayheadHit');
            const row = criarLinhaStem(faixa, index);
            grid.insertBefore(row, playheadHit || null);
            const player = new Audio(faixa.url);
            player.preload = 'auto';
            if (!faixa.isLocalRecording) player.crossOrigin = 'anonymous';
            player.loop = false;
            player.preservesPitch = false;

            const sourceNode = masterStemState.context.createMediaElementSource(player);
            const gainNode = masterStemState.context.createGain();
            const trimGainNode = masterStemState.context.createGain();
            trimGainNode.gain.value = 1;

            const pannerNode = typeof masterStemState.context.createStereoPanner === 'function'
                ? masterStemState.context.createStereoPanner()
                : null;
            const fxState = criarEstadoFxStem();
            const fxNodes = criarFxNodesStem(masterStemState.context, fxState);

            const eqFilters = masterEqFreqs.map((freq) => {
                const f = masterStemState.context.createBiquadFilter();
                f.type = 'peaking';
                f.frequency.value = freq;
                f.Q.value = 1;
                f.gain.value = 0;
                return f;
            });

            sourceNode.connect(eqFilters[0]);
            for (let i = 0; i < eqFilters.length - 1; i++) {
                eqFilters[i].connect(eqFilters[i + 1]);
            }

            eqFilters[eqFilters.length - 1].connect(fxNodes.input);
            fxNodes.output.connect(pannerNode ? pannerNode : trimGainNode);
            if (pannerNode) fxNodes.autopanDepth.connect(pannerNode.pan);
            if (pannerNode) pannerNode.connect(trimGainNode);
            trimGainNode.connect(gainNode);
            gainNode.connect(masterStemState.masterGain);

            const track = {
                row,
                player,
                sourceNode,
                trimGainNode,
                gainNode,
                pannerNode,
                eqFilters,
                eqGains: new Array(masterEqFreqs.length).fill(0),
                fxNodes,
                fxState,
                volume: row.querySelector('.stem-volume'),
                panValue: 0,
                duration: 0,
                trimStart: 0,
                trimEnd: 1,
                fadeIn: 0,
                fadeOut: 0,
                _currentTrimTarget: 1,
            };
            masterStemState.tracks.push(track);
            player.addEventListener('loadedmetadata', () => {
                track.duration = Number(player.duration || track.duration || 0);
                row.dataset.duration = `${track.duration || 0}`;
                atualizarLargurasClipStems();
                atualizarPlayheadStems();
            });
            conectarEventosStem(row, track);
            atualizarContadorStems();
            aplicarEstadosMixerStems();
            atualizarPlayheadStems();
            const canvas = row.querySelector('.stem-wave');
            if (canvas) {
                gerarPicosStem(faixa.url).then((picos) => desenharPicosStem(canvas, picos)).catch(() => {
                    desenharPicosStem(canvas, new Float32Array(200).fill(.08));
                });
            }
            return track;
        }

        let stemRecorderState = null;
        async function alternarGravacaoStem(btn){
            if (stemRecorderState?.recorder?.state === 'recording') {
                stemRecorderState.recorder.stop();
                btn.classList.remove('is-on');
                btn.textContent = 'Gravar nova trilha';
                return;
            }

            if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
                alert('Gravacao pelo navegador nao esta disponivel aqui.');
                return;
            }

            try {
                await ensureStemAudioContext();
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                const chunks = [];
                const recorder = new MediaRecorder(stream);
                stemRecorderState = { recorder, stream, chunks };

                recorder.addEventListener('dataavailable', (event) => {
                    if (event.data?.size) chunks.push(event.data);
                });
                recorder.addEventListener('stop', () => {
                    stream.getTracks().forEach((track) => track.stop());
                    const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
                    const url = URL.createObjectURL(blob);
                    const take = masterStemState.tracks.filter((track) => track.row.dataset.title.startsWith('Gravacao')).length + 1;
                    adicionarFaixaStem({
                        titulo: `Gravacao ${take}`,
                        nome: `gravacao-${take}.webm`,
                        url,
                        isLocalRecording: true,
                    });
                    setMasterStatus(`Nova trilha gravada: Gravacao ${take}`);
                    stemRecorderState = null;
                });

                recorder.start();
                btn.classList.add('is-on');
                btn.textContent = 'Parar gravacao';
                setMasterStatus('Gravando nova trilha...');
            } catch (error) {
                alert('Nao consegui acessar o microfone: ' + error.message);
                stemRecorderState = null;
            }
        }

        async function montarMixerStems(faixas){
            const grid = document.getElementById('masterStemGrid');
            if (!grid) return;
            destruirMixerStems();
            grid.querySelectorAll('.stem-row').forEach((row) => row.remove());

            for (const [index, faixa] of faixas.entries()) {
                await adicionarFaixaStem(faixa, index);
            }

            atualizarContadorStems();
            aplicarEstadosMixerStems();
            atualizarLargurasClipStems();
            renderizarWaveformsMaster();
            sincronizarStemsComMaster(true);
        }

        function bindStemMasterSync(){
            const audio = document.getElementById('masterAudio');
            const grid = document.getElementById('masterStemGrid');
            const playheadHit = document.getElementById('masterStemPlayheadHit');
            if (!audio) return;

            let playheadRaf;
            const loopPlayhead = () => {
                if (!audio.paused) {
                    atualizarPlayheadStems();
                    atualizarTrimMuteStems();
                    playheadRaf = requestAnimationFrame(loopPlayhead);
                }
            };

            audio.addEventListener('play', () => {
                if (masterStemState.tracks.length) tocarTodasStems();
                const stemPlayBtn = document.getElementById('stemGlobalPlayBtn');
                if (stemPlayBtn) stemPlayBtn.innerHTML = '⏸ Pausar Stems';
                playheadRaf = requestAnimationFrame(loopPlayhead);
            });
            audio.addEventListener('pause', () => {
                pausarTodasStems();
                audio.muted = false;
                const stemPlayBtn = document.getElementById('stemGlobalPlayBtn');
                if (stemPlayBtn) stemPlayBtn.innerHTML = '▶ Reproduzir Stems';
                cancelAnimationFrame(playheadRaf);
                atualizarPlayheadStems();
            });
            audio.addEventListener('seeked', () => sincronizarStemsComMaster(true));
            audio.addEventListener('timeupdate', () => {
                sincronizarStemsComMaster(false);
                atualizarPlayheadStems();
            });
            audio.addEventListener('ended', () => {
                pausarTodasStems();
                audio.muted = false;
                const stemPlayBtn = document.getElementById('stemGlobalPlayBtn');
                if (stemPlayBtn) stemPlayBtn.innerHTML = '▶ Reproduzir Stems';
                cancelAnimationFrame(playheadRaf);
                atualizarPlayheadStems();
            });
            if (playheadHit && grid) {
                playheadHit.addEventListener('click', (event) => {
                    if (!masterStemState.tracks.length) return;
                    const rect = playheadHit.getBoundingClientRect();
                    if (!rect.width || Number(audio.duration || 0) <= 0) return;
                    audio.currentTime = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)) * audio.duration;
                    sincronizarStemsComMaster(true);
                });
            }
        }

        async function renderizarStems(resultado) {
                const area = document.getElementById("stemsArea");
                if (!area) return;
                area.style.display = "block";

                const faixas = resultado && Array.isArray(resultado.faixas)
                    ? resultado.faixas
                    : [];

                if (!faixas.length) {
                    setMasterStatus('Stems processados, mas nenhuma faixa foi encontrada.');
                    return;
                }

                let controls = document.getElementById('stemGlobalControls');
                if (!controls) {
                    controls = document.createElement('div');
                    controls.id = 'stemGlobalControls';
                    controls.style.display = 'flex';
                    controls.style.gap = '12px';
                    controls.style.marginBottom = '16px';
                    controls.style.alignItems = 'center';
                    controls.style.flexWrap = 'wrap';
                    
                    const btnPlay = document.createElement('button');
                    btnPlay.id = 'stemGlobalPlayBtn';
                    btnPlay.className = 'presetBtn is-on';
                    btnPlay.style.minWidth = '160px';
                    btnPlay.style.fontWeight = 'bold';
                    btnPlay.style.justifyContent = 'center';
                    
                    const audio = document.getElementById('masterAudio');
                    btnPlay.innerHTML = (audio && !audio.paused) ? '⏸ Pausar Stems' : '▶ Reproduzir Stems';

                    btnPlay.onclick = () => {
                        if (audio) {
                            if (audio.paused) {
                                audio.play().catch(()=>{});
                            } else {
                                audio.pause();
                            }
                        }
                    };
                    controls.appendChild(btnPlay);

                    const btnRecord = document.createElement('button');
                    btnRecord.id = 'stemRecordTrackBtn';
                    btnRecord.className = 'presetBtn';
                    btnRecord.type = 'button';
                    btnRecord.textContent = 'Gravar nova trilha';
                    btnRecord.onclick = () => alternarGravacaoStem(btnRecord);
                    controls.appendChild(btnRecord);

                    const btnCut = document.createElement('button');
                    btnCut.id = 'stemCutModeBtn';
                    btnCut.className = 'presetBtn';
                    btnCut.type = 'button';
                    btnCut.innerHTML = '✂️ Modo Corte: OFF';
                    btnCut.setAttribute('aria-pressed', 'false');
                    btnCut.onclick = () => alternarModoCorteStems(btnCut);
                    controls.appendChild(btnCut);

                    const btnUndoCut = document.createElement('button');
                    btnUndoCut.id = 'stemUndoCutBtn';
                    btnUndoCut.className = 'presetBtn';
                    btnUndoCut.type = 'button';
                    btnUndoCut.textContent = '↶ Desfazer corte';
                    btnUndoCut.disabled = true;
                    btnUndoCut.onclick = () => desfazerUltimoCorteStem();
                    controls.appendChild(btnUndoCut);
                    atualizarBotaoDesfazerCorte();

                    const btnSaveConfig = document.createElement('button');
                    btnSaveConfig.className = 'presetBtn';
                    btnSaveConfig.type = 'button';
                    btnSaveConfig.innerHTML = '💾 Salvar Configs';
                    btnSaveConfig.title = 'Salvar configurações atuais de edição (cortes, fx, volume)';
                    btnSaveConfig.onclick = salvarConfiguracoesStems;
                    controls.appendChild(btnSaveConfig);

                    const btnLoadConfig = document.createElement('button');
                    btnLoadConfig.className = 'presetBtn';
                    btnLoadConfig.type = 'button';
                    btnLoadConfig.innerHTML = '📂 Carregar Configs';
                    btnLoadConfig.title = 'Carregar configurações salvas';
                    btnLoadConfig.onclick = carregarConfiguracoesStems;
                    controls.appendChild(btnLoadConfig);

                    const btnExportWav = document.createElement('button');
                    btnExportWav.id = 'stemExportMixBtn';
                    btnExportWav.className = 'presetBtn';
                    btnExportWav.style.backgroundColor = '#16a34a';
                    btnExportWav.style.color = 'white';
                    btnExportWav.type = 'button';
                    btnExportWav.innerHTML = '⬇️ Exportar Mix';
                    btnExportWav.title = 'Renderizar mix final e escolher formato WAV ou MP3';
                    btnExportWav.onclick = abrirModalExportacaoStems;
                    controls.appendChild(btnExportWav);

                    const btnLoop = document.createElement('button');
                    btnLoop.id = 'stemLoopBtn';
                    btnLoop.className = 'presetBtn';
                    btnLoop.type = 'button';
                    btnLoop.innerHTML = (audio && audio.loop) ? '🔁 Loop: ON' : '🔁 Loop: OFF';
                    btnLoop.title = 'Alternar repetição contínua (Loop)';
                    if (audio && audio.loop) {
                        btnLoop.classList.add('is-on');
                    }
                    btnLoop.onclick = () => {
                        if (audio) {
                            audio.loop = !audio.loop;
                            btnLoop.innerHTML = audio.loop ? '🔁 Loop: ON' : '🔁 Loop: OFF';
                            btnLoop.classList.toggle('is-on', audio.loop);
                        }
                    };
                    controls.appendChild(btnLoop);

                    const grid = document.getElementById('masterStemGrid');
                    if (grid && grid.parentNode) {
                        grid.parentNode.insertBefore(controls, grid);
                    }
                }

                await montarMixerStems(faixas);
                setMasterStatus('Stems extraídos e carregados.');
            }


        function processarArquivoSelecionado(file) {
            if (!file) return;
            arquivoAtual = file;

            const fileInput = document.getElementById('masterFile');
            if (fileInput) {
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                fileInput.files = dataTransfer.files;
            }

            const audioObj = document.getElementById('masterAudio');
            if (audioObj) {
                audioObj.src = URL.createObjectURL(file);
                audioObj.load();
            }

            const nameLabel = document.getElementById('currentFileName');
            if (nameLabel) nameLabel.textContent = file.name;

            const dropZone = document.getElementById('fileDropZone');
            const workspace = document.getElementById('masterWorkspace');
            
            if (dropZone) dropZone.classList.add('fade-out');
            
            setTimeout(() => {
                if (dropZone) dropZone.style.display = 'none';
                if (workspace) workspace.style.display = 'block';
                if (workspace) workspace.classList.add('fade-in', 'workflow-active');

                const panelStems = document.getElementById("panelStems");
                const panelEq = document.getElementById("panelEq");
                const stack = document.querySelector(".advancedStack");

                if (currentWorkflow === 'mix') {
                    if (panelStems) {
                        panelStems.style.display = "block";
                        panelStems.open = true;
                        if (stack) stack.prepend(panelStems);
                    }
                    if (panelEq) panelEq.open = false;
                    
                    const areaStems = document.getElementById("stemsArea");
                    if (areaStems) areaStems.style.display = "block";
                    
                    separarStems();
                } else {
                    if (panelStems) panelStems.style.display = "none";
                    if (panelEq) panelEq.open = true;
                    
                    uploadMasterFile();
                }
            }, 400);
        }

        document.addEventListener('DOMContentLoaded', () => {
            const dropZone = document.getElementById('fileDropZone');
            const fileInput = document.getElementById('masterFile');
            const openBtn = document.getElementById('openFileBrowserBtn');

            if (openBtn) openBtn.addEventListener('click', () => fileInput.click());

            if (fileInput) {
                fileInput.addEventListener('change', (e) => processarArquivoSelecionado(e.target.files[0]));
            }

            if (dropZone) {
                ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(evt => {
                    dropZone.addEventListener(evt, (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                    }, false);
                });

                ['dragenter', 'dragover'].forEach(evt => {
                    dropZone.addEventListener(evt, () => dropZone.classList.add('drag-over'), false);
                });

                ['dragleave', 'drop'].forEach(evt => {
                    dropZone.addEventListener(evt, () => dropZone.classList.remove('drag-over'), false);
                });

                dropZone.addEventListener('drop', (e) => {
                    const file = e.dataTransfer.files[0];
                    processarArquivoSelecionado(file);
                }, false);
            }
            
            const btnSepStems = document.getElementById('btnSepararStems');
            if (btnSepStems) btnSepStems.addEventListener('click', separarStems);
        });

        document.getElementById('autoLufsBtn').addEventListener('click', () => {
            const current = window.lufsSmooth || -14;
            const diff = -14 - current;
            if (masterEqState.gainNode) {
                const currentGain = masterEqState.gainNode.gain.value;
                const factor = Math.pow(10, diff / 20);
                masterEqState.gainNode.gain.value = currentGain * factor;
            }
        });
        async function aplicarVibe(evt, vibeMode) {
            const jobId = document.getElementById('jobIdField')?.value || masterJobId;
            if (!jobId) { 
                alert("Por favor, faca o upload de um audio primeiro!"); 
                return; 
            }

            const btn = evt.currentTarget;
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '<span>⏳</span> Processando...';
            btn.disabled = true;

            try {
                const response = await fetch('/masterizacao/preview', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        job_id: jobId, 
                        mode: vibeMode, 
                        compression: masterCompression, 
                        vocal_position: masterVoicePosition, 
                        no_drums: masterNoDrums
                    })
                });
                
                const data = await response.json();

                if (response.ok && data.preview_url) {
                    masterActiveMode = vibeMode;
                    updateModeButtons();
                    await switchPlayerSource(data.preview_url);
                    setMasterStatus('Vibe ativa: ' + (data.mode_label || vibeMode));
                } else { 
                    throw new Error(data.error || "Erro ao processar"); 
                }
            } catch (e) { 
                alert("Erro na Vibe: " + e.message); 
            } finally {
                btn.innerHTML = originalHTML;
                btn.disabled = false;
            }
        }

        function setMasterStatus(text){
            const el = document.getElementById('masterStatus');
            if (el) el.textContent = text;
        }

        function fmtTime(sec){
            const s = Math.max(0, Math.floor(Number(sec) || 0));
            const m = Math.floor(s / 60);
            const r = s % 60;
            return String(m) + ':' + String(r).padStart(2, '0');
        }

        function updateModeButtons(){
            document.querySelectorAll('.presetBtn').forEach((btn) => {
                const mode = btn.getAttribute('data-mode') || '';
                btn.classList.toggle('is-on', mode && mode === masterActiveMode);
            });
            const badge = document.getElementById('masterModeBadge');
            if (badge) badge.textContent = (masterActiveMode && masterActiveMode !== 'original') ? ('Preset: ' + masterActiveMode) : 'Original';
        }

        function updateMixButtons(){
            document.querySelectorAll('#compressionGroup .ctlBtn').forEach((btn) => {
                btn.classList.toggle('is-on', btn.getAttribute('data-comp') === masterCompression);
            });
            document.querySelectorAll('#voiceGroup .ctlBtn').forEach((btn) => {
                btn.classList.toggle('is-on', btn.getAttribute('data-voice') === masterVoicePosition);
            });
            const drumBtn = document.getElementById('noDrumsBtn');
            if (drumBtn) drumBtn.classList.toggle('is-on', masterNoDrums);
        }

          function getMixPayload(){
                return {
                    compression: masterCompression,
                    vocal_position: masterVoicePosition,
                    no_drums: masterNoDrums ? "true" : "false", 
                };
            }


        function buildPreviewKey(mode){
            return [mode, masterCompression, masterVoicePosition, masterNoDrums ? 'sem_bateria' : 'com_bateria'].join('|');
        }

        function connectEqGraph(){
            if (!masterEqState.source || !masterEqState.context) return;

            try { masterEqState.source.disconnect(); } catch(e){}
            try { masterEqState.gainNode.disconnect(); } catch(e){}
            masterEqState.filters.forEach(f=>{ try{ f.disconnect(); }catch(e){} });

            const endOfChain = masterEqState.gainNode;

            if(!masterEqState.enabled || !masterEqState.filters.length){
                masterEqState.source.connect(endOfChain);
            } else {
                masterEqState.source.connect(masterEqState.filters[0]);
                for(let i = 0; i < masterEqState.filters.length - 1; i++){
                    masterEqState.filters[i].connect(masterEqState.filters[i + 1]);
                }
                masterEqState.filters[masterEqState.filters.length - 1].connect(endOfChain);
            }
            
            endOfChain.connect(masterEqState.analyser);
        }

        function buildEqPanel(){
            const grid = document.getElementById('eqGrid');
            if (!grid) return;
            grid.innerHTML = '';
            masterEqFreqs.forEach((freq, idx) => {
                const band = document.createElement('div');
                band.className = 'eqBand';
                band.innerHTML =
                    '<div class="eqVal" id="eqVal' + idx + '">0.0 dB</div>' +
                    '<input class="eqSlider" type="range" min="-18" max="18" step="0.1" value="0" data-band="' + idx + '" />' +
                    '<div class="eqLabel">' + (freq >= 1000 ? (String(freq / 1000) + 'k') : String(freq)) + '</div>';
                grid.appendChild(band);
            });
        }

        function resetEqSliders(){
            document.querySelectorAll('.eqSlider').forEach((slider) => {
                slider.value = '0';
                const idx = Number(slider.getAttribute('data-band') || 0);
                const val = document.getElementById('eqVal' + idx);
                if (val) val.textContent = '0.0 dB';
                if (masterEqState.filters[idx]) masterEqState.filters[idx].gain.value = 0;
            });
        }

        function bindEqUi(){
            const powerBtn = document.getElementById('eqPowerBtn');
            const resetBtn = document.getElementById('eqResetBtn');

            document.querySelectorAll('.eqSlider').forEach((slider) => {
                slider.addEventListener('input', () => {
                    const idx = Number(slider.getAttribute('data-band') || 0);
                    const gain = Number(slider.value || 0);
                    const val = document.getElementById('eqVal' + idx);
                    if (val) val.textContent = gain.toFixed(1) + ' dB';
                    if (masterEqState.filters[idx]) masterEqState.filters[idx].gain.value = gain;
                });
            });

            if (powerBtn) {
                powerBtn.addEventListener('click', () => {
                    masterEqState.enabled = !masterEqState.enabled;
                    powerBtn.textContent = masterEqState.enabled ? 'EQ ON' : 'EQ OFF';
                    powerBtn.classList.toggle('on', masterEqState.enabled);
                    connectEqGraph();
                });
            }

            if (resetBtn) {
                resetBtn.addEventListener('click', () => {
                    resetEqSliders();
                });
            }
        }

        function getEqPayload(){
            const gains = masterEqFreqs.map((_, idx) => {
                const slider = document.querySelector('.eqSlider[data-band="' + idx + '"]');
                return Number(slider ? slider.value : 0);
            });
            return { eq_enabled: !!masterEqState.enabled, eq_gains: gains };
        }

      
function bindMixUi(){
    document.querySelectorAll('#compressionGroup .ctlBtn').forEach((btn) => {
        btn.addEventListener('click', () => {
            masterCompression = btn.getAttribute('data-comp') || 'media';
            updateMixButtons();
            requestPreview(masterActiveMode || 'original', true);
        });
    });

    document.querySelectorAll('#voiceGroup .ctlBtn').forEach((btn) => {
        btn.addEventListener('click', () => {
            masterVoicePosition = btn.getAttribute('data-voice') || 'central';
            updateMixButtons();
            requestPreview(masterActiveMode || 'original', true);
        });
    });

    const drumBtn = document.getElementById('noDrumsBtn');
    if (drumBtn) {
        drumBtn.replaceWith(drumBtn.cloneNode(true));
        
        const novoDrumBtn = document.getElementById('noDrumsBtn');
        novoDrumBtn.addEventListener('click', () => {
            masterNoDrums = !masterNoDrums;
            updateMixButtons();
            requestPreview(masterActiveMode || 'original', true);
        });
    }
}

        async function ensureEqAudioGraph(){
            const audio = document.getElementById('masterAudio');
            if (!audio) return;

            initSharedAudioContext();

            if (!masterEqState.source) {
                masterEqState.source = masterEqState.context.createMediaElementSource(audio);
                masterEqState.gainNode = masterEqState.context.createGain();
                masterEqState.gainNode.gain.value = 1.0;

                masterEqState.filters = masterEqFreqs.map((freq) => {
                    const f = masterEqState.context.createBiquadFilter();
                    f.type = 'peaking';
                    f.frequency.value = freq;
                    f.Q.value = 1;
                    f.gain.value = 0;
                    return f;
                });

                connectEqGraph();
            }

            if (masterEqState.context.state === 'suspended') {
                await masterEqState.context.resume();
            }
        }

        function bindPlayerUi(){
            const audio = document.getElementById('masterAudio');
            const playBtn = document.getElementById('masterPlayBtn');
            const seek = document.getElementById('masterSeek');
            const cur = document.getElementById('masterCurrent');
            const dur = document.getElementById('masterDuration');
            if (!audio || !playBtn || !seek || !cur || !dur) return;

            playBtn.addEventListener('click', async () => {
                if (!audio.getAttribute('src')) return;
                await ensureEqAudioGraph();
                if (audio.paused) {
                    try { await audio.play(); } catch (e) {}
                } else {
                    audio.pause();
                }
            });

            audio.addEventListener('play', () => { playBtn.textContent = '⏸'; });
            audio.addEventListener('pause', () => { playBtn.textContent = '▶'; });
            audio.addEventListener('loadedmetadata', () => {
                dur.textContent = fmtTime(audio.duration);
            });
            audio.addEventListener('timeupdate', () => {
                cur.textContent = fmtTime(audio.currentTime);
                const total = Number(audio.duration || 0);
                if (total > 0) {
                    seek.value = String((audio.currentTime / total) * 100);
                }
            });

            seek.addEventListener('input', () => {
                const total = Number(audio.duration || 0);
                if (total > 0) {
                    audio.currentTime = (Number(seek.value || 0) / 100) * total;
                }
            });
        }

        async function switchPlayerSource(nextUrl){
            const audio = document.getElementById('masterAudio');
            if (!audio || !nextUrl) return;
            const wasPlaying = !audio.paused;
            const keepTime = Number(audio.currentTime || 0);
            pausarTodasStems();
            audio.src = nextUrl;
            audio.load();
            await new Promise((resolve) => {
                const done = () => {
                    audio.removeEventListener('loadedmetadata', done);
                    resolve();
                };
                audio.addEventListener('loadedmetadata', done, { once: true });
                setTimeout(resolve, 1200);
            });
            try {
                audio.currentTime = keepTime;
                sincronizarStemsComMaster(true);
            } catch (e) {}
            if (wasPlaying) {
                try { await audio.play(); } catch (e) {}
            }
        }

        async function uploadMasterFile(){
            const input = document.getElementById('masterFile');
            const file = input && input.files ? input.files[0] : null;
            if (!file){
                setMasterStatus('Selecione um arquivo de audio.');
                return;
            }

            const body = new FormData();
            body.append('audio_file', file);
            setMasterStatus('Enviando arquivo...');

            const r = await fetch('/masterizacao/upload', { method: 'POST', body });
            const data = await r.json();
            if (!r.ok || !data.job_id){
                setMasterStatus(data.error || 'Falha no upload.');
                return;
            }

            masterJobId = data.job_id;
            const field = document.getElementById('jobIdField');
            if (field) field.value = data.job_id;
            masterOriginalUrl = data.original_url || '';
            masterActiveMode = 'original';
            Object.keys(masterPreviewCache).forEach((k) => delete masterPreviewCache[k]);
            updateModeButtons();
            await switchPlayerSource(masterOriginalUrl);
            setMasterStatus('Arquivo carregado. Clique em um preset ou use os controles de mixagem.');
        }

        async function requestPreview(mode, forceRefresh=false){
            if (!masterJobId){
                setMasterStatus('Primeiro envie um arquivo de audio.');
                return;
            }
            
            if (!forceRefresh && masterActiveMode === mode) {
                if (mode === 'original') return; 
                masterActiveMode = 'original';
                updateModeButtons();
                requestPreview('original', true);
                return;
            }

            const key = buildPreviewKey(mode);
            if (masterPreviewCache[key]) {
                masterActiveMode = mode;
                updateModeButtons();
                await switchPlayerSource(masterPreviewCache[key]);
                setMasterStatus('Preset ativo: ' + mode + '.');
                return;
            }

            setMasterStatus('Processando preview...');
            
            const btnClicado = document.querySelector(`.presetBtn[data-mode="${mode}"]`);
            let originalTexto = "";
            if (btnClicado) {
                originalTexto = btnClicado.innerHTML;
                btnClicado.innerHTML = `<div class="spinner"></div> Processando...`;
                document.querySelectorAll('.presetBtn').forEach(b => b.disabled = true);
            }

            const progContainer = document.getElementById('masterProgressContainer');
            const progBar = document.getElementById('masterProgressBar');
            if (progContainer && progBar) {
                progContainer.style.display = 'block';
                progBar.style.width = '0%';
                setTimeout(() => progBar.style.width = '25%', 200);
                setTimeout(() => progBar.style.width = '60%', 1500);
                setTimeout(() => progBar.style.width = '85%', 3000);
            }

            const mix = getMixPayload();
            try {
                const r = await fetch('/masterizacao/preview', {
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body: JSON.stringify({ job_id: masterJobId, mode, ...mix })
                });
                const data = await r.json();
                
                if (!r.ok || !data.preview_url){
                    setMasterStatus(data.error || 'Nao foi possivel gerar preview.');
                    if (progContainer) progContainer.style.display = 'none';
                    return;
                }

                if (progBar) progBar.style.width = '100%';
                setTimeout(() => { if (progContainer) progContainer.style.display = 'none'; }, 500);

                masterPreviewCache[key] = data.preview_url;
                masterActiveMode = mode;
                updateModeButtons();
                await switchPlayerSource(data.preview_url);
                setMasterStatus('Preset ativo: ' + (data.mode_label || mode));

            } catch (err) {
                setMasterStatus('Erro ao processar áudio.');
                if (progContainer) progContainer.style.display = 'none';
            } finally {
                if (btnClicado) {
                    btnClicado.innerHTML = originalTexto;
                }
                document.querySelectorAll('.presetBtn').forEach(b => b.disabled = false);
                updateModeButtons();
            }
        }

        async function exportMasterAudio(){
            if (!masterJobId){
                setMasterStatus('Primeiro envie um arquivo de audio.');
                return;
            }

            const exportBtn = document.getElementById('masterExportBtn');
            const originalExportText = exportBtn ? exportBtn.innerHTML : "Exportar";

            if (exportBtn) {
                exportBtn.innerHTML = `<div class="spinner"></div> Exportando...`;
                exportBtn.disabled = true;
            }

            const payload = getEqPayload();
            payload.job_id = masterJobId;
            payload.mode = masterActiveMode || 'original';

            const mix = getMixPayload();
            payload.compression = mix.compression;
            payload.vocal_position = mix.vocal_position;
            payload.no_drums = mix.no_drums;

            const formatSelect = document.getElementById('masterExportFormat');
            payload.export_format = formatSelect ? (formatSelect.value || 'wav') : 'wav';

            setMasterStatus('Gerando exportacao final...');

            try {
                const r = await fetch('/masterizacao/export', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const data = await r.json();

                if (!r.ok || !data.download_url){
                    setMasterStatus(data.error || 'Nao foi possivel exportar.');
                    return;
                }

                const a = document.createElement('a');
                a.href = data.download_url;
                a.download = data.filename || ('master_export.' + payload.export_format);
                document.body.appendChild(a);
                a.click();
                a.remove();
                setMasterStatus('Exportacao pronta: ' + (data.mode_label || 'Original') + ' + EQ.');

            } catch (err) {
                setMasterStatus('Erro na exportação.');
            } finally {
                if (exportBtn) {
                    exportBtn.innerHTML = originalExportText;
                    exportBtn.disabled = false;
                }
            }
        }

        function bindMasterVolume(){
            const slider = document.getElementById('masterVolume');
            const value = document.getElementById('masterVolumeValue');
            if(!slider || !value) return;

            slider.addEventListener('input', () => {
                const pct = Number(slider.value);
                value.textContent = pct + '%';
                if(masterEqState.gainNode){
                    masterEqState.gainNode.gain.value = pct / 100;
                }
                if(masterStemState.masterGain){
                    masterStemState.masterGain.gain.value = pct / 100;
                }
            });
        }   
        document.addEventListener("DOMContentLoaded", () => {
                const audioPlayer = document.getElementById("masterAudio");
                const btnA = document.getElementById("abBtnA");
                const btnB = document.getElementById("abBtnB");
                const modeBadge = document.getElementById("masterModeBadge");
                
                window.masterTrackUrls = { original: "", mastered: "" };

                const originalXHR = window.XMLHttpRequest;
                function FilteredXHR() {
                    const xhr = new originalXHR();
                    xhr.addEventListener("readystatechange", function() {
                        if (xhr.readyState === 4 && xhr.status === 200) {
                            const urlChamada = xhr._url || "";
                            
                            if (urlChamada.includes("/masterizacao/upload")) {
                                try {
                                    const data = JSON.parse(xhr.responseText);
                                    if (data.job_id && data.ext) {
                                        window.masterTrackUrls.original = `/masterizacao/audio/${data.job_id}${data.ext.toLowerCase()}`;
                                        window.masterTrackUrls.mastered = "";
                                        btnB.setAttribute("disabled", "true");
                                        
                                        switchAudioSource("original");
                                    }
                                } catch(e) { console.error("Erro ao ler upload via XHR:", e); }
                            }
                            
                            if (urlChamada.includes("/masterizacao/preview")) {
                                try {
                                    const data = JSON.parse(xhr.responseText);
                                    if (data.download_url) {
                                        window.masterTrackUrls.mastered = data.download_url;
                                        btnB.removeAttribute("disabled");
                                        
                                        if (btnB.classList.contains("active")) {
                                            switchAudioSource("mastered");
                                        }
                                    }
                                } catch(e) { console.error("Erro ao ler preview via XHR:", e); }
                            }
                        }
                    });
                    
                    const originalOpen = xhr.open;
                    xhr.open = function(method, url, ...args) {
                        xhr._url = url;
                        return originalOpen.apply(xhr, [method, url, ...args]);
                    };
                    
                    return xhr;
                }
                window.XMLHttpRequest = FilteredXHR;

                function switchAudioSource(target) {
                    const url = window.masterTrackUrls[target];
                    if (!url) return;

                    const currentTime = audioPlayer.currentTime;
                    const isPlaying = !audioPlayer.paused;

                    audioPlayer.src = url;
                    audioPlayer.load();
                    audioPlayer.currentTime = currentTime;

                    if (isPlaying) {
                        audioPlayer.play().catch(() => {});
                    }

                    if (target === "original") {
                        btnA.classList.add("active");
                        btnB.classList.remove("active");
                        if(modeBadge) {
                            modeBadge.textContent = "Original (Bypass)";
                            modeBadge.style.background = "rgba(245, 158, 11, 0.2)";
                        }
                    } else {
                        btnB.classList.add("active");
                        btnA.classList.remove("active");
                        if(modeBadge) {
                            modeBadge.textContent = "Masterizado (A/B Ativo)";
                            modeBadge.style.background = "rgba(57, 215, 230, 0.2)";
                        }
                    }
                }

                btnA.addEventListener("click", () => switchAudioSource("original"));
                btnB.addEventListener("click", () => switchAudioSource("mastered"));
            });

        document.addEventListener('DOMContentLoaded', () => {
            buildEqPanel();
            startLufsMeter();
            bindEqUi();
            startSpectrum();
            bindMasterVolume();
            bindMixUi();
            bindPlayerUi();
            bindStemMasterSync();
            bindConfiguracoesVisualizacao();
            atualizarInformacoesFFT();
            const upBtn = document.getElementById('masterUploadBtn');
            const exBtn = document.getElementById('masterExportBtn');
            if (upBtn) upBtn.addEventListener('click', uploadMasterFile);
            if (exBtn) exBtn.addEventListener('click', exportMasterAudio);
            document.querySelectorAll('.presetBtn').forEach((btn) => {
                btn.addEventListener('click', () => requestPreview(btn.getAttribute('data-mode') || 'rock'));
            });
            updateModeButtons();
            updateMixButtons();
        });

       async function analisarMusicaIA() {
    const jobId = document.getElementById('jobIdField')?.value || masterJobId;
    if (!jobId) {
        alert("Por favor, faça o upload de um áudio primeiro!");
        return;
    }

    const btn = document.getElementById('btnIaAnalise');
    const statusText = document.getElementById('iaStatusText');
    const badge = document.getElementById('badgeIaDetectado');

    const originalHTML = btn.innerHTML;
    btn.innerHTML = '<span>🧠</span> Analisando Timbre Vocais e Espectro...';
    btn.disabled = true;
    statusText.textContent = "A IA está escutando as frequências e calculando a tessitura vocal...";

    try {
        const response = await fetch(`/masterizacao/analise_ia/${jobId}`);
        const data = await response.json();
        if(data.histograma){

            atualizarHistograma(
                data.histograma,
                data.diagnostico || []
            );

        }

        if(data.scores){

            document.getElementById('mixScore').textContent =
                data.scores.mix_score + "/100";

            document.getElementById('masterScore').textContent =
                data.scores.master_score + "/100";

            document.getElementById('spotifyScore').textContent =
                data.scores.spotify_score + "/100";
        }

        if (!response.ok) throw new Error(data.error || "Erro na análise de IA");

        let labelFinal = `🎯 Estilo: ${data.genero_label}`;
        if (data.vocal_info) {
            labelFinal += ` | 🎤 Voz: ${data.vocal_info.genero_voz} (${data.vocal_info.classificacao} a ~${data.vocal_info.f0_media_hz} Hz)`;
        }

        badge.style.display = 'block';
        badge.textContent = labelFinal;
        statusText.textContent = `Preset [${data.preset_aplicado.toUpperCase()}] injetado automaticamente!`;

        if (typeof requestPreview === 'function') {
            await requestPreview(data.preset_aplicado, true);
        }

    } catch (e) {
        alert("Erro na análise inteligente: " + e.message);
        statusText.textContent = "Falha ao analisar vocal.";
    } finally {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
    }
}

      let   modoEspectroAtivo = 'bars';
let waterfallCanvasAux = null;
let peakHoldArray = null;

function mudarModoEspectro(modo) {
    modoEspectroAtivo = modo;

    const selectMode = document.getElementById('settingSelectMode');
    if (selectMode) selectMode.value = modo;

    const botoes = document.querySelectorAll('[onclick^="mudarModoEspectro"]');
    botoes.forEach(btn => {
        btn.classList.toggle('is-on', btn.getAttribute('onclick').includes(modo));
    });
}

function atualizarInformacoesFFT() {
    const analyser = masterEqState.analyser;
    const hzBadge = document.getElementById('hzBinBadge');
    const fftSelect = document.getElementById('settingFftSize');

    if (!hzBadge || !fftSelect) return;

    const sampleRate = (masterEqState.context) ? masterEqState.context.sampleRate : 44100;
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

            if (masterEqState.analyser) {
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
    document.getElementById('lblPitchNota').textContent = "--";
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

function startSpectrum(){
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
            const analyser = masterEqState.analyser;
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

    function draw(){
        requestAnimationFrame(draw);
        const analyser = masterEqState.analyser;
        const audioPlayer = document.getElementById("masterAudio");

        if(!analyser || !audioPlayer) {
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
        }

        else if (modoEspectroAtivo === 'line') {
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
        }

        else if (modoEspectroAtivo === 'spectrogram') {
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
        }

        else if (modoEspectroAtivo === 'waterfall') {
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
        function startLufsMeter(){
            function update(){
                const now = performance.now();
                if(now - lastMeterUpdate < 250){
                    requestAnimationFrame(update);
                    return;
                }
                lastMeterUpdate = now;
                requestAnimationFrame(update);

                const analyser = masterEqState.analyser;
                if(!analyser) return;
                const data = new Float32Array(analyser.fftSize);
                analyser.getFloatTimeDomainData(data);

                let sum = 0;
                let peak = 0;
                for(let i=0;i<data.length;i++){
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

        function bindMasterVolume(){
            const slider = document.getElementById('masterVolume');
            const value = document.getElementById('masterVolumeValue');
            if(!slider || !value) return;

            slider.addEventListener('input', () => {
                const pct = Number(slider.value);
                value.textContent = pct + '%';
                if(masterEqState.gainNode){
                    masterEqState.gainNode.gain.value = pct / 100;
                }
                if(masterStemState.masterGain){
                    masterStemState.masterGain.gain.value = pct / 100;
                }
            });
        }   
        document.addEventListener("DOMContentLoaded", () => {
                const audioPlayer = document.getElementById("masterAudio");
                const btnA = document.getElementById("abBtnA");
                const btnB = document.getElementById("abBtnB");
                const modeBadge = document.getElementById("masterModeBadge");
                
                window.masterTrackUrls = { original: "", mastered: "" };

                const originalXHR = window.XMLHttpRequest;
                function FilteredXHR() {
                    const xhr = new originalXHR();
                    xhr.addEventListener("readystatechange", function() {
                        if (xhr.readyState === 4 && xhr.status === 200) {
                            const urlChamada = xhr._url || "";
                            
                            if (urlChamada.includes("/masterizacao/upload")) {
                                try {
                                    const data = JSON.parse(xhr.responseText);
                                    if (data.job_id && data.ext) {
                                        window.masterTrackUrls.original = `/masterizacao/audio/${data.job_id}${data.ext.toLowerCase()}`;
                                        window.masterTrackUrls.mastered = "";
                                        btnB.setAttribute("disabled", "true");
                                        
                                        switchAudioSource("original");
                                    }
                                } catch(e) { console.error("Erro ao ler upload via XHR:", e); }
                            }
                            
                            if (urlChamada.includes("/masterizacao/preview")) {
                                try {
                                    const data = JSON.parse(xhr.responseText);
                                    if (data.download_url) {
                                        window.masterTrackUrls.mastered = data.download_url;
                                        btnB.removeAttribute("disabled");
                                        
                                        if (btnB.classList.contains("active")) {
                                            switchAudioSource("mastered");
                                        }
                                    }
                                } catch(e) { console.error("Erro ao ler preview via XHR:", e); }
                            }
                        }
                    });
                    
                    const originalOpen = xhr.open;
                    xhr.open = function(method, url, ...args) {
                        xhr._url = url;
                        return originalOpen.apply(xhr, [method, url, ...args]);
                    };
                    
                    return xhr;
                }
                window.XMLHttpRequest = FilteredXHR;

                function switchAudioSource(target) {
                    const url = window.masterTrackUrls[target];
                    if (!url) return;

                    const currentTime = audioPlayer.currentTime;
                    const isPlaying = !audioPlayer.paused;

                    audioPlayer.src = url;
                    audioPlayer.load();
                    audioPlayer.currentTime = currentTime;

                    if (isPlaying) {
                        audioPlayer.play().catch(() => {});
                    }

                    if (target === "original") {
                        btnA.classList.add("active");
                        btnB.classList.remove("active");
                        if(modeBadge) {
                            modeBadge.textContent = "Original (Bypass)";
                            modeBadge.style.background = "rgba(245, 158, 11, 0.2)";
                        }
                    } else {
                        btnB.classList.add("active");
                        btnA.classList.remove("active");
                        if(modeBadge) {
                            modeBadge.textContent = "Masterizado (A/B Ativo)";
                            modeBadge.style.background = "rgba(57, 215, 230, 0.2)";
                        }
                    }
                }

                btnA.addEventListener("click", () => switchAudioSource("original"));
                btnB.addEventListener("click", () => switchAudioSource("mastered"));
            });