// ===== SCRIPT PARA LOGIN.HTML =====

// ===== ELEMENTOS DEL DOM =====
const authForm = document.getElementById('auth-form');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const loginBtn = document.getElementById('login-btn');
const registerBtn = document.getElementById('register-btn');

// ===== VERIFICAR SI YA HAY SESIÓN ACTIVA =====
document.addEventListener('DOMContentLoaded', function() {
    // Si ya hay sesión activa, redirigir a menu
    if (loadSession()) {
        window.location.href = 'menu.html';
        return;
    }
    
    // Configurar event listeners
    setupEventListeners();
});

// ===== FUNCIONES DE AUTENTICACIÓN =====
async function login(email, password) {
    try {
        showLoading('Iniciando sesión...');
        
        const response = await apiRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
            skipAuth: true
        });
        
        // Guardar sesión en localStorage
        saveSession(response.email, response.token);
        
        showMessage(response.message, 'success');
        
        // Redirigir a menu.html después de 500ms
        setTimeout(() => {
            window.location.href = 'menu.html';
        }, 500);
        
    } catch (error) {
        showMessage(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function register(email, password) {
    try {
        showLoading('Registrando usuario...');
        
        const response = await apiRequest('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
            skipAuth: true
        });
        
        showMessage(response.message + ' - Ahora puedes iniciar sesión', 'success');
        
    } catch (error) {
        showMessage(error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ===== EVENT LISTENERS =====
function setupEventListeners() {
    authForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const email = emailInput.value.trim();
        const password = passwordInput.value;
        
        if (!email || !password) {
            showMessage('Por favor completa todos los campos', 'error');
            return;
        }
        
        login(email, password);
    });
    
    registerBtn.addEventListener('click', function(e) {
        e.preventDefault();
        const email = emailInput.value.trim();
        const password = passwordInput.value;
        
        if (!email || !password) {
            showMessage('Por favor completa todos los campos', 'error');
            return;
        }
        
        register(email, password);
    });
}

// Elementos del DOM
        const overlay = document.getElementById('modal-overlay');
        const termsModal = document.getElementById('terms-modal');
        const privacyModal = document.getElementById('privacy-modal');
        
        const openTermsBtn = document.getElementById('open-terms');
        const openPrivacyBtn = document.getElementById('open-privacy');
        
        const closeTermsBtn = document.getElementById('close-terms');
        const closePrivacyBtn = document.getElementById('close-privacy');

        // Función para abrir modal
        function openModal(modal) {
            overlay.classList.add('active');
            modal.classList.add('active');
            document.body.style.overflow = 'hidden'; // Prevenir scroll en la página
        }

        // Función para cerrar modal
        function closeModal(modal) {
            overlay.classList.remove('active');
            modal.classList.remove('active');
            document.body.style.overflow = ''; // Restaurar scroll
        }

        // Event Listeners - Abrir modales
        openTermsBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openModal(termsModal);
        });

        openPrivacyBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openModal(privacyModal);
        });

        // Event Listeners - Cerrar modales
        closeTermsBtn.addEventListener('click', () => {
            closeModal(termsModal);
        });

        closePrivacyBtn.addEventListener('click', () => {
            closeModal(privacyModal);
        });

        // Cerrar al hacer clic en el overlay
        overlay.addEventListener('click', () => {
            closeModal(termsModal);
            closeModal(privacyModal);
        });

        // Cerrar con la tecla ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeModal(termsModal);
                closeModal(privacyModal);
            }
        });