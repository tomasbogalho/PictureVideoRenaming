const filterSelect = document.getElementById("status-filter");
const rowsBody = document.getElementById("diff-rows");
const resultCount = document.getElementById("result-count");
const pageLabel = document.getElementById("page-label");
const prevBtn = document.getElementById("prev-page");
const nextBtn = document.getElementById("next-page");

const PAGE_SIZE = 100;
let page = 1;

function formatBytes(bytes) {
    if (bytes === null || bytes === undefined) return "-";
    const gb = bytes / (1024 ** 3);
    return gb >= 0.1 ? `${gb.toFixed(2)} GB` : `${(bytes / 1024).toFixed(1)} KB`;
}

function formatTime(epochSeconds) {
    if (!epochSeconds) return "-";
    return new Date(epochSeconds * 1000).toLocaleString();
}

async function loadRows() {
    const status = filterSelect.value;
    const params = new URLSearchParams({ drive_a: "A", drive_b: "B", page, page_size: PAGE_SIZE });
    if (status) params.set("status", status);

    const res = await fetch(`/api/differences?${params}`);
    if (!res.ok) {
        resultCount.textContent = "Run a comparison from the Overview page first.";
        rowsBody.innerHTML = "";
        return;
    }
    const data = await res.json();

    rowsBody.innerHTML = "";
    for (const row of data.rows) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${row.rel_path}</td>
            <td><span class="status-pill status-${row.status}">${row.status.replace("_", " ")}</span></td>
            <td>${formatBytes(row.size_a)}</td>
            <td>${formatBytes(row.size_b)}</td>
            <td>${formatTime(row.mtime_a)}</td>
            <td>${formatTime(row.mtime_b)}</td>
        `;
        rowsBody.appendChild(tr);
    }

    const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));
    resultCount.textContent = `${data.total} results`;
    pageLabel.textContent = `Page ${page} of ${totalPages}`;
    prevBtn.disabled = page <= 1;
    nextBtn.disabled = page >= totalPages;
}

filterSelect.addEventListener("change", () => {
    page = 1;
    loadRows();
});
prevBtn.addEventListener("click", () => {
    if (page > 1) {
        page -= 1;
        loadRows();
    }
});
nextBtn.addEventListener("click", () => {
    page += 1;
    loadRows();
});

loadRows();
