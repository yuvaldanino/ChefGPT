from django.test import TransactionTestCase
from django.conf import settings
from cooking.embeddings import generate_recipe_embedding, store_recipe_embedding
import os
from dotenv import load_dotenv
from django.db import connection

load_dotenv()

class TestEmbeddings(TransactionTestCase):
    def setUp(self):
        """Set up test data."""
        self.test_recipes = {
            'cookies': {
                'title': 'Chocolate Chip Cookies',
                'cuisine': 'American',
                'difficulty': 'Easy',
                'ingredients': [
                    '2 1/4 cups flour',
                    '1 cup butter',
                    '3/4 cup sugar',
                    '2 eggs',
                    '2 cups chocolate chips'
                ],
                'instructions': [
                    'Preheat oven to 375°F',
                    'Mix butter and sugar',
                    'Add eggs and flour',
                    'Fold in chocolate chips',
                    'Bake for 10 minutes'
                ],
                'tips': [
                    'Use room temperature butter',
                    'Don\'t overmix the dough'
                ]
            },
            'pasta': {
                'title': 'Spaghetti Carbonara',
                'cuisine': 'Italian',
                'difficulty': 'Medium',
                'ingredients': [
                    '1 lb spaghetti',
                    '4 large eggs',
                    '1 cup grated Pecorino Romano',
                    '4 oz pancetta',
                    'Black pepper',
                    'Salt'
                ],
                'instructions': [
                    'Cook pasta in salted water',
                    'Crisp pancetta in a pan',
                    'Mix eggs and cheese',
                    'Combine hot pasta with egg mixture',
                    'Add pancetta and pepper'
                ],
                'tips': [
                    'Use hot pasta to cook the eggs',
                    'Don\'t add cream - it\'s not traditional'
                ]
            },
            'salad': {
                'title': 'Greek Salad',
                'cuisine': 'Greek',
                'difficulty': 'Easy',
                'ingredients': [
                    '2 large tomatoes',
                    '1 cucumber',
                    '1 red onion',
                    '200g feta cheese',
                    'Kalamata olives',
                    'Extra virgin olive oil',
                    'Dried oregano'
                ],
                'instructions': [
                    'Chop vegetables into chunks',
                    'Combine in a bowl',
                    'Add olives and feta',
                    'Drizzle with olive oil',
                    'Sprinkle with oregano'
                ],
                'tips': [
                    'Use fresh, ripe tomatoes',
                    'Don\'t refrigerate the tomatoes'
                ]
            }
        }
    
    def test_basic_recipe_embedding(self):
        """Test generating and storing a basic recipe embedding."""
        recipe = self.test_recipes['cookies']
        
        # Generate embedding
        recipe_with_embedding = generate_recipe_embedding(recipe)
        
        # Verify embedding was generated
        self.assertIn('embedding', recipe_with_embedding)
        self.assertIsInstance(recipe_with_embedding['embedding'], list)
        self.assertEqual(len(recipe_with_embedding['embedding']), 1536)
        
        # Store in Supabase
        stored_recipe = store_recipe_embedding(recipe_with_embedding)
        self.assertIsNotNone(stored_recipe)
        self.assertEqual(stored_recipe['title'], recipe['title'])
    
    def test_multiple_recipes(self):
        """Test storing multiple different recipes."""
        for recipe_name, recipe in self.test_recipes.items():
            # Generate embedding
            recipe_with_embedding = generate_recipe_embedding(recipe)
            
            # Store in Supabase
            stored_recipe = store_recipe_embedding(recipe_with_embedding)
            
            # Verify storage
            self.assertIsNotNone(stored_recipe)
            self.assertEqual(stored_recipe['title'], recipe['title'])
            self.assertEqual(stored_recipe['cuisine'], recipe['cuisine'])
            self.assertEqual(stored_recipe['difficulty'], recipe['difficulty'])
            self.assertEqual(stored_recipe['ingredients'], recipe['ingredients'])
            self.assertEqual(stored_recipe['instructions'], recipe['instructions'])
            self.assertEqual(stored_recipe['tips'], recipe['tips'])
    
    def test_recipe_variations(self):
        """Test storing variations of the same recipe."""
        base_recipe = self.test_recipes['cookies'].copy()
        
        # Create a gluten-free variation
        gf_recipe = base_recipe.copy()
        gf_recipe['title'] = 'Gluten-Free Chocolate Chip Cookies'
        gf_recipe['ingredients'] = [
            '2 1/4 cups gluten-free flour',
            '1 cup butter',
            '3/4 cup sugar',
            '2 eggs',
            '2 cups chocolate chips'
        ]
        gf_recipe['tips'].append('Use certified gluten-free ingredients')
        
        # Store both versions
        for recipe in [base_recipe, gf_recipe]:
            recipe_with_embedding = generate_recipe_embedding(recipe)
            stored_recipe = store_recipe_embedding(recipe_with_embedding)
            
            self.assertIsNotNone(stored_recipe)
            self.assertEqual(stored_recipe['title'], recipe['title'])
            self.assertEqual(stored_recipe['ingredients'], recipe['ingredients'])
    
    def tearDown(self):
        """Clean up after tests."""
        # Close all database connections
        connection.close()
        
        # Force close any remaining connections
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT pg_terminate_backend(pid) 
                FROM pg_stat_activity 
                WHERE datname = 'test_postgres'
                AND pid <> pg_backend_pid();
            """) 