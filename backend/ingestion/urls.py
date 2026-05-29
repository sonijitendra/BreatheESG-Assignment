from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DataSourceViewSet, IngestionJobViewSet, RawRecordViewSet

router = DefaultRouter()
router.register(r'sources', DataSourceViewSet, basename='source')
router.register(r'jobs', IngestionJobViewSet, basename='job')
router.register(r'raw-records', RawRecordViewSet, basename='raw-record')

urlpatterns = [
    path('', include(router.urls)),
]
