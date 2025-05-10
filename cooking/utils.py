def get_recipe_metadata(content):
    """Extract metadata from recipe content."""
    metadata = {
        'difficulty': '',
        'cuisine': '',
        'prep_time': '',
        'servings': ''
    }
    
    # Extract difficulty
    difficulty_start = content.find('<h3 data-recipe="difficulty">')
    if difficulty_start != -1:
        difficulty_end = content.find('<h3', difficulty_start + 1)
        if difficulty_end != -1:
            difficulty_text = content[difficulty_start:difficulty_end]
            difficulty = difficulty_text.split('\n')[1].strip()
            metadata['difficulty'] = difficulty
    
    # Extract cuisine
    cuisine_start = content.find('<h3 data-recipe="cuisine">')
    if cuisine_start != -1:
        cuisine_end = content.find('<h3', cuisine_start + 1)
        if cuisine_end != -1:
            cuisine_text = content[cuisine_start:cuisine_end]
            cuisine = cuisine_text.split('\n')[1].strip()
            metadata['cuisine'] = cuisine
    
    # Extract prep time
    prep_time_start = content.find('<h3 data-recipe="prep-time">')
    if prep_time_start != -1:
        prep_time_end = content.find('<h3', prep_time_start + 1)
        if prep_time_end != -1:
            prep_time_text = content[prep_time_start:prep_time_end]
            prep_time = prep_time_text.split('\n')[1].strip()
            metadata['prep_time'] = prep_time
    
    # Extract servings
    servings_start = content.find('<h3 data-recipe="servings">')
    if servings_start != -1:
        servings_end = content.find('<h3', servings_start + 1)
        if servings_end != -1:
            servings_text = content[servings_start:servings_end]
            servings = servings_text.split('\n')[1].strip()
            metadata['servings'] = servings
    
    return metadata

def extract_recipe_sections(content):
    """Extract all sections from recipe content."""
    sections = {
        'ingredients': [],
        'instructions': [],
        'tips': []
    }
    
    # Extract ingredients
    ingredients_start = content.find('<h3 data-recipe="ingredients">')
    if ingredients_start != -1:
        ingredients_end = content.find('<h3', ingredients_start + 1)
        if ingredients_end != -1:
            ingredients_section = content[ingredients_start:ingredients_end]
            ingredients = [line.strip() for line in ingredients_section.split('\n') 
                         if line.strip() and not line.startswith('<')]
            sections['ingredients'] = ingredients
    
    # Extract instructions
    instructions_start = content.find('<h3 data-recipe="instructions">')
    if instructions_start != -1:
        instructions_end = content.find('<h3', instructions_start + 1)
        if instructions_end != -1:
            instructions_section = content[instructions_start:instructions_end]
            instructions = [line.strip() for line in instructions_section.split('\n') 
                          if line.strip() and not line.startswith('<')]
            sections['instructions'] = instructions
    
    # Extract tips
    tips_start = content.find('<h3 data-recipe="tips">')
    if tips_start != -1:
        tips_section = content[tips_start:]
        tips = [line.strip() for line in tips_section.split('\n') 
                if line.strip() and not line.startswith('<')]
        sections['tips'] = tips
    
    return sections 