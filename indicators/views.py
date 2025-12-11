from django.views.generic import TemplateView
from .models import EconomicIndicator

class DashboardView(TemplateView):
    template_name = 'dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        years = EconomicIndicator.objects.values_list('year', flat=True).order_by('year')
        context.update({
            'page_title': 'German Economic Anomaly Detection',
            'year_range': f"{min(years)} - {max(years)}" if years else "No data",
            'total_years': len(years),
        })
        return context
