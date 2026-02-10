import { addToQueue, deleteFile, fetchList, submitRename, uploadQueue } from "./operations.js";
import { closeRenameModal, openRenameModal, setStatus, setViewMode } from "./render.js";
import { dom, state } from "./shared.js";

export function initEvents() {
    dom.browseBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        dom.fileInput.click();
    });

    if (dom.refreshBtn) {
        dom.refreshBtn.addEventListener("click", async () => {
            setStatus("Обновляем список файлов...", "loading");
            await fetchList();
            if (dom.statusEl.classList.contains("loading")) {
                setStatus("", "");
            }
        });
    }

    if (dom.viewGridBtn) {
        dom.viewGridBtn.addEventListener("click", () => setViewMode("grid"));
    }
    if (dom.viewListBtn) {
        dom.viewListBtn.addEventListener("click", () => setViewMode("list"));
    }

    dom.dropzone.addEventListener("click", (event) => {
        if (event.target.closest("a, button, input, textarea, label")) {
            return;
        }
        if (event.target.closest(".file-item") || event.target.closest(".upload-queue")) {
            return;
        }
        if (state.filesCache.length || state.pendingItems.length) {
            return;
        }
        dom.fileInput.click();
    });

    dom.dropzone.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            if (!state.filesCache.length && !state.pendingItems.length) {
                dom.fileInput.click();
            }
        }
    });

    dom.fileInput.addEventListener("change", (event) => {
        addToQueue(event.target.files);
        dom.fileInput.value = "";
    });

    dom.dropzone.addEventListener("dragover", (event) => {
        event.preventDefault();
        dom.dropzone.classList.add("dragover");
    });

    dom.dropzone.addEventListener("dragleave", () => {
        dom.dropzone.classList.remove("dragover");
    });

    dom.dropzone.addEventListener("drop", (event) => {
        event.preventDefault();
        dom.dropzone.classList.remove("dragover");
        addToQueue(event.dataTransfer.files);
    });

    if (dom.uploadBtn) {
        dom.uploadBtn.addEventListener("click", uploadQueue);
    }

    dom.listEl.addEventListener("click", (event) => {
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

    if (dom.renameModal) {
        dom.renameModal.addEventListener("click", (event) => {
            if (event.target.closest("[data-close]")) {
                closeRenameModal();
            }
        });
    }

    if (dom.renameCancelBtn) {
        dom.renameCancelBtn.addEventListener("click", closeRenameModal);
    }
    if (dom.renameSaveBtn) {
        dom.renameSaveBtn.addEventListener("click", submitRename);
    }
    if (dom.renameInput) {
        dom.renameInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                submitRename();
            } else if (event.key === "Escape") {
                closeRenameModal();
            }
        });
    }

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && dom.renameModal && !dom.renameModal.hidden) {
            closeRenameModal();
        }
    });
}
