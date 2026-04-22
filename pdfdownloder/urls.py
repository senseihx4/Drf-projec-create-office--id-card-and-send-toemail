from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import userviewset, loginviewset, GeneratePDF, PDFReportView

router = DefaultRouter()
router.register(r'users', userviewset, basename='user')
router.register(r'login', loginviewset, basename='login')
router.register(r'generate-pdf', GeneratePDF, basename='generate-pdf')
router.register(r'pdfreports', PDFReportView, basename='pdfreport')  

urlpatterns = [
    path('', include(router.urls)),
]
