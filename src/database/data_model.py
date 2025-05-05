# -*- coding: utf-8 -*-
"""
****************************************************
*             Modular Voice Assistant              *
*            (c) 2024 Alexander Hering             *
****************************************************
"""
from sqlalchemy.orm import declarative_base
from sqlalchemy import Engine, Column, String, JSON, Integer, DateTime, func, Boolean


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
        Log class, representing an model entry.
        """
        __tablename__ = f"{schema}model"
        __table_args__ = {
            "comment": "Model table.", "extend_existing": True}

        id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False,
                    comment="ID of the entry.")
        url = Column(String, unique=True, nullable=False,
                     comment="URL of the entry.")
        source = Column(String,
                     comment="Source of the entry.")
        data = Column(JSON,
                      comment="Metadata entry config.")
        
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

        id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False,
                    comment="ID of the entry.")
        url = Column(String, unique=True, nullable=False,
                     comment="URL of the entry.")
        source = Column(String,
                     comment="Source of the entry.")
        data = Column(JSON,
                      comment="Metadata entry config.")
        file = Column(String,
                     comment="Name of the image file.")
        
        created = Column(DateTime, server_default=func.now(),
                         comment="Timestamp of creation.")
        updated = Column(DateTime, server_default=func.now(), server_onupdate=func.now(),
                         comment="Timestamp of last update.")
        inactive = Column(Boolean, nullable=False, default=False,
                          comment="Inactivity flag.")

    for dataclass in [Model, Image]:
        model[dataclass.__tablename__.replace(schema, "")] = dataclass

    base.metadata.create_all(bind=engine)


def get_default_entries() -> dict:
    """
    Returns default entries.
    :return: Default entries.
    """
    return {}