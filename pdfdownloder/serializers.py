from rest_framework import serializers
from .models import User, PDFReport


class UserSerializer(serializers.ModelSerializer):
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username',
            'user_type', 'user_type_display',
            'password', 'profile_picture', 'is_verified',
        ]
        read_only_fields = ['id', 'is_verified']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = super().create(validated_data)
        user.set_password(password)
        user.save()
        return user
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

class signupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'username', 'profile_picture', ]

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class PDFReportSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()
    signature = serializers.CharField(required=False, allow_blank=True)

    def get_profile_picture(self, instance):
        pic = instance.user.profile_picture
        if pic:
            request = self.context.get('request')
            return request.build_absolute_uri(pic.url) if request else pic.url
        return None

    class Meta:
        model = PDFReport
        fields = [
            'id', 'user', 'created_at', 'name', 'job_title',
            'blood_group', 'bio', 'joined_date', 'signature', 'profile_picture'
        ]
        read_only_fields = ['id', 'created_at', 'user', 'profile_picture']