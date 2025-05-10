from django.test import TransactionTestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from ..models import ChatSession, Message
from ..langchain_setup import get_recipe_response
from ..context_manager import classify_message_type
import json
import re

User = get_user_model()

class LangChainRealWorldTest(TransactionTestCase):
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

    def test_complete_recipe_conversation(self):
        """Test a complete recipe conversation with multiple modifications"""
        # Initial recipe request
        response = self.client.post(
            reverse('send_message', args=[self.chat.id]),
            {'message': 'Can you give me a recipe for chocolate chip cookies?'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        initial_recipe = data['message']
        
        # Verify initial recipe format
        self.assert_valid_recipe_format(initial_recipe)
        self.assertIn('chocolate chip', initial_recipe.lower())
        self.assertIn('cookie', initial_recipe.lower())
        
        # Modify to be gluten-free
        response = self.client.post(
            reverse('send_message', args=[self.chat.id]),
            {'message': 'Can you make this recipe gluten-free?'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        gluten_free_recipe = data['message']
        
        # Verify gluten-free modifications
        self.assert_valid_recipe_format(gluten_free_recipe)
        self.assertIn('gluten-free', gluten_free_recipe.lower())
        self.assertIn('flour', gluten_free_recipe.lower())
        
        # Modify to be healthier
        response = self.client.post(
            reverse('send_message', args=[self.chat.id]),
            {'message': 'Can you make it healthier with less sugar?'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        healthy_recipe = data['message']
        
        # Verify health modifications
        self.assert_valid_recipe_format(healthy_recipe)
        # Check for sweetener content (sugar, honey, maple syrup, etc.)
        sweetener_pattern = r'\d+\s*(cup|tablespoon|teaspoon|tbsp|tsp)\s*(of\s*)?(sugar|honey|maple syrup|sweetener)'
        sweetener_matches = re.findall(sweetener_pattern, healthy_recipe.lower())
        self.assertTrue(len(sweetener_matches) > 0, "Recipe should mention sweetener quantities")

    def test_cooking_advice_conversation(self):
        """Test a conversation about cooking techniques"""
        # Ask about baking
        response = self.client.post(
            reverse('send_message', args=[self.chat.id]),
            {'message': 'How do I know when cookies are done baking?'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        baking_advice = data['message']
        
        # Verify baking advice
        self.assertIn('bake', baking_advice.lower())
        self.assertIn('done', baking_advice.lower())
        self.assertNotIn('<h2 data-recipe="title">', baking_advice)
        
        # Follow-up question
        response = self.client.post(
            reverse('send_message', args=[self.chat.id]),
            {'message': 'What temperature should I use?'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        temp_advice = data['message']
        
        # Verify temperature advice
        self.assertIn('temperature', temp_advice.lower())
        # Check for temperature values (more flexible pattern)
        temp_pattern = r'\d+\s*(degrees?|°)?\s*(F|C|fahrenheit|celsius)?'
        self.assertTrue(re.search(temp_pattern, temp_advice.lower()), 
                       "Response should include temperature values")
        self.assertNotIn('<h2 data-recipe="title">', temp_advice)

    def test_recipe_variations(self):
        """Test requesting different variations of a recipe"""
        # Get basic recipe
        response = self.client.post(
            reverse('send_message', args=[self.chat.id]),
            {'message': 'Give me a recipe for chocolate chip cookies'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        basic_recipe = data['message']
        
        # Request vegan version
        response = self.client.post(
            reverse('send_message', args=[self.chat.id]),
            {'message': 'Can you make this recipe vegan?'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        vegan_recipe = data['message']
        
        # Verify vegan modifications
        self.assert_valid_recipe_format(vegan_recipe)
        self.assertIn('vegan', vegan_recipe.lower())
        # Check for vegan substitutions
        self.assertTrue(
            any(term in vegan_recipe.lower() for term in ['vegan butter', 'plant-based', 'dairy-free']),
            "Recipe should include vegan substitutions"
        )
        
        # Request double chocolate version
        response = self.client.post(
            reverse('send_message', args=[self.chat.id]),
            {'message': 'Can you make it double chocolate?'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        double_choc_recipe = data['message']
        
        # Verify double chocolate modifications
        self.assert_valid_recipe_format(double_choc_recipe)
        self.assertIn('chocolate', double_choc_recipe.lower())
        # Check for additional chocolate ingredients
        chocolate_terms = ['cocoa', 'chocolate chips', 'chocolate chunks', 'chocolate powder']
        self.assertTrue(
            sum(term in double_choc_recipe.lower() for term in chocolate_terms) >= 2,
            "Recipe should include multiple chocolate ingredients"
        )

    def test_error_handling(self):
        """Test how the system handles various error cases"""
        # Test with empty message
        response = self.client.post(
            reverse('send_message', args=[self.chat.id]),
            {'message': ''}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # Empty message should either fail or return a helpful message
        if data['success']:
            self.assertTrue(len(data['message']) > 0, "Empty message should return a helpful response")
        
        # Test with very long message
        long_message = "cookie" * 1000
        response = self.client.post(
            reverse('send_message', args=[self.chat.id]),
            {'message': long_message}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # Long message should either fail gracefully or return a response
        if data['success']:
            self.assertTrue(len(data['message']) > 0, "Long message should return a response")
        
        # Test with invalid chat session ID
        response = self.client.post(
            reverse('send_message', args=[99999]),
            {'message': 'Give me a cookie recipe'}
        )
        self.assertEqual(response.status_code, 404) 