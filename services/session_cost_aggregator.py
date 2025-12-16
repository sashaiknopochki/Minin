"""Session Cost Aggregator Service - Phase 2

This service provides helper functions to aggregate LLM operation costs
at the session level. It updates the session's cost tracking fields in real-time
as translation and quiz operations are performed.

Usage:
    from services.session_cost_aggregator import add_translation_cost, add_quiz_cost

    # After a translation operation
    add_translation_cost(session_id, cost_usd)

    # After a quiz operation (question generation or answer evaluation)
    add_quiz_cost(session_id, cost_usd)
"""

from decimal import Decimal
from typing import Optional
from sqlalchemy.exc import SQLAlchemyError
from models import db
from models.session import Session
import logging

logger = logging.getLogger(__name__)


def add_translation_cost(session_id: str, cost_usd: Decimal) -> bool:
    """
    Add translation cost to a session's aggregated cost tracking.

    Updates:
    - total_translation_cost_usd: Increments by cost_usd
    - total_cost_usd: Increments by cost_usd
    - operations_count: Increments by 1

    Args:
        session_id: The UUID of the session
        cost_usd: The cost in USD (as Decimal for precision)

    Returns:
        True if successful, False otherwise

    Raises:
        ValueError: If session_id or cost_usd is invalid
    """
    if not session_id:
        raise ValueError("session_id is required")

    if cost_usd is None:
        raise ValueError("cost_usd is required")

    # Convert to Decimal if needed
    if not isinstance(cost_usd, Decimal):
        cost_usd = Decimal(str(cost_usd))

    try:
        session = Session.query.get(session_id)

        if not session:
            logger.warning(f"Session {session_id} not found, cannot add translation cost")
            return False

        # Initialize fields if they are None
        if session.total_translation_cost_usd is None:
            session.total_translation_cost_usd = Decimal('0.0')
        if session.total_cost_usd is None:
            session.total_cost_usd = Decimal('0.0')
        if session.operations_count is None:
            session.operations_count = 0

        # Update cost fields
        session.total_translation_cost_usd += cost_usd
        session.total_cost_usd += cost_usd
        session.operations_count += 1

        db.session.commit()

        logger.debug(
            f"Added translation cost ${cost_usd:.6f} to session {session_id}. "
            f"Total translation: ${session.total_translation_cost_usd:.6f}, "
            f"Total: ${session.total_cost_usd:.6f}, Ops: {session.operations_count}"
        )

        return True

    except SQLAlchemyError as e:
        logger.error(f"Database error adding translation cost to session {session_id}: {e}")
        db.session.rollback()
        return False
    except Exception as e:
        logger.error(f"Unexpected error adding translation cost to session {session_id}: {e}")
        db.session.rollback()
        return False


def add_quiz_cost(session_id: str, cost_usd: Decimal) -> bool:
    """
    Add quiz-related cost (question generation or answer evaluation) to session.

    Updates:
    - total_quiz_cost_usd: Increments by cost_usd
    - total_cost_usd: Increments by cost_usd
    - operations_count: Increments by 1

    Args:
        session_id: The UUID of the session
        cost_usd: The cost in USD (as Decimal for precision)

    Returns:
        True if successful, False otherwise

    Raises:
        ValueError: If session_id or cost_usd is invalid
    """
    if not session_id:
        raise ValueError("session_id is required")

    if cost_usd is None:
        raise ValueError("cost_usd is required")

    # Convert to Decimal if needed
    if not isinstance(cost_usd, Decimal):
        cost_usd = Decimal(str(cost_usd))

    try:
        session = Session.query.get(session_id)

        if not session:
            logger.warning(f"Session {session_id} not found, cannot add quiz cost")
            return False

        # Initialize fields if they are None
        if session.total_quiz_cost_usd is None:
            session.total_quiz_cost_usd = Decimal('0.0')
        if session.total_cost_usd is None:
            session.total_cost_usd = Decimal('0.0')
        if session.operations_count is None:
            session.operations_count = 0

        # Update cost fields
        session.total_quiz_cost_usd += cost_usd
        session.total_cost_usd += cost_usd
        session.operations_count += 1

        db.session.commit()

        logger.debug(
            f"Added quiz cost ${cost_usd:.6f} to session {session_id}. "
            f"Total quiz: ${session.total_quiz_cost_usd:.6f}, "
            f"Total: ${session.total_cost_usd:.6f}, Ops: {session.operations_count}"
        )

        return True

    except SQLAlchemyError as e:
        logger.error(f"Database error adding quiz cost to session {session_id}: {e}")
        db.session.rollback()
        return False
    except Exception as e:
        logger.error(f"Unexpected error adding quiz cost to session {session_id}: {e}")
        db.session.rollback()
        return False


def get_session_cost_summary(session_id: str) -> Optional[dict]:
    """
    Get a summary of all costs for a session.

    Args:
        session_id: The UUID of the session

    Returns:
        Dictionary with cost summary or None if session not found:
        {
            'session_id': str,
            'total_translation_cost_usd': Decimal,
            'total_quiz_cost_usd': Decimal,
            'total_cost_usd': Decimal,
            'operations_count': int,
            'started_at': datetime,
            'ended_at': datetime or None
        }
    """
    try:
        session = Session.query.get(session_id)

        if not session:
            logger.warning(f"Session {session_id} not found")
            return None

        return {
            'session_id': session.session_id,
            'total_translation_cost_usd': session.total_translation_cost_usd or Decimal('0.0'),
            'total_quiz_cost_usd': session.total_quiz_cost_usd or Decimal('0.0'),
            'total_cost_usd': session.total_cost_usd or Decimal('0.0'),
            'operations_count': session.operations_count or 0,
            'started_at': session.started_at,
            'ended_at': session.ended_at
        }

    except SQLAlchemyError as e:
        logger.error(f"Database error getting session cost summary for {session_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting session cost summary for {session_id}: {e}")
        return None