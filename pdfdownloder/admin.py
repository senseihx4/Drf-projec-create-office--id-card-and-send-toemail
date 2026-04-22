from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User 

    

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    
    list_display = ('email', 'username', 'user_type', 'is_staff', 'is_active', 'is_verified')
    list_filter = ('user_type', 'is_staff', 'is_verified')
    search_fields = ('email', 'username')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('username', 'profile_picture')}),
        ('Membership', {'fields': ('user_type',)}),
        ('Permissions', {'fields': ('is_staff',  'is_superuser', 'is_verified', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )


