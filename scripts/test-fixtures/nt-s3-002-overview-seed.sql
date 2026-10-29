-- NT-S3-002 / TC-004.S1-S2: nine formal task statuses with distinct counts, five exception types,
-- replanning events, plus dry-run (template trial) tasks that MUST NOT be counted.
-- Run only inside a dedicated schema via scripts/nt-s3-002-seed-overview.py (refuses "public").
-- Idempotent: rows with task_code LIKE 'NT002-%' are removed first.
DELETE FROM task_events WHERE task_id IN (SELECT id FROM tasks WHERE task_code LIKE 'NT002-%');
DELETE FROM task_exceptions WHERE task_id IN (SELECT id FROM tasks WHERE task_code LIKE 'NT002-%');
DELETE FROM tasks WHERE task_code LIKE 'NT002-%';

-- formal tasks: status -> count  (PLANNING 1 ... MANUAL_TERMINATED 9)
INSERT INTO tasks (task_code, task_goal, task_family, status, created_by, is_dry_run)
SELECT 'NT002-F-' || s.status || '-' || g, 'fixture formal ' || s.status, 'GENERAL_GUIDANCE', s.status, 'fixture', FALSE
FROM (VALUES ('PLANNING',1),('SUPERVISING',2),('PENDING_ASSIGNMENT',3),('DOWNGRADING',4),('EXECUTING',5),
             ('COMPLETED',6),('FAILED',7),('PENDING_MANUAL',8),('MANUAL_TERMINATED',9)) AS s(status, n)
CROSS JOIN LATERAL generate_series(1, s.n) AS g;

-- dry-run tasks: must be excluded from every overview figure and from the task list
INSERT INTO tasks (task_code, task_goal, task_family, status, created_by, is_dry_run)
SELECT 'NT002-D-' || s.status || '-' || g, 'fixture dry-run ' || s.status, 'GENERAL_GUIDANCE', s.status, 'fixture', TRUE
FROM (VALUES ('COMPLETED',6),('EXECUTING',2),('PENDING_MANUAL',1)) AS s(status, n)
CROSS JOIN LATERAL generate_series(1, s.n) AS g;

-- five exception types on formal tasks (PENDING x3, PROCESSING, RESOLVED), one PENDING on a dry-run task
INSERT INTO task_exceptions (task_id, step_seq, exception_type, occurred_at, impact_conclusion, reason_code, exception_status)
SELECT t.id, 1, e.etype, now() - (e.mins || ' minutes')::interval, 'fixture impact ' || e.etype, 'FIXTURE_' || e.etype, e.est
FROM (VALUES ('AGENT_OFFLINE',50,'PENDING','NT002-F-EXECUTING-1'),
             ('CAPABILITY_GAP',40,'PENDING','NT002-F-FAILED-1'),
             ('EXECUTION_TIMEOUT',30,'PROCESSING','NT002-F-EXECUTING-2'),
             ('STEP_FAILED',20,'PENDING','NT002-F-PENDING_MANUAL-1'),
             ('REPLAN_FAILED',10,'RESOLVED','NT002-F-FAILED-2')) AS e(etype, mins, est, code)
JOIN tasks t ON t.task_code = e.code;
INSERT INTO task_exceptions (task_id, step_seq, exception_type, exception_status, reason_code)
SELECT id, 1, 'STEP_FAILED', 'PENDING', 'FIXTURE_DRYRUN_MUST_NOT_COUNT' FROM tasks WHERE task_code = 'NT002-D-EXECUTING-1';

-- replanning events: 3 formal (2 today, 1 eight days ago), 2 dry-run today (excluded)
INSERT INTO task_events (task_id, event_type, occurred_at, trigger, reason_code)
SELECT t.id, 'REPLANNING_TRIGGERED', now() - (v.hrs || ' hours')::interval, 'SYSTEM', 'FIXTURE'
FROM (VALUES ('NT002-F-EXECUTING-1',0),('NT002-F-EXECUTING-3',0),('NT002-F-FAILED-3',192),
             ('NT002-D-EXECUTING-1',0),('NT002-D-EXECUTING-2',0)) AS v(code, hrs)
JOIN tasks t ON t.task_code = v.code;
