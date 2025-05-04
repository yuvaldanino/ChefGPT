from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default="New Chat")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s chat - {self.title}"

class Message(models.Model):
    chat = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20)  # 'user' or 'assistant'
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return ""

    class Meta:
        ordering = ['created_at']

class SavedRecipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_recipes')
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    chat_session = models.ForeignKey(ChatSession, on_delete=models.SET_NULL, null=True, related_name='saved_recipes')
    
    # New metadata fields
    difficulty = models.CharField(max_length=50, null=True, blank=True)
    cuisine_type = models.CharField(max_length=100, null=True, blank=True)
    prep_time = models.CharField(max_length=50, null=True, blank=True)
    servings = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"
        
    def get_clean_value(self, value):
        """Helper method to get the last non-empty line from a string."""
        if not value:
            return ''
        lines = [line.strip() for line in value.split('\n') if line.strip()]
        return lines[-1] if lines else ''
        
    @property
    def clean_difficulty(self):
        return self.get_clean_value(self.difficulty)
        
    @property
    def clean_cuisine_type(self):
        return self.get_clean_value(self.cuisine_type)
        
    @property
    def clean_prep_time(self):
        return self.get_clean_value(self.prep_time)
        
    @property
    def clean_servings(self):
        return self.get_clean_value(self.servings)
