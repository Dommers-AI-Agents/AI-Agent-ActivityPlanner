"""
AI Planner logic for activity planning and recommendations.
"""
import json
import re
from datetime import datetime, timedelta

from app.models.database import Activity, Participant, Preference, Plan
from app import db

class ActivityPlanner:
    """AI-powered activity planner for group activities."""
    
    def __init__(self, activity_id=None):
        """Initialize the planner with an activity ID."""
        self.activity_id = activity_id
        self.activity = None
        
        if activity_id:
            self.load_activity()
    
    def load_activity(self):
        """Load activity data from the database."""
        self.activity = Activity.query.get(self.activity_id)
        if not self.activity:
            raise ValueError(f"Activity with ID {self.activity_id} not found")
    
    def create_activity(self):
        """Create a new activity planning session."""
        activity = Activity(status='planning')
        db.session.add(activity)
        db.session.commit()
        
        self.activity_id = activity.id
        self.activity = activity
        
        return activity
    
    def get_response_stats(self):
        """Get participant response statistics."""
        total = len(self.participants)
        responded = sum(1 for p in self.participants if p.status != 'invited')
        completed = sum(1 for p in self.participants if p.status == 'complete')
        
        return {
            'total': total,
            'responded': responded,
            'completed': completed,
            'response_rate': (responded / total * 100) if total > 0 else 0,
            'completion_rate': (completed / total * 100) if total > 0 else 0
        }
    
    def add_participant(self, phone_number, email=None, name=None):
        """Add a participant to the activity."""
        if not self.activity:
            self.load_activity()
        
        # Check if participant with this phone number already exists
        existing = Participant.query.filter_by(
            activity_id=self.activity_id,
            phone_number=phone_number
        ).first()
        
        if existing:
            # Update existing participant
            if email and not existing.email:
                existing.email = email
            if name and not existing.name:
                existing.name = name
            db.session.commit()
            return existing
        
        # Create new participant
        participant = Participant(
            activity_id=self.activity_id,
            phone_number=phone_number,
            email=email,
            name=name,
            status='invited'
        )
        
        db.session.add(participant)
        db.session.commit()
        
        return participant
    
    def update_participant(self, participant_id, data):
        """Update participant information."""
        participant = Participant.query.get(participant_id)
        if not participant:
            raise ValueError(f"Participant with ID {participant_id} not found")
        
        # Update fields
        for key, value in data.items():
            if hasattr(participant, key):
                setattr(participant, key, value)
        
        db.session.commit()
        return participant
    
    def save_preference(self, participant_id, category, key, value):
        """Save a preference for a participant."""
        if not self.activity:
            self.load_activity()
        
        # Check if this preference already exists
        existing = Preference.query.filter_by(
            activity_id=self.activity_id,
            participant_id=participant_id,
            category=category,
            key=key
        ).first()
        
        # Serialize value if it's a dictionary or list
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        if existing:
            # Update existing preference
            existing.value = value
        else:
            # Create new preference
            preference = Preference(
                activity_id=self.activity_id,
                participant_id=participant_id,
                category=category,
                key=key,
                value=value
            )
            db.session.add(preference)
        
        db.session.commit()
    
    def get_participant_preferences(self, participant_id):
        """Get all preferences for a specific participant."""
        preferences = Preference.query.filter_by(
            activity_id=self.activity_id,
            participant_id=participant_id
        ).all()
        
        # Organize preferences by category
        result = {}
        for pref in preferences:
            if pref.category not in result:
                result[pref.category] = {}
            
            # Try to parse JSON values
            try:
                parsed_value = json.loads(pref.value)
            except (json.JSONDecodeError, TypeError):
                parsed_value = pref.value
            
            result[pref.category][pref.key] = parsed_value
        
        return result
    
    def get_all_preferences(self):
        """Get all preferences for the activity."""
        if not self.activity:
            self.load_activity()
        
        preferences = Preference.query.filter_by(activity_id=self.activity_id).all()
        
        # Organize preferences by participant and category
        result = {}
        for pref in preferences:
            participant_id = pref.participant_id or 'group'
            
            if participant_id not in result:
                result[participant_id] = {}
            
            if pref.category not in result[participant_id]:
                result[participant_id][pref.category] = {}
            
            # Try to parse JSON values
            try:
                parsed_value = json.loads(pref.value)
            except (json.JSONDecodeError, TypeError):
                parsed_value = pref.value
            
            result[participant_id][pref.category][pref.key] = parsed_value
        
        return result
    
    def generate_questions_batch(self, participant_id, previous_answers=None):
        """Generate the next batch of questions based on previous answers."""
        # In a real implementation, this would use AI to determine the next most relevant questions
        # For this example, we'll use a predefined sequence of question batches
        
        import logging
        logger = logging.getLogger('planner')
        logger.setLevel(logging.INFO)
        
        logger.info(f"Generating questions batch for participant {participant_id}")
        
        # Clear any cached data - make sure we're using fresh data
        db.session.expire_all()
        
        # Define the question batches - these should be loaded fresh each time
        question_batches = [
            # First batch - Basic info
            [
                {
                    'id': 'email',
                    'type': 'email',
                    'question': 'What is your email address?',
                    'required': True
                },
                {
                    'id': 'name',
                    'type': 'text',
                    'question': 'What is your name?',
                    'required': True
                },
                {
                    'id': 'allow_group_text',
                    'type': 'boolean',
                    'question': 'Would you like to be included in a group text for this activity?',
                    'required': True
                }
            ],
            # Second batch - Budget and Activity Type
            [
                {
                    'id': 'budget_range',
                    'type': 'select',
                    'question': 'How much would you be open to spending on a fun activity?',
                    'options': ['$10 or less', '$25', '$50', '$100 or more'],
                    'required': True
                },
                {
                    'id': 'activity_type',
                    'type': 'multiselect',
                    'question': 'What types of activities are you interested in?',
                    'options': ['Outdoor', 'Indoor', 'Cultural', 'Educational', 'Relaxation', 'Food', 'Sports', 'Adventure', 'Art', 'Music'],
                    'required': True
                },
                {
                    'id': 'meals_included',
                    'type': 'multiselect',
                    'question': 'Would you like this activity to include meals?',
                    'options': ['Breakfast', 'Lunch', 'Dinner', 'Snacks only', 'No meals needed'],
                    'required': True
                }
            ],
            # Third batch - Physical Activity and Timing
            [
                {
                    'id': 'physical_exertion',
                    'type': 'select',
                    'question': 'How much physical exertion would you like on a scale from 0-10? (2 = casual walking, 10 = hiking a mountain)',
                    'options': ['0-1 (Very minimal)', '2-3 (Casual walking)', '4-5 (Moderate activity)', '6-7 (Somewhat active)', '8-10 (Very active)'],
                    'required': True
                },
                {
                    'id': 'preferred_day',
                    'type': 'select',
                    'question': 'What day would you prefer for this activity?',
                    'options': ['Weekday morning', 'Weekday afternoon', 'Weekday evening', 'Weekend morning', 'Weekend afternoon', 'Weekend evening'],
                    'required': True
                },
                {
                    'id': 'duration',
                    'type': 'select',
                    'question': 'How long would you like the activity to be?',
                    'options': ['1-2 hours', '2-4 hours', 'Half day (4-6 hours)', 'Full day (6+ hours)'],
                    'required': True
                }
            ],
            # Fourth batch - Social and Experience Preferences
            [
                {
                    'id': 'group_size',
                    'type': 'select',
                    'question': 'What group size do you prefer for this activity?',
                    'options': ['Small (2-4 people)', 'Medium (5-8 people)', 'Large (9+ people)', 'No preference'],
                    'required': True
                },
                {
                    'id': 'learning_preference',
                    'type': 'select',
                    'question': 'Would you prefer an activity where you:',
                    'options': ['Learn something new', 'Practice existing skills', 'Just have fun (no learning)'],
                    'required': True
                },
                {
                    'id': 'social_level',
                    'type': 'select',
                    'question': 'How social would you like this activity to be?',
                    'options': ['Highly interactive with others', 'Some interaction', 'Minimal interaction', 'No preference'],
                    'required': True
                }
            ],
            # Fifth batch - Special requirements and Direct Input
            [
                {
                    'id': 'dietary_restrictions',
                    'type': 'text',
                    'question': 'Do you have any dietary restrictions or preferences we should consider?',
                    'required': False
                },
                {
                    'id': 'accessibility_needs',
                    'type': 'text',
                    'question': 'Do you have any accessibility requirements we should know about?',
                    'required': False
                },
                {
                    'id': 'direct_input',
                    'type': 'textarea',
                    'question': 'Is there anything specific you\'d like to do or additional information you\'d like to share? Feel free to directly interact with our AI here to express your preferences.',
                    'required': False
                }
            ]
        ]
        
        # Get the preferences for this participant
        preferences = self.get_participant_preferences(participant_id)
        logger.info(f"Participant preferences: {preferences}")
        
        # Check if participant has already answered contact questions
        if 'contact' in preferences:
            # Map category names to batch indexes
            category_to_batch = {
                'contact': 0,
                'activity': 1,  # budget_range, activity_type
                'meals': 1,     # meals_included
                'timing': 2,    # physical_exertion, preferred_day, duration
                'group': 3,     # group_size, social_level
                'requirements': 4  # dietary_restrictions, etc
            }
            
            # Determine the highest batch completed
            highest_batch = 0
            for category in preferences.keys():
                if category in category_to_batch and category_to_batch[category] > highest_batch:
                    highest_batch = category_to_batch[category]
            
            logger.info(f"Highest batch completed: {highest_batch}")
            
            # If we've finished the first batch, we provide the next batch
            next_batch = highest_batch + 1
            
            # If the next batch is available, return it
            if next_batch < len(question_batches):
                logger.info(f"Returning batch {next_batch}: {question_batches[next_batch][0]['question']}")
                return question_batches[next_batch]
            else:
                logger.info("No more batches available")
                return None
        else:
            # If contact info hasn't been provided yet, return the first batch
            logger.info("No contact info yet, returning first batch")
            return question_batches[0]
    
    def generate_plan(self):
        """Generate an activity plan based on all preferences."""
        if not self.activity:
            self.load_activity()
        
        # Get all preferences
        all_preferences = self.get_all_preferences()
        
        # Extract preferences for the plan
        activity_types = []
        durations = []
        preferred_days = []
        budget_ranges = []
        physical_exertion_levels = []
        meals_included = []
        direct_inputs = []
        
        for participant_id, categories in all_preferences.items():
            if participant_id == 'group':
                continue
                
            # Activity types
            if 'activity' in categories and 'activity_type' in categories['activity']:
                activity_type = categories['activity']['activity_type']
                if isinstance(activity_type, list):
                    activity_types.extend(activity_type)
                else:
                    activity_types.append(activity_type)
            
            # Duration preferences
            if 'timing' in categories and 'duration' in categories['timing']:
                durations.append(categories['timing']['duration'])
            
            # Day preferences
            if 'timing' in categories and 'preferred_day' in categories['timing']:
                preferred_days.append(categories['timing']['preferred_day'])
                
            # Budget preferences
            if 'activity' in categories and 'budget_range' in categories['activity']:
                budget_ranges.append(categories['activity']['budget_range'])
                
            # Physical exertion levels
            if 'activity' in categories and 'physical_exertion' in categories['activity']:
                physical_exertion_levels.append(categories['activity']['physical_exertion'])
                
            # Meals included
            if 'meals' in categories and 'meals_included' in categories['meals']:
                meals = categories['meals']['meals_included']
                if isinstance(meals, list):
                    meals_included.extend(meals)
                else:
                    meals_included.append(meals)
                    
            # Direct inputs
            if 'requirements' in categories and 'direct_input' in categories['requirements']:
                input_text = categories['requirements']['direct_input']
                if input_text and len(input_text.strip()) > 0:
                    direct_inputs.append(input_text)
        
        # Count frequencies to determine most popular choices
        def most_common(lst):
            if not lst:
                return None
            return max(set(lst), key=lst.count)
        
        most_common_activity = most_common(activity_types) if activity_types else "Outdoor"
        most_common_duration = most_common(durations) if durations else "2-4 hours"
        most_common_day = most_common(preferred_days) if preferred_days else "Weekend morning"
        most_common_budget = most_common(budget_ranges) if budget_ranges else "$25"
        most_common_exertion = most_common(physical_exertion_levels) if physical_exertion_levels else "2-3 (Casual walking)"
        
        # Process the day preference
        day_part = "morning"
        if "afternoon" in most_common_day.lower():
            day_part = "afternoon"
        elif "evening" in most_common_day.lower():
            day_part = "evening"
            
        is_weekend = "weekend" in most_common_day.lower()
        day_type = "Weekend" if is_weekend else "Weekday"
        
        # Generate activity options based on preferences
        activities = {
            "Outdoor": ["Park Visit", "Nature Trail", "Botanical Gardens", "Lake Day"],
            "Indoor": ["Museum Visit", "Art Gallery", "Escape Room", "Board Game Cafe"],
            "Cultural": ["Local Festival", "Historical Tour", "Cultural Museum", "Live Music"],
            "Educational": ["Science Museum", "Workshop", "Guided Tour", "Library Event"],
            "Relaxation": ["Spa Day", "Picnic", "Beach Day", "Yoga Session"],
            "Food": ["Food Tour", "Cooking Class", "Restaurant Hopping", "Farmers Market"],
            "Sports": ["Mini Golf", "Bowling", "Frisbee in the Park", "Bike Ride"],
            "Adventure": ["Zip-lining", "Rock Climbing", "Kayaking", "Hiking"],
            "Art": ["Painting Class", "Pottery Workshop", "Art Gallery Tour", "Craft Session"],
            "Music": ["Concert", "Music Festival", "Karaoke Night", "Live Music Venue"]
        }
        
        # Select activity based on physical exertion preference
        activity_options = activities.get(most_common_activity, ["Group Outing"])
        activity_name = activity_options[0]
        
        # Generate a plan title
        title = f"{activity_name} - {day_type} {day_part.capitalize()} Activity"
        
        # Create a description based on preferences
        exertion_level = "low-impact" if "0-1" in most_common_exertion or "2-3" in most_common_exertion else (
            "moderate" if "4-5" in most_common_exertion or "6-7" in most_common_exertion else "high-energy"
        )
        
        # Get group composition information
        has_children = any(
            'group' in categories and 'has_children' in categories['group'] and categories['group']['has_children']
            for participant_id, categories in all_preferences.items() if participant_id != 'group'
        )
        
        has_seniors = any(
            'group' in categories and 'has_seniors' in categories['group'] and categories['group']['has_seniors']
            for participant_id, categories in all_preferences.items() if participant_id != 'group'
        )
        
        # Handle meals
        meal_preferences = set(meals_included)
        include_meals = not ("No meals needed" in meal_preferences and len(meal_preferences) == 1)
        
        # Format meal options
        meal_text = ""
        if include_meals:
            selected_meals = [meal for meal in meal_preferences if meal != "No meals needed"]
            if "Breakfast" in selected_meals:
                meal_text += "breakfast "
            if "Lunch" in selected_meals:
                meal_text += "lunch "
            if "Dinner" in selected_meals:
                meal_text += "dinner "
            if "Snacks only" in selected_meals:
                meal_text = "snacks "
                
            meal_text = meal_text.strip().replace(" ", ", ")
            if "," in meal_text:
                last_comma = meal_text.rindex(",")
                meal_text = meal_text[:last_comma] + " and" + meal_text[last_comma+1:]
        
        # Build description
        description_parts = [
            f"A {exertion_level}, {most_common_duration} {most_common_activity.lower()} activity for your group on a {day_type.lower()} {day_part}.",
            f"This activity fits within a budget of approximately {most_common_budget} per person."
        ]
        
        if include_meals:
            description_parts.append(f"The plan includes {meal_text}.")
        
        if has_children:
            description_parts.append("This plan includes child-friendly options.")
            
        if has_seniors:
            description_parts.append("The activity is accessible for seniors and those with mobility concerns.")
            
        # Include direct input feedback
        if direct_inputs:
            description_parts.append("\nAdditional participant requests incorporated into this plan:")
            for input_text in direct_inputs[:3]:  # Limit to first 3 inputs
                description_parts.append(f"- {input_text}")
                
        # Add a generic schedule based on day part and duration
        now = datetime.now()
        start_date = now + timedelta(days=(5 if is_weekend else 3))
        
        # Adjust to be on a weekend if requested
        if is_weekend and start_date.weekday() < 5:  # 5 = Saturday, 6 = Sunday
            days_to_saturday = 5 - start_date.weekday()
            start_date = start_date + timedelta(days=days_to_saturday)
            
        # Create time slots based on duration and day part
        schedule = []
        start_time = ""
        
        if day_part == "morning":
            start_time = "9:00 AM"
        elif day_part == "afternoon":
            start_time = "1:00 PM"
        else:  # evening
            start_time = "5:00 PM"
        
        # Parse duration into hours
        duration_hours = 2
        if "2-4" in most_common_duration:
            duration_hours = 3
        elif "Half day" in most_common_duration:
            duration_hours = 5
        elif "Full day" in most_common_duration:
            duration_hours = 8
        
        # Generate schedule based on start time and duration
        schedule = self._generate_schedule(start_time, duration_hours, meal_preferences)
        
        # Format full description with schedule
        description = " ".join(description_parts) + "\n\n"
        description += f"Proposed Date: {start_date.strftime('%A, %B %d, %Y')}\n\n"
        description += "Tentative Schedule:\n"
        for item in schedule:
            description += f"{item['time']} - {item['activity']}\n"
            
        # Create the plan
        plan = Plan(
            activity_id=self.activity_id,
            title=title,
            description=description,
            scheduled_date=self.activity.proposed_date,  # Copy date from activity
            time_window=self.activity.time_window,      # Copy time window from activity
            start_time=self.activity.start_time,        # Copy start time from activity
            location_address=self.activity.location_address,  # Copy address from activity
            schedule=json.dumps(schedule),
            status='draft'
        )
        
        db.session.add(plan)
        db.session.commit()
        
        # Update activity status
        self.activity.status = 'planned'
        db.session.commit()
        
        return plan
        
    def _generate_schedule(self, start_time_str, duration_hours, meal_preferences):
        """Helper method to generate a schedule based on start time and duration."""
        from datetime import datetime, timedelta
        
        # Parse start time
        start_time = datetime.strptime(start_time_str, "%I:%M %p")
        
        # Determine if we should include meals
        include_breakfast = "Breakfast" in meal_preferences
        include_lunch = "Lunch" in meal_preferences
        include_dinner = "Dinner" in meal_preferences
        include_snacks = "Snacks only" in meal_preferences or len(meal_preferences) > 0
        
        # Create schedule
        schedule = []
        current_time = start_time
        
        # Add meeting time
        schedule.append({
            "time": current_time.strftime("%-I:%M %p"),
            "activity": "Meet at the location"
        })
        
        # Add 15 minutes for everyone to arrive
        current_time = current_time + timedelta(minutes=15)
        
        # Start activity
        schedule.append({
            "time": current_time.strftime("%-I:%M %p"),
            "activity": "Activity begins"
        })
        
        # Morning schedule (if starting in morning)
        morning_hours = 0
        if start_time.hour < 11:
            morning_hours = min(duration_hours, 12 - start_time.hour)
            
            # Add breakfast if needed
            if include_breakfast and start_time.hour <= 9:
                breakfast_time = start_time + timedelta(hours=1)
                schedule.append({
                    "time": breakfast_time.strftime("%-I:%M %p"),
                    "activity": "Breakfast"
                })
                current_time = breakfast_time + timedelta(minutes=45)
            else:
                # Morning activity continues
                current_time = current_time + timedelta(hours=1.5)
                
            # Add mid-morning break with snacks if appropriate
            if include_snacks and morning_hours > 2 and start_time.hour < 10:
                schedule.append({
                    "time": current_time.strftime("%-I:%M %p"),
                    "activity": "Morning break with snacks"
                })
                current_time = current_time + timedelta(minutes=20)
                
        # Afternoon portion
        afternoon_hours = 0
        if (start_time.hour + duration_hours > 12) and start_time.hour < 17:
            afternoon_start = max(current_time, datetime(start_time.year, start_time.month, start_time.day, 12, 0))
            afternoon_end = min(datetime(start_time.year, start_time.month, start_time.day, 17, 0), 
                               start_time + timedelta(hours=duration_hours))
            afternoon_hours = (afternoon_end - afternoon_start).total_seconds() / 3600
            
            # Add lunch if needed
            if include_lunch and ((12 <= start_time.hour <= 13) or (duration_hours > 3 and start_time.hour < 12)):
                lunch_time = max(current_time, datetime(start_time.year, start_time.month, start_time.day, 12, 30))
                schedule.append({
                    "time": lunch_time.strftime("%-I:%M %p"),
                    "activity": "Lunch break"
                })
                current_time = lunch_time + timedelta(hours=1)
            
            if afternoon_hours > 1:
                schedule.append({
                    "time": current_time.strftime("%-I:%M %p"),
                    "activity": "Afternoon activity"
                })
                current_time = current_time + timedelta(hours=1.5)
                
                # Add afternoon snack if appropriate
                if include_snacks and afternoon_hours > 3:
                    schedule.append({
                        "time": current_time.strftime("%-I:%M %p"),
                        "activity": "Afternoon break with refreshments"
                    })
                    current_time = current_time + timedelta(minutes=20)
        
        # Evening portion
        evening_hours = 0
        if (start_time.hour + duration_hours > 17):
            evening_start = max(current_time, datetime(start_time.year, start_time.month, start_time.day, 17, 0))
            evening_end = start_time + timedelta(hours=duration_hours)
            evening_hours = (evening_end - evening_start).total_seconds() / 3600
            
            if evening_hours > 0:
                schedule.append({
                    "time": evening_start.strftime("%-I:%M %p"),
                    "activity": "Evening activity"
                })
                current_time = evening_start + timedelta(hours=1)
                
            # Add dinner if needed
            if include_dinner and (current_time.hour >= 17 or 
                                  (start_time.hour + duration_hours > 19 and current_time.hour >= 16)):
                dinner_time = max(current_time, datetime(start_time.year, start_time.month, start_time.day, 18, 0))
                schedule.append({
                    "time": dinner_time.strftime("%-I:%M %p"),
                    "activity": "Dinner"
                })
                current_time = dinner_time + timedelta(hours=1.5)
                
        # Add conclusion
        end_time = start_time + timedelta(hours=duration_hours)
        schedule.append({
            "time": end_time.strftime("%-I:%M %p"),
            "activity": "Activity concludes"
        })
        
        return schedule
    
    def process_conversation_input(self, input_text):
        """Process conversational input and generate a plan based on minimal information."""
        import json
        import re
        from datetime import datetime, timedelta
        import random
        
        # Extract basic information from text
        group_size = 8  # Default
        activity_level = "low"  # Default
        budget = "$25 per person"  # Default
        
        # Basic parsing of input text
        if re.search(r'(\d+)\s+people', input_text, re.IGNORECASE):
            group_size = int(re.search(r'(\d+)\s+people', input_text, re.IGNORECASE).group(1))
        
        # Extract activity level preference
        if any(word in input_text.lower() for word in ["inactive", "nothing too active", "low", "easy", "simple"]):
            activity_level = "low"
        elif any(word in input_text.lower() for word in ["active", "energetic", "sports", "workout"]):
            activity_level = "high"
        else:
            activity_level = "moderate"
        
        # Extract budget if mentioned
        budget_match = re.search(r'\$(\d+)', input_text)
        if budget_match:
            budget = f"${budget_match.group(1)} per person"
        
        # Define activity options based on activity level
        low_activities = ["Casual Dinner", "Board Game Night", "Movie Night", "Art Gallery Visit", "Wine Tasting"]
        moderate_activities = ["Bowling", "Mini Golf", "Easy Hike", "Museum Tour", "Cooking Class"]
        high_activities = ["Bike Ride", "Kayaking", "Hiking Trip", "Sports Tournament", "Dance Class"]
        
        # Choose appropriate activity based on activity level
        if activity_level == "low":
            activity_name = random.choice(low_activities)
        elif activity_level == "high":
            activity_name = random.choice(high_activities)
        else:
            activity_name = random.choice(moderate_activities)
        
        # Generate plan title
        title = f"{activity_name} for {group_size} People"
        
        # Generate plan description
        description = f"A {activity_level}-impact activity for a group of {group_size} people.\n\n"
        description += f"This plan includes {activity_name.lower()} with an approximate budget of {budget}.\n\n"
        
        # Add detailed description based on activity
        if "Dinner" in activity_name:
            description += "The group will enjoy dinner at a restaurant with a relaxed atmosphere, perfect for conversation and bonding."
        elif "Game" in activity_name:
            description += "The group will enjoy a selection of board games suitable for players of all experience levels."
        elif "Movie" in activity_name:
            description += "The group will enjoy watching a film together, followed by discussion time."
        elif "Hike" in activity_name or "Bike" in activity_name:
            description += "The group will enjoy an outdoor activity on a scenic trail suitable for the desired activity level."
        
        # Create a simple schedule
        start_time = datetime.now().replace(hour=18, minute=0, second=0)  # Default to 6 PM
        duration = 3  # hours
        
        schedule = []
        current_time = start_time
        
        # Add meeting time
        schedule.append({
            "time": current_time.strftime("%-I:%M %p"),
            "activity": "Meet at the venue"
        })
        
        # Add start of activity
        current_time = current_time + timedelta(minutes=15)
        schedule.append({
            "time": current_time.strftime("%-I:%M %p"),
            "activity": f"Begin {activity_name}"
        })
        
        # Add break if duration is long enough
        if duration > 2:
            current_time = current_time + timedelta(hours=1, minutes=30)
            schedule.append({
                "time": current_time.strftime("%-I:%M %p"),
                "activity": "Break for refreshments"
            })
        
        # Add end time
        current_time = start_time + timedelta(hours=duration)
        schedule.append({
            "time": current_time.strftime("%-I:%M %p"),
            "activity": "Activity concludes"
        })
        
        # Create plan in database
        plan = Plan(
            activity_id=self.activity_id,
            title=title,
            description=description,
            scheduled_date=self.activity.proposed_date if self.activity else None,  # Copy date from activity
            time_window=self.activity.time_window if self.activity else None,      # Copy time window from activity
            start_time=self.activity.start_time if self.activity else None,        # Copy start time from activity
            location_address=self.activity.location_address if self.activity else None,  # Copy address from activity
            schedule=json.dumps(schedule),
            status='draft'
        )
        
        db.session.add(plan)
        db.session.commit()
        
        # Update activity status
        self.activity.status = 'planned'
        db.session.commit()
    
        return plan

    def revise_plan(self, plan_id, feedback, participant_id=None):
        """Revise an existing plan based on feedback."""
        from flask import current_app
        
        plan = Plan.query.get(plan_id)
        if not plan:
            raise ValueError(f"Plan with ID {plan_id} not found")
            
        # Store the feedback - with extra logging
        if participant_id:
            current_app.logger.info(f"Inside revise_plan: Saving feedback for participant {participant_id}")
            self.save_preference(participant_id, 'feedback', 'plan_feedback', feedback)
            
            # Verify the save worked
            saved_prefs = Preference.query.filter_by(
                activity_id=self.activity_id,
                participant_id=participant_id,
                category='feedback',
                key='plan_feedback'
            ).all()
            current_app.logger.info(f"Inside revise_plan: Found {len(saved_prefs)} feedback preferences after saving")
        
        # Get all feedback for this plan
        all_feedback = []
        for participant in Participant.query.filter_by(activity_id=self.activity_id).all():
            participant_prefs = self.get_participant_preferences(participant.id)
            if 'feedback' in participant_prefs and 'plan_feedback' in participant_prefs['feedback']:
                all_feedback.append({
                    'participant_id': participant.id,
                    'participant_name': participant.name,
                    'feedback': participant_prefs['feedback']['plan_feedback']
                })
        
        # In a real implementation, this would use AI to revise the plan
        # based on all feedback collected
        
        # For this example, create a revised plan incorporating feedback
        revised_description = plan.description + "\n\nRevisions based on feedback:\n"
        for fb in all_feedback:
            revised_description += f"- {fb['participant_name'] or 'Anonymous'}: {fb['feedback']}\n"
        
        # Create new plan object with revised content
        revised_plan = Plan(
            activity_id=self.activity_id,
            title=f"Revised: {plan.title}",
            description=revised_description,
            schedule=plan.schedule,  # Reuse schedule for simplicity
            status='revised'
        )
        
        db.session.add(revised_plan)
        db.session.commit()
        
        return revised_plan
    
    def create_plan_from_claude(self, claude_plan):
        from flask import current_app
        
        if not self.activity:
            self.load_activity()
    
        # Extract plan details from Claude's response
        title = claude_plan.get('title', 'Group Activity Plan')
        description = claude_plan.get('description', '')
        
        # Add considerations to the description if provided
        considerations = claude_plan.get('considerations')
        if considerations:
            description += f"\n\nSpecial Considerations:\n{considerations}"
        
        # Add alternatives to the description if provided
        alternatives = claude_plan.get('alternatives')
        if alternatives and isinstance(alternatives, list):
            description += "\n\nAlternative Options:\n"
            for i, alt in enumerate(alternatives, 1):
                description += f"{i}. {alt}\n"
        
        # Process schedule
        schedule = claude_plan.get('schedule', [])
        
        # Convert schedule to JSON string
        schedule_json = json.dumps(schedule)
        
        try:
            # Create the plan
            plan = Plan(
                activity_id=self.activity_id,
                title=title,
                description=description,
                schedule=schedule_json,
                status='draft'
            )
            
            db.session.add(plan)
            db.session.commit()
            
            # Update activity status
            self.activity.status = 'planned'
            db.session.commit()
            
            return plan
        except Exception as e:
            current_app.logger.error(f"Error creating plan from Claude response: {str(e)}")
            # Roll back session if error
            db.session.rollback()
            raise

    def get_claude_conversation(self, participant_id=None):
        """Get conversation history with AI for a participant or activity creator.
        
        Args:
            participant_id (str, optional): The participant ID. If None, get creator conversation.
            
        Returns:
            list: The conversation history.
        """
        from app.models.database import Message
        
        if not self.activity:
            if not self.activity_id:
                return []
            self.load_activity()
        
        # Query messages from the database
        query = Message.query.filter(Message.activity_id == self.activity_id)
        
        if participant_id:
            query = query.filter(Message.participant_id == participant_id)
        else:
            # For creator, participant_id is None
            query = query.filter(Message.participant_id.is_(None))
        
        # Order by creation time
        messages = query.order_by(Message.created_at).all()
        
        # Convert to the format expected by Claude service
        conversation = []
        for msg in messages:
            role = "user" if msg.direction == "incoming" else "assistant"
            conversation.append({
                "role": role,
                "content": msg.content
            })
        
        return conversation

    def save_conversation_message(self, message, is_user=True, participant_id=None):
        """Save a message in the conversation history.
        
        Args:
            message (str): The message content.
            is_user (bool): Whether this is a user message.
            participant_id (str, optional): The participant ID. If None, this is a creator message.
            
        Returns:
            Message: The saved message.
        """
        from app.models.database import Message
        from flask import current_app
        
        try:
            if not self.activity:
                if not self.activity_id:
                    raise ValueError("No activity ID provided")
                self.load_activity()
            
            # Create message
            direction = "incoming" if is_user else "outgoing"
            channel = "web"  # Or "voice" if implemented
            
            # Ensure message is a string
            if not isinstance(message, str):
                message = str(message)
            
            message_obj = Message(
                activity_id=self.activity_id,
                participant_id=participant_id,
                direction=direction,
                channel=channel,
                content=message
            )
            
            current_app.db.session.add(message_obj)
            current_app.db.session.commit()
            
            return message_obj
            
        except Exception as e:
            current_app.logger.error(f"Error saving conversation message: {str(e)}")
            # Try to roll back the session if there was an error
            try:
                current_app.db.session.rollback()
            except:
                pass
            
            # Return None to indicate failure, but don't crash
            return None

    def process_claude_input(self, message, participant_id=None, conversation_history=None):
        """Process user input with Claude and save results.
        
        Args:
            message (str): The user message.
            participant_id (str, optional): The participant ID. If None, this is from the creator.
            conversation_history (list, optional): The conversation history.
                If None, it will be loaded from the database.
                
        Returns:
            dict: Claude's response with extracted information/preferences.
        """
        from app.services.claude_service import claude_service
        from flask import current_app
        
        if not conversation_history:
            conversation_history = self.get_claude_conversation(participant_id)
        
        # Log the request to Claude
        current_app.logger.info(f"Sending request to Claude API with message: {message[:100]}...")
        
        try:
            # Process with Claude
            if participant_id:
                # Get activity info
                activity_info = {
                    'title': self.activity.title,
                    'description': self.activity.description,
                    'status': self.activity.status
                }
                
                # Process participant input
                result = claude_service.process_participant_input(
                    message,
                    conversation_history,
                    activity_info
                )
                
                # Save extracted preferences
                if result.get('extracted_preferences'):
                    preferences = result['extracted_preferences']
                    
                    for category, prefs in preferences.items():
                        for key, value in prefs.items():
                            if value:  # Only save if we have a value
                                self.save_preference(participant_id, category, key, value)
            else:
                # Process creator input
                result = claude_service.process_activity_creator_input(message, conversation_history)
            
            # Log Claude's response
            current_app.logger.info(f"Claude API response: {result.get('message', '')[:100]}...")
            
            # Save the assistant's response
            self.save_conversation_message(result.get('message', ''), is_user=False, participant_id=participant_id)
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error processing Claude input: {str(e)}")
            
            # Generate a fallback response
            fallback_response = {
                "message": "I'm sorry, I'm having trouble connecting to my language processing system. Let me try to understand your request based on keywords instead.",
                "extracted_info": {}
            }
            
            # Save the fallback response
            self.save_conversation_message(fallback_response["message"], is_user=False, participant_id=participant_id)
            
            return fallback_response

    def analyze_feedback_with_claude(self, plan_id):
        """Analyze feedback from all participants and generate suggestions for plan improvements.
        
        Args:
            plan_id (str): The plan ID to analyze feedback for.
            
        Returns:
            AISuggestion: The AI suggestion object with recommended changes.
        """
        from app.models.database import AISuggestion, Preference
        from app.services.claude_service import claude_service
        from flask import current_app
        
        plan = Plan.query.get(plan_id)
        if not plan:
            raise ValueError(f"Plan with ID {plan_id} not found")
        
        # Get all feedback for this activity
        feedback_list = Preference.get_feedback_for_activity(self.activity_id)
        
        # If no feedback is available, use a placeholder for Claude to just analyze the plan itself
        if not feedback_list:
            feedback_list = [{
                'participant_name': 'System',
                'feedback': 'No participant feedback available yet. Please analyze the plan for any potential improvements.',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M')
            }]
        
        # Get current plan details
        current_plan = {
            'title': plan.title,
            'description': plan.description,
            'scheduled_date': plan.scheduled_date.strftime('%Y-%m-%d') if plan.scheduled_date else None,
            'time_window': plan.time_window,
            'start_time': plan.start_time,
            'location_address': plan.location_address,
            'schedule': json.loads(plan.schedule) if plan.schedule else []
        }
        
        # Construct prompt for Claude
        system_prompt = """
        You are an AI-powered Activity Planner that analyzes plans and suggests improvements.
        
        Your task is to:
        1. Review the current plan and any available feedback from participants
        2. Identify potential improvements or enhancements to the plan
        3. Recommend specific changes to improve the plan
        4. Create a clear summary of your recommendations
        
        Format your response as JSON with the following structure:
        {
            "summary": "A concise summary of your analysis and overall recommendations",
            "changes": [
                "Specific change #1 recommendation",
                "Specific change #2 recommendation"
            ],
            "revised_title": "Suggested new title if needed",
            "revised_description": "Suggested revised description if needed",
            "revised_date": "YYYY-MM-DD (only if date change is suggested)",
            "revised_start_time": "HH:MM (only if time change is suggested)",
            "revised_location": "New location address (only if location change is suggested)"
        }
        """
        
        # Format feedback for the prompt
        feedback_text = ""
        for i, fb in enumerate(feedback_list, 1):
            feedback_text += f"Feedback #{i} from {fb['participant_name']}:\n{fb['feedback']}\n\n"
        
        message = f"""
        I need to analyze{' participant feedback for' if len(feedback_list) > 1 else ''} an activity plan and suggest improvements.
        
        Current plan details:
        
        Title: {current_plan['title']}
        Date: {current_plan['scheduled_date'] or 'Not specified'}
        Time: {current_plan['start_time'] or 'Not specified'} ({current_plan['time_window'] or 'No time window specified'})
        Location: {current_plan['location_address'] or 'Not specified'}
        
        Description:
        {current_plan['description']}
        
        Schedule:
        {json.dumps(current_plan['schedule'], indent=2) if current_plan['schedule'] else 'No detailed schedule'}
        
        {'Participant Feedback:' if len(feedback_list) > 1 or feedback_list[0]['participant_name'] != 'System' else 'Note:'}
        {feedback_text}
        
        {'Please analyze this feedback and suggest changes to improve the plan. Focus on addressing the most important concerns while staying true to the original activity concept.' if len(feedback_list) > 1 or feedback_list[0]['participant_name'] != 'System' else 'Please analyze this plan and suggest potential improvements or enhancements. Even though there is no participant feedback yet, identify any areas that could be improved or clarified to create a better experience.'}
        """
        
        try:
            # Call Claude API
            messages = [{"role": "user", "content": message}]
            response = claude_service._call_claude_api(system_prompt, messages)
            
            # Parse the response
            response_content = response.get("content", [])[0].get("text", "")
            
            try:
                # Parse JSON response - first clean it up to avoid parsing issues
                clean_response = response_content.strip()
                
                # If it starts with markdown JSON code block, remove it
                if clean_response.startswith("```json"):
                    end_marker = "```"
                    if end_marker in clean_response:
                        clean_response = clean_response[7:clean_response.rindex(end_marker)].strip()
                
                # Try to parse as JSON
                suggestion_data = json.loads(clean_response)
                
                # Create AISuggestion object
                suggestion = AISuggestion(
                    plan_id=plan_id,
                    activity_id=self.activity_id,
                    summary=suggestion_data.get('summary', 'No summary provided'),
                    changes=json.dumps(suggestion_data.get('changes', [])),
                )
                
                # Log the data we're saving
                current_app.logger.info(f"Saving AI suggestion with summary: {suggestion.summary[:100]}...")
                current_app.logger.info(f"Changes: {suggestion.changes[:100]}...")
                
                # Save the suggestion to database
                db.session.add(suggestion)
                db.session.commit()
                
                return suggestion
                
            except json.JSONDecodeError as e:
                # Handle non-JSON response
                current_app.logger.error(f"Failed to parse Claude response as JSON: {e}")
                current_app.logger.error(f"Response content: {response_content[:500]}")
                
                # Try to extract useful content from the response
                # Even if it's not valid JSON, see if we can parse out suggestions
                suggestions = []
                
                # Look for potential suggestions in the text
                if "recommendations" in response_content.lower() or "suggestions" in response_content.lower() or "changes" in response_content.lower():
                    lines = response_content.split('\n')
                    for line in lines:
                        # Look for bullet points or numbered items that might be suggestions
                        if line.strip().startswith('-') or line.strip().startswith('*') or re.match(r'^\d+\.', line.strip()):
                            suggestions.append(line.strip())
                
                # If we couldn't find any suggestions, use a default message
                if not suggestions:
                    suggestions = ["Please review the plan and feedback manually and make appropriate changes."]
                
                # Create a suggestion with the extracted suggestions or default
                suggestion = AISuggestion(
                    plan_id=plan_id,
                    activity_id=self.activity_id,
                    summary=f"Claude analyzed {len(feedback_list)} pieces of feedback but provided an unstructured response.",
                    changes=json.dumps(suggestions)
                )
                
                db.session.add(suggestion)
                db.session.commit()
                
                return suggestion
                
        except Exception as e:
            current_app.logger.error(f"Error analyzing feedback with Claude: {str(e)}")
            raise
    
    def apply_ai_suggestions(self, suggestion_id):
        """Apply AI suggestions to create a new plan version.
        
        Args:
            suggestion_id (str): The AI suggestion ID to apply.
            
        Returns:
            Plan: The updated plan with applied suggestions.
        """
        from app.models.database import AISuggestion, Plan
        
        # Get the suggestion
        suggestion = AISuggestion.query.get(suggestion_id)
        if not suggestion:
            raise ValueError(f"Suggestion with ID {suggestion_id} not found")
        
        # Get the original plan
        original_plan = Plan.query.get(suggestion.plan_id)
        if not original_plan:
            raise ValueError(f"Original plan with ID {suggestion.plan_id} not found")
        
        # Get suggestion data
        suggestion_data = {}
        try:
            # Try to parse the suggestion response as JSON
            suggestion_data = json.loads(suggestion.changes)
        except (json.JSONDecodeError, TypeError):
            # If it's not valid JSON, use an empty dict
            suggestion_data = {}
        
        # Create a new revised plan
        revised_plan = Plan(
            activity_id=self.activity_id,
            title=suggestion_data.get('revised_title', f"Revised: {original_plan.title}"),
            description=suggestion_data.get('revised_description', original_plan.description),
            scheduled_date=original_plan.scheduled_date,
            time_window=original_plan.time_window,
            start_time=suggestion_data.get('revised_start_time', original_plan.start_time),
            location_address=suggestion_data.get('revised_location', original_plan.location_address),
            schedule=original_plan.schedule,  # Keep original schedule for now
            status='revised'
        )
        
        # Add a note about the AI-suggested changes
        if suggestion.summary:
            revised_plan.description += f"\n\nRevisions based on AI analysis of participant feedback:\n{suggestion.summary}"
        
        db.session.add(revised_plan)
        db.session.commit()
        
        return revised_plan
    
    def update_plan_manually(self, plan_id, updated_data):
        """Update a plan manually with provided data.
        
        Args:
            plan_id (str): The plan ID to update.
            updated_data (dict): The updated plan data.
            
        Returns:
            Plan: The updated plan.
        """
        from app.models.database import Plan, Activity
        import datetime
        
        # Get the plan
        plan = Plan.query.get(plan_id)
        if not plan:
            raise ValueError(f"Plan with ID {plan_id} not found")
        
        # Update the plan directly instead of creating a new one
        plan.title = updated_data.get('plan_title', plan.title)
        plan.description = updated_data.get('plan_description', plan.description)
        
        # Handle date
        if 'scheduled_date' in updated_data and updated_data['scheduled_date']:
            try:
                plan.scheduled_date = datetime.datetime.strptime(
                    updated_data['scheduled_date'], '%Y-%m-%d'
                ).date()
            except Exception as e:
                # Leave as is if there's an error
                current_app.logger.error(f"Error parsing date: {str(e)}")
        
        # Update other fields
        plan.time_window = updated_data.get('time_window', plan.time_window)
        plan.start_time = updated_data.get('start_time', plan.start_time)
        plan.location_address = updated_data.get('location_address', plan.location_address)
        
        # Update the activity with the same details
        activity = Activity.query.get(self.activity_id)
        if activity:
            activity.proposed_date = plan.scheduled_date
            activity.time_window = plan.time_window
            activity.start_time = plan.start_time
            activity.location_address = plan.location_address
        
        # Add note about the update if not already present
        update_note = "\n\nThis plan was manually updated by the activity creator based on participant feedback."
        if update_note not in plan.description:
            plan.description += update_note
        
        # Update status to revised if it was a draft
        if plan.status == 'draft':
            plan.status = 'revised'
        
        db.session.commit()
        
        return plan
    
    def request_plan_approval(self, plan_id):
        """Request approval from all participants for a plan.
        
        Args:
            plan_id (str): The plan ID to request approval for.
            
        Returns:
            bool: True if successful.
        """
        from app.models.database import Plan, PlanApproval, Participant
        
        # Get the plan
        plan = Plan.query.get(plan_id)
        if not plan:
            raise ValueError(f"Plan with ID {plan_id} not found")
        
        # Set plan to require approval
        plan.requires_approval = True
        plan.status = 'pending_approval'
        
        # Create approval requests for all participants
        participants = Participant.query.filter_by(activity_id=self.activity_id).all()
        
        for participant in participants:
            # Create or update approval record
            existing_approval = PlanApproval.query.filter_by(
                plan_id=plan_id,
                participant_id=participant.id
            ).first()
            
            if existing_approval:
                # Reset existing approval
                existing_approval.approved = False
                existing_approval.feedback = None
            else:
                # Create new approval request
                approval = PlanApproval(
                    plan_id=plan_id,
                    participant_id=participant.id,
                    approved=False
                )
                db.session.add(approval)
        
        db.session.commit()
        return True
    
    def revise_plan_with_claude(self, plan_id, feedback):
        """Revise a plan with Claude based on feedback.
        
        Args:
            plan_id (str): The plan ID.
            feedback (str): The feedback on the plan.
            
        Returns:
            Plan: The revised plan.
        """
        plan = Plan.query.get(plan_id)
        if not plan:
            raise ValueError(f"Plan with ID {plan_id} not found")
        
        # Get current plan details
        current_plan = {
            'title': plan.title,
            'description': plan.description,
            'schedule': json.loads(plan.schedule) if plan.schedule else []
        }
        
        # Construct prompt for Claude
        system_prompt = """
        You are an AI-powered Activity Planner that revises activity plans based on feedback.
        
        Your task is to analyze the feedback and modify the existing plan to address concerns or suggestions.
        
        Format your response as JSON with the following structure:
        {
            "title": "Revised title for the activity",
            "description": "Revised description of the activity plan",
            "schedule": [
                {"time": "Start time", "activity": "Description of this part of the activity"},
                {"time": "Next time", "activity": "Description of the next part"}
            ],
            "revision_notes": "Notes explaining what changes were made and why"
        }
        """
        
        message = f"""
        I need to revise an activity plan based on feedback. Here is the current plan:
        
        Title: {current_plan['title']}
        
        Description:
        {current_plan['description']}
        
        Schedule:
        {json.dumps(current_plan['schedule'], indent=2)}
        
        Feedback received:
        {feedback}
        
        Please revise the plan to address this feedback while keeping what works.
        """
        
        try:
            # Call Claude API
            messages = [{"role": "user", "content": message}]
            response = claude_service._call_claude_api(system_prompt, messages)
            
            # Parse the response
            try:
                response_content = response.get("content", [])[0].get("text", "")
                revised_plan = json.loads(response_content)
                
                # Update the plan
                plan.title = revised_plan.get('title', plan.title)
                
                # Update description, including revision notes
                new_description = revised_plan.get('description', plan.description)
                revision_notes = revised_plan.get('revision_notes', '')
                
                if revision_notes:
                    new_description += f"\n\nRevision Notes:\n{revision_notes}"
                
                plan.description = new_description
                
                # Update schedule if provided
                new_schedule = revised_plan.get('schedule')
                if new_schedule:
                    plan.schedule = json.dumps(new_schedule)
                
                # Update status
                plan.status = 'revised'
                
                current_app.db.session.commit()
                
                return plan
                
            except (json.JSONDecodeError, IndexError) as e:
                current_app.logger.error(f"Failed to parse Claude response: {str(e)}")
                # Append feedback to description as fallback
                plan.description += f"\n\nFeedback received:\n{feedback}\n\nNote: This feedback has been noted but not yet addressed in the plan."
                plan.status = 'revised'
                current_app.db.session.commit()
                return plan
                
        except Exception as e:
            current_app.logger.error(f"Claude API call failed: {str(e)}")
            # Append feedback to description as fallback
            plan.description += f"\n\nFeedback received:\n{feedback}\n\nNote: This feedback has been noted but not yet addressed in the plan."
            plan.status = 'revised'
            current_app.db.session.commit()
            return plan
        
    def generate_quick_plan(self, conversation_input):
        """Generate a plan based on minimal conversational input."""
        import json
        import re
        from datetime import datetime, timedelta
        import random
        
        # Parse the conversation input for key parameters
        parsed_input = self._parse_conversation_input(conversation_input)
        
        # Extract basic information from text
        group_size = parsed_input.get('group_size', 6)  # Default
        activity_level = parsed_input.get('activity_level', 'moderate')  # Default
        budget = parsed_input.get('budget', "$25 per person")  # Default
        
        # Define activity options based on activity level
        low_activities = ["Casual Dinner", "Board Game Night", "Movie Night", "Art Gallery Visit", "Wine Tasting"]
        moderate_activities = ["Bowling", "Mini Golf", "Easy Hike", "Museum Tour", "Cooking Class"]
        high_activities = ["Bike Ride", "Kayaking", "Hiking Trip", "Sports Tournament", "Dance Class"]
        
        # Choose appropriate activity based on activity level
        if activity_level == "low":
            activity_name = random.choice(low_activities)
        elif activity_level == "high":
            activity_name = random.choice(high_activities)
        else:
            activity_name = random.choice(moderate_activities)
            
        # Override with specific activity type if found in parsed input
        if 'activity_type' in parsed_input:
            activity_name = parsed_input['activity_type']
        
        # Generate plan title
        title = f"{activity_name} for {group_size} People"
        
        # Generate plan description
        description = f"A {activity_level}-impact activity for a group of {group_size} people.\n\n"
        description += f"This plan includes {activity_name.lower()} with an approximate budget of {budget}.\n\n"
        
        # Add detailed description based on activity
        if "Dinner" in activity_name:
            description += "The group will enjoy dinner at a restaurant with a relaxed atmosphere, perfect for conversation and bonding."
        elif "Game" in activity_name:
            description += "The group will enjoy a selection of board games suitable for players of all experience levels."
        elif "Movie" in activity_name:
            description += "The group will enjoy watching a film together, followed by discussion time."
        elif "Hike" in activity_name or "Bike" in activity_name:
            description += "The group will enjoy an outdoor activity on a scenic trail suitable for the desired activity level."
        
        # Create a simple schedule
        start_time = datetime.now().replace(hour=18, minute=0, second=0)  # Default to 6 PM
        duration = 3  # hours
        
        schedule = []
        current_time = start_time
        
        # Add meeting time
        schedule.append({
            "time": current_time.strftime("%-I:%M %p"),
            "activity": "Meet at the venue"
        })
        
        # Add start of activity
        current_time = current_time + timedelta(minutes=15)
        schedule.append({
            "time": current_time.strftime("%-I:%M %p"),
            "activity": f"Begin {activity_name}"
        })
        
        # Add break if duration is long enough
        if duration > 2:
            current_time = current_time + timedelta(hours=1, minutes=30)
            schedule.append({
                "time": current_time.strftime("%-I:%M %p"),
                "activity": "Break for refreshments"
            })
        
        # Add end time
        current_time = start_time + timedelta(hours=duration)
        schedule.append({
            "time": current_time.strftime("%-I:%M %p"),
            "activity": "Activity concludes"
        })
        
        # Create plan in database
        plan = Plan(
            activity_id=self.activity_id,
            title=title,
            description=description,
            scheduled_date=self.activity.proposed_date if self.activity else None,  # Copy date from activity
            time_window=self.activity.time_window if self.activity else None,      # Copy time window from activity
            start_time=self.activity.start_time if self.activity else None,        # Copy start time from activity
            location_address=self.activity.location_address if self.activity else None,  # Copy address from activity
            schedule=json.dumps(schedule),
            status='draft'
        )
        
        db.session.add(plan)
        db.session.commit()
        
        # Update activity status
        self.activity.status = 'planned'
        db.session.commit()
        
        return plan

    def create_plan_from_description(self, description, activity_type=None):
        """Create a plan from the AI conversation description.
        
        Args:
            description (str): The description text from AI conversation
            activity_type (str, optional): The activity type if available
            
        Returns:
            Plan: The created plan
        """
        import json
        from datetime import datetime, timedelta
        import re
        
        if not self.activity:
            self.load_activity()
            
        # Parse the description for key information
        parsed_info = self._parse_conversation_input(description)
        
        # Use provided activity type or extract from description
        if activity_type:
            parsed_info['activity_type'] = activity_type
            
        # Set defaults if needed
        activity_name = parsed_info.get('activity_type', 'Group Activity')
        group_size = parsed_info.get('group_size', 8)
        budget = parsed_info.get('budget', '$25 per person')
        
        # Generate plan title
        title = f"{activity_name} Plan"
        
        # Create a simple schedule from parsed info
        day_part = parsed_info.get('time', 'afternoon')
        is_weekend = parsed_info.get('day', 'weekend') == 'weekend'
        
        # Default duration of 3 hours
        duration = 3
        
        # Create start time based on time of day
        start_time = datetime.now().replace(hour=12, minute=0, second=0)  # Default to noon
        if day_part == 'morning':
            start_time = start_time.replace(hour=10)
        elif day_part == 'afternoon':
            start_time = start_time.replace(hour=14)
        elif day_part == 'evening':
            start_time = start_time.replace(hour=18)
            
        # Generate a simple schedule
        schedule = []
        current_time = start_time
        
        # Add meeting time
        schedule.append({
            "time": current_time.strftime("%-I:%M %p"),
            "activity": "Meet at the venue"
        })
        
        # Add start of activity
        current_time = current_time + timedelta(minutes=15)
        schedule.append({
            "time": current_time.strftime("%-I:%M %p"),
            "activity": f"Begin {activity_name}"
        })
        
        # Add break if duration is long enough
        if duration > 2:
            current_time = current_time + timedelta(hours=1, minutes=30)
            schedule.append({
                "time": current_time.strftime("%-I:%M %p"),
                "activity": "Break for refreshments"
            })
        
        # Add end time
        current_time = start_time + timedelta(hours=duration)
        schedule.append({
            "time": current_time.strftime("%-I:%M %p"),
            "activity": "Activity concludes"
        })
        
        # Create the plan
        plan = Plan(
            activity_id=self.activity_id,
            title=title,
            description=description,  # Use the full description from AI
            schedule=json.dumps(schedule),
            status='draft'
        )
        
        db.session.add(plan)
        db.session.commit()
        
        # Update activity status
        self.activity.status = 'planned'
        db.session.commit()
        
        return plan
    
    def _parse_conversation_input(self, input_text):
        """Extract key parameters from conversational input."""
        # Simple parsing logic - in a real implementation you would use NLP
        parsed = {}
        lower_text = input_text.lower()
        
        # Extract group size
        group_size_match = re.search(r'(\d+)\s+people', input_text, re.IGNORECASE)
        if group_size_match:
            parsed['group_size'] = int(group_size_match.group(1))
        
        # Extract activity level
        if any(phrase in lower_text for phrase in ["nothing too active", "low activity", "relaxed", "casual", "easy"]):
            parsed['activity_level'] = "low"
        elif any(phrase in lower_text for phrase in ["very active", "high activity", "energetic", "intense", "challenging"]):
            parsed['activity_level'] = "high"
        elif any(phrase in lower_text for phrase in ["moderate", "medium", "average"]):
            parsed['activity_level'] = "moderate"
        
        # Extract budget information
        budget_match = re.search(r'\$(\d+)', input_text)
        if budget_match:
            budget_amount = budget_match.group(1)
            parsed['budget'] = f"${budget_amount} per person"
        
        # Extract activity type
        if "dinner" in lower_text or "restaurant" in lower_text or "eat" in lower_text:
            parsed['activity_type'] = "Group Dinner"
        elif "movie" in lower_text or "cinema" in lower_text or "film" in lower_text:
            parsed['activity_type'] = "Movie Night"
        elif "game" in lower_text or "board game" in lower_text:
            parsed['activity_type'] = "Game Night"
        elif "hike" in lower_text or "hiking" in lower_text or "trail" in lower_text:
            parsed['activity_type'] = "Hiking Trip"
        elif "museum" in lower_text or "gallery" in lower_text or "art" in lower_text:
            parsed['activity_type'] = "Museum Visit"
        elif "park" in lower_text or "picnic" in lower_text:
            parsed['activity_type'] = "Park Outing"
        elif "bowling" in lower_text:
            parsed['activity_type'] = "Bowling"
        elif "sports" in lower_text:
            parsed['activity_type'] = "Sports Activity"
        
        # Extract location preferences
        if "indoor" in lower_text or "inside" in lower_text:
            parsed['location'] = "indoor"
        elif "outdoor" in lower_text or "outside" in lower_text:
            parsed['location'] = "outdoor"
        
        # Extract timing preferences
        if "weekend" in lower_text:
            parsed['day'] = "weekend"
        elif "weekday" in lower_text:
            parsed['day'] = "weekday"
            
        if "morning" in lower_text:
            parsed['time'] = "morning"
        elif "afternoon" in lower_text:
            parsed['time'] = "afternoon"
        elif "evening" in lower_text or "night" in lower_text:
            parsed['time'] = "evening"
        
        return parsed
