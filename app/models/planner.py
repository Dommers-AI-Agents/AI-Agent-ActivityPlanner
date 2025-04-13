"""
AI Planner logic for activity planning and recommendations.
"""
import json
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
    
    def revise_plan(self, plan_id, feedback):
        """Revise an existing plan based on feedback."""
        plan = Plan.query.get(plan_id)
        if not plan:
            raise ValueError(f"Plan with ID {plan_id} not found")
            
        # In a real implementation, this would use AI to revise the plan
        # For this example, we'll just update the plan with the feedback
        
        original_plan = plan.to_dict()
        
        # Append feedback to description
        plan.description += f"\n\nRevisions based on feedback:\n{feedback}"
        
        # Update status
        plan.status = 'revised'
        
        db.session.commit()
        return plan
