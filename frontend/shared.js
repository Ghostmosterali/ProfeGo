// ===== SHARED.JS - VERSIÃ"N CONSOLIDADA =====
// Este archivo contiene todas las funciones compartidas entre login-script.js y menu-script.js
// VersiÃ³n: 2.0 - Compatible con ambos contextos

// ===== VARIABLES GLOBALES =====
let currentUser = null;
let currentToken = null;
const API_BASE = '/api';
const SESSION_STORAGE_KEY = 'profego_session';
const SESSION_DURATION = 3600000; // 1 hora en milisegundos

// ===== GESTIÃ"N DE SESIÃ"N =====

/**
 * Guarda la sesiÃ³n del usuario en localStorage
 * @param {string} email - Email del usuario
 * @param {string} token - Token de autenticaciÃ³n
 */
function saveSession(email, token) {
    try {
        const sessionData = {
            email: email,
            token: token,
            timestamp: Date.now()
        };
        localStorage.setItem('userToken', token);
        localStorage.setItem('userEmail', email);
        localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessionData));
        
        // Actualizar variables globales
        currentUser = email;
        currentToken = token;
        
        console.log('SesiÃ³n guardada correctamente');
        return true;
    } catch (error) {
        console.error('Error guardando sesiÃ³n:', error);
        return false;
    }
}

/**
 * Carga la sesiÃ³n del usuario desde localStorage
 * @returns {boolean} - True si la sesiÃ³n es vÃ¡lida, false si no
 */
function loadSession() {
    try {
        // Intentar cargar con el nuevo formato
        const sessionStr = localStorage.getItem(SESSION_STORAGE_KEY);
        
        if (sessionStr) {
            const session = JSON.parse(sessionStr);
            
            // Verificar si la sesiÃ³n ha expirado
            if (Date.now() - session.timestamp > SESSION_DURATION) {
                console.log('SesiÃ³n expirada');
                clearSession();
                return false;
            }
            
            currentToken = session.token;
            currentUser = session.email;
            console.log('SesiÃ³n cargada desde formato nuevo');
            return true;
        }
        
        // Fallback: intentar cargar con el formato antiguo
        const token = localStorage.getItem('userToken');
        const email = localStorage.getItem('userEmail');
        
        if (token && email) {
            currentToken = token;
            currentUser = email;
            
            // Migrar al nuevo formato
            saveSession(email, token);
            console.log('SesiÃ³n migrada al nuevo formato');
            return true;
        }
        
        console.log('No hay sesiÃ³n guardada');
        return false;
    } catch (error) {
        console.error('Error cargando sesiÃ³n:', error);
        clearSession();
        return false;
    }
}

/**
 * Limpia la sesiÃ³n del usuario
 */
function clearSession() {
    try {
        localStorage.removeItem('userToken');
        localStorage.removeItem('userEmail');
        localStorage.removeItem(SESSION_STORAGE_KEY);
        currentUser = null;
        currentToken = null;
        console.log('SesiÃ³n limpiada correctamente');
    } catch (error) {
        console.error('Error limpiando sesiÃ³n:', error);
    }
}

/**
 * Valida si el token actual es vÃ¡lido
 * @param {string} token - Token a validar (opcional, usa currentToken si no se proporciona)
 * @returns {Promise<boolean>} - True si el token es vÃ¡lido
 */
async function validateSession(token = currentToken) {
    try {
        if (!token) {
            console.log('No hay token para validar');
            return false;
        }
        
        const response = await fetch(`${API_BASE}/user/storage-info`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const isValid = response.ok;
        console.log('ValidaciÃ³n de sesiÃ³n:', isValid ? 'VÃ¡lida' : 'InvÃ¡lida');
        return isValid;
    } catch (error) {
        console.error('Error validando sesiÃ³n:', error);
        return false;
    }
}

// ===== UTILIDADES DE UI =====

/**
 * Muestra un mensaje al usuario
 * @param {string} message - Mensaje a mostrar
 * @param {string} type - Tipo de mensaje: 'info', 'success', 'error', 'warning'
 */
function showMessage(message, type = 'info') {
    const authMessage = document.getElementById('auth-message');
    if (!authMessage) {
        console.warn('Elemento auth-message no encontrado, usando console');
        console.log(`[${type.toUpperCase()}] ${message}`);
        return;
    }
    
    authMessage.textContent = message;
    authMessage.className = `message ${type}`;
    authMessage.classList.remove('hidden');
    
    // Ocultar automÃ¡ticamente despuÃ©s de 5 segundos
    setTimeout(() => {
        authMessage.classList.add('hidden');
    }, 5000);
}

/**
 * Muestra el overlay de carga
 * @param {string} text - Texto a mostrar en el loading
 */
function showLoading(text = 'Cargando...') {
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');
    
    if (loadingText) {
        loadingText.textContent = text;
    }
    
    if (loadingOverlay) {
        loadingOverlay.classList.remove('hidden');
    } else {
        console.warn('Elemento loading-overlay no encontrado');
    }
}

/**
 * Oculta el overlay de carga
 */
function hideLoading() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.classList.add('hidden');
    }
}

/**
 * Muestra un modal de confirmaciÃ³n
 * @param {string} message - Mensaje a mostrar
 * @param {Function} onConfirm - FunciÃ³n a ejecutar si el usuario confirma
 * @param {Function} onCancel - FunciÃ³n a ejecutar si el usuario cancela (opcional)
 */
function showModal(message, onConfirm, onCancel = null) {
    const confirmModal = document.getElementById('confirm-modal');
    const confirmMessage = document.getElementById('confirm-message');
    const confirmYes = document.getElementById('confirm-yes');
    const confirmNo = document.getElementById('confirm-no');
    
    if (!confirmModal) {
        console.warn('Modal de confirmaciÃ³n no encontrado');
        // Fallback a confirm nativo
        if (confirm(message)) {
            onConfirm();
        } else if (onCancel) {
            onCancel();
        }
        return;
    }
    
    confirmMessage.textContent = message;
    confirmModal.classList.remove('hidden');
    
    // Limpiar eventos anteriores
    const newConfirmYes = confirmYes.cloneNode(true);
    const newConfirmNo = confirmNo.cloneNode(true);
    confirmYes.parentNode.replaceChild(newConfirmYes, confirmYes);
    confirmNo.parentNode.replaceChild(newConfirmNo, confirmNo);
    
    // Asignar nuevos eventos
    newConfirmYes.onclick = () => {
        confirmModal.classList.add('hidden');
        if (onConfirm) onConfirm();
    };
    
    newConfirmNo.onclick = () => {
        confirmModal.classList.add('hidden');
        if (onCancel) onCancel();
    };
}

// ===== FUNCIONES DE API =====

/**
 * Realiza una peticiÃ³n a la API
 * @param {string} endpoint - Endpoint de la API (ej: '/auth/login')
 * @param {Object} options - Opciones de fetch
 * @param {boolean} options.skipAuth - Si true, no incluye el token de autorizaciÃ³n
 * @returns {Promise<Object>} - Respuesta JSON de la API
 */
async function apiRequest(endpoint, options = {}) {
    try {
        const headers = {};
        
        // Agregar token de autorizaciÃ³n si existe y no se solicita omitir
        if (currentToken && !options.skipAuth) {
            headers['Authorization'] = `Bearer ${currentToken}`;
        } else if (!options.skipAuth && !currentToken) {
            throw new Error('No hay token de autorizaciÃ³n. Inicia sesiÃ³n nuevamente.');
        }
        
        // Agregar Content-Type para JSON
        if (options.body && typeof options.body === 'string') {
            headers['Content-Type'] = 'application/json';
        }
        
        // Combinar headers personalizados
        Object.assign(headers, options.headers || {});
        
        // Construir URL completa
        const url = `${API_BASE}${endpoint}`;
        
        console.log(`API Request: ${options.method || 'GET'} ${url}`);
        
        // Realizar peticiÃ³n
        const response = await fetch(url, {
            ...options,
            headers
        });
        
        // Manejar respuesta
        if (!response.ok) {
            let errorMessage = 'Error en la solicitud';
            
            try {
                const error = await response.json();
                errorMessage = error.detail || error.message || errorMessage;
            } catch (e) {
                errorMessage = `Error ${response.status}: ${response.statusText}`;
            }
            
            // Si es error 401, la sesiÃ³n expirÃ³
            if (response.status === 401) {
                console.warn('SesiÃ³n invÃ¡lida o expirada');
                clearSession();
                errorMessage = 'Tu sesiÃ³n ha expirado. Por favor inicia sesiÃ³n nuevamente.';
            }
            
            throw new Error(errorMessage);
        }
        
        // Parsear respuesta JSON
        const data = await response.json();
        console.log('API Response:', data);
        return data;
        
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ===== UTILIDADES ADICIONALES =====

/**
 * Formatea el tamaÃ±o de un archivo
 * @param {number} bytes - TamaÃ±o en bytes
 * @returns {string} - TamaÃ±o formateado
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Formatea una fecha
 * @param {string|Date} date - Fecha a formatear
 * @returns {string} - Fecha formateada
 */
function formatDate(date) {
    try {
        const d = new Date(date);
        return d.toLocaleDateString('es-MX', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (error) {
        console.error('Error formateando fecha:', error);
        return 'Fecha no disponible';
    }
}

/**
 * Escapa caracteres HTML para prevenir XSS
 * @param {string} text - Texto a escapar
 * @returns {string} - Texto escapado
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Valida un email
 * @param {string} email - Email a validar
 * @returns {boolean} - True si el email es vÃ¡lido
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Debounce function - limita la frecuencia de ejecuciÃ³n de una funciÃ³n
 * @param {Function} func - FunciÃ³n a ejecutar
 * @param {number} wait - Tiempo de espera en milisegundos
 * @returns {Function} - FunciÃ³n debounced
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ===== INICIALIZACIÃ"N Y VALIDACIÃ"N =====

/**
 * Verifica el estado de la sesiÃ³n al cargar
 * Usa esta funciÃ³n en lugar de loadSession cuando necesites validar con el servidor
 * @returns {Promise<boolean>} - True si hay una sesiÃ³n vÃ¡lida
 */
async function checkSession() {
    try {
        // Intentar cargar sesiÃ³n local
        if (!loadSession()) {
            return false;
        }
        
        // Validar con el servidor
        const isValid = await validateSession();
        
        if (!isValid) {
            clearSession();
            return false;
        }
        
        return true;
    } catch (error) {
        console.error('Error verificando sesiÃ³n:', error);
        clearSession();
        return false;
    }
}

// ===== LOGGING Y DEBUG =====

/**
 * Sistema de logging mejorado
 */
const Logger = {
    enabled: true, // Cambiar a false en producciÃ³n
    
    log: function(message, data = null) {
        if (!this.enabled) return;
        console.log(`[ProfeGo] ${message}`, data || '');
    },
    
    error: function(message, error = null) {
        console.error(`[ProfeGo Error] ${message}`, error || '');
    },
    
    warn: function(message, data = null) {
        if (!this.enabled) return;
        console.warn(`[ProfeGo Warning] ${message}`, data || '');
    },
    
    info: function(message, data = null) {
        if (!this.enabled) return;
        console.info(`[ProfeGo Info] ${message}`, data || '');
    }
};

// ===== EXPORTAR FUNCIONES PARA USO GLOBAL =====
// Estas funciones estÃ¡n disponibles globalmente para login-script.js y menu-script.js

console.log('shared.js cargado correctamente - VersiÃ³n 2.0');
console.log('Funciones disponibles:', {
    session: ['saveSession', 'loadSession', 'clearSession', 'validateSession', 'checkSession'],
    ui: ['showMessage', 'showLoading', 'hideLoading', 'showModal'],
    api: ['apiRequest'],
    utilities: ['formatFileSize', 'formatDate', 'escapeHtml', 'isValidEmail', 'debounce'],
    logger: 'Logger'
});