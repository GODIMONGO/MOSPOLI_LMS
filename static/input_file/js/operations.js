import {
    allowedExts,
    dom,
    getExtension,
    isSafeClientName,
    normalizeFilename,
    state,
    uploadConfig,
    withCourse,
    withUuidPath,
} from "./shared.js";
import { closeRenameModal, renderList, renderQueue, setStatus } from "./render.js";

export async function fetchList() {
    const response = await fetch(withCourse(withUuidPath("/list")), { cache: "no-store" });
    if (!response.ok) {
        setStatus("Не удалось обновить список файлов.", "error");
        return;
    }
    const data = await response.json();
    state.filesCache = data.files || [];
    renderList(state.filesCache);
}

export function addToQueue(files) {
    const list = Array.from(files || []);
    if (!list.length) {
        return;
    }
    list.forEach((file) => {
        state.pendingItems.push({ id: state.nextQueueId, file, name: file.name });
        state.nextQueueId += 1;
    });
    renderQueue();
}

function buildUploadPlan() {
    const plan = [];
    const errors = [];
    const usedNames = new Set();
    const existingNames = new Set(
        (state.filesCache || []).map((file) => (file && file.name ? file.name.toLowerCase() : "")).filter((name) => name)
    );
    let resultingCount = state.filesCache.length;

    state.pendingItems.forEach((item) => {
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
        if (uploadConfig.maxBytes && item.file.size > uploadConfig.maxBytes) {
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

    if (uploadConfig.maxFiles && resultingCount > uploadConfig.maxFiles) {
        errors.push(`Превышено максимальное количество файлов: ${uploadConfig.maxFiles}.`);
    }

    return { plan, errors };
}

export async function uploadQueue() {
    if (state.isUploading || !state.pendingItems.length) {
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
    state.isUploading = true;
    renderQueue();

    try {
        const response = await fetch(withCourse(withUuidPath("/upload")), { method: "POST", body: formData });
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
            const addedNames = new Set(data.added.map((entry) => (entry.name || "").toLowerCase()).filter((name) => name));
            state.pendingItems = state.pendingItems.filter((item) => {
                const finalName = normalizeFilename(item.file.name, item.name).toLowerCase();
                return !addedNames.has(finalName);
            });
        }

        await fetchList();
    } catch (_err) {
        setStatus("Ошибка сети при загрузке.", "error");
    } finally {
        state.isUploading = false;
        dom.fileInput.value = "";
        renderQueue();
    }
}

export async function deleteFile(filename) {
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
    } catch (_err) {
        setStatus("Ошибка сети при удалении.", "error");
    }
}

export async function submitRename() {
    if (!state.renameFromName || !dom.renameInput) {
        return;
    }

    const desired = dom.renameInput.value;
    const finalName = normalizeFilename(state.renameFromName, desired);
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

    setStatus("Переименовываем файл...", "loading");
    try {
        const response = await fetch(withCourse(withUuidPath("/rename")), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ from: state.renameFromName, to: finalName }),
        });
        const data = await response.json();
        if (!response.ok || !data.ok) {
            setStatus(data.error || "Не удалось переименовать файл.", "error");
            return;
        }
        setStatus("Файл переименован.", "success");
        closeRenameModal();
        await fetchList();
    } catch (_err) {
        setStatus("Ошибка сети при переименовании.", "error");
    }
}
