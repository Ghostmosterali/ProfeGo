// ===== SCRIPT PARA MENU.HTML - VERSIÓN PRODUCCIÓN =====

// ===== ELEMENTOS DEL DOM =====
const logoutBtn = document.getElementById('logout-btn');
const userInfo = document.getElementById('user-info');
const fileInput = document.getElementById('file-input');
const filesGallery = document.getElementById('files-gallery');

const navButtons = {
    inicio: document.getElementById('nav-inicio'),
    archivos: document.getElementById('nav-archivos'),
    planes: document.getElementById('nav-planes'),
    acerca: document.getElementById('nav-acerca')
};

const contentSections = {
    inicio: document.getElementById('inicio-content'),
    archivos: document.getElementById('archivos-content'),
    planes: document.getElementById('planes-content'),
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

// Elementos Plan de Estudio
const createPlanBtn = document.getElementById('create-plan-btn');
const planModal = document.getElementById('plan-modal');
const closePlanModal = document.getElementById('close-plan-modal');
const cancelPlanBtn = document.getElementById('cancel-plan-btn');
const savePlanBtn = document.getElementById('save-plan-btn');
const addModuleBtn = document.getElementById('add-module-btn');
const modulesContainer = document.getElementById('modules-container');
const planesList = document.getElementById('planes-list');
const planNombreInput = document.getElementById('plan-nombre');

// Modal selector de archivos
const fileSelectorModal = document.getElementById('file-selector-modal');
const closeFileSelector = document.getElementById('close-file-selector');
const fileSelectorList = document.getElementById('file-selector-list');

// Variables globales para planes
let currentModuleIndex = 0;
let currentActivityElement = null;
let planesDeEstudio = [];
let currentPage = 1;
const itemsPerPage = 3;

// ===== VERIFICAR AUTENTICACIÓN AL CARGAR =====
document.addEventListener('DOMContentLoaded', function() {
    // Verificar si hay sesión activa
    if (!loadSession()) {
        window.location.href = 'login.html';
        return;
    }
    
    // Mostrar información del usuario
    userInfo.textContent = `👋 Hola, ${currentUser}`;
    
    // Cargar planes guardados
    loadPlanes();
    
    // Iniciar en la sección de inicio
    switchToSection('inicio');
    
    // Configurar event listeners
    setupEventListeners();
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
    
    // Cargar archivos solo si vamos a esa sección
    if (sectionName === 'archivos' && currentToken) {
        loadFiles();
    }
    
    // Cargar planes si vamos a esa sección
    if (sectionName === 'planes') {
        displayPlanes();
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
                <p>Usa el botón 'Subir archivos' para agregar tus documentos</p>
            </div>
        `;
        return;
    }
    
    const originalFiles = files.filter(file => file.category === 'original');
    const processedFiles = files.filter(file => file.category === 'procesado');
    
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
        else if (fileType.includes('word')) icon = '📝';
        else if (fileType.includes('excel')) icon = '📊';
    }
    
    // Escapar el nombre del archivo para evitar problemas con comillas
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
            <button class="preview-btn" onclick="openFilePreview('${file.category}', '${escapedName}')" title="Vista previa de ${file.name}">
                👁️
            </button>
            <button class="download-btn" onclick="downloadFileAction('${file.category}', '${escapedName}')" title="Descargar ${file.name}">
                📥
            </button>
            <button class="delete-btn" onclick="confirmDeleteFile('${file.category}', '${escapedName}')" title="Eliminar ${file.name}">
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

// ===== GESTIÓN DE PLANES DE ESTUDIO =====

function loadPlanes() {
    const stored = localStorage.getItem(`planesDeEstudio_${currentUser}`);
    if (stored) {
        planesDeEstudio = JSON.parse(stored);
    }
}

function savePlanesToStorage() {
    // Guardar planes por usuario
    localStorage.setItem(`planesDeEstudio_${currentUser}`, JSON.stringify(planesDeEstudio));
}

function displayPlanes() {
    if (planesDeEstudio.length === 0) {
        planesList.innerHTML = `
            <div class="empty-state">
                <p>No hay planes de estudio para mostrar.</p>
                <p style="font-size: 12px; margin-top: 10px;">Crea tu primer plan usando el botón "Crear Plan de Estudio"</p>
            </div>
        `;
        return;
    }
    
    // Calcular paginación
    const totalPages = Math.ceil(planesDeEstudio.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    
    // Obtener planes para la página actual (invertidos para mostrar los más recientes primero)
    const reversedPlanes = [...planesDeEstudio].reverse();
    const currentPlans = reversedPlanes.slice(startIndex, endIndex);
    
    // Generar HTML de los planes
    planesList.innerHTML = currentPlans.map((plan, index) => {
        const realIndex = planesDeEstudio.length - 1 - (startIndex + index);
        return `
            <div class="plan-card">
                <div class="plan-card-header" onclick="togglePlanCard(${realIndex})">
                    <div class="plan-card-title">
                        <h4>${plan.nombre}</h4>
                        <span class="plan-card-arrow">▼</span>
                    </div>
                    <div class="plan-card-meta">
                        <span class="plan-date">📅 ${new Date(plan.fecha).toLocaleDateString()}</span>
                        <span class="plan-modules">📚 ${plan.modulos.length} módulos</span>
                    </div>
                </div>
                <div class="plan-card-body" id="plan-body-${realIndex}">
                    ${plan.modulos.map((modulo, modIndex) => `
                        <div class="plan-module-item">
                            <div class="module-number">Módulo ${modIndex + 1}</div>
                            <div class="module-details">
                                <div class="module-objective">
                                    <strong>Objetivo:</strong>
                                    <p>${modulo.objetivo}</p>
                                </div>
                                <div class="module-activity">
                                    <strong>Actividad:</strong>
                                    <p>📄 ${modulo.actividad}</p>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                    <div class="plan-card-actions">
                        <button class="btn btn-danger btn-sm" onclick="deletePlan(${realIndex})">
                            🗑️ Eliminar Plan
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    // Agregar paginación si hay más de una página
    if (totalPages > 1) {
        const paginationHTML = `
            <div class="pagination">
                <button class="pagination-btn" onclick="changePage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
                    ← Anterior
                </button>
                <div class="pagination-numbers">
                    ${generatePaginationNumbers(totalPages)}
                </div>
                <button class="pagination-btn" onclick="changePage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>
                    Siguiente →
                </button>
            </div>
        `;
        planesList.insertAdjacentHTML('beforeend', paginationHTML);
    }
}

function generatePaginationNumbers(totalPages) {
    let html = '';
    for (let i = 1; i <= totalPages; i++) {
        html += `
            <button class="pagination-number ${i === currentPage ? 'active' : ''}" onclick="changePage(${i})">
                ${i}
            </button>
        `;
    }
    return html;
}

function changePage(page) {
    const totalPages = Math.ceil(planesDeEstudio.length / itemsPerPage);
    if (page < 1 || page > totalPages) return;
    
    currentPage = page;
    displayPlanes();
    
    // Scroll suave hacia arriba
    planesList.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function togglePlanCard(index) {
    const cardBody = document.getElementById(`plan-body-${index}`);
    const arrow = cardBody.previousElementSibling.querySelector('.plan-card-arrow');
    
    if (cardBody.classList.contains('expanded')) {
        cardBody.classList.remove('expanded');
        arrow.style.transform = 'rotate(0deg)';
    } else {
        cardBody.classList.add('expanded');
        arrow.style.transform = 'rotate(180deg)';
    }
}

function openPlanModal() {
    planModal.classList.add('active');
    planNombreInput.value = '';
    modulesContainer.innerHTML = '';
    currentModuleIndex = 0;
    addModule();
}

function closePlanModalFn() {
    planModal.classList.remove('active');
}

function addModule() {
    currentModuleIndex++;
    const moduleDiv = document.createElement('div');
    moduleDiv.className = 'module-item';
    moduleDiv.dataset.moduleIndex = currentModuleIndex;
    
    moduleDiv.innerHTML = `
        <div class="module-header">
            <h4>Módulo ${currentModuleIndex}</h4>
            <button class="btn-icon-delete" onclick="removeModule(${currentModuleIndex})" title="Eliminar módulo">
                ✕
            </button>
        </div>
        <div class="form-group">
            <label>Objetivo:</label>
            <textarea class="module-objetivo" rows="2" placeholder="Escribe el objetivo del módulo"></textarea>
        </div>
        <div class="form-group">
            <label>Actividad:</label>
            <div class="activity-selector">
                <button type="button" class="btn-file-selector" onclick="openFileSelector(${currentModuleIndex})">
                    📁 Seleccionar archivo
                </button>
                <div class="selected-file" data-module="${currentModuleIndex}">
                    <span class="no-file">No se ha seleccionado ningún archivo</span>
                </div>
            </div>
        </div>
        <div class="module-actions">
            <button type="button" class="btn btn-secondary btn-sm" onclick="changeModule(${currentModuleIndex})">Cambiar</button>
            <button type="button" class="btn btn-danger btn-sm" onclick="removeActivityModule(${currentModuleIndex})">Eliminar</button>
        </div>
    `;
    
    modulesContainer.appendChild(moduleDiv);
}

function removeModule(moduleIndex) {
    const moduleDiv = document.querySelector(`[data-module-index="${moduleIndex}"]`);
    if (moduleDiv) {
        moduleDiv.remove();
    }
}

function removeActivityModule(moduleIndex) {
    const selectedFileDiv = document.querySelector(`.selected-file[data-module="${moduleIndex}"]`);
    if (selectedFileDiv) {
        selectedFileDiv.innerHTML = '<span class="no-file">No se ha seleccionado ningún archivo</span>';
        selectedFileDiv.dataset.filename = '';
        selectedFileDiv.dataset.category = '';
    }
}

function changeModule(moduleIndex) {
    openFileSelector(moduleIndex);
}

async function openFileSelector(moduleIndex) {
    currentActivityElement = document.querySelector(`.selected-file[data-module="${moduleIndex}"]`);
    
    // Cargar archivos REALES desde la API
    try {
        showLoading('Cargando archivos...');
        
        const files = await apiRequest('/files/list');
        
        hideLoading();
        
        if (files.length === 0) {
            fileSelectorList.innerHTML = `
                <div class="empty-state">
                    <p>No hay archivos en tu biblioteca</p>
                    <p style="font-size: 12px; margin-top: 10px;">Sube archivos en la sección "ARCHIVOS" primero</p>
                </div>
            `;
        } else {
            fileSelectorList.innerHTML = files.map(file => {
                const icon = file.category === 'procesado' ? '📄' : getFileIcon(file.type);
                return `
                    <div class="file-selector-item" onclick="selectFile('${escapeHtml(file.name)}', '${file.category}')">
                        <span class="file-icon">${icon}</span>
                        <div class="file-selector-info">
                            <span class="file-selector-name">${escapeHtml(file.name)}</span>
                            <span class="file-selector-type">${file.type} • ${file.size}</span>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        fileSelectorModal.classList.add('active');
    } catch (error) {
        hideLoading();
        showMessage('Error cargando archivos: ' + error.message, 'error');
    }
}

function getFileIcon(fileType) {
    const type = fileType.toLowerCase();
    if (type.includes('pdf')) return '📄';
    if (type.includes('word')) return '📝';
    if (type.includes('excel')) return '📊';
    if (type.includes('imagen')) return '🖼️';
    if (type.includes('txt')) return '📄';
    return '📎';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function selectFile(filename, category) {
    if (currentActivityElement) {
        const icon = category === 'procesado' ? '📄' : '📁';
        currentActivityElement.innerHTML = `
            <span class="selected-file-icon">${icon}</span>
            <span class="selected-file-name">${escapeHtml(filename)}</span>
        `;
        currentActivityElement.dataset.filename = filename;
        currentActivityElement.dataset.category = category;
    }
    fileSelectorModal.classList.remove('active');
}

function savePlan() {
    const nombre = planNombreInput.value.trim();
    
    if (!nombre) {
        showMessage('Por favor ingresa un nombre para el plan', 'error');
        return;
    }
    
    const modules = Array.from(modulesContainer.querySelectorAll('.module-item'));
    
    if (modules.length === 0) {
        showMessage('Debes agregar al menos un módulo', 'error');
        return;
    }
    
    const modulos = modules.map(moduleDiv => {
        const objetivo = moduleDiv.querySelector('.module-objetivo').value.trim();
        const selectedFileDiv = moduleDiv.querySelector('.selected-file');
        const filename = selectedFileDiv.dataset.filename || '';
        const category = selectedFileDiv.dataset.category || '';
        
        return {
            objetivo: objetivo || 'Sin objetivo definido',
            actividad: filename || 'Sin archivo seleccionado',
            category: category
        };
    });
    
    const plan = {
        nombre,
        modulos,
        fecha: new Date().toISOString(),
        usuario: currentUser
    };
    
    planesDeEstudio.push(plan);
    savePlanesToStorage();
    
    showMessage('Plan de estudio guardado correctamente', 'success');
    closePlanModalFn();
    
    // Ir a la última página donde está el nuevo plan
    const totalPages = Math.ceil(planesDeEstudio.length / itemsPerPage);
    currentPage = totalPages;
    
    displayPlanes();
}

function deletePlan(index) {
    showModal(
        '¿Estás seguro de que quieres eliminar este plan de estudio?',
        () => {
            planesDeEstudio.splice(index, 1);
            savePlanesToStorage();
            
            // Ajustar página actual si es necesario
            const totalPages = Math.ceil(planesDeEstudio.length / itemsPerPage);
            if (currentPage > totalPages && totalPages > 0) {
                currentPage = totalPages;
            } else if (planesDeEstudio.length === 0) {
                currentPage = 1;
            }
            
            displayPlanes();
            showMessage('Plan eliminado correctamente', 'success');
        }
    );
}

// ===== FUNCIONES DE VISTA PREVIA =====

async function openFilePreview(category, filename) {
    try {
        showLoading('Cargando vista previa...');
        
        // Determinar tipo de archivo
        const ext = filename.split('.').pop().toLowerCase();
        
        // Mostrar modal
        previewModal.classList.add('active');
        previewFilename.textContent = filename;
        
        // Guardar archivo actual para descargar
        currentPreviewFile = { category, filename };
        
        // Limpiar contenedor
        previewContainer.innerHTML = '<div class="loading-preview"><div class="spinner"></div><p>Cargando...</p></div>';
        
        // Obtener el contenido
        const response = await fetch(`${API_BASE}/files/preview/${category}/${encodeURIComponent(filename)}`, {
            headers: {
                'Authorization': `Bearer ${currentToken}`
            }
        });
        
        if (!response.ok) {
            throw new Error('No se pudo cargar la vista previa');
        }
        
        // Limpiar contenedor nuevamente
        previewContainer.innerHTML = '';
        
        // Mostrar según tipo de archivo
        if (ext === 'pdf') {
            // PDF - usar iframe
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            
            previewContainer.classList.add('pdf-preview');
            previewContainer.innerHTML = `
                <iframe src="${url}" style="width: 100%; height: 100%; border: none;"></iframe>
            `;
        } else if (['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(ext)) {
            // Imagen
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            
            previewContainer.classList.add('image-preview');
            previewContainer.innerHTML = `
                <img src="${url}" style="max-width: 100%; max-height: 100%; object-fit: contain;" alt="${escapeHtml(filename)}">
            `;
            previewContainer.style.background = '#000';
        } else if (ext === 'txt') {
            // Texto
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
    
    // Event listeners Plan de Estudio
    createPlanBtn.addEventListener('click', openPlanModal);
    closePlanModal.addEventListener('click', closePlanModalFn);
    cancelPlanBtn.addEventListener('click', closePlanModalFn);
    savePlanBtn.addEventListener('click', savePlan);
    addModuleBtn.addEventListener('click', addModule);
    
    // Cerrar modal selector de archivos
    closeFileSelector.addEventListener('click', () => {
        fileSelectorModal.classList.remove('active');
    });
    
    // Cerrar modales al hacer clic fuera
    planModal.addEventListener('click', (e) => {
        if (e.target === planModal) {
            closePlanModalFn();
        }
    });
    
    fileSelectorModal.addEventListener('click', (e) => {
        if (e.target === fileSelectorModal) {
            fileSelectorModal.classList.remove('active');
        }
    });
    // Event listeners para vista previa
    closePreviewModal.addEventListener('click', () => {
        previewModal.classList.remove('active');
        previewContainer.innerHTML = '';
        previewContainer.className = 'preview-container'; // Reset classes
        previewContainer.style.background = ''; // Reset background
        currentPreviewFile = null;
    });

    downloadPreviewBtn.addEventListener('click', () => {
        if (currentPreviewFile) {
            downloadFileAction(currentPreviewFile.category, currentPreviewFile.filename);
        }
    });

    // Cerrar modal al hacer clic fuera
    previewModal.addEventListener('click', (e) => {
        if (e.target === previewModal) {
            previewModal.classList.remove('active');
            previewContainer.innerHTML = '';
            previewContainer.className = 'preview-container';
            previewContainer.style.background = '';
            currentPreviewFile = null;
        }
    });
}

// Hacer funciones globales para usar en onclick
window.confirmDeleteFile = confirmDeleteFile;
window.openFilePreview = openFilePreview;
window.downloadFileAction = downloadFileAction;
window.removeModule = removeModule;
window.removeActivityModule = removeActivityModule;
window.changeModule = changeModule;
window.openFileSelector = openFileSelector;
window.selectFile = selectFile;
window.deletePlan = deletePlan;
window.togglePlanCard = togglePlanCard;
window.changePage = changePage;