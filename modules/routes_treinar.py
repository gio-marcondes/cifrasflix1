@app.route("/treinar/")
@app.route("/treinar/<artista>/<musica>")
def treinar_piano(artista="", musica=""):
    import html as html_escape

    artista_nome = (artista or "").replace("-", " ").strip().title()
    musica_nome = (musica or "").replace("-", " ").strip().title()
    modo_livre = not (artista or musica)

    html = header("Treinar Piano" + (" - " + musica_nome if musica_nome else ""))
    html += f"""
    <script src="https://cdn.jsdelivr.net/npm/jzz"></script>
    <script src="https://cdn.jsdelivr.net/npm/jzz-midi-gm"></script>
    <script src="https://cdn.jsdelivr.net/npm/jzz-synth-tiny"></script>
    <script src="https://cdn.jsdelivr.net/npm/jzz-input-kbd"></script>
    <script src="https://cdn.jsdelivr.net/npm/jzz-midi-smf"></script>
    <script src="https://cdn.jsdelivr.net/npm/jzz-input-pad"></script>
    <script src="https://cdn.jsdelivr.net/npm/jzz-input-slider"></script>
    <style>
        .treinarPage {{
            margin: 0;
            background: #eef2f7;
            color: #1f2937;
            font-family: 'Segoe UI', Tahoma, sans-serif;
        }}
        .treinarPage.wrap {{
            max-width: 1160px;
            margin: 18px auto;
            padding: 0 14px 30px;
        }}
        .treinarPage .globalCard {{
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #dbe4ee;
            border-radius: 18px;
            padding: 16px;
            box-shadow: 0 14px 36px rgba(15, 23, 42, 0.10);
        }}
        .treinarPage .sectionDivider {{
            height: 1px;
            background: linear-gradient(90deg, rgba(148, 163, 184, 0.05), rgba(148, 163, 184, 0.5), rgba(148, 163, 184, 0.05));
            margin: 14px 0;
        }}
        .treinarPage .head {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }}
        .treinarPage .head a {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 34px;
            border-radius: 999px;
            border: 1px solid rgba(148, 163, 184, 0.4);
            color: #334155;
            text-decoration: none;
            padding: 0 13px;
            background: rgba(255, 255, 255, 0.75);
            backdrop-filter: blur(4px);
        }}
        .treinarPage .headMeta {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 2px;
        }}
        .treinarPage .metaChip {{
            display: inline-flex;
            align-items: center;
            min-height: 26px;
            padding: 0 10px;
            border-radius: 999px;
            border: 1px solid rgba(148, 163, 184, 0.35);
            background: rgba(255, 255, 255, 0.7);
            color: #475569;
            font-size: 12px;
            font-weight: 700;
        }}
        .treinarPage h1 {{ margin: 0; font-size: 28px; letter-spacing: 0.2px; }}
        .treinarPage .meta {{ color: #64748b; margin-top: 4px; font-size: 13px; }}
        .treinarPage h2 {{
            margin: 0 0 10px;
            font-size: 15px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #475569;
        }}
        .treinarPage .instrumentHeader {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
        }}
        .treinarPage .controls {{
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
            align-items: center;
            margin-bottom: 10px;
        }}
        .treinarPage .controlGroup {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.72);
            padding: 7px 10px;
        }}
        .treinarPage label {{ font-size: 13px; color: #334155; }}
        .treinarPage input[type=range] {{ width: 170px; }}
        .treinarPage #piano {{ margin: 10px auto; overflow-x: auto; }}
        .treinarPage .note-hint {{ color: #64748b; font-size: 12px; }}
        .treinarPage .instrument-name {{
            font-size: 13px;
            font-weight: 700;
            color: #1f2937;
            margin: 0;
            white-space: nowrap;
        }}
        .treinarPage .extra-controls {{
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            align-items: center;
            margin-top: 10px;
            margin-bottom: 6px;
        }}
        .treinarPage .extra-controls button {{
            border: 1px solid rgba(148, 163, 184, 0.38);
            background: rgba(255, 255, 255, 0.74);
            color: #334155;
            border-radius: 8px;
            padding: 6px 10px;
            cursor: pointer;
            backdrop-filter: blur(4px);
        }}
        .treinarPage .extra-controls button:disabled {{
            opacity: 0.42;
            cursor: not-allowed;
        }}
        .treinarPage .statusPill {{
            display: inline-flex;
            align-items: center;
            min-height: 32px;
            border: 1px solid rgba(148, 163, 184, 0.38);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.74);
            color: #334155;
            font-size: 12px;
            font-weight: 700;
            padding: 0 12px;
        }}
        .treinarPage .instrumentMenu {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 4px;
        }}
        .treinarPage .menu-btn {{
            border: 1px solid rgba(148, 163, 184, 0.38);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.74);
            color: #334155;
            padding: 8px 12px;
            cursor: pointer;
            font-weight: 700;
            backdrop-filter: blur(4px);
        }}
        .treinarPage .menu-btn:hover {{
            background: rgba(226, 232, 240, 0.95);
            border-color: rgba(99, 102, 241, 0.55);
            color: #312e81;
        }}
        .treinarOverlay {{
            position: fixed;
            inset: 0;
            background: rgba(15, 23, 42, 0.24);
            backdrop-filter: blur(3px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        }}
        .treinarOverlay .overlay-content {{
            width: min(360px, 92vw);
            max-height: 78vh;
            overflow: auto;
            border-radius: 12px;
            border: 1px solid #d1d9e2;
            background: #ffffff;
            padding: 10px;
        }}
        .treinarPage .instrument {{
            padding: 9px 10px;
            border-radius: 8px;
            border: 1px solid #dbe4ee;
            margin-bottom: 8px;
            cursor: pointer;
            color: #334155;
            background: rgba(248, 250, 252, 0.9);
        }}
        .treinarPage .instrument:hover {{
            border-color: #93c5fd;
            background: #eef6ff;
        }}
        .treinarPage #controlArea {{
            position: relative;
            width: 320px;
            height: 165px;
        }}
        .treinarPage #pad, .treinarPage #sld1, .treinarPage #sld2 {{ position: absolute; }}
        .treinarPage #pad {{ left: 70px; top: 0; }}
        .treinarPage #sld1 {{ left: 30px; top: 0; }}
        .treinarPage #sld2 {{ left: 0; top: 0; }}
        .treinarPage #piano [data-kbd]::after {{
            content: attr(data-kbd);
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
            bottom: 8px;
            font-size: 10px;
            font-weight: 800;
            line-height: 1;
            color: #0f172a;
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(148, 163, 184, 0.6);
            border-radius: 999px;
            padding: 2px 6px;
            pointer-events: none;
            white-space: nowrap;
        }}
        .treinarPage #piano [data-kbd-black="1"]::after {{
            bottom: 6px;
            font-size: 9px;
            color: #e2e8f0;
            background: rgba(15, 23, 42, 0.92);
            border-color: rgba(100, 116, 139, 0.9);
        }}
    </style>

    <section class="wrap treinarPage">
        <div class="globalCard">
            <div class="head">
                <div>
                    <h1>Treinar no Piano</h1>
                    <div class="meta">{"Modo livre" if modo_livre else html_escape.escape(artista_nome) + " - " + html_escape.escape(musica_nome)}</div>
                </div>
                <a href="{'/flix-play' if modo_livre else '/tocador-gp4/' + html_escape.escape(artista) + '/' + html_escape.escape(musica)}">{'Voltar ao Flix Play' if modo_livre else 'Voltar ao tocador'}</a>
            </div>
            <div class="headMeta">
                <span class="metaChip">Teclado com atalhos visiveis</span>
                <span class="metaChip">Gravacao e exportacao MIDI</span>
                <span class="metaChip">Troca rapida de timbre</span>
            </div>
            <div class="sectionDivider"></div>

            <div class="instrumentHeader">
                <h2>Instrumentos</h2>
                <div class="instrument-name" id="instrumentName">Instrumento: Piano</div>
            </div>
            <div class="instrumentMenu" id="menu"></div>

            <div class="sectionDivider"></div>

            <div class="controls">
                <label class="controlGroup">Volume <input type="range" id="volume" min="0" max="127" value="100"></label>
                <label class="controlGroup">Oitava <input type="range" id="octave" min="2" max="7" value="4"></label>
            </div>
            <div class="extra-controls">
                <label class="controlGroup">MIDI <input type="file" id="midiFile" accept=".mid,.midi"></label>
                <button id="playBtn" disabled>Play</button>
                <button id="recStartBtn">Gravar</button>
                <button id="recStopBtn">Parar</button>
                <button id="exportBtn">Exportar</button>
                <span class="statusPill" id="status">Parado</span>
            </div>

            <div id="piano"></div>
            <div class="note-hint">Atalhos logicos ativos: q=Do, 2=Do#, w=Re, 3=Re#, e continuacao em x/d/c/f ... ;/~.</div>

            <div class="sectionDivider"></div>

            <h2>Controles PRO</h2>
            <div id="controlArea">
                <span id="pad"></span>
                <span id="sld1"></span>
                <span id="sld2"></span>
            </div>
        </div>
    </section>

    <div class="overlay treinarOverlay" id="overlay">
        <div class="overlay-content" id="overlayContent"></div>
    </div>

    <script>
        JZZ.synth.Tiny.register('Web Audio');
        var out = JZZ().openMidiOut();

        var piano = JZZ.input.Kbd({{ at: 'piano', from: 'C3', to: 'C6', ww: 38, bw: 24, wl: 170, bl: 105 }});
        piano.connect(out);

        function noteRange(fromMidi, toMidi) {{
            var noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
            var outNotes = [];
            for (var m = fromMidi; m <= toMidi; m += 1) {{
                var octave = Math.floor(m / 12) - 1;
                var name = noteNames[m % 12] + octave;
                outNotes.push(name);
            }}
            return outNotes;
        }}

        function keyboardMaps(o) {{
            var keyToNote = {{
                Q: 'C' + (o - 1),
                '2': 'C#' + (o - 1),
                W: 'D' + (o - 1),
                '3': 'D#' + (o - 1),
                E: 'E' + (o - 1),
                R: 'F' + (o - 1),
                '5': 'F#' + (o - 1),
                T: 'G' + (o - 1),
                '6': 'G#' + (o - 1),
                Y: 'A' + (o - 1),
                '7': 'A#' + (o - 1),
                U: 'B' + (o - 1),
                I: 'C' + o,
                '9': 'C#' + o,
                O: 'D' + o,
                '0': 'D#' + o,
                P: 'E' + o,
                '[': 'F' + o,
                '=': 'F#' + o,
                Z: 'G' + o,
                S: 'G#' + o,
                X: 'A' + o,
                D: 'A#' + o,
                C: 'B' + o,
                V: 'C' + (o + 1),
                G: 'C#' + (o + 1),
                B: 'D' + (o + 1),
                H: 'D#' + (o + 1),
                N: 'E' + (o + 1),
                M: 'F' + (o + 1),
                K: 'F#' + (o + 1),
                ',': 'G' + (o + 1),
                L: 'G#' + (o + 1),
                '.': 'A' + (o + 1),
                ';': 'A#' + (o + 1),
                '/': 'B' + (o + 1),
                '`': 'C' + (o + 2)
            }};

            var noteToKey = {{}};
            Object.keys(keyToNote).forEach(function(keyName) {{
                var noteName = keyToNote[keyName];
                if (!noteToKey[noteName]) noteToKey[noteName] = keyName;
            }});

            return {{ keyToNote: keyToNote, noteToKey: noteToKey }};
        }}

        function keyboardLegendMap(o) {{
            return keyboardMaps(o).noteToKey;
        }}

        function annotatePianoKeys(o) {{
            var pianoRoot = document.querySelector('#piano > span');
            if (!pianoRoot) return;

            var keys = Array.prototype.slice.call(pianoRoot.children || []);
            if (!keys.length) return;

            var notes = noteRange(48, 84);
            var whiteNotes = notes.filter(function(n) {{ return n.indexOf('#') === -1; }});
            var blackNotes = notes.filter(function(n) {{ return n.indexOf('#') !== -1; }});

            var whiteKeys = keys
                .filter(function(el) {{ return parseInt(el.style.height || '0', 10) >= 150; }})
                .sort(function(a, b) {{ return parseInt(a.style.left || '0', 10) - parseInt(b.style.left || '0', 10); }});

            var blackKeys = keys
                .filter(function(el) {{ return parseInt(el.style.height || '0', 10) < 150; }})
                .sort(function(a, b) {{ return parseInt(a.style.left || '0', 10) - parseInt(b.style.left || '0', 10); }});

            var legendMap = keyboardLegendMap(o);

            function paintLegend(el, noteName, isBlack) {{
                if (!el) return;
                var keyName = legendMap[noteName] || noteName;
                el.setAttribute('data-kbd', keyName);
                if (isBlack) el.setAttribute('data-kbd-black', '1');
                else el.removeAttribute('data-kbd-black');
            }}

            for (var i = 0; i < whiteKeys.length; i += 1) {{
                paintLegend(whiteKeys[i], whiteNotes[i], false);
            }}

            for (var j = 0; j < blackKeys.length; j += 1) {{
                paintLegend(blackKeys[j], blackNotes[j], true);
            }}
        }}

        function createKeyboard(o) {{
            return JZZ.input.ASCII(keyboardMaps(o).keyToNote).connect(piano);
        }}

        var ascii = createKeyboard(4);
        annotatePianoKeys(4);

        var midiPlayer = null;
        var isPlaying = false;
        var recSmf = null;
        var recTrack = null;
        var isRecording = false;
        var recLastTs = null;
        var recEventCount = 0;
        var REC_BPM = 120;
        var REC_PPQ = 96;

        var statusEl = document.getElementById('status');
        var playBtn = document.getElementById('playBtn');
        var midiFileInput = document.getElementById('midiFile');

        function setStatus(text) {{
            if (statusEl) statusEl.textContent = text;
        }}

        midiFileInput.addEventListener('change', function(e) {{
            var file = e.target.files && e.target.files[0];
            if (!file) return;

            var reader = new FileReader();
            reader.onload = function(ev) {{
                var bytes = new Uint8Array(ev.target.result);
                var data = '';
                for (var i = 0; i < bytes.length; i += 1) data += String.fromCharCode(bytes[i]);
                try {{
                    midiPlayer = JZZ.MIDI.SMF(data).player();
                    midiPlayer.connect(out);
                    playBtn.disabled = false;
                    setStatus('MIDI carregado');
                }} catch (err) {{
                    setStatus('Falha ao carregar MIDI');
                }}
            }};
            reader.readAsArrayBuffer(file);
        }});

        playBtn.addEventListener('click', function() {{
            if (!midiPlayer) return;
            if (!isPlaying) {{
                midiPlayer.play();
                isPlaying = true;
                playBtn.textContent = 'Stop';
                setStatus('Tocando MIDI');
            }} else {{
                midiPlayer.stop();
                isPlaying = false;
                playBtn.textContent = 'Play';
                setStatus('Parado');
            }}
        }});

        document.getElementById('recStartBtn').addEventListener('click', function() {{
            recSmf = new JZZ.MIDI.SMF(0, REC_PPQ);
            recTrack = new JZZ.MIDI.SMF.MTrk();
            recSmf.push(recTrack);
            recTrack.smfBPM(REC_BPM);
            isRecording = true;
            recLastTs = null;
            recEventCount = 0;
            setStatus('Gravando');
        }});

        document.getElementById('recStopBtn').addEventListener('click', function() {{
            if (!isRecording || !recTrack) return;
            isRecording = false;
            recTrack.smfEndOfTrack();
            if (!recEventCount) setStatus('Gravacao vazia');
            else setStatus('Gravacao finalizada (' + recEventCount + ' eventos)');
        }});

        document.getElementById('exportBtn').addEventListener('click', function() {{
            if (!recSmf || !recEventCount) {{
                setStatus('Nada para exportar');
                return;
            }}
            try {{
                var dump = recSmf.dump();
                var bin = dump.split('').map(function(c) {{ return c.charCodeAt(0); }});
                var blob = new Blob([new Uint8Array(bin)], {{ type: 'audio/midi' }});
                var url = URL.createObjectURL(blob);
                var a = document.createElement('a');
                a.href = url;
                a.download = 'gravacao.mid';
                a.click();
                URL.revokeObjectURL(url);
                setStatus('MIDI exportado (' + recEventCount + ' eventos)');
            }} catch (err) {{
                setStatus('Falha ao exportar');
            }}
        }});

        var categories = [
            {{ name: 'Piano', range: [0, 7] }},
            {{ name: 'Guitar', range: [24, 31] }},
            {{ name: 'Bass', range: [32, 39] }},
            {{ name: 'Strings', range: [40, 47] }},
            {{ name: 'Orchestra', range: [48, 55] }},
            {{ name: 'Synth', range: [80, 87] }},
            {{ name: 'Drums', range: [112, 119] }}
        ];

        var menu = document.getElementById('menu');
        var overlay = document.getElementById('overlay');
        var overlayContent = document.getElementById('overlayContent');
        var instrumentName = document.getElementById('instrumentName');

        function closeOverlay() {{
            overlay.style.display = 'none';
            overlayContent.innerHTML = '';
        }}

        function openOverlay(cat) {{
            overlay.style.display = 'flex';
            overlayContent.innerHTML = '';

            for (var i = cat.range[0]; i <= cat.range[1]; i += 1) {{
                (function(program) {{
                    var row = document.createElement('div');
                    row.className = 'instrument';
                    row.textContent = JZZ.MIDI.programName(program);
                    row.addEventListener('click', function() {{
                        try {{
                            out.program(0, program);
                            instrumentName.textContent = 'Instrumento: ' + JZZ.MIDI.programName(program);
                        }} catch (err) {{}}
                        closeOverlay();
                    }});
                    overlayContent.appendChild(row);
                }})(i);
            }}
        }}

        categories.forEach(function(cat) {{
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'menu-btn';
            btn.textContent = cat.name;
            btn.addEventListener('click', function() {{ openOverlay(cat); }});
            menu.appendChild(btn);
        }});

        overlay.addEventListener('click', function(e) {{
            if (e.target === overlay) closeOverlay();
        }});

        try {{
            var pad = JZZ.input.Pad({{ at: 'pad', rh: 100, kw: 20 }}).connect(piano);
            var slider1 = JZZ.input.Slider({{ at: 'sld1' }}).connect(out);
            var slider2 = JZZ.input.Slider({{ at: 'sld2', data: 'mod' }}).connect(out);
            pad.connect(slider1).connect(slider2);
        }} catch (err) {{}}

        piano.connect(function(msg) {{
            if (!isRecording || !recTrack) return;

            var now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
            var deltaMs = recLastTs == null ? 0 : Math.max(0, now - recLastTs);
            var ticksPerMs = (REC_PPQ * REC_BPM) / 60000;
            var deltaTicks = recLastTs == null ? 0 : Math.max(1, Math.round(deltaMs * ticksPerMs));

            recTrack.tick(deltaTicks).send(msg);
            recLastTs = now;
            recEventCount += 1;
        }});

        document.getElementById('volume').addEventListener('input', function (e) {{
            out.control(0, 7, parseInt(e.target.value || '100', 10));
        }});

        document.getElementById('octave').addEventListener('input', function (e) {{
            var o = parseInt(e.target.value || '4', 10);
            ascii.disconnect();
            ascii = createKeyboard(o);
            annotatePianoKeys(o);
        }});
    </script>

    """
    return html
