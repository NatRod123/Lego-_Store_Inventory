# LEGO Store - Gestor de Inventario

Proyecto de control de inventarios para sets de LEGO que conecta un frontend web dinámico con una API en FastAPI y una base de datos en la nube en MongoDB Atlas.

# ¿Qué hace este proyecto?

* Gestión completa de productos (CRUD): Puedes agregar nuevos sets, consultar el catálogo actual, actualizar datos (precio, stock, categoría) y eliminar productos.
* Proyección de stock: Un módulo que calcula de forma automática la demanda estimada a 6 meses, las piezas a reabastecer y el valor total proyectado de las ventas según el stock actual.
* Base de datos en la nube: Todo se guarda en tiempo real en MongoDB Atlas.
* Documentación automática: Incluye la interfaz interactiva de Swagger UI para probar las rutas directamente.

# Características Principales

* CRUD Completo de Inventario:
    * Crear: Alta de nuevos sets LEGO con número de set, nombre, categoría, precio y stock.
    * Consultar: Listado dinámico de productos y búsqueda individual.
    * Actualizar: Edición parcial o total de datos de los sets
    registrados.
    * Eliminar: Borrado seguro de registros con confirmación previa.
* Módulo de Proyección Asíncrona: Cálculo dinámico de demanda estimada a 6 meses, sugerencia de reabastecimiento, estimación de ingresos y estado del stock.
* Persistencia en la Nube: Conexión directa a MongoDB Atlas mediante driver asíncrono (`Motor` / `AsyncMongoClient`).
* Documentación Interactiva: Integración nativa con OpenAPI y Swagger UI.

# Tecnologías utilizadas

Backend: Python 3.13, FastAPI, Pydantic v2, Motor / AsyncMongoClient, Uvicorn.
Frontend: HTML5, JavaScript (Fetch API), Tailwind CSS, FontAwesome.
Base de datos: MongoDB Atlas (NoSQL).

# Estructura de carpetas

```text
lego_store_inventory/
|-- static/
│   |-- index.html        # Interfaz gráfica
│   |__ lego_head.png     # Logo/icono del sistema
|-- .env                  # Credenciales de conexión (MongoDB)
|-- .gitignore            # Archivos excluidos de Git
|-- main.py               # API y rutas con FastAPI
|-- README.md             # Documentación
|-- requirements.txt      # Dependencias del proyecto

