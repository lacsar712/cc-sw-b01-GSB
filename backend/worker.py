import os
import time

import psycopg
from psycopg.rows import dict_row

from domain import judge

DSN = os.environ.get("DATABASE_URL", "postgresql://app:app@localhost:54395/spectrum")
# 待处理宽限：入队/重投后留出改实测的窗口，过期才会被领取
GRACE_SECONDS = float(os.environ.get("CLAIM_GRACE_SECONDS", "5"))
# 领取后稍作停留，让「领取中」状态对外可见
CLAIM_HOLD_SECONDS = float(os.environ.get("CLAIM_HOLD_SECONDS", "0.8"))


def connect():
    return psycopg.connect(DSN, row_factory=dict_row)


def claim_one(conn):
    row = conn.execute(
        """
        SELECT id, nominal_nm, measured_nm FROM jobs
        WHERE status='pending' AND updated_at <= now() - make_interval(secs => %s)
        ORDER BY id
        FOR UPDATE SKIP LOCKED
        LIMIT 1
        """,
        (GRACE_SECONDS,),
    ).fetchone()
    if not row:
        return None
    conn.execute(
        "UPDATE jobs SET status='claimed', updated_at=now() WHERE id=%s",
        (row["id"],),
    )
    conn.commit()
    return dict(row)


def finalize(conn, job):
    verdict, reason = judge(job["nominal_nm"], job["measured_nm"])
    conn.execute(
        "UPDATE jobs SET status='done', verdict=%s, reason=%s, updated_at=now() WHERE id=%s",
        (verdict, reason, job["id"]),
    )
    conn.commit()
    return job["id"]


def main():
    while True:
        try:
            with connect() as conn:
                job = claim_one(conn)
                if job is None:
                    time.sleep(0.4)
                    continue
                time.sleep(CLAIM_HOLD_SECONDS)
                finalize(conn, job)
        except Exception as exc:
            print("worker err", exc, flush=True)
            time.sleep(0.4)


if __name__ == "__main__":
    main()
