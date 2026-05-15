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


class UserNotFoundError(Exception):
    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"User `{user_id}` not found.")


class LastAdminRoleRemovalError(Exception):
    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"Cannot remove the last admin role from user `{user_id}`.")


class PredictionNotFoundError(Exception):
    def __init__(self, prediction_id: UUID) -> None:
        super().__init__(f"Prediction `{prediction_id}` not found.")


class PredictionReviewNotAllowedError(Exception):
    def __init__(self, prediction_id: UUID, confidence: float, threshold: float) -> None:
        super().__init__(
            f"Prediction `{prediction_id}` confidence {confidence:.3f} "
            f"is not below review threshold {threshold:.3f}."
        )
