document.addEventListener('DOMContentLoaded', function () {
    function resolvePanel(block, trigger) {
        var panelId = trigger.getAttribute('aria-controls');
        if (panelId) {
            return document.getElementById(panelId);
        }
        return block.querySelector('.block-items');
    }

    function syncBlockState(block, trigger, panel, isCollapsed) {
        var labelCollapsed = trigger.getAttribute('data-label-collapsed');
        var labelExpanded = trigger.getAttribute('data-label-expanded');

        block.classList.toggle('collapsed', isCollapsed);
        block.dataset.state = isCollapsed ? 'collapsed' : 'expanded';
        trigger.setAttribute('aria-expanded', String(!isCollapsed));
        if (labelCollapsed && labelExpanded) {
            trigger.setAttribute('aria-label', isCollapsed ? labelCollapsed : labelExpanded);
        }
        trigger.title = isCollapsed ? 'Развернуть' : 'Свернуть';
        if (panel) {
            panel.setAttribute('aria-hidden', String(isCollapsed));
        }
    }

    // Инициализация кнопок сворачивания/разворачивания
    document.querySelectorAll('.curse-block .cross').forEach(function (btn) {
        var block = btn.closest('.curse-block');
        if (!block) return;

        var panel = resolvePanel(block, btn);
        var isCollapsed = block.classList.contains('collapsed') || block.dataset.state === 'collapsed';
        syncBlockState(block, btn, panel, isCollapsed);

        btn.addEventListener('click', function () {
            var nowCollapsed = !block.classList.contains('collapsed');
            syncBlockState(block, btn, panel, nowCollapsed);
        });

        // Поддержка клавиш Enter/Space для нестандартных кейсов
        btn.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                btn.click();
            }
        });
    });
});
