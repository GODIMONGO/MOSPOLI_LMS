# План настройки Codex GitHub Actions

1. Создать инфраструктуру для Codex в репозитории:
- Добавить каталог `.github/codex/` и хранить там `config.toml` + шаблоны промптов.
- В `config.toml` зафиксировать полный custom-provider конфиг (`model_provider`, `base_url`, `chatgpt_base_url`, `wire_api`, фичи и лимиты).
- Вынести общие инструкции для `issue` и `pull_request` в отдельные markdown-файлы.

2. Настроить workflow c запуском по тегу:
- Создать `.github/workflows/codex-auto.yml`.
- Триггеры: `issues` и `pull_request` (opened/edited/reopened/labeled/synchronize).
- Условие запуска: у issue/PR должен быть label `codex`.

3. Интегрировать Codex запуск:
- Устанавливать Codex CLI в job через `npm install -g @openai/codex@latest`.
- `OPENAI_API_KEY` опционален для custom backend; при отсутствии выставляется placeholder для совместимости CLI.
- Использовать репозиторный `.github/codex/config.toml` либо секрет `CODEX_CONFIG_TOML` для override.
- Установить custom CA certificate из `.github/codex/certs/cert.pem` (или override через `CODEX_CA_CERT_PEM`, raw PEM/base64) перед запуском Codex.

4. Сформировать контекстные промпты:
- На лету собирать runtime prompt из шаблона + метаданных issue/PR.
- Для PR дополнительно подтягивать base/head refs для корректного review diff.

5. Публиковать результат:
- Брать `final-message` из выхода шага Codex.
- Автоматически публиковать комментарий в соответствующий issue/PR.

6. Валидация:
- Проверить синтаксис workflow и структуру файлов.
- Проверить `git status`, что изменения ограничены workflow/infra-файлами.
