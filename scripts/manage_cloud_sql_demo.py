"""Explicit admin seed and independent DB-enforced reader checks (never API startup)."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pymysql

TABLES = ("products", "inventory_snapshots", "purchase_orders", "suppliers")


def connect(args: argparse.Namespace, *, admin: bool = False):
    return pymysql.connect(
        host=args.host,
        unix_socket=args.socket,
        user=args.admin_user if admin else "decision_agent_readonly",
        password=os.environ["NEXUS_SQL_ADMIN_PASSWORD" if admin else "NEXUS_SQL_READER_PASSWORD"],
        database="enterprise_operations",
        charset="utf8mb4",
        connect_timeout=5,
        read_timeout=10,
        write_timeout=10,
        init_command="SET time_zone = '+08:00'",
        autocommit=False,
    )


def seed(args: argparse.Namespace) -> None:
    # One-time fresh database only. Existing tables cause a hard failure.
    with connect(args, admin=True) as connection, connection.cursor() as cursor:
        for name in ("01-schema.sql", "02-seed.sql"):
            source = (args.init_directory / name).read_text()
            for statement in source.split(";"):
                if statement.strip():
                    cursor.execute(statement)
        cursor.execute(
            "CREATE USER 'decision_agent_readonly'@'%%' IDENTIFIED BY %s",
            (os.environ["NEXUS_SQL_READER_PASSWORD"],),
        )
        for table in TABLES:
            cursor.execute(
                f"GRANT SELECT ON enterprise_operations.{table} TO 'decision_agent_readonly'@'%'"
            )
        connection.commit()


def verify(args: argparse.Namespace) -> None:
    with connect(args) as connection, connection.cursor() as cursor:
        for table in TABLES:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            assert cursor.fetchone()[0] > 0
        for sql in (
            "UPDATE products SET status=status WHERE 1=0",
            "DELETE FROM products WHERE 1=0",
            "INSERT INTO products SELECT * FROM products WHERE 1=0",
            "SELECT * FROM sales_orders LIMIT 0",
        ):
            try:
                cursor.execute(sql)
            except pymysql.err.OperationalError as exc:
                if exc.args[0] not in {1142, 1143}:
                    raise RuntimeError("unexpected database denial") from None
            else:
                connection.rollback()
                raise RuntimeError("reader grants are broader than approved demo scope")
        connection.rollback()
    print(
        json.dumps(
            {"status": "passed", "approved_tables": len(TABLES), "database_enforced_denials": 4}
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("seed", "verify"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--socket")
    parser.add_argument("--admin-user", default="root")
    parser.add_argument("--init-directory", type=Path, default=Path("docker/mysql/init"))
    args = parser.parse_args()
    try:
        (seed if args.operation == "seed" else verify)(args)
    except Exception:
        parser.exit(1, "cloud_sql_demo_operation_failed\n")


if __name__ == "__main__":
    main()
