import { initEvents } from "./events.js";
import { fetchList } from "./operations.js";
import { renderList, renderQueue } from "./render.js";
import { state } from "./shared.js";

export function initUploader() {
    renderList(state.filesCache);
    renderQueue();
    initEvents();
    fetchList();
}
