from pathlib import Path
p = Path('static/js/masterizacao.js')
s = p.read_text(encoding='utf-8')

# Inject alternarModoCorteStems + alternarModoCorteStems right after the masterCutMode declaration.
anchor = 'let masterCutMode = false;\n        let cutSelection = null;'
addition = (
    'let masterCutMode = false;\n'
    '        let cutSelection = null;\n'
    '\n'
    '        function alternarModoCorteStems(btn) {\n'
    '            masterCutMode = !masterCutMode;\n'
    '            if (masterCutMode) {\n'
    '                removerSelecaoCorte();\n'
    '            }\n'
    '            document.body.classList.toggle(\'stem-cut-mode\', masterCutMode);\n'
    '            btn.classList.toggle(\'is-on\', masterCutMode);\n'
    '            btn.setAttribute(\'aria-pressed\', masterCutMode ? \'true\' : \'false\');\n'
    '            btn.innerHTML = masterCutMode ? \'\u2702\ufe0f Modo Corte: ON\' : \'\u2702\ufe0f Modo Corte: OFF\';\n'
    '            if (masterCutMode) {\n'
    '                setMasterStatus(\'Modo Corte: arraste no waveform para selecionar um trecho da stem.\');\n'
    '            } else {\n'
    '                setMasterStatus(\'Modo Corte desativado. Clique no waveform volta a ser seek.\');\n'
    '            }\n'
    '        }\n'
    '\n'
    '        function formatarTempoCorte(segundos) {\n'
    '            if (!Number.isFinite(segundos) || segundos < 0) return \'00:00.00\';\n'
    '            const min = Math.floor(segundos / 60);\n'
    '            const seg = Math.floor(segundos % 60);\n'
    '            const cs = Math.floor((segundos - Math.floor(segundos)) * 100);\n'
    '            const m = String(min).padStart(2, \'0\');\n'
    '            const s = String(seg).padStart(2, \'0\');\n'
    '            const c = String(cs).padStart(2, \'0\');\n'
    '            return ${m}:.;\n'
    '        }\n'
)
if anchor not in s:
    print('ANCHOR NOT FOUND')
else:
    s = s.replace(anchor, addition, 1)
    p.write_text(s, encoding='utf-8')
    print('OK1', s.count('alternarModoCorteStems'))
