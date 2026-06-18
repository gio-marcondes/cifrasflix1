// ==========================================
// MÓDULO DE EXPORTAÇÃO DE ÁUDIO
// ==========================================

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

        setUint32(0x46464952); // "RIFF"
        setUint32(length - 8); // file length - 8
        setUint32(0x45564157); // "WAVE"
        setUint32(0x20746d66); // "fmt " chunk
        setUint32(16); // length = 16
        setUint16(1); // PCM (uncompressed)
        setUint16(numOfChan);
        setUint32(buffer.sampleRate);
        setUint32(buffer.sampleRate * 2 * numOfChan); // avg. bytes/sec
        setUint16(numOfChan * 2); // block-align
        setUint16(16); // 16-bit

        setUint32(0x61746164); // "data" - chunk
        setUint32(length - pos - 4); // chunk length

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