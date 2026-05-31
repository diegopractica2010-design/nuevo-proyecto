# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Radar de Precios
# Build with: pyinstaller radar_precios.spec

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

ROOT = Path(SPECPATH)

# Collect all submodules for packages that use dynamic imports
celery_hidden = collect_submodules('celery')
kombu_hidden = collect_submodules('kombu')
billiard_hidden = collect_submodules('billiard')

# Include frontend static files if they exist
datas = []
frontend_out = ROOT / 'frontend' / 'out'
frontend_public = ROOT / 'frontend' / 'public'
if frontend_out.exists():
    datas.append((str(frontend_out), 'frontend/out'))
if frontend_public.exists():
    datas.append((str(frontend_public), 'frontend/public'))

# Include .env if present
env_file = ROOT / '.env'
if env_file.exists():
    datas.append((str(env_file), '.'))

block_cipher = None

a = Analysis(
    ['launcher.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # uvicorn — uses dynamic imports internally
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.protocols.websockets.wsproto_impl',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        # h11 (HTTP/1.1 parser)
        'h11',
        'h11._readers',
        'h11._writers',
        'h11._events',
        # anyio async backend
        'anyio',
        'anyio._backends._asyncio',
        'anyio._backends._trio',
        # FastAPI / Starlette
        'fastapi',
        'fastapi.middleware',
        'fastapi.middleware.cors',
        'fastapi.staticfiles',
        'fastapi.responses',
        'fastapi.routing',
        'fastapi.encoders',
        'fastapi.exceptions',
        'fastapi.security',
        'fastapi.security.oauth2',
        'fastapi.security.http',
        'starlette',
        'starlette.middleware',
        'starlette.middleware.cors',
        'starlette.middleware.base',
        'starlette.staticfiles',
        'starlette.routing',
        'starlette.responses',
        'starlette.requests',
        'starlette.background',
        'starlette.datastructures',
        'starlette.exceptions',
        'starlette.types',
        'starlette.concurrency',
        # Pydantic v2
        'pydantic',
        'pydantic_settings',
        'pydantic_core',
        'pydantic._internal',
        'pydantic._internal._generate_schema',
        'pydantic._internal._config',
        # SQLAlchemy
        'sqlalchemy',
        'sqlalchemy.dialects',
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.dialects.sqlite.pysqlite',
        'sqlalchemy.dialects.postgresql',
        'sqlalchemy.dialects.postgresql.psycopg2',
        'sqlalchemy.pool',
        'sqlalchemy.orm',
        'sqlalchemy.orm.session',
        'sqlalchemy.engine',
        'sqlalchemy.sql',
        'sqlalchemy.sql.expression',
        'sqlalchemy.ext.asyncio',
        # passlib
        'passlib',
        'passlib.context',
        'passlib.handlers',
        'passlib.handlers.bcrypt',
        'passlib.handlers.sha2_crypt',
        'passlib.handlers.pbkdf2',
        'passlib.utils',
        'passlib.utils.binary',
        'passlib.utils.decor',
        'passlib.crypto',
        'passlib.crypto.digest',
        # bcrypt
        'bcrypt',
        # cryptography / python-jose
        'cryptography',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.asymmetric',
        'cryptography.hazmat.primitives.ciphers',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.backends.openssl',
        'jose',
        'jose.jwt',
        'jose.jws',
        'jose.backends',
        # redis
        'redis',
        'redis.client',
        'redis.connection',
        'redis.exceptions',
        'redis.asyncio',
        'hiredis',
        # celery / kombu / billiard — collected via collect_submodules above
        *celery_hidden,
        *kombu_hidden,
        *billiard_hidden,
        # requests + BeautifulSoup
        'requests',
        'requests.adapters',
        'requests.auth',
        'requests.cookies',
        'requests.exceptions',
        'bs4',
        'bs4.builder',
        'bs4.builder._htmlparser',
        'bs4.formatter',
        # monitoring
        'prometheus_client',
        'prometheus_client.metrics',
        'prometheus_client.registry',
        # sentry
        'sentry_sdk',
        'sentry_sdk.integrations',
        'sentry_sdk.integrations.fastapi',
        'sentry_sdk.integrations.sqlalchemy',
        # python-json-logger
        'pythonjsonlogger',
        'pythonjsonlogger.jsonlogger',
        # email / SMTP
        'email',
        'email.mime',
        'email.mime.text',
        'email.mime.multipart',
        'smtplib',
        # AWS / boto3
        'boto3',
        'botocore',
        'botocore.session',
        'botocore.loaders',
        # aiofiles
        'aiofiles',
        'aiofiles.os',
        'aiofiles.threadpool',
        # python-dotenv
        'dotenv',
        # python-multipart
        'multipart',
        # alembic
        'alembic',
        'alembic.runtime',
        'alembic.runtime.migration',
        # psycopg2 (optional - only needed if using PostgreSQL)
        'psycopg2',
        # backend — all modules listed to prevent missing import errors
        'backend',
        'backend.main',
        'backend.config',
        'backend.db',
        'backend.models',
        'backend.models_auth',
        'backend.models_baskets',
        'backend.parser',
        'backend.parser_monitor',
        'backend.scraper',
        'backend.scraper_jumbo',
        'backend.search_service',
        'backend.catalog_indexer',
        'backend.shopping_list_service',
        'backend.auth',
        'backend.alerts',
        'backend.backup',
        'backend.basket_service',
        'backend.celery_app',
        'backend.compliance',
        'backend.exception_handlers',
        'backend.health_check',
        'backend.logging_config',
        'backend.logging_setup',
        'backend.metrics',
        'backend.middleware',
        'backend.rate_limiter',
        'backend.repositories',
        'backend.request_context',
        'backend.security',
        'backend.status_dashboard',
        'backend.store_adapters',
        'backend.infrastructure',
        'backend.infrastructure.cache',
        'backend.infrastructure.cache.cache',
        'backend.infrastructure.db',
        'backend.infrastructure.db.models',
        'backend.infrastructure.db.repositories',
        'backend.infrastructure.scrapers',
        'backend.infrastructure.scrapers.base',
        'backend.infrastructure.scrapers.lider',
        'backend.infrastructure.scrapers.santa_isabel',
        'backend.infrastructure.scrapers.tottus',
        'backend.infrastructure.scrapers.unimarc',
        'backend.infrastructure.scrapers.acuenta',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy unused test/dev packages
        'pytest',
        'black',
        'flake8',
        'mypy',
        'IPython',
        'jupyter',
        'notebook',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'sklearn',
        'tensorflow',
        'torch',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RadarPrecios',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,      # Keep console window to show server logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='RadarPrecios',
)
