from django.test import TransactionTestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import connection, connections
from ..models import ChatSession, Message
from ..langchain_setup import get_recipe_response
from ..context_manager import classify_message_type
import json
import re

User = get_user_model()

class LangChainIntegrationTest(TransactionTestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create a test chat session
        self.chat = ChatSession.objects.create(user=self.user)
        
        # Create a test client
        self.client = Client()
        
        # Log in the test user
        self.client.login(username='testuser', password='testpass123')

    def tearDown(self):
        # Clean up any remaining objects
        Message.objects.all().delete()
        ChatSession.objects.all().delete()
        User.objects.all().delete()

    def assert_valid_recipe_format(self, response):
        """Helper method to validate recipe format"""
        # Check for all required sections
        required_sections = [
            '<h2 data-recipe="title">',
            '<h3 data-recipe="difficulty">',
            '<h3 data-recipe="cuisine">',
            '<h3 data-recipe="prep-time">',
            '<h3 data-recipe="servings">',
            '<h3 data-recipe="ingredients">',
            '<h3 data-recipe="instructions">',
            '<h3 data-recipe="tips">'
        ]
        
        for section in required_sections:
            self.assertIn(section, response, f"Missing required section: {section}")
        
        # Check for list elements
        self.assertIn('<ul>', response, "Missing ingredients list")
        self.assertIn('<ol>', response, "Missing instructions list")
        
        # Check for actual content (not just placeholders)
        self.assertNotIn('[Recipe Name]', response, "Recipe name is still a placeholder")
        self.assertNotIn('[List ingredients]', response, "Ingredients are still a placeholder")
        self.assertNotIn('[Numbered steps]', response, "Instructions are still a placeholder")

    def test_recipe_creation(self):
        """Test creating a new recipe using LangChain"""
        message = "Can you give me a recipe for chocolate chip cookies?"
        
        # Test message classification
        message_type = classify_message_type(message)
        self.assertEqual(message_type, 'recipe_creation')
        
        # Test LangChain response
        response = get_recipe_response(self.chat, message)
        
        # Verify response format and content
        self.assert_valid_recipe_format(response)
        
        # Verify specific content
        self.assertIn('chocolate chip', response.lower(), "Recipe doesn't mention chocolate chips")
        self.assertIn('cookie', response.lower(), "Recipe doesn't mention cookies")
        
        # Verify measurements are present
        self.assertTrue(re.search(r'\d+\s*(cup|tablespoon|teaspoon|g|ml|oz)', response.lower()),
                       "Recipe doesn't include measurements")

    def test_recipe_modification(self):
        """Test modifying an existing recipe using LangChain"""
        # First create a recipe
        initial_message = "Can you give me a recipe for chocolate chip cookies?"
        initial_response = get_recipe_response(self.chat, initial_message)
        
        # Save the initial recipe
        Message.objects.create(
            chat=self.chat,
            role='assistant',
            content=initial_response,
            message_type='recipe_creation'
        )
        
        # Test modification
        modification_message = "Can you make this recipe gluten-free?"
        modification_type = classify_message_type(modification_message)
        self.assertEqual(modification_type, 'recipe_modification')
        
        # Test LangChain response for modification
        modified_response = get_recipe_response(self.chat, modification_message)
        
        # Verify modified response format and content
        self.assert_valid_recipe_format(modified_response)
        
        # Verify the modification was actually applied
        self.assertIn('gluten-free', modified_response.lower(), "Recipe wasn't modified to be gluten-free")
        
        # Verify ingredients were changed
        self.assertIn('gluten-free flour', modified_response.lower(), "Recipe doesn't use gluten-free flour")
        
        # Verify the recipe structure was maintained
        self.assertIn('chocolate chip', modified_response.lower(), "Recipe lost its chocolate chip focus")

    def test_cooking_question(self):
        """Test asking a cooking question using LangChain"""
        message = "How do I know when cookies are done baking?"
        
        # Test message classification
        message_type = classify_message_type(message)
        self.assertEqual(message_type, 'cooking_question')
        
        # Test LangChain response
        response = get_recipe_response(self.chat, message)
        
        # Verify response is helpful and doesn't contain recipe structure
        self.assertNotIn('<h2 data-recipe="title">', response)
        self.assertTrue(len(response) > 50, "Response is too short")
        
        # Verify response contains relevant information
        self.assertIn('done', response.lower(), "Response doesn't address when cookies are done")
        self.assertIn('bake', response.lower(), "Response doesn't mention baking")
        
        # Verify response is not generic
        self.assertNotIn("i'm here to help", response.lower(), "Response is too generic")
        self.assertNotIn("how can i assist", response.lower(), "Response is too generic")

    def test_end_to_end_chat(self):
        """Test a complete conversation flow through the API"""
        # Start a new chat
        response = self.client.post(
            reverse('send_message', args=[self.chat.id]),
            {'message': 'Can you give me a recipe for chocolate chip cookies?'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assert_valid_recipe_format(data['message'])
        
        # Modify the recipe
        response = self.client.post(
            reverse('send_message', args=[self.chat.id]),
            {'message': 'Can you make it with less sugar?'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assert_valid_recipe_format(data['message'])
        self.assertIn('sugar', data['message'].lower(), "Response doesn't address sugar modification")
        
        # Ask a cooking question
        response = self.client.post(
            reverse('send_message', args=[self.chat.id]),
            {'message': 'How do I know when the cookies are done?'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertNotIn('<h2 data-recipe="title">', data['message'])
        self.assertIn('done', data['message'].lower(), "Response doesn't address when cookies are done") 