from uuid import UUID


class ReplyReviewNotFoundError(Exception):
    def __init__(self, review_id: UUID) -> None:
        self.review_id = review_id
        super().__init__("The selected Review does not exist.")


class ReplyCreationForbiddenError(Exception):
    def __init__(self) -> None:
        super().__init__("You do not have permission to reply to this Review.")


class OrganizerReplyOwnershipError(Exception):
    def __init__(self, review_id: UUID) -> None:
        self.review_id = review_id
        super().__init__("You can only reply to Reviews for your own Events.")


class OrganizerReplyAlreadyExistsError(Exception):
    def __init__(self, review_id: UUID) -> None:
        self.review_id = review_id
        super().__init__("An Organizer Reply already exists for this Review.")


class AdminReplyAlreadyExistsError(Exception):
    def __init__(self, review_id: UUID) -> None:
        self.review_id = review_id
        super().__init__("An Admin Reply already exists for this Review.")


class UserAlreadyRepliedError(Exception):
    def __init__(self, review_id: UUID) -> None:
        self.review_id = review_id
        super().__init__("You have already replied to this Review.")


class InvalidReplyBodyError(Exception):
    def __init__(self) -> None:
        super().__init__("The Reply body cannot be empty.")


class ReplyTransactionError(Exception):
    def __init__(self) -> None:
        super().__init__("The Reply could not be saved.")
