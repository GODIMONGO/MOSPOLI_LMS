document.addEventListener("DOMContentLoaded", () => {
    const STORAGE_KEY = "course_builder_state_v8";

    const catalogRoot = document.getElementById("builder-sidebar-list");
    const modulesRoot = document.getElementById("builder-modules");
    const addModuleBtn = document.getElementById("builder-add-module-btn");
    const addModuleInlineBtn = document.getElementById("builder-add-module-inline");
    const addTopicBtn = document.getElementById("builder-add-topic-btn");
    const toggleCatalogBtn = document.getElementById("builder-toggle-catalog-btn");
    const constructorPanel = document.querySelector(".cb-constructor");
    const blocksJsonEl = document.getElementById("builder-blocks-json");
    const courseInput = document.getElementById("builder-course-input");
    const courseCounter = document.getElementById("builder-course-counter");
    const courseTitleInput = document.getElementById("builder-course-title-input");
    const courseTitleCounter = document.getElementById("builder-course-title-counter");
    const courseMeta = document.getElementById("builder-course-meta");
    const toggleCourseBtn = document.getElementById("builder-toggle-course");
    const iconCourse = "/static/my_curse/icons/curse-icon.svg";
    const iconCross = "/static/my_curse/icons/cross.svg";
    const iconArrow = "/static/admin/CourseBuilder/icons/arrow.svg";
    const iconArrowTopic = "/static/my_curse/icons/arrow.svg";

    const loadedStyles = new Set();
    const readyBlockCache = new Map();
    let hoveredDropTopic = null;

    const toneMap = {
        mint: { bg: "#c8f6dc", fg: "#157247" },
        lilac: { bg: "#f4cae4", fg: "#8d4370" },
        cyan: { bg: "#d5d9ff", fg: "#5258a6" },
        amber: { bg: "#bfeaed", fg: "#2e7f7f" },
        violet: { bg: "#dcccf8", fg: "#5d4e92" }
    };

    const state = {
        catalog: parseCatalog(),
        courseTitle: "Введение в проектную деятельность 2025/2026",
        courseLabel: "|Текст",
        modules: [],
        activeCatalogId: "",
        activeModuleId: "",
        activeTopicId: ""
    };

    function parseCatalog() {
        if (!blocksJsonEl) {
            return [];
        }
        try {
            const parsed = JSON.parse(blocksJsonEl.textContent || "[]");
            if (!Array.isArray(parsed)) {
                return [];
            }
            return parsed.map((item, index) => ({
                id: String(item.id || "block_" + index),
                title: String(item.title || "Блок"),
                caption: String(item.caption || item.title || "Блок"),
                tone: String(item.tone || "mint"),
                icon: String(item.icon || "/static/admin/CourseBuilder/icons/todo_list.svg"),
                item_icon: String(item.item_icon || "/static/admin/CourseBuilder/icons/todo_list.svg"),
                template_url: item.template_url || "",
                root_selector: item.root_selector || "",
                styles: Array.isArray(item.styles) ? item.styles : []
            }));
        } catch (error) {
            console.error("Не удалось распарсить JSON блоков:", error);
            return [];
        }
    }

    function uid(prefix) {
        return prefix + "_" + Date.now() + "_" + Math.random().toString(36).slice(2, 8);
    }

    function escapeHtml(value) {
        return String(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;");
    }

    function titleCounter(value) {
        return Math.min(String(value || "").length, 80) + "/80";
    }

    function toneFor(block) {
        return toneMap[block.tone] || toneMap.mint;
    }

    function ensureStyles(styles) {
        if (!Array.isArray(styles)) {
            return;
        }
        styles.forEach((href) => {
            if (!href || loadedStyles.has(href)) {
                return;
            }
            const link = document.createElement("link");
            link.rel = "stylesheet";
            link.href = href;
            document.head.appendChild(link);
            loadedStyles.add(href);
        });
    }

    async function fetchReadyBlockMarkup(block) {
        if (readyBlockCache.has(block.id)) {
            return readyBlockCache.get(block.id);
        }
        const promise = (async () => {
            if (!block.template_url) {
                return "";
            }
            ensureStyles(block.styles);
            const response = await fetch(block.template_url, { credentials: "same-origin" });
            if (!response.ok) {
                throw new Error("HTTP " + response.status);
            }
            const html = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, "text/html");
            const root = block.root_selector ? doc.querySelector(block.root_selector) : doc.body.firstElementChild;
            if (!root) {
                return "";
            }
            root.querySelectorAll("script").forEach((script) => script.remove());
            return root.outerHTML;
        })();
        readyBlockCache.set(block.id, promise);
        return promise;
    }

    function createTopic(title) {
        return {
            id: uid("topic"),
            title: title || "|Текст",
            items: [],
            customContent: "",
            showCustomEditor: false
        };
    }

    function createQuizQuestion(order) {
        return {
            id: uid("quiz_q"),
            title: "Вопрос " + order,
            type: "single",
            options: ["Вариант 1", "Вариант 2"]
        };
    }

    function normalizeQuizModel(source) {
        const raw = source && typeof source === "object" ? source : {};
        const sourceQuestions = Array.isArray(raw.questions) && raw.questions.length > 0
            ? raw.questions
            : [createQuizQuestion(1)];

        const questions = sourceQuestions.map((question, index) => {
            const rawOptions = Array.isArray(question.options) && question.options.length > 0
                ? question.options
                : ["Вариант 1", "Вариант 2"];
            return {
                id: String(question.id || uid("quiz_q")),
                title: String(question.title || ("Вопрос " + (index + 1))),
                type: question.type === "multi" ? "multi" : "single",
                options: rawOptions.map((option, optionIndex) => String(option || ("Вариант " + (optionIndex + 1))))
            };
        });

        return {
            intro: String(raw.intro || "|Текст"),
            passingScore: String(raw.passingScore || "60"),
            attempts: String(raw.attempts || "2"),
            duration: String(raw.duration || "20"),
            questions
        };
    }

    function ensureQuizModel(item) {
        if (!item) {
            return null;
        }
        item.quiz = normalizeQuizModel(item.quiz);
        return item.quiz;
    }

    function createModule() {
        const number = state.modules.length + 1;
        return {
            id: uid("module"),
            title: "Модуль " + number + ". Основы проектной деятельности",
            collapsed: false,
            topics: [createTopic(number === 1 ? "Тема 1" : "|Текст")]
        };
    }

    function getModule(moduleId) {
        return state.modules.find((module) => module.id === moduleId) || null;
    }

    function getTopic(moduleId, topicId) {
        const module = getModule(moduleId);
        if (!module) {
            return null;
        }
        return module.topics.find((topic) => topic.id === topicId) || null;
    }

    function getItem(moduleId, topicId, itemId) {
        const topic = getTopic(moduleId, topicId);
        if (!topic) {
            return null;
        }
        return topic.items.find((item) => item.id === itemId) || null;
    }

    function ensureActiveTopic() {
        const active = getTopic(state.activeModuleId, state.activeTopicId);
        if (active) {
            return active;
        }
        const firstModule = state.modules[0];
        if (!firstModule || firstModule.topics.length === 0) {
            return null;
        }
        state.activeModuleId = firstModule.id;
        state.activeTopicId = firstModule.topics[0].id;
        return firstModule.topics[0];
    }

    function persistState() {
        try {
            const payload = {
                v: 1,
                courseTitle: state.courseTitle,
                courseLabel: state.courseLabel,
                activeCatalogId: state.activeCatalogId,
                activeModuleId: state.activeModuleId,
                activeTopicId: state.activeTopicId,
                modules: state.modules.map((module) => ({
                    id: module.id,
                    title: module.title,
                    collapsed: !!module.collapsed,
                    topics: module.topics.map((topic) => ({
                        id: topic.id,
                        title: topic.title,
                        customContent: topic.customContent || "",
                        showCustomEditor: !!topic.showCustomEditor,
                        items: topic.items.map((item) => ({
                            id: item.id,
                            blockId: item.blockId,
                            title: item.title,
                            tone: item.tone,
                            icon: item.icon,
                            expanded: !!item.expanded,
                            quiz: item.blockId === "quiz" ? normalizeQuizModel(item.quiz) : undefined
                        }))
                    }))
                }))
            };
            localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
        } catch (error) {
            console.warn("Не удалось сохранить состояние конструктора:", error);
        }
    }

    function restoreState() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) {
                return false;
            }
            const parsed = JSON.parse(raw);
            if (!parsed || !Array.isArray(parsed.modules)) {
                return false;
            }

            state.courseTitle = String(parsed.courseTitle || state.courseTitle);
            state.courseLabel = String(parsed.courseLabel || state.courseLabel);
            state.activeCatalogId = String(parsed.activeCatalogId || "");
            state.activeModuleId = String(parsed.activeModuleId || "");
            state.activeTopicId = String(parsed.activeTopicId || "");

            state.modules = parsed.modules.map((module, moduleIndex) => ({
                id: String(module.id || uid("module")),
                title: String(module.title || ("Модуль " + (moduleIndex + 1))),
                collapsed: !!module.collapsed,
                topics: Array.isArray(module.topics) && module.topics.length > 0
                    ? module.topics.map((topic) => ({
                        id: String(topic.id || uid("topic")),
                        title: String(topic.title || "|Текст"),
                        customContent: String(topic.customContent || ""),
                        showCustomEditor: !!topic.showCustomEditor,
                        items: Array.isArray(topic.items)
                            ? topic.items.map((item) => {
                                const restoredItem = {
                                    id: String(item.id || uid("item")),
                                    blockId: String(item.blockId || ""),
                                    title: String(item.title || "Блок"),
                                    tone: String(item.tone || "mint"),
                                    icon: String(item.icon || "/static/admin/CourseBuilder/icons/todo_list.svg"),
                                    expanded: !!item.expanded,
                                    status: "idle",
                                    readyHtml: "",
                                    error: ""
                                };
                                if (restoredItem.blockId === "quiz") {
                                    restoredItem.quiz = normalizeQuizModel(item.quiz);
                                }
                                return restoredItem;
                            })
                            : []
                    }))
                    : [createTopic()]
            }));

            return true;
        } catch (error) {
            console.warn("Не удалось восстановить состояние конструктора:", error);
            return false;
        }
    }

    function addModule() {
        const module = createModule();
        state.modules.push(module);
        state.activeModuleId = module.id;
        state.activeTopicId = module.topics[0].id;
        persistState();
        render();
    }

    function addTopic(moduleId) {
        const module = getModule(moduleId);
        if (!module) {
            return;
        }
        const topic = createTopic("Тема " + (module.topics.length + 1));
        module.topics.push(topic);
        state.activeModuleId = module.id;
        state.activeTopicId = topic.id;
        persistState();
        render();
    }

    function removeModule(moduleId) {
        state.modules = state.modules.filter((module) => module.id !== moduleId);
        if (state.modules.length === 0) {
            addModule();
            return;
        }
        ensureActiveTopic();
        persistState();
        render();
    }

    function removeTopic(moduleId, topicId) {
        const module = getModule(moduleId);
        if (!module) {
            return;
        }
        module.topics = module.topics.filter((topic) => topic.id !== topicId);
        if (module.topics.length === 0) {
            module.topics.push(createTopic("Тема 1"));
        }
        ensureActiveTopic();
        persistState();
        render();
    }

    function removeItem(moduleId, topicId, itemId) {
        const topic = getTopic(moduleId, topicId);
        if (!topic) {
            return;
        }
        topic.items = topic.items.filter((item) => item.id !== itemId);
        persistState();
        render();
    }

    async function hydrateItem(item) {
        if (!item || item.status !== "idle") {
            return;
        }
        if (item.blockId === "quiz") {
            ensureQuizModel(item);
            item.status = "ready";
            return;
        }
        const block = state.catalog.find((catalogItem) => catalogItem.id === item.blockId);
        if (!block) {
            item.status = "error";
            item.error = "Блок не найден";
            return;
        }
        item.status = "loading";
        render();
        try {
            item.readyHtml = await fetchReadyBlockMarkup(block);
            item.status = "ready";
        } catch (error) {
            item.status = "error";
            item.error = "Не удалось загрузить готовый блок";
            console.error(error);
        }
        persistState();
        render();
    }

    function hydrateAllItems() {
        state.modules.forEach((module) => {
            module.topics.forEach((topic) => {
                topic.items.forEach((item) => {
                    if (item.status === "idle") {
                        hydrateItem(item);
                    }
                });
            });
        });
    }

    async function addCatalogBlock(blockId, moduleId, topicId) {
        const topic = getTopic(moduleId || state.activeModuleId, topicId || state.activeTopicId) || ensureActiveTopic();
        const block = state.catalog.find((item) => item.id === blockId);
        if (!topic || !block) {
            return;
        }

        const item = {
            id: uid("item"),
            blockId: block.id,
            title: block.caption,
            tone: block.tone,
            icon: block.item_icon || block.icon,
            expanded: block.id === "quiz",
            status: block.id === "quiz" ? "ready" : "loading",
            readyHtml: "",
            error: ""
        };
        if (block.id === "quiz") {
            item.quiz = normalizeQuizModel();
        }
        topic.items.push(item);
        state.activeCatalogId = block.id;
        persistState();
        render();

        if (block.id === "quiz") {
            return;
        }

        try {
            item.readyHtml = await fetchReadyBlockMarkup(block);
            item.status = "ready";
        } catch (error) {
            item.status = "error";
            item.error = "Не удалось загрузить готовый блок";
            console.error(error);
        }

        persistState();
        render();
    }

    function renderItemPreview(item, moduleId, topicId) {
        if (item.blockId === "quiz") {
            return renderQuizPreview(moduleId, topicId, item);
        }
        if (item.status === "loading") {
            return '<p class="cb-ready-state">Загрузка готового блока...</p>';
        }
        if (item.status === "error") {
            return '<p class="cb-ready-state is-error">' + escapeHtml(item.error) + '</p>';
        }
        return item.readyHtml ? '<div class="cb-ready-content">' + item.readyHtml + '</div>' : "";
    }

    function renderQuizPreview(moduleId, topicId, item) {
        const quiz = ensureQuizModel(item);
        if (!quiz) {
            return "";
        }
        const questionsHtml = quiz.questions.map((question) => {
            const optionsHtml = question.options.map((option, optionIndex) => (
                '<div class="cb-quiz-option">' +
                '<input class="cb-quiz-input" type="text" maxlength="80" value="' + escapeHtml(option) + '" data-action="quiz-edit-option" data-module-id="' + moduleId + '" data-topic-id="' + topicId + '" data-item-id="' + item.id + '" data-question-id="' + question.id + '" data-option-index="' + optionIndex + '">' +
                '<button type="button" class="cb-topic-remove cb-remove-icon-btn" aria-label="Удалить вариант" data-action="quiz-remove-option" data-module-id="' + moduleId + '" data-topic-id="' + topicId + '" data-item-id="' + item.id + '" data-question-id="' + question.id + '" data-option-index="' + optionIndex + '">' +
                '<img src="' + iconCross + '" alt="">' +
                '</button>' +
                '</div>'
            )).join("");
            return (
                '<article class="cb-quiz-question">' +
                '<div class="cb-quiz-question-head">' +
                '<input class="cb-quiz-input cb-quiz-question-title" type="text" maxlength="80" value="' + escapeHtml(question.title) + '" data-action="quiz-edit-question" data-module-id="' + moduleId + '" data-topic-id="' + topicId + '" data-item-id="' + item.id + '" data-question-id="' + question.id + '">' +
                '<select class="cb-quiz-select" data-action="quiz-edit-type" data-module-id="' + moduleId + '" data-topic-id="' + topicId + '" data-item-id="' + item.id + '" data-question-id="' + question.id + '">' +
                '<option value="single"' + (question.type === "single" ? " selected" : "") + '>Один ответ</option>' +
                '<option value="multi"' + (question.type === "multi" ? " selected" : "") + '>Несколько</option>' +
                '</select>' +
                '<button type="button" class="cb-topic-remove cb-remove-icon-btn" aria-label="Удалить вопрос" data-action="quiz-remove-question" data-module-id="' + moduleId + '" data-topic-id="' + topicId + '" data-item-id="' + item.id + '" data-question-id="' + question.id + '">' +
                '<img src="' + iconCross + '" alt="">' +
                '</button>' +
                '</div>' +
                '<div class="cb-quiz-options">' +
                optionsHtml +
                '<button type="button" class="cb-quiz-link-btn" data-action="quiz-add-option" data-module-id="' + moduleId + '" data-topic-id="' + topicId + '" data-item-id="' + item.id + '" data-question-id="' + question.id + '">+ Вариант</button>' +
                '</div>' +
                '</article>'
            );
        }).join("");

        return (
            '<div class="cb-quiz-preview">' +
            '<div class="cb-quiz-line">' +
            '<input class="cb-quiz-input" type="text" maxlength="80" value="' + escapeHtml(quiz.intro) + '" data-action="quiz-edit-intro" data-module-id="' + moduleId + '" data-topic-id="' + topicId + '" data-item-id="' + item.id + '">' +
            '<p class="cb-counter">' + titleCounter(quiz.intro) + '</p>' +
            '</div>' +
            '<div class="cb-quiz-meta">' +
            '<label class="cb-quiz-chip"><span>Порог %</span><input class="cb-quiz-chip-input" type="text" maxlength="3" value="' + escapeHtml(quiz.passingScore) + '" data-action="quiz-edit-passing" data-module-id="' + moduleId + '" data-topic-id="' + topicId + '" data-item-id="' + item.id + '"></label>' +
            '<label class="cb-quiz-chip"><span>Попытки</span><input class="cb-quiz-chip-input" type="text" maxlength="2" value="' + escapeHtml(quiz.attempts) + '" data-action="quiz-edit-attempts" data-module-id="' + moduleId + '" data-topic-id="' + topicId + '" data-item-id="' + item.id + '"></label>' +
            '<label class="cb-quiz-chip"><span>Мин.</span><input class="cb-quiz-chip-input" type="text" maxlength="3" value="' + escapeHtml(quiz.duration) + '" data-action="quiz-edit-duration" data-module-id="' + moduleId + '" data-topic-id="' + topicId + '" data-item-id="' + item.id + '"></label>' +
            '</div>' +
            '<div class="cb-quiz-questions">' +
            questionsHtml +
            '</div>' +
            '<button type="button" class="cb-quiz-link-btn" data-action="quiz-add-question" data-module-id="' + moduleId + '" data-topic-id="' + topicId + '" data-item-id="' + item.id + '">+ Добавить вопрос</button>' +
            '</div>'
        );
    }

    function renderCatalog() {
        if (!catalogRoot) {
            return;
        }
        catalogRoot.innerHTML = state.catalog
            .map((block) => {
                const tone = toneFor(block);
                const activeClass = block.id === state.activeCatalogId ? " is-active" : "";
                return (
                    '<button class="cb-catalog-item' + activeClass + '" type="button" draggable="true" data-action="add-block" data-block-id="' + block.id + '"' +
                    ' style="--tone-bg:' + tone.bg + ';--tone-fg:' + tone.fg + ';">' +
                    '<img src="' + escapeHtml(block.icon) + '" alt="">' +
                    '<span>' + escapeHtml(block.title) + '</span>' +
                    '</button>'
                );
            })
            .join("");
    }

    function renderModules() {
        if (!modulesRoot) {
            return;
        }

        modulesRoot.innerHTML = state.modules.map((module) => {
            const collapsedClass = module.collapsed ? " is-collapsed" : "";
            const topicsHtml = module.topics.map((topic) => {
                const isActive = topic.id === state.activeTopicId && module.id === state.activeModuleId;
                const activeClass = isActive ? " is-active" : "";
                const itemsHtml = topic.items.length === 0
                    ? '<p class="cb-topic-empty">Перетащите блок сюда или нажмите на блок слева.</p>'
                    : topic.items.map((item) => {
                        const stateHtml = renderItemPreview(item, module.id, topic.id);
                        const metaBlock = state.catalog.find((c) => c.id === item.blockId);
                        const metaIcon = item.blockId === "quiz"
                            ? "/static/admin/CourseBuilder/icons/assessments.svg"
                            : "/static/admin/CourseBuilder/icons/file.svg";
                        const metaText = item.blockId === "quiz"
                            ? "Вопросы и параметры"
                            : (metaBlock ? metaBlock.caption : "Блок");
                        return (
                            '<article class="cb-topic-item' + (item.blockId === "quiz" ? ' is-quiz' : '') + '">' +
                            '<div class="cb-item-row">' +
                            '<img src="' + escapeHtml(item.icon) + '" alt="">' +
                            '<input class="cb-item-title" type="text" maxlength="80" value="' + escapeHtml(item.title) + '" data-action="rename-item" data-module-id="' + module.id + '" data-topic-id="' + topic.id + '" data-item-id="' + item.id + '">' +
                            '<button class="cb-topic-item-expand cb-topic-remove' + (item.expanded ? ' is-open' : '') + '" type="button" aria-label="Показать предпросмотр" data-action="toggle-item-preview" data-module-id="' + module.id + '" data-topic-id="' + topic.id + '" data-item-id="' + item.id + '">' +
                            '<img src="' + iconArrowTopic + '" alt="">' +
                            '</button>' +
                            '<button class="cb-topic-item-remove cb-topic-remove cb-remove-icon-btn" type="button" aria-label="Удалить блок" data-action="remove-item" data-module-id="' + module.id + '" data-topic-id="' + topic.id + '" data-item-id="' + item.id + '">' +
                            '<img src="' + iconCross + '" alt="">' +
                            '</button>' +
                            '</div>' +
                            '<div class="cb-item-row">' +
                            '<img src="' + metaIcon + '" alt="">' +
                            '<span>' + metaText + '</span>' +
                            '</div>' +
                            (item.expanded ? stateHtml : "") +
                            '</article>'
                        );
                    }).join("");

                const customClass = topic.showCustomEditor ? " is-open" : "";
                return (
                    '<section class="cb-topic' + activeClass + '" data-module-id="' + module.id + '" data-topic-id="' + topic.id + '">' +
                    '<div class="cb-topic-head" data-action="select-topic" data-module-id="' + module.id + '" data-topic-id="' + topic.id + '">' +
                    '<input class="cb-topic-title" type="text" data-action="rename-topic" data-module-id="' + module.id + '" data-topic-id="' + topic.id + '" value="' + escapeHtml(topic.title) + '" maxlength="80">' +
                    '<p class="cb-topic-counter">' + titleCounter(topic.title) + '</p>' +
                    '<button class="cb-topic-remove cb-remove-icon-btn" type="button" aria-label="Удалить тему" data-action="remove-topic" data-module-id="' + module.id + '" data-topic-id="' + topic.id + '">' +
                    '<img src="' + iconCross + '" alt="">' +
                    '</button>' +
                    '</div>' +
                    '<div class="cb-topic-body" data-drop-module-id="' + module.id + '" data-drop-topic-id="' + topic.id + '">' +
                    itemsHtml +
                    '<div class="cb-custom-editor' + customClass + '">' +
                    '<button type="button" class="cb-custom-toggle" data-action="toggle-custom" data-module-id="' + module.id + '" data-topic-id="' + topic.id + '">' + (topic.showCustomEditor ? 'Скрыть собственный контент' : 'Добавить собственный контент') + '</button>' +
                    '<label>Собственный контент</label>' +
                    '<textarea data-action="edit-custom" data-module-id="' + module.id + '" data-topic-id="' + topic.id + '" placeholder="Введите свой текст или описание...">' + escapeHtml(topic.customContent) + '</textarea>' +
                    '</div>' +
                    '</div>' +
                    '</section>'
                );
            }).join("");

            return (
                '<section class="cb-module' + collapsedClass + '" data-module-id="' + module.id + '">' +
                '<header class="cb-module-head">' +
                '<img src="' + iconCourse + '" alt="">' +
                '<input class="cb-module-title" type="text" data-action="rename-module" data-module-id="' + module.id + '" value="' + escapeHtml(module.title) + '" maxlength="80">' +
                '<p class="cb-counter">' + titleCounter(module.title) + '</p>' +
                '<button type="button" class="cb-icon-btn" data-action="toggle-module" data-module-id="' + module.id + '">' +
                '<img src="' + iconArrow + '" alt="">' +
                '</button>' +
                '<button type="button" class="cb-remove-btn cb-remove-icon-btn" aria-label="Удалить модуль" data-action="remove-module" data-module-id="' + module.id + '">' +
                '<img src="' + iconCross + '" alt="">' +
                '</button>' +
                '</header>' +
                '<div class="cb-module-body">' +
                topicsHtml +
                '<button type="button" class="cb-module-add-topic" data-action="add-topic-module" data-module-id="' + module.id + '">' +
                '<img src="/static/admin/CourseBuilder/icons/plus-square.svg" alt="">' +
                '<span>Добавить тему</span>' +
                '</button>' +
                '</div>' +
                '</section>'
            );
        }).join("");
    }

    function renderCourseMeta() {
        if (courseInput) {
            courseInput.value = state.courseLabel;
        }
        if (courseCounter) {
            courseCounter.textContent = titleCounter(state.courseLabel);
        }
        if (courseTitleInput) {
            courseTitleInput.value = state.courseTitle;
        }
        if (courseTitleCounter) {
            courseTitleCounter.textContent = titleCounter(state.courseTitle);
        }
    }

    function render() {
        renderCatalog();
        renderModules();
        renderCourseMeta();
    }

    function applyActiveTopicClass(moduleId, topicId) {
        if (!modulesRoot) {
            return;
        }
        modulesRoot.querySelectorAll(".cb-topic").forEach((node) => {
            if (!(node instanceof HTMLElement)) {
                return;
            }
            const isActive = node.dataset.moduleId === moduleId && node.dataset.topicId === topicId;
            node.classList.toggle("is-active", isActive);
        });
    }

    function setDropTarget(topicNode) {
        if (hoveredDropTopic && hoveredDropTopic !== topicNode) {
            hoveredDropTopic.classList.remove("is-drop-target");
        }
        hoveredDropTopic = topicNode;
        if (hoveredDropTopic) {
            hoveredDropTopic.classList.add("is-drop-target");
        }
    }

    function clearDropTarget() {
        if (hoveredDropTopic) {
            hoveredDropTopic.classList.remove("is-drop-target");
            hoveredDropTopic = null;
        }
    }

    if (toggleCatalogBtn && constructorPanel) {
        toggleCatalogBtn.addEventListener("click", () => {
            constructorPanel.classList.toggle("is-collapsed");
        });
    }

    if (toggleCourseBtn && courseMeta) {
        toggleCourseBtn.addEventListener("click", () => {
            courseMeta.classList.toggle("is-collapsed");
        });
    }

    if (courseInput) {
        courseInput.addEventListener("input", () => {
            state.courseLabel = courseInput.value;
            if (courseCounter) {
                courseCounter.textContent = titleCounter(state.courseLabel);
            }
            persistState();
        });
    }

    if (courseTitleInput) {
        courseTitleInput.addEventListener("input", () => {
            state.courseTitle = courseTitleInput.value;
            if (courseTitleCounter) {
                courseTitleCounter.textContent = titleCounter(state.courseTitle);
            }
            persistState();
        });
    }

    if (catalogRoot) {
        catalogRoot.addEventListener("click", (event) => {
            const target = event.target;
            if (!(target instanceof Element)) {
                return;
            }
            const button = target.closest('[data-action="add-block"]');
            if (!button) {
                return;
            }
            const blockId = button.getAttribute("data-block-id");
            if (!blockId) {
                return;
            }
            const activeTopic = ensureActiveTopic();
            if (!activeTopic) {
                return;
            }
            addCatalogBlock(blockId, state.activeModuleId, state.activeTopicId);
        });

        catalogRoot.addEventListener("dragstart", (event) => {
            const target = event.target;
            if (!(target instanceof Element)) {
                return;
            }
            const item = target.closest('[data-action="add-block"]');
            if (!item) {
                return;
            }
            const blockId = item.getAttribute("data-block-id") || "";
            if (!blockId) {
                return;
            }
            item.classList.add("is-dragging");
            event.dataTransfer?.setData("text/plain", blockId);
            event.dataTransfer?.setData("application/x-course-block", blockId);
            event.dataTransfer?.setDragImage(item, 24, 14);
        });

        catalogRoot.addEventListener("dragend", () => {
            catalogRoot.querySelectorAll(".cb-catalog-item.is-dragging").forEach((node) => node.classList.remove("is-dragging"));
        });
    }

    if (addModuleBtn) {
        addModuleBtn.addEventListener("click", addModule);
    }

    if (addModuleInlineBtn) {
        addModuleInlineBtn.addEventListener("click", addModule);
    }

    if (addTopicBtn) {
        addTopicBtn.addEventListener("click", () => {
            const module = getModule(state.activeModuleId) || state.modules[0];
            if (module) {
                addTopic(module.id);
            }
        });
    }

    if (modulesRoot) {
        modulesRoot.addEventListener("dragover", (event) => {
            const target = event.target;
            if (!(target instanceof Element)) {
                return;
            }
            const body = target.closest("[data-drop-module-id][data-drop-topic-id]");
            if (!body) {
                clearDropTarget();
                return;
            }
            event.preventDefault();
            const topic = body.closest(".cb-topic");
            if (topic instanceof HTMLElement) {
                setDropTarget(topic);
            }
        });

        modulesRoot.addEventListener("dragleave", (event) => {
            const related = event.relatedTarget;
            if (!(related instanceof Element) || !modulesRoot.contains(related)) {
                clearDropTarget();
            }
        });

        modulesRoot.addEventListener("drop", (event) => {
            const target = event.target;
            if (!(target instanceof Element)) {
                clearDropTarget();
                return;
            }
            const body = target.closest("[data-drop-module-id][data-drop-topic-id]");
            const blockId = event.dataTransfer?.getData("application/x-course-block") || event.dataTransfer?.getData("text/plain");
            if (!body || !blockId) {
                clearDropTarget();
                return;
            }
            event.preventDefault();
            const moduleId = body.getAttribute("data-drop-module-id") || "";
            const topicId = body.getAttribute("data-drop-topic-id") || "";
            if (moduleId && topicId) {
                state.activeModuleId = moduleId;
                state.activeTopicId = topicId;
                addCatalogBlock(blockId, moduleId, topicId);
            }
            clearDropTarget();
        });

        modulesRoot.addEventListener("click", (event) => {
            const target = event.target;
            if (!(target instanceof Element)) {
                return;
            }

            const removeItemBtn = target.closest('[data-action="remove-item"]');
            if (removeItemBtn) {
                removeItem(
                    String(removeItemBtn.getAttribute("data-module-id") || ""),
                    String(removeItemBtn.getAttribute("data-topic-id") || ""),
                    String(removeItemBtn.getAttribute("data-item-id") || "")
                );
                return;
            }

            const toggleItemPreviewBtn = target.closest('[data-action="toggle-item-preview"]');
            if (toggleItemPreviewBtn) {
                const moduleId = String(toggleItemPreviewBtn.getAttribute("data-module-id") || "");
                const topicId = String(toggleItemPreviewBtn.getAttribute("data-topic-id") || "");
                const itemId = String(toggleItemPreviewBtn.getAttribute("data-item-id") || "");
                const item = getItem(moduleId, topicId, itemId);
                if (item) {
                    item.expanded = !item.expanded;
                    persistState();
                    render();
                }
                return;
            }

            const quizAddQuestionBtn = target.closest('[data-action="quiz-add-question"]');
            if (quizAddQuestionBtn) {
                const moduleId = String(quizAddQuestionBtn.getAttribute("data-module-id") || "");
                const topicId = String(quizAddQuestionBtn.getAttribute("data-topic-id") || "");
                const itemId = String(quizAddQuestionBtn.getAttribute("data-item-id") || "");
                const item = getItem(moduleId, topicId, itemId);
                if (item && item.blockId === "quiz") {
                    const quiz = ensureQuizModel(item);
                    quiz.questions.push(createQuizQuestion(quiz.questions.length + 1));
                    persistState();
                    render();
                }
                return;
            }

            const quizRemoveQuestionBtn = target.closest('[data-action="quiz-remove-question"]');
            if (quizRemoveQuestionBtn) {
                const moduleId = String(quizRemoveQuestionBtn.getAttribute("data-module-id") || "");
                const topicId = String(quizRemoveQuestionBtn.getAttribute("data-topic-id") || "");
                const itemId = String(quizRemoveQuestionBtn.getAttribute("data-item-id") || "");
                const questionId = String(quizRemoveQuestionBtn.getAttribute("data-question-id") || "");
                const item = getItem(moduleId, topicId, itemId);
                if (item && item.blockId === "quiz") {
                    const quiz = ensureQuizModel(item);
                    if (quiz.questions.length > 1) {
                        quiz.questions = quiz.questions.filter((question) => question.id !== questionId);
                        persistState();
                        render();
                    }
                }
                return;
            }

            const quizAddOptionBtn = target.closest('[data-action="quiz-add-option"]');
            if (quizAddOptionBtn) {
                const moduleId = String(quizAddOptionBtn.getAttribute("data-module-id") || "");
                const topicId = String(quizAddOptionBtn.getAttribute("data-topic-id") || "");
                const itemId = String(quizAddOptionBtn.getAttribute("data-item-id") || "");
                const questionId = String(quizAddOptionBtn.getAttribute("data-question-id") || "");
                const item = getItem(moduleId, topicId, itemId);
                if (item && item.blockId === "quiz") {
                    const quiz = ensureQuizModel(item);
                    const question = quiz.questions.find((entry) => entry.id === questionId);
                    if (question) {
                        question.options.push("Вариант " + (question.options.length + 1));
                        persistState();
                        render();
                    }
                }
                return;
            }

            const quizRemoveOptionBtn = target.closest('[data-action="quiz-remove-option"]');
            if (quizRemoveOptionBtn) {
                const moduleId = String(quizRemoveOptionBtn.getAttribute("data-module-id") || "");
                const topicId = String(quizRemoveOptionBtn.getAttribute("data-topic-id") || "");
                const itemId = String(quizRemoveOptionBtn.getAttribute("data-item-id") || "");
                const questionId = String(quizRemoveOptionBtn.getAttribute("data-question-id") || "");
                const optionIndex = Number(quizRemoveOptionBtn.getAttribute("data-option-index"));
                const item = getItem(moduleId, topicId, itemId);
                if (item && item.blockId === "quiz") {
                    const quiz = ensureQuizModel(item);
                    const question = quiz.questions.find((entry) => entry.id === questionId);
                    if (question && question.options.length > 1 && Number.isInteger(optionIndex)) {
                        question.options.splice(optionIndex, 1);
                        persistState();
                        render();
                    }
                }
                return;
            }

            const removeTopicBtn = target.closest('[data-action="remove-topic"]');
            if (removeTopicBtn) {
                removeTopic(
                    String(removeTopicBtn.getAttribute("data-module-id") || ""),
                    String(removeTopicBtn.getAttribute("data-topic-id") || "")
                );
                return;
            }

            const addTopicModuleBtn = target.closest('[data-action="add-topic-module"]');
            if (addTopicModuleBtn) {
                const moduleId = addTopicModuleBtn.getAttribute("data-module-id");
                if (moduleId) {
                    addTopic(moduleId);
                }
                return;
            }

            const toggleModuleBtn = target.closest('[data-action="toggle-module"]');
            if (toggleModuleBtn) {
                const moduleId = toggleModuleBtn.getAttribute("data-module-id");
                const module = moduleId ? getModule(moduleId) : null;
                if (module) {
                    module.collapsed = !module.collapsed;
                    persistState();
                    render();
                }
                return;
            }

            const removeModuleBtn = target.closest('[data-action="remove-module"]');
            if (removeModuleBtn) {
                const moduleId = removeModuleBtn.getAttribute("data-module-id");
                if (moduleId) {
                    removeModule(moduleId);
                }
                return;
            }

            const toggleCustomBtn = target.closest('[data-action="toggle-custom"]');
            if (toggleCustomBtn) {
                const moduleId = toggleCustomBtn.getAttribute("data-module-id");
                const topicId = toggleCustomBtn.getAttribute("data-topic-id");
                const topic = moduleId && topicId ? getTopic(moduleId, topicId) : null;
                if (topic) {
                    topic.showCustomEditor = !topic.showCustomEditor;
                    persistState();
                    render();
                }
            }

            const selectTopic = target.closest('[data-action="select-topic"]');
            if (selectTopic) {
                const moduleId = selectTopic.getAttribute("data-module-id");
                const topicId = selectTopic.getAttribute("data-topic-id");
                if (!moduleId || !topicId) {
                    return;
                }

                const changed = state.activeModuleId !== moduleId || state.activeTopicId !== topicId;
                state.activeModuleId = moduleId;
                state.activeTopicId = topicId;

                if (!changed) {
                    return;
                }

                const clickedEditable = target.closest("input, textarea, button") !== null;
                persistState();
                if (clickedEditable) {
                    applyActiveTopicClass(moduleId, topicId);
                } else {
                    render();
                }
            }
        });

        modulesRoot.addEventListener("input", (event) => {
            const target = event.target;
            if (!(target instanceof Element)) {
                return;
            }

            if (target instanceof HTMLInputElement && target.getAttribute("data-action") === "rename-module") {
                const moduleId = target.getAttribute("data-module-id");
                const module = moduleId ? getModule(moduleId) : null;
                if (module) {
                    module.title = target.value;
                    const counter = target.parentElement?.querySelector(".cb-counter");
                    if (counter) {
                        counter.textContent = titleCounter(module.title);
                    }
                    persistState();
                }
                return;
            }

            if (target instanceof HTMLInputElement && target.getAttribute("data-action") === "rename-topic") {
                const moduleId = target.getAttribute("data-module-id");
                const topicId = target.getAttribute("data-topic-id");
                const topic = moduleId && topicId ? getTopic(moduleId, topicId) : null;
                if (topic) {
                    topic.title = target.value;
                    const counter = target.parentElement?.querySelector(".cb-topic-counter");
                    if (counter) {
                        counter.textContent = titleCounter(topic.title);
                    }
                    persistState();
                }
                return;
            }

            if (target instanceof HTMLInputElement && target.getAttribute("data-action") === "rename-item") {
                const moduleId = String(target.getAttribute("data-module-id") || "");
                const topicId = String(target.getAttribute("data-topic-id") || "");
                const itemId = String(target.getAttribute("data-item-id") || "");
                const item = getItem(moduleId, topicId, itemId);
                if (item) {
                    item.title = target.value;
                    persistState();
                }
                return;
            }

            if (target instanceof HTMLInputElement && String(target.getAttribute("data-action") || "").startsWith("quiz-")) {
                const action = String(target.getAttribute("data-action") || "");
                const moduleId = String(target.getAttribute("data-module-id") || "");
                const topicId = String(target.getAttribute("data-topic-id") || "");
                const itemId = String(target.getAttribute("data-item-id") || "");
                const questionId = String(target.getAttribute("data-question-id") || "");
                const optionIndex = Number(target.getAttribute("data-option-index"));
                const item = getItem(moduleId, topicId, itemId);
                if (!item || item.blockId !== "quiz") {
                    return;
                }
                const quiz = ensureQuizModel(item);
                if (!quiz) {
                    return;
                }
                if (action === "quiz-edit-intro") {
                    quiz.intro = target.value;
                    const counter = target.parentElement?.querySelector(".cb-counter");
                    if (counter) {
                        counter.textContent = titleCounter(quiz.intro);
                    }
                }
                if (action === "quiz-edit-passing") {
                    quiz.passingScore = target.value;
                }
                if (action === "quiz-edit-attempts") {
                    quiz.attempts = target.value;
                }
                if (action === "quiz-edit-duration") {
                    quiz.duration = target.value;
                }
                if (action === "quiz-edit-question") {
                    const question = quiz.questions.find((entry) => entry.id === questionId);
                    if (question) {
                        question.title = target.value;
                    }
                }
                if (action === "quiz-edit-option") {
                    const question = quiz.questions.find((entry) => entry.id === questionId);
                    if (question && Number.isInteger(optionIndex) && optionIndex >= 0 && optionIndex < question.options.length) {
                        question.options[optionIndex] = target.value;
                    }
                }
                persistState();
                return;
            }

            if (target instanceof HTMLTextAreaElement && target.getAttribute("data-action") === "edit-custom") {
                const moduleId = target.getAttribute("data-module-id");
                const topicId = target.getAttribute("data-topic-id");
                const topic = moduleId && topicId ? getTopic(moduleId, topicId) : null;
                if (topic) {
                    topic.customContent = target.value;
                    persistState();
                }
            }
        });

        modulesRoot.addEventListener("change", (event) => {
            const target = event.target;
            if (!(target instanceof HTMLSelectElement)) {
                return;
            }
            if (target.getAttribute("data-action") !== "quiz-edit-type") {
                return;
            }
            const moduleId = String(target.getAttribute("data-module-id") || "");
            const topicId = String(target.getAttribute("data-topic-id") || "");
            const itemId = String(target.getAttribute("data-item-id") || "");
            const questionId = String(target.getAttribute("data-question-id") || "");
            const item = getItem(moduleId, topicId, itemId);
            if (!item || item.blockId !== "quiz") {
                return;
            }
            const quiz = ensureQuizModel(item);
            const question = quiz.questions.find((entry) => entry.id === questionId);
            if (question) {
                question.type = target.value === "multi" ? "multi" : "single";
                persistState();
            }
        });
    }

    const restored = restoreState();
    if (!restored || state.modules.length === 0) {
        addModule();
        if (state.catalog[0]) {
            addCatalogBlock(state.catalog[0].id, state.activeModuleId, state.activeTopicId);
        }
    }

    ensureActiveTopic();
    render();
    hydrateAllItems();
});
