const chordShapes = {
    // C chords
    "C": [
        { frets: [null, 3, 2, 0, 1, 0], fingers: [0, 3, 2, 0, 1, 0] },
        { frets: [null, 3, 5, 5, 5, 3], fingers: [0, 1, 2, 3, 4, 1], barre: 3 },
        { frets: [8, 10, 10, 9, 8, 8], fingers: [1, 3, 4, 2, 1, 1], barre: 8 }
    ],
    "Cm": [
        { frets: [null, 3, 5, 5, 4, 3], fingers: [0, 1, 3, 4, 2, 1], barre: 3 },
        { frets: [8, 10, 10, 8, 8, 8], fingers: [1, 3, 4, 1, 1, 1], barre: 8 }
    ],
    "C7": [
        { frets: [null, 3, 2, 3, 1, 0], fingers: [0, 3, 2, 4, 1, 0] },
        { frets: [null, 3, 5, 3, 5, 3], fingers: [0, 1, 3, 1, 4, 1], barre: 3 }
    ],
    "Cmaj7": [
        { frets: [null, 3, 2, 0, 0, 0], fingers: [0, 3, 2, 0, 0, 0] },
        { frets: [null, 3, 5, 4, 5, 3], fingers: [0, 1, 3, 2, 4, 1], barre: 3 }
    ],
    "C9": [
        { frets: [null, 3, 2, 3, 3, null], fingers: [0, 2, 1, 3, 4, 0] }
    ],
    "Csus4": [
        { frets: [null, 3, 3, 0, 1, 1], fingers: [0, 3, 4, 0, 1, 1] }
    ],
    "C5": [
        { frets: [null, 3, 5, 5, null, null] }
    ],
    
    // C# / Db
    "C#": [
        { frets: [null, 4, 6, 6, 6, 4], fingers: [0, 1, 2, 3, 4, 1], barre: 4 },
        { frets: [9, 11, 11, 10, 9, 9], fingers: [1, 3, 4, 2, 1, 1], barre: 9 }
    ],
    "C#m": [
        { frets: [null, 4, 6, 6, 5, 4], fingers: [0, 1, 3, 4, 2, 1], barre: 4 },
        { frets: [9, 11, 11, 9, 9, 9], fingers: [1, 3, 4, 1, 1, 1], barre: 9 }
    ],
    "C#7": [
        { frets: [null, 4, 6, 4, 6, 4], fingers: [0, 1, 3, 1, 4, 1], barre: 4 }
    ],
    "C#maj7": [
        { frets: [null, 4, 6, 5, 6, 4], fingers: [0, 1, 3, 2, 4, 1], barre: 4 }
    ],
    "Db": [
        { frets: [null, 4, 6, 6, 6, 4], fingers: [0, 1, 2, 3, 4, 1], barre: 4 }
    ],
    "Dbm": [
        { frets: [null, 4, 6, 6, 5, 4], fingers: [0, 1, 3, 4, 2, 1], barre: 4 }
    ],
    
    // D chords
    "D": [
        { frets: [null, null, 0, 2, 3, 2], fingers: [0, 0, 0, 1, 3, 2] },
        { frets: [null, 5, 7, 7, 7, 5], fingers: [0, 1, 2, 3, 4, 1], barre: 5 },
        { frets: [10, 12, 12, 11, 10, 10], fingers: [1, 3, 4, 2, 1, 1], barre: 10 }
    ],
    "Dm": [
        { frets: [null, null, 0, 2, 3, 1], fingers: [0, 0, 0, 2, 3, 1] },
        { frets: [null, 5, 7, 7, 6, 5], fingers: [0, 1, 3, 4, 2, 1], barre: 5 }
    ],
    "D7": [
        { frets: [null, null, 0, 2, 1, 2], fingers: [0, 0, 0, 2, 1, 3] },
        { frets: [null, 5, 7, 5, 7, 5], fingers: [0, 1, 3, 1, 4, 1], barre: 5 }
    ],
    "Dmaj7": [
        { frets: [null, null, 0, 2, 2, 2], fingers: [0, 0, 0, 1, 1, 1], barre: 2 },
        { frets: [null, 5, 7, 6, 7, 5], fingers: [0, 1, 3, 2, 4, 1], barre: 5 }
    ],
    "Dsus4": [
        { frets: [null, null, 0, 2, 3, 3], fingers: [0, 0, 0, 1, 3, 4] }
    ],
    "Dsus2": [
        { frets: [null, null, 0, 2, 3, 0], fingers: [0, 0, 0, 1, 2, 0] }
    ],
    
    // D# / Eb
    "D#": [
        { frets: [null, 6, 8, 8, 8, 6], fingers: [0, 1, 2, 3, 4, 1], barre: 6 }
    ],
    "D#m": [
        { frets: [null, 6, 8, 8, 7, 6], fingers: [0, 1, 3, 4, 2, 1], barre: 6 }
    ],
    "Eb": [
        { frets: [null, 6, 8, 8, 8, 6], fingers: [0, 1, 2, 3, 4, 1], barre: 6 }
    ],
    "Ebm": [
        { frets: [null, 6, 8, 8, 7, 6], fingers: [0, 1, 3, 4, 2, 1], barre: 6 }
    ],
    
    // E chords
    "E": [
        { frets: [0, 2, 2, 1, 0, 0], fingers: [0, 2, 3, 1, 0, 0] },
        { frets: [null, 7, 9, 9, 9, 7], fingers: [0, 1, 2, 3, 4, 1], barre: 7 },
        { frets: [12, 14, 14, 13, 12, 12], fingers: [1, 3, 4, 2, 1, 1], barre: 12 }
    ],
    "Em": [
        { frets: [0, 2, 2, 0, 0, 0], fingers: [0, 2, 3, 0, 0, 0] },
        { frets: [null, 7, 9, 9, 8, 7], fingers: [0, 1, 3, 4, 2, 1], barre: 7 }
    ],
    "E7": [
        { frets: [0, 2, 0, 1, 0, 0], fingers: [0, 2, 0, 1, 0, 0] },
        { frets: [null, 7, 9, 7, 9, 7], fingers: [0, 1, 3, 1, 4, 1], barre: 7 }
    ],
    "Emaj7": [
        { frets: [0, 2, 1, 1, 0, 0], fingers: [0, 3, 1, 2, 0, 0] }
    ],
    "Esus4": [
        { frets: [0, 2, 2, 2, 0, 0], fingers: [0, 2, 3, 4, 0, 0] }
    ],
    
    // F chords
    "F": [
        { frets: [1, 3, 3, 2, 1, 1], fingers: [1, 3, 4, 2, 1, 1], barre: 1 },
        { frets: [null, 8, 10, 10, 10, 8], fingers: [0, 1, 2, 3, 4, 1], barre: 8 }
    ],
    "Fm": [
        { frets: [1, 3, 3, 1, 1, 1], fingers: [1, 3, 4, 1, 1, 1], barre: 1 },
        { frets: [null, 8, 10, 10, 9, 8], fingers: [0, 1, 3, 4, 2, 1], barre: 8 }
    ],
    "F7": [
        { frets: [1, 3, 1, 2, 1, 1], fingers: [1, 3, 1, 2, 1, 1], barre: 1 }
    ],
    "Fmaj7": [
        { frets: [null, 3, 3, 2, 1, 0], fingers: [0, 3, 4, 2, 1, 0] }
    ],
    
    // F# / Gb
    "F#": [
        { frets: [2, 4, 4, 3, 2, 2], fingers: [1, 3, 4, 2, 1, 1], barre: 2 },
        { frets: [null, 9, 11, 11, 11, 9], fingers: [0, 1, 2, 3, 4, 1], barre: 9 }
    ],
    "F#m": [
        { frets: [2, 4, 4, 2, 2, 2], fingers: [1, 3, 4, 1, 1, 1], barre: 2 },
        { frets: [null, 9, 11, 11, 10, 9], fingers: [0, 1, 3, 4, 2, 1], barre: 9 }
    ],
    "Gb": [
        { frets: [2, 4, 4, 3, 2, 2], fingers: [1, 3, 4, 2, 1, 1], barre: 2 }
    ],
    "Gbm": [
        { frets: [2, 4, 4, 2, 2, 2], fingers: [1, 3, 4, 1, 1, 1], barre: 2 }
    ],
    
    // G chords
    "G": [
        { frets: [3, 2, 0, 0, 0, 3], fingers: [2, 1, 0, 0, 0, 3] },
        { frets: [3, 5, 5, 4, 3, 3], fingers: [1, 3, 4, 2, 1, 1], barre: 3 },
        { frets: [null, 10, 12, 12, 12, 10], fingers: [0, 1, 2, 3, 4, 1], barre: 10 }
    ],
    "Gm": [
        { frets: [3, 5, 5, 3, 3, 3], fingers: [1, 3, 4, 1, 1, 1], barre: 3 },
        { frets: [null, 10, 12, 12, 11, 10], fingers: [0, 1, 3, 4, 2, 1], barre: 10 }
    ],
    "G7": [
        { frets: [3, 2, 0, 0, 0, 1], fingers: [3, 2, 0, 0, 0, 1] },
        { frets: [3, 5, 3, 4, 3, 3], fingers: [1, 3, 1, 2, 1, 1], barre: 3 }
    ],
    "Gmaj7": [
        { frets: [3, 2, 0, 0, 0, 2], fingers: [3, 1, 0, 0, 0, 2] }
    ],
    
    // G# / Ab
    "G#": [
        { frets: [4, 6, 6, 5, 4, 4], fingers: [1, 3, 4, 2, 1, 1], barre: 4 }
    ],
    "G#m": [
        { frets: [4, 6, 6, 4, 4, 4], fingers: [1, 3, 4, 1, 1, 1], barre: 4 }
    ],
    "Ab": [
        { frets: [4, 6, 6, 5, 4, 4], fingers: [1, 3, 4, 2, 1, 1], barre: 4 }
    ],
    
    // A chords
    "A": [
        { frets: [null, 0, 2, 2, 2, 0], fingers: [0, 0, 1, 2, 3, 0] },
        { frets: [5, 7, 7, 6, 5, 5], fingers: [1, 3, 4, 2, 1, 1], barre: 5 },
        { frets: [null, 12, 14, 14, 14, 12], fingers: [0, 1, 2, 3, 4, 1], barre: 12 }
    ],
    "Am": [
        { frets: [null, 0, 2, 2, 1, 0], fingers: [0, 0, 2, 3, 1, 0] },
        { frets: [5, 7, 7, 5, 5, 5], fingers: [1, 3, 4, 1, 1, 1], barre: 5 }
    ],
    "A7": [
        { frets: [null, 0, 2, 0, 2, 0], fingers: [0, 0, 1, 0, 2, 0] },
        { frets: [5, 7, 5, 6, 5, 5], fingers: [1, 3, 1, 2, 1, 1], barre: 5 }
    ],
    "Amaj7": [
        { frets: [null, 0, 2, 1, 2, 0], fingers: [0, 0, 2, 1, 3, 0] }
    ],
    
    // A# / Bb
    "A#": [
        { frets: [null, 1, 3, 3, 3, 1], fingers: [0, 1, 2, 3, 4, 1], barre: 1 }
    ],
    "A#m": [
        { frets: [null, 1, 3, 3, 2, 1], fingers: [0, 1, 3, 4, 2, 1], barre: 1 }
    ],
    "Bb": [
        { frets: [null, 1, 3, 3, 3, 1], fingers: [0, 1, 2, 3, 4, 1], barre: 1 },
        { frets: [6, 8, 8, 7, 6, 6], fingers: [1, 3, 4, 2, 1, 1], barre: 6 }
    ],
    "Bbm": [
        { frets: [null, 1, 3, 3, 2, 1], fingers: [0, 1, 3, 4, 2, 1], barre: 1 },
        { frets: [6, 8, 8, 6, 6, 6], fingers: [1, 3, 4, 1, 1, 1], barre: 6 }
    ],
    
    // B chords
    "B": [
        { frets: [null, 2, 4, 4, 4, 2], fingers: [0, 1, 2, 3, 4, 1], barre: 2 },
        { frets: [7, 9, 9, 8, 7, 7], fingers: [1, 3, 4, 2, 1, 1], barre: 7 }
    ],
    "Bm": [
        { frets: [null, 2, 4, 4, 3, 2], fingers: [0, 1, 3, 4, 2, 1], barre: 2 },
        { frets: [7, 9, 9, 7, 7, 7], fingers: [1, 3, 4, 1, 1, 1], barre: 7 }
    ],
    "B7": [
        { frets: [null, 2, 1, 2, 0, 2], fingers: [0, 2, 1, 3, 0, 4] },
        { frets: [7, 9, 7, 8, 7, 7], fingers: [1, 3, 1, 2, 1, 1], barre: 7 }
    ]
};

function getChordShapes(name) {
    let baseName = name.split('/')[0].trim();
    if (chordShapes[baseName]) return chordShapes[baseName];
    
    // fallbacks
    if (baseName.endsWith("maj7") || baseName.endsWith("M7") || baseName.endsWith("maj9")) {
        let fallback = baseName.replace(/maj7|M7|maj9/, "");
        if (chordShapes[fallback + "maj7"]) return chordShapes[fallback + "maj7"];
        if (chordShapes[fallback]) return chordShapes[fallback];
    }
    if (baseName.endsWith("m7") || baseName.endsWith("min7") || baseName.endsWith("m9")) {
        let fallback = baseName.replace(/m7|min7|m9/, "");
        if (chordShapes[fallback + "m"]) return chordShapes[fallback + "m"];
        if (chordShapes[fallback]) return chordShapes[fallback];
    }
    if (baseName.endsWith("7") || baseName.endsWith("9") || baseName.endsWith("11") || baseName.endsWith("13")) {
        let fallback = baseName.replace(/7|9|11|13/, "");
        if (chordShapes[fallback + "7"]) return chordShapes[fallback + "7"];
        if (chordShapes[fallback]) return chordShapes[fallback];
    }
    if (baseName.endsWith("sus4") || baseName.endsWith("sus2") || baseName.endsWith("sus")) {
        let fallback = baseName.replace(/sus4|sus2|sus/, "");
        if (chordShapes[fallback + "sus4"]) return chordShapes[fallback + "sus4"];
        if (chordShapes[fallback]) return chordShapes[fallback];
    }
    if (baseName.endsWith("m")) {
        let fallback = baseName.slice(0, -1);
        if (chordShapes[fallback]) return chordShapes[fallback];
    }
    let rootMatch = baseName.match(/^[A-G][#b]?/);
    if (rootMatch && chordShapes[rootMatch[0]]) {
        return chordShapes[rootMatch[0]];
    }
    return null;
}

function drawChordSVG(name, shape) {
    if (!shape) {
        return `<div style="padding:12px; background:#fff; border-radius:10px; box-shadow:0 4px 12px rgba(0,0,0,0.15); width:150px; color:#ef4444; font-family:Arial, sans-serif; font-size:12px; font-weight:bold; text-align:center;">${name}</div>`;
    }
    
    let frets = shape.frets;
    let fingers = shape.fingers || [];
    let barre = shape.barre || null;
    
    let maxFret = 0;
    let minFret = 99;
    frets.forEach(f => {
        if (typeof f === 'number') {
            if (f > maxFret) maxFret = f;
            if (f > 0 && f < minFret) minFret = f;
        }
    });
    
    let startFret = 1;
    if (maxFret > 4) {
        startFret = minFret;
    }
    
    let stringsX = [25, 45, 65, 85, 105, 125];
    let fretsY = [20, 46, 72, 98, 124];
    
    let svg = `<svg width="150" height="150" viewBox="0 0 150 150" xmlns="http://www.w3.org/2000/svg" style="background:#fff; display:block;">`;
    
    if (startFret > 1) {
        svg += `<text x="8" y="33" font-family="Arial, sans-serif" font-size="11" font-weight="bold" fill="#ff7a00" text-anchor="start">${startFret}fr</text>`;
    }
    
    for (let i = 0; i < 5; i++) {
        let y = fretsY[i];
        let isNut = (startFret === 1 && i === 0);
        let strokeWidth = isNut ? 4 : 1;
        let strokeColor = isNut ? "#1f2937" : "#d1d5db";
        svg += `<line x1="25" y1="${y}" x2="125" y2="${y}" stroke="${strokeColor}" stroke-width="${strokeWidth}" />`;
    }
    
    for (let i = 0; i < 6; i++) {
        let x = stringsX[i];
        svg += `<line x1="${x}" y1="20" x2="${x}" y2="124" stroke="#d1d5db" stroke-width="1" />`;
    }
    
    for (let i = 0; i < 6; i++) {
        let f = frets[i];
        let x = stringsX[i];
        let y = 13;
        if (f === null || f === 'x') {
            svg += `<path d="M${x-4} ${y-4} L${x+4} ${y+4} M${x+4} ${y-4} L${x-4} ${y+4}" stroke="#9ca3af" stroke-width="1.5" stroke-linecap="round" />`;
        } else if (f === 0) {
            svg += `<circle cx="${x}" cy="${y}" r="3.5" fill="none" stroke="#ff7a00" stroke-width="1.5" />`;
        }
    }
    
    if (barre !== null) {
        let barreRelative = barre - startFret + 1;
        if (barreRelative >= 1 && barreRelative <= 4) {
            let y = fretsY[barreRelative - 1] + 13;
            let firstString = -1;
            let lastString = -1;
            for (let i = 0; i < 6; i++) {
                if (frets[i] === barre) {
                    if (firstString === -1) firstString = i;
                    lastString = i;
                }
            }
            if (firstString !== -1 && lastString !== -1) {
                let x1 = stringsX[firstString];
                let x2 = stringsX[lastString];
                svg += `<rect x="${x1 - 6}" y="${y - 6}" width="${x2 - x1 + 12}" height="12" rx="6" fill="#ff7a00" opacity="0.8" />`;
            }
        }
    }
    
    for (let i = 0; i < 6; i++) {
        let f = frets[i];
        if (typeof f === 'number' && f > 0) {
            let x = stringsX[i];
            let relFret = f - startFret + 1;
            if (relFret >= 1 && relFret <= 4) {
                let y = fretsY[relFret - 1] + 13;
                let finger = fingers[i] || 0;
                svg += `<circle cx="${x}" cy="${y}" r="8.5" fill="#ff7a00" stroke="#ff7a00" stroke-width="1" />`;
                if (finger > 0) {
                    svg += `<text x="${x}" y="${y + 3.5}" font-family="Arial, sans-serif" font-size="10" font-weight="bold" fill="#fff" text-anchor="middle">${finger}</text>`;
                }
            }
        }
    }
    
    svg += `</svg>`;
    return svg;
}
