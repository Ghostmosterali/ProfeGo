// ===== SCRIPT PARA MENU.HTML - VERSIÓN CON GENERACIÓN DE PLANES IA =====

// ===== ELEMENTOS DEL DOM =====
const logoutBtn = document.getElementById('logout-btn');
const userInfo = document.getElementById('user-info');
const fileInput = document.getElementById('file-input');
const filesGallery = document.getElementById('files-gallery');

const navButtons = {
    inicio: document.getElementById('nav-inicio'),
    archivos: document.getElementById('nav-archivos'),
    consulta: document.getElementById('nav-consulta'),
    acerca: document.getElementById('nav-acerca')
};

const contentSections = {
    inicio: document.getElementById('inicio-content'),
    archivos: document.getElementById('archivos-content'),
    consulta: document.getElementById('consulta-content'),
    acerca: document.getElementById('acerca-content')
};

const confirmModal = document.getElementById('confirm-modal');

// Modal Vista Previa
const previewModal = document.getElementById('preview-modal');
const closePreviewModal = document.getElementById('close-preview-modal');
const previewContainer = document.getElementById('preview-container');
const previewFilename = document.getElementById('preview-filename');
const downloadPreviewBtn = document.getElementById('download-preview-btn');

let currentPreviewFile = null;

// NUEVO: Elementos para generación de planes
const generatePlanBtn = document.getElementById('generate-plan-btn');
const generatePlanModal = document.getElementById('generate-plan-modal');
const closeGeneratePlanModal = document.getElementById('close-generate-plan-modal');
const cancelGeneratePlanBtn = document.getElementById('cancel-generate-plan-btn');
const processPlanBtn = document.getElementById('process-plan-btn');
const planFileInput = document.getElementById('plan-file-input');
const diagnosticoFileInput = document.getElementById('diagnostico-file-input');
const planFileSelected = document.getElementById('plan-file-selected');
const diagnosticoFileSelected = document.getElementById('diagnostico-file-selected');
const planesList = document.getElementById('planes-list');
const consultaStats = document.getElementById('consulta-stats');

// Modal detalle de plan
const planDetailModal = document.getElementById('plan-detail-modal');
const closePlanDetailModal = document.getElementById('close-plan-detail-modal');
const planDetailTitle = document.getElementById('plan-detail-title');
const planDetailContent = document.getElementById('plan-detail-content');

// Variables globales
let planesGenerados = [];
let currentPage = 1;
const itemsPerPage = 5;

// ===== VERIFICAR AUTENTICACIÓN AL CARGAR =====
document.addEventListener('DOMContentLoaded', function() {
    if (!loadSession()) {
        window.location.href = 'login.html';
        return;
    }
    
    userInfo.textContent = `👋 Hola, ${currentUser}`;
    
    switchToSection('inicio');
    setupEventListeners();
    loadPlanes();
});

// ===== NAVEGACIÓN =====
function switchToSection(sectionName) {
    Object.keys(navButtons).forEach(key => {
        navButtons[key].classList.toggle('active', key === sectionName);
    });
    
    Object.keys(contentSections).forEach(key => {
        contentSections[key].classList.toggle('active', key === sectionName);
        contentSections[key].classList.toggle('hidden', key !== sectionName);
    });
    
    if (sectionName === 'archivos' && currentToken) {
        loadFiles();
    }
    
    if (sectionName === 'consulta') {
        loadPlanes();
    }
}

// ===== GESTIÓN DE ARCHIVOS =====
async function uploadFiles(files) {
    try {
        showLoading('Subiendo y procesando archivos...');
        
        if (!currentToken) {
            throw new Error('No hay sesión activa. Por favor inicia sesión.');
        }
        
        const formData = new FormData();
        Array.from(files).forEach(file => {
            formData.append('files', file);
        });
        
        const response = await fetch(`${API_BASE}/files/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${currentToken}`
            },
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error subiendo archivos');
        }
        
        const result = await response.json();
        
        let message = `Archivos subidos: ${result.files_uploaded}`;
        if (result.files_processed > 0) {
            message += `\nArchivos procesados: ${result.files_processed}`;
        }
        
        showMessage(message, 'success');
        await loadFiles();
        
    } catch (error) {
        showMessage(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function loadFiles() {
    try {
        if (!currentToken) {
            filesGallery.innerHTML = `
                <div class="empty-state">
                    <h3>Inicia sesión para ver tus archivos</h3>
                </div>
            `;
            return;
        }
        
        const files = await apiRequest('/files/list');
        displayFiles(files);
    } catch (error) {
        console.error('Error cargando archivos:', error);
        filesGallery.innerHTML = `
            <div class="empty-state">
                <h3>Error cargando archivos</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

function displayFiles(files) {
    filesGallery.innerHTML = '';
    
    if (files.length === 0) {
        filesGallery.innerHTML = `
            <div class="empty-state">
                <h3>No hay archivos aún</h3>
                <p>Usa el botón 'Subir archivos adicionales' para agregar documentos</p>
            </div>
        `;
        return;
    }
    
    const originalFiles = files.filter(file => file.category === 'original');
    const processedFiles = files.filter(file => file.category === 'procesado' && !file.name.startsWith('plan_'));
    
    if (originalFiles.length > 0) {
        const originalSection = document.createElement('div');
        originalSection.innerHTML = `
            <div class="file-section-title">ARCHIVOS ORIGINALES (${originalFiles.length})</div>
        `;
        filesGallery.appendChild(originalSection);
        
        originalFiles.forEach(file => {
            filesGallery.appendChild(createFileCard(file));
        });
    }
    
    if (processedFiles.length > 0) {
        const processedSection = document.createElement('div');
        processedSection.innerHTML = `
            <div class="file-section-title procesados">ARCHIVOS PROCESADOS (.txt) (${processedFiles.length})</div>
        `;
        filesGallery.appendChild(processedSection);
        
        processedFiles.forEach(file => {
            filesGallery.appendChild(createFileCard(file));
        });
    }
}

function createFileCard(file) {
    const card = document.createElement('div');
    card.className = `file-card ${file.category}`;
    
    let icon = '📎';
    if (file.category === 'procesado') {
        icon = '📄';
    } else {
        const fileType = file.type.toLowerCase();
        if (fileType.includes('pdf')) icon = '📄';
        else if (fileType.includes('imagen')) icon = '🖼️';
        else if (fileType.includes('word')) icon = '📘';
        else if (fileType.includes('excel')) icon = '📊';
    }
    
    const escapedName = file.name.replace(/'/g, "\\'");
    
    card.innerHTML = `
        <div class="file-info">
            <div class="file-name">
                <span class="file-icon">${icon}</span>
                <span>${file.name}</span>
            </div>
            <div class="file-details">
                <span>Tipo: ${file.type}</span>
                <span>Tamaño: ${file.size}</span>
            </div>
        </div>
        <div class="file-actions">
            <button class="preview-btn" onclick="openFilePreview('${file.category}', '${escapedName}')" title="Vista previa">
                👁️
            </button>
            <button class="download-btn" onclick="downloadFileAction('${file.category}', '${escapedName}')" title="Descargar">
                📥
            </button>
            <button class="delete-btn" onclick="confirmDeleteFile('${file.category}', '${escapedName}')" title="Eliminar">
                🗑️
            </button>
        </div>
    `;
    
    return card;
}

async function deleteFile(category, filename) {
    try {
        showLoading('Eliminando archivo...');
        
        await apiRequest(`/files/delete/${category}/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        
        showMessage(`Archivo '${filename}' eliminado correctamente`, 'success');
        await loadFiles();
        
    } catch (error) {
        showMessage(error.message, 'error');
    } finally {
        hideLoading();
    }
}

function confirmDeleteFile(category, filename) {
    showModal(
        `¿Estás seguro de que quieres eliminar "${filename}"?`,
        () => deleteFile(category, filename)
    );
}

// ===== GENERACIÓN DE PLANES CON IA =====

function openGeneratePlanModal() {
    generatePlanModal.classList.add('active');
    resetGeneratePlanModal();
}

function closeGeneratePlanModalFn() {
    generatePlanModal.classList.remove('active');
    resetGeneratePlanModal();
}

function resetGeneratePlanModal() {
    planFileInput.value = '';
    diagnosticoFileInput.value = '';
    planFileSelected.innerHTML = '<span class="no-file-text">Ningún archivo seleccionado</span>';
    diagnosticoFileSelected.innerHTML = '<span class="no-file-text">Ningún archivo seleccionado (opcional)</span>';
    processPlanBtn.disabled = true;
}

function updateFileDisplay(inputElement, displayElement) {
    const file = inputElement.files[0];
    
    if (file) {
        const icon = getFileIconByName(file.name);
        const size = (file.size / (1024 * 1024)).toFixed(2);
        
        displayElement.innerHTML = `
            <span class="file-icon">${icon}</span>
            <span class="file-name-text">${file.name}</span>
            <span class="file-size-text">(${size} MB)</span>
        `;
    } else {
        const isOptional = inputElement === diagnosticoFileInput;
        displayElement.innerHTML = `<span class="no-file-text">Ningún archivo seleccionado${isOptional ? ' (opcional)' : ''}</span>`;
    }
    
    // Habilitar botón si al menos el plan está seleccionado
    processPlanBtn.disabled = !planFileInput.files[0];
}

function getFileIconByName(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const icons = {
        'pdf': '📄',
        'doc': '📘',
        'docx': '📘',
        'txt': '📄',
        'jpg': '🖼️',
        'jpeg': '🖼️',
        'png': '🖼️'
    };
    return icons[ext] || '📎';
}

async function processPlan() {
    try {
        const planFile = planFileInput.files[0];
        const diagnosticoFile = diagnosticoFileInput.files[0];
        
        if (!planFile) {
            showMessage('Debes seleccionar el archivo del plan de estudios', 'error');
            return;
        }
        
        // Validar tamaños
        const maxSize = 80 * 1024 * 1024; // 80MB
        if (planFile.size > maxSize) {
            showMessage('El plan de estudios excede el tamaño máximo de 80MB', 'error');
            return;
        }
        
        if (diagnosticoFile && diagnosticoFile.size > maxSize) {
            showMessage('El diagnóstico excede el tamaño máximo de 80MB', 'error');
            return;
        }
        
        // Cerrar modal y mostrar loading
        closeGeneratePlanModalFn();
        showLoadingWithProgress('Procesando archivos con IA...', 'Esto puede tardar 1-3 minutos');
        
        // Crear FormData
        const formData = new FormData();
        formData.append('plan_file', planFile);
        if (diagnosticoFile) {
            formData.append('diagnostico_file', diagnosticoFile);
        }
        
        // Enviar a la API
        const response = await fetch(`${API_BASE}/plans/generate`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${currentToken}`
            },
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error generando plan');
        }
        
        const result = await response.json();
        
        hideLoading();
        
        if (result.success) {
            showMessage(
                `Plan generado exitosamente: "${result.plan_data.nombre_plan}"`,
                'success'
            );
            
            // Recargar planes y cambiar a sección consulta
            await loadPlanes();
            switchToSection('consulta');
            
            // Mostrar el plan recién creado
            setTimeout(() => {
                showPlanDetail(result.plan_data.plan_id);
            }, 500);
        } else {
            showMessage(result.error || 'Error generando plan', 'error');
        }
        
    } catch (error) {
        hideLoading();
        console.error('Error procesando plan:', error);
        showMessage(`Error: ${error.message}`, 'error');
    }
}

// ===== CARGA Y VISUALIZACIÓN DE PLANES =====

async function loadPlanes() {
    try {
        if (!currentToken) {
            planesList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🔒</div>
                    <h3>Inicia sesión para ver tus planes</h3>
                </div>
            `;
            return;
        }
        
        const response = await apiRequest('/plans/list');
        
        if (response.success) {
            planesGenerados = response.planes || [];
            displayPlanes();
            updateConsultaStats();
        } else {
            throw new Error('Error cargando planes');
        }
        
    } catch (error) {
        console.error('Error cargando planes:', error);
        planesList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">⚠️</div>
                <h3>Error cargando planes</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

function displayPlanes() {
    if (planesGenerados.length === 0) {
        planesList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <h3>No hay planes generados aún</h3>
                <p>Ve a la sección ARCHIVOS y presiona "AÑADIR PLAN" para comenzar</p>
            </div>
        `;
        return;
    }
    
    // Calcular paginación
    const totalPages = Math.ceil(planesGenerados.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const currentPlans = planesGenerados.slice(startIndex, endIndex);
    
    planesList.innerHTML = currentPlans.map(plan => createPlanCard(plan)).join('');
    
    // Agregar paginación si hay más de una página
    if (totalPages > 1) {
        const paginationHTML = `
            <div class="pagination">
                <button class="pagination-btn" onclick="changePage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
                    ← Anterior
                </button>
                <span class="pagination-info">Página ${currentPage} de ${totalPages}</span>
                <button class="pagination-btn" onclick="changePage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>
                    Siguiente →
                </button>
            </div>
        `;
        planesList.insertAdjacentHTML('beforeend', paginationHTML);
    }
}

function createPlanCard(plan) {
    const fecha = new Date(plan.fecha_generacion).toLocaleDateString('es-MX', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    
    const diagnosticoIcon = plan.tiene_diagnostico ? '✅' : '⚪';
    const diagnosticoText = plan.tiene_diagnostico ? 'Con diagnóstico' : 'Sin diagnóstico';
    
    // Adaptar para mostrar campo_formativo o materia
    const campoFormativo = plan.campo_formativo_principal || plan.campo_formativo || plan.materia || '';
    
    return `
        <div class="plan-card-consulta">
            <div class="plan-card-header-consulta">
                <div class="plan-card-icon">📚</div>
                <div class="plan-card-info">
                    <h3 class="plan-card-title">${escapeHtml(plan.nombre_plan)}</h3>
                    <div class="plan-card-meta">
                        <span class="meta-item">📅 ${fecha}</span>
                        <span class="meta-item">📊 ${plan.num_modulos} módulos</span>
                        <span class="meta-item">${diagnosticoIcon} ${diagnosticoText}</span>
                    </div>
                    ${plan.grado ? `<div class="plan-card-badge">${escapeHtml(plan.grado)}</div>` : ''}
                    ${campoFormativo ? `<div class="plan-card-badge secondary">${escapeHtml(campoFormativo)}</div>` : ''}
                </div>
            </div>
            <div class="plan-card-actions">
                <button class="btn-action btn-view" onclick="showPlanDetail('${plan.plan_id}')" title="Ver detalle">
                    👁️ Ver
                </button>
                <button class="btn-action btn-download" onclick="downloadPlan('${plan.plan_id}')" title="Descargar JSON">
                    📥 Descargar
                </button>
                <button class="btn-action btn-delete" onclick="confirmDeletePlan('${plan.plan_id}')" title="Eliminar">
                    🗑️ Eliminar
                </button>
            </div>
        </div>
    `;
}

function updateConsultaStats() {
    const total = planesGenerados.length;
    const conDiagnostico = planesGenerados.filter(p => p.tiene_diagnostico).length;
    
    consultaStats.innerHTML = `
        <span>📊 ${total} ${total === 1 ? 'plan generado' : 'planes generados'}</span>
        ${conDiagnostico > 0 ? `<span>✅ ${conDiagnostico} con diagnóstico</span>` : ''}
    `;
}

async function showPlanDetail(planId) {
    try {
        showLoading('Cargando plan...');
        
        const response = await apiRequest(`/plans/${planId}`);
        
        if (!response.success) {
            throw new Error('No se pudo cargar el plan');
        }
        
        const plan = response.plan;
        
        // Actualizar título del modal
        planDetailTitle.textContent = plan.nombre_plan;
        
        // Detectar si es estructura NUEVA o ANTIGUA
        const esEstructuraNueva = plan.modulos[0] && plan.modulos[0].actividad_inicio !== undefined;
        
        // Generar contenido adaptado
        let html = `
            <div class="plan-detail-header">
                <div class="plan-detail-meta">
                    ${plan.grado ? `<span class="detail-badge">${escapeHtml(plan.grado)}</span>` : ''}
                    ${plan.campo_formativo_principal ? `<span class="detail-badge secondary">${escapeHtml(plan.campo_formativo_principal)}</span>` : ''}
                    ${plan.materia && !plan.campo_formativo_principal ? `<span class="detail-badge secondary">${escapeHtml(plan.materia)}</span>` : ''}
                    ${plan.edad_aprox ? `<span class="detail-badge secondary">👶 ${escapeHtml(plan.edad_aprox)}</span>` : ''}
                </div>
                <div class="plan-detail-info">
                    <p><strong>📅 Generado:</strong> ${new Date(plan.fecha_generacion).toLocaleString('es-MX')}</p>
                    <p><strong>📊 Total de módulos:</strong> ${plan.num_modulos}</p>
                    ${plan.duracion_total ? `<p><strong>⏱️ Duración total:</strong> ${plan.duracion_total}</p>` : ''}
                    <p><strong>🤖 Generado con:</strong> ${plan.generado_con || 'IA'}</p>
                    ${plan.tiene_diagnostico ? '<p><strong>✅ Personalizado con diagnóstico del grupo</strong></p>' : '<p><strong>⚪ Sin diagnóstico (plan estándar)</strong></p>'}
                </div>
                
                ${plan.ejes_articuladores_generales && plan.ejes_articuladores_generales.length > 0 ? `
                    <div class="plan-ejes-section">
                        <h4>🔗 Ejes Articuladores:</h4>
                        <div class="ejes-list">
                            ${plan.ejes_articuladores_generales.map(eje => `<span class="eje-badge">${escapeHtml(eje)}</span>`).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
            
            <div class="plan-modules-container">
        `;
        
        // Agregar módulos según la estructura
        plan.modulos.forEach((modulo, index) => {
            html += `
                <div class="module-card" id="module-${index}">
                    <div class="module-header" onclick="toggleModule(${index})">
                        <div class="module-number">Módulo ${modulo.numero}</div>
                        <h3 class="module-title">${escapeHtml(modulo.nombre)}</h3>
                        <span class="module-arrow">▼</span>
                    </div>
                    <div class="module-body" id="module-body-${index}">
            `;
            
            // SI ES ESTRUCTURA NUEVA (con actividad_inicio, actividades_desarrollo, etc.)
            if (esEstructuraNueva) {
                html += `
                    ${modulo.campo_formativo ? `
                        <div class="module-section">
                            <h4>📚 Campo Formativo</h4>
                            <p>${escapeHtml(modulo.campo_formativo)}</p>
                        </div>
                    ` : ''}
                    
                    ${modulo.ejes_articuladores && modulo.ejes_articuladores.length > 0 ? `
                        <div class="module-section">
                            <h4>🔗 Ejes Articuladores</h4>
                            <div class="ejes-list-small">
                                ${modulo.ejes_articuladores.map(eje => `<span class="eje-badge-small">${escapeHtml(eje)}</span>`).join('')}
                            </div>
                        </div>
                    ` : ''}
                    
                    ${modulo.aprendizaje_esperado ? `
                        <div class="module-section">
                            <h4>🎯 Aprendizaje Esperado</h4>
                            <p>${escapeHtml(modulo.aprendizaje_esperado)}</p>
                        </div>
                    ` : ''}
                    
                    ${modulo.tiempo_estimado ? `
                        <div class="module-section">
                            <h4>⏱️ Tiempo Estimado</h4>
                            <p>${escapeHtml(modulo.tiempo_estimado)}</p>
                        </div>
                    ` : ''}
                    
                    ${modulo.actividad_inicio ? `
                        <div class="module-section actividad-section">
                            <h4>🎬 Actividad de Inicio: ${escapeHtml(modulo.actividad_inicio.nombre)}</h4>
                            <p><strong>Descripción:</strong> ${escapeHtml(modulo.actividad_inicio.descripcion)}</p>
                            <p><strong>⏱️ Duración:</strong> ${escapeHtml(modulo.actividad_inicio.duracion)}</p>
                            ${modulo.actividad_inicio.materiales ? `
                                <p><strong>🛠️ Materiales:</strong> ${Array.isArray(modulo.actividad_inicio.materiales) ? modulo.actividad_inicio.materiales.map(m => escapeHtml(m)).join(', ') : escapeHtml(modulo.actividad_inicio.materiales)}</p>
                            ` : ''}
                            ${modulo.actividad_inicio.organizacion ? `
                                <p><strong>👥 Organización:</strong> ${escapeHtml(modulo.actividad_inicio.organizacion)}</p>
                            ` : ''}
                        </div>
                    ` : ''}
                    
                    ${modulo.actividades_desarrollo && modulo.actividades_desarrollo.length > 0 ? `
                        <div class="module-section actividad-section">
                            <h4>🚀 Actividades de Desarrollo</h4>
                            ${modulo.actividades_desarrollo.map((act, idx) => `
                                <div class="actividad-card">
                                    <h5>Actividad ${idx + 1}: ${escapeHtml(act.nombre)}</h5>
                                    <p><strong>Tipo:</strong> ${act.tipo ? `<span class="tipo-badge">${escapeHtml(act.tipo)}</span>` : 'N/A'}</p>
                                    <p><strong>Descripción:</strong> ${escapeHtml(act.descripcion)}</p>
                                    ${act.duracion ? `<p><strong>⏱️ Duración:</strong> ${escapeHtml(act.duracion)}</p>` : ''}
                                    ${act.organizacion ? `<p><strong>👥 Organización:</strong> ${escapeHtml(act.organizacion)}</p>` : ''}
                                    ${act.materiales ? `
                                        <p><strong>🛠️ Materiales:</strong> ${Array.isArray(act.materiales) ? act.materiales.map(m => escapeHtml(m)).join(', ') : escapeHtml(act.materiales)}</p>
                                    ` : ''}
                                    ${act.aspectos_a_observar ? `
                                        <p><strong>👀 Aspectos a observar:</strong> ${escapeHtml(act.aspectos_a_observar)}</p>
                                    ` : ''}
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                    
                    ${modulo.actividad_cierre ? `
                        <div class="module-section actividad-section">
                            <h4>🎬 Actividad de Cierre: ${escapeHtml(modulo.actividad_cierre.nombre)}</h4>
                            <p><strong>Descripción:</strong> ${escapeHtml(modulo.actividad_cierre.descripcion)}</p>
                            <p><strong>⏱️ Duración:</strong> ${escapeHtml(modulo.actividad_cierre.duracion)}</p>
                            ${modulo.actividad_cierre.preguntas_guia && modulo.actividad_cierre.preguntas_guia.length > 0 ? `
                                <p><strong>💬 Preguntas guía:</strong></p>
                                <ul class="preguntas-list">
                                    ${modulo.actividad_cierre.preguntas_guia.map(p => `<li>${escapeHtml(p)}</li>`).join('')}
                                </ul>
                            ` : ''}
                        </div>
                    ` : ''}
                    
                    ${modulo.consejos_maestra ? `
                        <div class="module-section">
                            <h4>💡 Consejos para la Maestra</h4>
                            <p>${escapeHtml(modulo.consejos_maestra)}</p>
                        </div>
                    ` : ''}
                    
                    ${modulo.variaciones ? `
                        <div class="module-section">
                            <h4>🔄 Variaciones</h4>
                            <p>${escapeHtml(modulo.variaciones)}</p>
                        </div>
                    ` : ''}
                    
                    ${modulo.vinculo_familia ? `
                        <div class="module-section">
                            <h4>🏠 Vínculo con la Familia</h4>
                            <p>${escapeHtml(modulo.vinculo_familia)}</p>
                        </div>
                    ` : ''}
                    
                    ${modulo.evaluacion ? `
                        <div class="module-section">
                            <h4>📋 Evaluación</h4>
                            <p>${escapeHtml(modulo.evaluacion)}</p>
                        </div>
                    ` : ''}
                `;
            } 
            // SI ES ESTRUCTURA ANTIGUA (con tema, objetivo, planteamiento, etc.)
            else {
                html += `
                    ${modulo.tema ? `
                        <div class="module-section">
                            <h4>🎯 Tema</h4>
                            <p>${escapeHtml(modulo.tema)}</p>
                        </div>
                    ` : ''}
                    
                    ${modulo.objetivo ? `
                        <div class="module-section">
                            <h4>📋 Objetivo</h4>
                            <p>${escapeHtml(modulo.objetivo)}</p>
                        </div>
                    ` : ''}
                    
                    ${modulo.planteamiento ? `
                        <div class="module-section">
                            <h4>📝 Planteamiento</h4>
                            <p>${escapeHtml(modulo.planteamiento)}</p>
                        </div>
                    ` : ''}
                    
                    ${modulo.materiales ? `
                        <div class="module-section">
                            <h4>🛠️ Materiales</h4>
                            <p>${escapeHtml(modulo.materiales)}</p>
                        </div>
                    ` : ''}
                    
                    ${modulo.tiempo ? `
                        <div class="module-section">
                            <h4>⏱️ Tiempo</h4>
                            <p>${escapeHtml(modulo.tiempo)}</p>
                        </div>
                    ` : ''}
                    
                    ${modulo.participacion ? `
                        <div class="module-section">
                            <h4>👥 Participación</h4>
                            <p>${escapeHtml(modulo.participacion)}</p>
                        </div>
                    ` : ''}
                    
                    ${modulo.ejes_articulares ? `
                        <div class="module-section">
                            <h4>🔗 Ejes Articulares</h4>
                            <p>${escapeHtml(modulo.ejes_articulares)}</p>
                        </div>
                    ` : ''}
                `;
            }
            
            html += `
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        
        // Agregar sección de recursos si existe (solo estructura nueva)
        if (plan.recursos_educativos) {
            html += `
                <div class="recursos-section">
                    <h3>📚 Recursos Educativos</h3>
            `;
            
            if (plan.recursos_educativos.materiales_generales && plan.recursos_educativos.materiales_generales.length > 0) {
                html += `
                    <div class="recurso-subsection">
                        <h4>🛠️ Materiales Generales</h4>
                        <ul class="materiales-list">
                            ${plan.recursos_educativos.materiales_generales.map(m => `<li>${escapeHtml(m)}</li>`).join('')}
                        </ul>
                    </div>
                `;
            }
            
            if (plan.recursos_educativos.cuentos_recomendados && plan.recursos_educativos.cuentos_recomendados.length > 0) {
                html += `
                    <div class="recurso-subsection">
                        <h4>📖 Cuentos Recomendados</h4>
                        ${plan.recursos_educativos.cuentos_recomendados.map(cuento => `
                            <div class="recurso-card">
                                <p><strong>${escapeHtml(cuento.titulo)}</strong></p>
                                ${cuento.autor ? `<p><em>Autor: ${escapeHtml(cuento.autor)}</em></p>` : ''}
                                <div class="recurso-badges">
                                    <span class="recurso-badge ${cuento.tipo === 'RECURSO REAL' ? 'real' : 'creativo'}">${escapeHtml(cuento.tipo)}</span>
                                    <span class="recurso-badge ${cuento.acceso === 'GRATUITO' ? 'gratuito' : 'compra'}">${escapeHtml(cuento.acceso)}</span>
                                </div>
                                ${cuento.disponibilidad ? `<p class="disponibilidad">📍 ${escapeHtml(cuento.disponibilidad)}</p>` : ''}
                                ${cuento.descripcion_breve ? `<p class="descripcion">${escapeHtml(cuento.descripcion_breve)}</p>` : ''}
                            </div>
                        `).join('')}
                    </div>
                `;
            }
            
            if (plan.recursos_educativos.canciones_recomendadas && plan.recursos_educativos.canciones_recomendadas.length > 0) {
                html += `
                    <div class="recurso-subsection">
                        <h4>🎵 Canciones Recomendadas</h4>
                        ${plan.recursos_educativos.canciones_recomendadas.map(cancion => `
                            <div class="recurso-card">
                                <p><strong>${escapeHtml(cancion.titulo)}</strong></p>
                                <div class="recurso-badges">
                                    <span class="recurso-badge ${cancion.tipo === 'RECURSO REAL' ? 'real' : 'creativo'}">${escapeHtml(cancion.tipo)}</span>
                                    <span class="recurso-badge ${cancion.acceso === 'GRATUITO' ? 'gratuito' : 'compra'}">${escapeHtml(cancion.acceso)}</span>
                                </div>
                                ${cancion.disponibilidad ? `<p class="disponibilidad">📍 ${escapeHtml(cancion.disponibilidad)}</p>` : ''}
                                ${cancion.uso_sugerido ? `<p class="uso">💡 ${escapeHtml(cancion.uso_sugerido)}</p>` : ''}
                            </div>
                        `).join('')}
                    </div>
                `;
            }
            
            html += '</div>';
        }
        
        // Agregar recomendaciones de ambiente si existen
        if (plan.recomendaciones_ambiente) {
            html += `
                <div class="recomendaciones-section">
                    <h3>🏫 Recomendaciones para el Ambiente</h3>
                    <p>${escapeHtml(plan.recomendaciones_ambiente)}</p>
                </div>
            `;
        }
        
        // Agregar vinculación curricular si existe
        if (plan.vinculacion_curricular) {
            html += `
                <div class="vinculacion-section">
                    <h3>🔗 Vinculación Curricular</h3>
                    <div class="vinculacion-grid">
                        ${plan.vinculacion_curricular.campo_formativo_principal ? `
                            <div class="vinculacion-item">
                                <h4>Campo Formativo Principal:</h4>
                                <p>${escapeHtml(plan.vinculacion_curricular.campo_formativo_principal)}</p>
                            </div>
                        ` : ''}
                        
                        ${plan.vinculacion_curricular.campos_secundarios && plan.vinculacion_curricular.campos_secundarios.length > 0 ? `
                            <div class="vinculacion-item">
                                <h4>Campos Secundarios:</h4>
                                <ul>
                                    ${plan.vinculacion_curricular.campos_secundarios.map(c => `<li>${escapeHtml(c)}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                        
                        ${plan.vinculacion_curricular.ejes_transversales && plan.vinculacion_curricular.ejes_transversales.length > 0 ? `
                            <div class="vinculacion-item">
                                <h4>Ejes Transversales:</h4>
                                <ul>
                                    ${plan.vinculacion_curricular.ejes_transversales.map(e => `<li>${escapeHtml(e)}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                        
                        ${plan.vinculacion_curricular.aprendizajes_clave && plan.vinculacion_curricular.aprendizajes_clave.length > 0 ? `
                            <div class="vinculacion-item">
                                <h4>Aprendizajes Clave:</h4>
                                <ul>
                                    ${plan.vinculacion_curricular.aprendizajes_clave.map(a => `<li>${escapeHtml(a)}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }
        
        planDetailContent.innerHTML = html;
        hideLoading();
        planDetailModal.classList.add('active');
        
    } catch (error) {
        hideLoading();
        showMessage(`Error cargando plan: ${error.message}`, 'error');
    }
}

function toggleModule(index) {
    const moduleBody = document.getElementById(`module-body-${index}`);
    const arrow = document.querySelector(`#module-${index} .module-arrow`);
    
    if (moduleBody.classList.contains('expanded')) {
        moduleBody.classList.remove('expanded');
        arrow.style.transform = 'rotate(0deg)';
    } else {
        moduleBody.classList.add('expanded');
        arrow.style.transform = 'rotate(180deg)';
    }
}

async function downloadPlan(planId) {
    try {
        showLoading('Generando documento Word...');
        
        // Cambiar la URL para usar la nueva ruta de descarga Word
        const response = await fetch(`${API_BASE}/plans/${planId}/download`, {
            headers: {
                'Authorization': `Bearer ${currentToken}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Error descargando plan');
        }
        
        // Obtener el nombre del archivo desde los headers o generar uno
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'Plan_Educativo.docx';
        
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename=(.+)/);
            if (filenameMatch) {
                filename = filenameMatch[1].replace(/['"]/g, '');
            }
        }
        
        // Crear blob y descargar
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        hideLoading();
        showMessage('Plan descargado correctamente en formato Word', 'success');
        
    } catch (error) {
        hideLoading();
        showMessage(`Error descargando: ${error.message}`, 'error');
    }
}

async function deletePlan(planId) {
    try {
        showLoading('Eliminando plan...');
        
        await apiRequest(`/plans/${planId}`, {
            method: 'DELETE'
        });
        
        showMessage('Plan eliminado correctamente', 'success');
        await loadPlanes();
        
    } catch (error) {
        showMessage(`Error eliminando plan: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

function confirmDeletePlan(planId) {
    const plan = planesGenerados.find(p => p.plan_id === planId);
    const planName = plan ? plan.nombre_plan : 'este plan';
    
    showModal(
        `¿Estás seguro de que quieres eliminar "${planName}"? Esta acción no se puede deshacer.`,
        () => deletePlan(planId)
    );
}

function changePage(page) {
    const totalPages = Math.ceil(planesGenerados.length / itemsPerPage);
    if (page < 1 || page > totalPages) return;
    
    currentPage = page;
    displayPlanes();
    
    // Scroll suave hacia arriba
    planesList.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ===== FUNCIONES DE VISTA PREVIA =====

async function openFilePreview(category, filename) {
    try {
        showLoading('Cargando vista previa...');
        
        const ext = filename.split('.').pop().toLowerCase();
        
        previewModal.classList.add('active');
        previewFilename.textContent = filename;
        currentPreviewFile = { category, filename };
        previewContainer.innerHTML = '<div class="loading-preview"><div class="spinner"></div><p>Cargando...</p></div>';
        
        const response = await fetch(`${API_BASE}/files/preview/${category}/${encodeURIComponent(filename)}`, {
            headers: {
                'Authorization': `Bearer ${currentToken}`
            }
        });
        
        if (!response.ok) {
            throw new Error('No se pudo cargar la vista previa');
        }
        
        previewContainer.innerHTML = '';
        
        if (ext === 'pdf') {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            
            previewContainer.classList.add('pdf-preview');
            previewContainer.innerHTML = `
                <iframe src="${url}" style="width: 100%; height: 100%; border: none;"></iframe>
            `;
        } else if (['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(ext)) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            
            previewContainer.classList.add('image-preview');
            previewContainer.innerHTML = `
                <img src="${url}" style="max-width: 100%; max-height: 100%; object-fit: contain;" alt="${escapeHtml(filename)}">
            `;
            previewContainer.style.background = '#000';
        } else if (ext === 'txt') {
            const data = await response.json();
            
            previewContainer.classList.add('text-preview');
            previewContainer.innerHTML = `
                <pre style="padding: 20px; text-align: left; white-space: pre-wrap; word-wrap: break-word; width: 100%; height: 100%; overflow: auto; margin: 0;">${escapeHtml(data.content)}</pre>
            `;
            previewContainer.style.background = '#fafafa';
        } else {
            previewContainer.innerHTML = `
                <div class="preview-error">
                    <div class="preview-error-icon">❌</div>
                    <h3>Vista previa no disponible</h3>
                    <p>Este tipo de archivo no se puede previsualizar</p>
                    <button class="btn btn-primary" onclick="downloadFileAction('${category}', '${filename.replace(/'/g, "\\'")}')">
                        📥 Descargar archivo
                    </button>
                </div>
            `;
        }
        
        hideLoading();
        
    } catch (error) {
        hideLoading();
        previewContainer.innerHTML = `
            <div class="preview-error">
                <div class="preview-error-icon">⚠️</div>
                <h3>Error al cargar vista previa</h3>
                <p>${error.message}</p>
                <button class="btn btn-primary" onclick="previewModal.classList.remove('active')">
                    Cerrar
                </button>
            </div>
        `;
        console.error('Error en vista previa:', error);
    }
}

async function downloadFileAction(category, filename) {
    try {
        showLoading('Descargando archivo...');
        
        const response = await fetch(`${API_BASE}/files/download/${category}/${encodeURIComponent(filename)}`, {
            headers: {
                'Authorization': `Bearer ${currentToken}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Error al descargar archivo');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showMessage(`Archivo "${filename}" descargado correctamente`, 'success');
        
    } catch (error) {
        showMessage('Error al descargar: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ===== UTILIDADES =====

function showLoadingWithProgress(mainText, subText) {
    const loadingText = document.getElementById('loading-text');
    const loadingSubtext = document.getElementById('loading-subtext');
    
    loadingText.textContent = mainText;
    loadingSubtext.textContent = subText;
    
    document.getElementById('loading-overlay').classList.remove('hidden');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== CERRAR SESIÓN =====
function logout() {
    clearSession();
    window.location.href = 'login.html';
}

// ===== EVENT LISTENERS =====
function setupEventListeners() {
    logoutBtn.addEventListener('click', logout);
    
    Object.keys(navButtons).forEach(key => {
        navButtons[key].addEventListener('click', () => switchToSection(key));
    });
    
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            uploadFiles(e.target.files);
            e.target.value = '';
        }
    });
    
    confirmModal.addEventListener('click', function(e) {
        if (e.target === confirmModal) {
            confirmModal.classList.add('hidden');
        }
    });
    
    // Event listeners para generación de planes
    generatePlanBtn.addEventListener('click', openGeneratePlanModal);
    closeGeneratePlanModal.addEventListener('click', closeGeneratePlanModalFn);
    cancelGeneratePlanBtn.addEventListener('click', closeGeneratePlanModalFn);
    processPlanBtn.addEventListener('click', processPlan);
    
    planFileInput.addEventListener('change', () => updateFileDisplay(planFileInput, planFileSelected));
    diagnosticoFileInput.addEventListener('change', () => updateFileDisplay(diagnosticoFileInput, diagnosticoFileSelected));
    
    // Cerrar modales al hacer clic fuera
    generatePlanModal.addEventListener('click', (e) => {
        if (e.target === generatePlanModal) {
            closeGeneratePlanModalFn();
        }
    });
    
    // Event listeners para vista previa
    closePreviewModal.addEventListener('click', () => {
        previewModal.classList.remove('active');
        previewContainer.innerHTML = '';
        previewContainer.className = 'preview-container';
        previewContainer.style.background = '';
        currentPreviewFile = null;
    });

    downloadPreviewBtn.addEventListener('click', () => {
        if (currentPreviewFile) {
            downloadFileAction(currentPreviewFile.category, currentPreviewFile.filename);
        }
    });

    previewModal.addEventListener('click', (e) => {
        if (e.target === previewModal) {
            previewModal.classList.remove('active');
            previewContainer.innerHTML = '';
            previewContainer.className = 'preview-container';
            previewContainer.style.background = '';
            currentPreviewFile = null;
        }
    });
    
    // Event listeners para modal de detalle
    closePlanDetailModal.addEventListener('click', () => {
        planDetailModal.classList.remove('active');
    });
    
    planDetailModal.addEventListener('click', (e) => {
        if (e.target === planDetailModal) {
            planDetailModal.classList.remove('active');
        }
    });
}

// Hacer funciones globales para usar en onclick
window.confirmDeleteFile = confirmDeleteFile;
window.openFilePreview = openFilePreview;
window.downloadFileAction = downloadFileAction;
window.showPlanDetail = showPlanDetail;
window.downloadPlan = downloadPlan;
window.confirmDeletePlan = confirmDeletePlan;
window.changePage = changePage;
window.toggleModule = toggleModule;