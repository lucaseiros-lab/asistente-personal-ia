import sys
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Bajo pytest, cada test (y el portal síncrono de TestClient) puede correr en
# un event loop async distinto. Un pool con conexiones persistentes termina
# reutilizando conexiones de un loop ya cerrado. NullPool evita ese problema
# creando una conexión nueva por checkout, siempre atada al loop vigente.
# `PYTEST_CURRENT_TEST` recién existe una vez que un test arrancó, no al
# importar este módulo durante la colección; `sys.modules` sí está disponible
# en ese momento porque pytest ya se auto-importó antes de recolectar tests.
_engine_kwargs = {"poolclass": NullPool} if "pytest" in sys.modules else {"pool_pre_ping": True}

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
