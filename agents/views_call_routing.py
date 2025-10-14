"""
Call Routing API Views
Provides endpoints to test and monitor the intelligent call routing system.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.utils import timezone
from .models import Agent
from .call_routing import CallRoutingManager
from .ai_agent_models import CallSession
import logging

logger = logging.getLogger(__name__)


class CallRoutingTestView(APIView):
    """Test the call routing system with different scenarios"""
    
    def post(self, request):
        """Test call routing with simulated data"""
        try:
            test_data = request.data
            caller_number = test_data.get('caller_number', '+1234567890')
            context = test_data.get('context', 'general')
            
            # Test the routing system
            routing_result = CallRoutingManager.route_incoming_call(
                caller_number=caller_number,
                twilio_data={'test': True}
            )
            
            response_data = {
                'test_caller': caller_number,
                'routing_successful': routing_result['success'],
                'selected_agent': {
                    'id': str(routing_result['agent'].id) if routing_result['agent'] else None,
                    'name': routing_result['agent'].name if routing_result['agent'] else None,
                    'calls_handled': routing_result['agent'].calls_handled if routing_result['agent'] else 0
                } if routing_result['agent'] else None,
                'routing_method': routing_result['routing_method'],
                'context': routing_result['context'],
                'error': routing_result.get('error')
            }
            
            return Response(response_data, status=200)
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class CallRoutingStatsView(APIView):
    """Get call routing statistics and system status"""
    
    def get(self, request):
        """Get routing system statistics"""
        try:
            # Get routing stats
            stats = CallRoutingManager.get_routing_stats()
            
            # Get agent load distribution
            agents = Agent.objects.filter(agent_type='inbound', status='active')
            agent_stats = []
            
            for agent in agents:
                agent_stats.append({
                    'id': str(agent.id),
                    'name': agent.name,
                    'calls_handled': agent.calls_handled,
                    'total_calls': agent.total_calls,
                    'auto_answer_enabled': agent.auto_answer_enabled,
                    'success_rate': (agent.successful_calls / agent.total_calls * 100) if agent.total_calls > 0 else 0
                })
            
            # Recent call routing history
            recent_calls = CallSession.objects.filter(
                call_type='inbound'
            ).order_by('-started_at')[:10]
            
            call_history = []
            for call in recent_calls:
                call_history.append({
                    'caller_number': call.caller_number,  # Fixed: use caller_number field
                    'agent_name': call.ai_agent.name if call.ai_agent else 'Unassigned',
                    'routing_method': getattr(call, 'routing_method', 'unknown'),
                    'outcome': call.outcome,
                    'duration': call.duration_seconds,
                    'timestamp': call.started_at.isoformat()
                })
            
            return Response({
                'routing_stats': stats,
                'agent_distribution': agent_stats,
                'recent_calls': call_history,
                'system_status': 'operational' if stats['routing_ready'] else 'no_agents_available'
            }, status=200)
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class AvailableAgentsView(APIView):
    """Get list of available inbound agents"""
    
    def get(self, request):
        """Get currently available inbound agents"""
        try:
            agents = CallRoutingManager.get_available_inbound_agents()
            
            agent_list = []
            for agent in agents:
                agent_list.append({
                    'id': str(agent.id),
                    'name': agent.name,
                    'calls_handled': agent.calls_handled,
                    'total_calls': agent.total_calls,
                    'average_duration': agent.average_call_duration,
                    'customer_satisfaction': agent.customer_satisfaction,
                    'auto_answer_enabled': agent.auto_answer_enabled,
                    'voice_model': agent.voice_model,
                    'specialization': getattr(agent, 'specialization', 'general')
                })
            
            return Response({
                'available_agents': agent_list,
                'total_available': len(agent_list),
                'routing_ready': len(agent_list) > 0
            }, status=200)
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class SimulateInboundCallView(APIView):
    """Simulate an inbound call for testing"""
    
    def post(self, request):
        """Simulate an inbound call scenario"""
        try:
            sim_data = request.data
            caller_number = sim_data.get('caller_number', '+1555000TEST')
            caller_context = sim_data.get('context', 'general')
            
            logger.info(f"🧪 Simulating inbound call from {caller_number}")
            
            # Simulate the routing process
            routing_result = CallRoutingManager.route_incoming_call(
                caller_number=caller_number,
                twilio_data={'simulation': True, 'context': caller_context}
            )
            
            if routing_result['success']:
                selected_agent = routing_result['agent']
                
                # Create a simulated call session
                call_session = CallSession.objects.create(
                    twilio_call_sid=f"SIM_{caller_number}_{timezone.now().timestamp()}",
                    phone_number=caller_number,
                    call_type='inbound',
                    ai_agent=selected_agent,
                    outcome='simulated',
                    routing_method=routing_result['routing_method']
                )
                
                response = {
                    'simulation_successful': True,
                    'call_session_id': str(call_session.id),
                    'routed_to_agent': {
                        'id': str(selected_agent.id),
                        'name': selected_agent.name,
                        'calls_handled': selected_agent.calls_handled
                    },
                    'routing_details': {
                        'method': routing_result['routing_method'],
                        'context': routing_result['context']
                    },
                    'twiml_response': f"""
                    <Response>
                        <Say voice="alice">Hello! You've reached {selected_agent.name}. This is a simulation.</Say>
                    </Response>
                    """.strip()
                }
                
                return Response(response, status=200)
            else:
                return Response({
                    'simulation_successful': False,
                    'error': routing_result.get('error', 'No agents available'),
                    'routing_details': routing_result
                }, status=200)
                
        except Exception as e:
            logger.error(f"Simulation error: {str(e)}")
            return Response({'error': str(e)}, status=500)