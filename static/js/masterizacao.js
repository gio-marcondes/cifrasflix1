let histogramaChart = null;
        let masterJobId = '';
        let masterOriginalUrl = '';
        let masterActiveMode = 'original';
        const masterPreviewCache = {};
        let masterCompression = 'media';
        let masterVoicePosition = 'central';
        let masterNoDrums = false;
        const masterEqFreqs = [31, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000];
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
        };

        async function separarStems(){
                const progContainer =
                    document.getElementById('masterProgressContainer');

                const progBar =
                    document.getElementById('masterProgressBar');

                if(progContainer && progBar){

                    progContainer.style.display = 'block';

                    progBar.style.width = '0%';

                    setTimeout(
                        ()=> progBar.style.width = '20%',
                        200
                    );

                    setTimeout(
                        ()=> progBar.style.width = '45%',
                        1200
                    );

                    setTimeout(
                        ()=> progBar.style.width = '70%',
                        2500
                    );

                    setTimeout(
                        ()=> progBar.style.width = '90%',
                        5000
                    );
                }
            if(!arquivoAtual){

                alert("Selecione um áudio");
                return;
            }

            const fd = new FormData();

            fd.append(
                "arquivo",
                arquivoAtual
            );

            const r = await fetch(
                "/api/separar-stems",
                {
                    method:"POST",
                    body:fd
                }
            );

            const data = await r.json();

            acompanharStems(
                data.job_id
            );
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
                    if (progBar) {
                        progBar.style.width =
                            (data.progresso || 0) + '%';
                    }

                    if(
                        data.status ===
                        "completed"
                    ){
                        if(progBar){
                                progBar.style.width = '100%';
                            }

                            setTimeout(()=>{

                                if(progContainer){

                                    progContainer.style.display = 'none';

                                }

                            },800);
                        clearInterval(timer);

                        renderizarStems(
                            data.resultado
                        );
                    }

                    if(
                        data.status ===
                        "failed"
                    ){

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

        function ensureStemAudioContext(){
            if (!masterStemState.context) {
                const Ctx = window.AudioContext || window.webkitAudioContext;
                masterStemState.context = new Ctx();
                masterStemState.masterGain = masterStemState.context.createGain();
                const volume = Number(document.getElementById('masterVolume')?.value || 100) / 100;
                masterStemState.masterGain.gain.value = volume;
                masterStemState.masterGain.connect(masterStemState.context.destination);
            }
            if (masterStemState.context.state === 'suspended') {
                masterStemState.context.resume().catch(() => {});
            }
        }

        function destruirMixerStems(){
            pausarTodasStems();
            masterStemState.tracks.forEach((track) => {
                try { track.player.pause(); } catch(e) {}
                try { track.sourceNode.disconnect(); } catch(e) {}
                try { track.gainNode.disconnect(); } catch(e) {}
                try { track.pannerNode?.disconnect(); } catch(e) {}
            });
            masterStemState.tracks = [];
        }

        function criarLinhaStem(faixa, index){
            const row = document.createElement('div');
            row.className = `stem-row${index === 0 ? ' active' : ''}`;
            row.dataset.src = faixa.url || '';
            row.dataset.title = normalizarNomeStem(faixa);
            row.dataset.file = faixa.nome || '';
            row.innerHTML = `
                <div class="stem-meta">
                    <p class="stem-name"></p>
                    <div class="stem-controls">
                        <button class="stem-toggle stem-mute" type="button" title="Mute">M</button>
                        <button class="stem-toggle stem-solo" type="button" title="Solo">S</button>
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
                    <div class="stem-wave-wrap">
                        <canvas class="stem-wave"></canvas>
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

        function atualizarPlayheadStems(){
            const audio = document.getElementById('masterAudio');
            const playhead = document.getElementById('masterStemPlayhead');
            if (!audio || !playhead) return;
            const total = Number(audio.duration || 0);
            const pct = total > 0 ? Math.max(0, Math.min(100, (Number(audio.currentTime || 0) / total) * 100)) : 0;
            playhead.style.setProperty('--playhead-pct', `${pct}%`);
        }

        function sincronizarStemsComMaster(forcar = false){
            const audio = document.getElementById('masterAudio');
            if (!audio || masterStemState.syncing) return;
            const tempo = Number(audio.currentTime || 0);
            masterStemState.tracks.forEach(({ player }) => {
                try {
                    if (forcar || Math.abs(Number(player.currentTime || 0) - tempo) > .08) {
                        player.currentTime = tempo;
                    }
                } catch(e) {}
            });
            atualizarPlayheadStems();
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

        function conectarEventosStem(row, track){
            const mute = row.querySelector('.stem-mute');
            const solo = row.querySelector('.stem-solo');
            const waveHit = row.querySelector('.stem-wave-hit');
            const volume = row.querySelector('.stem-volume');
            const volOut = row.querySelector('.stem-volume-value');
            const panKnob = row.querySelector('.stem-pan-knob');
            const panOut = row.querySelector('.stem-pan-value');

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
                waveHit.addEventListener('click', (event) => {
                    const audio = document.getElementById('masterAudio');
                    const wrap = waveHit.querySelector('.stem-wave-wrap');
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
            }
            atualizarPan(0);
        }

        function montarMixerStems(faixas){
            const grid = document.getElementById('masterStemGrid');
            const badge = document.getElementById('stemsCountBadge');
            if (!grid) return;
            destruirMixerStems();
            grid.querySelectorAll('.stem-row').forEach((row) => row.remove());
            ensureStemAudioContext();

            const playheadHit = document.getElementById('masterStemPlayheadHit');
            faixas.forEach((faixa, index) => {
                if (!faixa.url) return;
                const row = criarLinhaStem(faixa, index);
                grid.insertBefore(row, playheadHit || null);
                const player = new Audio(faixa.url);
                player.preload = 'auto';
                player.crossOrigin = 'anonymous';
                player.loop = false;
                player.preservesPitch = false;

                const sourceNode = masterStemState.context.createMediaElementSource(player);
                const gainNode = masterStemState.context.createGain();
                const pannerNode = typeof masterStemState.context.createStereoPanner === 'function'
                    ? masterStemState.context.createStereoPanner()
                    : null;
                if (pannerNode) {
                    sourceNode.connect(pannerNode);
                    pannerNode.connect(gainNode);
                } else {
                    sourceNode.connect(gainNode);
                }
                gainNode.connect(masterStemState.masterGain);
                const track = {
                    row,
                    player,
                    sourceNode,
                    gainNode,
                    pannerNode,
                    volume: row.querySelector('.stem-volume'),
                    panValue: 0,
                };
                masterStemState.tracks.push(track);
                conectarEventosStem(row, track);
            });

            if (badge) badge.textContent = `${masterStemState.tracks.length} faixas`;
            aplicarEstadosMixerStems();
            renderizarWaveformsMaster();
            sincronizarStemsComMaster(true);
        }

        function bindStemMasterSync(){
            const audio = document.getElementById('masterAudio');
            const grid = document.getElementById('masterStemGrid');
            const playheadHit = document.getElementById('masterStemPlayheadHit');
            if (!audio) return;

            audio.addEventListener('play', () => {
                if (masterStemState.tracks.length) tocarTodasStems();
            });
            audio.addEventListener('pause', () => {
                pausarTodasStems();
                audio.muted = false;
            });
            audio.addEventListener('seeked', () => sincronizarStemsComMaster(true));
            audio.addEventListener('timeupdate', () => {
                sincronizarStemsComMaster(false);
                atualizarPlayheadStems();
            });
            audio.addEventListener('ended', () => {
                pausarTodasStems();
                audio.muted = false;
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

        function renderizarStems(resultado) {
                const area = document.getElementById("stemsArea");
                if (!area) return;
                area.style.display = "block"; // Exibe a div

                const faixas = resultado && Array.isArray(resultado.faixas)
                    ? resultado.faixas
                    : [];

                if (!faixas.length) {
                    setMasterStatus('Stems processados, mas nenhuma faixa foi encontrada.');
                    return;
                }

                montarMixerStems(faixas);
                setMasterStatus('Stems extraidos e carregados.');
            }
        function atualizarHistograma(histograma, diagnostico){

            document.getElementById('histograma-container').style.display = 'block';

            document.getElementById('gravePct').textContent =
                histograma.graves + "%";

            document.getElementById('medioPct').textContent =
                histograma.medios + "%";

            document.getElementById('agudoPct').textContent =
                histograma.agudos + "%";

           
                        document.getElementById('diagnosticoIA').innerHTML =
                diagnostico.map(item =>
                    `<div>• ${item}</div>`
                ).join('');
        }

document
.getElementById('btnSepararStems')
.addEventListener('click', separarStems);

masterFile.addEventListener('change', e => {

    arquivoAtual = e.target.files[0];

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
async function detectarTomEPitch() {
    const jobId = document.getElementById('jobIdField')?.value || masterJobId;
    if (!jobId) { 
        alert("Por favor, faça o upload de um áudio primeiro!"); 
        return; 
    }

    const btn = document.getElementById('btnDetectarTom');
    const painel = document.getElementById('panelResultadosTom');
    const lblTom = document.getElementById('lblTomDetectado');
    const lblBpm = document.getElementById('lblBpmDetectado');
    const lblCamelot = document.getElementById('lblCamelotDetectado');

    const originalHTML = btn.innerHTML;
    btn.innerHTML = '<span>⏳</span> Analisando transientes e harmônicos...';
    btn.disabled = true;

    try {
        const response = await fetch(`/masterizacao/detectar_tom/${jobId}`);
        const data = await response.json();

        if (!response.ok) throw new Error(data.error || "Erro ao processar análise tonal");

        // Alimenta os cards com o retorno do servidor
        lblTom.textContent = data.tom;
        lblBpm.textContent = Math.round(data.bpm) + " BPM";
        lblCamelot.textContent = data.camelot;
        document.getElementById('lblTonsSemelhantes').innerHTML = data.tons_semelhantes.join('<br>');
        document.getElementById('lblAcordesPossiveis').textContent = data.acordes.join('  •  ');
        // Exibe o painel de resultados de forma elegante
        painel.style.display = 'block';

    } catch (e) {
        alert("Erro na detecção harmônica: " + e.message);
    } finally {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
    }
}
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
                // Força o envio como string "true" ou "false" para alinhar com o validador do Python
                return {
                    compression: masterCompression,
                    vocal_position: masterVoicePosition,
                    no_drums: masterNoDrums ? "true" : "false", 
                };
            }


        function buildPreviewKey(mode){
            // Cria uma chave única baseada nas escolhas do usuário
            return [mode, masterCompression, masterVoicePosition, masterNoDrums ? 'sem_bateria' : 'com_bateria'].join('|');
        }

        function connectEqGraph(){
            if (!masterEqState.source || !masterEqState.context) return;

            try { masterEqState.source.disconnect(); } catch(e){}
            try { masterEqState.analyser.disconnect(); } catch(e){}
            try { masterEqState.gainNode.disconnect(); } catch(e){}
            masterEqState.filters.forEach(f=>{ try{ f.disconnect(); }catch(e){} });

            if(!masterEqState.enabled || !masterEqState.filters.length){
                masterEqState.source.connect(masterEqState.gainNode);
                masterEqState.gainNode.connect(masterEqState.analyser);
                masterEqState.analyser.connect(masterEqState.context.destination);
                return;
            }

            masterEqState.source.connect(masterEqState.filters[0]);
            for(let i = 0; i < masterEqState.filters.length - 1; i++){
                masterEqState.filters[i].connect(masterEqState.filters[i + 1]);
            }
            masterEqState.filters[masterEqState.filters.length - 1].connect(masterEqState.gainNode);
            masterEqState.gainNode.connect(masterEqState.analyser);
            masterEqState.analyser.connect(masterEqState.context.destination);
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
        // Remove ouvintes antigos para evitar duplicação de cliques
        drumBtn.replaceWith(drumBtn.cloneNode(true));
        
        // Readiciona o evento correto
        const novoDrumBtn = document.getElementById('noDrumsBtn');
        novoDrumBtn.addEventListener('click', () => {
            masterNoDrums = !masterNoDrums; // Inverte o estado real
            updateMixButtons();             // Atualiza a classe 'is-on' no CSS
            requestPreview(masterActiveMode || 'original', true); // Força o Python a reprocessar
        });
    }
}

        async function ensureEqAudioGraph(){
            const audio = document.getElementById('masterAudio');
            if (!audio) return;

            if (!masterEqState.context) {
                const Ctx = window.AudioContext || window.webkitAudioContext;
                const context = new Ctx();
                const source = context.createMediaElementSource(audio);
                const analyser = context.createAnalyser();
                const gainNode = context.createGain();

                gainNode.gain.value = 1.0;
                analyser.fftSize = 512; // Configurado para uma ótima resolução de espectro
                analyser.smoothingTimeConstant = 0.75;
                masterEqState.gainNode = gainNode;  
                const filters = masterEqFreqs.map((freq) => {
                    const f = context.createBiquadFilter();
                    f.type = 'peaking';
                    f.frequency.value = freq;
                    f.Q.value = 1;
                    f.gain.value = 0;
                    return f;
                });

                masterEqState.context = context;
                masterEqState.source = source;
                masterEqState.filters = filters;
                masterEqState.analyser = analyser;
                connectEqGraph();
            }

            if (masterEqState.context && masterEqState.context.state === 'suspended') {
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

            // --- INÍCIO DO LOADING E SPINNER ---
            setMasterStatus('Processando preview...');
            
            // Encontra o botão do preset clicado para colocar o spinner nele
            const btnClicado = document.querySelector(`.presetBtn[data-mode="${mode}"]`);
            let originalTexto = "";
            if (btnClicado) {
                originalTexto = btnClicado.innerHTML;
                btnClicado.innerHTML = `<div class="spinner"></div> Processando...`;
                document.querySelectorAll('.presetBtn').forEach(b => b.disabled = true);
            }

            // Ativa e anima a barra de progresso de forma preditiva (3 a 5 segundos)
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

                // Finaliza a barra em 100% antes de sumir
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
                // --- RESTAURA O ESTADO DOS BOTÕES ---
                if (btnClicado) {
                    btnClicado.innerHTML = originalTexto;
                }
                document.querySelectorAll('.presetBtn').forEach(b => b.disabled = false);
                updateModeButtons(); // Garante o realce do botão ativo
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

        // Monta o texto de feedback incluindo os dados do cantor se existirem
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
    const analyser = masterEqState.analyser;
    const hzBadge = document.getElementById('hzBinBadge');
    const fftSelect = document.getElementById('settingFftSize');
    
    if (!hzBadge || !fftSelect) return;

    // Se o áudio já iniciou o context, calcula baseado no sampleRate real (ex: 44100 ou 48000)
    // Se não, assume o padrão comercial de 44100 para exibição prévia
    const sampleRate = (masterEqState.context) ? masterEqState.context.sampleRate : 44100;
    const currentFftSize = parseInt(fftSelect.value);

    // Fórmula idêntica à do print: Sample Rate / Tamanho da FFT
    const hzPerBin = sampleRate / currentFftSize;
    
    hzBadge.textContent = hzPerBin.toFixed(1) + ' Hz/bin';

    // Aplica as configurações em tempo real se o nó analyser já existir
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
let lastPitchUpdateTime = 0;    // Controla o tempo para o Throttling
let notaEstavelAtual = "";       // Guarda a nota que está travada no ecrã
let historicoNotas = [];         // Buffer para votação de estabilidade

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

    // Configurações de Grade Estática
    const dbLines = [0, -20, -40, -60, -80];
    const freqLinesLog = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000];

    // Função interna para desenhar o fundo estático (Grid Logarítmico)
    function drawGrid() {
        ctx.lineWidth = 1;
        ctx.font = '10px monospace';

        // 1. Linhas Horizontais (Nível em dB)
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

        // 2. Linhas Verticais (Frequências em Hz Logarítmicas)
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

    // --- LÓGICA DE DETECÇÃO DO MOUSE (TOOLTIP) ---
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

        // --- MOTOR DE DETECÇÃO DE PITCH COM FILTRO DE VELOCIDADE (PIANO) ---
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

        // --- VARIÁVEIS DO ESCOPO DO ESPETRO (CORRIGIDO) ---
        const graphWidth = canvas.width - 50;
        const logMin = Math.log10(20);
        const logMax = Math.log10(20000);
        const sampleRate = masterEqState.context.sampleRate;

        // Inicializa ou redimensiona o array de picos de forma segura
        if (!peakHoldArray || peakHoldArray.length !== 60) {
            peakHoldArray = new Float32Array(60).fill(0);
        }

        // --- MODO 1: BARRAS FFT LOGARÍTMICO ---
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
        
        // --- MODO 2: LINHA DE FREQUÊNCIA ---
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

        // --- MODO 3: ESPECTROGRAMA COLORIDO LOGARÍTMICO ---
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

        // --- MODO 4: WATERFALL CACHOEIRA ---
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

// Função auxiliar de contagem para o Peak Hold Array
function totalBarsCalculated(mode) {
    if (mode === 'spectrogram') return 55;
    return 45; // Bars standard
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
                
                // Links dinâmicos reais estruturados
                window.masterTrackUrls = { original: "", mastered: "" };

                // Interceptador para XMLHttpRequest (Usado pelo seu front-end original)
                const originalXHR = window.XMLHttpRequest;
                function FilteredXHR() {
                    const xhr = new originalXHR();
                    xhr.addEventListener("readystatechange", function() {
                        if (xhr.readyState === 4 && xhr.status === 200) {
                            const urlChamada = xhr._url || "";
                            
                            // 1. Captura quando o upload do arquivo original finaliza
                            if (urlChamada.includes("/masterizacao/upload")) {
                                try {
                                    const data = JSON.parse(xhr.responseText);
                                    if (data.job_id && data.ext) {
                                        window.masterTrackUrls.original = `/masterizacao/audio/${data.job_id}${data.ext.toLowerCase()}`;
                                        window.masterTrackUrls.mastered = ""; // Reseta a masterização anterior
                                        btnB.setAttribute("disabled", "true");
                                        
                                        // Ativa o botão A por padrão e carrega o áudio original
                                        switchAudioSource("original");
                                    }
                                } catch(e) { console.error("Erro ao ler upload via XHR:", e); }
                            }
                            
                            // 2. Captura quando um preview/preset masterizado termina de processar
                            if (urlChamada.includes("/masterizacao/preview")) {
                                try {
                                    const data = JSON.parse(xhr.responseText);
                                    if (data.download_url) {
                                        window.masterTrackUrls.mastered = data.download_url;
                                        btnB.removeAttribute("disabled"); // Ativa o botão [B] Masterizado!
                                        
                                        // Se o utilizador já tiver clicado no [B], atualiza o som na hora
                                        if (btnB.classList.contains("active")) {
                                            switchAudioSource("mastered");
                                        }
                                    }
                                } catch(e) { console.error("Erro ao ler preview via XHR:", e); }
                            }
                        }
                    });
                    
                    // Guarda a URL chamada para sabermos qual rota respondeu
                    const originalOpen = xhr.open;
                    xhr.open = function(method, url, ...args) {
                        xhr._url = url;
                        return originalOpen.apply(xhr, [method, url, ...args]);
                    };
                    
                    return xhr;
                }
                window.XMLHttpRequest = FilteredXHR;

                // Função central que gerencia a troca de áudio mantendo o currentTime idêntico
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
