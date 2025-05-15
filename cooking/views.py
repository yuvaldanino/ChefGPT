from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from django.http import JsonResponse, HttpResponse
from .forms import CustomUserCreationForm
from .models import ChatSession, Message, SavedRecipe
import requests
import os
from dotenv import load_dotenv
import json
from django.views.decorators.http import require_POST, require_http_methods
from .context_manager import classify_message_type, create_conversation_summary, get_relevant_context
from .langchain_setup import get_recipe_response
from .embeddings import generate_recipe_embedding, store_recipe_embedding
from .db_connection import get_db_connection
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from django.core.exceptions import PermissionDenied
import traceback
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required

# Load environment variables
load_dotenv()

# Constants for validation
MAX_MESSAGE_LENGTH = 1000
MAX_CHAT_SESSIONS = 50
MAX_RECIPES_PER_USER = 100
MAX_RECIPES_PER_CHAT = 10
MAX_RECIPE_TITLE_LENGTH = 200
MAX_RECIPE_CONTENT_LENGTH = 10000
MAX_RECIPE_DIFFICULTY_LENGTH = 50
MAX_RECIPE_CUISINE_LENGTH = 100
MAX_RECIPE_PREP_TIME_LENGTH = 50
MAX_RECIPE_SERVINGS_LENGTH = 50
MAX_RECIPE_EMBEDDING_ID_LENGTH = 100

@csrf_exempt
@require_http_methods(["GET"])
def root_view(request):
    """Root view that redirects to login if not authenticated."""
    try:
        print("=" * 80)
        print("Root view called")
        print(f"User authenticated: {request.user.is_authenticated}")
        print(f"Request headers: {request.headers}")
        print(f"Request method: {request.method}")
        print(f"Request path: {request.path}")
        print(f"Request GET params: {request.GET}")
        print(f"Request POST params: {request.POST}")
        print(f"Request META: {request.META}")
        
        # Get the host from various possible headers
        host = (
            request.META.get('HTTP_HOST') or
            request.META.get('SERVER_NAME') or
            request.META.get('REMOTE_ADDR') or
            'localhost'
        )
        print(f"Using host: {host}")
        
        # Check if the host is allowed
        print(f"Allowed hosts: {settings.ALLOWED_HOSTS}")
        if host not in settings.ALLOWED_HOSTS and not any(host.endswith(h.replace('*', '')) for h in settings.ALLOWED_HOSTS if '*' in h):
            print(f"Host {host} not in allowed hosts")
            # Instead of raising PermissionDenied, just log and continue
            print(f"Warning: Host {host} not in allowed hosts, but continuing anyway")
        
        # Set the host in the request
        request.META['HTTP_HOST'] = host
        
        # Check if user is authenticated
        if request.user.is_authenticated:
            return redirect('home')
        
        # If not authenticated, redirect to login
        response = redirect('login')
        
        # Set session cookie options
        response.set_cookie('sessionid', request.session.session_key or '', 
                          samesite='Lax', 
                          secure=False)  # Set to True in production with HTTPS
        
        return response
    except Exception as e:
        print(f"Error in root_view: {str(e)}")
        print("Traceback:")
        print(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)

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
            
            # Prepare recipe data for embedding
            recipe_data = {
                'title': title,
                'cuisine': cuisine_type,
                'difficulty': difficulty,
                'ingredients': extract_ingredients(content),
                'instructions': extract_instructions(content),
                'tips': extract_tips(content)
            }
            
            # Generate and store embedding
            recipe_with_embedding = generate_recipe_embedding(recipe_data)
            stored_embedding = store_recipe_embedding(recipe_with_embedding)
            
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
                existing_recipe.embedding_id = stored_embedding['id']
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
                    servings=servings,
                    embedding_id=stored_embedding['id']
                )
                return JsonResponse({
                    'success': True,
                    'message': 'Recipe saved successfully',
                    'recipe_id': recipe.id
                })
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def extract_ingredients(content):
    """Extract ingredients from recipe content."""
    try:
        # Find the ingredients section
        start = content.find('<h3 data-recipe="ingredients">')
        if start == -1:
            return []
        
        # Find the end of ingredients section
        end = content.find('<h3 data-recipe="instructions">')
        if end == -1:
            end = content.find('<h3 data-recipe="tips">')
        
        if end == -1:
            return []
        
        # Extract the ingredients list
        ingredients_section = content[start:end]
        # Remove HTML tags and split into lines
        ingredients = [line.strip() for line in ingredients_section.split('\n') 
                      if line.strip() and not line.startswith('<')]
        return ingredients
    except Exception:
        return []

def extract_instructions(content):
    """Extract instructions from recipe content."""
    try:
        # Find the instructions section
        start = content.find('<h3 data-recipe="instructions">')
        if start == -1:
            return []
        
        # Find the end of instructions section
        end = content.find('<h3 data-recipe="tips">')
        if end == -1:
            return []
        
        # Extract the instructions list
        instructions_section = content[start:end]
        # Remove HTML tags and split into lines
        instructions = [line.strip() for line in instructions_section.split('\n') 
                       if line.strip() and not line.startswith('<')]
        return instructions
    except Exception:
        return []

def extract_tips(content):
    """Extract tips from recipe content."""
    try:
        # Find the tips section
        start = content.find('<h3 data-recipe="tips">')
        if start == -1:
            return []
        
        # Extract the tips list
        tips_section = content[start:]
        # Remove HTML tags and split into lines
        tips = [line.strip() for line in tips_section.split('\n') 
                if line.strip() and not line.startswith('<')]
        return tips
    except Exception:
        return []

@login_required
def delete_recipe(request, recipe_id):
    if request.method == 'POST':
        try:
            # Get the recipe and verify ownership
            recipe = get_object_or_404(SavedRecipe, id=recipe_id, user=request.user)
            
            # Delete the embedding from Supabase if it exists
            if recipe.embedding_id:
                try:
                    # Connect to database and delete embedding
                    with get_db_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                DELETE FROM public.recipe_embeddings 
                                WHERE id = %s
                            """, (recipe.embedding_id,))
                            conn.commit()
                except Exception as e:
                    print(f"Error deleting embedding: {str(e)}")
                    # Continue with recipe deletion even if embedding deletion fails
            
            # Delete the recipe from Django database
            recipe.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
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

@csrf_exempt
def health_check(request):
    """Simple health check endpoint for load balancer."""
    return JsonResponse({"status": "healthy"}, status=200)

def debug_view(request):
    """Debug view to check request headers."""
    try:
        debug_info = {
            'Host': request.get_host(),
            'Raw Host': request.META.get('HTTP_HOST'),
            'X-Forwarded-Host': request.headers.get('X-Forwarded-Host'),
            'X-Forwarded-Proto': request.headers.get('X-Forwarded-Proto'),
            'X-Forwarded-Port': request.headers.get('X-Forwarded-Port'),
            'All Headers': dict(request.headers),
            'META': {k: v for k, v in request.META.items() if k.startswith('HTTP_')},
            'ALLOWED_HOSTS': settings.ALLOWED_HOSTS,
            'Request Method': request.method,
            'Request Path': request.path,
            'Request GET': dict(request.GET),
            'Request POST': dict(request.POST),
        }
        print("=" * 80)
        print("Debug View Called")
        print(f"Debug Info: {json.dumps(debug_info, indent=2)}")
        print("=" * 80)
        return HttpResponse(f"Debug Info: {json.dumps(debug_info, indent=2)}")
    except Exception as e:
        print("=" * 80)
        print(f"Error in debug_view: {str(e)}")
        print("Traceback:")
        print(traceback.format_exc())
        print("=" * 80)
        return HttpResponse(f"Error: {str(e)}\nTraceback: {traceback.format_exc()}", status=500)

@staff_member_required
def vllm_connect_view(request):
    """View for connecting to the vLLM server"""
    print(f"vllm_connect_view called by user: {request.user.username}")
    print(f"Request method: {request.method}")
    print(f"Request path: {request.path}")
    print(f"Request headers: {request.headers}")
    
    if request.method == 'POST':
        try:
            print(f"Request body: {request.body}")
            data = json.loads(request.body)
            ip_address = data.get('ip_address')
            print(f"IP address: {ip_address}")
            
            if not ip_address:
                return JsonResponse({'error': 'No IP address provided'}, status=400)
            
            # Store IP in Django session
            request.session['vllm_server_ip'] = ip_address
            print(f"Stored IP in session: {request.session['vllm_server_ip']}")
            return JsonResponse({'success': True})
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}")
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            print(f"Error in vllm_connect_view POST: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return JsonResponse({'error': str(e)}, status=500)
            
    return render(request, 'cooking/vllm_connect.html')

@staff_member_required
def vllm_chat_view(request):
    """View for the vLLM chat interface"""
    print(f"vllm_chat_view called by user: {request.user.username}")
    print(f"User is staff: {request.user.is_staff}")
    print(f"User is superuser: {request.user.is_superuser}")
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message')
            
            if not user_message:
                return JsonResponse({'error': 'No message provided'}, status=400)
            
            # Get the stored IP from the request
            server_ip = request.session.get('vllm_server_ip')
            print(f"Stored server IP: {server_ip}")
            
            if not server_ip:
                return JsonResponse({'error': 'Not connected to vLLM server'}, status=400)
            
            # Make request to vLLM API
            api_url = f'http://{server_ip}:8000/generate_tip'
            print(f"Making API request to: {api_url}")
            response = requests.post(api_url, json={'prompt': user_message})
            
            if response.status_code == 200:
                data = response.json()
                return JsonResponse({
                    'response': data['tip'],
                    'tokens': data['tokens_generated']
                })
            else:
                print(f"API request failed with status {response.status_code}")
                return JsonResponse({'error': 'Failed to generate tip'}, status=500)
                
        except Exception as e:
            print(f"Error in vllm_chat_view POST: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return render(request, 'cooking/vllm_chat.html')
