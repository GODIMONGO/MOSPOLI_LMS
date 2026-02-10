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

export const dom = {
    dropzone,
    fileInput,
    browseBtn,
    refreshBtn,
    viewGridBtn,
    viewListBtn,
    uploadQueueEl,
    uploadQueueListEl,
    uploadBtn,
    listEl,
    countEl,
    emptyEl,
    statusEl,
    configEl,
    renameModal,
    renameOldEl,
    renameInput,
    renameCancelBtn,
    renameSaveBtn,
};

function parseJson(el, fallback) {
    if (!el) {
        return fallback;
    }
    try {
        return JSON.parse(el.textContent);
    } catch (_err) {
        return fallback;
    }
}

function getInitialViewMode() {
    let stored = null;
    try {
        stored = localStorage.getItem("filesView");
    } catch (_err) {
        stored = null;
    }
    if (stored === "list" || stored === "grid") {
        return stored;
    }
    return "grid";
}

export function persistViewMode(mode) {
    try {
        localStorage.setItem("filesView", mode);
    } catch (_err) {
        // ignore
    }
}

const config = parseJson(configEl, {});
const course = String(config.course || "").trim();
const uuidForUpload = String(config.uuidForUpload || "").trim();

export const uploadConfig = {
    course,
    uuidForUpload,
    maxBytes: (config.maxFileSizeMb || 0) * 1024 * 1024,
    maxFiles: Number(config.maxFiles || 0),
};

export const allowedExts = new Set((config.allowedExts || []).map((ext) => ext.toLowerCase()));

export const state = {
    filesCache: [],
    pendingItems: [],
    nextQueueId: 1,
    isUploading: false,
    viewMode: getInitialViewMode(),
    renameFromName: "",
};

export function withCourse(url) {
    const params = new URLSearchParams();
    if (uploadConfig.course) {
        params.set("course", uploadConfig.course);
    }
    if (uploadConfig.uuidForUpload) {
        params.set("uuid_for_upload", uploadConfig.uuidForUpload);
    }
    const query = params.toString();
    if (!query) {
        return url;
    }
    const separator = url.includes("?") ? "&" : "?";
    return `${url}${separator}${query}`;
}

export function withUuidPath(suffix) {
    const uuid = encodeURIComponent(uploadConfig.uuidForUpload || "");
    return `/input_file/${uuid}${suffix}`;
}

export function formatBytes(sizeBytes) {
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

export function getExtension(name) {
    const trimmed = (name || "").trim();
    const dot = trimmed.lastIndexOf(".");
    if (dot <= 0 || dot === trimmed.length - 1) {
        return "";
    }
    return trimmed.slice(dot + 1);
}

export function normalizeFilename(originalName, desiredName) {
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

export function isSafeClientName(name) {
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
