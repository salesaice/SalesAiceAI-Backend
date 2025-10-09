from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from datetime import datetime, timedelta
import json
import logging

from .ai_agent_models import AIAgent, CallSession, AIAgentTraining
from .homeai_integration import HomeAIService

logger = logging.getLogger(__name__)


class RealTimeCallLearningAPIView(APIView):
    """
    Real-time AI Agent Learning during active calls
    Agent apne ap ko har call ke dauran train karta hai
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Process real-time learning during active call"""
        try:
            agent = request.user.ai_agent
            data = request.data
            
            call_id = data.get('call_id')
            learning_event = data.get('learning_event')  # 'objection', 'success', 'customer_response'
            
            call_session = CallSession.objects.get(id=call_id, ai_agent=agent)
            
            # Process different learning events
            if learning_event == 'customer_objection':
                self._process_objection_learning(agent, call_session, data)
            elif learning_event == 'successful_response':
                self._process_success_learning(agent, call_session, data)
            elif learning_event == 'conversation_turn':
                self._process_conversation_learning(agent, call_session, data)
            elif learning_event == 'call_sentiment_change':
                self._process_sentiment_learning(agent, call_session, data)
            
            return Response({
                'message': 'Real-time learning processed',
                'learning_event': learning_event,
                'agent_updated': True,
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Real-time learning error: {str(e)}")
            return Response({
                'error': f'Learning processing failed: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def _process_objection_learning(self, agent, call_session, data):
        """Customer objection se sikhna"""
        objection_text = data.get('objection_text', '')
        agent_response = data.get('agent_response', '')
        response_effectiveness = data.get('effectiveness_score', 0)  # 1-10
        
        # Get current memory
        memory = agent.conversation_memory or {}
        
        # Initialize objection patterns if not exists
        if 'real_time_objections' not in memory:
            memory['real_time_objections'] = {}
        
        objection_key = objection_text.lower()[:50].replace(' ', '_')
        
        if objection_key not in memory['real_time_objections']:
            memory['real_time_objections'][objection_key] = {
                'objection_text': objection_text,
                'responses': [],
                'best_response': None,
                'avg_effectiveness': 0,
                'frequency': 0
            }
        
        # Add this response
        response_data = {
            'response': agent_response,
            'effectiveness': response_effectiveness,
            'call_id': str(call_session.id),
            'timestamp': datetime.now().isoformat(),
            'customer_reaction': data.get('customer_reaction', 'neutral')
        }
        
        memory['real_time_objections'][objection_key]['responses'].append(response_data)
        memory['real_time_objections'][objection_key]['frequency'] += 1
        
        # Update best response if this was more effective
        current_best = memory['real_time_objections'][objection_key].get('best_response')
        if not current_best or response_effectiveness > current_best.get('effectiveness', 0):
            memory['real_time_objections'][objection_key]['best_response'] = response_data
        
        # Update average effectiveness
        all_scores = [r['effectiveness'] for r in memory['real_time_objections'][objection_key]['responses']]
        memory['real_time_objections'][objection_key]['avg_effectiveness'] = sum(all_scores) / len(all_scores)
        
        agent.conversation_memory = memory
        agent.save()
        
        logger.info(f"Agent learned from objection: {objection_text[:30]}... (effectiveness: {response_effectiveness})")
    
    def _process_success_learning(self, agent, call_session, data):
        """Successful response se sikhna"""
        successful_approach = data.get('approach_used', '')
        context = data.get('context', '')
        customer_positive_reaction = data.get('customer_reaction', '')
        effectiveness_score = data.get('effectiveness_score', 8)
        
        memory = agent.conversation_memory or {}
        
        if 'successful_patterns' not in memory:
            memory['successful_patterns'] = []
        
        success_pattern = {
            'approach': successful_approach,
            'context': context,
            'customer_reaction': customer_positive_reaction,
            'effectiveness': effectiveness_score,
            'call_id': str(call_session.id),
            'timestamp': datetime.now().isoformat(),
            'customer_profile': {
                'interest_level': call_session.customer_profile.interest_level,
                'previous_calls': call_session.customer_profile.total_calls
            }
        }
        
        memory['successful_patterns'].append(success_pattern)
        
        # Keep only top 50 successful patterns (memory management)
        if len(memory['successful_patterns']) > 50:
            memory['successful_patterns'] = sorted(
                memory['successful_patterns'], 
                key=lambda x: x['effectiveness'], 
                reverse=True
            )[:50]
        
        agent.conversation_memory = memory
        agent.save()
        
        logger.info(f"Agent learned successful pattern: {successful_approach[:30]}...")
    
    def _process_conversation_learning(self, agent, call_session, data):
        """General conversation pattern se sikhna"""
        conversation_turn = data.get('conversation_turn', {})
        customer_input = conversation_turn.get('customer_said', '')
        agent_response = conversation_turn.get('agent_said', '')
        turn_effectiveness = data.get('turn_effectiveness', 5)
        
        memory = agent.conversation_memory or {}
        
        if 'conversation_patterns' not in memory:
            memory['conversation_patterns'] = {
                'effective_transitions': [],
                'question_response_pairs': [],
                'conversation_flow_analysis': {}
            }
        
        # Analyze question-response effectiveness
        if '?' in agent_response:  # Agent asked a question
            qr_pair = {
                'agent_question': agent_response,
                'customer_response': customer_input,
                'effectiveness': turn_effectiveness,
                'led_to_positive_outcome': turn_effectiveness > 6,
                'timestamp': datetime.now().isoformat()
            }
            
            memory['conversation_patterns']['question_response_pairs'].append(qr_pair)
            
            # Keep only recent 100 pairs
            if len(memory['conversation_patterns']['question_response_pairs']) > 100:
                memory['conversation_patterns']['question_response_pairs'] = \
                    memory['conversation_patterns']['question_response_pairs'][-100:]
        
        agent.conversation_memory = memory
        agent.save()
    
    def _process_sentiment_learning(self, agent, call_session, data):
        """Customer sentiment changes se sikhna"""
        previous_sentiment = data.get('previous_sentiment', 'neutral')
        current_sentiment = data.get('current_sentiment', 'neutral')
        trigger_action = data.get('trigger_action', '')  # What agent did that caused change
        sentiment_score = data.get('sentiment_score', 0)  # -5 to +5
        
        memory = agent.conversation_memory or {}
        
        if 'sentiment_learning' not in memory:
            memory['sentiment_learning'] = {
                'positive_triggers': [],
                'negative_triggers': [],
                'sentiment_recovery_strategies': []
            }
        
        sentiment_change = {
            'from': previous_sentiment,
            'to': current_sentiment,
            'trigger': trigger_action,
            'score_change': sentiment_score,
            'call_id': str(call_session.id),
            'timestamp': datetime.now().isoformat()
        }
        
        # Categorize as positive or negative trigger
        if sentiment_score > 0:  # Positive change
            memory['sentiment_learning']['positive_triggers'].append(sentiment_change)
            # Keep top 30 positive triggers
            if len(memory['sentiment_learning']['positive_triggers']) > 30:
                memory['sentiment_learning']['positive_triggers'] = \
                    sorted(memory['sentiment_learning']['positive_triggers'], 
                           key=lambda x: x['score_change'], reverse=True)[:30]
        
        elif sentiment_score < 0:  # Negative change
            memory['sentiment_learning']['negative_triggers'].append(sentiment_change)
            # Keep top 30 negative triggers to avoid
            if len(memory['sentiment_learning']['negative_triggers']) > 30:
                memory['sentiment_learning']['negative_triggers'] = \
                    memory['sentiment_learning']['negative_triggers'][-30:]
        
        agent.conversation_memory = memory
        agent.save()
        
        logger.info(f"Agent learned sentiment change: {previous_sentiment} -> {current_sentiment} (score: {sentiment_score})")


class AutoCallAnalysisAPIView(APIView):
    """
    Automatic call analysis and learning after call ends
    Call khatam hone ke baad comprehensive analysis
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Comprehensive post-call analysis and learning"""
        try:
            agent = request.user.ai_agent
            data = request.data
            
            call_id = data.get('call_id')
            call_session = CallSession.objects.get(id=call_id, ai_agent=agent)
            
            # Get call recording analysis from HumeAI
            homeai_service = HomeAIService()
            
            # Analyze full conversation
            analysis_result = homeai_service.analyze_conversation_for_learning(
                conversation_id=data.get('conversation_id'),
                full_transcript=data.get('full_transcript', ''),
                call_outcome=call_session.outcome
            )
            
            if analysis_result:
                # Process comprehensive learning
                learning_insights = self._extract_learning_insights(analysis_result)
                
                # Create detailed training session
                training_session = AIAgentTraining.objects.create(
                    ai_agent=agent,
                    training_type='post_call_analysis',
                    training_data={
                        'call_analysis': analysis_result,
                        'learning_insights': learning_insights,
                        'call_metadata': {
                            'call_id': str(call_session.id),
                            'duration': call_session.duration_seconds,
                            'outcome': call_session.outcome,
                            'customer_satisfaction': data.get('customer_satisfaction', 5)
                        },
                        'improvement_recommendations': learning_insights.get('recommendations', [])
                    },
                    completion_percentage=100,
                    is_completed=True
                )
                
                # Update agent memory with insights
                self._update_agent_memory_with_insights(agent, learning_insights)
                
                # Increment training level based on call quality
                call_quality_score = self._calculate_call_quality_score(analysis_result)
                if call_quality_score > 7:
                    agent.training_level = min(agent.training_level + 1, 100)
                    agent.save()
                
                return Response({
                    'message': 'Post-call analysis completed',
                    'training_session_id': str(training_session.id),
                    'learning_insights': learning_insights,
                    'call_quality_score': call_quality_score,
                    'agent_improvement': {
                        'new_training_level': agent.training_level,
                        'insights_learned': len(learning_insights.get('key_learnings', [])),
                        'recommendations': learning_insights.get('recommendations', [])
                    }
                }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Auto call analysis error: {str(e)}")
            return Response({
                'error': f'Call analysis failed: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def _extract_learning_insights(self, analysis_result):
        """Extract actionable learning insights from analysis"""
        insights = {
            'key_learnings': [],
            'successful_moments': [],
            'improvement_areas': [],
            'recommendations': [],
            'conversation_metrics': {}
        }
        
        # Extract key insights from HumeAI analysis
        if 'successful_techniques' in analysis_result:
            insights['successful_moments'] = analysis_result['successful_techniques']
        
        if 'areas_for_improvement' in analysis_result:
            insights['improvement_areas'] = analysis_result['areas_for_improvement']
        
        if 'conversation_metrics' in analysis_result:
            insights['conversation_metrics'] = analysis_result['conversation_metrics']
        
        # Generate recommendations
        recommendations = []
        
        for area in insights['improvement_areas']:
            if area.get('type') == 'objection_handling':
                recommendations.append(f"Practice better responses to '{area.get('specific_objection', 'objections')}'")
            elif area.get('type') == 'questioning':
                recommendations.append("Ask more open-ended questions to better understand customer needs")
            elif area.get('type') == 'closing':
                recommendations.append("Work on more confident closing techniques")
        
        insights['recommendations'] = recommendations
        
        return insights
    
    def _update_agent_memory_with_insights(self, agent, insights):
        """Update agent memory with comprehensive insights"""
        memory = agent.conversation_memory or {}
        
        # Update successful techniques repository
        if 'proven_techniques' not in memory:
            memory['proven_techniques'] = []
        
        for technique in insights.get('successful_moments', []):
            memory['proven_techniques'].append({
                'technique': technique,
                'learned_date': datetime.now().isoformat(),
                'effectiveness_confirmed': True
            })
        
        # Update improvement focus areas
        if 'focus_areas' not in memory:
            memory['focus_areas'] = {}
        
        for area in insights.get('improvement_areas', []):
            area_type = area.get('type', 'general')
            if area_type not in memory['focus_areas']:
                memory['focus_areas'][area_type] = {
                    'priority': area.get('priority', 'medium'),
                    'instances': [],
                    'improvement_plan': []
                }
            
            memory['focus_areas'][area_type]['instances'].append({
                'identified_date': datetime.now().isoformat(),
                'context': area.get('context', ''),
                'suggestion': area.get('suggestion', '')
            })
        
        agent.conversation_memory = memory
        agent.save()
    
    def _calculate_call_quality_score(self, analysis_result):
        """Calculate overall call quality score (1-10)"""
        metrics = analysis_result.get('conversation_metrics', {})
        
        # Base score factors
        sentiment_score = metrics.get('average_sentiment', 5)
        engagement_score = metrics.get('customer_engagement', 5)
        objection_handling = metrics.get('objection_handling_effectiveness', 5)
        closing_effectiveness = metrics.get('closing_effectiveness', 5)
        
        # Calculate weighted average
        quality_score = (
            sentiment_score * 0.3 +
            engagement_score * 0.25 +
            objection_handling * 0.25 +
            closing_effectiveness * 0.2
        )
        
        return round(quality_score, 1)
