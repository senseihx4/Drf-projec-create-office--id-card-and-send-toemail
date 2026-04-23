from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from django.contrib.auth import login
from django.contrib.auth.hashers import make_password
import sib_api_v3_sdk
import stripe
from .models import User, PendingUser, PDFReport
from .serializers import UserSerializer, PDFReportSerializer , signupSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
import io
from django.http import FileResponse
from django.core.mail import EmailMessage
from django.conf import settings
from .models import PDFReport as pdfreport
from sib_api_v3_sdk.rest import ApiException
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
import textwrap
import base64
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt


stripe.api_key = settings.STRIPE_SECRET_KEY



def http_response(status_code, message=None, data=None, errors=None):
    payload = {}
    if data is not None:
        payload['data'] = data
    if errors is not None:
        payload['errors'] = errors

    status_map = {
        200: ('OK',                    status.HTTP_200_OK),
        201: ('Created',               status.HTTP_201_CREATED),
        204: ('No Content',            status.HTTP_204_NO_CONTENT),
        400: ('Bad Request',           status.HTTP_400_BAD_REQUEST),
        401: ('Unauthorized',          status.HTTP_401_UNAUTHORIZED),
        403: ('Forbidden',             status.HTTP_403_FORBIDDEN),
        404: ('Not Found',             status.HTTP_404_NOT_FOUND),
        405: ('Method Not Allowed',    status.HTTP_405_METHOD_NOT_ALLOWED),
        409: ('Conflict',              status.HTTP_409_CONFLICT),
        422: ('Unprocessable Entity',  status.HTTP_422_UNPROCESSABLE_ENTITY),
        429: ('Too Many Requests',     status.HTTP_429_TOO_MANY_REQUESTS),
        500: ('Internal Server Error', status.HTTP_500_INTERNAL_SERVER_ERROR),
        502: ('Bad Gateway',           status.HTTP_502_BAD_GATEWAY),
        503: ('Service Unavailable',   status.HTTP_503_SERVICE_UNAVAILABLE),
    }

    label, drf_status = status_map.get(status_code, (str(status_code), status_code))
    payload['status'] = status_code
    payload['message'] = message or label
    return Response(payload, status=drf_status)



class userviewset(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


        
    def list(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return http_response(403, message='You do not have permission to view this resource.')
        return super().list(request, *args, **kwargs)
    def create(self, request, *args, **kwargs):
            return super().create(request, *args, **kwargs)


          
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
    

class signupviewset(viewsets.ViewSet):
    permission_classes = [AllowAny]
    serializer_class = signupSerializer
    authentication_classes = []

    def create(self, request):
        if User.objects.filter(email=request.data.get('email')).exists():
            return http_response(409, message='An account with this email already exists.')
        serializer = signupSerializer(data=request.data)
        if not serializer.is_valid():
            return http_response(400, errors=serializer.errors)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        pending_user, _ = PendingUser.objects.update_or_create(
            email=email,
            defaults={'password_hash': make_password(password)},
        )

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': 'ID Card Membership'},
                    'unit_amount': 1000,  # $10.00
                },
                'quantity': 1,
            }],
            mode='payment',
            metadata={'pending_user_id': pending_user.id},
            success_url=(
                getattr(settings, 'FRONTEND_URL', request.build_absolute_uri('/'))
                + 'api/signup/complete/?session_id={CHECKOUT_SESSION_ID}'
            ),
            cancel_url=(
                getattr(settings, 'FRONTEND_URL', request.build_absolute_uri('/'))
                + 'api/signup/cancel/'
            ),
        )

        pending_user.stripe_session_id = checkout_session.id
        pending_user.save(update_fields=['stripe_session_id'])

        return http_response(200, data={'checkout_url': checkout_session.url})

    @action(detail=False, methods=['get', 'post'], url_path='complete')
    def complete(self, request):
        session_id = request.data.get('session_id') or request.query_params.get('session_id')
        if not session_id:
            return http_response(400, message='session_id is required.')

        checkout_session = stripe.checkout.Session.retrieve(session_id)
        if checkout_session.payment_status != 'paid':
            return http_response(402, message='Payment not completed.')

        try:
            pending_user_id = checkout_session.metadata['pending_user_id']
            pending_user = PendingUser.objects.get(id=pending_user_id)
        except (KeyError, PendingUser.DoesNotExist):
            return http_response(404, message='No pending registration found for this session.')

        if User.objects.filter(email=pending_user.email).exists():
            return http_response(409, message='Account already created for this email.')

        user = User.objects.create(
            email=pending_user.email,
            password=pending_user.password_hash, 
        )
        pending_user.delete()

        refresh = RefreshToken.for_user(user)
        return http_response(201, data={
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })
    



class loginviewset(viewsets.ViewSet):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserSerializer
    authentication_classes = []

    def create(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = User.objects.filter(email=email).first()

        if user and user.check_password(password):
                login(request, user)
                refresh = RefreshToken.for_user(user)
                return http_response(200, data={
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                })
        else:
            return http_response(401, message='Invalid email or password.')
        



class PDFReportView(viewsets.ViewSet):
    serializer_class = PDFReportSerializer
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()

    def list(self, request):
        pdf_report = pdfreport.objects.filter(user=request.user).first()
        if not pdf_report:
            return http_response(404, message='No report found for this user.')

        serializer = PDFReportSerializer(pdf_report)
        return http_response(200, data=serializer.data)

    def create(self, request):
        pdf_report = pdfreport.objects.filter(user=request.user).first()
        if not pdf_report:
            pdf_report = pdfreport.objects.create(user=request.user)
        serializer = PDFReportSerializer(pdf_report, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return http_response(200, data=serializer.data)
        return http_response(400, errors=serializer.errors)

    def update(self, request, pk=None):
        pdf_report = pdfreport.objects.filter(user=request.user).first()
        if not pdf_report:
            return http_response(404, message='No report found for this user.')

        serializer = PDFReportSerializer(pdf_report, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return http_response(200, data=serializer.data)
        return http_response(400, errors=serializer.errors)

    def destroy(self, request, pk=None):
        pdf_report = pdfreport.objects.filter(user=request.user).first()
        if not pdf_report:
            return http_response(404, message='No report found for this user.')

        pdf_report.delete()
        return http_response(204)


class GeneratePDF(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
       

        pdf_report = pdfreport.objects.filter(user=request.user).first()
        if not pdf_report:
            return http_response(404, message='No report found for this user.')

        if not pdf_report.name and not pdf_report.job_title:
            return http_response(404, message='No report found for this user.')

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
            return http_response(500, message=f'Failed to send email: {e}')

        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename='idcard.pdf', content_type='application/pdf')
    
class SignatureUploadView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        pdf_report = pdfreport.objects.filter(user=request.user).first()
        if not pdf_report:
            return http_response(404, message='No report found for this user.')

        signature_file = request.FILES.get('signature')
        if not signature_file:
            return http_response(400, message='No signature file provided.')

        pdf_report.signature = signature_file
        pdf_report.save()

        return http_response(200, message='Signature uploaded successfully.')


#