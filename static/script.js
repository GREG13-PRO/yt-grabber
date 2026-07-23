const urlInput = document.getElementById("url-input");
const pasteBtn = document.getElementById("paste-btn");
const fetchBtn = document.getElementById("fetch-btn");
const fetchBtnLabel = fetchBtn.querySelector(".btn-label");
const fetchBtnSpinner = fetchBtn.querySelector(".spinner");
const fetchError = document.getElementById("fetch-error");

const resultSection = document.getElementById("result");
const thumbnail = document.getElementById("thumbnail");
const videoTitle = document.getElementById("video-title");
const videoDuration = document.getElementById("video-duration");
const qualityPicker = document.getElementById("quality-picker");
const downloadBtn = document.getElementById("download-btn");

const progressArea = document.getElementById("progress-area");
const progressFill = document.getElementById("progress-fill");
const progressStatus = document.getElementById("progress-status");
const progressPercent = document.getElementById("progress-percent");
const downloadLink = document.getElementById("download-link");
const downloadError = document.getElementById("download-error");

const QUALITY_LABELS = {
  best: "Legjobb",
  "2160p": "4K",
  "1440p": "1440p",
  "1080p": "1080p",
  "720p": "720p",
  "480p": "480p",
  "360p": "360p",
  audio: "MP3",
};

let pollTimer = null;
let selectedQuality = null;

function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return "";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

function showError(el, message) {
  el.textContent = message;
  el.classList.remove("hidden");
}

function hideError(el) {
  el.textContent = "";
  el.classList.add("hidden");
}

function setFetchLoading(loading) {
  fetchBtn.disabled = loading;
  fetchBtnLabel.textContent = loading ? "Betöltés..." : "Lekérdezés";
  fetchBtnSpinner.classList.toggle("hidden", !loading);
}

function renderQualityPicker(available) {
  qualityPicker.innerHTML = "";
  selectedQuality = available[0] || null;

  for (const quality of available) {
    const pill = document.createElement("button");
    pill.type = "button";
    pill.className = "quality-pill" + (quality === selectedQuality ? " active" : "");
    pill.textContent = QUALITY_LABELS[quality] || quality;
    pill.addEventListener("click", () => {
      selectedQuality = quality;
      qualityPicker.querySelectorAll(".quality-pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
    });
    qualityPicker.appendChild(pill);
  }
}

async function fetchFormats() {
  const url = urlInput.value.trim();
  hideError(fetchError);
  resultSection.classList.add("hidden");
  progressArea.classList.add("hidden");

  if (!url) {
    showError(fetchError, "Adj meg egy YouTube URL-t.");
    return;
  }

  setFetchLoading(true);

  try {
    const resp = await fetch("/api/formats", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const data = await resp.json();

    if (!resp.ok) {
      showError(fetchError, data.error || "Ismeretlen hiba történt.");
      return;
    }

    thumbnail.src = data.thumbnail || "";
    videoTitle.textContent = data.title || "";
    videoDuration.textContent = formatDuration(data.duration);
    renderQualityPicker(data.available || []);

    resultSection.classList.remove("hidden");
  } catch (e) {
    showError(fetchError, "Nem sikerült kapcsolódni a szerverhez.");
  } finally {
    setFetchLoading(false);
  }
}

async function startDownload() {
  const url = urlInput.value.trim();
  const quality = selectedQuality;
  hideError(downloadError);
  downloadLink.classList.add("hidden");
  progressArea.classList.remove("hidden");
  progressFill.style.width = "0%";
  progressPercent.textContent = "";
  progressStatus.textContent = "Indítás...";
  downloadBtn.disabled = true;

  try {
    const resp = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, quality }),
    });
    const data = await resp.json();

    if (!resp.ok) {
      showError(downloadError, data.error || "Ismeretlen hiba történt.");
      downloadBtn.disabled = false;
      return;
    }

    pollProgress(data.download_id);
  } catch (e) {
    showError(downloadError, "Nem sikerült kapcsolódni a szerverhez.");
    downloadBtn.disabled = false;
  }
}

function pollProgress(downloadId) {
  if (pollTimer) clearInterval(pollTimer);

  pollTimer = setInterval(async () => {
    try {
      const resp = await fetch(`/api/progress/${downloadId}`);
      const data = await resp.json();

      if (data.status === "downloading") {
        const pct = data.percent ?? 0;
        progressFill.style.width = `${pct}%`;
        progressStatus.textContent = "Letöltés...";
        progressPercent.textContent = data.percent ? `${data.percent}%` : "";
      } else if (data.status === "processing") {
        progressStatus.textContent = "Feldolgozás (egyesítés/konverzió)...";
        progressPercent.textContent = "";
      } else if (data.status === "transcoding") {
        const pct = data.percent ?? 0;
        progressFill.style.width = `${pct}%`;
        progressStatus.textContent = "Átkódolás H.264-re (QuickTime-kompatibilis)...";
        progressPercent.textContent = data.percent ? `${data.percent}%` : "";
      } else if (data.status === "finished") {
        clearInterval(pollTimer);
        progressFill.style.width = "100%";
        progressStatus.textContent = "Kész!";
        progressPercent.textContent = "100%";
        downloadLink.href = `/downloads/${encodeURIComponent(data.filename)}`;
        downloadLink.classList.remove("hidden");
        downloadBtn.disabled = false;
      } else if (data.status === "error") {
        clearInterval(pollTimer);
        progressStatus.textContent = "";
        showError(downloadError, data.error || "Hiba történt a letöltés során.");
        downloadBtn.disabled = false;
      }
    } catch (e) {
      clearInterval(pollTimer);
      showError(downloadError, "Nem sikerült kapcsolódni a szerverhez.");
      downloadBtn.disabled = false;
    }
  }, 1000);
}

fetchBtn.addEventListener("click", fetchFormats);
downloadBtn.addEventListener("click", startDownload);
urlInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") fetchFormats();
});
pasteBtn.addEventListener("click", async () => {
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      urlInput.value = text.trim();
      fetchFormats();
    }
  } catch (e) {
    urlInput.focus();
  }
});
