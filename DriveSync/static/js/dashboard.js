const STATUS_LABELS = {
    only_a: "Only on A",
    only_b: "Only on B",
    identical: "Identical",
    same_content: "Same content",
    conflict: "Conflict",
    error: "Error",
};

async function postJSON(url, body) {
    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    return res.json();
}

function formatBytes(bytes) {
    if (bytes === null || bytes === undefined) return "-";
    const gb = bytes / (1024 ** 3);
    return gb >= 0.1 ? `${gb.toFixed(2)} GB` : `${(bytes / 1024).toFixed(1)} KB`;
}

function setStatusLine(card, text) {
    card.querySelector(".status-line").textContent = text;
}

function describeScan(scan) {
    if (!scan) return "Not scanned yet.";
    if (scan.status === "running") return "Scan in progress...";
    if (scan.status === "error") return "Last scan failed.";
    return `${scan.file_count} files, ${formatBytes(scan.total_size)} — last scanned ${scan.finished_at}`;
}

function pollJob(jobId, onProgress, onDone) {
    const timer = setInterval(async () => {
        const res = await fetch(`/api/jobs/${jobId}`);
        const job = await res.json();
        onProgress(job);
        if (job.status === "done" || job.status === "error") {
            clearInterval(timer);
            onDone(job);
        }
    }, 800);
}

document.querySelectorAll(".drive-card").forEach((card) => {
    const label = card.dataset.label;
    const input = card.querySelector(".drive-path");
    const saveBtn = card.querySelector(".save-btn");
    const scanBtn = card.querySelector(".scan-btn");
    const progressBar = card.querySelector(".progress-bar");
    const fill = progressBar.querySelector(".fill");

    setStatusLine(card, describeScan(driveData[label]));

    saveBtn.addEventListener("click", async () => {
        await postJSON("/api/drives", { label, path: input.value });
        setStatusLine(card, "Path saved.");
    });

    scanBtn.addEventListener("click", async () => {
        if (!input.value) {
            alert("Enter a path first.");
            return;
        }
        await postJSON("/api/drives", { label, path: input.value });
        scanBtn.disabled = true;
        progressBar.style.display = "block";
        fill.style.width = "5%";

        const { job_id } = await postJSON("/api/scan", { label });
        pollJob(
            job_id,
            (job) => {
                const count = job.progress.file_count || 0;
                fill.style.width = "100%";
                setStatusLine(card, `Scanning... ${count} files found so far.`);
            },
            (job) => {
                scanBtn.disabled = false;
                progressBar.style.display = "none";
                if (job.status === "error") {
                    setStatusLine(card, `Scan failed: ${job.error}`);
                } else {
                    setStatusLine(card, `${job.progress.file_count} files, ${formatBytes(job.progress.total_size)} scanned.`);
                }
            }
        );
    });
});

const compareBtn = document.getElementById("compare-btn");
const compareProgress = document.getElementById("compare-progress");
const compareStatus = document.getElementById("compare-status");
const summaryGrid = document.getElementById("summary-grid");

function renderSummary(summary) {
    summaryGrid.innerHTML = "";
    for (const key of ["only_a", "only_b", "identical", "same_content", "conflict", "error"]) {
        const count = summary[key] || 0;
        const tile = document.createElement("div");
        tile.className = "summary-tile";
        tile.innerHTML = `<div class="count">${count}</div><div class="label">${STATUS_LABELS[key]}</div>`;
        summaryGrid.appendChild(tile);
    }
}

async function loadSummary() {
    const res = await fetch("/api/summary?drive_a=A&drive_b=B");
    if (!res.ok) return;
    const data = await res.json();
    if (Object.keys(data.summary).length > 0) {
        renderSummary(data.summary);
        compareStatus.textContent = "Comparison results below (also see the Differences page).";
    }
}

compareBtn.addEventListener("click", async () => {
    compareBtn.disabled = true;
    compareProgress.style.display = "block";
    compareProgress.querySelector(".fill").style.width = "10%";
    compareStatus.textContent = "Comparing...";

    const { job_id } = await postJSON("/api/compare", { drive_a: "A", drive_b: "B" });
    pollJob(
        job_id,
        (job) => {
            const p = job.progress;
            compareStatus.textContent = `Comparing... hashed ${p.hashed_count || 0} files so far.`;
        },
        async (job) => {
            compareBtn.disabled = false;
            compareProgress.style.display = "none";
            if (job.status === "error") {
                compareStatus.textContent = `Compare failed: ${job.error}`;
            } else {
                await loadSummary();
            }
        }
    );
});

loadSummary();
