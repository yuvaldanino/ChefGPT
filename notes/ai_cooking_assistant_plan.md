# 🧑‍🍳 AI Cooking Assistant – Feature Plan & Model Design

This document describes all core features and database models for the AI Cooking Assistant app, built using Django.

---

## 🚀 Features Overview

### 1. User Authentication
- Allow users to register, log in, and log out.
- Authenticated users have a profile that stores their chat history and saved recipes.

### 2. AI Chat Interface
- Users can start new cooking chats with the AI (GPT-4).
- The chat UI allows message exchange, with user and AI responses shown.
- Messages are stored per chat session and used to build a recipe.

### 3. Dynamic Recipe Generation
- Each chat is tied to a recipe object that builds up as the conversation continues.
- Recipe includes title, description, ingredients, and steps.
- Option to update the recipe live after each AI message (Celery or synchronous).

### 4. Finalize Recipe
- A "Finalize Recipe" button lets users save the completed recipe.
- Finalized recipes are read-only and viewable from the user's recipe book.

### 5. Recipe Book (User Profile)
- Each user has a personal recipe book showing all saved recipes.
- Recipes can be viewed, edited via new chat, or deleted.

### 6. Recipe Sharing
- Users can choose to share recipes publicly or keep them private.
- Public recipes get a unique shareable link for easy viewing.

### 7. Voice Input (Planned)
- Users will be able to speak to the AI instead of typing using browser APIs or Whisper.
- Transcribed input is sent to the chat endpoint.

---

## 🧱 Models

### `User` (extends Django's default)
- Handled via Django’s auth system.

---

### `ChatSession`
Represents a single chat between the user and the AI, tied to a dynamic recipe.

```python
class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
```

---

### `Message`
Represents a message in a chat session, either from the user or GPT.

```python
class Message(models.Model):
    chat = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10, choices=[('user', 'User'), ('ai', 'AI')])
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
```

---

### `Recipe`
The dynamic or finalized recipe generated from a chat.

```python
class Recipe(models.Model):
    chat = models.OneToOneField(ChatSession, on_delete=models.CASCADE, related_name='recipe')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    ingredients = models.TextField()  # Can be JSON or newline-separated
    steps = models.TextField()        # Can be JSON or newline-separated
    is_finalized = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

---

### `SharedRecipeView`
Log for recipe sharing (optional – analytics or controls for public access).

```python
class SharedRecipeView(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)
    viewer_ip = models.GenericIPAddressField()
```

---

## 🧰 Optional Enhancements (Future Scope)

- `Tag` model for recipes (e.g., vegetarian, quick, spicy)
- `Rating` or `Comment` models if you allow feedback
- `Ingredient` model if you want to normalize and reuse ingredients
- `ChatSummary` model for summarizing chats
- Calendar model for meal planning

---

## ⚙️ Supporting Tech

- GPT-4 via OpenAI API for AI interactions
- Celery (optional) for async recipe updates
- Redis as broker for Celery
- Django session-based auth
- HTML + CSS + JS (Fetch API) for frontend


Suggested Development Approach:
Phase 1: Core Infrastructure
Set up Django project with proper configuration
Implement user authentication system
Create basic database models
Set up OpenAI API integration
Phase 2: Chat Interface & Recipe Generation
Build the chat interface
Implement real-time recipe generation
Create the recipe finalization feature
Add basic recipe viewing capabilities
Phase 3: Recipe Management
Develop the recipe book feature
Implement recipe sharing functionality
Add recipe editing capabilities
Phase 4: Enhanced Features
Add voice input support
Implement optional enhancements (tags, ratings, etc.)
Add analytics for shared recipes