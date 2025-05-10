from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from django.http import JsonResponse
from .forms import CustomUserCreationForm
from .models import ChatSession, Message, SavedRecipe
import requests
import os
from dotenv import load_dotenv
import json
from django.views.decorators.http import require_POST
from .context_manager import classify_message_type, create_conversation_summary, get_relevant_context
from .langchain_setup import get_recipe_response

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
    user = request.user
    return render(request, 'cooking/chat.html', {'chat': chat, 'messages': messages, 'user': user})

@login_required
def send_message(request, chat_id):
    if request.method == 'POST':
        chat = get_object_or_404(ChatSession, id=chat_id, user=request.user)
        user_message = request.POST.get('message')
        
        # Classify the message type
        message_type = classify_message_type(user_message)
        
        # Save user message
        Message.objects.create(
            chat=chat,
            role='user',
            content=user_message,
            message_type=message_type
        )
        
        try:
            # Check if we need to summarize the conversation
            if chat.should_summarize():
                create_conversation_summary(chat)
            
            # Get response using LangChain
            ai_message = get_recipe_response(chat, user_message)
            
            # Save AI message
            Message.objects.create(
                chat=chat,
                role='assistant',
                content=ai_message,
                message_type='system' if message_type == 'recipe_creation' else message_type
            )
            
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
    referer = request.META.get('HTTP_REFERER', '')
    back_url = 'my_recipes'  # default fallback
    
    if 'profile' in referer:
        back_url = 'profile'
    elif 'my-recipes' in referer:
        back_url = 'my_recipes'
        
    return render(request, 'cooking/view_recipe.html', {
        'recipe': recipe,
        'back_url': back_url
    })

@login_required
def my_recipes(request):
    saved_recipes = SavedRecipe.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'cooking/my_recipes.html', {'saved_recipes': saved_recipes})

@login_required
def chat_list(request):
    # Get chats that have at least one message
    chats = ChatSession.objects.filter(
        user=request.user,
        messages__isnull=False  # Ensures chat has messages
    ).distinct().order_by('-updated_at')  # distinct to avoid duplicates if multiple messages
    return render(request, 'cooking/chat_list.html', {'chats': chats})
