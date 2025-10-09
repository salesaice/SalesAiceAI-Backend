"""
AI Agent Intelligent Decision Making System
===========================================

This module handles automatic decision making for AI agents based on their knowledge,
learning data, and current context. The agent makes smart decisions without human intervention.
"""

from django.utils import timezone
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Any, Optional

from .ai_agent_models import AIAgent, CustomerProfile, CallSession
from .auto_campaign_models import AutoCallCampaign, AutoCampaignContact

logger = logging.getLogger(__name__)


class AIAgentDecisionEngine:
    """
    Core AI decision engine that makes intelligent choices based on agent's knowledge
    """
    
    def __init__(self, ai_agent: AIAgent):
        self.agent = ai_agent
        self.learning_data = ai_agent.conversation_memory or {}
        
    def should_start_calling_campaign(self, campaign: AutoCallCampaign) -> Dict[str, Any]:
        """
        Agent decides when to start calling campaigns based on:
        - Historical performance data
        - Customer behavior patterns
        - Time optimization
        - Success rate predictions
        """
        decision = {
            'should_start': False,
            'confidence': 0.0,
            'reasoning': '',
            'recommended_time': None,
            'priority_adjustments': {}
        }
        
        try:
            # Check agent's learning data
            learning = self.learning_data.get('automatic_learning', {})
            successful_patterns = learning.get('successful_patterns', [])
            
            # Time-based decision making
            current_hour = timezone.now().hour
            
            # Analyze successful call times from history
            successful_hours = []
            for pattern in successful_patterns:
                if pattern.get('timestamp'):
                    call_time = datetime.fromisoformat(pattern['timestamp'].replace('Z', '+00:00'))
                    successful_hours.append(call_time.hour)
            
            # Calculate best time to call
            if successful_hours:
                best_hours = self._get_most_frequent_hours(successful_hours)
                if current_hour in best_hours:
                    decision['confidence'] += 0.4
                    decision['reasoning'] += f"Current time ({current_hour}:00) is historically successful. "
            
            # Check agent's current conversion rate
            if self.agent.conversion_rate >= 15.0:  # Good performance
                decision['confidence'] += 0.3
                decision['reasoning'] += f"High conversion rate ({self.agent.conversion_rate}%). "
            elif self.agent.conversion_rate >= 8.0:  # Average performance
                decision['confidence'] += 0.1
                decision['reasoning'] += f"Decent conversion rate ({self.agent.conversion_rate}%). "
            
            # Check recent performance trends
            recent_success = self._analyze_recent_performance()
            if recent_success['trending_up']:
                decision['confidence'] += 0.2
                decision['reasoning'] += "Recent performance is improving. "
            
            # Final decision
            if decision['confidence'] >= 0.6:
                decision['should_start'] = True
                decision['reasoning'] += "Agent is confident about starting campaign now."
            elif decision['confidence'] >= 0.3:
                # Suggest better time
                if successful_hours:
                    next_best_hour = min([h for h in best_hours if h > current_hour], default=min(best_hours))
                    decision['recommended_time'] = f"{next_best_hour}:00"
                    decision['reasoning'] += f"Recommend waiting until {next_best_hour}:00 for better results."
            
            return decision
            
        except Exception as e:
            logger.error(f"Error in campaign decision making: {str(e)}")
            decision['reasoning'] = "Using default scheduling due to analysis error."
            return decision
    
    def prioritize_customers_intelligently(self, contacts: List[AutoCampaignContact]) -> List[AutoCampaignContact]:
        """
        Agent intelligently prioritizes customers based on:
        - Previous interaction history
        - Customer behavior patterns
        - Likelihood of conversion
        - Optimal contact times
        """
        try:
            learning = self.learning_data.get('automatic_learning', {})
            customer_insights = learning.get('customer_behavior_insights', {})
            
            # Score each contact
            prioritized_contacts = []
            
            for contact in contacts:
                score = self._calculate_customer_priority_score(contact, customer_insights)
                prioritized_contacts.append({
                    'contact': contact,
                    'priority_score': score['total_score'],
                    'reasoning': score['reasoning']
                })
            
            # Sort by priority score (highest first)
            prioritized_contacts.sort(key=lambda x: x['priority_score'], reverse=True)
            
            # Update contact priorities in database
            for i, item in enumerate(prioritized_contacts):
                contact = item['contact']
                contact.priority = min(10, max(1, int(item['priority_score'] * 10)))
                contact.ai_notes = f"AI Priority Reasoning: {item['reasoning']}"
                contact.save()
            
            return [item['contact'] for item in prioritized_contacts]
            
        except Exception as e:
            logger.error(f"Error in customer prioritization: {str(e)}")
            return contacts
    
    def decide_call_schedule_intelligently(self, contact: AutoCampaignContact) -> Dict[str, Any]:
        """
        Agent decides optimal call schedule for each customer based on:
        - Customer's previous response times
        - Industry best practices from learning data
        - Customer's timezone and preferences
        """
        decision = {
            'recommended_datetime': None,
            'confidence': 0.0,
            'reasoning': '',
            'follow_up_strategy': None
        }
        
        try:
            learning = self.learning_data.get('automatic_learning', {})
            successful_patterns = learning.get('successful_patterns', [])
            
            # Analyze successful call times
            successful_times = []
            for pattern in successful_patterns:
                if pattern.get('timestamp'):
                    call_time = datetime.fromisoformat(pattern['timestamp'].replace('Z', '+00:00'))
                    successful_times.append({
                        'hour': call_time.hour,
                        'day_of_week': call_time.weekday(),
                        'effectiveness': pattern.get('effectiveness_score', 5)
                    })
            
            # Find optimal time patterns
            if successful_times:
                # Best hours
                hour_scores = {}
                for time_data in successful_times:
                    hour = time_data['hour']
                    if hour not in hour_scores:
                        hour_scores[hour] = []
                    hour_scores[hour].append(time_data['effectiveness'])
                
                best_hour = max(hour_scores.keys(), key=lambda h: sum(hour_scores[h])/len(hour_scores[h]))
                
                # Best days
                day_scores = {}
                for time_data in successful_times:
                    day = time_data['day_of_week']
                    if day not in day_scores:
                        day_scores[day] = []
                    day_scores[day].append(time_data['effectiveness'])
                
                best_day = max(day_scores.keys(), key=lambda d: sum(day_scores[d])/len(day_scores[d]))
                
                # Schedule for next occurrence of best day and time
                now = timezone.now()
                days_ahead = best_day - now.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                
                target_date = now + timedelta(days=days_ahead)
                recommended_time = target_date.replace(hour=best_hour, minute=0, second=0, microsecond=0)
                
                decision['recommended_datetime'] = recommended_time
                decision['confidence'] = 0.8
                decision['reasoning'] = f"Optimal time based on {len(successful_times)} successful patterns: {best_hour}:00 on weekday {best_day}"
            
            # Fallback to business hours if no patterns
            else:
                now = timezone.now()
                if now.hour < 17:  # Still business hours
                    decision['recommended_datetime'] = now + timedelta(hours=1)
                else:  # Next business day
                    next_day = now + timedelta(days=1)
                    decision['recommended_datetime'] = next_day.replace(hour=10, minute=0, second=0, microsecond=0)
                
                decision['confidence'] = 0.3
                decision['reasoning'] = "Default business hours scheduling (no historical data available)"
            
            return decision
            
        except Exception as e:
            logger.error(f"Error in call scheduling decision: {str(e)}")
            decision['reasoning'] = "Error in analysis, using default timing"
            return decision
    
    def should_approve_follow_up_automatically(self, call_session: CallSession) -> Dict[str, Any]:
        """
        Agent decides whether to automatically approve follow-ups based on:
        - Customer interest level during call
        - Conversation sentiment
        - Success probability
        """
        decision = {
            'auto_approve': False,
            'confidence': 0.0,
            'reasoning': '',
            'suggested_follow_up_type': None,
            'suggested_timing': None
        }
        
        try:
            # Analyze call outcome
            call_outcome = call_session.outcome or ''
            customer_interest = call_session.customer_profile.interest_level
            
            # High interest customers - auto approve
            if customer_interest in ['hot', 'warm']:
                decision['auto_approve'] = True
                decision['confidence'] = 0.9
                decision['reasoning'] = f"Customer shows {customer_interest} interest level"
                decision['suggested_follow_up_type'] = 'demo_scheduling' if customer_interest == 'hot' else 'information_follow_up'
                decision['suggested_timing'] = '24_hours' if customer_interest == 'hot' else '3_days'
            
            # Analyze conversation content for interest signals
            elif call_outcome:
                interest_keywords = ['interested', 'tell me more', 'pricing', 'demo', 'when can we', 'how does it work']
                positive_signals = sum(1 for keyword in interest_keywords if keyword.lower() in call_outcome.lower())
                
                if positive_signals >= 2:
                    decision['auto_approve'] = True
                    decision['confidence'] = 0.7
                    decision['reasoning'] = f"Detected {positive_signals} positive interest signals in conversation"
                    decision['suggested_follow_up_type'] = 'information_follow_up'
                    decision['suggested_timing'] = '2_days'
            
            # Check learning patterns for similar scenarios
            learning = self.learning_data.get('automatic_learning', {})
            successful_patterns = learning.get('successful_patterns', [])
            
            similar_outcomes = [p for p in successful_patterns if call_outcome.lower() in p.get('customer_response', '').lower()]
            if len(similar_outcomes) >= 2:
                avg_effectiveness = sum(p['effectiveness_score'] for p in similar_outcomes) / len(similar_outcomes)
                if avg_effectiveness >= 7:
                    decision['auto_approve'] = True
                    decision['confidence'] = 0.8
                    decision['reasoning'] += f" Similar scenarios had {avg_effectiveness}/10 success rate"
            
            return decision
            
        except Exception as e:
            logger.error(f"Error in follow-up decision: {str(e)}")
            decision['reasoning'] = "Error in analysis, manual approval required"
            return decision
    
    def _get_most_frequent_hours(self, hours_list: List[int]) -> List[int]:
        """Get the most frequently successful hours"""
        from collections import Counter
        hour_counts = Counter(hours_list)
        max_count = max(hour_counts.values()) if hour_counts else 0
        return [hour for hour, count in hour_counts.items() if count >= max_count * 0.7]
    
    def _analyze_recent_performance(self) -> Dict[str, Any]:
        """Analyze recent performance trends"""
        try:
            # Get recent call sessions
            recent_calls = CallSession.objects.filter(
                ai_agent=self.agent,
                created_at__gte=timezone.now() - timedelta(days=7)
            ).order_by('created_at')
            
            if len(recent_calls) < 3:
                return {'trending_up': False, 'confidence': 0.0}
            
            # Calculate success rate trend
            first_half = recent_calls[:len(recent_calls)//2]
            second_half = recent_calls[len(recent_calls)//2:]
            
            first_half_success = sum(1 for call in first_half if call.outcome and 'converted' in call.outcome) / len(first_half)
            second_half_success = sum(1 for call in second_half if call.outcome and 'converted' in call.outcome) / len(second_half)
            
            trending_up = second_half_success > first_half_success
            confidence = abs(second_half_success - first_half_success)
            
            return {'trending_up': trending_up, 'confidence': confidence}
            
        except Exception as e:
            logger.error(f"Error analyzing recent performance: {str(e)}")
            return {'trending_up': False, 'confidence': 0.0}
    
    def _calculate_customer_priority_score(self, contact: AutoCampaignContact, insights: Dict) -> Dict[str, Any]:
        """Calculate priority score for a customer"""
        score = 0.0
        reasoning_parts = []
        
        # Customer interest level
        interest_mapping = {'hot': 0.4, 'warm': 0.3, 'cold': 0.1}
        interest_score = interest_mapping.get(contact.customer_profile.interest_level, 0.1)
        score += interest_score
        reasoning_parts.append(f"Interest: {contact.customer_profile.interest_level} (+{interest_score})")
        
        # Previous interaction success
        if contact.customer_profile.last_contact_outcome:
            if 'positive' in contact.customer_profile.last_contact_outcome.lower():
                score += 0.2
                reasoning_parts.append("Previous positive interaction (+0.2)")
            elif 'interested' in contact.customer_profile.last_contact_outcome.lower():
                score += 0.3
                reasoning_parts.append("Previously showed interest (+0.3)")
        
        # Time since last contact (fresher leads get priority)
        if contact.customer_profile.last_contacted:
            days_since = (timezone.now() - contact.customer_profile.last_contacted).days
            if days_since <= 7:
                score += 0.2
                reasoning_parts.append("Recent lead (+0.2)")
            elif days_since <= 30:
                score += 0.1
                reasoning_parts.append("Moderately recent (+0.1)")
        else:
            score += 0.25  # New lead bonus
            reasoning_parts.append("New lead bonus (+0.25)")
        
        return {
            'total_score': min(1.0, score),  # Cap at 1.0
            'reasoning': '; '.join(reasoning_parts)
        }