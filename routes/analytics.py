"""
Analytics Blueprint

Provides endpoints for cost tracking and usage analytics.
Includes monthly cost reporting, session statistics, and usage trends.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timezone
from services.cost_service import CostCalculationService
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('analytics', __name__, url_prefix='/analytics')


@bp.route('/test')
def test():
    """Test endpoint to verify analytics blueprint is working"""
    return jsonify({'message': 'Analytics blueprint working'})


@bp.route('/costs/monthly', methods=['GET'])
@login_required
def get_monthly_costs():
    """
    Get user's monthly LLM usage costs with detailed breakdown.

    Query Parameters:
        year (int, optional): Year for cost query (defaults to current year)
        month (int, optional): Month for cost query (1-12, defaults to current month)

    Returns:
        JSON response with cost breakdown:
        {
            'year': int,
            'month': int,
            'total_cost_usd': float,
            'translation_cost_usd': float,
            'quiz_cost_usd': float,
            'operations_count': int,
            'session_count': int
        }

    Example:
        GET /analytics/costs/monthly?year=2025&month=12

    Response:
        {
            "year": 2025,
            "month": 12,
            "total_cost_usd": 0.0523,
            "translation_cost_usd": 0.0312,
            "quiz_cost_usd": 0.0211,
            "operations_count": 47,
            "session_count": 3
        }
    """
    try:
        # Get year and month from query params, default to current month
        now = datetime.now(timezone.utc)
        year = request.args.get('year', type=int)
        if year is None:
            year = now.year
        month = request.args.get('month', type=int)
        if month is None:
            month = now.month

        # Validate month range
        if month < 1 or month > 12:
            return jsonify({
                'success': False,
                'error': 'Invalid month. Must be between 1 and 12.'
            }), 400

        # Validate year range (reasonable bounds)
        if not (2020 <= year <= 2100):
            return jsonify({
                'success': False,
                'error': 'Invalid year. Must be between 2020 and 2100.'
            }), 400

        # Get cost data from service
        costs = CostCalculationService.get_monthly_cost(current_user.id, year, month)

        # Log the query
        logger.info(
            f"Monthly cost query for user {current_user.email}: "
            f"{year}-{month:02d} -> ${costs['total_cost_usd']}"
        )

        # Convert Decimal to float for JSON serialization
        response = {
            'success': True,
            'year': year,
            'month': month,
            'total_cost_usd': float(costs['total_cost_usd']),
            'translation_cost_usd': float(costs['translation_cost_usd']),
            'quiz_cost_usd': float(costs['quiz_cost_usd']),
            'operations_count': costs['operations_count'],
            'session_count': costs['session_count']
        }

        return jsonify(response), 200

    except ValueError as e:
        logger.warning(f"Invalid parameters for monthly cost query: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except Exception as e:
        logger.exception(f"Error fetching monthly costs for user {current_user.email}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch monthly costs. Please try again later.'
        }), 500


@bp.route('/costs/current', methods=['GET'])
@login_required
def get_current_month_costs():
    """
    Convenience endpoint to get current month's costs without parameters.

    Returns:
        Same as get_monthly_costs() but for the current month.

    Example:
        GET /analytics/costs/current
    """
    try:
        now = datetime.now(timezone.utc)
        costs = CostCalculationService.get_monthly_cost(current_user.id, now.year, now.month)

        response = {
            'success': True,
            'year': now.year,
            'month': now.month,
            'total_cost_usd': float(costs['total_cost_usd']),
            'translation_cost_usd': float(costs['translation_cost_usd']),
            'quiz_cost_usd': float(costs['quiz_cost_usd']),
            'operations_count': costs['operations_count'],
            'session_count': costs['session_count']
        }

        return jsonify(response), 200

    except Exception as e:
        logger.exception(f"Error fetching current month costs for user {current_user.email}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch current month costs. Please try again later.'
        }), 500


@bp.route('/costs/history', methods=['GET'])
@login_required
def get_cost_history():
    """
    Get cost history for multiple months (last N months).

    Query Parameters:
        months (int, optional): Number of months to retrieve (1-12, default: 6)

    Returns:
        JSON response with array of monthly costs:
        {
            'success': True,
            'months': [
                {
                    'year': 2025,
                    'month': 12,
                    'total_cost_usd': 0.0523,
                    'translation_cost_usd': 0.0312,
                    'quiz_cost_usd': 0.0211,
                    'operations_count': 47,
                    'session_count': 3
                },
                ...
            ]
        }

    Example:
        GET /analytics/costs/history?months=6
    """
    try:
        # Get number of months to retrieve
        months_count = request.args.get('months', type=int)
        if months_count is None:
            months_count = 6

        # Validate range
        if months_count < 1 or months_count > 12:
            return jsonify({
                'success': False,
                'error': 'Invalid months parameter. Must be between 1 and 12.'
            }), 400

        # Generate list of months to query
        now = datetime.now(timezone.utc)
        current_year = now.year
        current_month = now.month

        history = []

        for i in range(months_count):
            # Calculate year and month for this iteration
            month = current_month - i
            year = current_year

            # Handle year rollover
            while month < 1:
                month += 12
                year -= 1

            # Get costs for this month
            costs = CostCalculationService.get_monthly_cost(current_user.id, year, month)

            history.append({
                'year': year,
                'month': month,
                'total_cost_usd': float(costs['total_cost_usd']),
                'translation_cost_usd': float(costs['translation_cost_usd']),
                'quiz_cost_usd': float(costs['quiz_cost_usd']),
                'operations_count': costs['operations_count'],
                'session_count': costs['session_count']
            })

        logger.info(f"Cost history query for user {current_user.email}: {months_count} months")

        return jsonify({
            'success': True,
            'months': history
        }), 200

    except ValueError as e:
        logger.warning(f"Invalid parameters for cost history query: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except Exception as e:
        logger.exception(f"Error fetching cost history for user {current_user.email}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch cost history. Please try again later.'
        }), 500