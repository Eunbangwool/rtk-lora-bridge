#!/usr/bin/env python3
"""고객 관리 CLI

사용 예:
    python manage_customers.py add  --id AGMO_001 --pw password123
    python manage_customers.py list
    python manage_customers.py disable --id AGMO_001
    python manage_customers.py enable  --id AGMO_001
    python manage_customers.py remove  --id AGMO_001

DB 경로는 --db 로 지정 (기본 customers.db). server.py 와 동일 파일을 가리켜야 한다.
비밀번호는 sha256 해시로 저장된다 (server.py 의 인증과 동일 방식).
"""

import argparse
import hashlib
import sqlite3


def _connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            subscription TEXT DEFAULT 'active',
            created_at TEXT
        )
        """
    )
    conn.commit()
    return conn


def add_customer(db_path, customer_id, password):
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    with _connect(db_path) as conn:
        try:
            conn.execute(
                "INSERT INTO customers (id, password_hash, subscription, created_at) "
                "VALUES (?, ?, 'active', datetime('now'))",
                (customer_id, pw_hash),
            )
            conn.commit()
            print(f"고객 추가 완료: {customer_id}")
        except sqlite3.IntegrityError:
            print(f"이미 존재하는 고객: {customer_id} (변경하려면 set-pw 사용)")


def set_password(db_path, customer_id, password):
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    with _connect(db_path) as conn:
        cur = conn.execute(
            "UPDATE customers SET password_hash=? WHERE id=?", (pw_hash, customer_id)
        )
        conn.commit()
        print("비밀번호 변경 완료" if cur.rowcount else f"없는 고객: {customer_id}")


def set_subscription(db_path, customer_id, status):
    with _connect(db_path) as conn:
        cur = conn.execute(
            "UPDATE customers SET subscription=? WHERE id=?", (status, customer_id)
        )
        conn.commit()
        print(f"{customer_id} → {status}" if cur.rowcount else f"없는 고객: {customer_id}")


def remove_customer(db_path, customer_id):
    with _connect(db_path) as conn:
        cur = conn.execute("DELETE FROM customers WHERE id=?", (customer_id,))
        conn.commit()
        print("삭제 완료" if cur.rowcount else f"없는 고객: {customer_id}")


def list_customers(db_path):
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, subscription, created_at FROM customers ORDER BY created_at"
        ).fetchall()
    if not rows:
        print("(등록된 고객 없음)")
        return
    for r in rows:
        print(f"ID: {r[0]:<16} | 상태: {r[1]:<8} | 가입일: {r[2]}")


def main():
    parser = argparse.ArgumentParser(description="NTRIP 프록시 고객 관리")
    parser.add_argument(
        "command",
        choices=["add", "list", "remove", "disable", "enable", "set-pw"],
    )
    parser.add_argument("--id", help="고객 ID")
    parser.add_argument("--pw", help="고객 PW")
    parser.add_argument("--db", default="customers.db", help="SQLite DB 경로")
    args = parser.parse_args()

    if args.command == "add":
        if not args.id or not args.pw:
            parser.error("add 는 --id 와 --pw 가 필요합니다")
        add_customer(args.db, args.id, args.pw)
    elif args.command == "set-pw":
        if not args.id or not args.pw:
            parser.error("set-pw 는 --id 와 --pw 가 필요합니다")
        set_password(args.db, args.id, args.pw)
    elif args.command == "list":
        list_customers(args.db)
    elif args.command == "remove":
        if not args.id:
            parser.error("remove 는 --id 가 필요합니다")
        remove_customer(args.db, args.id)
    elif args.command == "disable":
        if not args.id:
            parser.error("disable 는 --id 가 필요합니다")
        set_subscription(args.db, args.id, "expired")
    elif args.command == "enable":
        if not args.id:
            parser.error("enable 는 --id 가 필요합니다")
        set_subscription(args.db, args.id, "active")


if __name__ == "__main__":
    main()
