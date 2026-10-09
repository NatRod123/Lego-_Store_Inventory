import asyncio
import os
import certifi
from contextlib import asynccontextmanager
from typing import List, Optional

from bson import ObjectId
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

# 1. Cargar Variables de Entorno
load_dotenv(override=True)

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "LegoStore")
COLL_PRODUCTOS = os.getenv("COLL_PRODUCTOS", "productos")

# 2. Variables Globales para MongoDB
client: Optional[AsyncMongoClient] = None
db = None
productos_coll = None

# 3. Gestor de Ciclo de Vida (Lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, db, productos_coll

    if not MONGODB_URI:
        print("ERROR: MONGODB_URI no encontrada en el archivo .env")
        yield
        return

    try:
        client = AsyncMongoClient(
            MONGODB_URI,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=5000,
        )
        await client.admin.command("ping")

        db = client[DB_NAME]
        productos_coll = db[COLL_PRODUCTOS]
        print(f"Conectado exitosamente a MongoDB Atlas - Base de Datos: {DB_NAME}")
    except Exception as e:
        print(f"Error al conectar a MongoDB: {type(e).__name__}: {e}")
        productos_coll = None
        if client:
            await client.close()
            client = None

    yield

    if client:
        await client.close()
        print("Conexión a MongoDB cerrada.")

# 4. Inicialización de FastAPI y Archivos Estáticos
app = FastAPI(
    title="LEGO STORE",
    description="API RESTful con FastAPI y MongoDB Atlas",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.exception_handler(PyMongoError)
async def mongo_error_handler(request: Request, exc: PyMongoError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": f"Error de MongoDB: {type(exc).__name__}: {exc}"},
    )

# 5. Modelos Pydantic
class ProductoBase(BaseModel):
    num_set: str = Field(..., description="Número identificador del set LEGO")
    nombre: str = Field(..., description="Nombre comercial del set")
    categoria: str = Field(..., description="Categoría o línea del producto")
    precio: float = Field(..., gt=0, description="Precio del set")
    stock: int = Field(..., ge=0, description="Cantidad en stock")

class ProductoCrear(ProductoBase):
    pass

class ProductoActualizar(BaseModel):
    num_set: Optional[str] = Field(None, description="Número identificador del set LEGO")
    nombre: Optional[str] = Field(None, description="Nombre comercial del set")
    categoria: Optional[str] = Field(None, description="Categoría o línea del producto")
    precio: Optional[float] = Field(None, gt=0, description="Precio del set")
    stock: Optional[int] = Field(None, ge=0, description="Cantidad en stock")

class ProductoRespuesta(ProductoBase):
    id: str = Field(..., alias="_id", description="ID asignado por MongoDB")

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }

class ProyeccionRespuesta(BaseModel):
    demanda_estimada_6meses: int
    sugerencia_reabastecimiento: int
    proyeccion_ventas_mxn: float
    status_analisis: str

# 6. Funciones Auxiliares
def mapear_producto(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

def get_coll():
    if productos_coll is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La conexión a MongoDB Atlas no está disponible.",
        )
    return productos_coll

# 7. Endpoints / Rutas
@app.get("/", response_class=HTMLResponse, tags=["Interfaz"])
async def obtener_interfaz():
    with open("static/index.html", "r", encoding="utf-8") as file:
        return file.read()

@app.get(
    "/productos",
    response_model=List[ProductoRespuesta],
    status_code=status.HTTP_200_OK,
    tags=["Productos"],
)
async def listar_productos(coll=Depends(get_coll)):
    return [mapear_producto(doc) async for doc in coll.find({})]

@app.post(
    "/productos",
    response_model=ProductoRespuesta,
    status_code=status.HTTP_201_CREATED,
    tags=["Productos"],
)
async def crear_producto(p: ProductoCrear, coll=Depends(get_coll)):
    existente = await coll.find_one({"num_set": p.num_set})
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El set LEGO '{p.num_set}' ya se encuentra registrado.",
        )

    doc = p.model_dump()
    resultado = await coll.insert_one(doc)
    doc["_id"] = str(resultado.inserted_id)
    return doc

@app.get(
    "/productos/{num_set}",
    response_model=ProductoRespuesta,
    status_code=status.HTTP_200_OK,
    tags=["Productos"],
)
async def obtener_producto(num_set: str, coll=Depends(get_coll)):
    doc = await coll.find_one({"num_set": num_set})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el set LEGO '{num_set}'.",
        )
    return mapear_producto(doc)

@app.put(
    "/productos/{id}",
    response_model=ProductoRespuesta,
    status_code=status.HTTP_200_OK,
    tags=["Productos"],
)
async def actualizar_producto(id: str, p: ProductoActualizar, coll=Depends(get_coll)):
    datos_actualizar = {k: v for k, v in p.model_dump().items() if v is not None}
    
    if not datos_actualizar:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se enviaron campos válidos para actualizar.",
        )

    filtro = {"_id": ObjectId(id)} if ObjectId.is_valid(id) else {"num_set": id}

    resultado = await coll.find_one_and_update(
        filtro,
        {"$set": datos_actualizar},
        return_document=True
    )

    if not resultado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el producto con el ID/num_set '{id}'.",
        )

    return mapear_producto(resultado)

@app.post(
    "/productos/{id}/proyeccion-stock",
    response_model=ProyeccionRespuesta,
    status_code=status.HTTP_200_OK,
    tags=["Proyecciones"],
)
async def calcular_proyeccion(id: str, coll=Depends(get_coll)):
    filtro = {"_id": ObjectId(id)} if ObjectId.is_valid(id) else {"num_set": id}
    doc = await coll.find_one(filtro)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el producto con el ID/num_set '{id}'.",
        )

    precio = float(doc.get("precio", 0))
    stock = int(doc.get("stock", 0))
    
    # Simulación de proyección
    demanda_estimada = stock * 2 + 10
    sugerencia_reabastecimiento = max(0, demanda_estimada - stock)
    proyeccion_ventas = demanda_estimada * precio
    status_analisis = "Stock Óptimo" if stock >= 10 else "Requiere Reabastecimiento"

    return {
        "demanda_estimada_6meses": demanda_estimada,
        "sugerencia_reabastecimiento": sugerencia_reabastecimiento,
        "proyeccion_ventas_mxn": proyeccion_ventas,
        "status_analisis": status_analisis,
    }

@app.delete(
    "/productos/{num_set}",
    status_code=status.HTTP_200_OK,
    tags=["Productos"],
)
async def eliminar_producto(num_set: str, coll=Depends(get_coll)):
    filtro = {"_id": ObjectId(num_set)} if ObjectId.is_valid(num_set) else {"num_set": num_set}
    resultado = await coll.delete_one(filtro)
    
    if resultado.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe el set LEGO '{num_set}'.",
        )
    return {"mensaje": f"El set LEGO '{num_set}' fue eliminado exitosamente."}