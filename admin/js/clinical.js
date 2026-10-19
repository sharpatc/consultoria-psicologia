document.addEventListener('DOMContentLoaded', async () => {
    const evaluationGroups = [
        {
            title: 'I. Datos generales del paciente',
            fields: [
                ['nombre', 'Nombre completo', 'text', true],
                ['edad', 'Edad', 'text'],
                ['fecha_nacimiento', 'Fecha de nacimiento', 'date'],
                ['sexo', 'Sexo', 'select', false, ['Femenino', 'Masculino', 'Otro', 'Prefiere no indicar']],
                ['escuela', 'Escuela', 'text'],
                ['grado', 'Grado', 'text'],
                ['direccion', 'Direccion', 'text']
            ]
        },
        {
            title: 'II. Datos del padre, madre o tutor',
            fields: [
                ['padre', 'Nombre del padre', 'text'],
                ['madre', 'Nombre de la madre', 'text'],
                ['tutor', 'Nombre del tutor', 'text'],
                ['telefonos', 'Telefonos de contacto', 'text']
            ]
        },
        {
            title: 'III. Motivo de consulta',
            fields: [['motivo_consulta', 'Motivo de consulta', 'textarea', true]]
        },
        {
            title: 'IV. Historia del problema',
            fields: [['historia_problema', 'Historia del problema', 'textarea']]
        },
        {
            title: 'V. Antecedentes prenatales',
            fields: [['antecedentes_prenatales', 'Antecedentes prenatales', 'textarea']]
        },
        {
            title: 'VI. Antecedentes del parto',
            fields: [['antecedentes_parto', 'Antecedentes del parto', 'textarea']]
        },
        {
            title: 'VII. Desarrollo psicomotor',
            fields: [
                ['sostuvo_cabeza', 'Sostuvo la cabeza (edad o detalle)', 'text'],
                ['se_sento', 'Se sento (edad o detalle)', 'text'],
                ['gateo', 'Gateo (edad o detalle)', 'text'],
                ['camino', 'Camino (edad o detalle)', 'text'],
                ['primeras_palabras', 'Primeras palabras', 'text'],
                ['control_esfinteres', 'Control de esfinteres', 'text']
            ]
        },
        {
            title: 'VIII. Antecedentes medicos',
            fields: [['antecedentes_medicos', 'Antecedentes medicos', 'textarea']]
        },
        {
            title: 'IX. Antecedentes familiares',
            fields: [['antecedentes_familiares', 'Antecedentes familiares', 'textarea']]
        },
        {
            title: 'X. Dinamica familiar',
            fields: [['dinamica_familiar', 'Dinamica familiar', 'textarea']]
        },
        {
            title: 'XI. Area escolar',
            fields: [['area_escolar', 'Area escolar', 'textarea']]
        },
        {
            title: 'XII. Area emocional',
            fields: [['area_emocional', 'Ansiedad, tristeza, irritabilidad, agresividad, impulsividad, autoestima, TDAH u otros', 'textarea']]
        },
        {
            title: 'XIII. Area conductual',
            fields: [['area_conductual', 'Area conductual', 'textarea']]
        },
        {
            title: 'XIV. Habitos',
            fields: [
                ['sueno', 'Sueno', 'text'],
                ['alimentacion', 'Alimentacion', 'text'],
                ['pantallas', 'Uso de pantallas', 'text'],
                ['juego', 'Juego', 'text']
            ]
        },
        {
            title: 'XV. Observacion clinica',
            fields: [['observacion_clinica', 'Observacion clinica', 'textarea']]
        },
        {
            title: 'XVI. Fortalezas',
            fields: [['fortalezas', 'Fortalezas y recursos', 'textarea']]
        },
        {
            title: 'XVII. Impresion clinica',
            fields: [['impresion_clinica', 'Impresion clinica', 'textarea']]
        },
        {
            title: 'XVIII. Objetivos terapeuticos',
            fields: [['objetivos_terapeuticos', 'Objetivos terapeuticos', 'textarea']]
        },
        {
            title: 'XIX. Plan de intervencion',
            fields: [['plan_intervencion', 'Plan de intervencion', 'textarea']]
        },
        {
            title: 'XX. Consentimiento',
            fields: [
                ['consentimiento_tutor', 'Nombre / constancia de consentimiento del padre, madre o tutor', 'text'],
                ['firma_psicologa', 'Profesional responsable', 'text']
            ]
        }
    ];

    const fieldLabels = new Map(
        evaluationGroups.flatMap(group => group.fields.map(field => [field[0], field[1]]))
    );
    const records = document.getElementById('clinicalRecords');
    const search = document.getElementById('clinicalSearch');
    const evaluationForm = document.getElementById('evaluationForm');
    const evaluationModal = document.getElementById('evaluationModal');
    const detailModal = document.getElementById('clinicalDetailModal');
    const detailBody = document.getElementById('clinicalDetailBody');
    const sessionModal = document.getElementById('sessionModal');
    const sessionForm = document.getElementById('clinicalSessionForm');
    let evaluationId = null;
    let sessionId = null;
    let currentEvaluation = null;
    let allRecords = [];

    const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, char => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[char]);

    function notify(message, type = 'info') {
        if (typeof window.showToast === 'function') window.showToast(message, type);
        else window.alert(message);
    }

    async function requestJSON(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            headers: {
                ...(options.body ? { 'Content-Type': 'application/json' } : {}),
                ...options.headers
            }
        });
        if (response.status === 401) {
            window.location.href = '/admin/login.html';
            throw new Error('La sesion ha expirado. Inicia sesion nuevamente.');
        }
        const result = response.status === 204 ? {} : await response.json();
        if (!response.ok) throw new Error(result.error || 'No se pudo completar la solicitud.');
        return result;
    }

    function localDateValue() {
        const today = new Date();
        return [
            today.getFullYear(),
            String(today.getMonth() + 1).padStart(2, '0'),
            String(today.getDate()).padStart(2, '0')
        ].join('-');
    }

    function renderEvaluationForm() {
        document.getElementById('clinicalEvaluationFields').innerHTML = evaluationGroups.map(group => `
            <fieldset class="clinical-fieldset">
                <legend>${escapeHTML(group.title)}</legend>
                <div class="clinical-fields-grid">
                    ${group.fields.map(([name, label, type, required, options]) => {
                        const control = type === 'textarea'
                            ? `<textarea id="clinical-${name}" name="${name}" maxlength="4000"${required ? ' required' : ''}></textarea>`
                            : type === 'select'
                                ? `<select id="clinical-${name}" name="${name}"><option value="">Seleccionar</option>${options.map(option => `<option value="${escapeHTML(option)}">${escapeHTML(option)}</option>`).join('')}</select>`
                                : `<input type="${type}" id="clinical-${name}" name="${name}" maxlength="${name === 'motivo_consulta' ? 4000 : 500}"${required ? ' required' : ''}>`;
                        return `<div class="form-group ${type === 'textarea' ? 'clinical-field-wide' : ''}">
                            <label for="clinical-${name}">${escapeHTML(label)}${required ? ' *' : ''}</label>
                            ${control}
                        </div>`;
                    }).join('')}
                </div>
            </fieldset>
        `).join('');
    }

    function renderRecords() {
        const query = (search.value || '').trim().toLocaleLowerCase();
        const filtered = allRecords.filter(item => item.patient_name.toLocaleLowerCase().includes(query));
        if (!filtered.length) {
            records.innerHTML = `<div class="empty-state"><p>${query ? 'No se encontraron pacientes' : 'Aun no hay evaluaciones registradas'}</p></div>`;
            return;
        }
        records.innerHTML = filtered.map(item => `
            <article class="clinical-record">
                <div class="clinical-record-info">
                    <h3>${escapeHTML(item.patient_name)}</h3>
                    <p>${Number(item.session_count)} atencion(es) registradas</p>
                    <p>${item.last_session ? `Ultima atencion: ${escapeHTML(item.last_session)}` : 'Sin atenciones registradas'}</p>
                </div>
                <div class="clinical-record-actions">
                    <button class="btn btn-outline btn-sm" data-action="view" data-id="${item.id}">Ver ficha y atenciones</button>
                    <button class="btn btn-primary btn-sm" data-action="session" data-id="${item.id}">Registrar atencion</button>
                </div>
            </article>
        `).join('');
    }

    async function loadRecords() {
        records.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Cargando evaluaciones...</p></div>';
        try {
            allRecords = await requestJSON('/api/clinical/evaluations');
            renderRecords();
        } catch (error) {
            records.innerHTML = `<div class="empty-state"><p>${escapeHTML(error.message)}</p><button class="btn btn-outline btn-sm" id="retryClinicalLoad">Intentar de nuevo</button></div>`;
            document.getElementById('retryClinicalLoad')?.addEventListener('click', loadRecords);
        }
    }

    function closeModal(modal) {
        modal.classList.remove('active');
    }

    async function openEvaluation(id = null) {
        evaluationForm.reset();
        evaluationId = id;
        document.getElementById('evaluationModalTitle').textContent = id
            ? 'Editar evaluacion psicologica'
            : 'Nueva evaluacion psicologica infantil y adolescente';
        document.getElementById('saveEvaluationBtn').textContent = id
            ? 'Guardar cambios'
            : 'Guardar evaluacion';
        if (id) {
            try {
                const evaluation = await requestJSON(`/api/clinical/evaluations/${id}`);
                Object.entries(evaluation.data).forEach(([name, value]) => {
                    const field = evaluationForm.elements.namedItem(name);
                    if (field) field.value = value;
                });
            } catch (error) {
                notify(error.message, 'error');
                return;
            }
        }
        evaluationModal.classList.add('active');
    }

    function formatSession(session) {
        return `
            <article class="clinical-session">
                <div class="clinical-session-heading">
                    <strong>${escapeHTML(session.session_date)}</strong>
                    <span>${escapeHTML(session.attendance)} · ${escapeHTML(session.modality)} · ${Number(session.duration_minutes)} min</span>
                </div>
                <p><b>Tema:</b> ${escapeHTML(session.focus)}</p>
                ${session.interventions ? `<p><b>Intervenciones:</b> ${escapeHTML(session.interventions)}</p>` : ''}
                ${session.progress ? `<p><b>Progreso:</b> ${escapeHTML(session.progress)}</p>` : ''}
                ${session.agreements ? `<p><b>Acuerdos:</b> ${escapeHTML(session.agreements)}</p>` : ''}
                ${session.next_session ? `<p><b>Seguimiento:</b> ${escapeHTML(session.next_session)}</p>` : ''}
                <div class="clinical-record-actions">
                    <button class="btn btn-outline btn-sm" data-action="edit-session" data-id="${session.id}">Editar atencion</button>
                    <button class="btn btn-outline btn-sm clinical-delete-btn" data-action="delete-session" data-id="${session.id}">Eliminar</button>
                </div>
            </article>
        `;
    }

    async function showEvaluation(id) {
        try {
            currentEvaluation = await requestJSON(`/api/clinical/evaluations/${id}`);
            const sections = evaluationGroups.map(group => {
                const filled = group.fields
                    .filter(([name]) => currentEvaluation.data[name])
                    .map(([name]) => `<p><b>${escapeHTML(fieldLabels.get(name))}:</b> ${escapeHTML(currentEvaluation.data[name])}</p>`)
                    .join('');
                return filled ? `<section class="clinical-detail-section"><h3>${escapeHTML(group.title)}</h3>${filled}</section>` : '';
            }).join('');
            detailBody.innerHTML = `
                <div class="clinical-detail-actions">
                    <button class="btn btn-outline btn-sm" data-action="edit-evaluation">Editar ficha</button>
                    <button class="btn btn-primary btn-sm" data-action="session">Registrar atencion</button>
                    <button class="btn btn-outline btn-sm clinical-delete-btn" data-action="delete-evaluation">Eliminar ficha</button>
                </div>
                ${sections}
                <section class="clinical-detail-section">
                    <h3>Registro de atenciones (${currentEvaluation.sessions.length})</h3>
                    ${currentEvaluation.sessions.length
                        ? currentEvaluation.sessions.map(formatSession).join('')
                        : '<p>Aun no hay atenciones registradas.</p>'}
                </section>
            `;
            document.getElementById('clinicalDetailTitle').textContent = currentEvaluation.patient_name;
            detailModal.classList.add('active');
        } catch (error) {
            notify(error.message, 'error');
        }
    }

    function openSession(session = null) {
        sessionForm.reset();
        sessionId = session ? session.id : null;
        document.getElementById('sessionModalTitle').textContent = session
            ? 'Editar atencion'
            : `Registrar atencion: ${currentEvaluation.patient_name}`;
        document.getElementById('clinicalSessionDate').value = session?.session_date || localDateValue();
        document.getElementById('clinicalSessionDuration').value = session?.duration_minutes || 50;
        document.getElementById('clinicalSessionModality').value = session?.modality || 'Presencial';
        document.getElementById('clinicalSessionAttendance').value = session?.attendance || 'Atendida';
        document.getElementById('clinicalSessionFocus').value = session?.focus || '';
        document.getElementById('clinicalSessionInterventions').value = session?.interventions || '';
        document.getElementById('clinicalSessionProgress').value = session?.progress || '';
        document.getElementById('clinicalSessionAgreements').value = session?.agreements || '';
        document.getElementById('clinicalSessionNext').value = session?.next_session || '';
        sessionModal.classList.add('active');
    }

    document.getElementById('navClinical').addEventListener('click', loadRecords);
    document.getElementById('refreshClinicalBtn').addEventListener('click', loadRecords);
    document.getElementById('newEvaluationBtn').addEventListener('click', () => openEvaluation());
    search.addEventListener('input', renderRecords);
    records.addEventListener('click', async event => {
        const button = event.target.closest('[data-action]');
        if (!button) return;
        const id = Number(button.dataset.id);
        if (button.dataset.action === 'view') await showEvaluation(id);
        if (button.dataset.action === 'session') {
            try {
                currentEvaluation = await requestJSON(`/api/clinical/evaluations/${id}`);
                openSession();
            } catch (error) {
                notify(error.message, 'error');
            }
        }
    });

    evaluationForm.addEventListener('submit', async event => {
        event.preventDefault();
        const data = Object.fromEntries(new FormData(evaluationForm));
        const button = document.getElementById('saveEvaluationBtn');
        button.disabled = true;
        try {
            await requestJSON(
                evaluationId ? `/api/clinical/evaluations/${evaluationId}` : '/api/clinical/evaluations',
                { method: evaluationId ? 'PUT' : 'POST', body: JSON.stringify(data) }
            );
            closeModal(evaluationModal);
            notify('Evaluacion guardada correctamente.', 'success');
            await loadRecords();
            if (detailModal.classList.contains('active') && evaluationId) await showEvaluation(evaluationId);
        } catch (error) {
            notify(error.message, 'error');
        } finally {
            button.disabled = false;
        }
    });

    sessionForm.addEventListener('submit', async event => {
        event.preventDefault();
        const data = Object.fromEntries(new FormData(sessionForm));
        data.duration_minutes = Number(data.duration_minutes);
        const button = sessionForm.querySelector('button[type="submit"]');
        button.disabled = true;
        try {
            await requestJSON(
                sessionId ? `/api/clinical/sessions/${sessionId}` : `/api/clinical/evaluations/${currentEvaluation.id}/sessions`,
                { method: sessionId ? 'PUT' : 'POST', body: JSON.stringify(data) }
            );
            closeModal(sessionModal);
            notify('Atencion guardada correctamente.', 'success');
            await loadRecords();
            await showEvaluation(currentEvaluation.id);
        } catch (error) {
            notify(error.message, 'error');
        } finally {
            button.disabled = false;
        }
    });

    detailBody.addEventListener('click', async event => {
        const button = event.target.closest('[data-action]');
        if (!button || !currentEvaluation) return;
        const action = button.dataset.action;
        if (action === 'edit-evaluation') await openEvaluation(currentEvaluation.id);
        if (action === 'session') openSession();
        if (action === 'edit-session') {
            const session = currentEvaluation.sessions.find(item => item.id === Number(button.dataset.id));
            if (session) openSession(session);
        }
        if (action === 'delete-session' && window.confirm('Eliminar esta atencion?')) {
            try {
                await requestJSON(`/api/clinical/sessions/${button.dataset.id}`, { method: 'DELETE' });
                notify('Atencion eliminada.', 'success');
                await loadRecords();
                await showEvaluation(currentEvaluation.id);
            } catch (error) {
                notify(error.message, 'error');
            }
        }
        if (action === 'delete-evaluation' && window.confirm('Eliminar la ficha y todo su historial de atenciones? Esta accion no se puede deshacer.')) {
            try {
                await requestJSON(`/api/clinical/evaluations/${currentEvaluation.id}`, { method: 'DELETE' });
                closeModal(detailModal);
                notify('Ficha e historial eliminados.', 'success');
                await loadRecords();
            } catch (error) {
                notify(error.message, 'error');
            }
        }
    });

    document.getElementById('closeEvaluationModal').addEventListener('click', () => closeModal(evaluationModal));
    document.getElementById('cancelEvaluationBtn').addEventListener('click', () => closeModal(evaluationModal));
    document.getElementById('closeClinicalDetail').addEventListener('click', () => closeModal(detailModal));
    document.getElementById('closeSessionModal').addEventListener('click', () => closeModal(sessionModal));
    document.getElementById('cancelSessionBtn').addEventListener('click', () => closeModal(sessionModal));
    [evaluationModal, detailModal, sessionModal].forEach(modal => {
        modal.addEventListener('click', event => {
            if (event.target === modal) closeModal(modal);
        });
    });

    renderEvaluationForm();
});
