(function () {
    function initSemanticRouter(root) {
        var form = root.querySelector("[data-semantic-router-form]");
        var input = root.querySelector("[data-semantic-router-input]");
        var status = root.querySelector("[data-semantic-router-status]");
        var options = root.querySelector("[data-semantic-router-options]");

        if (!form || !input || !status || !options) {
            return;
        }

        form.addEventListener("submit", function (event) {
            event.preventDefault();
            var query = input.value.trim();
            options.innerHTML = "";
            if (!query) {
                status.textContent = "Введите запрос.";
                return;
            }

            status.textContent = "Ищем подходящий раздел...";
            fetch("/api/semantic-router/search", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ query: query })
            })
                .then(function (response) {
                    return response.json().then(function (payload) {
                        if (!response.ok) {
                            throw new Error(payload.message || "Сервис недоступен.");
                        }
                        return payload;
                    });
                })
                .then(function (payload) {
                    if (payload.status === "success" && payload.path) {
                        status.textContent = "Открываем: " + payload.title;
                        window.location.href = payload.path;
                        return;
                    }

                    if (payload.status === "clarify") {
                        status.textContent = payload.options && payload.options.length ? "Выберите подходящий раздел:" : "Подходящих разделов пока нет.";
                        renderOptions(options, payload.options || []);
                        return;
                    }

                    status.textContent = payload.message || "Не удалось найти раздел.";
                })
                .catch(function (error) {
                    status.textContent = error.message;
                });
        });
    }

    function renderOptions(container, items) {
        container.innerHTML = "";
        items.forEach(function (item) {
            if (!item.path || !item.title) {
                return;
            }
            var link = document.createElement("a");
            link.className = "semantic-router-option";
            link.href = item.path;
            link.textContent = item.title;
            container.appendChild(link);
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-semantic-router]").forEach(initSemanticRouter);
    });
})();
