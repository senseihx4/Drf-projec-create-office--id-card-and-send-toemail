from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from django.contrib.auth import login
import sib_api_v3_sdk
from .models import User
from .serializers import UserSerializer, PDFReportSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
import io
from django.http import FileResponse
from django.core.mail import EmailMessage
from django.conf import settings
from .models import PDFReport as pdfreport
from sib_api_v3_sdk.rest import ApiException






class userviewset(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAdminUser()]

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data['next'] = '/verify-otp/'
        return response

    def perform_create(self, serializer):
        email = self.request.data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError({'email': 'A user with this email already exists.'})
        user = serializer.save()
        user.save()

    @action(detail=False, methods=['get', 'patch'], permission_classes=[IsAuthenticated])
    def me(self, request):
        if request.method == 'GET':
            return Response(UserSerializer(request.user, context={'request': request}).data)
        serializer = UserSerializer(request.user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class loginviewset(viewsets.ViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def create(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = User.objects.filter(email=email).first()

        if user and user.check_password(password):

                login(request, user)
                refresh = RefreshToken.for_user(user)
                return Response({
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                }, status=status.HTTP_200_OK)

        else:
            return Response({'detail': 'Invalid email or password.'}, status=status.HTTP_401_UNAUTHORIZED)
        



class PDFReportView(viewsets.ViewSet):
    serializer_class = PDFReportSerializer
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()

    def list(self, request):
        pdf_report = pdfreport.objects.filter(user=request.user).first()
        if not pdf_report:
            return Response({'error': 'No report found for this user.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = PDFReportSerializer(pdf_report)
        return Response(serializer.data)
    
    def create(self, request):
        pdf_report = pdfreport.objects.filter(user=request.user).first()
        if not pdf_report:
            pdf_report = pdfreport.objects.create(user=request.user)
        serializer = PDFReportSerializer(pdf_report, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def update(self, request, pk=None):
        pdf_report = pdfreport.objects.filter(user=request.user).first()
        if not pdf_report:
            return Response({'error': 'No report found for this user.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = PDFReportSerializer(pdf_report, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def destroy(self, request, pk=None):
        pdf_report = pdfreport.objects.filter(user=request.user).first()
        if not pdf_report:
            return Response({'error': 'No report found for this user.'}, status=status.HTTP_404_NOT_FOUND)

        pdf_report.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GeneratePDF(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.utils import ImageReader
        from reportlab.lib import colors
        import textwrap
        import base64

        pdf_report = pdfreport.objects.filter(user=request.user).first()
        if not pdf_report:
            return Response({'error': 'No report found for this user.'}, status=status.HTTP_404_NOT_FOUND)

        if not pdf_report.name and not pdf_report.job_title:
            return Response({'error': 'No report found for this user.'}, status=status.HTTP_404_NOT_FOUND)

        CARD_W, CARD_H = 450, 270
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=(CARD_W, CARD_H))

        # === BACKGROUND (WHITE) ===
        p.setFillColorRGB(1, 1, 1)
        p.rect(0, 0, CARD_W, CARD_H, fill=1, stroke=0)

        # Blue top bar
        p.setFillColorRGB(0.05, 0.25, 0.65)
        p.rect(0, CARD_H - 60, CARD_W, 60, fill=1, stroke=0)

        # Blue bottom strip
        p.setFillColorRGB(0.05, 0.25, 0.65)
        p.rect(0, 0, CARD_W, 8, fill=1, stroke=0)

        # Decorative circle top right
        p.setFillColorRGB(0.08, 0.30, 0.72)
        p.circle(CARD_W - 30, CARD_H - 10, 80, fill=1, stroke=0)

        # Decorative circle bottom left
        p.setFillColorRGB(0.85, 0.90, 1.0)
        p.circle(20, 20, 50, fill=1, stroke=0)

        # === TOP BAR TEXT ===
        p.setFillColorRGB(1, 1, 1)
        p.setFont("Helvetica-Bold", 20)
        p.drawString(20, CARD_H - 40, "ID CARD")

        p.setFont("Helvetica", 9)
        p.setFillColorRGB(0.75, 0.85, 1.0)
        p.drawString(20, CARD_H - 52, "EMPLOYEE IDENTIFICATION")

        # === PROFILE PHOTO ===
        photo_x, photo_y = 20, CARD_H - 155
        photo_w, photo_h = 85, 90

        # Photo border
        p.setStrokeColorRGB(0.05, 0.40, 0.90)
        p.setLineWidth(2)
        p.rect(photo_x - 2, photo_y - 2, photo_w + 4, photo_h + 4, fill=0, stroke=1)

        if request.user.profile_picture:
            try:
                img = ImageReader(request.user.profile_picture.path)
                p.drawImage(img, photo_x, photo_y, width=photo_w, height=photo_h,
                            preserveAspectRatio=True, mask='auto')
            except Exception:
                p.setFillColorRGB(0.90, 0.93, 1.0)
                p.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=0)
                p.setFillColorRGB(0.4, 0.4, 0.5)
                p.setFont("Helvetica", 8)
                p.drawString(photo_x + 10, photo_y + 40, "NO PHOTO")
        else:
            p.setFillColorRGB(0.90, 0.93, 1.0)
            p.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=0)
            p.setFillColorRGB(0.4, 0.4, 0.5)
            p.setFont("Helvetica", 8)
            p.drawString(photo_x + 10, photo_y + 40, "NO PHOTO")

        # === DIVIDER LINE ===
        p.setStrokeColorRGB(0.05, 0.40, 0.90)
        p.setLineWidth(1)
        p.line(120, CARD_H - 70, 120, CARD_H - 175)

        # === USER DETAILS ===
        details_x = 130

        def draw_label_value(label, value, y):
            p.setFont("Helvetica-Bold", 7.5)
            p.setFillColorRGB(0.05, 0.25, 0.65)  # blue label
            p.drawString(details_x, y, label.upper())
            p.setFont("Helvetica", 10)
            p.setFillColorRGB(0.1, 0.1, 0.1)  # dark text
            p.drawString(details_x, y - 13, value or "—")

        draw_label_value("Name",        pdf_report.name or request.user.username or "—", CARD_H - 75)
        draw_label_value("Job Title",   pdf_report.job_title or "—",                     CARD_H - 105)
        draw_label_value("Blood Group", pdf_report.blood_group or "—",                   CARD_H - 135)
        draw_label_value("Joined Date", str(pdf_report.joined_date) if pdf_report.joined_date else "—", CARD_H - 165)

        # === BIO ===
        if pdf_report.bio:
            p.setFont("Helvetica-Bold", 7)
            p.setFillColorRGB(0.05, 0.25, 0.65)  # blue label
            p.drawString(20, 95, "BIO")
            p.setFont("Helvetica", 7.5)
            p.setFillColorRGB(0.1, 0.1, 0.1)  # dark text
            bio_lines = textwrap.wrap(pdf_report.bio, width=80)
            bio_y = 83
            for line in bio_lines[:2]:
                p.drawString(20, bio_y, line)
                bio_y -= 11

        # === SEPARATOR ===
        p.setStrokeColorRGB(0.05, 0.40, 0.90)
        p.setLineWidth(0.5)
        p.line(20, 55, CARD_W - 20, 55)

        # === SIGNATURE (bottom right) ===
        sig_x, sig_y = CARD_W - 170, 15
        sig_w, sig_h = 150, 40

        p.setFont("Helvetica", 7)
        p.setFillColorRGB(0.05, 0.25, 0.65)  # blue label
        p.drawString(sig_x, sig_y + sig_h + 3, "SIGNATURE")

        if pdf_report.signature:
            try:
                sig_data = pdf_report.signature
                if ',' in sig_data:
                    sig_data = sig_data.split(',')[1]
                sig_bytes = base64.b64decode(sig_data)
                sig_buffer = io.BytesIO(sig_bytes)
                sig_img = ImageReader(sig_buffer)
                p.drawImage(sig_img, sig_x, sig_y, width=sig_w, height=sig_h,
                            preserveAspectRatio=True, mask='auto')
            except Exception:
                pass

        # Signature underline
        p.setStrokeColorRGB(0.05, 0.40, 0.90)
        p.setLineWidth(0.5)
        p.line(sig_x, sig_y, sig_x + sig_w, sig_y)

        # === FOOTER ===
        p.setFont("Helvetica", 7)
        p.setFillColorRGB(0.2, 0.2, 0.2)  # dark gray
        p.drawString(20, 20, f"ID: {str(request.user.id).zfill(6)}")
        p.drawString(20, 11, f"EMAIL: {request.user.email}")

        p.showPage()
        p.save()

        pdf_content = buffer.getvalue()

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = settings.BREVO_API_KEY

        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": request.user.email}],
            sender={"email": settings.BREVO_SENDER_EMAIL, "name": settings.BREVO_SENDER_NAME},
            subject="Your ID Card PDF",
            text_content="Please find attached your ID card.",
            attachment=[{
                "content": base64.b64encode(pdf_content).decode('utf-8'),
                "name": "idcard.pdf"
            }]
        )               

        try:
            api_instance.send_transac_email(send_smtp_email)
        except ApiException as e:
            print(f"Email error: {e}")
            return Response({'error': f'Failed to send email: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename='idcard.pdf', content_type='application/pdf')
    
class SignatureUploadView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        pdf_report = pdfreport.objects.filter(user=request.user).first()
        if not pdf_report:
            return Response({'error': 'No report found for this user.'}, status=status.HTTP_404_NOT_FOUND)

        signature_file = request.FILES.get('signature')
        if not signature_file:
            return Response({'error': 'No signature file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        pdf_report.signature = signature_file
        pdf_report.save()

        return Response({'message': 'Signature uploaded successfully.'}, status=status.HTTP_200_OK)