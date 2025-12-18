from models import db
from datetime import datetime, timezone
from decimal import Decimal


class LLMPricing(db.Model):
    """LLM Pricing model - stores cost information for different LLM providers and models"""
    __tablename__ = 'llm_pricing'

    id = db.Column(db.Integer, primary_key=True)

    # Provider name (e.g., 'openai', 'mistral')
    provider = db.Column(db.String(20), nullable=False)

    # Model name (e.g., 'gpt-4o-mini', 'mistral-small-latest')
    model_name = db.Column(db.String(50), nullable=False)

    # Cost per 1 million input tokens (USD)
    input_cost_per_1m = db.Column(db.Numeric(10, 4), nullable=False)

    # Cost per 1 million output tokens (USD)
    output_cost_per_1m = db.Column(db.Numeric(10, 4), nullable=False)

    # Cost per 1 million cached input tokens (USD) - optional, for providers that support it
    cached_input_cost_per_1m = db.Column(db.Numeric(10, 4), nullable=True)

    # Effective date for this pricing (allows historical tracking if prices change)
    effective_date = db.Column(db.DateTime, nullable=False)

    # Optional notes about this pricing tier or changes
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Unique constraint on (provider, model_name, effective_date)
    __table_args__ = (
        db.UniqueConstraint('provider', 'model_name', 'effective_date',
                          name='uq_provider_model_effective_date'),
    )

    def __repr__(self):
        return f'<LLMPricing {self.provider}/{self.model_name} ${self.input_cost_per_1m}/{self.output_cost_per_1m} per 1M>'

    def to_dict(self):
        """Convert pricing to dictionary"""
        return {
            'provider': self.provider,
            'model_name': self.model_name,
            'input_cost_per_1m': float(self.input_cost_per_1m),
            'output_cost_per_1m': float(self.output_cost_per_1m),
            'cached_input_cost_per_1m': float(self.cached_input_cost_per_1m) if self.cached_input_cost_per_1m else None,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'notes': self.notes
        }