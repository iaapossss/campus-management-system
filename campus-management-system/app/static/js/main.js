// app/static/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    // 全局通用 JavaScript 逻辑可以在这里添加
    // 例如：侧边栏的展开/折叠、全局导航的交互等

    // 侧边栏子菜单展开/折叠示例
    const hasSubmenus = document.querySelectorAll('.sidebar-nav .has-submenu > a');
    hasSubmenus.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault(); // 阻止默认跳转
            const parentLi = this.closest('li');
            parentLi.classList.toggle('expanded'); // 切换 expanded 类
        });
    });

    // 这里可以添加其他通用功能，如：
    // - 登出确认弹窗
    // - 顶部导航的用户菜单下拉
});