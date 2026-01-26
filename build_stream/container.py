# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from dependency_injector import containers, providers

from infra.db import (
    SqlAuditEventRepository,
    SqlIdempotencyRepository,
    SqlJobRepository,
    SqlStageRepository,
    get_db,
)
from infra.id_generator import UUIDv7Generator
from infra.repositories import (
    InMemoryAuditEventRepository,
    InMemoryIdempotencyRepository,
    InMemoryJobRepository,
    InMemoryStageRepository,
)
from orchestrator.jobs.use_cases import CreateJobUseCase


class DevContainer(containers.DeclarativeContainer):
    """Development profile container.
    
    Uses in-memory mock repositories for fast development and testing.
    No external dependencies (database, S3, etc.) required.
    
    Activated when ENV=dev (default).
    """
    
    wiring_config = containers.WiringConfiguration(
        modules=[
            "api.jobs.routes",
            "api.jobs.dependencies",
        ]
    )
    
    job_id_generator = providers.Singleton(UUIDv7Generator)
    
    job_repository = providers.Singleton(InMemoryJobRepository)
    
    stage_repository = providers.Singleton(InMemoryStageRepository)
    
    idempotency_repository = providers.Singleton(InMemoryIdempotencyRepository)
    
    audit_repository = providers.Singleton(InMemoryAuditEventRepository)
    
    create_job_use_case = providers.Factory(
        CreateJobUseCase,
        job_repo=job_repository,
        stage_repo=stage_repository,
        idempotency_repo=idempotency_repository,
        audit_repo=audit_repository,
        job_id_generator=job_id_generator,
    )


class ProdContainer(containers.DeclarativeContainer):
    """Production profile container.
    
    Uses PostgreSQL repositories with per-request database session scope.
    Requires DATABASE_URL environment variable to be configured.
    
    Activated when ENV=prod.
    """
    
    wiring_config = containers.WiringConfiguration(
        modules=[
            "api.jobs.routes",
            "api.jobs.dependencies",
        ]
    )
    
    job_id_generator = providers.Singleton(UUIDv7Generator)
    
    db_session = providers.Resource(get_db)
    
    job_repository = providers.Factory(
        SqlJobRepository,
        session=db_session,
    )
    
    stage_repository = providers.Factory(
        SqlStageRepository,
        session=db_session,
    )
    
    idempotency_repository = providers.Factory(
        SqlIdempotencyRepository,
        session=db_session,
    )
    
    audit_repository = providers.Factory(
        SqlAuditEventRepository,
        session=db_session,
    )
    
    create_job_use_case = providers.Factory(
        CreateJobUseCase,
        job_repo=job_repository,
        stage_repo=stage_repository,
        idempotency_repo=idempotency_repository,
        audit_repo=audit_repository,
        job_id_generator=job_id_generator,
    )


def get_container_class():
    """Select container class based on ENV environment variable.
    
    Returns:
        DevContainer if ENV=dev (default)
        ProdContainer if ENV=prod
    
    Usage:
        # Set environment variable before running
        ENV=prod python main.py
        
        # Or set in code before importing
        os.environ['ENV'] = 'prod'
        
        # Or set in shell
        export ENV=prod
        python main.py
        
        # Windows PowerShell
        $env:ENV = "prod"
        python main.py
        
        # Windows Command Prompt
        set ENV=prod
        python main.py
    """
    env = os.getenv("ENV", "dev").lower()
    
    if env == "prod":
        return ProdContainer
    
    return DevContainer


Container = get_container_class()
