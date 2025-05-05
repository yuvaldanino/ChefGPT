from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import ChatSession, Message, SavedRecipe
from django.utils.html import format_html
from django.urls import reverse

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined', 'recipe_count', 'chat_count')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    def recipe_count(self, obj):
        return SavedRecipe.objects.filter(user=obj).count()
    recipe_count.short_description = 'Saved Recipes'
    
    def chat_count(self, obj):
        return ChatSession.objects.filter(user=obj).count()
    chat_count.short_description = 'Chat Sessions'

# Unregister the default User admin
admin.site.unregister(User)

# Register our custom User admin
admin.site.register(User, CustomUserAdmin)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('truncated_content', 'chat', 'role', 'message_type', 'created_at', 'is_summarized')
    list_filter = ('role', 'message_type', 'is_summarized', 'created_at')
    search_fields = ('content', 'chat__user__username')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    
    def truncated_content(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    truncated_content.short_description = 'Content'

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'created_at', 'message_count', 'has_saved_recipe', 'view_chat_link')
    list_filter = ('created_at', 'user')
    search_fields = ('user__username', 'title')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'message_count', 'last_summary_at')

    def has_saved_recipe(self, obj):
        return obj.saved_recipes.exists()
    has_saved_recipe.boolean = True
    has_saved_recipe.short_description = 'Has Recipe'
    
    def view_chat_link(self, obj):
        url = reverse('chat', args=[obj.id])
        return format_html('<a href="{}" target="_blank">View Chat</a>', url)
    view_chat_link.short_description = 'Chat Link'

@admin.register(SavedRecipe)
class SavedRecipeAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'difficulty', 'cuisine_type', 'prep_time', 'servings', 'created_at', 'view_recipe_link')
    list_filter = ('created_at', 'difficulty', 'cuisine_type')
    search_fields = ('title', 'user__username', 'content')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    
    def view_recipe_link(self, obj):
        if obj.chat_session:
            url = reverse('chat', args=[obj.chat_session.id])
            return format_html('<a href="{}" target="_blank">View Original Chat</a>', url)
        return "No chat available"
    view_recipe_link.short_description = 'Original Chat'
