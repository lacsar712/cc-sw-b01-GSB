import os
import time
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.rows import dict_row

from domain import judge

DSN = os.environ.get("DATABASE_URL", "postgresql://app:app@localhost:54395/spectrum")

# 待处理任务至少排队这么久才会被领取，给校准员留出改实测重投的窗口
MIN_PENDING_SECONDS = float(os.environ.get("WORKER_MIN_PENDING_SECONDS", "12"))
# 领取中（processing）停留时长，便于观察「领取中不可改」
PROCESS_SECONDS = float(os.environ.get("WORKER_PROCESS_SECONDS", "2"))
IDLE_SECONDS = float(os.environ.get("WORKER_IDLE_SECONDS", "1"))


def connect():
    return psycopg.connect(DSN, row_factory=dict_row)


def claim_one(conn):
    threshold = datetime.now(timezone.utc) - timedelta(seconds=MIN_PENDING_SECONDS)
    row = conn.execute(
        """
        SELECT id FROM jobs
        WHERE status='pending' AND created_at < %s
        ORDER BY id
        FOR UPDATE SKIP LOCKED
        LIMIT 1
        """,
        (threshold,),
    ).fetchone()
    if not row:
        return None
    conn.execute("UPDATE jobs SET status='processing' WHERE id=%s", (row["id"],))
    conn.commit()
    return row["id"]


def finish_one(conn):
    row = conn.execute(
        """
        SELECT id, nominal_nm, measured_nm FROM jobs
        WHERE status='processing'
        ORDER BY id
        FOR UPDATE SKIP LOCKED
        LIMIT 1
        """
    ).fetchone()
    if not row:
        return None
    verdict, reason = judge(row["nominal_nm"], row["measured_nm"])
    conn.execute(
        "UPDATE jobs SET status='done', verdict=%s, reason=%s WHERE id=%s",
        (verdict, reason, row["id"]),
    )
    conn.commit()
    return row["id"]


def main():
    while True:
        try:
            with connect() as conn:
                finish_one(conn)
                job_id = claim_one(conn)
            if job_id is not None:
                time.sleep(PROCESS_SECONDS)
        except Exception as exc:
            print("worker err", exc, flush=True)
        time.sleep(IDLE_SECONDS)


if __name__ == "__main__":
    main()
