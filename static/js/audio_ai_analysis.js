// ==========================================
// MÓDULO DE INTELIGÊNCIA ARTIFICIAL E PITCH
// ==========================================

function atualizarHistograma(histograma, diagnostico) {
    const container = document.getElementById('histograma-container');
    if (container) container.style.display = 'block';

    const gravePct = document.getElementById('gravePct');
    if (gravePct) gravePct.textContent = histograma.graves + "%";

    const medioPct = document.getElementById('medioPct');
    if (medioPct) medioPct.textContent = histograma.medios + "%";

    const agudoPct = document.getElementById('agudoPct');
    if (agudoPct) agudoPct.textContent = histograma.agudos + "%";

    const diagEl = document.getElementById('diagnosticoIA');
    if (diagEl) {
        diagEl.innerHTML = diagnostico.map(item => `<div>• ${item}</div>`).join('');
    }
}

async function detectarTomEPitch() {
    const jobId = document.getElementById('jobIdField')?.value || (typeof masterJobId !== 'undefined' ? masterJobId : '');
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

        lblTom.textContent = data.tom;
        lblBpm.textContent = Math.round(data.bpm) + " BPM";
        lblCamelot.textContent = data.camelot;
        document.getElementById('lblTonsSemelhantes').innerHTML = data.tons_semelhantes.join('<br>');
        document.getElementById('lblAcordesPossiveis').textContent = data.acordes.join('  •  ');
        painel.style.display = 'block';
    } catch (e) {
        alert("Erro na detecção harmônica: " + e.message);
    } finally {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
    }
}

async function analisarMusicaIA() {
    const jobId = document.getElementById('jobIdField')?.value || (typeof masterJobId !== 'undefined' ? masterJobId : '');
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
    if (statusText) statusText.textContent = "A IA está escutando as frequências e calculando a tessitura vocal...";

    try {
        const response = await fetch(`/masterizacao/analise_ia/${jobId}`);
        const data = await response.json();
        
        if(data.histograma){
            atualizarHistograma(data.histograma, data.diagnostico || []);
        }

        if(data.scores){
            const mixSc = document.getElementById('mixScore');
            if (mixSc) mixSc.textContent = data.scores.mix_score + "/100";
            const mastSc = document.getElementById('masterScore');
            if (mastSc) mastSc.textContent = data.scores.master_score + "/100";
            const spotSc = document.getElementById('spotifyScore');
            if (spotSc) spotSc.textContent = data.scores.spotify_score + "/100";
        }

        if (!response.ok) throw new Error(data.error || "Erro na análise de IA");

        let labelFinal = `🎯 Estilo: ${data.genero_label}`;
        if (data.vocal_info) {
            labelFinal += ` | 🎤 Voz: ${data.vocal_info.genero_voz} (${data.vocal_info.classificacao} a ~${data.vocal_info.f0_media_hz} Hz)`;
        }

        if (badge) {
            badge.style.display = 'block';
            badge.textContent = labelFinal;
        }
        if (statusText) statusText.textContent = `Preset [${data.preset_aplicado.toUpperCase()}] injetado automaticamente!`;

        if (typeof requestPreview === 'function') {
            await requestPreview(data.preset_aplicado, true);
        }

    } catch (e) {
        alert("Erro na análise inteligente: " + e.message);
        if (statusText) statusText.textContent = "Falha ao analisar vocal.";
    } finally {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
    }
}