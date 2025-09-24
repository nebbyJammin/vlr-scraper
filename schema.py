from pg_connection.PostgresPool import PostgresPool
from psycopg2.extensions import connection
from logging_config import PG_LOGGER as LOGGER

db_pool = PostgresPool()

try:
    conn: connection = db_pool.get_conn()
except Exception as e:
    raise RuntimeError("Could not acquire database connection") from e

try:
    with conn.cursor() as cur:
        # DROP TABLES
        cur.execute("""
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END
            $$;
        """)

        # Create Series Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS series (
                id SERIAL,
                vlr_id INT NOT NULL,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                status SMALLINT NOT NULL,

                CONSTRAINT series_pk_id PRIMARY KEY (id),
                CONSTRAINT series_unique_vlr_id UNIQUE (vlr_id)
            )
        """)

        # Create Event Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL,
                vlr_id INT NOT NULL,
                status SMALLINT NOT NULL,
                series_id INT NOT NULL,
                region VARCHAR(5),
                location_long VARCHAR(50),
                tags TEXT[] NOT NULL,
                prize TEXT NOT NULL,
                date_str TEXT,
                date_start DATE,
                date_end DATE,
                thumbnail TEXT,

                CONSTRAINT events_pk_id PRIMARY KEY (id),
                CONSTRAINT events_unique_vlr_id UNIQUE (vlr_id),
                CONSTRAINT events_fk_series_id FOREIGN KEY (series_id) REFERENCES series(id)
            )
        """)
    
    try:
        conn.commit()
    except Exception as e:
        conn.rollback()
        LOGGER.error("Failed to reset schema.", exc_info=e)
        raise

    LOGGER.debug("Successfully created schema.")
finally:
    db_pool.put_conn(conn)