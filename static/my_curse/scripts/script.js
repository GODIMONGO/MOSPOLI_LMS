document.addEventListener('DOMContentLoaded', function () {
    // Инициализация кнопок сворачивания/разворачивания
    document.querySelectorAll('.curse-block .cross').forEach(function (btn) {
        var block = btn.closest('.curse-block');
        var panel = block.querySelector('.block-items');

        // Установить начальное значение aria (соответствует наличию класса collapsed)
        var isCollapsed = block.classList.contains('collapsed');
        btn.setAttribute('aria-expanded', String(!isCollapsed));
        if (panel) panel.setAttribute('aria-hidden', String(isCollapsed));
        btn.title = isCollapsed ? 'Развернуть' : 'Свернуть';

        // Обработчик клика
        btn.addEventListener('click', function () {
            var nowCollapsed = block.classList.toggle('collapsed'); // true если теперь свернут
            btn.setAttribute('aria-expanded', String(!nowCollapsed));
            if (panel) panel.setAttribute('aria-hidden', String(nowCollapsed));
            btn.title = nowCollapsed ? 'Развернуть' : 'Свернуть';
        });

        // Поддержка клавиш Enter/Space
        btn.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                btn.click();
            }
        });
    });
});