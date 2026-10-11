"""Review-path correction for the shared SQLite transaction experiment."""

from __future__ import annotations

from typing import Any, cast

from variants.store_layout import DeferredConnection, SingleFileExecutionService


class SingleFileExecutionServiceWithAtomicReview(SingleFileExecutionService):
    """Defer review state and audit commits until both operations succeed."""

    def review(self, approval_id: str, **kwargs: Any):
        connection = cast(DeferredConnection, self.approvals.connection)
        connection.defer_commits = True
        try:
            result = super(SingleFileExecutionService, self).review(
                approval_id, **kwargs
            )
            if result.status == "unresolved" or result.audit_error is not None:
                connection.rollback()
            else:
                connection.defer_commits = False
                connection.commit()
            return result
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.defer_commits = False