-- A TASK_CANCEL remains pending until an online idle report confirms that
-- the device released its task. Preserve the distinct confirmed state.
ALTER TABLE device_commands DROP CONSTRAINT chk_device_command_status;
ALTER TABLE device_commands ADD CONSTRAINT chk_device_command_status CHECK (command_status IN
    ('PENDING', 'DELIVERY_FAILED', 'SENT', 'ACCEPTED', 'REJECTED', 'RUNNING',
     'SUCCEEDED', 'FAILED', 'TIMED_OUT', 'CANCELLED', 'CONFIRMED_IDLE'));
