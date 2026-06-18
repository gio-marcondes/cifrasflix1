// ==========================================
// MÓDULO RACK DE EFEITOS (STEMS FX)
// ==========================================

const stemFxCatalog = [
    ['eq', 'EQ'],
    ['compressor', 'Compressor'],
    ['gate', 'Gate'],
    ['saturation', 'Saturacao'],
    ['limiter', 'Limiter'],
    ['deesser', 'De-esser'],
    ['filter', 'Filtros'],
    ['reverb', 'Reverb'],
    ['delay', 'Delay'],
    ['chorus', 'Chorus'],
    ['tremolo', 'Tremolo'],
    ['autopan', 'Auto-pan'],
];

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

    const nodes = { input, output, highpass, lowpass, deesser, gateNode, saturationInput, saturationDry, saturationShaper, saturationWet, saturationOutput, compressor, limiter, tremoloGain, tremoloLfo, tremoloDepth, chorusInput, chorusDry, chorusDelay, chorusWet, chorusOutput, chorusLfo, chorusDepth, autopanLfo, autopanDepth, delaySend, delayNode, delayFeedback, delayReturn, reverbSend, reverbNode, reverbReturn };
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

    // ... Todos os bindings dos outros efeitos continuam aqui do mesmo jeito (Tremolo, Chorus, Delay, etc).
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