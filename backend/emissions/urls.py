from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmissionRecordViewSet, EmissionFactorViewSet, DashboardSummaryViewSet

router = DefaultRouter()
router.register(r'records', EmissionRecordViewSet, basename='record')
router.register(r'factors', EmissionFactorViewSet, basename='factor')
router.register(r'dashboard/summary', DashboardSummaryViewSet, basename='dashboard-summary')

urlpatterns = [
    path('', include(router.urls)),
]
