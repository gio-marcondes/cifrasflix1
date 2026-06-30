from flask import Blueprint
from modules.layout import header

jamstudio_bp = Blueprint('jamstudio', __name__)

@jamstudio_bp.route("/jam-studio")
def jam_studio():
    html = header("CifrasFlix - Estúdio Jam & Voz")
    
    html += """
    <script src="https://cdn.jsdelivr.net/npm/soundfont-player/dist/soundfont-player.min.js"></script>
    <style>
        /* CSS customizado para o JamStudio */
        .jamStudioContainer {
            max-width: 1200px;
            margin: 20px auto;
            padding: 0 15px 40px;
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            color: var(--text);
        }
        
        .studioHeader {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--line);
        }
        
        .studioHeader h1 {
            font-size: 28px;
            font-weight: 700;
            margin: 0;
            background: linear-gradient(135deg, var(--teal) 0%, var(--blue) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .studioHeader p {
            margin: 5px 0 0;
            color: var(--muted);
            font-size: 14px;
        }

        .studioGrid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }

        @media (max-width: 920px) {
            .studioGrid {
                grid-template-columns: 1fr;
            }
        }

        .studioCard {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
            display: flex;
            flex-direction: column;
            gap: 20px;
            position: relative;
            overflow: hidden;
        }

        body.theme-dark .studioCard {
            background: var(--surface-2);
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
        }

        .cardTitle {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 18px;
            font-weight: 700;
            margin: 0;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--line);
        }

        .cardTitle span.icon {
            font-size: 24px;
        }

        /* Sessão Playalong */
        .controlsGroup {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .controlsGroup label {
            font-size: 12px;
            font-weight: 700;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        /* Grid de Tons */
        .keyGrid {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 6px;
        }

        .keyBtn {
            min-height: 36px;
            font-size: 12px;
            font-weight: 600;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--surface-2);
            color: var(--text);
            cursor: pointer;
            transition: all 0.2s ease;
        }

        body.theme-dark .keyBtn {
            background: var(--surface);
        }

        .keyBtn:hover {
            border-color: var(--teal);
            transform: translateY(-1px);
        }

        .keyBtn.active {
            background: var(--teal);
            color: #000;
            font-weight: 800;
            border-color: var(--teal);
            box-shadow: 0 0 10px rgba(255, 122, 0, 0.4);
        }

        body.theme-dark .keyBtn.active {
            color: #000;
            box-shadow: 0 0 10px rgba(30, 224, 198, 0.4);
        }

        /* Toggle de escala (Maior / Menor) */
        .scaleToggle {
            display: flex;
            background: var(--surface-2);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 3px;
        }

        body.theme-dark .scaleToggle {
            background: var(--surface);
        }

        .scaleToggleBtn {
            flex: 1;
            border: none;
            background: transparent;
            color: var(--text);
            font-size: 13px;
            font-weight: 600;
            padding: 8px;
            border-radius: 6px;
            cursor: pointer;
            min-height: auto;
            transition: all 0.2s ease;
        }

        .scaleToggleBtn.active {
            background: var(--surface);
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }

        body.theme-dark .scaleToggleBtn.active {
            background: var(--surface-2);
            color: var(--teal);
        }

        /* Slider de BPM e Tap Tempo */
        .bpmControls {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .bpmSliderContainer {
            flex: 1;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .bpmSliderContainer input[type="range"] {
            flex: 1;
            accent-color: var(--teal);
        }

        .bpmValueDisplay {
            font-size: 16px;
            font-weight: 700;
            min-width: 60px;
            text-align: right;
        }

        .tapTempoBtn {
            min-height: 40px;
            padding: 0 15px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            border: 1px solid var(--line);
            background: var(--surface-2);
            border-radius: 8px;
            cursor: pointer;
        }

        body.theme-dark .tapTempoBtn {
            background: var(--surface);
        }

        .tapTempoBtn:active {
            transform: scale(0.95);
            background: var(--teal);
            color: #000;
        }

        /* Grid de Estilos */
        .styleSelector {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
        }

        .styleCard {
            border: 1px solid var(--line);
            border-radius: 10px;
            background: var(--surface-2);
            padding: 12px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
        }

        body.theme-dark .styleCard {
            background: var(--surface);
        }

        .styleCard:hover {
            border-color: var(--blue);
            transform: translateY(-2px);
        }

        .styleCard.active {
            border-color: var(--blue);
            background: rgba(37, 99, 235, 0.08);
            box-shadow: 0 0 12px rgba(37, 99, 235, 0.2);
        }

        body.theme-dark .styleCard.active {
            background: rgba(102, 166, 255, 0.1);
            border-color: var(--blue);
        }

        .styleCard .emoji {
            font-size: 20px;
        }

        .styleCard .name {
            font-size: 12px;
            font-weight: 700;
        }

        /* Botão Play do Acompanhamento */
        .actionBtnContainer {
            margin-top: 10px;
        }

        .playalongPlayBtn {
            width: 100%;
            min-height: 52px;
            font-size: 16px;
            font-weight: 800;
            border-radius: 12px;
            color: #2f1600;
            background: linear-gradient(135deg, var(--teal) 0%, #ffb36b 100%);
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(255, 122, 0, 0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            transition: all 0.2s ease;
        }

        .playalongPlayBtn:hover {
            filter: brightness(1.05);
            transform: translateY(-1px);
        }

        .playalongPlayBtn:active {
            transform: translateY(1px);
        }

        .playalongPlayBtn.playing {
            background: linear-gradient(135deg, var(--rose) 0%, #ff4d4d 100%);
            color: #fff;
            box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
        }

        /* Metrônomo Visual e Canvas Visualizer */
        .visualizerContainer {
            background: #000;
            border-radius: 12px;
            height: 100px;
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .metronomeBeatDot {
            position: absolute;
            width: 24px;
            height: 24px;
            background: var(--teal);
            border-radius: 50%;
            opacity: 0.15;
            transition: transform 0.1s ease, opacity 0.1s ease;
        }

        .metronomeBeatDot.active {
            opacity: 1;
            transform: scale(2.2);
            box-shadow: 0 0 20px var(--teal);
        }

        .visualizerCanvas {
            width: 100%;
            height: 100%;
            position: absolute;
            top: 0;
            left: 0;
        }

        .beatSequencerDots {
            display: flex;
            justify-content: center;
            gap: 8px;
            margin-top: 5px;
        }

        .sequencerDot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--line);
        }

        .sequencerDot.active {
            background: var(--teal);
            transform: scale(1.3);
            box-shadow: 0 0 5px var(--teal);
        }

        /* Sessão Canto / Microfone */
        .microphoneToggleBtn {
            width: 100%;
            min-height: 48px;
            font-size: 14px;
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

        body.theme-dark .microphoneToggleBtn {
            background: var(--surface);
        }

        .microphoneToggleBtn.active {
            background: rgba(239, 68, 68, 0.15);
            border-color: var(--rose);
            color: var(--rose);
            box-shadow: 0 0 10px rgba(239, 68, 68, 0.2);
        }

        .pitchDisplayContainer {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 180px;
            background: var(--surface-2);
            border: 1px solid var(--line);
            border-radius: 12px;
            position: relative;
        }

        body.theme-dark .pitchDisplayContainer {
            background: var(--surface);
        }

        .pitchNoteName {
            font-size: 72px;
            font-weight: 900;
            color: var(--text);
            line-height: 1;
            margin: 0;
            letter-spacing: -2px;
            transition: transform 0.1s ease;
        }

        .pitchNoteName.stable {
            color: var(--teal);
            text-shadow: 0 0 20px rgba(255, 122, 0, 0.3);
        }

        body.theme-dark .pitchNoteName.stable {
            color: var(--teal);
            text-shadow: 0 0 20px rgba(30, 224, 198, 0.4);
        }

        .pitchFrequency {
            font-size: 14px;
            color: var(--muted);
            margin-top: 8px;
        }

        /* Medidor de Afinação (Tuner Gauge) */
        .tunerMeterContainer {
            width: 100%;
            padding: 0 20px;
            margin-top: 15px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
        }

        .tunerTrack {
            width: 100%;
            height: 6px;
            background: var(--line);
            border-radius: 3px;
            position: relative;
        }

        .tunerCenter {
            position: absolute;
            left: 50%;
            top: -3px;
            width: 2px;
            height: 12px;
            background: var(--muted);
            transform: translateX(-50%);
        }

        .tunerCenter.inTune {
            background: #10b981;
            width: 4px;
            box-shadow: 0 0 8px #10b981;
        }

        .tunerNeedle {
            position: absolute;
            top: -6px;
            left: 50%;
            width: 12px;
            height: 18px;
            background: var(--teal);
            border-radius: 3px;
            transform: translateX(-50%);
            transition: left 0.15s ease-out;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }

        .tunerNeedle.inTune {
            background: #10b981;
            box-shadow: 0 0 8px #10b981;
        }

        .tunerLabels {
            display: flex;
            justify-content: space-between;
            width: 100%;
            font-size: 10px;
            color: var(--muted);
            font-weight: 700;
        }

        /* Sugestão de Escalas Detectadas */
        .scaleSuggesterBox {
            background: var(--surface-2);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        body.theme-dark .scaleSuggesterBox {
            background: var(--surface);
        }

        .detectedNotesRow {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            align-items: center;
        }

        .noteChip {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            height: 28px;
            min-width: 28px;
            padding: 0 8px;
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            animation: popIn 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }

        body.theme-dark .noteChip {
            background: var(--surface-2);
        }

        @keyframes popIn {
            0% { transform: scale(0); opacity: 0; }
            100% { transform: scale(1); opacity: 1; }
        }

        .scaleSuggestionsList {
            display: flex;
            flex-direction: column;
            gap: 6px;
            margin-top: 5px;
        }

        .suggestionRow {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
            padding: 6px 10px;
            border-radius: 6px;
            background: var(--surface);
            border: 1px solid var(--line);
        }

        body.theme-dark .suggestionRow {
            background: var(--surface-2);
        }

        .suggestionRow.bestMatch {
            border-color: var(--blue);
            background: rgba(37, 99, 235, 0.05);
            font-weight: 700;
        }

        body.theme-dark .suggestionRow.bestMatch {
            background: rgba(102, 166, 255, 0.06);
        }

        .suggestionScore {
            font-size: 11px;
            background: var(--line);
            padding: 2px 6px;
            border-radius: 4px;
            color: var(--text);
        }

        .suggestionRow.bestMatch .suggestionScore {
            background: var(--blue);
            color: #fff;
        }

        /* Botões Auxiliares */
        .clearHistoryBtn {
            align-self: flex-end;
            min-height: 28px;
            font-size: 11px;
            padding: 0 10px;
            border-radius: 6px;
            background: transparent;
            color: var(--muted);
            border: 1px solid var(--line);
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .clearHistoryBtn:hover {
            color: var(--danger);
            border-color: var(--danger);
        }
    </style>

    <div class="jamStudioContainer">
        <section class="studioHeader">
            <div>
                <h1>Estúdio Jam & Voz</h1>
                <p>Criação de playalongs e análise de tom em tempo real direto no seu navegador.</p>
            </div>
            <a class="clearHistoryBtn" href="/" style="align-self: center;">Voltar à Central</a>
        </section>

        <div class="studioGrid">
            <!-- CARTÃO DE PLAYALONG -->
            <div class="studioCard">
                <h2 class="cardTitle">
                    <span class="icon">🎸</span>
                    <span>Criador de Playalong</span>
                </h2>

                <!-- Seleção do Tom -->
                <div class="controlsGroup">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <label>1. Escolha o Tom Principal</label>
                        <span id="currentChordDisplay" style="font-size: 13px; font-weight: 700; color: var(--blue);"></span>
                    </div>
                    
                    <!-- Toggle Maior / Menor -->
                    <div class="scaleToggle">
                        <button type="button" class="scaleToggleBtn active" id="scaleMajorBtn" onclick="setScaleMode('Major')">Escala Maior</button>
                        <button type="button" class="scaleToggleBtn" id="scaleMinorBtn" onclick="setScaleMode('Minor')">Escala Menor</button>
                    </div>

                    <!-- Grid de Notas -->
                    <div class="keyGrid">
                        <button type="button" class="keyBtn active" data-key="C" onclick="selectKey('C')">C</button>
                        <button type="button" class="keyBtn" data-key="C#" onclick="selectKey('C#')">C#</button>
                        <button type="button" class="keyBtn" data-key="D" onclick="selectKey('D')">D</button>
                        <button type="button" class="keyBtn" data-key="D#" onclick="selectKey('D#')">D#</button>
                        <button type="button" class="keyBtn" data-key="E" onclick="selectKey('E')">E</button>
                        <button type="button" class="keyBtn" data-key="F" onclick="selectKey('F')">F</button>
                        <button type="button" class="keyBtn" data-key="F#" onclick="selectKey('F#')">F#</button>
                        <button type="button" class="keyBtn" data-key="G" onclick="selectKey('G')">G</button>
                        <button type="button" class="keyBtn" data-key="G#" onclick="selectKey('G#')">G#</button>
                        <button type="button" class="keyBtn" data-key="A" onclick="selectKey('A')">A</button>
                        <button type="button" class="keyBtn" data-key="A#" onclick="selectKey('A#')">A#</button>
                        <button type="button" class="keyBtn" data-key="B" onclick="selectKey('B')">B</button>
                    </div>
                </div>

                <!-- Fórmula de Compasso -->
                <div class="controlsGroup">
                    <label>Fórmula de Compasso</label>
                    <div style="display: flex; gap: 10px;">
                        <button type="button" class="scaleToggleBtn active" id="ts44Btn" onclick="setTimeSignature('4/4')" style="flex: 1; padding: 10px; font-weight: 600; border-radius: 8px;">4/4</button>
                        <button type="button" class="scaleToggleBtn" id="ts34Btn" onclick="setTimeSignature('3/4')" style="flex: 1; padding: 10px; font-weight: 600; border-radius: 8px;">3/4</button>
                        <button type="button" class="scaleToggleBtn" id="ts68Btn" onclick="setTimeSignature('6/8')" style="flex: 1; padding: 10px; font-weight: 600; border-radius: 8px;">6/8</button>
                    </div>
                </div>

                <!-- Controle de BPM -->
                <div class="controlsGroup">
                    <label>2. Ajuste o Tempo (BPM)</label>
                    <div class="bpmControls">
                        <div class="bpmSliderContainer">
                            <input type="range" id="bpmSlider" min="60" max="200" value="120" oninput="updateBPM(this.value)" />
                            <span class="bpmValueDisplay" id="bpmDisplay">120 BPM</span>
                        </div>
                        <button type="button" class="tapTempoBtn" onclick="tapTempo()">TAP</button>
                    </div>
                </div>

                <!-- Seleção do Estilo -->
                <div class="controlsGroup">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <label style="margin-bottom: 0;">3. Selecione o Estilo Musical</label>
                        <a href="/estilos" target="_blank" style="font-size: 13px; font-weight: 600; color: var(--blue); text-decoration: none; display: flex; align-items: center; gap: 4px;">📖 Guia de Estilos</a>
                    </div>
                    <div class="styleSelector" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 10px; width: 100%;">
                        <div class="styleCard active" id="stylePop" onclick="selectStyle('Pop')">
                            <span class="emoji">🥁</span>
                            <span class="name">Pop</span>
                        </div>
                        <div class="styleCard" id="styleBlues" onclick="selectStyle('Blues')">
                            <span class="emoji">🎷</span>
                            <span class="name">Blues</span>
                        </div>
                        <div class="styleCard" id="styleRock" onclick="selectStyle('Rock')">
                            <span class="emoji">🎸</span>
                            <span class="name">Rock Clássico</span>
                        </div>
                        <div class="styleCard" id="styleJazz" onclick="selectStyle('Jazz')">
                            <span class="emoji">🎹</span>
                            <span class="name">Jazz</span>
                        </div>
                        <div class="styleCard" id="styleReggae" onclick="selectStyle('Reggae')">
                            <span class="emoji">🌴</span>
                            <span class="name">Reggae</span>
                        </div>
                        <div class="styleCard" id="styleCountry" onclick="selectStyle('Country')">
                            <span class="emoji">🤠</span>
                            <span class="name">Country</span>
                        </div>
                        <div class="styleCard" id="styleBalada" onclick="selectStyle('Balada')">
                            <span class="emoji">🎵</span>
                            <span class="name">Balada</span>
                        </div>
                        <div class="styleCard" id="styleSoul" onclick="selectStyle('Soul')">
                            <span class="emoji">🎙️</span>
                            <span class="name">Soul / R&B</span>
                        </div>
                        <div class="styleCard" id="styleAlternativo" onclick="selectStyle('Alternativo')">
                            <span class="emoji">🌌</span>
                            <span class="name">Alternativo</span>
                        </div>
                        <div class="styleCard" id="styleBossa" onclick="selectStyle('Bossa')">
                            <span class="emoji">🌊</span>
                            <span class="name">Bossa Nova</span>
                        </div>
                        <div class="styleCard" id="styleFunk" onclick="selectStyle('Funk')">
                            <span class="emoji">🕺</span>
                            <span class="name">Funk</span>
                        </div>
                    </div>
                </div>

                <!-- Visualizador & Metrônomo -->
                <div class="controlsGroup">
                    <div class="visualizerContainer">
                        <div class="metronomeBeatDot" id="metronomeDot"></div>
                        <canvas class="visualizerCanvas" id="synthVisualizer"></canvas>
                    </div>
                    <!-- Indicador visual dos tempos do compasso -->
                    <div class="beatSequencerDots">
                        <div class="sequencerDot" data-beat="0"></div>
                        <div class="sequencerDot" data-beat="1"></div>
                        <div class="sequencerDot" data-beat="2"></div>
                        <div class="sequencerDot" data-beat="3"></div>
                        <div class="sequencerDot" data-beat="4"></div>
                        <div class="sequencerDot" data-beat="5"></div>
                        <div class="sequencerDot" data-beat="6"></div>
                        <div class="sequencerDot" data-beat="7"></div>
                    </div>
                </div>

                <!-- Botão de Iniciar -->
                <div class="actionBtnContainer">
                    <button type="button" class="playalongPlayBtn" id="playBtn" onclick="togglePlayalong()">
                        <span id="playBtnIcon">▶</span>
                        <span id="playBtnText">Iniciar Acompanhamento</span>
                    </button>
                </div>
            </div>

            <!-- CARTÃO DE MICROFONE & ANALISADOR -->
            <div class="studioCard">
                <h2 class="cardTitle">
                    <span class="icon">🎙️</span>
                    <span>Analisador de Canto & Tom</span>
                </h2>

                <!-- Ativação de microfone -->
                <button type="button" class="microphoneToggleBtn" id="micBtn" onclick="toggleMicrophone()">
                    <span id="micBtnIcon">🎤</span>
                    <span id="micBtnText">Ativar Microfone</span>
                </button>

                <!-- Display do Pitch -->
                <div class="pitchDisplayContainer">
                    <p class="pitchNoteName" id="pitchNote">-</p>
                    <span class="pitchFrequency" id="pitchFreq">Aguardando áudio...</span>
                    
                    <!-- Afinador de Cents (Canvas Chromatic Dial) -->
                    <div class="gaugeContainer" style="width: 100%; height: 160px; position: relative; margin-top: 15px;">
                        <canvas id="jamGaugeCanvas" style="width: 100%; height: 100%; display: block;"></canvas>
                    </div>
                    
                    <!-- Feedback de Voz -->
                    <div id="vocalFeedbackContainer" style="display: none; margin-top: 16px; padding: 14px; border-radius: 12px; background: rgba(255, 255, 255, 0.03); border: 1px solid var(--line); font-size: 13px; text-align: center; color: var(--text); transition: all 0.3s ease;">
                        <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: var(--accent); margin-bottom: 6px; letter-spacing: 0.05em;">Feedback de Voz IA</div>
                        <span id="vocalFeedbackText" style="font-weight: 600; line-height: 1.4; display: block;"></span>
                    </div>
                </div>

                <!-- Detector de Campo Harmônico / Tom Cantado -->
                <div class="scaleSuggesterBox">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <label>Notas Cantadas Detectadas</label>
                        <div>
                            <button type="button" class="clearHistoryBtn" onclick="simulateRandomSinging()" style="margin-right: 5px;">Simular 3 Notas</button>
                            <button type="button" class="clearHistoryBtn" onclick="clearNoteHistory()">Limpar Notas</button>
                        </div>
                    </div>
                    
                    <!-- Chips de notas acumuladas -->
                    <div class="detectedNotesRow" id="detectedNotesArea">
                        <span style="color: var(--muted); font-size: 12px; font-style: italic;">Nenhuma nota cantada ainda.</span>
                    </div>

                    <!-- Lista de escalas sugeridas -->
                    <div style="display: flex; flex-direction: column; gap: 4px; margin-top: 5px;">
                        <label>Escalas / Tons Sugeridos</label>
                        <div class="scaleSuggestionsList" id="scaleSuggestionsArea">
                            <div class="suggestionRow">
                                <span style="color: var(--muted); font-size: 12px;">Cante pelo menos 3 notas diferentes para receber sugestões.</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Lógica de áudio e interface do JamStudio
        
        // --- 1. CONFIGURAÇÕES & DADOS GERAIS ---
        let currentKey = "C";
        let currentScaleMode = "Major"; // 'Major' ou 'Minor'
        let currentStyle = "Pop";
        let bpm = 120;
        let currentTimeSignature = "4/4";
        
        const noteNames = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
        const rootMidiOffsets = {
            "C": 48, "C#": 49, "D": 50, "D#": 51, "E": 40, "F": 41, 
            "F#": 42, "G": 43, "G#": 44, "A": 45, "A#": 46, "B": 47
        };

        // --- 2. SINTETIZADOR E AUDIO CONTEXT DO PLAYALONG ---
        let audioCtx = null;
        let masterGain = null;
        let analyserNode = null;
        
        let playalongIntervalId = null;
        let isPlaying = false;
        
        // Instrumentos SoundFont reais
        let pianoInstrument = null;
        let bassInstrument = null;
        let isInstrumentsLoading = false;
        let instrumentsLoaded = false;
        
        let nextNoteTime = 0.0;
        let current8thNote = 0; // 0 a 7 por compasso (Pop, Blues, Reggae)
        const lookahead = 25.0; // milissegundos
        const scheduleAheadTime = 0.1; // segundos
        
        let noiseBuffer = null;
        let activeSynthOscs = [];
        
        // Lógica de Tap Tempo
        let tapTimes = [];
        function tapTempo() {
            const now = performance.now();
            tapTimes.push(now);
            if (tapTimes.length > 4) {
                tapTimes.shift();
            }
            if (tapTimes.length > 1) {
                let intervals = [];
                for (let i = 1; i < tapTimes.length; i++) {
                    intervals.push(tapTimes[i] - tapTimes[i - 1]);
                }
                let avgInterval = intervals.reduce((a, b) => a + b) / intervals.length;
                let calculatedBpm = Math.round(60000 / avgInterval);
                if (calculatedBpm >= 60 && calculatedBpm <= 200) {
                    updateBPM(calculatedBpm);
                    document.getElementById("bpmSlider").value = calculatedBpm;
                }
            }
        }
        
        function updateBPM(val) {
            bpm = parseInt(val);
            document.getElementById("bpmDisplay").innerText = bpm + " BPM";
        }
        
        function setScaleMode(mode) {
            currentScaleMode = mode;
            document.getElementById("scaleMajorBtn").classList.toggle("active", mode === "Major");
            document.getElementById("scaleMinorBtn").classList.toggle("active", mode === "Minor");
            updateChordDisplay();
        }
        
        function selectKey(key) {
            currentKey = key;
            document.querySelectorAll(".keyGrid .keyBtn").forEach(btn => {
                btn.classList.toggle("active", btn.getAttribute("data-key") === key);
            });
            updateChordDisplay();
        }
        
        function selectStyle(style) {
            currentStyle = style;
            document.querySelectorAll(".styleSelector .styleCard").forEach(card => {
                card.classList.toggle("active", card.id === "style" + style);
            });
            
            // Resetar posição do compasso ao mudar de estilo para evitar quebra de acordes
            if (isPlaying) {
                current8thNote = 0;
                if (audioCtx) nextNoteTime = audioCtx.currentTime;
            }
            updateChordDisplay();
        }
        function setTimeSignature(ts) {
            currentTimeSignature = ts;
            document.getElementById("ts44Btn").classList.toggle("active", ts === "4/4");
            document.getElementById("ts34Btn").classList.toggle("active", ts === "3/4");
            document.getElementById("ts68Btn").classList.toggle("active", ts === "6/8");
            
            if (isPlaying) {
                current8thNote = 0;
                if (audioCtx) nextNoteTime = audioCtx.currentTime;
            }
            
            updateSequencerDots();
            updateChordDisplay();
        }
        
        function updateSequencerDots() {
            let steps = (currentTimeSignature === "4/4") ? 8 : 6;
            let container = document.querySelector(".beatSequencerDots");
            if (container) {
                container.innerHTML = "";
                for (let i = 0; i < steps; i++) {
                    let dot = document.createElement("div");
                    dot.className = "sequencerDot";
                    dot.setAttribute("data-beat", i);
                    container.appendChild(dot);
                }
            }
        }

        // --- 3. GERAÇÃO DE ROTEAMENTO DE ACORDES ---
        // Retorna as notas (midi numbers) do acorde baseado na escala e estilo
        function getChordForStep(step) {
            const keyIndex = noteNames.indexOf(currentKey);
            const baseMidi = rootMidiOffsets[currentKey];
            
            let stepsPerBar = (currentTimeSignature === "4/4") ? 8 : 6;
            let bar = Math.floor(step / stepsPerBar); // compasso atual
            
            // Intervalos das escalas
            // Major: I=0, ii=2, iii=4, IV=5, V=7, vi=9, vii=11
            // Minor: i=0, iiø=2, III=3, iv=5, V=7, VI=8, VII=10
            
            let degreeOffset = 0; // diferença em semitones da raiz
            let chordType = "Major"; // Major, Minor, Dom7, Maj7, Min7, HalfDim
            
            if (currentScaleMode === "Major") {
                if (currentStyle === "Pop") {
                    const progression = [
                        { deg: 0, type: "Major" },  // I
                        { deg: 7, type: "Major" },  // V
                        { deg: 9, type: "Minor" },  // vi
                        { deg: 5, type: "Major" }   // IV
                    ];
                    let currentChord = progression[bar % 4];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                } else if (currentStyle === "Rock") {
                    // I - IV - I - V
                    const progression = [
                        { deg: 0, type: "Major" },  // I
                        { deg: 5, type: "Major" },  // IV
                        { deg: 0, type: "Major" },  // I
                        { deg: 7, type: "Major" }   // V
                    ];
                    let currentChord = progression[bar % 4];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                } else if (currentStyle === "Jazz") {
                    // ii7 - V7 - Imaj7 - Imaj7
                    const progression = [
                        { deg: 2, type: "Min7" },   // ii7
                        { deg: 7, type: "Dom7" },   // V7
                        { deg: 0, type: "Maj7" },   // Imaj7
                        { deg: 0, type: "Maj7" }    // Imaj7
                    ];
                    let currentChord = progression[bar % 4];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                } else if (currentStyle === "Reggae") {
                    // I - IV - V - IV
                    const progression = [
                        { deg: 0, type: "Major" },  // I
                        { deg: 5, type: "Major" },  // IV
                        { deg: 7, type: "Major" },  // V
                        { deg: 5, type: "Major" }   // IV
                    ];
                    let currentChord = progression[bar % 4];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                } else if (currentStyle === "Country") {
                    // I - IV - V - V
                    const progression = [
                        { deg: 0, type: "Major" },  // I
                        { deg: 5, type: "Major" },  // IV
                        { deg: 7, type: "Major" },  // V
                        { deg: 7, type: "Major" }   // V
                    ];
                    let currentChord = progression[bar % 4];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                } else if (currentStyle === "Balada") {
                    // I - vi - IV - V
                    const progression = [
                        { deg: 0, type: "Major" },  // I
                        { deg: 9, type: "Minor" },  // vi
                        { deg: 5, type: "Major" },  // IV
                        { deg: 7, type: "Major" }   // V
                    ];
                    let currentChord = progression[bar % 4];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                } else if (currentStyle === "Soul") {
                    // I - iii - vi - IV
                    const progression = [
                        { deg: 0, type: "Major" },  // I
                        { deg: 4, type: "Minor" },  // iii
                        { deg: 9, type: "Minor" },  // vi
                        { deg: 5, type: "Major" }   // IV
                    ];
                    let currentChord = progression[bar % 4];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                } else if (currentStyle === "Alternativo") {
                    // vi - IV - I - V
                    const progression = [
                        { deg: 9, type: "Minor" },  // vi
                        { deg: 5, type: "Major" },  // IV
                        { deg: 0, type: "Major" },  // I
                        { deg: 7, type: "Major" }   // V
                    ];
                    let currentChord = progression[bar % 4];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                } else if (currentStyle === "Bossa") {
                    // ii9 - V13 - Imaj7 - Imaj7 (usando extensões!)
                    const progression = [
                        { deg: 2, type: "Min7" },   // ii7
                        { deg: 7, type: "Dom7" },   // V7
                        { deg: 0, type: "Maj7" },   // Imaj7
                        { deg: 0, type: "Maj7" }    // Imaj7
                    ];
                    let currentChord = progression[bar % 4];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                } else if (currentStyle === "Funk") {
                    // i7 - IV7 - i7 - IV7 (Dorian Groove)
                    const progression = [
                        { deg: 9, type: "Min7" },   // vi (dorian i)
                        { deg: 2, type: "Dom7" },   // ii (dorian IV)
                        { deg: 9, type: "Min7" },
                        { deg: 2, type: "Dom7" }
                    ];
                    let currentChord = progression[bar % 4];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                } else if (currentStyle === "Blues") {
                    const bluesProg = [
                        0, 0, 0, 0,
                        5, 5,
                        0, 0,
                        7, 5,
                        0, 0
                    ];
                    degreeOffset = bluesProg[bar % 12];
                    chordType = "Dom7";
                }
            } else { // Minor Scale Mode
                if (currentStyle === "Pop") {
                    const progression = [
                        { deg: 0, type: "Minor" },  // i
                        { deg: 8, type: "Major" },  // VI
                        { deg: 3, type: "Major" },  // III
                        { deg: 10, type: "Major" }  // VII
                    ];
                    let currentChord = progression[bar % 4];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                } else if (currentStyle === "Rock") {
                    // i - iv - i - V
                    const progression = [
                        { deg: 0, type: "Minor" },
                        { deg: 5, type: "Minor" },
                        { deg: 0, type: "Minor" },
                        { deg: 7, type: "Major" }
                    ];
                    let currentChord = progression[bar % 4];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                } else if (currentStyle === "Jazz" || currentStyle === "Bossa") {
                    // iiø7 - V7 - i7 - i7
                    const progression = [
                        { deg: 2, type: "HalfDim" },
                        { deg: 7, type: "Dom7" },
                        { deg: 0, type: "Min7" },
                        { deg: 0, type: "Min7" }
                    ];
                    let currentChord = progression[bar % 4];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                } else if (currentStyle === "Reggae") {
                    // i - iv - V - iv
                    const progression = [
                        { deg: 0, type: "Minor" },
                        { deg: 5, type: "Minor" },
                        { deg: 7, type: "Major" },
                        { deg: 5, type: "Minor" }
                    ];
                    let currentChord = progression[bar % 4];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                } else if (currentStyle === "Country") {
                    // i - iv - v - v
                    const progression = [
                        { deg: 0, type: "Minor" },
                        { deg: 5, type: "Minor" },
                        { deg: 7, type: "Minor" },
                        { deg: 7, type: "Minor" }
                    ];
                    let currentChord = progression[bar % 4];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                } else if (currentStyle === "Balada") {
                    // i - VI - iv - v
                    const progression = [
                        { deg: 0, type: "Minor" },
                        { deg: 8, type: "Major" },
                        { deg: 5, type: "Minor" },
                        { deg: 7, type: "Minor" }
                    ];
                    let currentChord = progression[bar % 4];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                } else if (currentStyle === "Soul") {
                    // i - III - VI - iv
                    const progression = [
                        { deg: 0, type: "Minor" },
                        { deg: 3, type: "Major" },
                        { deg: 8, type: "Major" },
                        { deg: 5, type: "Minor" }
                    ];
                    let currentChord = progression[bar % 4];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                } else if (currentStyle === "Alternativo") {
                    // VI - iv - i - v
                    const progression = [
                        { deg: 8, type: "Major" },
                        { deg: 5, type: "Minor" },
                        { deg: 0, type: "Minor" },
                        { deg: 7, type: "Minor" }
                    ];
                    let currentChord = progression[bar % 4];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                } else if (currentStyle === "Funk") {
                    // i7 - IV7
                    const progression = [
                        { deg: 0, type: "Min7" },
                        { deg: 5, type: "Dom7" },
                        { deg: 0, type: "Min7" },
                        { deg: 5, type: "Dom7" }
                    ];
                    let currentChord = progression[bar % 4];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                } else if (currentStyle === "Blues") {
                    const bluesProg = [
                        { deg: 0, type: "Min7" }, { deg: 0, type: "Min7" }, { deg: 0, type: "Min7" }, { deg: 0, type: "Min7" },
                        { deg: 5, type: "Min7" }, { deg: 5, type: "Min7" },
                        { deg: 0, type: "Min7" }, { deg: 0, type: "Min7" },
                        { deg: 7, type: "Dom7" }, { deg: 5, type: "Min7" },
                        { deg: 0, type: "Min7" }, { deg: 0, type: "Min7" }
                    ];
                    let currentChord = bluesProg[bar % 12];
                    degreeOffset = currentChord.deg;
                    chordType = currentChord.type;
                }
            }
            
            // Raiz do acorde
            let chordRootIndex = (keyIndex + degreeOffset) % 12;
            let chordRootName = noteNames[chordRootIndex];
            
            // Calcular MIDI root e notas da tríade/tétrade
            let chordRootMidi = baseMidi + degreeOffset;
            if (chordRootMidi >= 60) chordRootMidi -= 12; // manter no baixo
            
            let chordNotes = [];
            let rootForChord = chordRootMidi + 12; // o acorde toca uma oitava acima do baixo
            
            if (chordType === "Major") {
                chordNotes = [rootForChord, rootForChord + 4, rootForChord + 7];
            } else if (chordType === "Minor") {
                chordNotes = [rootForChord, rootForChord + 3, rootForChord + 7];
            } else if (chordType === "Maj7") {
                chordNotes = [rootForChord, rootForChord + 4, rootForChord + 7, rootForChord + 11];
            } else if (chordType === "Min7") {
                chordNotes = [rootForChord, rootForChord + 3, rootForChord + 7, rootForChord + 10];
            } else if (chordType === "Dom7") {
                chordNotes = [rootForChord, rootForChord + 4, rootForChord + 7, rootForChord + 10];
            } else if (chordType === "HalfDim") {
                chordNotes = [rootForChord, rootForChord + 3, rootForChord + 6, rootForChord + 10];
            }
            
            let label = chordRootName;
            if (chordType === "Minor") label += "m";
            else if (chordType === "Maj7") label += "maj7";
            else if (chordType === "Min7") label += "m7";
            else if (chordType === "Dom7") label += "7";
            else if (chordType === "HalfDim") label += "m7(b5)";
            
            return {
                rootMidi: chordRootMidi,
                notes: chordNotes,
                label: label
            };
        }
        
        function updateChordDisplay(step) {
            if (!isPlaying) {
                document.getElementById("currentChordDisplay").innerText = "";
                return;
            }
            let activeStep = (step !== undefined) ? step : current8thNote;
            let info = getChordForStep(activeStep);
            document.getElementById("currentChordDisplay").innerText = "Acorde: " + info.label;
        }

        // --- 4. ENGINE DE ÁUDIO WEB AUDIO ---
        
        function initAudio() {
            if (audioCtx) return;
            
            // Garantir suporte ao AudioContext
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            audioCtx = new AudioCtx();
            
            // Ganho Master
            masterGain = audioCtx.createGain();
            masterGain.gain.setValueAtTime(0.5, audioCtx.currentTime); // volume confortável
            
            // Analisador para o visualizador do synth
            analyserNode = audioCtx.createAnalyser();
            analyserNode.fftSize = 256;
            
            masterGain.connect(analyserNode);
            analyserNode.connect(audioCtx.destination);
            
            // Criar buffer de ruído branco para bateria (snare/hihat)
            let bufferSize = 2 * audioCtx.sampleRate;
            let noiseBufferData = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
            let output = noiseBufferData.getChannelData(0);
            for (let i = 0; i < bufferSize; i++) {
                output[i] = Math.random() * 2 - 1;
            }
            noiseBuffer = noiseBufferData;
            
            // Iniciar animação do visualizador
            drawSynthVisualizer();
        }
        
        function midiToFreq(note) {
            return 440 * Math.pow(2, (note - 69) / 12);
        }
        
        // --- 5. SINTETIZADORES ---
        
        function playKick(time) {
            let osc = audioCtx.createOscillator();
            let gain = audioCtx.createGain();
            osc.connect(gain);
            gain.connect(masterGain);
            
            osc.frequency.setValueAtTime(150, time);
            osc.frequency.exponentialRampToValueAtTime(45, time + 0.12);
            
            gain.gain.setValueAtTime(1.0, time);
            gain.gain.exponentialRampToValueAtTime(0.01, time + 0.12);
            
            osc.start(time);
            osc.stop(time + 0.13);
        }
        
        function playSnare(time) {
            // Ruído branco filtrado
            let noise = audioCtx.createBufferSource();
            noise.buffer = noiseBuffer;
            
            let filter = audioCtx.createBiquadFilter();
            filter.type = "bandpass";
            filter.frequency.setValueAtTime(1100, time);
            
            let gain = audioCtx.createGain();
            noise.connect(filter);
            filter.connect(gain);
            gain.connect(masterGain);
            
            gain.gain.setValueAtTime(0.4, time);
            gain.gain.exponentialRampToValueAtTime(0.01, time + 0.18);
            
            noise.start(time);
            noise.stop(time + 0.19);
            
            // Snap inicial senoidal
            let snap = audioCtx.createOscillator();
            let snapGain = audioCtx.createGain();
            snap.connect(snapGain);
            snapGain.connect(masterGain);
            
            snap.frequency.setValueAtTime(180, time);
            snapGain.gain.setValueAtTime(0.5, time);
            snapGain.gain.exponentialRampToValueAtTime(0.01, time + 0.08);
            
            snap.start(time);
            snap.stop(time + 0.09);
        }
        
        function playHihat(time, vol = 0.2) {
            let noise = audioCtx.createBufferSource();
            noise.buffer = noiseBuffer;
            
            let filter = audioCtx.createBiquadFilter();
            filter.type = "highpass";
            filter.frequency.setValueAtTime(7500, time);
            
            let gain = audioCtx.createGain();
            noise.connect(filter);
            filter.connect(gain);
            gain.connect(masterGain);
            
            gain.gain.setValueAtTime(vol, time);
            gain.gain.exponentialRampToValueAtTime(0.01, time + 0.05);
            
            noise.start(time);
            noise.stop(time + 0.06);
        }
        
        function playBass(note, time, duration) {
            if (instrumentsLoaded && bassInstrument) {
                bassInstrument.play(note, time, { duration: duration, gain: 0.8 });
            } else {
                let osc = audioCtx.createOscillator();
                let gain = audioCtx.createGain();
                
                // Combinação clássica: onda triangular com leve low-pass para um baixo aveludado e cheio
                osc.type = "triangle";
                osc.connect(gain);
                gain.connect(masterGain);
                
                let freq = midiToFreq(note);
                osc.frequency.setValueAtTime(freq, time);
                
                gain.gain.setValueAtTime(0.0, time);
                gain.gain.linearRampToValueAtTime(0.65, time + 0.02);
                gain.gain.setValueAtTime(0.65, time + duration - 0.04);
                gain.gain.exponentialRampToValueAtTime(0.005, time + duration);
                
                osc.start(time);
                osc.stop(time + duration + 0.01);
            }
        }
        
        function playChord(notes, time, duration) {
            if (instrumentsLoaded && pianoInstrument) {
                notes.forEach(note => {
                    pianoInstrument.play(note, time, { duration: duration, gain: 0.5 });
                });
            } else {
                notes.forEach(note => {
                    let osc1 = audioCtx.createOscillator();
                    let osc2 = audioCtx.createOscillator();
                    let filter = audioCtx.createBiquadFilter();
                    let gain = audioCtx.createGain();
                    
                    osc1.type = "triangle";
                    osc2.type = "sawtooth";
                    osc2.detune.setValueAtTime(12, time); // detune para efeito chorus stereo / rico
                    
                    osc1.connect(filter);
                    osc2.connect(filter);
                    filter.connect(gain);
                    gain.connect(masterGain);
                    
                    filter.type = "lowpass";
                    filter.frequency.setValueAtTime(350, time);
                    filter.frequency.exponentialRampToValueAtTime(700, time + 0.4); // envelope de filtro
                    
                    let freq = midiToFreq(note);
                    osc1.frequency.setValueAtTime(freq, time);
                    osc2.frequency.setValueAtTime(freq, time);
                    
                    gain.gain.setValueAtTime(0.0, time);
                    gain.gain.linearRampToValueAtTime(0.18, time + 0.08); // ataque suave
                    gain.gain.setValueAtTime(0.18, time + duration - 0.08);
                    gain.gain.exponentialRampToValueAtTime(0.001, time + duration);
                    
                    osc1.start(time);
                    osc2.start(time);
                    
                    osc1.stop(time + duration);
                    osc2.stop(time + duration);
                });
            }
        }

        // --- 6. AGENDADOR DE RITMO (SCHEDULER) ---
        
        function scheduler() {
            // Impedir empilhamento de notas por atraso de aba em segundo plano
            if (nextNoteTime < audioCtx.currentTime) {
                nextNoteTime = audioCtx.currentTime;
            }
            while (nextNoteTime < audioCtx.currentTime + scheduleAheadTime) {
                scheduleNote(current8thNote, nextNoteTime);
                next8thNote();
            }
        }
        
        function next8thNote() {
            let secondsPerBeat = 60.0 / bpm;
            let secondsPerStep;
            
            if (currentTimeSignature === "4/4" || currentTimeSignature === "3/4") {
                secondsPerStep = 0.5 * secondsPerBeat; // colcheia
            } else if (currentTimeSignature === "6/8") {
                secondsPerStep = (1/3) * secondsPerBeat; // semínima pontuada dividida por 3
            }
            
            nextNoteTime += secondsPerStep;
            current8thNote++;
            
            let stepsPerBar = (currentTimeSignature === "4/4") ? 8 : 6;
            let numBars = (currentStyle === "Blues") ? 12 : 4;
            let totalSteps = stepsPerBar * numBars;
            
            if (current8thNote >= totalSteps) {
                current8thNote = 0;
            }
        }
        
        function scheduleNote(step, time) {
            let chordInfo = getChordForStep(step);
            let stepsPerBar = (currentTimeSignature === "4/4") ? 8 : 6;
            let barStep = step % stepsPerBar; // passo do compasso
            
            let beatDuration = 60.0 / bpm;
            let stepDuration;
            
            if (currentTimeSignature === "4/4" || currentTimeSignature === "3/4") {
                stepDuration = 0.5 * beatDuration; // colcheia
            } else if (currentTimeSignature === "6/8") {
                stepDuration = (1/3) * beatDuration; // semínima pontuada dividida por 3
            }
            
            // --- GESTÃO DE ESTILOS E FÓRMULAS DE COMPASSO ---
            
            if (currentStyle === "Pop") {
                if (currentTimeSignature === "4/4") {
                    // DRUMS
                    if (barStep === 0 || barStep === 4) playKick(time);
                    if (barStep === 2 || barStep === 6) playSnare(time);
                    playHihat(time, (barStep % 2 === 0) ? 0.15 : 0.07);
                    
                    // BASS
                    if (barStep === 0) playBass(chordInfo.rootMidi, time, stepDuration * 3.8);
                    else if (barStep === 4) playBass(chordInfo.rootMidi + 7, time, stepDuration * 3.8);
                    
                    // CHORDS
                    if (barStep === 0) playChord(chordInfo.notes, time, stepDuration * 7.8);
                } else if (currentTimeSignature === "3/4") {
                    // Pop Waltz
                    if (barStep === 0) playKick(time);
                    if (barStep === 2 || barStep === 4) playSnare(time);
                    playHihat(time, (barStep % 2 === 0) ? 0.15 : 0.07);
                    
                    if (barStep === 0) playBass(chordInfo.rootMidi, time, stepDuration * 3.8);
                    
                    if (barStep === 0) playChord(chordInfo.notes, time, stepDuration * 5.8);
                } else if (currentTimeSignature === "6/8") {
                    // Pop 6/8 Ballad
                    if (barStep === 0) playKick(time);
                    if (barStep === 3) playSnare(time);
                    playHihat(time, 0.12);
                    
                    if (barStep === 0) playBass(chordInfo.rootMidi, time, stepDuration * 2.8);
                    if (barStep === 3) playBass(chordInfo.rootMidi + 7, time, stepDuration * 2.8);
                    
                    if (barStep === 0 || barStep === 3) playChord(chordInfo.notes, time, stepDuration * 2.8);
                }
            }
            
            else if (currentStyle === "Reggae") {
                if (currentTimeSignature === "4/4") {
                    if (barStep === 4) { playKick(time); playSnare(time); }
                    playHihat(time, 0.15);
                    
                    if (barStep === 0) playBass(chordInfo.rootMidi, time, stepDuration * 1.5);
                    else if (barStep === 3) playBass(chordInfo.rootMidi + 7, time, stepDuration * 0.8);
                    else if (barStep === 4) playBass(chordInfo.rootMidi, time, stepDuration * 1.5);
                    else if (barStep === 7) playBass(chordInfo.rootMidi + 4, time, stepDuration * 0.8);
                    
                    if (barStep === 2 || barStep === 6) playChord(chordInfo.notes, time, 0.10);
                } else {
                    // Reggae 3/4 ou 6/8
                    if (barStep === 3) { playKick(time); playSnare(time); }
                    playHihat(time, 0.12);
                    
                    if (barStep === 0) playBass(chordInfo.rootMidi, time, stepDuration * 1.8);
                    else if (barStep === 3) playBass(chordInfo.rootMidi + 7, time, stepDuration * 1.8);
                    
                    if (barStep === 1 || barStep === 4) playChord(chordInfo.notes, time, 0.08);
                }
            }
            
            else if (currentStyle === "Jazz") {
                if (currentTimeSignature === "4/4") {
                    if (barStep === 0 || barStep === 4) playKick(time);
                    if (barStep === 2 || barStep === 6) playHihat(time, 0.18);
                    if (barStep % 2 === 0) playHihat(time + 0.01, 0.15);
                    if (barStep === 1 || barStep === 5) playHihat(time + (stepDuration * 0.6), 0.08);
                    
                    // Walking bass
                    if (barStep % 2 === 0) {
                        let beatNum = barStep / 2;
                        let bassNote = chordInfo.rootMidi;
                        if (beatNum === 1) bassNote = chordInfo.rootMidi + 4;
                        else if (beatNum === 2) bassNote = chordInfo.rootMidi + 7;
                        else if (barStep === 6) { // Ajuste para beat 3 no passo 6 (4/4)
                             let nextChordInfo = getChordForStep(step + 2);
                             bassNote = nextChordInfo.rootMidi - 1;
                        }
                        playBass(bassNote, time, stepDuration * 1.8);
                    }
                    if (barStep === 0) playChord(chordInfo.notes, time, stepDuration * 1.2);
                    else if (barStep === 3) playChord(chordInfo.notes, time, stepDuration * 0.8);
                } else {
                    // Jazz 3/4 ou 6/8 (Jazz Waltz)
                    if (barStep === 0) playKick(time);
                    playHihat(time, 0.15);
                    
                    if (barStep === 0) playBass(chordInfo.rootMidi, time, stepDuration * 1.8);
                    else if (barStep === 2) playBass(chordInfo.rootMidi + 4, time, stepDuration * 1.8);
                    else if (barStep === 4) playBass(chordInfo.rootMidi + 7, time, stepDuration * 1.8);
                    
                    if (barStep === 0) playChord(chordInfo.notes, time, stepDuration * 3.8);
                }
            }
            
            else if (currentStyle === "Blues") {
                if (currentTimeSignature === "4/4") {
                    if (barStep === 0 || barStep === 4) playKick(time);
                    if (barStep === 2 || barStep === 6) playSnare(time);
                    playHihat(time, 0.18);
                    if (barStep % 2 === 0) playHihat(time + (stepDuration * 0.6), 0.08);
                    
                    // Boogie Woogie Bass
                    if (barStep % 2 === 0) {
                        let beatNum = barStep / 2;
                        let bassNote = chordInfo.rootMidi;
                        if (beatNum === 1) bassNote = chordInfo.rootMidi + 4;
                        else if (beatNum === 2) bassNote = chordInfo.rootMidi + 7;
                        else if (beatNum === 3) bassNote = chordInfo.rootMidi + 9;
                        playBass(bassNote, time, stepDuration * 1.8);
                    }
                    if (barStep === 0 || barStep === 4) playChord(chordInfo.notes, time, stepDuration * 3.8);
                } else {
                    // Blues slow 6/8 ou 3/4
                    if (barStep === 0) playKick(time);
                    if (barStep === 3) playSnare(time);
                    playHihat(time, 0.15);
                    
                    if (barStep === 0) playBass(chordInfo.rootMidi, time, stepDuration * 2.8);
                    else if (barStep === 2) playBass(chordInfo.rootMidi + 4, time, stepDuration * 2.8);
                    else if (barStep === 4) playBass(chordInfo.rootMidi + 7, time, stepDuration * 2.8);
                    
                    if (barStep === 0 || barStep === 3) playChord(chordInfo.notes, time, stepDuration * 2.8);
                }
            }
            
            else if (currentStyle === "Rock" || currentStyle === "Alternativo") {
                if (currentTimeSignature === "4/4") {
                    if (barStep === 0 || barStep === 4) playKick(time);
                    if (barStep === 2 || barStep === 6) playSnare(time);
                    playHihat(time, 0.15);
                    
                    if (barStep === 0) playBass(chordInfo.rootMidi, time, stepDuration * 3.8);
                    else if (barStep === 4) playBass(chordInfo.rootMidi + 7, time, stepDuration * 3.8);
                    
                    if (barStep === 0) playChord(chordInfo.notes, time, stepDuration * 7.8);
                } else {
                    if (barStep === 0) playKick(time);
                    if (barStep === 2 || barStep === 4) playSnare(time);
                    playHihat(time, 0.15);
                    if (barStep === 0) playBass(chordInfo.rootMidi, time, stepDuration * 3.8);
                    if (barStep === 0) playChord(chordInfo.notes, time, stepDuration * 5.8);
                }
            }
            
            else if (currentStyle === "Country") {
                if (currentTimeSignature === "4/4") {
                    if (barStep === 0 || barStep === 4) playKick(time);
                    if (barStep === 2 || barStep === 6) playSnare(time);
                    playHihat(time, 0.10);
                    
                    if (barStep === 0) playBass(chordInfo.rootMidi, time, stepDuration * 3.5);
                    else if (barStep === 4) playBass(chordInfo.rootMidi + 7, time, stepDuration * 3.5);
                    
                    if (barStep === 2 || barStep === 6) playChord(chordInfo.notes, time, stepDuration * 1.8);
                } else {
                    if (barStep === 0) playKick(time);
                    if (barStep === 2 || barStep === 4) playSnare(time);
                    playHihat(time, 0.10);
                    if (barStep === 0) playBass(chordInfo.rootMidi, time, stepDuration * 3.5);
                    if (barStep === 2) playChord(chordInfo.notes, time, stepDuration * 1.8);
                }
            }
            
            else if (currentStyle === "Balada" || currentStyle === "Soul") {
                if (currentTimeSignature === "4/4") {
                    if (barStep === 0 || barStep === 4) playKick(time);
                    if (barStep === 2 || barStep === 6) playHihat(time, 0.15);
                    
                    if (barStep === 0) playBass(chordInfo.rootMidi, time, stepDuration * 7.5);
                    
                    if (barStep === 0) playChord(chordInfo.notes, time, stepDuration * 7.8);
                } else {
                    if (barStep === 0) playKick(time);
                    if (barStep === 2) playHihat(time, 0.15);
                    if (barStep === 0) playBass(chordInfo.rootMidi, time, stepDuration * 5.5);
                    if (barStep === 0) playChord(chordInfo.notes, time, stepDuration * 5.8);
                }
            }
            
            else if (currentStyle === "Bossa") {
                if (barStep === 0) playKick(time);
                if (barStep === 3) playKick(time + 0.05);
                playHihat(time, 0.08);
                
                if (barStep === 0) playBass(chordInfo.rootMidi, time, stepDuration * 2.5);
                else if (barStep === 3) playBass(chordInfo.rootMidi + 7, time, stepDuration * 2.5);
                
                if (barStep === 0 || barStep === 2 || barStep === 3 || barStep === 5) {
                    playChord(chordInfo.notes, time, 0.18);
                }
            }
            
            else if (currentStyle === "Funk") {
                if (barStep === 0 || barStep === 4) playKick(time);
                if (barStep === 2 || barStep === 6) playSnare(time);
                playHihat(time, (barStep % 2 === 0) ? 0.18 : 0.09);
                
                if (barStep === 0) playBass(chordInfo.rootMidi, time, stepDuration * 1.5);
                else if (barStep === 3) playBass(chordInfo.rootMidi + 5, time, stepDuration * 1.2);
                else if (barStep === 5) playBass(chordInfo.rootMidi + 7, time, stepDuration * 0.8);
                
                if (barStep === 2 || barStep === 3 || barStep === 6 || barStep === 7) {
                    playChord(chordInfo.notes, time, 0.08);
                }
            }
            
            // Atualizar UI no compasso principal
            setTimeout(() => {
                if (!isPlaying) return;
                updateVisualMetronome(barStep, step);
            }, (time - audioCtx.currentTime) * 1000);
        }

        // --- 7. ATUALIZAÇÕES VISUAIS DA ROTAÇÃO DO PLAYALONG ---
        
        function updateVisualMetronome(barStep, step) {
            let dot = document.getElementById("metronomeDot");
            let beats = (currentTimeSignature === "4/4") ? [0, 2, 4, 6] : (currentTimeSignature === "3/4" ? [0, 2, 4] : [0, 3]);
            let activeBeat = beats.indexOf(barStep);
            
            if (activeBeat !== -1) {
                dot.style.opacity = "1";
                dot.classList.add("active");
                setTimeout(() => {
                    dot.classList.remove("active");
                }, 80);
            }
            
            // Sequenciador de luzes de compasso
            document.querySelectorAll(".sequencerDot").forEach((d, idx) => {
                d.classList.toggle("active", idx === barStep);
            });
            
            updateChordDisplay(step);
        }
        
        function togglePlayalong() {
            initAudio();
            if (audioCtx.state === "suspended") {
                audioCtx.resume();
            }
            
            isPlaying = !isPlaying;
            let playBtn = document.getElementById("playBtn");
            let playBtnText = document.getElementById("playBtnText");
            let playBtnIcon = document.getElementById("playBtnIcon");
            
            if (isPlaying) {
                if (!instrumentsLoaded) {
                    if (isInstrumentsLoading) {
                        isPlaying = false;
                        return;
                    }
                    isInstrumentsLoading = true;
                    playBtn.disabled = true;
                    let oldText = playBtnText.innerText;
                    let oldIcon = playBtnIcon.innerText;
                    playBtnText.innerText = "Carregando timbres reais (Piano e Baixo)...";
                    playBtnIcon.innerText = "⏳";
                    
                    Promise.all([
                        Soundfont.instrument(audioCtx, 'acoustic_grand_piano'),
                        Soundfont.instrument(audioCtx, 'electric_bass_finger')
                    ]).then(([piano, bass]) => {
                        pianoInstrument = piano;
                        bassInstrument = bass;
                        instrumentsLoaded = true;
                        isInstrumentsLoading = false;
                        playBtn.disabled = false;
                        
                        startPlayalongSession(playBtn, playBtnText, playBtnIcon);
                    }).catch(err => {
                        console.error("Erro ao carregar SoundFont: ", err);
                        isInstrumentsLoading = false;
                        playBtn.disabled = false;
                        instrumentsLoaded = false;
                        
                        startPlayalongSession(playBtn, playBtnText, playBtnIcon);
                    });
                } else {
                    startPlayalongSession(playBtn, playBtnText, playBtnIcon);
                }
            } else {
                stopPlayalongSession(playBtn, playBtnText, playBtnIcon);
            }
        }
        
        function startPlayalongSession(playBtn, playBtnText, playBtnIcon) {
            playBtn.classList.add("playing");
            playBtnText.innerText = "Parar Acompanhamento";
            playBtnIcon.innerText = "⏹";
            
            current8thNote = 0;
            nextNoteTime = audioCtx.currentTime + 0.05;
            
            playalongIntervalId = setInterval(scheduler, lookahead);
            updateChordDisplay();
        }
        
        function stopPlayalongSession(playBtn, playBtnText, playBtnIcon) {
            clearInterval(playalongIntervalId);
            playalongIntervalId = null;
            
            playBtn.classList.remove("playing");
            playBtnText.innerText = "Iniciar Acompanhamento";
            playBtnIcon.innerText = "▶";
            
            document.querySelectorAll(".sequencerDot").forEach(d => d.classList.remove("active"));
            document.getElementById("currentChordDisplay").innerText = "";
        }
        
        // Desenha ondas na tela com o AnalyserNode do synth
        function drawSynthVisualizer() {
            if (!analyserNode) return;
            requestAnimationFrame(drawSynthVisualizer);
            
            let canvas = document.getElementById("synthVisualizer");
            let canvasCtx = canvas.getContext("2d");
            
            let width = canvas.width = canvas.parentElement.clientWidth;
            let height = canvas.height = canvas.parentElement.clientHeight;
            
            let bufferLength = analyserNode.frequencyBinCount;
            let dataArray = new Uint8Array(bufferLength);
            analyserNode.getByteTimeDomainData(dataArray);
            
            canvasCtx.clearRect(0, 0, width, height);
            canvasCtx.lineWidth = 2.5;
            
            // Gradiente neon azul/laranja
            let gradient = canvasCtx.createLinearGradient(0, 0, width, 0);
            gradient.addColorStop(0, '#2563eb');
            gradient.addColorStop(1, '#ff7a00');
            canvasCtx.strokeStyle = gradient;
            
            canvasCtx.beginPath();
            
            let sliceWidth = width * 1.0 / bufferLength;
            let x = 0;
            
            for(let i = 0; i < bufferLength; i++) {
                let v = dataArray[i] / 128.0;
                let y = v * height/2;
                
                if(i === 0) {
                    canvasCtx.moveTo(x, y);
                } else {
                    canvasCtx.lineTo(x, y);
                }
                
                x += sliceWidth;
            }
            
            canvasCtx.lineTo(canvas.width, canvas.height/2);
            canvasCtx.stroke();
        }

        // --- 8. MICROFONE & ANALISADOR DE CANTO ---
        let micStream = null;
        let micSource = null;
        let micAnalyser = null;
        let isMicActive = false;
        let pitchIntervalId = null;
        let detectedNotesSet = new Set();
        let stabilityCount = 0;
        let lastDetectedNote = "";
        
        // Dados do afinador compartilhados com o loop de render do canvas
        window.currentCentsDeviation = 0;
        window.currentNoteName = "-";
        window.lastDetectedPitch = -1;
        
        function toggleMicrophone() {
            isMicActive = !isMicActive;
            let micBtn = document.getElementById("micBtn");
            let micBtnIcon = document.getElementById("micBtnIcon");
            let micBtnText = document.getElementById("micBtnText");
            
            if (isMicActive) {
                // Solicitar permissão de áudio
                navigator.mediaDevices.getUserMedia({ audio: true, video: false })
                .then(stream => {
                    micStream = stream;
                    
                    // Inicializar AudioContext se não existir
                    initAudio();
                    if (audioCtx.state === "suspended") {
                        audioCtx.resume();
                    }
                    
                    micSource = audioCtx.createMediaStreamSource(stream);
                    micAnalyser = audioCtx.createAnalyser();
                    micAnalyser.fftSize = 2048;
                    micSource.connect(micAnalyser);
                    
                    // CORREÇÃO PARA MANTER CORRENTE DE ÁUDIO ATIVA NO CHROME:
                    let silentGain = audioCtx.createGain();
                    silentGain.gain.setValueAtTime(0.0, audioCtx.currentTime);
                    micAnalyser.connect(silentGain);
                    silentGain.connect(audioCtx.destination);
                    
                    micBtn.classList.add("active");
                    micBtnIcon.innerText = "🛑";
                    micBtnText.innerText = "Desativar Microfone";
                    
                    // Iniciar loop de análise
                    analyzePitchLoop();
                })
                .catch(err => {
                    console.error("Erro ao acessar microfone: ", err);
                    alert("Para utilizar o analisador, por favor, permita o acesso ao microfone.");
                    isMicActive = false;
                });
            } else {
                stopMicrophone();
            }
        }
        
        function stopMicrophone() {
            isMicActive = false;
            let micBtn = document.getElementById("micBtn");
            let micBtnIcon = document.getElementById("micBtnIcon");
            let micBtnText = document.getElementById("micBtnText");
            
            micBtn.classList.remove("active");
            micBtnIcon.innerText = "🎤";
            micBtnText.innerText = "Ativar Microfone";
            
            if (pitchIntervalId) {
                cancelAnimationFrame(pitchIntervalId);
                pitchIntervalId = null;
            }
            
            if (micStream) {
                micStream.getTracks().forEach(track => track.stop());
                micStream = null;
            }
            
            document.getElementById("pitchNote").innerText = "-";
            document.getElementById("pitchNote").classList.remove("stable");
            document.getElementById("pitchFreq").innerText = "Microfone desativado.";
            window.lastDetectedPitch = -1;
            window.currentNoteName = "-";
            window.currentCentsDeviation = 0;
        }
        
        // Loop com requestAnimationFrame
        function analyzePitchLoop() {
            if (!isMicActive) return;
            pitchIntervalId = requestAnimationFrame(analyzePitchLoop);
            
            if (typeof window.lastUIUpdateTime === "undefined") {
                window.lastUIUpdateTime = 0;
                window.pitchAccumulator = [];
                window.lastFeedbackTime = 0;
            }
            
            let bufferLength = micAnalyser.fftSize;
            let buffer = new Float32Array(bufferLength);
            if (typeof micAnalyser.getFloat32TimeDomainData === "function") {
                micAnalyser.getFloat32TimeDomainData(buffer);
            } else {
                let byteBuffer = new Uint8Array(bufferLength);
                micAnalyser.getByteTimeDomainData(byteBuffer);
                for (let i = 0; i < bufferLength; i++) {
                    buffer[i] = (byteBuffer[i] - 128) / 128.0;
                }
            }
            
            // Algoritmo de autocorrelação AMDF (Average Magnitude Difference Function)
            let pitch = autoCorrelate(buffer, audioCtx.sampleRate);
            let now = Date.now();
            let shouldUpdateUI = (now - window.lastUIUpdateTime >= 500);
            
            if (pitch !== -1) {
                // Acumular frequências para feedback de 4 segundos
                window.pitchAccumulator.push({ pitch: pitch, time: now });
                window.pitchAccumulator = window.pitchAccumulator.filter(item => now - item.time <= 4000);
                
                // Analisar voz após 4 segundos de canto constante
                if (window.pitchAccumulator.length > 50) {
                    let firstTime = window.pitchAccumulator[0].time;
                    let lastTime = window.pitchAccumulator[window.pitchAccumulator.length - 1].time;
                    if (lastTime - firstTime >= 4000 && now - window.lastFeedbackTime >= 6000) {
                        window.lastFeedbackTime = now;
                        
                        let sum = 0;
                        window.pitchAccumulator.forEach(item => sum += item.pitch);
                        let avgPitch = sum / window.pitchAccumulator.length;
                        
                        let voiceType = "";
                        let desc = "";
                        
                        if (avgPitch > 260) {
                            voiceType = "Soprano 👸";
                            desc = "Olha! Sua voz média está em " + avgPitch.toFixed(0) + " Hz. Você canta de forma aguda e limpa, ideal para vocais melódicos brilhantes!";
                        } else if (avgPitch > 200) {
                            voiceType = "Mezzo-soprano 👩";
                            desc = "Olha! Sua voz média está em " + avgPitch.toFixed(0) + " Hz. Um timbre quente, rico e equilibrado, excelente para transições!";
                        } else if (avgPitch > 150) {
                            voiceType = "Contralto / Tenor 🎤";
                            desc = "Olha! Sua voz média está em " + avgPitch.toFixed(0) + " Hz. Voz potente, encorpada e com excelente sustentação de notas médias!";
                        } else if (avgPitch > 110) {
                            voiceType = "Barítono 👨";
                            desc = "Olha! Sua voz média está em " + avgPitch.toFixed(0) + " Hz. Tom de voz aveludado, encorpado e com excelente ressonância média!";
                        } else {
                            voiceType = "Baixo 🧔";
                            desc = "Olha! Sua voz média está em " + avgPitch.toFixed(0) + " Hz. Graves incríveis e profundos, com uma sustentação robusta e marcante!";
                        }
                        
                        const container = document.getElementById("vocalFeedbackContainer");
                        const text = document.getElementById("vocalFeedbackText");
                        if (container && text) {
                            text.textContent = voiceType + " - " + desc;
                            container.style.display = "block";
                        }
                        
                        window.pitchAccumulator = []; // reset
                    }
                }

                let noteNum = Math.round(12 * Math.log2(pitch / 440)) + 69;
                let noteName = noteNames[noteNum % 12];
                let octave = Math.floor(noteNum / 12) - 1;
                
                // Frequência esperada exata da nota
                let expectedFreq = 440 * Math.pow(2, (noteNum - 69) / 12);
                let cents = Math.round(1200 * Math.log2(pitch / expectedFreq));
                
                window.currentCentsDeviation = cents;
                window.lastDetectedPitch = pitch;
                
                // Estabilização da nota mostrada no dial cromático para evitar oscilações frenéticas
                if (typeof window.noteStabilityCounter === "undefined") {
                    window.noteStabilityCounter = 0;
                    window.tempNoteName = "-";
                }
                if (noteName !== window.tempNoteName) {
                    window.tempNoteName = noteName;
                    window.noteStabilityCounter = 0;
                } else {
                    window.noteStabilityCounter++;
                }
                
                // Exige que a nota permaneça a mesma por pelo menos 10 frames (~160ms) para atualizar o dial
                if (window.noteStabilityCounter >= 10 || window.currentNoteName === "-") {
                    window.currentNoteName = noteName;
                }
                
                if (shouldUpdateUI) {
                    document.getElementById("pitchNote").innerText = noteName + octave;
                    document.getElementById("pitchFreq").innerText = pitch.toFixed(1) + " Hz (" + (cents >= 0 ? "+" : "") + cents + " cents)";
                    window.lastUIUpdateTime = now;
                }
                
                // Se a afinação estiver dentro de 8 cents, considera-se perfeitamente afinado (verde)
                if (typeof window.lastTuningUpdateTime === "undefined") {
                    window.lastTuningUpdateTime = 0;
                }
                let inTune = Math.abs(cents) <= 8;
                let shouldUpdateTuning = (now - window.lastTuningUpdateTime >= 200);
                if (shouldUpdateTuning) {
                    document.getElementById("pitchNote").classList.toggle("stable", inTune);
                    window.lastTuningUpdateTime = now;
                }
                
                // Acumulador de notas para sugestão de escala
                if (inTune) {
                    if (noteName === lastDetectedNote) {
                        stabilityCount++;
                        if (stabilityCount > 8) { // nota mantida estável por várias frames
                            addDetectedNote(noteName);
                        }
                    } else {
                        lastDetectedNote = noteName;
                        stabilityCount = 0;
                    }
                }
            } else {
                // Silêncio / sem sinal coerente
                window.lastDetectedPitch = -1;
                if (shouldUpdateUI) {
                    document.getElementById("pitchFreq").innerText = "Ouvindo...";
                    window.lastUIUpdateTime = now;
                }
            }
        }
        
        // Algoritmo de Autocorrelação para detecção de pitch
        function autoCorrelate(buf, sampleRate) {
            let SIZE = buf.length;
            let rms = 0;

            for (let i = 0; i < SIZE; i++) {
                let val = buf[i];
                rms += val * val;
            }
            rms = Math.sqrt(rms / SIZE);
            
            if (rms < 0.005) { // Limiar de silêncio reduzido para captar vozes mais baixas
                return -1;
            }

            // Autocorrelação direta no buffer inteiro para máxima estabilidade
            let c = new Float32Array(SIZE);
            for (let i = 0; i < SIZE; i++) {
                for (let j = 0; j < SIZE - i; j++) {
                    c[i] = c[i] + buf[j] * buf[j + i];
                }
            }

            let d = 0;
            while (c[d] > c[d + 1]) d++;
            let maxval = -1, maxpos = -1;
            for (let i = d; i < SIZE; i++) {
                if (c[i] > maxval) {
                    maxval = c[i];
                    maxpos = i;
                }
            }
            let T0 = maxpos;

            // Interpolação parabólica para maior precisão matemática
            if (T0 > 0 && T0 < SIZE - 1) {
                let x1 = c[T0 - 1], x2 = c[T0], x3 = c[T0 + 1];
                let a = (x1 + x3 - 2 * x2) / 2;
                let b = (x3 - x1) / 2;
                if (a) T0 = T0 - b / (2 * a);
            }

            let calculatedFreq = sampleRate / T0;
            
            // Frequência aceitável para a voz humana cantando (aprox 50Hz a 1600Hz)
            if (calculatedFreq > 50 && calculatedFreq < 1600) {
                return calculatedFreq;
            }
            return -1;
        }

        // --- 9. SUGESTÕES DE ESCALA ---
        
        const scalesDatabase = {
            "C Maior": ["C", "D", "E", "F", "G", "A", "B"],
            "C# Maior": ["C#", "D#", "F", "F#", "G#", "A#", "C"],
            "D Maior": ["D", "E", "F#", "G", "A", "B", "C#"],
            "D# Maior": ["D#", "F", "G", "G#", "A#", "C", "D"],
            "E Maior": ["E", "F#", "G#", "A", "B", "C#", "D#"],
            "F Maior": ["F", "G", "A", "A#", "C", "D", "E"],
            "F# Maior": ["F#", "G#", "A#", "B", "C#", "D#", "F"],
            "G Maior": ["G", "A", "B", "C", "D", "E", "F#"],
            "G# Maior": ["G#", "A#", "C", "C#", "D#", "F", "G"],
            "A Maior": ["A", "B", "C#", "D", "E", "F#", "G#"],
            "A# Maior": ["A#", "C", "D", "D#", "F", "G", "A"],
            "B Maior": ["B", "C#", "D#", "E", "F#", "G#", "A#"],
            
            "C Menor": ["C", "D", "D#", "F", "G", "G#", "A#"],
            "C# Menor": ["C#", "D#", "E", "F#", "G#", "A", "B"],
            "D Menor": ["D", "E", "F", "G", "A", "A#", "C"],
            "D# Menor": ["D#", "F", "F#", "G#", "A#", "B", "C#"],
            "E Menor": ["E", "F#", "G", "A", "B", "C", "D"],
            "F Menor": ["F", "G", "G#", "A#", "C", "C#", "D#"],
            "F# Menor": ["F#", "G#", "A", "B", "C#", "D", "E"],
            "G Menor": ["G", "A", "A#", "C", "D", "D#", "F"],
            "G# Menor": ["G#", "A#", "B", "C#", "D#", "E", "F#"],
            "A Menor": ["A", "B", "C", "D", "E", "F", "G"],
            "A# Menor": ["A#", "C", "C#", "D#", "F", "F#", "G#"],
            "B Menor": ["B", "C#", "D", "E", "F#", "G", "A"]
        };
        
        function addDetectedNote(note) {
            if (!detectedNotesSet.has(note)) {
                detectedNotesSet.add(note);
                renderDetectedNotes();
                calculateScaleSuggestions();
            }
        }
        
        function renderDetectedNotes() {
            let area = document.getElementById("detectedNotesArea");
            if (detectedNotesSet.size === 0) {
                area.innerHTML = '<span style="color: var(--muted); font-size: 12px; font-style: italic;">Nenhuma nota cantada ainda.</span>';
                return;
            }
            
            area.innerHTML = "";
            detectedNotesSet.forEach(note => {
                let chip = document.createElement("span");
                chip.className = "noteChip";
                chip.innerText = note;
                area.appendChild(chip);
            });
        }
        
        function clearNoteHistory() {
            detectedNotesSet.clear();
            renderDetectedNotes();
            document.getElementById("scaleSuggestionsArea").innerHTML = `
                <div class="suggestionRow">
                    <span style="color: var(--muted); font-size: 12px;">Cante pelo menos 3 notas diferentes para receber sugestões.</span>
                </div>
            `;
            stabilityCount = 0;
            lastDetectedNote = "";
        }
        
        function simulateRandomSinging() {
            // Seleciona 3 notas aleatórias da lista de notas e adiciona
            let availableNotes = [...noteNames];
            availableNotes.sort(() => Math.random() - 0.5);
            for (let i = 0; i < 3; i++) {
                addDetectedNote(availableNotes[i]);
            }
        }
        
        function calculateScaleSuggestions() {
            if (detectedNotesSet.size < 3) {
                document.getElementById("scaleSuggestionsArea").innerHTML = `
                    <div class="suggestionRow">
                        <span style="color: var(--muted); font-size: 12px;">Cante pelo menos 3 notas diferentes para receber sugestões (${detectedNotesSet.size}/3).</span>
                    </div>
                `;
                return;
            }
            
            let detectedArray = Array.from(detectedNotesSet);
            let results = [];
            
            for (let scaleName in scalesDatabase) {
                let scaleNotes = scalesDatabase[scaleName];
                let matchCount = 0;
                
                detectedArray.forEach(note => {
                    if (scaleNotes.includes(note)) {
                        matchCount++;
                    }
                });
                
                let score = Math.round((matchCount / detectedArray.length) * 100);
                results.push({ scale: scaleName, score: score });
            }
            
            // Ordenar por maior pontuação
            results.sort((a, b) => b.score - a.score);
            
            // Exibir as top 3 sugestões
            let top3 = results.slice(0, 3);
            let area = document.getElementById("scaleSuggestionsArea");
            area.innerHTML = "";
            
            top3.forEach((res, idx) => {
                let row = document.createElement("div");
                row.className = "suggestionRow" + (idx === 0 ? " bestMatch" : "");
                
                let nameSpan = document.createElement("span");
                nameSpan.innerText = (idx === 0 ? "🏆 " : "") + res.scale;
                
                let scoreSpan = document.createElement("span");
                scoreSpan.className = "suggestionScore";
                scoreSpan.innerText = res.score + "% compatível";
                
                row.appendChild(nameSpan);
                row.appendChild(scoreSpan);
                area.appendChild(row);
            });
        }
        
        // --- 9. RENDERIZADOR DO AFINADOR CANVAS (SLIDING DIAL) ---
        function drawJamStudioGauge() {
            let canvas = document.getElementById("jamGaugeCanvas");
            if (!canvas) return;
            let ctx = canvas.getContext("2d");
            updateSequencerDots();
            
            function renderLoop() {
                requestAnimationFrame(renderLoop);
                
                let width = canvas.width = canvas.parentElement.clientWidth;
                let height = canvas.height = canvas.parentElement.clientHeight;
                
                ctx.clearRect(0, 0, width, height);
                
                let cx = width / 2;
                let cy = height - 20;
                let radius = height * 0.75;
                
                // 1. Desenhar arco de fundo
                ctx.beginPath();
                ctx.arc(cx, cy, radius, Math.PI * 1.15, Math.PI * 1.85);
                ctx.lineWidth = 8;
                ctx.strokeStyle = "rgba(107, 114, 128, 0.15)";
                ctx.stroke();
                
                // 2. Desenhar ticks
                ctx.lineWidth = 1.5;
                for (let i = -50; i <= 50; i += 10) {
                    let angle = Math.PI * 1.5 + (i * (Math.PI * 0.35) / 50);
                    let startX = cx + (radius - 8) * Math.cos(angle);
                    let startY = cy + (radius - 8) * Math.sin(angle);
                    let endX = cx + (radius + 2) * Math.cos(angle);
                    let endY = cy + (radius + 2) * Math.sin(angle);
                    
                    ctx.beginPath();
                    ctx.moveTo(startX, startY);
                    ctx.lineTo(endX, endY);
                    ctx.strokeStyle = (i === 0) ? "#10b981" : "rgba(107, 114, 128, 0.3)";
                    ctx.stroke();
                }
                
                // 3. Suavização exponencial para o ponteiro triangular
                if (typeof window.smoothedJamCents === "undefined") {
                    window.smoothedJamCents = 0;
                }
                let rawCents = (isMicActive && window.lastDetectedPitch !== -1) ? window.currentCentsDeviation : 0;
                window.smoothedJamCents = (0.08 * rawCents) + (0.92 * window.smoothedJamCents);
                let cents = Math.max(-50, Math.min(50, window.smoothedJamCents));
                
                let targetAngle = Math.PI * 1.5 + (cents * (Math.PI * 0.33) / 50);
                
                // 4. Desenhar triângulo deslizante (▼) no topo do arco
                let indicatorRadius = radius + 3;
                let indX = cx + indicatorRadius * Math.cos(targetAngle);
                let indY = cy + indicatorRadius * Math.sin(targetAngle);
                
                ctx.save();
                ctx.translate(indX, indY);
                ctx.rotate(targetAngle + Math.PI / 2);
                
                if (Math.abs(cents) <= 8 && isMicActive && window.lastDetectedPitch !== -1) {
                    ctx.fillStyle = "#10b981";
                } else {
                    ctx.fillStyle = "#3a7097";
                }
                
                ctx.beginPath();
                ctx.moveTo(0, 0);
                ctx.lineTo(-12, -16);
                ctx.lineTo(12, -16);
                ctx.closePath();
                ctx.fill();
                ctx.restore();
                
                // 5. Desenhar notas cromáticas sob o arco
                let chroma = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
                let activeNoteStr = "-";
                if (isMicActive && window.lastDetectedPitch !== -1 && window.currentNoteName) {
                    activeNoteStr = window.currentNoteName;
                }
                
                if (activeNoteStr !== "-") {
                    let baseIdx = chroma.indexOf(activeNoteStr);
                    if (baseIdx !== -1) {
                        ctx.textAlign = "center";
                        ctx.textBaseline = "middle";
                        
                        for (let offset = -2; offset <= 2; offset++) {
                            let noteIdx = (baseIdx + offset + 12) % 12;
                            let noteText = chroma[noteIdx];
                            let angle = Math.PI * 1.5 + (offset * (Math.PI * 0.155));
                            
                            if (offset === 0) {
                                ctx.font = "bold 34px 'Inter', sans-serif";
                                ctx.fillStyle = "#3a7097";
                            } else {
                                ctx.font = "bold 20px 'Inter', sans-serif";
                                ctx.fillStyle = "rgba(148, 163, 184, 0.4)";
                            }
                            
                            let textX = cx + (radius - 32) * Math.cos(angle);
                            let textY = cy + (radius - 32) * Math.sin(angle);
                            ctx.fillText(noteText, textX, textY);
                        }
                    }
                }
            }
            renderLoop();
        }
        
        window.addEventListener("DOMContentLoaded", drawJamStudioGauge);
    </script>
    """
    
    html += "<!-- Fim do JamStudio -->"
    html += "</main></body></html>"
    return html

@jamstudio_bp.route("/estilos")
def estilos_info():
    html = header("CifrasFlix - Guia de Estilos e Harmonias")
    html += """
    <style>
        .estilosContainer {
            max-width: 1200px;
            margin: 40px auto;
            padding: 20px;
            font-family: 'Outfit', 'Inter', sans-serif;
            color: #334155;
        }
        .estilosHeader {
            text-align: center;
            margin-bottom: 50px;
        }
        .estilosHeader h1 {
            font-size: 3rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--blue), var(--purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        .estilosHeader p {
            font-size: 1.2rem;
            color: #64748b;
        }
        .estilosGrid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
        }
        .estiloCard {
            background: #ffffff;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
            border-left: 6px solid var(--blue);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        .estiloCard:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.08);
        }
        .estiloCard.blues { border-left-color: #f59e0b; }
        .estiloCard.pop { border-left-color: #ec4899; }
        .estiloCard.rock { border-left-color: #ef4444; }
        .estiloCard.jazz { border-left-color: #8b5cf6; }
        .estiloCard.reggae { border-left-color: #10b981; }
        .estiloCard.country { border-left-color: #854d0e; }
        .estiloCard.balada { border-left-color: #06b6d4; }
        .estiloCard.soul { border-left-color: #a855f7; }
        .estiloCard.alternativo { border-left-color: #6366f1; }
        .estiloCard.bossa { border-left-color: #14b8a6; }
        .estiloCard.funk { border-left-color: #e11d48; }

        .estiloTitle {
            font-size: 1.6rem;
            font-weight: 700;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .formulaBox {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 1.1rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 20px;
            display: inline-block;
        }
        .estiloDesc {
            font-size: 0.95rem;
            line-height: 1.6;
            color: #475569;
            margin-bottom: 20px;
        }
        .exemploBox {
            background: #f1f5f9;
            border-radius: 8px;
            padding: 15px;
            font-size: 0.9rem;
        }
        .exemploTitle {
            font-weight: 700;
            color: #334155;
            margin-bottom: 6px;
            text-transform: uppercase;
            font-size: 0.8rem;
            letter-spacing: 0.5px;
        }
        .exemploChords {
            font-weight: 700;
            color: var(--blue);
            font-size: 1rem;
        }
    </style>

    <div class="estilosContainer">
        <div class="estilosHeader">
            <h1>Guia de Harmonias e Estilos</h1>
            <p>Aprenda a estrutura dos acordes de cada gênero musical e compreenda as regras da harmonia na prática</p>
        </div>

        <div class="estilosGrid">
            <!-- Blues -->
            <div class="estiloCard blues">
                <div class="estiloTitle">🎷 Blues</div>
                <div class="formulaBox">I I I I | IV IV | I I | V IV | I I</div>
                <div class="estiloDesc">
                    A lendária progressão de 12 compassos (12-bar blues) é a base de todo o Rock e Blues moderno. Utiliza acordes dominantes com sétima em todos os graus, trazendo aquela tensão melancólica e expressiva típica do gênero.
                </div>
                <div class="exemploBox">
                    <div class="exemploTitle">Exemplo em Lá (A):</div>
                    <div class="exemploChords">A7 | A7 | A7 | A7 | D7 | D7 | A7 | A7 | E7 | D7 | A7 | A7</div>
                </div>
            </div>

            <!-- Pop -->
            <div class="estiloCard pop">
                <div class="estiloTitle">🥁 Pop</div>
                <div class="formulaBox">I V vi IV</div>
                <div class="estiloDesc">
                    A progressão de acordes mais famosa e cativante do mundo. Utilizada em centenas de hits globais por sua sonoridade perfeitamente balanceada entre energia (I, V) e uma pitada de emoção (vi, IV).
                </div>
                <div class="exemploBox">
                    <div class="exemploTitle">Exemplo em Dó (C):</div>
                    <div class="exemploChords">C | G | Am | F</div>
                </div>
            </div>

            <!-- Rock Clássico -->
            <div class="estiloCard rock">
                <div class="estiloTitle">🎸 Rock Clássico</div>
                <div class="formulaBox">I IV I V</div>
                <div class="estiloDesc">
                    Forte e direto. Alterna dinamicamente entre a tônica (I) e a subdominante (IV) antes de resolver com a tensão da dominante (V). É a progressão definitiva das guitarras elétricas e riffs enérgicos dos anos 70 e 80.
                </div>
                <div class="exemploBox">
                    <div class="exemploTitle">Exemplo em Lá (A):</div>
                    <div class="exemploChords">A | D | A | E</div>
                </div>
            </div>

            <!-- Jazz -->
            <div class="estiloCard jazz">
                <div class="estiloTitle">🎹 Jazz</div>
                <div class="formulaBox">ii V I</div>
                <div class="estiloDesc">
                    A progressão fundamental do Jazz (ii-V-I). Constrói uma tensão sofisticada que sai do acorde menor de segundo grau (ii), passa pela dominante instável (V) e resolve suavemente no acorde de tônica maior com sétima (Imaj7).
                </div>
                <div class="exemploBox">
                    <div class="exemploTitle">Exemplo em Dó (C):</div>
                    <div class="exemploChords">Dm7 | G7 | Cmaj7 | Cmaj7</div>
                </div>
            </div>

            <!-- Reggae -->
            <div class="estiloCard reggae">
                <div class="estiloTitle">🌴 Reggae</div>
                <div class="formulaBox">I IV V IV</div>
                <div class="estiloDesc">
                    Um groove descontraído e solar. A progressão anda em círculos entre a tônica (I) e os acordes maiores (IV e V), sempre executados nos tempos fracos (offbeats/contratempos) para dar o pulso clássico jamaicano.
                </div>
                <div class="exemploBox">
                    <div class="exemploTitle">Exemplo em Dó (C):</div>
                    <div class="exemploChords">C | F | G | F</div>
                </div>
            </div>

            <!-- Country -->
            <div class="estiloCard country">
                <div class="estiloTitle">🤠 Country</div>
                <div class="formulaBox">I IV V</div>
                <div class="estiloDesc">
                    A clássica progressão de três acordes ("three chords and the truth"). Altamente folk, narrativo e tradicional, apoia-se inteiramente nos três pilares harmônicos principais da música ocidental.
                </div>
                <div class="exemploBox">
                    <div class="exemploTitle">Exemplo em Sol (G):</div>
                    <div class="exemploChords">G | C | D | D</div>
                </div>
            </div>

            <!-- Balada -->
            <div class="estiloCard balada">
                <div class="estiloTitle">🎵 Balada Romântica</div>
                <div class="formulaBox">I vi IV V</div>
                <div class="estiloDesc">
                    Também conhecida como progressão dos anos 50 ("50s progression"). Muito melódica e romântica, cria uma sensação nostálgica que flui perfeitamente para canções calmas e sentimentais.
                </div>
                <div class="exemploBox">
                    <div class="exemploTitle">Exemplo em Dó (C):</div>
                    <div class="exemploChords">C | Am | F | G</div>
                </div>
            </div>

            <!-- Soul / R&B -->
            <div class="estiloCard soul">
                <div class="estiloTitle">🎙️ Soul / R&B</div>
                <div class="formulaBox">I iii vi IV</div>
                <div class="estiloDesc">
                    Transmite suavidade e sentimentos profundos. A inserção do acorde menor de terceiro grau (iii) cria uma transição harmônica aveludada e misteriosa em direção à tônica e subdominante.
                </div>
                <div class="exemploBox">
                    <div class="exemploTitle">Exemplo em Dó (C):</div>
                    <div class="exemploChords">C | Em | Am | F</div>
                </div>
            </div>

            <!-- Alternativo -->
            <div class="estiloCard alternativo">
                <div class="estiloTitle">🌌 Alternativo</div>
                <div class="formulaBox">vi IV I V</div>
                <div class="estiloDesc">
                    Uma variação melancólica e introspectiva da progressão pop. Ao começar no acorde relativo menor (vi) e caminhar em direção aos maiores, traz um sentimento épico e reflexivo, típico do Rock Alternativo.
                </div>
                <div class="exemploBox">
                    <div class="exemploTitle">Exemplo em Lá menor (Am):</div>
                    <div class="exemploChords">Am | F | C | G</div>
                </div>
            </div>

            <!-- Bossa Nova -->
            <div class="estiloCard bossa">
                <div class="estiloTitle">🌊 Bossa Nova</div>
                <div class="formulaBox">ii V I</div>
                <div class="estiloDesc">
                    Traz a riqueza harmônica do samba e jazz carioca. Em vez de acordes simples, utiliza acordes com extensões ricas como nonas (9), décimas terceiras (13) e sétimas maiores (Maj7), junto a uma levada de baixo altamente sincopada.
                </div>
                <div class="exemploBox">
                    <div class="exemploTitle">Exemplo com Extensões:</div>
                    <div class="exemploChords">Dm9 | G13 | Cmaj7 | Cmaj7</div>
                </div>
            </div>

            <!-- Funk -->
            <div class="estiloCard funk">
                <div class="estiloTitle">🕺 Funk Groove</div>
                <div class="formulaBox">i IV</div>
                <div class="estiloDesc">
                    Foco total no ritmo e no balanço (groove). A harmonia é minimalista, repetindo-se entre a tônica menor e a quarta maior (modo Dórico), deixando espaço livre para as síncopas da bateria e os slaps do baixo.
                </div>
                <div class="exemploBox">
                    <div class="exemploTitle">Exemplo em Dó menor (Cm):</div>
                    <div class="exemploChords">Cm7 | F7 | Cm7 | F7</div>
                </div>
            </div>
        </div>
    </div>
    """
    html += "</main></body></html>"
    return html
