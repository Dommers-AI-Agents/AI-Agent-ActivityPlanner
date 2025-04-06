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
        
        # Define the question batches
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
            # Second batch - Group composition
            [
                {
                    'id': 'group_size',
                    'type': 'number',
                    'question': 'How many people will be in your group?',
                    'required': True
                },
                {
                    'id': 'has_children',
                    'type': 'boolean',
                    'question': 'Will there be any children in your group?',
                    'required': True
                },
                {
                    'id': 'has_seniors',
                    'type': 'boolean',
                    'question': 'Will there be any seniors or people with mobility concerns in your group?',
                    'required': True
                }
            ],
            # Third batch - Timing preferences
            [
                {
                    'id': 'preferred_day',
                    'type': 'select',
                    'question': 'What day would you prefer for this activity?',
                    'options': ['Weekday', 'Weekend', 'No preference'],
                    'required': True
                },
                {
                    'id': 'preferred_time',
                    'type': 'select',
                    'question': 'What time of day do you prefer?',
                    'options': ['Morning', 'Afternoon', 'Evening', 'No preference'],
                    'required': True
                },
                {
                    'id': 'duration',
                    'type': 'select',
                    'question': 'How long would you like the activity to be?',
                    'options': ['1-2 hours', '2-4 hours', 'Half day', 'Full day'],
                    'required': True
                }
            ],
            # Fourth batch - Activity preferences
            [
                {
                    'id': 'activity_type',
                    'type': 'multiselect',
                    'question': 'What types of activities are you interested in?',
                    'options': ['Outdoor', 'Indoor', 'Cultural', 'Educational', 'Relaxation', 'Food', 'Sports'],
                    'required': True
                },
                {
                    'id': 'walking_preference',
                    'type': 'select',
                    'question': 'How much walking are you comfortable with?',
                    'options': ['Minimal', 'Moderate', 'Extensive'],
                    'required': True
                },
                {
                    'id': 'budget_range',
                    'type': 'select',
                    'question': 'What is your budget range per person?',
                    'options': ['$0-$25', '$25-$50', '$50-$100', '$100+'],
                    'required': True
                }
            ],
            # Fifth batch - Special requirements
            [
                {
                    'id': 'dietary_restrictions',
                    'type': 'text',
                    'question': 'Are there any dietary restrictions or preferences to consider?',
                    'required': False
                },
                {
                    'id': 'accessibility_needs',
                    'type': 'text',
                    'question': 'Are there any accessibility requirements to consider?',
                    'required': False
                },
                {
                    'id': 'additional_info',
                    'type': 'textarea',
                    'question': 'Is there anything else you would like to add?',
                    'required': False
                }
            ]
        ]
        
        # Determine which batch to send next
        if not previous_answers:
            return question_batches[0]
        
        # Count the number of preference categories in the database
        preferences = self.get_participant_preferences(participant_id)
        answered_categories = len(preferences.keys())
        
        # Get the next batch or return None if all batches have been answered
        if answered_categories < len(question_batches):
            return question_batches[answered_categories]
        else:
            return None
    
    def generate_plan(self):
        """Generate an activity plan based on all preferences."""
        if not self.activity:
            self.load_activity()
        
        # Get all preferences
        all_preferences = self.get_all_preferences()
        
        # In a real implementation, this would use AI to generate a custom plan
        # For this example, we'll create a simple plan
        
        # Extract some basic preferences for the plan
        activity_types = []
        durations = []
        preferred_days = []
        
        for participant_id, categories in all_preferences.items():
            if participant_id == 'group':
                continue
                
            if 'activity' in categories and 'activity_type' in categories['activity']:
                activity_type = categories['activity']['activity_type']
                if isinstance(activity_type, list):
                    activity_types.extend(activity_type)
                else:
                    activity_types.append(activity_type)
            
            if 'timing' in categories and 'duration' in categories['timing']:
                durations.append(categories['timing']['duration'])
            
            if 'timing' in categories and 'preferred_day' in categories['timing']:
                preferred_days.append(categories['timing']['preferred_day'])
        
        # Count frequencies to determine most popular choices
        def most_common(lst):
            if not lst:
                return None
            return max(set(lst), key=lst.count)
        
        most_common_activity = most_common(activity_types) if activity_types else "Outdoor"
        most_common_duration = most_common(durations) if durations else "2-4 hours"
        most_common_day = most_common(preferred_days) if preferred_days else "Weekend"
        
        # Generate a simple plan title
        if most_common_activity in ["Outdoor", "Sports"]:
            activities = {
                "Outdoor": ["Park Visit", "Nature Trail", "Botanical Gardens", "Lake Day"],
                "Sports": ["Mini Golf", "Bowling", "Frisbee in the Park", "Bike Ride"],
                "Indoor": ["Museum Visit", "Art Gallery", "Escape Room", "Board Game Cafe"],
                "Cultural": ["Local Festival", "Historical Tour", "Cultural Museum", "Live Music"],
                "Educational": ["Science Museum", "Workshop", "Guided Tour", "Library Event"],
                "Relaxation": ["Spa Day", "Picnic", "Beach Day", "Yoga Session"],
                "Food": ["Food Tour", "Cooking Class", "Restaurant Hopping", "Farmers Market"]
            }
            
            activity_name = activities.get(most_common_activity, ["Group Outing"])[0]
            title = f"{activity_name} - {most_common_day} {most_common_duration} Event"
        else:
            title = f"Group {most_common_activity} Activity - {most_common_day} Event"
            
        # Create a description based on preferences
        has_children = any(
            'group' in categories and 'has_children' in categories['group'] and categories['group']['has_children']
            for participant_id, categories in all_preferences.items() if participant_id != 'group'
        )
        
        has_seniors = any(
            'group' in categories and 'has_seniors' in categories['group'] and categories['group']['has_seniors']
            for participant_id, categories in all_preferences.items() if participant_id != 'group'
        )
        
        # Build description
        description_parts = [
            f"A {most_common_duration} {most_common_activity.lower()} activity for your group on a {most_common_day.lower()}.",
        ]
        
        if has_children:
            description_parts.append("This plan includes child-friendly options.")
            
        if has_seniors:
            description_parts.append("The activity is accessible for seniors and those with mobility concerns.")
            
        # Add a generic schedule
        now = datetime.now()
        start_date = now + timedelta(days=(5 if most_common_day == "Weekend" else 3))
        
        # Adjust to be on a weekend if requested
        if most_common_day == "Weekend" and start_date.weekday() < 5:  # 5 = Saturday, 6 = Sunday
            days_to_saturday = 5 - start_date.weekday()
            start_date = start_date + timedelta(days=days_to_saturday)
        
        # Create time slots based on duration
        schedule = []
        
        if most_common_duration == "1-2 hours":
            schedule = [
                {"time": "10:00 AM", "activity": "Meet at the location"},
                {"time": "10:15 AM", "activity": "Activity begins"},
                {"time": "11:45 AM", "activity": "Activity concludes"}
            ]
        elif most_common_duration == "2-4 hours":
            schedule = [
                {"time": "10:00 AM", "activity": "Meet at the location"},
                {"time": "10:30 AM", "activity": "Activity begins"},
                {"time": "12:30 PM", "activity": "Lunch break"},
                {"time": "1:30 PM", "activity": "Continue activity"},
                {"time": "2:30 PM", "activity": "Activity concludes"}
            ]
        elif most_common_duration == "Half day":
            schedule = [
                {"time": "9:00 AM", "activity": "Meet at the location"},
                {"time": "9:30 AM", "activity": "First activity begins"},
                {"time": "11:30 AM", "activity": "Break"},
                {"time": "12:00 PM", "activity": "Lunch"},
                {"time": "1:30 PM", "activity": "Second activity begins"},
                {"time": "3:00 PM", "activity": "Activities conclude"}
            ]
        else:  # Full day
            schedule = [
                {"time": "9:00 AM", "activity": "Meet at the location"},
                {"time": "9:30 AM", "activity": "Morning activity begins"},
                {"time": "11:30 AM", "activity": "Break"},
                {"time": "12:00 PM", "activity": "Lunch"},
                {"time": "1:30 PM", "activity": "Afternoon activity begins"},
                {"time": "3:30 PM", "activity": "Break"},
                {"time": "4:00 PM", "activity": "Final activity"},
                {"time": "5:30 PM", "activity": "Activities conclude"}
            ]
        
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
