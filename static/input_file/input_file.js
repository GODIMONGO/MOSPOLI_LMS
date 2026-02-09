(() => {
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("file-input");
    const browseBtn = document.getElementById("browse-btn");
    const refreshBtn = document.getElementById("refresh-btn");
    const viewGridBtn = document.getElementById("view-grid-btn");
    const viewListBtn = document.getElementById("view-list-btn");
    const uploadQueueEl = document.getElementById("upload-queue");
    const uploadQueueListEl = document.getElementById("upload-queue-list");
    const uploadBtn = document.getElementById("upload-btn");
    const listEl = document.getElementById("file-list");
    const countEl = document.getElementById("file-count");
    const emptyEl = document.getElementById("file-empty");
    const statusEl = document.getElementById("uploader-status");
    const configEl = document.getElementById("uploader-config");

    const renameModal = document.getElementById("rename-modal");
    const renameOldEl = document.getElementById("rename-old");
    const renameInput = document.getElementById("rename-input");
    const renameCancelBtn = document.getElementById("rename-cancel");
    const renameSaveBtn = document.getElementById("rename-save");

    const config = parseJson(configEl, {});
    const course = String(config.course || "").trim();
    const uuidForUpload = String(config.uuidForUpload || "").trim();
    const allowedExts = new Set((config.allowedExts || []).map((ext) => ext.toLowerCase()));
    const maxBytes = (config.maxFileSizeMb || 0) * 1024 * 1024;
    const maxFiles = Number(config.maxFiles || 0);

    let filesCache = [];
    let pendingItems = [];
    let nextQueueId = 1;
    let isUploading = false;
    let viewMode = getInitialViewMode();
    let renameFromName = "";

    function withCourse(url) {
        const params = new URLSearchParams();
        if (course) {
            params.set("course", course);
        }
        if (uuidForUpload) {
            params.set("uuid_for_upload", uuidForUpload);
        }
        const query = params.toString();
        if (!query) {
            return url;
        }
        const separator = url.includes("?") ? "&" : "?";
        return `${url}${separator}${query}`;
    }

    function withUuidPath(suffix) {
        const uuid = encodeURIComponent(uuidForUpload || "");
        return `/input_file/${uuid}${suffix}`;
    }

    function parseJson(el, fallback) {
        if (!el) {
            return fallback;
        }
        try {
            return JSON.parse(el.textContent);
        } catch (err) {
            return fallback;
        }
    }

    function getInitialViewMode() {
        let stored = null;
        try {
            stored = localStorage.getItem("filesView");
        } catch (err) {
            stored = null;
        }
        if (stored === "list" || stored === "grid") {
            return stored;
        }
        return "grid";
    }

    function persistViewMode(mode) {
        try {
            localStorage.setItem("filesView", mode);
        } catch (err) {
            // ignore
        }
    }

    function setStatus(message, type) {
        statusEl.textContent = message || "";
        statusEl.className = "uploader-status";
        if (type) {
            statusEl.classList.add(type);
        }
    }

    function formatBytes(sizeBytes) {
        if (!Number.isFinite(sizeBytes)) {
            return "";
        }
        const units = ["B", "KB", "MB", "GB", "TB"];
        let size = sizeBytes;
        for (let i = 0; i < units.length; i += 1) {
            if (size < 1024 || i === units.length - 1) {
                if (i === 0) {
                    return `${Math.round(size)} ${units[i]}`;
                }
                return `${size.toFixed(1)} ${units[i]}`;
            }
            size /= 1024;
        }
        return `${sizeBytes} B`;
    }

    function getExtension(name) {
        const trimmed = (name || "").trim();
        const dot = trimmed.lastIndexOf(".");
        if (dot <= 0 || dot === trimmed.length - 1) {
            return "";
        }
        return trimmed.slice(dot + 1);
    }

    function normalizeFilename(originalName, desiredName) {
        let name = (desiredName || "").trim();
        if (!name) {
            return originalName;
        }
        name = name.replace(/[\\/]/g, "_");
        const originalExt = getExtension(originalName);
        const desiredExt = getExtension(name);
        if (!desiredExt && originalExt) {
            name = `${name}.${originalExt}`;
        }
        return name;
    }

    function isSafeClientName(name) {
        if (!name) {
            return false;
        }
        if (name.includes("/") || name.includes("\\")) {
            return false;
        }
        if (name.includes("..")) {
            return false;
        }
        return true;
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

    function applyViewMode() {
        const isGrid = viewMode === "grid";
        listEl.classList.toggle("file-list--grid", isGrid);

        if (viewGridBtn) {
            viewGridBtn.setAttribute("aria-pressed", isGrid ? "true" : "false");
        }
        if (viewListBtn) {
            viewListBtn.setAttribute("aria-pressed", isGrid ? "false" : "true");
        }
    }

    function setViewMode(mode) {
        if (mode !== "grid" && mode !== "list") {
            return;
        }
        viewMode = mode;
        persistViewMode(mode);
        applyViewMode();
    }

    function updateEmptyState(fileCount) {
        if (!emptyEl) {
            return;
        }
        const showEmpty = fileCount === 0 && pendingItems.length === 0;
        emptyEl.style.display = showEmpty ? "block" : "none";
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

    function renderList(files) {
        listEl.innerHTML = "";
        files.forEach((file) => listEl.appendChild(createFileItem(file)));
        const count = files.length;
        countEl.textContent = count ? `Всего: ${count}` : "";
        applyViewMode();
        updateEmptyState(count);
    }

    async function fetchList() {
        const response = await fetch(withCourse(withUuidPath("/list")), { cache: "no-store" });
        if (!response.ok) {
            setStatus("Не удалось обновить список файлов.", "error");
            return;
        }
        const data = await response.json();
        filesCache = data.files || [];
        renderList(filesCache);
    }

    function renderQueue() {
        if (!uploadQueueEl || !uploadQueueListEl) {
            return;
        }
        uploadQueueEl.hidden = pendingItems.length === 0;
        uploadQueueListEl.innerHTML = "";

        pendingItems.forEach((item) => {
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
                pendingItems = pendingItems.filter((entry) => entry.id !== item.id);
                renderQueue();
            });

            row.appendChild(info);
            row.appendChild(removeBtn);

            uploadQueueListEl.appendChild(row);
        });

        if (uploadBtn) {
            uploadBtn.disabled = isUploading || pendingItems.length === 0;
            uploadBtn.textContent = pendingItems.length
                ? `Загрузить (${pendingItems.length})`
                : "Загрузить";
        }

        updateEmptyState(filesCache.length);
    }

    function addToQueue(files) {
        const list = Array.from(files || []);
        if (!list.length) {
            return;
        }
        list.forEach((file) => {
            pendingItems.push({
                id: nextQueueId,
                file,
                name: file.name,
            });
            nextQueueId += 1;
        });
        renderQueue();
    }

    function buildUploadPlan() {
        const plan = [];
        const errors = [];
        const usedNames = new Set();
        const existingNames = new Set(
            (filesCache || [])
                .map((file) => (file && file.name ? file.name.toLowerCase() : ""))
                .filter((name) => name)
        );
        let resultingCount = filesCache.length;

        pendingItems.forEach((item) => {
            const finalName = normalizeFilename(item.file.name, item.name);
            if (!finalName) {
                errors.push(`Пустое имя файла: ${item.file.name}`);
                return;
            }
            if (!isSafeClientName(finalName)) {
                errors.push(`Недопустимое имя файла: ${finalName}`);
                return;
            }
            const ext = getExtension(finalName).toLowerCase();
            if (allowedExts.size && !allowedExts.has(ext)) {
                errors.push(`Недопустимый тип: ${finalName}`);
                return;
            }
            if (maxBytes && item.file.size > maxBytes) {
                errors.push(`Слишком большой файл: ${finalName}`);
                return;
            }
            const key = finalName.toLowerCase();
            if (usedNames.has(key)) {
                errors.push(`Дублируется имя: ${finalName}`);
                return;
            }
            usedNames.add(key);
            const isReplacement = existingNames.has(key);
            if (!isReplacement) {
                resultingCount += 1;
            }
            plan.push({ item, finalName });
        });

        if (maxFiles && resultingCount > maxFiles) {
            errors.push(`Превышено максимальное количество файлов: ${maxFiles}.`);
        }

        return { plan, errors };
    }

    async function uploadQueue() {
        if (isUploading || !pendingItems.length) {
            return;
        }
        const { plan, errors } = buildUploadPlan();
        if (errors.length) {
            setStatus(errors.join(" • "), "error");
            return;
        }
        if (!plan.length) {
            setStatus("Нет файлов для загрузки.", "error");
            return;
        }

        const formData = new FormData();
        plan.forEach(({ item, finalName }) => formData.append("file", item.file, finalName));

        setStatus("Загружаем файлы...", "loading");
        isUploading = true;
        renderQueue();

        try {
            const response = await fetch(withCourse(withUuidPath("/upload")), {
                method: "POST",
                body: formData,
            });
            const data = await response.json();
            if (!response.ok) {
                const errText = (data.errors || []).join(" • ") || "Ошибка загрузки.";
                setStatus(errText, "error");
            } else if (data.errors && data.errors.length) {
                setStatus(data.errors.join(" • "), "error");
            } else {
                setStatus("Файлы загружены.", "success");
            }

            if (data && Array.isArray(data.added) && data.added.length) {
                const addedNames = new Set(
                    data.added
                        .map((entry) => (entry.name || "").toLowerCase())
                        .filter((name) => name)
                );
                pendingItems = pendingItems.filter((item) => {
                    const finalName = normalizeFilename(item.file.name, item.name).toLowerCase();
                    return !addedNames.has(finalName);
                });
            }

            await fetchList();
        } catch (err) {
            setStatus("Ошибка сети при загрузке.", "error");
        } finally {
            isUploading = false;
            fileInput.value = "";
            renderQueue();
        }
    }

    async function deleteFile(filename) {
        setStatus("Удаляем файл...", "loading");
        try {
            const response = await fetch(withCourse(withUuidPath("/delete")), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: filename }),
            });
            const data = await response.json();
            if (!response.ok || !data.ok) {
                setStatus(data.error || "Не удалось удалить файл.", "error");
                return;
            }
            setStatus("Файл удалён.", "success");
            await fetchList();
        } catch (err) {
            setStatus("Ошибка сети при удалении.", "error");
        }
    }

    function openRenameModal(filename) {
        if (!renameModal || !renameInput) {
            return;
        }
        renameFromName = filename || "";
        if (renameOldEl) {
            renameOldEl.textContent = renameFromName;
        }
        renameInput.value = renameFromName;
        renameModal.hidden = false;
        renameInput.focus();
        renameInput.select();
    }

    function closeRenameModal() {
        if (!renameModal) {
            return;
        }
        renameModal.hidden = true;
        renameFromName = "";
    }

    async function renameFile(oldName, newName) {
        setStatus("Переименовываем файл...", "loading");
        try {
            const response = await fetch(withCourse(withUuidPath("/rename")), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ from: oldName, to: newName }),
            });
            const data = await response.json();
            if (!response.ok || !data.ok) {
                setStatus(data.error || "Не удалось переименовать файл.", "error");
                return false;
            }
            setStatus("Файл переименован.", "success");
            await fetchList();
            return true;
        } catch (err) {
            setStatus("Ошибка сети при переименовании.", "error");
            return false;
        }
    }

    async function submitRename() {
        if (!renameFromName || !renameInput) {
            return;
        }
        const desired = renameInput.value;
        const finalName = normalizeFilename(renameFromName, desired);
        if (!finalName) {
            setStatus("Новое имя не задано.", "error");
            return;
        }
        if (!isSafeClientName(finalName)) {
            setStatus("Недопустимое имя файла.", "error");
            return;
        }
        const ext = getExtension(finalName).toLowerCase();
        if (allowedExts.size && !allowedExts.has(ext)) {
            setStatus("Недопустимый тип файла.", "error");
            return;
        }
        const ok = await renameFile(renameFromName, finalName);
        if (ok) {
            closeRenameModal();
        }
    }

    function initEvents() {
        browseBtn.addEventListener("click", (event) => {
            event.stopPropagation();
            fileInput.click();
        });

        if (refreshBtn) {
            refreshBtn.addEventListener("click", async () => {
                setStatus("Обновляем список файлов...", "loading");
                await fetchList();
                if (statusEl.classList.contains("loading")) {
                    setStatus("", "");
                }
            });
        }

        if (viewGridBtn) {
            viewGridBtn.addEventListener("click", () => setViewMode("grid"));
        }

        if (viewListBtn) {
            viewListBtn.addEventListener("click", () => setViewMode("list"));
        }

        dropzone.addEventListener("click", (event) => {
            if (event.target.closest("a, button, input, textarea, label")) {
                return;
            }
            if (event.target.closest(".file-item")) {
                return;
            }
            if (event.target.closest(".upload-queue")) {
                return;
            }
            if (filesCache.length || pendingItems.length) {
                return;
            }
            fileInput.click();
        });
        dropzone.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                if (!filesCache.length && !pendingItems.length) {
                    fileInput.click();
                }
            }
        });
        fileInput.addEventListener("change", (event) => {
            addToQueue(event.target.files);
            fileInput.value = "";
        });

        dropzone.addEventListener("dragover", (event) => {
            event.preventDefault();
            dropzone.classList.add("dragover");
        });

        dropzone.addEventListener("dragleave", () => {
            dropzone.classList.remove("dragover");
        });

        dropzone.addEventListener("drop", (event) => {
            event.preventDefault();
            dropzone.classList.remove("dragover");
            addToQueue(event.dataTransfer.files);
        });

        if (uploadBtn) {
            uploadBtn.addEventListener("click", uploadQueue);
        }

        listEl.addEventListener("click", (event) => {
            const deleteTarget = event.target.closest(".file-delete");
            if (deleteTarget) {
                deleteFile(deleteTarget.dataset.name);
                return;
            }

            const renameTarget = event.target.closest(".file-rename");
            if (renameTarget) {
                openRenameModal(renameTarget.dataset.name);
            }
        });

        if (renameModal) {
            renameModal.addEventListener("click", (event) => {
                if (event.target.closest("[data-close]")) {
                    closeRenameModal();
                }
            });
        }

        if (renameCancelBtn) {
            renameCancelBtn.addEventListener("click", closeRenameModal);
        }

        if (renameSaveBtn) {
            renameSaveBtn.addEventListener("click", submitRename);
        }

        if (renameInput) {
            renameInput.addEventListener("keydown", (event) => {
                if (event.key === "Enter") {
                    event.preventDefault();
                    submitRename();
                } else if (event.key === "Escape") {
                    closeRenameModal();
                }
            });
        }

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && renameModal && !renameModal.hidden) {
                closeRenameModal();
            }
        });
    }

    renderList(filesCache);
    fetchList();
    renderQueue();
    initEvents();
})();
