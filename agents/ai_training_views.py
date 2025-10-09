from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging

from .ai_agent_models import AIAgent, AIAgentTraining, CustomerProfile, CallSession
from .serializers import AgentDetailSerializer

logger = logging.getLogger(__name__)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'sales_script': openapi.Schema(type=openapi.TYPE_STRING, description='Complete sales script with placeholders'),
            'objection_responses': openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='Objection handling responses',
                example={
                    "price_too_high": "Let me explain the value you'll get...",
                    "not_interested": "I understand, but what if I could show you...",
                    "thinking_about_it": "I appreciate that. Can I ask what specific concerns you have?"
                }
            ),
            'product_details': openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description='Product/service information',
                example={
                    "features": ["Feature 1", "Feature 2"],
                    "benefits": ["Benefit 1", "Benefit 2"], 
                    "pricing": "$99/month",
                    "competitors": {"Competitor A": "Our advantage"}
                }
            ),
            'conversation_starters': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(type=openapi.TYPE_STRING),
                description='Different ways to start conversations'
            ),
            'closing_techniques': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(type=openapi.TYPE_STRING),
                description='Closing techniques to use'
            )
        }
    ),
    responses={
        200: 'Agent training updated successfully',
        201: 'New training session created',
        404: 'AI Agent not found'
    },
    operation_description="Train AI Agent with sales scripts, objection handling, and product knowledge",
    tags=['AI Agent Training']
)
@swagger_auto_schema(
    method='get',
    responses={
        200: 'Current training status and data',
        404: 'AI Agent not found'
    },
    operation_description="Get AI Agent training status and current knowledge",
    tags=['AI Agent Training']
)
@api_view(['POST', 'GET'])
@permission_classes([permissions.IsAuthenticated])
def ai_agent_training(request):
    """
    AI Agent Training Endpoint
    Agent ko train karne ke liye - sales script, objection handling, product knowledge
    """
    try:
        # Get or create AI Agent for user
        agent, created = AIAgent.objects.get_or_create(
            client=request.user,
            defaults={
                'name': f"{request.user.first_name or 'My'} AI Agent",
                'personality_type': 'professional',
                'status': 'training'
            }
        )
        
        if request.method == 'GET':
            # Return current training status
            training_sessions = AIAgentTraining.objects.filter(ai_agent=agent)
            
            # Get current knowledge from agent's memory
            current_memory = agent.conversation_memory or {}
            
            response_data = {
                'agent_info': {
                    'id': str(agent.id),
                    'name': agent.name,
                    'status': agent.status,
                    'training_level': agent.training_level,
                    'is_ready_for_calls': agent.is_ready_for_calls
                },
                'training_status': {
                    'total_sessions': training_sessions.count(),
                    'completed_sessions': training_sessions.filter(is_completed=True).count(),
                    'current_training_level': agent.training_level
                },
                'current_knowledge': {
                    'sales_script': current_memory.get('sales_script', ''),
                    'objection_responses': current_memory.get('objection_responses', {}),
                    'product_details': current_memory.get('product_details', {}),
                    'conversation_starters': current_memory.get('conversation_starters', []),
                    'closing_techniques': current_memory.get('closing_techniques', [])
                },
                'learning_data': current_memory.get('automatic_learning', {}),
                'recent_training_sessions': [
                    {
                        'type': session.training_type,
                        'completion': session.completion_percentage,
                        'created_at': session.created_at.isoformat()
                    }
                    for session in training_sessions.order_by('-created_at')[:5]
                ]
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        elif request.method == 'POST':
            # Train the agent with new data
            training_data = request.data
            
            # Update agent's memory with training data
            current_memory = agent.conversation_memory or {}
            
            # Process sales script
            if 'sales_script' in training_data:
                current_memory['sales_script'] = training_data['sales_script']
                agent.sales_script = training_data['sales_script']
                
                # Create training session record
                AIAgentTraining.objects.create(
                    ai_agent=agent,
                    training_type='script',
                    training_data={'sales_script': training_data['sales_script']},
                    is_completed=True,
                    completion_percentage=100
                )
            
            # Process objection responses
            if 'objection_responses' in training_data:
                if 'objection_responses' not in current_memory:
                    current_memory['objection_responses'] = {}
                current_memory['objection_responses'].update(training_data['objection_responses'])
                
                AIAgentTraining.objects.create(
                    ai_agent=agent,
                    training_type='objections',
                    training_data={'objection_responses': training_data['objection_responses']},
                    is_completed=True,
                    completion_percentage=100
                )
            
            # Process product details
            if 'product_details' in training_data:
                current_memory['product_details'] = training_data['product_details']
                
                AIAgentTraining.objects.create(
                    ai_agent=agent,
                    training_type='product',
                    training_data={'product_details': training_data['product_details']},
                    is_completed=True,
                    completion_percentage=100
                )
            
            # Process conversation starters
            if 'conversation_starters' in training_data:
                current_memory['conversation_starters'] = training_data['conversation_starters']
            
            # Process closing techniques
            if 'closing_techniques' in training_data:
                current_memory['closing_techniques'] = training_data['closing_techniques']
            
            # Update agent memory
            agent.conversation_memory = current_memory
            
            # Calculate new training level based on completed training types
            training_components = [
                'sales_script' in current_memory and current_memory['sales_script'],
                'objection_responses' in current_memory and current_memory['objection_responses'],
                'product_details' in current_memory and current_memory['product_details'],
                'conversation_starters' in current_memory and current_memory['conversation_starters'],
                'closing_techniques' in current_memory and current_memory['closing_techniques']
            ]
            
            completed_components = sum(1 for component in training_components if component)
            agent.training_level = (completed_components / len(training_components)) * 100
            
            # Update agent status based on training level
            if agent.training_level >= 80:
                agent.status = 'active'
            elif agent.training_level >= 40:
                agent.status = 'learning'
            else:
                agent.status = 'training'
            
            agent.save()
            
            return Response({
                'message': 'Agent training updated successfully',
                'agent_info': {
                    'id': str(agent.id),
                    'name': agent.name,
                    'training_level': agent.training_level,
                    'status': agent.status,
                    'is_ready_for_calls': agent.is_ready_for_calls
                },
                'training_completed': {
                    'sales_script': 'sales_script' in training_data,
                    'objection_responses': 'objection_responses' in training_data,
                    'product_details': 'product_details' in training_data,
                    'conversation_starters': 'conversation_starters' in training_data,
                    'closing_techniques': 'closing_techniques' in training_data
                }
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        logger.error(f"AI Agent training error: {str(e)}")
        return Response({
            'error': 'Training failed',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'call_id': openapi.Schema(type=openapi.TYPE_STRING, description='Call session ID'),
            'conversation_transcript': openapi.Schema(type=openapi.TYPE_STRING, description='Full conversation text'),
            'customer_responses': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(type=openapi.TYPE_STRING),
                description='Key customer responses during call'
            ),
            'call_outcome': openapi.Schema(
                type=openapi.TYPE_STRING, 
                enum=['converted', 'interested', 'callback_requested', 'not_interested', 'do_not_call'],
                description='Final call outcome'
            ),
            'customer_satisfaction': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                minimum=1,
                maximum=10,
                description='Customer satisfaction score (1-10)'
            ),
            'agent_performance_notes': openapi.Schema(
                type=openapi.TYPE_STRING,
                description='Notes on how agent performed'
            ),
            'objections_encountered': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(type=openapi.TYPE_STRING),
                description='Customer objections during call'
            ),
            'successful_techniques': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(type=openapi.TYPE_STRING),
                description='Which techniques worked well'
            ),
            'call_duration': openapi.Schema(type=openapi.TYPE_INTEGER, description='Call duration in seconds')
        },
        required=['call_outcome', 'customer_satisfaction']
    ),
    responses={
        200: 'Learning data processed successfully',
        404: 'AI Agent not found'
    },
    operation_description="Process call data for AI learning - agent learns from each conversation",
    tags=['AI Agent Learning']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def ai_agent_learning(request):
    """
    AI Agent Real-time Learning Endpoint
    Har call ke baad agent learning karta hai
    """
    try:
        agent = AIAgent.objects.get(client=request.user)
        
        learning_data = request.data
        call_outcome = learning_data.get('call_outcome')
        satisfaction_score = learning_data.get('customer_satisfaction', 5)
        
        # Determine if call was successful
        successful_outcomes = ['converted', 'interested', 'callback_requested']
        is_successful = call_outcome in successful_outcomes and satisfaction_score >= 6
        
        # Prepare learning data for agent
        processed_learning = {
            'successful': is_successful,
            'outcome': call_outcome,
            'satisfaction': satisfaction_score,
            'customer_response': ' '.join(learning_data.get('customer_responses', [])),
            'notes': learning_data.get('agent_performance_notes', ''),
            'call_duration': learning_data.get('call_duration', 0),
            'customer_interest_level': 'hot' if call_outcome == 'converted' else 'warm' if call_outcome in ['interested', 'callback_requested'] else 'cold'
        }
        
        # Update agent learning
        agent.update_learning_data(processed_learning)
        
        # Process objections for future improvement
        objections = learning_data.get('objections_encountered', [])
        if objections:
            current_memory = agent.conversation_memory
            if 'objection_database' not in current_memory.get('automatic_learning', {}):
                if 'automatic_learning' not in current_memory:
                    current_memory['automatic_learning'] = {}
                current_memory['automatic_learning']['objection_database'] = {}
            
            objection_db = current_memory['automatic_learning']['objection_database']
            for objection in objections:
                if objection not in objection_db:
                    objection_db[objection] = {'count': 0, 'successful_responses': []}
                objection_db[objection]['count'] += 1
                
                if is_successful:
                    objection_db[objection]['successful_responses'].append({
                        'response': learning_data.get('agent_performance_notes', ''),
                        'timestamp': timezone.now().isoformat(),
                        'satisfaction': satisfaction_score
                    })
            
            agent.conversation_memory = current_memory
            agent.save()
        
        # Generate learning insights
        insights = []
        memory = agent.conversation_memory.get('automatic_learning', {})
        
        if memory.get('total_calls_learned_from', 0) >= 5:
            conversion_trends = memory.get('performance_metrics', {}).get('conversion_trends', [])
            if conversion_trends:
                recent_conversions = sum(1 for trend in conversion_trends[-5:] if trend['converted'])
                if recent_conversions >= 3:
                    insights.append("Your conversion rate is improving! Keep using your current approach.")
                elif recent_conversions <= 1:
                    insights.append("Consider adjusting your approach based on successful patterns.")
        
        # Provide recommendations based on successful patterns
        recommendations = []
        successful_patterns = memory.get('successful_patterns', [])
        if successful_patterns:
            top_pattern = successful_patterns[0]
            recommendations.append({
                'type': 'success_replication',
                'message': f"Your most effective approach: '{top_pattern.get('approach_used', '')[:100]}...'",
                'confidence': 'high'
            })
        
        return Response({
            'message': 'Learning data processed successfully',
            'learning_summary': {
                'call_outcome': call_outcome,
                'learning_applied': is_successful,
                'total_calls_learned': memory.get('total_calls_learned_from', 0),
                'conversion_rate': agent.conversion_rate,
                'training_level': agent.training_level
            },
            'insights': insights,
            'recommendations': recommendations,
            'agent_status': {
                'status': agent.status,
                'calls_handled': agent.calls_handled,
                'successful_conversions': agent.successful_conversions,
                'is_ready_for_calls': agent.is_ready_for_calls
            }
        }, status=status.HTTP_200_OK)
        
    except AIAgent.DoesNotExist:
        return Response({
            'error': 'AI Agent not found',
            'message': 'Please create an AI Agent first via /api/agents/ai/training/'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"AI Agent learning error: {str(e)}")
        return Response({
            'error': 'Learning processing failed',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'customer_message': openapi.Schema(type=openapi.TYPE_STRING, description='What customer said'),
            'conversation_context': openapi.Schema(type=openapi.TYPE_STRING, description='Current conversation context'),
            'customer_phone': openapi.Schema(type=openapi.TYPE_STRING, description='Customer phone number'),
            'call_stage': openapi.Schema(
                type=openapi.TYPE_STRING,
                enum=['opening', 'presentation', 'objection_handling', 'closing'],
                description='Current stage of the call'
            )
        },
        required=['customer_message', 'call_stage']
    ),
    responses={
        200: 'AI generated response',
        404: 'AI Agent not found'
    },
    operation_description="Generate intelligent response based on AI training and learning",
    tags=['AI Agent Conversation']
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def ai_agent_response_generator(request):
    """
    AI Agent Response Generator
    Live call ke dauraan intelligent response generate karta hai
    """
    try:
        agent = AIAgent.objects.get(client=request.user)
        
        if not agent.is_ready_for_calls:
            return Response({
                'error': 'Agent not ready',
                'message': f'Agent training is {agent.training_level}% complete. Minimum 20% required for calls.',
                'training_url': '/api/agents/ai/training/'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        customer_message = request.data.get('customer_message', '').lower()
        call_stage = request.data.get('call_stage', 'opening')
        conversation_context = request.data.get('conversation_context', '')
        customer_phone = request.data.get('customer_phone')
        
        # Get agent's knowledge base
        memory = agent.conversation_memory or {}
        
        # Get customer profile if exists
        customer_profile = None
        if customer_phone:
            try:
                customer_profile = CustomerProfile.objects.get(
                    ai_agent=agent,
                    phone_number=customer_phone
                )
            except CustomerProfile.DoesNotExist:
                pass
        
        # Generate response based on call stage and customer message
        response_text = ""
        response_type = "general"
        
        # Check for objections first
        objection_responses = memory.get('objection_responses', {})
        objection_detected = None
        
        for objection_key, response in objection_responses.items():
            objection_keywords = objection_key.lower().replace('_', ' ').split()
            if any(keyword in customer_message for keyword in objection_keywords):
                objection_detected = objection_key
                response_text = response
                response_type = "objection_handling"
                break
        
        # If no objection detected, generate response based on call stage
        if not response_text:
            if call_stage == 'opening':
                conversation_starters = memory.get('conversation_starters', [])
                if conversation_starters:
                    response_text = conversation_starters[0]
                else:
                    sales_script = memory.get('sales_script', '')
                    if sales_script:
                        # Extract opening from sales script
                        lines = sales_script.split('\\n')
                        response_text = lines[0] if lines else "Hello! How are you doing today?"
                    else:
                        response_text = "Hello! Thank you for your time. How are you doing today?"
                response_type = "opening"
            
            elif call_stage == 'presentation':
                product_details = memory.get('product_details', {})
                if product_details:
                    features = product_details.get('features', [])
                    benefits = product_details.get('benefits', [])
                    if features and benefits:
                        response_text = f"Let me share some key benefits with you. {benefits[0]} This is possible because of our {features[0]}."
                    else:
                        response_text = "Let me explain how this can benefit you specifically."
                else:
                    response_text = "Based on what you've told me, I believe this could be a great fit for you."
                response_type = "presentation"
            
            elif call_stage == 'closing':
                closing_techniques = memory.get('closing_techniques', [])
                if closing_techniques:
                    response_text = closing_techniques[0]
                else:
                    response_text = "Based on everything we've discussed, are you ready to move forward with this?"
                response_type = "closing"
            
            else:
                # General conversation response
                if 'yes' in customer_message or 'interested' in customer_message:
                    response_text = "That's great! Let me provide you with more details."
                elif 'no' in customer_message or 'not interested' in customer_message:
                    response_text = "I understand. Can I ask what your main concern is?"
                else:
                    response_text = "I appreciate you sharing that with me. Let me address your question."
                response_type = "general"
        
        # Use successful patterns from learning if available
        automatic_learning = memory.get('automatic_learning', {})
        successful_patterns = automatic_learning.get('successful_patterns', [])
        
        if successful_patterns and response_type == "general":
            # Use most successful approach
            top_pattern = successful_patterns[0]
            if top_pattern.get('effectiveness_score', 0) >= 7:
                learned_response = top_pattern.get('approach_used', '')
                if learned_response and len(learned_response) > 20:
                    response_text = learned_response[:200] + "..."
                    response_type = "learned_pattern"
        
        # Personalize response if customer profile exists
        if customer_profile:
            communication_style = customer_profile.communication_style
            if communication_style == 'direct':
                response_text = f"Let me be direct: {response_text}"
            elif communication_style == 'friendly':
                response_text = f"I appreciate your time! {response_text}"
            elif communication_style == 'formal':
                response_text = f"Thank you for your consideration. {response_text}"
        
        # Generate follow-up suggestions
        follow_up_suggestions = []
        if call_stage == 'objection_handling':
            follow_up_suggestions = [
                "Ask for specific concerns",
                "Provide social proof",
                "Offer trial or demo"
            ]
        elif call_stage == 'presentation':
            follow_up_suggestions = [
                "Ask qualifying questions",
                "Share success story", 
                "Address potential concerns"
            ]
        
        return Response({
            'agent_response': response_text,
            'response_metadata': {
                'response_type': response_type,
                'call_stage': call_stage,
                'objection_detected': objection_detected,
                'confidence_level': 'high' if response_type in ['objection_handling', 'learned_pattern'] else 'medium',
                'personalization_applied': bool(customer_profile)
            },
            'follow_up_suggestions': follow_up_suggestions,
            'agent_learning_notes': {
                'total_patterns_learned': len(successful_patterns),
                'objection_database_size': len(automatic_learning.get('objection_database', {})),
                'training_level': agent.training_level
            },
            'customer_context': {
                'known_customer': bool(customer_profile),
                'interest_level': customer_profile.interest_level if customer_profile else 'unknown',
                'previous_calls': customer_profile.total_calls if customer_profile else 0
            }
        }, status=status.HTTP_200_OK)
        
    except AIAgent.DoesNotExist:
        return Response({
            'error': 'AI Agent not found',
            'message': 'Please create an AI Agent first'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"AI response generation error: {str(e)}")
        return Response({
            'error': 'Response generation failed',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)