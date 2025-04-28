import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class TestStore:
    """Manages storage and retrieval of Locust test files"""
    
    def __init__(self, base_dir: str = None):
        # Set up local tests directory in the project
        self.tests_dir = os.path.join(os.getcwd(), 'tests', 'generated')
        os.makedirs(self.tests_dir, exist_ok=True)
        
        # Set up cache directory for MCP protocol
        if base_dir is None:
            if os.name == 'nt':  # Windows
                cache_base = os.path.expandvars('%LOCALAPPDATA%')
            elif os.name == 'darwin':  # macOS
                cache_base = os.path.expanduser('~/Library/Caches')
            else:  # Linux
                cache_base = os.path.expanduser('~/.cache')
            self.cache_dir = os.path.join(cache_base, 'ms-locust', 'mcp-tests')
            os.makedirs(self.cache_dir, exist_ok=True)
        else:
            self.cache_dir = base_dir
            
        # Keep track of test history
        self.history_file = os.path.join(self.tests_dir, 'history.json')
        self.load_history()
        
        logger.info(f"Test store initialized. Tests will be saved in: {self.tests_dir}")

    def load_history(self):
        """Load test history from file"""
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r') as f:
                self.history = json.load(f)
        else:
            self.history = []

    def save_history(self):
        """Save test history to file"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)

    def save_test(self, script: str, config: Dict[str, Any], description: str = "") -> Dict[str, Any]:
        """
        Save a test script and its configuration.
        Returns dict with test ID and file locations.
        """
        # Generate unique test ID using timestamp
        test_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save in local tests directory
        test_dir = os.path.join(self.tests_dir, test_id)
        os.makedirs(test_dir, exist_ok=True)
        
        script_path = os.path.join(test_dir, f'locust_test_{test_id}.py')
        config_path = os.path.join(test_dir, 'config.json')
        
        with open(script_path, 'w') as f:
            f.write(script)
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        # Also save in cache directory for MCP protocol
        cache_test_dir = os.path.join(self.cache_dir, test_id)
        os.makedirs(cache_test_dir, exist_ok=True)
        
        cache_script_path = os.path.join(cache_test_dir, f'locust_test_{test_id}.py')
        cache_config_path = os.path.join(cache_test_dir, 'config.json')
        
        with open(cache_script_path, 'w') as f:
            f.write(script)
        with open(cache_config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Add to history
        test_info = {
            'id': test_id,
            'timestamp': datetime.now().isoformat(),
            'description': description,
            'script_path': script_path,
            'config_path': config_path,
            'config': config
        }
        self.history.append(test_info)
        self.save_history()
        
        logger.info(f"Test files generated:")
        logger.info(f"- Script: {script_path}")
        logger.info(f"- Config: {config_path}")
        
        return test_info

    def get_test(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a test by its ID"""
        test_dir = os.path.join(self.tests_dir, test_id)
        if not os.path.exists(test_dir):
            return None
            
        script_path = os.path.join(test_dir, f'locust_test_{test_id}.py')
        config_path = os.path.join(test_dir, 'config.json')
        
        if not os.path.exists(script_path) or not os.path.exists(config_path):
            return None
            
        with open(script_path, 'r') as f:
            script = f.read()
            
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        return {
            'script': script,
            'config': config,
            'script_path': script_path,
            'config_path': config_path
        }

    def list_tests(self) -> List[Dict[str, Any]]:
        """List all saved tests"""
        return self.history
