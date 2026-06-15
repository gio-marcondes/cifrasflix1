function abrirImpressaoLetra(artista, musica) {
    window.open(`/letra/${artista}/${musica}/print?translation=pt`, "_blank");
}

let lyricPreviewAudio = null;
let lyricPreviewBtnAtual = null;

async function toggleLyricPreview(btn) {
    const titleIdle = "Ouvir trecho";
    const titlePlaying = "Pausar trecho";
    let url = btn.dataset.preview || "";

    if (!url) {
        try {
            const r = await fetch(`/preview?artista=${encodeURIComponent(btn.dataset.artista || "")}&titulo=${encodeURIComponent(btn.dataset.titulo || "")}`);
            const data = await r.json();
            url = data.preview || "";
            btn.dataset.preview = url;
        } catch (e) {
            console.error("Erro preview:", e);
        }
    }

    if (!url) {
        btn.textContent = "Sem preview";
        return;
    }

    if (btn.audio) {
        if (!btn.audio.paused) {
            btn.audio.pause();
            btn.classList.remove("playing");
            btn.textContent = titleIdle;
            return;
        }

        btn.audio.play();
        btn.classList.add("playing");
        btn.textContent = titlePlaying;
        return;
    }

    if (lyricPreviewAudio) {
        lyricPreviewAudio.pause();
        if (lyricPreviewBtnAtual) {
            lyricPreviewBtnAtual.classList.remove("playing");
            lyricPreviewBtnAtual.textContent = titleIdle;
        }
    }

    const audio = new Audio(url);
    btn.audio = audio;
    lyricPreviewAudio = audio;
    lyricPreviewBtnAtual = btn;
    audio.play();
    btn.classList.add("playing");
    btn.textContent = titlePlaying;
    audio.onended = () => {
        btn.classList.remove("playing");
        btn.textContent = titleIdle;
    };
}





