// app/static/js/students.js

document.addEventListener('DOMContentLoaded', function() {
    const studentsTableBody = document.querySelector('#studentsTable tbody');
    const addStudentBtn = document.getElementById('addStudentBtn');
    const batchDeleteBtn = document.getElementById('batchDeleteBtn');
    const searchBtn = document.getElementById('searchBtn');
    const filterMajorSelect = document.getElementById('filterMajorSelect');
    const searchKeywordInput = document.getElementById('searchKeywordInput');
    const selectAllStudentsCheckbox = document.getElementById('selectAllStudents');
    const paginationDiv = document.getElementById('pagination');

    const studentModal = document.getElementById('studentModal');
    const modalTitle = document.getElementById('modalTitle');
    const studentForm = document.getElementById('studentForm');
    const closeButton = studentModal.querySelector('.close-button');
    const saveStudentBtn = document.getElementById('saveStudentBtn');
    const cancelStudentBtn = document.getElementById('cancelStudentBtn');

    let currentPage = 1;
    const itemsPerPage = 10; // 每页显示的学生数量

    // -- Functions --

    /**
     * 渲染学生表格内容
     * @param {Array} students - 学生数据数组
     */
    function renderStudentsTable(students) {
        studentsTableBody.innerHTML = ''; // 清空现有内容
        if (students.length === 0) {
            studentsTableBody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 20px;">暂无学生数据</td></tr>';
            return;
        }
        students.forEach(student => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><input type="checkbox" class="student-checkbox" data-id="${student.id}"></td>
                <td>${student.student_id}</td>
                <td>${student.name}</td>
                <td>${student.major}</td>
                <td>${student.birthdate || ''}</td>
                <td>${student.enrollment_date || ''}</td>
                <td>${student.origin || ''}</td>
                <td class="action-buttons">
                    <button class="edit-btn action-button" data-id="${student.id}">编辑</button>
                    <button class="delete-btn action-button danger" data-id="${student.id}">删除</button>
                </td>
            `;
            studentsTableBody.appendChild(row);
        });
        // 渲染完成后重置全选框状态
        selectAllStudentsCheckbox.checked = false;
    }

    /**
     * 从后端获取学生数据并渲染表格和分页
     * @param {number} page - 当前页码
     * @param {string} major - 筛选的专业
     * @param {string} keyword - 搜索关键词
     */
    async function fetchAndRenderStudents(page = 1, major = '', keyword = '') {
        const queryParams = new URLSearchParams({
            page: page,
            limit: itemsPerPage,
            major: major,
            keyword: keyword
        });
        // !!! 假设后端有一个用于获取学生列表的 API 路由，例如 /api/students
        const url = `/api/students?${queryParams.toString()}`;

        try {
            const response = await fetch(url);
            if (!response.ok) {
                // 检查HTTP状态码
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            if (data.code === 0) { // 假设后端返回 code: 0 表示成功
                renderStudentsTable(data.data); // 渲染学生表格
                renderPagination(data.count, page); // 渲染分页控件
                populateMajors(data.all_majors || []); // 填充专业筛选下拉框
            } else {
                alert('获取学生数据失败: ' + (data.msg || '未知错误'));
            }
        } catch (error) {
            console.error('Error fetching students:', error);
            alert('加载学生数据时发生错误，请检查网络或后端服务。');
        }
    }

    /**
     * 渲染分页控件
     * @param {number} totalCount - 数据总数
     * @param {number} currentPage - 当前页码
     */
    function renderPagination(totalCount, currentPage) {
        paginationDiv.innerHTML = ''; // 清空现有内容
        const totalPages = Math.ceil(totalCount / itemsPerPage);

        if (totalPages <= 1) return; // 如果只有一页或没有数据，不显示分页

        // Prev button
        const prevBtn = document.createElement('button');
        prevBtn.textContent = '上一页';
        prevBtn.classList.add('page-button');
        prevBtn.disabled = currentPage === 1;
        prevBtn.addEventListener('click', () => {
            currentPage--;
            fetchAndRenderStudents(currentPage, filterMajorSelect.value, searchKeywordInput.value);
        });
        paginationDiv.appendChild(prevBtn);

        // Page number buttons
        for (let i = 1; i <= totalPages; i++) {
            const btn = document.createElement('button');
            btn.textContent = i;
            btn.classList.add('page-button');
            if (i === currentPage) {
                btn.classList.add('active');
            }
            btn.addEventListener('click', () => {
                currentPage = i;
                fetchAndRenderStudents(currentPage, filterMajorSelect.value, searchKeywordInput.value);
            });
            paginationDiv.appendChild(btn);
        }

        // Next button
        const nextBtn = document.createElement('button');
        nextBtn.textContent = '下一页';
        nextBtn.classList.add('page-button');
        nextBtn.disabled = currentPage === totalPages;
        nextBtn.addEventListener('click', () => {
            currentPage++;
            fetchAndRenderStudents(currentPage, filterMajorSelect.value, searchKeywordInput.value);
        });
        paginationDiv.appendChild(nextBtn);
    }

    /**
     * 填充专业筛选下拉框
     * @param {Array} majors - 专业名称数组
     */
    function populateMajors(majors) {
        // 避免重复添加，每次都清空再添加
        filterMajorSelect.innerHTML = '<option value="">所有专业</option>';
        majors.forEach(major => {
            const option = document.createElement('option');
            option.value = major;
            option.textContent = major;
            filterMajorSelect.appendChild(option);
        });
        // 保持筛选状态
        const currentMajor = sessionStorage.getItem('filterMajor');
        if (currentMajor) {
            filterMajorSelect.value = currentMajor;
        }
    }

    /**
     * 显示模态框
     * @param {string} title - 模态框标题
     * @param {object} [student=null] - 要编辑的学生数据，如果是添加则为 null
     */
    function showModal(title, student = null) {
        modalTitle.textContent = title;
        studentForm.reset(); // 清空表单

        if (student) {
            // 填充表单数据
            document.getElementById('studentId').value = student.id || '';
            document.getElementById('student_id').value = student.student_id || '';
            document.getElementById('name').value = student.name || '';
            document.getElementById('major').value = student.major || '';
            document.getElementById('birthdate').value = student.birthdate || '';
            document.getElementById('enrollment_date').value = student.enrollment_date || '';
            document.getElementById('origin').value = student.origin || '';
        } else {
            // 添加学生时确保ID为空
            document.getElementById('studentId').value = '';
        }
        studentModal.style.display = 'flex'; // 显示模态框 (使用 flexbox 居中)
    }

    /**
     * 隐藏模态框
     */
    function hideModal() {
        studentModal.style.display = 'none';
        studentForm.reset(); // 隐藏时重置表单
    }

    // -- Event Listeners --

    // 页面加载完成后，首次获取并渲染学生数据
    fetchAndRenderStudents(currentPage);

    // "添加学生" 按钮点击事件
    addStudentBtn.addEventListener('click', () => {
        showModal('添加新学生');
    });

    // "批量删除" 按钮点击事件
    batchDeleteBtn.addEventListener('click', async () => {
        const selectedIds = Array.from(document.querySelectorAll('.student-checkbox:checked'))
                               .map(cb => cb.dataset.id); // 获取所有选中学生的ID

        if (selectedIds.length === 0) {
            alert('请选择要删除的学生');
            return;
        }

        if (confirm(`确定要批量删除这 ${selectedIds.length} 名学生吗？`)) {
            // !!! 假设后端有一个用于批量删除的 API 路由，例如 /api/students/batch_delete
            try {
                const response = await fetch('{{ url_for("admin.batch_delete_students_api") }}', { // 您需要在admin.py中定义此API
                    method: 'POST', // 或 DELETE，根据后端设计
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ student_ids: selectedIds })
                });
                const data = await response.json();
                if (data.code === 0) {
                    alert('批量删除成功');
                    fetchAndRenderStudents(currentPage, filterMajorSelect.value, searchKeywordInput.value); // 刷新表格
                } else {
                    alert('批量删除失败: ' + (data.msg || '未知错误'));
                }
            } catch (error) {
                console.error('Error batch deleting:', error);
                alert('批量删除请求失败，请检查网络或后端服务。');
            }
        }
    });

    // "搜索" 按钮点击事件
    searchBtn.addEventListener('click', () => {
        currentPage = 1; // 搜索时重置回第一页
        fetchAndRenderStudents(currentPage, filterMajorSelect.value, searchKeywordInput.value);
    });

    // 专业筛选下拉框变化事件
    filterMajorSelect.addEventListener('change', () => {
        sessionStorage.setItem('filterMajor', filterMajorSelect.value); // 保存选择状态
        currentPage = 1; // 筛选时重置回第一页
        fetchAndRenderStudents(currentPage, filterMajorSelect.value, searchKeywordInput.value);
    });

    // "全选/取消全选" 复选框事件
    selectAllStudentsCheckbox.addEventListener('change', (e) => {
        const checkboxes = document.querySelectorAll('.student-checkbox');
        checkboxes.forEach(cb => cb.checked = e.target.checked);
    });

    // 表格内部的 "编辑" 和 "删除" 按钮事件委托 (利用事件冒泡)
    studentsTableBody.addEventListener('click', async (e) => {
        if (e.target.classList.contains('edit-btn')) {
            const studentId = e.target.dataset.id;
            // !!! 假设后端有一个获取单个学生数据的 API 路由，例如 /api/students/<id>
            try {
                const response = await fetch(`/api/students/${studentId}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                if (data.code === 0 && data.data) {
                    showModal('编辑学生信息', data.data);
                } else {
                    alert('获取学生信息失败: ' + (data.msg || '未知错误'));
                }
            } catch (error) {
                console.error('Error fetching single student:', error);
                alert('获取学生信息时发生错误。');
            }
        } else if (e.target.classList.contains('delete-btn')) {
            const studentId = e.target.dataset.id;
            const studentName = e.target.closest('tr').children[2].textContent; // 假设姓名在第三列

            if (confirm(`确定要删除学生：${studentName} (ID: ${studentId}) 吗？`)) {
                // !!! 假设后端有一个用于删除单个学生的 API 路由，例如 /api/students/<id>
                try {
                    const response = await fetch(`{{ url_for("admin.delete_student_api", student_id="") }}${studentId}`, { // 您需要在admin.py中定义此API
                        method: 'POST', // 或 DELETE，根据后端设计
                    });
                    const data = await response.json();
                    if (data.code === 0) {
                        alert('删除成功');
                        fetchAndRenderStudents(currentPage, filterMajorSelect.value, searchKeywordInput.value); // 刷新表格
                    } else {
                        alert('删除失败: ' + (data.msg || '未知错误'));
                    }
                } catch (error) {
                    console.error('Error deleting student:', error);
                    alert('删除请求失败，请检查网络或后端服务。');
                }
            }
        }
    });

    // 模态框关闭按钮事件
    closeButton.addEventListener('click', hideModal);
    cancelStudentBtn.addEventListener('click', hideModal);

    // 点击模态框外部区域关闭模态框
    window.addEventListener('click', (event) => {
        if (event.target === studentModal) {
            hideModal();
        }
    });

    // 表单提交事件 (添加或编辑学生)
    studentForm.addEventListener('submit', async (e) => {
        e.preventDefault(); // 阻止表单默认提交行为

        const formData = new FormData(studentForm);
        const studentData = Object.fromEntries(formData.entries()); // 将 FormData 转换为普通对象

        const studentId = document.getElementById('studentId').value;
        const isEdit = studentId !== ''; // 根据是否有ID判断是编辑还是添加

        let url, method;
        if (isEdit) {
            // !!! 假设后端有一个用于编辑学生信息的 API 路由，例如 /api/students/<id>
            url = `{{ url_for("admin.edit_student_api", student_id="") }}${studentId}`; // 您需要在admin.py中定义此API
            method = 'POST'; // 或 PUT
        } else {
            // !!! 假设后端有一个用于添加学生的 API 路由，例如 /api/students/add
            url = `{{ url_for("admin.add_student_api") }}`; // 您需要在admin.py中定义此API
            method = 'POST';
        }

        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(studentData) // 将数据转换为 JSON 字符串发送
            });
            const data = await response.json();

            if (data.code === 0) {
                alert(isEdit ? '学生信息更新成功' : '学生添加成功');
                hideModal(); // 隐藏模态框
                fetchAndRenderStudents(currentPage, filterMajorSelect.value, searchKeywordInput.value); // 刷新表格
            } else {
                alert((isEdit ? '保存失败: ' : '添加失败: ') + (data.msg || '未知错误'));
            }
        } catch (error) {
            console.error('Form submission error:', error);
            alert('提交请求失败，请检查网络或后端服务。');
        }
    });
});