from uuid import UUID


class BatchNotFoundError(Exception):
    def __init__(self, batch_id: UUID) -> None:
        super().__init__(f"Batch `{batch_id}` not found.")


class BatchAlreadyCompletedError(Exception):
    def __init__(self, batch_id: UUID) -> None:
        super().__init__(
            f"Batch `{batch_id}` is already completed "
            "but no prediction exists for idempotent replay."
        )
