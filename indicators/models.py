"""
Economic Indicator Models
=========================
Django models for storing German economic indicators in PostgreSQL.

File location: indicators/models.py
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class EconomicIndicator(models.Model):
    """
    Stores annual economic indicators for Germany.
    Data sources: DESTATIS Genesis-Online database.
    """
    
    # Primary identifier
    year = models.IntegerField(
        unique=True,
        primary_key=True,
        validators=[MinValueValidator(1990), MaxValueValidator(2100)],
        help_text="Year of the economic data"
    )
    
    # Economy & Finance (from Table 99911-0012)
    gdp_current_prices = models.FloatField(
        null=True,
        blank=True,
        help_text="GDP in billion USD (current prices)"
    )
    gdp_per_capita = models.FloatField(
        null=True,
        blank=True,
        help_text="GDP per capita in USD"
    )
    gdp_growth_rate = models.FloatField(
        null=True,
        blank=True,
        help_text="GDP growth rate (annual change, %)"
    )
    inflation_rate = models.FloatField(
        null=True,
        blank=True,
        help_text="Inflation rate - CPI annual change (%)"
    )
    agriculture_share_gdp = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Agriculture as % of GDP"
    )
    industry_share_gdp = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Industry as % of GDP"
    )
    services_share_gdp = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Services as % of GDP"
    )
    
    # Labour Market (from Table 13231-0003)
    unemployment_rate = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Unemployment rate (%)"
    )
    labour_force_participation = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Labour force participation rate (%)"
    )
    youth_unemployment_rate = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Youth unemployment rate (%)"
    )
    
    # Foreign Trade (from Table 51000-0001)
    export_share_gdp = models.FloatField(
        null=True,
        blank=True,
        help_text="Exports as % of GDP"
    )
    import_goods_total = models.FloatField(
        null=True,
        blank=True,
        help_text="Total imports in billion USD"
    )
    export_goods_total = models.FloatField(
        null=True,
        blank=True,
        help_text="Total exports in billion USD"
    )
    
    # Industry (from Table 42153-0001)
    industrial_production_index = models.FloatField(
        null=True,
        blank=True,
        help_text="Industrial production index (base year = 100)"
    )
    manufacturing_production_index = models.FloatField(
        null=True,
        blank=True,
        help_text="Manufacturing production index (base year = 100)"
    )
    
    # Research & Development
    rd_expenditure_share_gdp = models.FloatField(
        null=True,
        blank=True,
        help_text="R&D expenditure as % of GDP"
    )
    internet_users_per_100 = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Internet users per 100 inhabitants"
    )
    
    # ML Model Results (populated by anomaly detection)
    is_anomaly = models.BooleanField(
        default=False,
        help_text="Whether this year was flagged as anomaly by ML model"
    )
    anomaly_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Anomaly score from Isolation Forest (-1 to 1, lower = more anomalous)"
    )
    anomaly_explanation = models.TextField(
        null=True,
        blank=True,
        help_text="Human-readable explanation of why this is an anomaly"
    )
    
    # Forecasting Results (populated by Prophet models)
    gdp_growth_forecast = models.FloatField(
        null=True,
        blank=True,
        help_text="Forecasted GDP growth rate for this year (%)"
    )
    gdp_growth_forecast_lower = models.FloatField(
        null=True,
        blank=True,
        help_text="Lower bound of forecast confidence interval"
    )
    gdp_growth_forecast_upper = models.FloatField(
        null=True,
        blank=True,
        help_text="Upper bound of forecast confidence interval"
    )
    
    inflation_forecast = models.FloatField(
        null=True,
        blank=True,
        help_text="Forecasted inflation rate for this year (%)"
    )
    inflation_forecast_lower = models.FloatField(
        null=True,
        blank=True,
        help_text="Lower bound of forecast confidence interval"
    )
    inflation_forecast_upper = models.FloatField(
        null=True,
        blank=True,
        help_text="Upper bound of forecast confidence interval"
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this record was last updated"
    )
    
    class Meta:
        ordering = ['year']
        verbose_name = 'Economic Indicator'
        verbose_name_plural = 'Economic Indicators'
        indexes = [
            models.Index(fields=['year']),
            models.Index(fields=['is_anomaly']),
        ]
    
    def __str__(self):
        return f"Economic Data - {self.year}"
    
    def get_trade_balance(self):
        """Calculate trade balance (exports - imports)."""
        if self.export_goods_total and self.import_goods_total:
            return self.export_goods_total - self.import_goods_total
        return None
    
    def is_complete(self):
        """Check if record has all core economic indicators."""
        return all([
            self.gdp_growth_rate is not None,
            self.inflation_rate is not None,
            self.gdp_current_prices is not None
        ])
    
    @property
    def completeness_percentage(self):
        """Calculate percentage of non-null fields."""
        total_fields = 17  # Number of economic indicator fields
        non_null_fields = sum([
            1 for field in [
                self.gdp_current_prices, self.gdp_per_capita, self.gdp_growth_rate,
                self.inflation_rate, self.agriculture_share_gdp, self.industry_share_gdp,
                self.services_share_gdp, self.unemployment_rate, self.labour_force_participation,
                self.youth_unemployment_rate, self.export_share_gdp, self.import_goods_total,
                self.export_goods_total, self.industrial_production_index,
                self.manufacturing_production_index, self.rd_expenditure_share_gdp,
                self.internet_users_per_100
            ]
            if field is not None
        ])
        return (non_null_fields / total_fields) * 100


class MLModel(models.Model):
    """
    Stores metadata about trained ML models.
    """
    
    MODEL_TYPES = [
        ('ISOLATION_FOREST', 'Isolation Forest'),
        ('PROPHET_GDP', 'Prophet - GDP Growth'),
        ('PROPHET_INFLATION', 'Prophet - Inflation'),
        ('PROPHET_UNEMPLOYMENT', 'Prophet - Unemployment'),
    ]
    
    model_type = models.CharField(
        max_length=50,
        choices=MODEL_TYPES,
        help_text="Type of ML model"
    )
    version = models.CharField(
        max_length=50,
        help_text="Model version identifier"
    )
    trained_on = models.DateTimeField(
        auto_now_add=True,
        help_text="When the model was trained"
    )
    training_data_years = models.CharField(
        max_length=100,
        help_text="Year range used for training (e.g., '2015-2021')"
    )
    model_file_path = models.CharField(
        max_length=500,
        help_text="Path to saved model file (.pkl)"
    )
    
    # Performance metrics
    accuracy = models.FloatField(
        null=True,
        blank=True,
        help_text="Model accuracy metric"
    )
    rmse = models.FloatField(
        null=True,
        blank=True,
        help_text="Root Mean Square Error (for forecasting models)"
    )
    mae = models.FloatField(
        null=True,
        blank=True,
        help_text="Mean Absolute Error (for forecasting models)"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the model"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this model version is currently in use"
    )
    
    class Meta:
        ordering = ['-trained_on']
        verbose_name = 'ML Model'
        verbose_name_plural = 'ML Models'
    
    # def __str__(self):
    #     return f"{self.get_model_type_display()} v{self.version} - {self.trained_on.date()}"
    
    def __str__(self):
        # Instead of self.get_model_type_display()
        return f"{dict(self.MODEL_TYPES).get(self.model_type, self.model_type)} v{self.version} - {self.trained_on.date()}"