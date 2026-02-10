import { dom, formatBytes, persistViewMode, state } from "./shared.js";

export function setStatus(message, type) {
    dom.statusEl.textContent = message || "";
    dom.statusEl.className = "uploader-status";
    if (type) {
        dom.statusEl.classList.add(type);
    }
}

function formatMeta(file) {
    const parts = [];
    if (file.size_label) {
        parts.push(file.size_label);
    }
    if (file.modified) {
        parts.push(file.modified);
    }
    const hashLabel = file.hash_short || file.hash;
    if (hashLabel) {
        parts.push(`SHA-256: ${hashLabel}`);
    }
    return parts.join(" • ");
}

export function applyViewMode() {
    const isGrid = state.viewMode === "grid";
    dom.listEl.classList.toggle("file-list--grid", isGrid);

    if (dom.viewGridBtn) {
        dom.viewGridBtn.setAttribute("aria-pressed", isGrid ? "true" : "false");
    }
    if (dom.viewListBtn) {
        dom.viewListBtn.setAttribute("aria-pressed", isGrid ? "false" : "true");
    }
}

export function setViewMode(mode) {
    if (mode !== "grid" && mode !== "list") {
        return;
    }
    state.viewMode = mode;
    persistViewMode(mode);
    applyViewMode();
}

function updateEmptyState(fileCount) {
    if (!dom.emptyEl) {
        return;
    }
    const showEmpty = fileCount === 0 && state.pendingItems.length === 0;
    dom.emptyEl.style.display = showEmpty ? "block" : "none";
}

function createFileItem(file) {
    const item = document.createElement("div");
    item.className = "file-item";

    const preview = document.createElement("div");
    preview.className = "file-preview";
    if (file.is_image && file.preview_url) {
        const img = document.createElement("img");
        img.src = file.preview_url;
        img.alt = file.name;
        preview.appendChild(img);
    } else {
        const ext = document.createElement("span");
        ext.className = "file-ext";
        ext.textContent = (file.ext || "file").toUpperCase();
        preview.appendChild(ext);
    }

    const info = document.createElement("div");
    info.className = "file-info";

    const name = document.createElement("a");
    name.className = "file-name";
    name.textContent = file.name;
    name.href = file.preview_url || file.download_url || "#";
    name.target = "_blank";
    name.rel = "noreferrer";

    const meta = document.createElement("div");
    meta.className = "file-meta";
    meta.textContent = formatMeta(file);
    if (file.hash) {
        meta.title = `SHA-256: ${file.hash}`;
    }

    info.appendChild(name);
    info.appendChild(meta);

    const actions = document.createElement("div");
    actions.className = "file-actions";

    const downloadLink = document.createElement("a");
    downloadLink.className = "file-download";
    downloadLink.textContent = "Скачать";
    downloadLink.href = file.download_url || "#";
    downloadLink.target = "_blank";
    downloadLink.rel = "noreferrer";
    downloadLink.setAttribute("aria-label", "Скачать файл");

    const renameBtn = document.createElement("button");
    renameBtn.type = "button";
    renameBtn.className = "file-rename";
    renameBtn.textContent = "✎";
    renameBtn.title = "Переименовать";
    renameBtn.setAttribute("aria-label", "Переименовать");
    renameBtn.dataset.name = file.name;

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "file-delete";
    deleteBtn.textContent = "Удалить";
    deleteBtn.dataset.name = file.name;

    actions.appendChild(downloadLink);
    actions.appendChild(renameBtn);
    actions.appendChild(deleteBtn);

    item.appendChild(preview);
    item.appendChild(info);
    item.appendChild(actions);
    return item;
}

export function renderList(files) {
    dom.listEl.innerHTML = "";
    files.forEach((file) => dom.listEl.appendChild(createFileItem(file)));
    const count = files.length;
    dom.countEl.textContent = count ? `Всего: ${count}` : "";
    applyViewMode();
    updateEmptyState(count);
}

export function renderQueue() {
    if (!dom.uploadQueueEl || !dom.uploadQueueListEl) {
        return;
    }

    dom.uploadQueueEl.hidden = state.pendingItems.length === 0;
    dom.uploadQueueListEl.innerHTML = "";

    state.pendingItems.forEach((item) => {
        const row = document.createElement("div");
        row.className = "queue-item";

        const info = document.createElement("div");
        info.className = "queue-info";

        const original = document.createElement("div");
        original.className = "queue-original";
        original.textContent = `Оригинал: ${item.file.name}`;

        const input = document.createElement("input");
        input.type = "text";
        input.className = "queue-name-input";
        input.value = item.name;
        input.placeholder = "Новое имя файла";
        input.addEventListener("input", () => {
            item.name = input.value;
        });

        const meta = document.createElement("div");
        meta.className = "queue-meta";
        meta.textContent = `Размер: ${formatBytes(item.file.size)}`;

        info.appendChild(original);
        info.appendChild(input);
        info.appendChild(meta);

        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "queue-remove";
        removeBtn.textContent = "Убрать";
        removeBtn.addEventListener("click", () => {
            state.pendingItems = state.pendingItems.filter((entry) => entry.id !== item.id);
            renderQueue();
        });

        row.appendChild(info);
        row.appendChild(removeBtn);
        dom.uploadQueueListEl.appendChild(row);
    });

    if (dom.uploadBtn) {
        dom.uploadBtn.disabled = state.isUploading || state.pendingItems.length === 0;
        dom.uploadBtn.textContent = state.pendingItems.length ? `Загрузить (${state.pendingItems.length})` : "Загрузить";
    }

    updateEmptyState(state.filesCache.length);
}

export function openRenameModal(filename) {
    if (!dom.renameModal || !dom.renameInput) {
        return;
    }
    state.renameFromName = filename || "";
    if (dom.renameOldEl) {
        dom.renameOldEl.textContent = state.renameFromName;
    }
    dom.renameInput.value = state.renameFromName;
    dom.renameModal.hidden = false;
    dom.renameInput.focus();
    dom.renameInput.select();
}

export function closeRenameModal() {
    if (!dom.renameModal) {
        return;
    }
    dom.renameModal.hidden = true;
    state.renameFromName = "";
}
