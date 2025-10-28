web_frontend — Landing y login (React + Vite)
===========================================

Este directorio contiene la landing (Home) y la página de login usadas por la plataforma ECG.
La landing que se ve en `/` está implementada en `src/Home.jsx` y usa el componente `src/Hero.jsx`.

Resumen rápido
- `/` → Landing (Home)
- `/login` → Página de login (Login.jsx)
- `/redirect` → Puente que reenvía el token a las apps Streamlit

Requisitos
- Node.js 16+ / 18+ recomendado
- npm o pnpm

Instalación y ejecución (desarrollo)

1. Instala dependencias:

```bash
cd web_frontend
npm install
```

2. Inicia servidor de desarrollo (Vite):

```bash
npm run dev
```

Por defecto Vite sirve la app en `http://localhost:5173`. Si usas Docker Compose en modo `dev`, la configuración del proyecto puede mapear otro puerto (p. ej. 13000) — revisa `docker-compose.yml` si corres via Docker.

Variables de entorno (Vite)
--------------------------------
Puedes configurar estas variables mediante `.env` o pasando `VITE_*` al build:

- `VITE_API_BASE` — URL base del backend (ej. `http://localhost:8000`)
- `VITE_STREAMLIT_URL` — URL base de Streamlit (ej. `http://localhost:8501`)
- `VITE_ADMIN_EMAIL` — correo del administrador (usado en el panel de "Registrarse")
- `VITE_ADMIN_WHATSAPP` — número del admin (ej. `+50583797821`)

Estructura relevante
- `src/Home.jsx` — Landing (encabezado, Hero y CTA a /login)
- `src/Hero.jsx` — componente visual animado usado en la landing
- `src/Login.jsx` — formulario de login, solicitud de acceso y redirección a Streamlit
- `src/RedirectToStreamlit.jsx` — componente que reenvía el JWT a la app Streamlit

Construir para producción

```bash
cd web_frontend
npm run build
# para previsualizar localmente
npm run preview
```

Si vas a desplegar con Docker/Nginx usa la imagen producida por `npm run build` y configura el servidor web para servir la carpeta `dist`.

Rutas y comportamiento UX
- Al abrir `/` verás la landing con un botón "Ingresar" que lleva a `/login`.
- `/login` es la fuente de verdad para autenticación. Después de autenticar, la app redirige a `/redirect?target=doctor&token=...` que reenvía el token a la app Streamlit correspondiente.

Consejos y solución de problemas
- Si la app no carga JS: abre la consola del navegador para ver errores de Vite (módulos no encontrados o import.meta.env faltantes).
- Si no llega al backend: revisa `VITE_API_BASE` y que el backend (FastAPI) esté corriendo y accesible desde el navegador.
- Para desarrollo local con HTTPS o dominios personalizados, configura Vite (ver `vite.config.js`).

Notas
- La landing es deliberadamente mínima y apunta al flujo de autenticación. Si quieres añadir secciones (Características, Equipo, Contacto), puedo crear componentes adicionales y actualizarlos en la landing.
