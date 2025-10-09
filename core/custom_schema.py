from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.openapi import Info

class CustomSchemaGenerator(OpenAPISchemaGenerator):
    """Custom schema generator to control API tags"""
    
    def get_operation_keys(self, subpath, method, view, base_path):
        """Override to control tag generation"""
        operation_keys = super().get_operation_keys(subpath, method, view, base_path)
        
        # Custom tag mapping based on URL patterns
        if operation_keys:
            first_key = operation_keys[0].lower()
            
            # Map URL prefixes to desired tags
            tag_mapping = {
                'agents': 'AI Agents',
                'accounts': 'User Management', 
                'calls': 'Calls',
                'subscriptions': 'Subscriptions',
                'dashboard': 'Dashboard',
                'auth': 'Authentication'
            }
            
            # Replace the auto-generated tag
            for url_prefix, custom_tag in tag_mapping.items():
                if first_key.startswith(url_prefix):
                    operation_keys[0] = custom_tag
                    break
        
        return operation_keys
