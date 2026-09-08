import sqlalchemy as sa


def sync_db_columns(db):
    """
    Ensures that newly defined columns on SQLAlchemy models are automatically
    added to existing database tables if they are missing (for SQLite and PostgreSQL).
    """
    try:
        inspector = sa.inspect(db.engine)
        with db.engine.connect() as conn:
            for table_name, table in db.Model.metadata.tables.items():
                if not inspector.has_table(table_name):
                    continue
                existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
                for col in table.columns:
                    if col.name not in existing_cols:
                        col_type = col.type.compile(db.engine.dialect)
                        sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{col.name}" {col_type}'
                        try:
                            conn.execute(sa.text(sql))
                            conn.commit()
                            print(f"[schema_sync] Added column {col.name} to {table_name}", flush=True)
                        except Exception as col_err:
                            print(f"[schema_sync] Note: could not add {col.name} to {table_name}: {col_err}", flush=True)
    except Exception as err:
        print(f"[schema_sync] Schema sync check encountered: {err}", flush=True)


if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        sync_db_columns(db)
    print("Schema sync finished.")
