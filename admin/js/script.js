document.addEventListener('DOMContentLoaded', async () => {
    let currentUser = '';
    let currentRole = '';
    let allMessages = [];
    let showPII = false;
    let currentPage = 1;
    const ITEMS_PER_PAGE = 8;

    // --- UTILITIES ---
    function escapeHTML(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function maskEmail(email) {
        if (!email) return '';
        const [local, domain] = email.split('@');
        if (!domain) return email;
        if (local.length <= 2) return email;
        return local[0] + '***' + local[local.length - 1] + '@' + domain;
    }

    function maskName(name) {
        if (!name) return '';
        if (name.length <= 2) return name;
        return name[0] + '*'.repeat(name.length - 2) + name[name.length - 1];
    }

    function showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icons = {
            success: '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
            error: '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
            info: '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
        };

        toast.innerHTML = `
            ${icons[type] || icons.info}
            <span class="toast-message">${escapeHTML(message)}</span>
            <button class="toast-dismiss" onclick="this.parentElement.remove()" aria-label="Cerrar">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
        `;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'toastOut 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    function showConfirm(title, message) {
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.className = 'confirm-overlay';
            overlay.innerHTML = `
                <div class="confirm-dialog">
                    <div class="confirm-dialog-icon">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                    </div>
                    <h3>${escapeHTML(title)}</h3>
                    <p>${escapeHTML(message)}</p>
                    <div class="confirm-actions">
                        <button class="btn btn-outline btn-sm confirm-cancel">Cancelar</button>
                        <button class="btn btn-danger btn-sm confirm-ok">Eliminar</button>
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);

            overlay.querySelector('.confirm-cancel').onclick = () => { overlay.remove(); resolve(false); };
            overlay.querySelector('.confirm-ok').onclick = () => { overlay.remove(); resolve(true); };
            overlay.onclick = (e) => { if (e.target === overlay) { overlay.remove(); resolve(false); } };
        });
    }

    function formatDate(dateStr) {
        if (!dateStr) return '-';
        const d = new Date(dateStr);
        return d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
    }

    function formatTime(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        return d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    }

    function getDayNum(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        return d.getDate();
    }

    function getMonthName(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        return d.toLocaleDateString('es-ES', { month: 'short' });
    }

    // --- AUTH ---
    let userData = null;
    try {
        const authRes = await fetch('/api/check-auth');
        const authData = await authRes.json();
        if (!authData.authenticated) {
            window.location.href = 'login.html';
            return;
        }
        userData = authData;
        currentUser = authData.username;
        currentRole = authData.role;

        const displayName = authData.full_name || authData.username;
        const initial = displayName.charAt(0).toUpperCase();

        document.getElementById('adminUsername').textContent = displayName;
        document.getElementById('topbarAvatar').textContent = initial;
        document.getElementById('sidebarAvatar').textContent = initial;
        document.getElementById('sidebarUserName').textContent = displayName;
        document.getElementById('sidebarUserRole').textContent = authData.role === 'admin' ? 'Administrador' : 'Visualizador';
    } catch (e) {
        window.location.href = 'login.html';
        return;
    }

    // --- LOGOUT ---
    document.getElementById('logoutBtn').addEventListener('click', async (e) => {
        e.preventDefault();
        await fetch('/api/logout', { method: 'POST' });
        window.location.href = 'login.html';
    });

    // --- USER DROPDOWN ---
    const userMenu = document.getElementById('userMenu');
    const userMenuTrigger = document.getElementById('userMenuTrigger');
    userMenuTrigger.addEventListener('click', (e) => {
        e.stopPropagation();
        userMenu.classList.toggle('open');
    });

    document.getElementById('myAccountLink').addEventListener('click', (e) => {
        e.preventDefault();
        userMenu.classList.remove('open');
        openAccountModal();
    });

    document.addEventListener('click', () => userMenu.classList.remove('open'));

    // --- SIDEBAR ---
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');

    mobileMenuBtn.addEventListener('click', () => {
        sidebar.classList.toggle('open');
        sidebarOverlay.classList.toggle('active');
    });

    sidebarOverlay.addEventListener('click', () => {
        sidebar.classList.remove('open');
        sidebarOverlay.classList.remove('active');
    });

    // --- NAVIGATION ---
    const navDashboard = document.getElementById('navDashboard');
    const navMessages = document.getElementById('navMessages');
    const navUsers = document.getElementById('navUsers');
    const panelDashboard = document.getElementById('panelDashboard');
    const panelMessages = document.getElementById('panelMessages');
    const panelUsers = document.getElementById('panelUsers');
    const pageTitle = document.getElementById('pageTitle');

    const navLinks = [navDashboard, navMessages, navUsers];
    const panels = [panelDashboard, panelMessages, panelUsers];

    function switchPanel(activeNav, activePanel, title) {
        navLinks.forEach(n => n.classList.remove('active'));
        panels.forEach(p => p.classList.remove('active'));
        activeNav.classList.add('active');
        activePanel.classList.add('active');
        pageTitle.textContent = title;
        sidebar.classList.remove('open');
        sidebarOverlay.classList.remove('active');
    }

    navDashboard.addEventListener('click', (e) => { e.preventDefault(); switchPanel(navDashboard, panelDashboard, 'Panel Principal'); loadDashboard(); });
    navMessages.addEventListener('click', (e) => { e.preventDefault(); switchPanel(navMessages, panelMessages, 'Gestion de Citas'); loadAppointments(); });
    navUsers.addEventListener('click', (e) => { e.preventDefault(); switchPanel(navUsers, panelUsers, 'Gestion de Usuarios'); loadUsers(); });

    document.getElementById('goToMessages').addEventListener('click', (e) => { e.preventDefault(); switchPanel(navMessages, panelMessages, 'Gestion de Citas'); loadAppointments(); });

    // --- DASHBOARD ---
    async function loadDashboard() {
        try {
            const res = await fetch('/api/dashboard/stats');
            if (res.status === 401) { window.location.href = 'login.html'; return; }
            const stats = await res.json();

            document.getElementById('statPending').textContent = stats.pending;
            document.getElementById('statUpcoming').textContent = stats.upcoming;
            document.getElementById('statPatients').textContent = stats.total_patients;
            document.getElementById('statScheduled').textContent = stats.scheduled;
        } catch (e) {
            console.error('Error loading stats:', e);
        }

        try {
            const res = await fetch('/api/messages');
            if (res.status === 401) { window.location.href = 'login.html'; return; }
            const messages = await res.json();
            const recent = messages.slice(0, 5);
            const container = document.getElementById('recentActivity');

            if (recent.length === 0) {
                container.innerHTML = '<div class="empty-state"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg><p>No hay actividad reciente</p></div>';
                return;
            }

            container.innerHTML = '';
            recent.forEach(msg => {
                const statusClass = msg.estado === 'Agendada' ? 'scheduled' : msg.estado === 'Cancelada' ? 'cancelled' : 'pending';
                const statusText = msg.estado || 'Pendiente';
                const icons = {
                    Pendiente: '&#9202;',
                    Agendada: '&#10004;',
                    Cancelada: '&#10006;'
                };

                const item = document.createElement('div');
                item.className = 'recent-item';
                item.innerHTML = `
                    <div class="recent-item-icon ${statusClass}">${icons[statusText] || '&#9202;'}</div>
                    <div class="recent-item-content">
                        <div class="recent-item-title">${escapeHTML(msg.nombre)}</div>
                        <div class="recent-item-subtitle">${escapeHTML(msg.email)} - ${escapeHTML(statusText)}</div>
                    </div>
                    <span class="recent-item-time">${formatDate(msg.fecha)}</span>
                `;
                container.appendChild(item);
            });
        } catch (e) {
            console.error('Error loading recent activity:', e);
        }
    }

    // --- APPOINTMENTS ---
    const appointmentsList = document.getElementById('appointmentsList');
    const searchInput = document.getElementById('searchInput');
    const statusFilter = document.getElementById('statusFilter');
    const paginationContainer = document.getElementById('pagination');

    function getFilteredMessages() {
        const query = (searchInput.value || '').toLowerCase().trim();
        const status = statusFilter.value;

        return allMessages.filter(msg => {
            const matchStatus = status === 'all' || msg.estado === status;
            const matchSearch = !query ||
                (msg.nombre && msg.nombre.toLowerCase().includes(query)) ||
                (msg.email && msg.email.toLowerCase().includes(query)) ||
                (msg.mensaje && msg.mensaje.toLowerCase().includes(query));
            return matchStatus && matchSearch;
        });
    }

    function renderPagination(total, current) {
        const totalPages = Math.ceil(total / ITEMS_PER_PAGE);
        paginationContainer.innerHTML = '';

        if (totalPages <= 1) return;

        const prevBtn = document.createElement('button');
        prevBtn.className = 'pagination-btn';
        prevBtn.textContent = 'Anterior';
        prevBtn.disabled = current === 1;
        prevBtn.onclick = () => { currentPage = current - 1; renderAppointments(); };
        paginationContainer.appendChild(prevBtn);

        for (let i = 1; i <= totalPages; i++) {
            const btn = document.createElement('button');
            btn.className = `pagination-btn ${i === current ? 'active' : ''}`;
            btn.textContent = i;
            btn.onclick = () => { currentPage = i; renderAppointments(); };
            paginationContainer.appendChild(btn);
        }

        const nextBtn = document.createElement('button');
        nextBtn.className = 'pagination-btn';
        nextBtn.textContent = 'Siguiente';
        nextBtn.disabled = current === totalPages;
        nextBtn.onclick = () => { currentPage = current + 1; renderAppointments(); };
        paginationContainer.appendChild(nextBtn);
    }

    function renderAppointments() {
        const filtered = getFilteredMessages();
        const total = filtered.length;
        const start = (currentPage - 1) * ITEMS_PER_PAGE;
        const paged = filtered.slice(start, start + ITEMS_PER_PAGE);

        if (paged.length === 0) {
            appointmentsList.innerHTML = `
                <div class="empty-state">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                    <p>No se encontraron resultados</p>
                </div>
            `;
            paginationContainer.innerHTML = '';
            return;
        }

        appointmentsList.innerHTML = '';
        paged.forEach(app => {
            const statusClass = (app.estado || 'Pendiente').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
            const statusMap = { 'Pendiente': 'pendiente', 'Agendada': 'agendada', 'Cancelada': 'cancelada' };
            const cardStatus = statusMap[app.estado] || 'pendiente';

            let statusBadge = '<span class="badge badge-pending"><span class="badge-dot"></span>Pendiente</span>';
            if (app.estado === 'Agendada') statusBadge = '<span class="badge badge-success"><span class="badge-dot"></span>Agendada</span>';
            if (app.estado === 'Cancelada') statusBadge = '<span class="badge badge-cancelled"><span class="badge-dot"></span>Cancelada</span>';

            const emailDisplay = showPII ? escapeHTML(app.email) : maskEmail(app.email);
            const nameDisplay = showPII ? escapeHTML(app.nombre) : maskName(app.nombre);
            const nameClass = showPII ? '' : 'pi-hidden';
            const emailClass = showPII ? '' : 'pi-hidden';

            const shortMessage = app.mensaje ? (app.mensaje.length > 60 ? app.mensaje.substring(0, 60) + '...' : app.mensaje) : '';

            let actionsHTML = '';
            if (app.estado === 'Agendada') {
                actionsHTML = `
                    <span class="appointment-scheduled-info">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                        ${escapeHTML(app.fecha_cita)}
                    </span>
                `;
            } else if (app.estado !== 'Cancelada') {
                actionsHTML = `<button onclick="openScheduleModal(${app.id})" class="btn btn-primary btn-sm">Agendar</button>`;
            }

            let cardMeta = '';
            if (app.modalidad) {
                cardMeta = `<span class="appointment-modalidad">${app.modalidad === 'Virtual' ? '&#128187;' : '&#127970;'} ${escapeHTML(app.modalidad)}</span>`;
            }

            const card = document.createElement('div');
            card.className = `appointment-card status-${cardStatus}`;
            card.innerHTML = `
                <div class="appointment-date">
                    <div class="appointment-date-day">${getDayNum(app.fecha)}</div>
                    <div class="appointment-date-month">${getMonthName(app.fecha)}</div>
                    <div class="appointment-date-time">${formatTime(app.fecha)}</div>
                </div>
                <div class="appointment-info">
                    <div class="appointment-patient ${nameClass}">${nameDisplay}</div>
                    <div class="appointment-email ${emailClass}">${emailDisplay}</div>
                    ${shortMessage ? `<div class="appointment-reason" onclick="viewMessage(this)" data-msg="${escapeHTML(app.mensaje)}" data-sender="${escapeHTML(app.nombre)}" data-email="${escapeHTML(app.email)}" title="Haz clic para leer completo">${escapeHTML(shortMessage)}</div>` : ''}
                    <div class="appointment-meta">
                        ${statusBadge}
                        ${cardMeta}
                    </div>
                </div>
                <div class="appointment-actions">
                    ${actionsHTML}
                    ${app.estado !== 'Cancelada' && app.estado !== 'Agendada' ? `<button onclick="cancelAppointment(${app.id})" class="btn btn-outline btn-sm" title="Cancelar cita">Cancelar</button>` : ''}
                </div>
            `;
            appointmentsList.appendChild(card);
        });

        renderPagination(total, currentPage);
    }

    async function loadAppointments() {
        appointmentsList.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Cargando citas...</p></div>';
        paginationContainer.innerHTML = '';

        try {
            const res = await fetch('/api/messages');
            if (res.status === 401) { window.location.href = 'login.html'; return; }
            allMessages = await res.json();
            currentPage = 1;
            renderAppointments();
        } catch (error) {
            appointmentsList.innerHTML = '<div class="empty-state"><p>Error al cargar las citas</p></div>';
        }
    }

    searchInput.addEventListener('input', () => { currentPage = 1; renderAppointments(); });
    statusFilter.addEventListener('change', () => { currentPage = 1; renderAppointments(); });
    document.getElementById('refreshBtn').addEventListener('click', loadAppointments);

    // --- PII TOGGLE ---
    const togglePIIBtn = document.getElementById('togglePIIBtn');
    togglePIIBtn.addEventListener('click', () => {
        showPII = !showPII;
        const eyeOn = togglePIIBtn.querySelector('.icon-eye');
        const eyeOff = togglePIIBtn.querySelector('.icon-eye-off');
        if (showPII) {
            eyeOn.style.display = 'none';
            eyeOff.style.display = 'block';
        } else {
            eyeOn.style.display = 'block';
            eyeOff.style.display = 'none';
        }
        renderAppointments();
    });

    // --- VIEW MESSAGE ---
    window.viewMessage = function(element) {
        const msg = element.getAttribute('data-msg');
        const sender = element.getAttribute('data-sender');
        const email = element.getAttribute('data-email');
        document.getElementById('modalMessageSender').textContent = `De: ${sender} (${email})`;
        document.getElementById('modalMessageText').textContent = msg;
        document.getElementById('messageModal').classList.add('active');
    };

    document.getElementById('closeMsgModal').addEventListener('click', () => {
        document.getElementById('messageModal').classList.remove('active');
    });

    // --- SCHEDULE MODAL ---
    window.openScheduleModal = function(id) {
        document.getElementById('scheduleMsgId').value = id;
        document.getElementById('scheduleForm').reset();
        document.getElementById('scheduleModal').classList.add('active');
    };

    document.getElementById('closeScheduleModal').addEventListener('click', () => {
        document.getElementById('scheduleModal').classList.remove('active');
    });

    document.getElementById('scheduleForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('btnSubmitSchedule');
        btn.disabled = true;

        const rawDate = document.getElementById('fechaCita').value;
        const rawTime = document.getElementById('horaCita').value;
        const formattedDateTime = `${rawDate} a las ${rawTime}`;

        const data = {
            fecha_cita: formattedDateTime,
            modalidad: document.getElementById('modalidadCita').value,
            notas: document.getElementById('notasCita').value
        };

        const msgId = document.getElementById('scheduleMsgId').value;

        try {
            const res = await fetch(`/api/messages/${msgId}/schedule`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await res.json();

            if (res.ok) {
                showToast('Cita agendada y correo enviado exitosamente', 'success');
                document.getElementById('scheduleModal').classList.remove('active');
                loadAppointments();
            } else {
                showToast(result.error || 'Error al agendar', 'error');
            }
        } catch (e) {
            showToast('Error de conexion con el servidor', 'error');
        } finally {
            btn.disabled = false;
        }
    });

    // --- CANCEL APPOINTMENT ---
    window.cancelAppointment = async function(id) {
        const confirmed = await showConfirm('Cancelar Cita', 'Estas seguro de que deseas cancelar esta cita? Esta accion no se puede deshacer.');
        if (!confirmed) return;

        try {
            const res = await fetch(`/api/messages/${id}/cancel`, { method: 'POST' });
            const result = await res.json();
            if (res.ok) {
                showToast('Cita cancelada correctamente', 'success');
                loadAppointments();
            } else {
                showToast(result.error || 'Error al cancelar', 'error');
            }
        } catch (e) {
            showToast('Error de conexion', 'error');
        }
    };

    // --- USERS ---
    const usersList = document.getElementById('usersList');
    const searchUsersInput = document.getElementById('searchUsersInput');
    let allUsers = [];

    function renderUsers(filter = '') {
        const q = filter.toLowerCase().trim();
        const filtered = allUsers.filter(u => !q || u.username.toLowerCase().includes(q) || (u.full_name && u.full_name.toLowerCase().includes(q)));

        if (filtered.length === 0) {
            usersList.innerHTML = '<div class="empty-state"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg><p>No se encontraron usuarios</p></div>';
            return;
        }

        usersList.innerHTML = '';
        filtered.forEach(u => {
            const isMe = u.username === currentUser;
            const isAdmin = u.role === 'admin';
            const initial = (u.full_name || u.username).charAt(0).toUpperCase();
            const canDelete = !isMe && currentRole === 'admin' && !(isAdmin && allUsers.filter(x => x.role === 'admin').length <= 1);

            const card = document.createElement('div');
            card.className = 'user-card';
            card.innerHTML = `
                <div class="user-card-avatar">${escapeHTML(initial)}</div>
                <div class="user-card-info">
                    <div class="user-card-name">${escapeHTML(u.full_name || u.username)} ${isMe ? '<span style="color:var(--gray-400); font-size:0.8em; margin-left: 6px;">(Tu)</span>' : ''}</div>
                    <div class="user-card-username">@${escapeHTML(u.username)}</div>
                </div>
                <span class="user-card-role">${isAdmin ? 'Admin' : 'Viewer'}</span>
                <div class="user-card-actions">
                    <button onclick="deleteUser(${u.id})" class="btn btn-outline btn-sm" ${!canDelete ? 'disabled title="No se puede eliminar"' : ''} style="${canDelete ? 'color:var(--danger-500); border-color: var(--danger-200);' : ''}">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                        Eliminar
                    </button>
                </div>
            `;
            usersList.appendChild(card);
        });
    }

    async function loadUsers() {
        usersList.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Cargando usuarios...</p></div>';
        try {
            const res = await fetch('/api/users');
            if (res.status === 401) { window.location.href = 'login.html'; return; }
            allUsers = await res.json();
            renderUsers(searchUsersInput.value);
        } catch (error) {
            usersList.innerHTML = '<div class="empty-state"><p>Error al cargar usuarios</p></div>';
        }
    }

    searchUsersInput.addEventListener('input', () => renderUsers(searchUsersInput.value));
    document.getElementById('refreshUsersBtn').addEventListener('click', loadUsers);

    // --- CREATE USER ---
    document.getElementById('newUserBtn').addEventListener('click', () => {
        document.getElementById('createUserForm').reset();
        document.getElementById('userModal').classList.add('active');
    });

    document.getElementById('closeUserModal').addEventListener('click', () => {
        document.getElementById('userModal').classList.remove('active');
    });

    document.getElementById('createUserForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = {
            full_name: document.getElementById('newFullName').value,
            username: document.getElementById('newUsername').value,
            password: document.getElementById('newPassword').value,
            role: document.getElementById('newRole').value
        };

        try {
            const res = await fetch('/api/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await res.json();
            if (res.ok) {
                showToast('Usuario creado exitosamente', 'success');
                document.getElementById('userModal').classList.remove('active');
                loadUsers();
            } else {
                showToast(result.error || 'Error al crear usuario', 'error');
            }
        } catch (e) {
            showToast('Error de conexion', 'error');
        }
    });

    // --- DELETE USER ---
    window.deleteUser = async function(id) {
        const confirmed = await showConfirm('Eliminar Usuario', 'Esta seguro de que deseas eliminar este usuario? Esta accion no se puede deshacer.');
        if (!confirmed) return;

        try {
            const res = await fetch('/api/users/' + id, { method: 'DELETE' });
            const result = await res.json();
            if (res.ok) {
                showToast('Usuario eliminado', 'success');
                loadUsers();
            } else {
                showToast(result.error || 'Error al eliminar', 'error');
            }
        } catch (e) {
            showToast('Error de conexion', 'error');
        }
    };

    // --- PROFILE / ACCOUNT ---
    function openAccountModal() {
        document.getElementById('profileFullName').value = userData.full_name || '';
        document.getElementById('profileEmail').value = userData.email || '';
        document.getElementById('accountModal').classList.add('active');
    }

    document.getElementById('closeAccountModal').addEventListener('click', () => {
        document.getElementById('accountModal').classList.remove('active');
    });

    document.getElementById('profileForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = {
            full_name: document.getElementById('profileFullName').value,
            email: document.getElementById('profileEmail').value
        };

        try {
            const res = await fetch('/api/profile', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await res.json();
            if (res.ok) {
                userData.full_name = data.full_name;
                userData.email = data.email;
                const displayName = data.full_name || currentUser;
                const initial = displayName.charAt(0).toUpperCase();
                document.getElementById('adminUsername').textContent = displayName;
                document.getElementById('topbarAvatar').textContent = initial;
                document.getElementById('sidebarAvatar').textContent = initial;
                document.getElementById('sidebarUserName').textContent = displayName;
                showToast('Perfil actualizado correctamente', 'success');
            } else {
                showToast(result.error || 'Error al actualizar', 'error');
            }
        } catch (e) {
            showToast('Error de conexion', 'error');
        }
    });

    document.getElementById('passwordForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const newPass = document.getElementById('newPasswordInput').value;
        const confirmPass = document.getElementById('confirmPassword').value;

        if (newPass !== confirmPass) {
            showToast('Las contrasenas no coinciden', 'error');
            return;
        }

        const data = {
            current_password: document.getElementById('currentPassword').value,
            new_password: newPass
        };

        try {
            const res = await fetch('/api/profile/password', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await res.json();
            if (res.ok) {
                showToast('Contrasena actualizada correctamente', 'success');
                document.getElementById('passwordForm').reset();
            } else {
                showToast(result.error || 'Error al cambiar contrasena', 'error');
            }
        } catch (e) {
            showToast('Error de conexion', 'error');
        }
    });

    // --- CLOSE MODALS ON OVERLAY CLICK ---
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) overlay.classList.remove('active');
        });
    });

    // --- KEYBOARD SHORTCUT ---
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active'));
        }
    });

    // --- INIT ---
    loadDashboard();
});
