from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import userviewset, loginviewset, GeneratePDF, PDFReportView, signupviewset,ArticleViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = DefaultRouter()
router.register(r'users', userviewset, basename='user')
router.register(r'login', loginviewset, basename='login')
router.register(r'generate-pdf', GeneratePDF, basename='generate-pdf')
router.register(r'pdfreports', PDFReportView, basename='pdfreport')
router.register(r'signup', signupviewset, basename='signup')
router.register(r'articles', ArticleViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('api/token/', TokenObtainPairView.as_view()),        
    path('api/token/refresh/', TokenRefreshView.as_view())
]
