from typing import List, Dict, Optional
import json

class AgentStory:
    def __init__(self, occupation="", career_outlook="", family_plan="", education_need="", housing_need="", selling_motivation="", background_story=""):
        self.occupation = occupation
        self.career_outlook = career_outlook
        self.family_plan = family_plan
        self.education_need = education_need
        self.housing_need = housing_need
        self.selling_motivation = selling_motivation
        self.background_story = background_story

class AgentPreference:
    def __init__(self, target_zone="", max_price=0.0, min_bedrooms=1, need_school_district=False):
        self.target_zone = target_zone
        self.max_price = max_price
        self.min_bedrooms = min_bedrooms
        self.need_school_district = need_school_district

class Agent:
    def __init__(self, id: int, age: int = 30, marital_status: str = "single", cash: float = 0.0, monthly_income: float = 0.0):
        self.id = id
        self.age = age
        self.marital_status = marital_status
        self.cash = cash
        self.last_month_cash = cash
        self.monthly_income = monthly_income
        self.owned_properties: List[Dict] = []
        self.life_events: Dict[int, str] = {}
        self.children_ages: List[int] = []
        
        self.children_ages: List[int] = []
        
        # 🆕 Extended Attributes via Composition
        self.story = AgentStory()
        self.preference = AgentPreference()
        self.monthly_event = None  # To store current month's event
        self.monthly_payment = 0.0 # Mortgage/Rent monthly payment commitment

        # Backward compatibility properties (property routing)
        @property
        def occupation(self): return self.story.occupation
        @occupation.setter
        def occupation(self, value): self.story.occupation = value

        @property
        def background_story(self): return self.story.background_story
        @background_story.setter
        def background_story(self, value): self.story.background_story = value
        
        @property
        def housing_need(self): return self.story.housing_need
        @housing_need.setter
        def housing_need(self, value): self.story.housing_need = value
        
        @property
        def education_need(self): return self.story.education_need
        @education_need.setter
        def education_need(self, value): self.story.education_need = value

    def get_life_event(self, month: int) -> Optional[str]:
        return self.life_events.get(month)
        
    def set_life_event(self, month: int, event: str):
        self.life_events[month] = event

    def has_children_near_school_age(self) -> bool:
        """Check if any child is near school age (5-6 years old)"""
        for age in self.children_ages:
            if 5 <= age <= 6:
                return True
        return False
        
    @property
    def net_worth(self) -> float:
        """Calculate total net worth (Cash + Property Value)"""
        # Note: Property value here simplifies to base_value or listed_price if available
        # Real calculation should query market current price, but for model simplicity we sum stored value
        prop_value = sum(p.get('base_value', 2000000) for p in self.owned_properties)
        return self.cash + prop_value

    def get_profile_summary(self) -> str:
        return (f"Agent {self.id} | Age: {self.age} | {self.marital_status} | "
                f"Cash: {self.cash/10000:.0f}w | Props: {len(self.owned_properties)} | "
                f"Net Worth: {self.net_worth/10000:.0f}w")

    def to_dict(self):
        return {
            "id": self.id,
            "age": self.age,
            "marital_status": self.marital_status,
            "cash": self.cash,
            "monthly_income": self.monthly_income,
            "children_ages": self.children_ages,
            "owned_properties_count": len(self.owned_properties),
            "net_worth": self.net_worth,
            "occupation": self.occupation,
            "education_need": self.education_need,
            "housing_need": self.housing_need
        }

class Market:
    def __init__(self, properties: List[Dict] = None):
        self.properties = properties or []
        self.price_history: Dict[str, Dict[int, float]] = {'A': {}, 'B': {}} # zone -> {month: avg_price}

    def get_price_change_rate(self, zone: str, month: int) -> float:
        """Calculate price change rate for a zone in a given month compared to previous month"""
        # For simulation start or missing data, return 0
        if month <= 1:
            return 0.0
            
        current_price = self.get_avg_price(zone, month)
        last_month_price = self.get_avg_price(zone, month - 1)
        
        if last_month_price == 0:
            return 0.0
            
        return (current_price - last_month_price) / last_month_price

    def get_avg_price(self, zone: str, month: int = None) -> float:
        """Get average price for a zone. If month is provided, use historical data."""
        if month is not None:
             # Look for recorded history first
             if month in self.price_history[zone]:
                 return self.price_history[zone][month]
        
        # Fallback to current properties list
        zone_props = [p for p in self.properties if p['zone'] == zone]
        if not zone_props:
            return 0.0
        
        # Calculate avg based on listed_price or base_value
        total_price = sum(p.get('listed_price', p.get('base_value', 0)) for p in zone_props)
        return total_price / len(zone_props)

    def set_price_change(self, zone: str, month: int, change_rate: float):
        """Mock method for testing price changes: sets price for current month based on prev * (1+rate)"""
        prev_price = self.get_avg_price(zone, month - 1)
        if prev_price == 0:
             prev_price = 5000000 if zone == 'A' else 2500000 # Default
             
        new_price = prev_price * (1 + change_rate)
        self.price_history[zone][month] = new_price
        
    def add_property(self, property: Dict):
        self.properties.append(property)
