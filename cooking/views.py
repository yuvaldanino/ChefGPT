from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from django.http import JsonResponse
from .forms import CustomUserCreationForm
from .models import ChatSession, Message, SavedRecipe
from openai import OpenAI
import os
from dotenv import load_dotenv
import json
from django.views.decorators.http import require_POST

# Load environment variables
load_dotenv()

@login_required
def home(request):
    saved_recipes = SavedRecipe.objects.filter(user=request.user)
    return render(request, 'cooking/home.html', {'saved_recipes': saved_recipes})

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CustomUserCreationForm()
    return render(request, 'cooking/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Login successful!')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'cooking/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')

@login_required
def profile_view(request):
    saved_recipes = SavedRecipe.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'cooking/profile.html', {
        'saved_recipes': saved_recipes
    })

@login_required
def new_chat(request):
    chat = ChatSession.objects.create(user=request.user)
    return redirect('chat', chat_id=chat.id)

@login_required
def chat_view(request, chat_id):
    chat = get_object_or_404(ChatSession, id=chat_id, user=request.user)
    messages = chat.messages.all()
    return render(request, 'cooking/chat.html', {'chat': chat, 'messages': messages})

@login_required
def send_message(request, chat_id):
    if request.method == 'POST':
        chat = get_object_or_404(ChatSession, id=chat_id, user=request.user)
        user_message = request.POST.get('message')
        
        # Save user message
        Message.objects.create(chat=chat, role='user', content=user_message)
        
        try:
            # Initialize OpenAI client with API key
            client = OpenAI()  # It will automatically use OPENAI_API_KEY from environment
            
            # Format messages for OpenAI
            messages = [
                {"role": "system", "content": """You are ChefGPT, an expert cooking assistant. You help users with recipes, cooking techniques, and culinary advice. Be friendly, professional, and focus on providing accurate cooking information.

When providing recipes, always use this format with exact spacing and line breaks:
<h2 data-recipe="title">🍳 [Recipe Name]</h2>

<h3 data-recipe="difficulty">⚡ Difficulty</h3>
[Easy/Medium/Hard]

<h3 data-recipe="cuisine">🌍 Cuisine Type</h3>
[Type of cuisine e.g. Italian, Mexican, Japanese, etc.]

<h3 data-recipe="prep-time">⏲️ Preparation Time</h3>
[Prep time details]

<h3 data-recipe="servings">👥 Servings</h3>
[Number of servings]

<h3 data-recipe="ingredients">📝 Ingredients</h3>
<ul>
[List ingredients with measurements]
</ul>

<h3 data-recipe="instructions">📋 Instructions</h3>
<ol>
[Numbered steps for cooking]
</ol>

<h3 data-recipe="tips">💡 Tips</h3>
<ul>
[Optional cooking tips and variations]
</ul>"""},
            ]
            
            # Add chat history
            for msg in chat.messages.all():
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
            )
            
            # Get AI response
            ai_message = response.choices[0].message.content
            
            # Save AI message
            Message.objects.create(chat=chat, role='assistant', content=ai_message)
            
            return JsonResponse({
                'success': True,
                'message': ai_message
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'An unexpected error occurred: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def save_recipe(request, chat_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            title = data.get('title')
            content = data.get('content')
            
            # Get metadata fields
            difficulty = data.get('difficulty')
            cuisine_type = data.get('cuisine_type')
            prep_time = data.get('prep_time')
            servings = data.get('servings')
            
            if not title or not content:
                return JsonResponse({'success': False, 'error': 'Missing title or content'})
            
            chat_session = get_object_or_404(ChatSession, id=chat_id, user=request.user)
            
            # Check if recipe already exists for this chat
            existing_recipe = SavedRecipe.objects.filter(
                chat_session=chat_session,
                user=request.user
            ).first()
            
            if existing_recipe:
                # Update existing recipe
                existing_recipe.title = title
                existing_recipe.content = content
                existing_recipe.difficulty = difficulty
                existing_recipe.cuisine_type = cuisine_type
                existing_recipe.prep_time = prep_time
                existing_recipe.servings = servings
                existing_recipe.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Recipe updated successfully',
                    'recipe_id': existing_recipe.id
                })
            else:
                # Create new recipe
                recipe = SavedRecipe.objects.create(
                    user=request.user,
                    chat_session=chat_session,
                    title=title,
                    content=content,
                    difficulty=difficulty,
                    cuisine_type=cuisine_type,
                    prep_time=prep_time,
                    servings=servings
                )
                return JsonResponse({
                    'success': True,
                    'message': 'Recipe saved successfully',
                    'recipe_id': recipe.id
                })
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def delete_recipe(request, recipe_id):
    if request.method == 'POST':
        recipe = get_object_or_404(SavedRecipe, id=recipe_id, user=request.user)
        recipe.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@require_POST
@login_required
def update_sidebar_state(request):
    try:
        data = json.loads(request.body)
        request.session['sidebar_collapsed'] = data.get('collapsed', False)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def view_recipe(request, recipe_id):
    recipe = get_object_or_404(SavedRecipe, id=recipe_id, user=request.user)
    return render(request, 'cooking/view_recipe.html', {'recipe': recipe})
