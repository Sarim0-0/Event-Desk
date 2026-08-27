from uuid import UUID


class ReviewBookingNotFoundError(Exception):
    def __init__(self, booking_id: UUID) -> None:
        self.booking_id = booking_id
        super().__init__("The selected booking does not exist.")


class ReviewBookingOwnershipError(Exception):
    def __init__(self, booking_id: UUID) -> None:
        self.booking_id = booking_id
        super().__init__("You can only review an event using your own booking.")


class ReviewBookingNotEligibleError(Exception):
    def __init__(self, booking_id: UUID) -> None:
        self.booking_id = booking_id
        super().__init__("Only a confirmed booking can be reviewed.")


class ReviewEventNotFoundError(Exception):
    def __init__(self, event_id: UUID) -> None:
        self.event_id = event_id
        super().__init__("The event for this booking does not exist.")


class ReviewAlreadyExistsError(Exception):
    def __init__(self, booking_id: UUID) -> None:
        self.booking_id = booking_id
        super().__init__("A review already exists for this booking.")


class InvalidReviewInputError(Exception):
    def __init__(self) -> None:
        super().__init__("The review information is invalid.")


class ReviewTransactionError(Exception):
    def __init__(self) -> None:
        super().__init__("The review could not be saved.")
