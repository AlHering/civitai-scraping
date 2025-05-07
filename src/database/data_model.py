# -*- coding: utf-8 -*-
"""
****************************************************
*             Modular Voice Assistant              *
*            (c) 2024 Alexander Hering             *
****************************************************
"""
from sqlalchemy.orm import declarative_base
from sqlalchemy import Engine, Column, String, JSON, Integer, DateTime, func, Boolean
from sqlalchemy_utils import UUIDType
from uuid import uuid4


def populate_data_infrastructure(engine: Engine, schema: str, model: dict) -> None:
    """
    Function for populating data infrastructure.
    :param engine: Database engine.
    :param schema: Schema for tables.
    :param model: Model dictionary for holding data classes.
    """
    schema = str(schema)
    if schema and not schema.endswith("."):
        schema += "."
    base = declarative_base()

    class Model(base):
        """
        Log class, representing a model entry.
        """
        __tablename__ = f"{schema}model"
        __table_args__ = {
            "comment": "Model table.", "extend_existing": True}

        uuid = Column(UUIDType(binary=False), primary_key=True, unique=True, nullable=False, default=uuid4,
                    comment="UUID of the entry.")
        url = Column(String, unique=True, nullable=False,
                     comment="URL of the entry.")
        source = Column(String,
                     comment="Source of the entry.")
        data = Column(JSON,
                      comment="Metadata entry config.")
        
        state = Column(String,
                     comment="State of the entry (full, extracted, ...).")
        created = Column(DateTime, server_default=func.now(),
                         comment="Timestamp of creation.")
        updated = Column(DateTime, server_default=func.now(), server_onupdate=func.now(),
                         comment="Timestamp of last update.")
        inactive = Column(Boolean, nullable=False, default=False,
                          comment="Inactivity flag.")
    
    class ModelVersion(base):
        """
        Log class, representing a model version entry.
        """
        __tablename__ = f"{schema}modelversion"
        __table_args__ = {
            "comment": "Model version table.", "extend_existing": True}

        uuid = Column(UUIDType(binary=False), primary_key=True, unique=True, nullable=False, default=uuid4,
                    comment="UUID of the entry.")
        url = Column(String, unique=True, nullable=False,
                     comment="URL of the entry.")
        source = Column(String,
                     comment="Source of the entry.")
        data = Column(JSON,
                      comment="Metadata entry config.")
        
        state = Column(String,
                     comment="State of the entry (full, extracted, ...).")
        created = Column(DateTime, server_default=func.now(),
                         comment="Timestamp of creation.")
        updated = Column(DateTime, server_default=func.now(), server_onupdate=func.now(),
                         comment="Timestamp of last update.")
        inactive = Column(Boolean, nullable=False, default=False,
                          comment="Inactivity flag.")

    class Image(base):
        """
        Log class, representing an image entry.
        """
        __tablename__ = f"{schema}image"
        __table_args__ = {
            "comment": "Image table.", "extend_existing": True}

        id = Column(UUIDType(binary=False), primary_key=True, unique=True, nullable=False, default=uuid4,
                    comment="UUID of the entry.")
        url = Column(String, unique=True, nullable=False,
                     comment="URL of the entry.")
        source = Column(String,
                     comment="Source of the entry.")
        data = Column(JSON,
                      comment="Metadata entry config.")
        path = Column(String,
                     comment="Path of the image file.")
        
        state = Column(String,
                     comment="State of the entry (full, extracted, ...).")
        created = Column(DateTime, server_default=func.now(),
                         comment="Timestamp of creation.")
        updated = Column(DateTime, server_default=func.now(), server_onupdate=func.now(),
                         comment="Timestamp of last update.")
        inactive = Column(Boolean, nullable=False, default=False,
                          comment="Inactivity flag.")

    for dataclass in [Model, ModelVersion, Image]:
        model[dataclass.__tablename__.replace(schema, "")] = dataclass

    base.metadata.create_all(bind=engine)


def get_default_entries() -> dict:
    """
    Returns default entries.
    :return: Default entries.
    """
    return {}