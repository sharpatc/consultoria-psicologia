document.addEventListener('DOMContentLoaded', async () => {
    // 1. Verificar Autenticación
    let currentUser = '';
    try {
        const authRes = await fetch('/api/check-auth');
        const authData = await authRes.json();
        if (!authData.authenticated) {
            window.location.href = 'login.html';
            return;
        }
        currentUser = authData.username;
        const usernameSpan = document.getElementById('adminUsername');
        if (usernameSpan) usernameSpan.textContent = 'Hola, ' + authData.username;
    } catch (e) {
        window.location.href = 'login.html';
        return;
    }

    // 2. Setup Logout
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            await fetch('/api/logout', { method: 'POST' });
            window.location.href = 'login.html';
        });
    }

    // 3. Navegación entre paneles
    const navMessages = document.getElementById('navMessages');
    const navUsers = document.getElementById('navUsers');
    const panelMessages = document.getElementById('panelMessages');
    const panelUsers = document.getElementById('panelUsers');
    const pageTitle = document.getElementById('pageTitle');

    navMessages.addEventListener('click', (e) => {
        e.preventDefault();
        navMessages.classList.add('active');
        navUsers.classList.remove('active');
        panelMessages.style.display = 'block';
        panelUsers.style.display = 'none';
        pageTitle.textContent = 'Gestión de Citas y Agendas';
        loadAppointments();
    });

    navUsers.addEventListener('click', (e) => {
        e.preventDefault();
        navUsers.classList.add('active');
        navMessages.classList.remove('active');
        panelUsers.style.display = 'block';
        panelMessages.style.display = 'none';
        pageTitle.textContent = 'Gestión de Usuarios';
        loadUsers();
    });

    // 4. Lógica de Mensajes
    const tableBody = document.querySelector('#appointmentsTable tbody');
    const refreshBtn = document.getElementById('refreshBtn');
    
    const msgModal = document.getElementById('messageModal');
    const closeMsgModal = document.getElementById('closeMsgModal');
    const modalMessageText = document.getElementById('modalMessageText');

    async function loadAppointments() {
        tableBody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 30px;">Cargando mensajes...</td></tr>';
        
        try {
            const res = await fetch('/api/messages');
            if (res.status === 401) { window.location.href = 'login.html'; return; }
            const messages = await res.json();

            if (messages.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 30px; color: #718096;">No hay mensajes registrados.</td></tr>';
                return;
            }

            tableBody.innerHTML = '';
            messages.forEach(app => {
                const tr = document.createElement('tr');
                
                const dateObj = new Date(app.fecha);
                const fecha = dateObj.toLocaleDateString();
                const hora = dateObj.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                
                let actionHTML = '-';
                let statusBadgeHTML = '<span class="badge badge-pending">Pendiente</span>';
                
                if (app.estado === 'Agendada') {
                    statusBadgeHTML = '<span class="badge badge-success">Agendada</span>';
                    actionHTML = `<div style="font-size:0.85rem; color:var(--primary-color);"><strong>${escapeHTML(app.fecha_cita)}</strong><br><span style="color:var(--text-muted)">${escapeHTML(app.modalidad)}</span></div>`;
                } else {
                    actionHTML = `<button onclick="openScheduleModal(${app.id})" class="btn btn-primary" style="padding: 6px 12px; font-size: 0.8rem;">🗓️ Agendar</button>`;
                }
                const shortMessage = app.mensaje ? (app.mensaje.length > 40 ? app.mensaje.substring(0, 40) + '...' : app.mensaje) : '';

                tr.innerHTML = `
                    <td>
                        <div style="font-size:0.9rem">${fecha}</div>
                        <div style="font-size:0.8rem; color:var(--text-muted); margin-top: 4px;">${hora}</div>
                    </td>
                    <td><span class="patient-name">${escapeHTML(app.nombre)}</span></td>
                    <td><a href="mailto:${escapeHTML(app.email)}" style="color:var(--text-muted); text-decoration:none;">✉️ ${escapeHTML(app.email)}</a></td>
                    <td><span class="td-msg" onclick="viewMessage(this)" data-msg="${escapeHTML(app.mensaje)}" title="Haz clic para leer">${escapeHTML(shortMessage)}</span></td>
                    <td>${statusBadgeHTML}</td>
                    <td>${actionHTML}</td>
                `;
                tableBody.appendChild(tr);
            });
        } catch (error) {
            tableBody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 30px; color: #e53e3e;">Error al cargar.</td></tr>';
        }
    }

    if (refreshBtn) refreshBtn.addEventListener('click', loadAppointments);

    window.viewMessage = function(element) {
        modalMessageText.textContent = element.getAttribute('data-msg');
        msgModal.style.display = 'block';
    };

    if (closeMsgModal) closeMsgModal.onclick = () => msgModal.style.display = 'none';

    // 4.5 Lógica de Agendamiento
    const scheduleModal = document.getElementById('scheduleModal');
    const closeScheduleModal = document.getElementById('closeScheduleModal');
    const scheduleForm = document.getElementById('scheduleForm');
    const scheduleMsgId = document.getElementById('scheduleMsgId');
    const btnSubmitSchedule = document.getElementById('btnSubmitSchedule');

    window.openScheduleModal = function(id) {
        scheduleMsgId.value = id;
        scheduleModal.style.display = 'block';
        scheduleForm.reset();
    };

    if (closeScheduleModal) closeScheduleModal.onclick = () => scheduleModal.style.display = 'none';

    scheduleForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        btnSubmitSchedule.disabled = true;
        btnSubmitSchedule.textContent = 'Enviando...';

        const rawDate = scheduleForm.fecha_cita.value;
        const rawTime = scheduleForm.hora_cita.value;
        const formattedDateTime = `${rawDate} a las ${rawTime}`;
        
        const data = {
            fecha_cita: formattedDateTime,
            modalidad: scheduleForm.modalidad.value
        };
        
        const msgId = scheduleMsgId.value;

        try {
            const res = await fetch(`/api/messages/${msgId}/schedule`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await res.json();
            
            if (res.ok) {
                alert('Cita agendada y correo enviado exitosamente.');
                scheduleModal.style.display = 'none';
                loadAppointments();
            } else {
                alert('Error: ' + result.error);
            }
        } catch (e) {
            alert('Error de conexión con el servidor al agendar cita.');
        } finally {
            btnSubmitSchedule.disabled = false;
            btnSubmitSchedule.textContent = '📅 Agendar y Enviar Correo';
        }
    });

    // 5. Lógica de Usuarios
    const usersTableBody = document.querySelector('#usersTable tbody');
    const refreshUsersBtn = document.getElementById('refreshUsersBtn');
    const newUserBtn = document.getElementById('newUserBtn');
    
    const userModal = document.getElementById('userModal');
    const closeUserModal = document.getElementById('closeUserModal');
    const createUserForm = document.getElementById('createUserForm');

    async function loadUsers() {
        usersTableBody.innerHTML = '<tr><td colspan="3" style="text-align:center; padding: 30px;">Cargando usuarios...</td></tr>';
        try {
            const res = await fetch('/api/users');
            if (res.status === 401) { window.location.href = 'login.html'; return; }
            const users = await res.json();

            usersTableBody.innerHTML = '';
            users.forEach(u => {
                const tr = document.createElement('tr');
                const isMe = u.username === currentUser;
                tr.innerHTML = `
                    <td># ${u.id}</td>
                    <td><strong>${escapeHTML(u.username)}</strong> ${isMe ? '<span style="color:var(--text-muted); font-size:0.85em; margin-left: 8px;">(Tú)</span>' : ''}</td>
                    <td>
                        <button onclick="deleteUser(${u.id})" class="btn btn-danger" ${isMe ? 'disabled' : ''}>✕ Eliminar</button>
                    </td>
                `;
                usersTableBody.appendChild(tr);
            });
        } catch (error) {
            usersTableBody.innerHTML = '<tr><td colspan="3" style="text-align:center; padding: 30px; color: #e53e3e;">Error al cargar.</td></tr>';
        }
    }

    if (refreshUsersBtn) refreshUsersBtn.addEventListener('click', loadUsers);
    
    if (newUserBtn) {
        newUserBtn.addEventListener('click', () => {
            userModal.style.display = 'block';
            createUserForm.reset();
        });
    }

    if (closeUserModal) closeUserModal.onclick = () => userModal.style.display = 'none';

    createUserForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = {
            username: createUserForm.username.value,
            password: createUserForm.password.value
        };
        try {
            const res = await fetch('/api/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await res.json();
            if (res.ok) {
                alert('Usuario creado exitosamente');
                userModal.style.display = 'none';
                loadUsers();
            } else {
                alert('Error: ' + result.error);
            }
        } catch (e) {
            alert('Error de conexión');
        }
    });

    window.deleteUser = async function(id) {
        if (!confirm('¿Seguro que deseas eliminar a este usuario?')) return;
        try {
            const res = await fetch('/api/users/' + id, { method: 'DELETE' });
            const result = await res.json();
            if (res.ok) {
                loadUsers();
            } else {
                alert('Error: ' + result.error);
            }
        } catch (e) {
            alert('Error al conectar con servidor');
        }
    };

    // Close Modals on outside click
    window.onclick = function(event) {
        if (event.target == msgModal) msgModal.style.display = 'none';
        if (event.target == userModal) userModal.style.display = 'none';
        if (event.target == scheduleModal) scheduleModal.style.display = 'none';
    }

    // Inicializar cargando mensajes
    loadAppointments();
});

function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, 
        tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag])
    );
}
