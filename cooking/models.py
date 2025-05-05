from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default="New Chat")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    recipe_summary = models.TextField(null=True, blank=True)  # Stores current recipe state
    last_summary_at = models.IntegerField(default=0)  # Message count when last summarized
    message_count = models.IntegerField(default=0)  # Total message count for quick reference

    def __str__(self):
        return f"{self.user.username}'s chat - {self.title}"

    def should_summarize(self):
        # Check if we need to create a new summary
        return self.message_count - self.last_summary_at >= 10  # Summarize every 10 messages

class Message(models.Model):
    MESSAGE_TYPES = [
        ('recipe_creation', 'Recipe Creation'),
        ('recipe_modification', 'Recipe Modification'),
        ('cooking_question', 'Cooking Question'),
        ('general_question', 'General Question'),
        ('system', 'System Message'),
    ]

    chat = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20)  # 'user' or 'assistant'
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='general_question')
    is_summarized = models.BooleanField(default=False)  # Track if this message is included in a summary

    def __str__(self):
        return f"{self.role} message in {self.chat.title}"

    def save(self, *args, **kwargs):
        # If this is a new message, increment the chat's message count
        if not self.pk:  # Only for new messages
            self.chat.message_count += 1
            self.chat.save()
        super().save(*args, **kwargs)

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
