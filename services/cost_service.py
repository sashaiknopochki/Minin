"""
Cost Calculation Service

Provides cost calculation for LLM operations based on token usage and model pricing.
Includes caching of pricing data and monthly cost aggregation queries.
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from functools import lru_cache
import logging

from models import db
from models.llm_pricing import LLMPricing
from models.session import Session
from sqlalchemy import func, and_

logger = logging.getLogger(__name__)


# Cache pricing data for 1 hour to reduce database queries
# Using a time-based approach with class-level cache
class PricingCache:
    """Simple time-based cache for pricing data"""
    def __init__(self, ttl_seconds=3600):  # 1 hour default
        self.cache = {}
        self.ttl_seconds = ttl_seconds

    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now(timezone.utc) - timestamp < timedelta(seconds=self.ttl_seconds):
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key, value):
        self.cache[key] = (value, datetime.now(timezone.utc))

    def clear(self):
        """Clear all cached entries"""
        self.cache.clear()


# Global pricing cache instance
_pricing_cache = PricingCache(ttl_seconds=3600)


class CostCalculationService:
    """Service for calculating LLM operation costs"""

    @staticmethod
    def calculate_cost(
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cached_tokens: int = 0
    ) -> Decimal:
        """
        Calculate cost for an LLM operation.

        Args:
            provider: Provider name ('openai', 'mistral')
            model: Model name ('gpt-4o-mini', 'mistral-small-latest')
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            cached_tokens: Number of cached input tokens (OpenAI only)

        Returns:
            Decimal: Cost in USD

        Example:
            >>> cost = CostCalculationService.calculate_cost(
            ...     'openai', 'gpt-4o-mini', 1000, 500, 200
            ... )
            >>> float(cost)  # Returns cost in USD
        """
        try:
            pricing = CostCalculationService._get_pricing(provider, model)

            if not pricing:
                logger.warning(f"No pricing found for {provider}/{model}, returning 0")
                return Decimal('0.0')

            # Calculate cost per token type
            # Regular input tokens
            regular_input_tokens = prompt_tokens - cached_tokens
            input_cost = (Decimal(str(regular_input_tokens)) * pricing['input_cost_per_1m']) / Decimal('1000000')

            # Cached input tokens (if applicable)
            cached_cost = Decimal('0.0')
            if cached_tokens > 0 and pricing['cached_input_cost_per_1m'] is not None:
                cached_cost = (Decimal(str(cached_tokens)) * pricing['cached_input_cost_per_1m']) / Decimal('1000000')

            # Output tokens
            output_cost = (Decimal(str(completion_tokens)) * pricing['output_cost_per_1m']) / Decimal('1000000')

            # Total cost
            total_cost = input_cost + cached_cost + output_cost

            # Round to 6 decimal places for USD (microdollars precision)
            total_cost = total_cost.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)

            logger.debug(
                f"Cost calculation: {provider}/{model} - "
                f"input={regular_input_tokens}, cached={cached_tokens}, output={completion_tokens} -> ${total_cost}"
            )

            return total_cost

        except Exception as e:
            logger.error(f"Error calculating cost: {e}", exc_info=True)
            return Decimal('0.0')

    @staticmethod
    def _get_pricing(provider: str, model: str) -> Optional[Dict]:
        """
        Get pricing information for a provider/model combination.
        Cached for 1 hour to reduce database queries.

        Args:
            provider: Provider name ('openai', 'mistral')
            model: Model name ('gpt-4o-mini', 'mistral-small-latest')

        Returns:
            Dict with pricing info or None if not found:
            {
                'input_cost_per_1m': Decimal,
                'output_cost_per_1m': Decimal,
                'cached_input_cost_per_1m': Decimal or None
            }
        """
        cache_key = f"{provider}:{model}"

        # Check cache first
        cached_pricing = _pricing_cache.get(cache_key)
        if cached_pricing is not None:
            logger.debug(f"Cache hit for pricing: {cache_key}")
            return cached_pricing

        # Query database for most recent pricing
        try:
            pricing_record = LLMPricing.query.filter(
                and_(
                    LLMPricing.provider == provider,
                    LLMPricing.model_name == model,
                    LLMPricing.effective_date <= datetime.now(timezone.utc)
                )
            ).order_by(LLMPricing.effective_date.desc()).first()

            if not pricing_record:
                logger.warning(f"No pricing found for {provider}/{model}")
                return None

            pricing_dict = {
                'input_cost_per_1m': pricing_record.input_cost_per_1m,
                'output_cost_per_1m': pricing_record.output_cost_per_1m,
                'cached_input_cost_per_1m': pricing_record.cached_input_cost_per_1m
            }

            # Cache the result
            _pricing_cache.set(cache_key, pricing_dict)
            logger.debug(f"Cached pricing for {cache_key}")

            return pricing_dict

        except Exception as e:
            logger.error(f"Error fetching pricing for {provider}/{model}: {e}", exc_info=True)
            return None

    @staticmethod
    def get_monthly_cost(user_id: int, year: int, month: int) -> Dict:
        """
        Get aggregated cost data for a user's sessions in a given month.

        Args:
            user_id: User ID
            year: Year (e.g., 2025)
            month: Month (1-12)

        Returns:
            Dict with cost breakdown:
            {
                'total_cost_usd': Decimal,
                'translation_cost_usd': Decimal,
                'quiz_cost_usd': Decimal,
                'operations_count': int,
                'session_count': int
            }
        """
        try:
            # Calculate date range for the month
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)

            # Query sessions within the date range
            sessions = Session.query.filter(
                and_(
                    Session.user_id == user_id,
                    Session.started_at >= start_date,
                    Session.started_at < end_date
                )
            ).all()

            # Aggregate costs
            total_translation_cost = Decimal('0.0')
            total_quiz_cost = Decimal('0.0')
            total_operations = 0

            for session in sessions:
                if session.total_translation_cost_usd:
                    total_translation_cost += Decimal(str(session.total_translation_cost_usd))
                if session.total_quiz_cost_usd:
                    total_quiz_cost += Decimal(str(session.total_quiz_cost_usd))
                if session.operations_count:
                    total_operations += session.operations_count

            total_cost = total_translation_cost + total_quiz_cost

            result = {
                'total_cost_usd': total_cost,
                'translation_cost_usd': total_translation_cost,
                'quiz_cost_usd': total_quiz_cost,
                'operations_count': total_operations,
                'session_count': len(sessions)
            }

            logger.info(
                f"Monthly cost for user {user_id} ({year}-{month:02d}): "
                f"${total_cost} ({len(sessions)} sessions, {total_operations} operations)"
            )

            return result

        except Exception as e:
            logger.error(f"Error calculating monthly cost: {e}", exc_info=True)
            return {
                'total_cost_usd': Decimal('0.0'),
                'translation_cost_usd': Decimal('0.0'),
                'quiz_cost_usd': Decimal('0.0'),
                'operations_count': 0,
                'session_count': 0
            }

    @staticmethod
    def clear_pricing_cache():
        """Clear the pricing cache (useful for testing or manual updates)"""
        _pricing_cache.clear()
        logger.info("Pricing cache cleared")