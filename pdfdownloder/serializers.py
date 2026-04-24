from rest_framework import serializers
from .models import User, PDFReport, Article


class UserSerializer(serializers.ModelSerializer):
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True )
    

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
    

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

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


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['id', 'email']

class ArticleSerializer(serializers.ModelSerializer):
    title = serializers.CharField(max_length=300, allow_blank=False ,required =True)
    content = serializers.CharField(allow_blank=False, required=True)
    price = serializers.DecimalField(min_value=0,  required=False , max_digits=6, decimal_places=2, default=0.00)
    read_count = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    author  = AuthorSerializer(read_only=True)       
    preview = serializers.SerializerMethodField()    

    class Meta:
        model = Article
        fields = ['id', 'title', 'content', 'price', 'is_premium', 'read_count', 'created_at', 'author', 'preview']


    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value
    def validate_content(self, value):
        if len(value) < 100:
            raise serializers.ValidationError("Content must be at least 100 characters long.")
        return value
    def validate(self, data):
        is_premium = data.get('is_premium')
        price      = data.get('price', 0)

        if is_premium and price <= 0:
            raise serializers.ValidationError("Premium articles must have a price.")
        return data
    
    def get_preview(self, obj):
        if len(obj.content) > 150:
            return obj.content[:150] + "..." 
        return obj.content  




    