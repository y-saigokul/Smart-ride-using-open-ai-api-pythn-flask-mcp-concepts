#!/usr/bin/env python3
"""
MCP HTTP Bridge Server - Complete Version with NLP and CRUD
Handles natural language processing and CRUD operations in Python backend
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import asyncio
import subprocess
import json
import re
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

class MCPBridge:
    """Bridge between HTTP REST API and MCP server"""
    
    def __init__(self, mcp_server_path: str = "mcp_server.py"):
        self.mcp_server_path = mcp_server_path
        self.request_counter = 0
    
    async def call_mcp_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call MCP tool via subprocess communication"""
        self.request_counter += 1
        
        try:
            # Prepare MCP messages
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "1.0.0",
                    "capabilities": {"tools": {}},
                    "clientInfo": {
                        "name": "smartride-http-bridge",
                        "version": "1.0.0"
                    }
                }
            }
            
            tool_request = {
                "jsonrpc": "2.0", 
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            # Start MCP server process
            process = subprocess.Popen(
                ['python', self.mcp_server_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )
            
            # Send initialization first
            init_data = json.dumps(init_message) + "\n"
            process.stdin.write(init_data)
            process.stdin.flush()
        
            # Wait a moment for initialization
            import time
            time.sleep(0.1)
            
            # Send tool request
            tool_data = json.dumps(tool_request) + "\n"
            stdout, stderr = process.communicate(input=tool_data)
            
            if stderr:
                print(f"MCP stderr: {stderr}")
            
            # Parse MCP response
            for line in stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    response = json.loads(line)
                    if response.get('id') == 2:  # Tool call response
                        if 'error' in response:
                            return {"success": False, "error": response['error']['message']}
                        
                        # Extract content from MCP response
                        result = response.get('result', {})
                        if isinstance(result, list) and len(result) > 0:
                            content_text = result[0].get('text', '{}')
                            try:
                                parsed_content = json.loads(content_text)
                                return {"success": True, "data": parsed_content}
                            except json.JSONDecodeError:
                                return {"success": True, "data": {"raw_response": content_text}}
                        
                        return {"success": True, "data": result}
                        
                except json.JSONDecodeError as e:
                    print(f"Failed to parse MCP response line: {line} - {e}")
                    continue
            
            return {"success": False, "error": "No valid MCP response received"}
            
        except Exception as e:
            return {"success": False, "error": f"MCP communication failed: {str(e)}"}

class CommandProcessor:
    """Processes natural language commands and routes to appropriate MCP tools"""
    
    def __init__(self):
        self.command_patterns = {
            'book': ['book', 'schedule', 'reserve'],
            'cancel': ['cancel', 'delete', 'remove'],
            'update': ['change', 'reschedule', 'update', 'modify'],
            'list': ['show', 'list', 'what rides', 'my rides']
        }
    
    def process_command(self, command: str, user_context: dict) -> dict:
        """Main command processing logic"""
        command_lower = command.lower()
        
        # Determine action type
        action = self.detect_action(command_lower)
        
        if action == 'book':
            return self.process_booking_command(command, user_context)
        elif action == 'cancel':
            return self.process_cancel_command(command, user_context)
        elif action == 'update':
            return self.process_update_command(command, user_context)
        elif action == 'list':
            return self.process_list_command(command, user_context)
        else:
            return {'success': False, 'error': 'Could not understand command. Try "book ride to office" or "cancel my ride"'}
    
    def detect_action(self, command: str) -> str:
        """Detect the intended action from command text"""
        for action, keywords in self.command_patterns.items():
            if any(keyword in command for keyword in keywords):
                return action
        return 'unknown'
    
    def extract_locations(self, command: str) -> tuple:
        """Extract from and to locations from command"""
        # Default values
        from_loc, to_loc = 'Home', 'Office'
        
        # Parse "to X from Y" pattern
        to_from_pattern = r'to\s+(\w+)\s+from\s+(\w+)'
        match = re.search(to_from_pattern, command, re.IGNORECASE)
        if match:
            to_loc = match.group(1).capitalize()
            from_loc = match.group(2).capitalize()
            return from_loc, to_loc
        
        # Parse direction keywords
        if 'office' in command:
            to_loc = 'Office'
            from_loc = 'Home'
        elif 'home' in command:
            to_loc = 'Home' 
            from_loc = 'Office'
        
        return from_loc, to_loc
    
    def extract_time(self, command: str) -> str:
        """Extract time from command"""
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm)',
            r'(\d{1,2})\s*(am|pm)',
            r'at\s*(\d{1,2}):?(\d{2})?\s*(am|pm)?'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        
        return None
    
    def extract_time_for_update(self, command: str) -> str:
        """Extract the target time for updates (time after 'to')"""
        command_lower = command.lower()
        
        # Look for patterns like "to 6pm", "to 6:00pm", "at 6pm"
        update_patterns = [
            r'to\s+(\d{1,2}):?(\d{2})?\s*(am|pm)',  # "to 6pm" or "to 6:30pm"
            r'at\s+(\d{1,2}):?(\d{2})?\s*(am|pm)',  # "at 6pm" 
            r'change.*to\s+(\d{1,2}):?(\d{2})?\s*(am|pm)',  # "change to 6pm"
        ]
        
        for pattern in update_patterns:
            match = re.search(pattern, command_lower)
            if match:
                hour = match.group(1)
                minute = match.group(2) if match.group(2) else "00"
                period = match.group(3).upper()
                
                # Format the time properly
                if minute == "00":
                    return f"{hour}:00 {period}"
                else:
                    return f"{hour}:{minute} {period}"
        
        # Fallback: look for any time pattern and take the LAST one found
        # (assuming it's the target time, not the identifying time)
        all_times = []
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm)',
            r'(\d{1,2})\s*(am|pm)',
        ]
        
        for pattern in time_patterns:
            matches = re.finditer(pattern, command_lower)
            for match in matches:
                all_times.append(match.group(0).strip())
        
        # Return the last time found (most likely the target)
        if len(all_times) > 1:
            return all_times[-1]  # Last time mentioned
        elif len(all_times) == 1:
            return all_times[0]
        
        return None

    def extract_identifier_time(self, command: str) -> str:
        """Extract the time that identifies which ride to update (before 'to')"""
        command_lower = command.lower()
        
        # Split on "to" and look for time in the first part
        if ' to ' in command_lower:
            before_to = command_lower.split(' to ')[0]
            
            # Look for time patterns in the identifying part
            time_patterns = [
                r'(\d{1,2}):(\d{2})\s*(am|pm)',
                r'(\d{1,2})\s*(am|pm)',
            ]
            
            for pattern in time_patterns:
                matches = list(re.finditer(pattern, before_to))
                if matches:
                    # Take the last time found in the identifying part
                    return matches[-1].group(0).strip()
        
        return None

    def normalize_time_format(self, time_str: str) -> str:
        """Normalize time format for comparison"""
        if not time_str:
            return ""
        
        time_lower = time_str.lower().strip()
        
        # Handle formats like "5pm", "5:00 pm", "17:00"
        import re
        
        # Pattern for "5pm" format
        match = re.match(r'(\d{1,2})\s*(am|pm)', time_lower)
        if match:
            hour = int(match.group(1))
            period = match.group(2)
            return f"{hour}:00 {period.upper()}"
        
        # Pattern for "5:00 pm" format
        match = re.match(r'(\d{1,2}):(\d{2})\s*(am|pm)', time_lower)
        if match:
            hour = int(match.group(1))
            minute = match.group(2)
            period = match.group(3)
            return f"{hour}:{minute} {period.upper()}"
        
        # Return as-is if no pattern matches
        return time_str

    def extract_destination_for_update(self, command: str) -> str:
        """Extract new destination from update command"""
        command_lower = command.lower()
        
        # Look for destination patterns
        dest_patterns = [
            r'to\s+([a-zA-Z]+)(?:\s|$)',  # "to airport", "to office"
            r'destination.*?to\s+([a-zA-Z]+)',  # "change destination to office"
        ]
        
        for pattern in dest_patterns:
            match = re.search(pattern, command_lower)
            if match:
                destination = match.group(1).capitalize()
                # Skip time-related words
                if destination.lower() not in ['am', 'pm', 'time']:
                    return destination
        
        return None
    
    def extract_date(self, command: str, current_date: int) -> int:
        """Extract target date from command"""
        if 'tomorrow' in command:
            return min(current_date + 1, 30)
        elif 'today' in command:
            return current_date
        else:
            return current_date
    
    def extract_preferences(self, command: str) -> dict:
        """Extract user preferences from command"""
        return {
            'no_shared_rides': any(phrase in command.lower() for phrase in 
                                 ['no shared', 'not shared', 'no pool', "don't want shared"]),
            'preferred_time': self.extract_time(command)
        }
    
    def process_booking_command(self, command: str, user_context: dict) -> dict:
        """Process ride booking commands"""
        from_loc, to_loc = self.extract_locations(command)
        time = self.extract_time(command)
        target_date = self.extract_date(command, user_context.get('selected_date', 12))
        preferences = self.extract_preferences(command)
        
        # Check if this is a tomorrow booking (weather feature)
        is_tomorrow = 'tomorrow' in command.lower()
        
        # Prepare MCP arguments
        mcp_args = {
            "from_location": from_loc,
            "to_location": to_loc,
            "user_preferences": preferences,
            "user_message": command,
            "target_date": target_date,
            "check_weather": is_tomorrow
        }
        
        print(f"Booking: {from_loc} → {to_loc}, Date: {target_date}, Weather check: {is_tomorrow}")
        
        # Call MCP tool
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            mcp_result = loop.run_until_complete(
                mcp_bridge.call_mcp_tool("compare_rides", mcp_args)
            )
        finally:
            loop.close()
        
        if not mcp_result["success"]:
            return {'success': False, 'error': mcp_result["error"]}
        
        # Process MCP response
        mcp_data = mcp_result["data"]
        
        # Extract AI recommendation
        ai_recommendation = mcp_data.get("ai_recommendation", {})
        best_option = self.extract_ai_recommended_option(ai_recommendation.get('ai_analysis', ''), 
                                                       mcp_data.get("all_options", []))
        
        if not best_option:
            return {'success': False, 'error': 'No suitable ride options found'}
        
        # Prepare response
        ride_id = int(datetime.now().timestamp())
        
        response_message = f"📊 Found {len(mcp_data.get('all_options', []))} options\n{ai_recommendation.get('ai_analysis', '')}\n✅ Booked {best_option['service']} {best_option['type']} - ${best_option['price']}"
        
        # Add weather information if applicable
        weather_info = mcp_data.get('weather_info')
        if weather_info:
            response_message += f"\n🌤️ {weather_info}"
        
        return {
            'success': True,
            'action': 'book_ride',
            'message': response_message,
            'ride_data': {
                'id': ride_id,
                'from': from_loc,
                'to': to_loc,
                'price': best_option['price'],
                'saved': round(mcp_data.get("metrics", {}).get('potential_savings', 0), 2),
                'service': best_option['type'],
                'date': f"Sep {target_date}, {time or '9:00 AM'}",
                'time': time or '9:00 AM',
                'target_date': target_date
            },
            'notification': f"✅ Booked {best_option['service']} {best_option['type']} - Saved ${round(mcp_data.get('metrics', {}).get('potential_savings', 0), 2)}"
        }
    
    def process_cancel_command(self, command: str, user_context: dict) -> dict:
        """Process ride cancellation commands"""
        current_rides = user_context.get('current_rides', [])
        
        if not current_rides:
            return {
                'success': True,
                'action': 'list_rides',
                'message': '📋 You have no booked rides to cancel.'
            }
        
        # Find which ride to cancel based on command
        ride_to_cancel = self.find_ride_from_command(command, current_rides)
        
        if not ride_to_cancel:
            rides_list = "\n".join([f"- {ride['from']} to {ride['to']} at {ride['time']} ({ride['service']})" 
                                   for ride in current_rides])
            return {
                'success': True,
                'action': 'list_rides',
                'message': f"🤔 Which ride would you like to cancel?\n\nYour current rides:\n{rides_list}\n\nPlease be more specific (e.g., 'cancel my office ride' or 'cancel tomorrow's ride')."
            }
        
        # Calculate refund (mock calculation)
        refund_amount = round(ride_to_cancel['price'] * 0.75, 2)  # 75% refund
        
        return {
            'success': True,
            'action': 'delete_ride',
            'message': f"❌ Cancelled {ride_to_cancel['service']} ride from {ride_to_cancel['from']} to {ride_to_cancel['to']}\n💰 Refund: ${refund_amount} refunded 75% of the original price by charging a 25% cancellation fee",
            'deleted_ride': {
                'id': ride_to_cancel['id'],
                'refund': refund_amount
            },
            'notification': f"❌ Ride cancelled - ${refund_amount} refund processed"
        }
    
    def process_update_command(self, command: str, user_context: dict) -> dict:
        """Process ride update commands with improved time extraction"""
        current_rides = user_context.get('current_rides', [])
        
        if not current_rides:
            return {
                'success': True,
                'action': 'list_rides',
                'message': '📋 You have no booked rides to update.'
            }
        
        # Find which ride to update
        ride_to_update = self.find_ride_from_command(command, current_rides)
        
        if not ride_to_update:
            return {
                'success': True,
                'action': 'list_rides',
                'message': '🤔 Which ride would you like to update? Please be more specific.'
            }
        
        # Extract what to update - use the new time extraction method
        new_time = self.extract_time_for_update(command)
        
        if new_time:
            updates = {'time': new_time}
            message = f"✏️ Updated {ride_to_update['service']} ride from {ride_to_update['from']} to {ride_to_update['to']} - time changed to {new_time}"
        else:
            # Check for other update types
            new_destination = self.extract_destination_for_update(command)
            if new_destination:
                updates = {'destination': new_destination}
                message = f"✏️ Updated {ride_to_update['service']} ride destination to {new_destination}"
            else:
                return {
                    'success': False,
                    'error': '🤔 What would you like to update? (e.g., "change my ride time to 10am" or "change destination to airport")'
                }
        
        return {
            'success': True,
            'action': 'update_ride',
            'message': message,
            'updated_ride': {
                'id': ride_to_update['id'],
                'updates': updates
            },
            'notification': f"✏️ Ride updated successfully"
        }
    
    def process_list_command(self, command: str, user_context: dict) -> dict:
        """Process ride listing commands"""
        current_rides = user_context.get('current_rides', [])
        
        if not current_rides:
            return {
                'success': True,
                'action': 'list_rides',
                'message': '📋 You have no booked rides currently.\n\n💡 Try saying "book ride to office" to schedule your first ride!'
            }
        
        total_cost = sum(ride['price'] for ride in current_rides)
        total_saved = sum(ride.get('saved', 0) for ride in current_rides)
        
        rides_summary = f"📋 Your booked rides ({len(current_rides)} total):\n\n"
        
        for ride in current_rides:
            rides_summary += f"🚗 {ride['from']} → {ride['to']}\n"
            rides_summary += f"   📅 {ride['date']} | 💰 ${ride['price']} | 🚙 {ride['service']}\n\n"
        
        rides_summary += f"💵 Total cost: ${total_cost:.2f}\n💰 Total saved: ${total_saved:.2f}"
        
        return {
            'success': True,
            'action': 'list_rides',
            'message': rides_summary,
            'rides': current_rides
        }
    
    def find_ride_from_command(self, command: str, rides: list) -> dict:
        """Find specific ride based on command text with improved matching"""
        if not rides:
            return None
            
        command_lower = command.lower()
        
        # For update commands, look for identifying time first (before "to")
        if 'update' in command_lower or 'change' in command_lower:
            # Extract the identifying time (the current time of the ride)
            identifying_time = self.extract_identifier_time(command)
            
            if identifying_time:
                # Normalize time formats for comparison
                identifying_time_normalized = self.normalize_time_format(identifying_time)
                
                for ride in rides:
                    ride_time_normalized = self.normalize_time_format(ride.get('time', ''))
                    if identifying_time_normalized == ride_time_normalized:
                        print(f"Found ride by identifying time: {ride['time']} matches {identifying_time}")
                        return ride
        
        # Match by specific time mentioned in the command (for non-update commands)
        time_patterns = ['5pm', '6pm', '7pm', '8pm', '9am', '10am', '11am', '12pm', '1pm', '2pm', '3pm', '4pm']
        for time_str in time_patterns:
            if time_str in command_lower:
                for ride in rides:
                    if time_str.replace('pm', ' PM').replace('am', ' AM') in ride.get('time', ''):
                        print(f"Found ride by time match: {ride['time']} contains {time_str}")
                        return ride
        
        # Match by route (destination priority)
        if 'office' in command_lower:
            for ride in rides:
                if 'office' in ride['to'].lower():
                    print(f"Found ride by destination: {ride['to']}")
                    return ride
        
        if 'home' in command_lower:
            for ride in rides:
                if 'home' in ride['to'].lower():
                    print(f"Found ride by destination: {ride['to']}")
                    return ride
        
        # Match by service type
        if 'uber' in command_lower:
            for ride in rides:
                if 'uber' in ride.get('service', '').lower():
                    print(f"Found ride by service: {ride['service']}")
                    return ride
        
        if 'lyft' in command_lower:
            for ride in rides:
                if 'lyft' in ride.get('service', '').lower():
                    print(f"Found ride by service: {ride['service']}")
                    return ride
        
        # If no specific match found, return the most recent ride
        if rides:
            print(f"No specific match - returning most recent ride: {rides[-1]['from']} → {rides[-1]['to']}")
            return rides[-1]
        
        return None
    
    def extract_ai_recommended_option(self, ai_text: str, all_options: list) -> dict:
        """Extract the AI recommended option from AI analysis text"""
        if not ai_text or not all_options:
            return all_options[0] if all_options else None

        ai_lower = ai_text.lower()
        
        # Parse the structured AI response format
        # Look for "RECOMMENDED_SERVICE: [Service] RECOMMENDED_TYPE: [Type]"
        
        # Extract recommended service
        recommended_service = None
        if 'recommended_service:' in ai_lower:
            service_part = ai_lower.split('recommended_service:')[1].split('recommended_type:')[0].strip()
            if 'uber' in service_part:
                recommended_service = 'Uber'
            elif 'lyft' in service_part:
                recommended_service = 'Lyft'
        
        # Extract recommended type
        recommended_type = None
        if 'recommended_type:' in ai_lower:
            type_part = ai_lower.split('recommended_type:')[1].split('reason:')[0].strip()
            recommended_type = type_part.strip()
        
        # Find exact match first
        if recommended_service and recommended_type:
            for opt in all_options:
                if (opt['service'] == recommended_service and 
                    opt['type'].lower() == recommended_type.lower()):
                    print(f"AI recommended: {recommended_service} {recommended_type} - Found exact match")
                    return opt
        
        # Fallback: look for service + type keywords in AI text
        if 'uberpool' in ai_lower or ('uber' in ai_lower and 'pool' in ai_lower):
            for opt in all_options:
                if opt['service'] == 'Uber' and 'pool' in opt['type'].lower():
                    print(f"AI recommended UberPool - Found via keyword match")
                    return opt
        
        if 'lyft shared' in ai_lower or ('lyft' in ai_lower and 'shared' in ai_lower):
            for opt in all_options:
                if opt['service'] == 'Lyft' and 'shared' in opt['type'].lower():
                    print(f"AI recommended Lyft Shared - Found via keyword match")
                    return opt
        
        if 'uberx' in ai_lower or ('uber' in ai_lower and 'pool' not in ai_lower):
            for opt in all_options:
                if opt['service'] == 'Uber' and 'pool' not in opt['type'].lower():
                    print(f"AI recommended UberX - Found via keyword match")
                    return opt
        
        if 'lyft' in ai_lower and 'shared' not in ai_lower:
            for opt in all_options:
                if opt['service'] == 'Lyft' and 'shared' not in opt['type'].lower():
                    print(f"AI recommended Lyft - Found via keyword match")
                    return opt
        
        # Final fallback - return cheapest option
        cheapest = min(all_options, key=lambda x: x['price'])
        print(f"No AI match found - Selecting cheapest option: {cheapest['service']} {cheapest['type']}")
        return cheapest

# Initialize components
mcp_bridge = MCPBridge()
command_processor = CommandProcessor()

@app.route('/api/process-command', methods=['POST'])
def process_command():
    """Main endpoint for processing natural language commands"""
    try:
        data = request.get_json()
        command = data.get('command', '')
        user_context = data.get('user_context', {})
        
        print(f"Processing command: {command}")
        
        # Process command
        result = command_processor.process_command(command, user_context)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Command processing failed: {str(e)}'})

# Legacy endpoints for backward compatibility
@app.route('/api/compare-rides', methods=['POST'])
def compare_rides():
    """Legacy endpoint - redirects to command processing"""
    try:
        data = request.get_json()
        
        # Convert to command format
        from_loc = data.get('from', 'Home')
        to_loc = data.get('to', 'Office')
        preferences = data.get('preferences', {})
        
        # Build command text
        command = f"book ride to {to_loc.lower()} from {from_loc.lower()}"
        if preferences.get('time'):
            command += f" at {preferences['time']}"
        if preferences.get('noShared'):
            command += " with no shared rides"
        
        # Process through new system
        result = command_processor.process_command(command, {})
        
        # Convert back to legacy format
        if result['success'] and result['action'] == 'book_ride':
            ride_data = result['ride_data']
            return jsonify({
                'success': True,
                'winner': {
                    'service': ride_data['service'].split()[0],
                    'type': ride_data['service'],
                    'price': ride_data['price']
                },
                'aiRecommendation': {
                    'service': ride_data['service'].split()[0],
                    'type': ride_data['service'],
                    'price': ride_data['price']
                },
                'explanation': result['message'],
                'savings': ride_data['saved']
            })
        
        return jsonify({'success': False, 'error': result.get('error', 'Unknown error')})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Legacy endpoint error: {str(e)}'})

@app.route('/api/schedule-recurring', methods=['POST'])
def schedule_recurring():
    """Legacy endpoint for recurring scheduling"""
    try:
        data = request.get_json()
        command = data.get('text', '')
        
        # Process through new system
        result = command_processor.process_command(command, {})
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message'],
                'events': result.get('events', [])
            })
        
        return jsonify({'success': False, 'error': result.get('error', 'Scheduling failed')})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Scheduling error: {str(e)}'})

@app.route('/api/mcp-status', methods=['GET'])
def mcp_status():
    """Status endpoint showing MCP integration details"""
    return jsonify({
        'status': 'MCP Bridge Active - NLP + CRUD Version',
        'architecture': 'Natural Language → Python Processing → MCP Protocol → AI Tools',
        'mcp_server': 'mcp_server.py',
        'request_count': mcp_bridge.request_counter,
        'features': [
            'Natural Language Processing',
            'CRUD Operations via Chat',
            'Weather-aware Booking',
            'AI-powered Recommendations'
        ],
        'available_commands': [
            'book ride to [location]',
            'cancel my ride',
            'change ride time to [time]',
            'show my rides'
        ]
    })

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'MCP HTTP Bridge running',
        'mcp_integration': True,
        'nlp_processing': True,
        'crud_operations': True,
        'weather_integration': True,
        'port': 3003
    })

if __name__ == '__main__':
    print("🌉 Starting SmartRide MCP HTTP Bridge (NLP + CRUD Version)...")
    print("🧠 Features: Natural Language Processing, CRUD Operations, Weather Integration")
    print("🔗 Architecture: Natural Language → Python Processing → MCP → AI")
    print("💬 Try commands like:")
    print("   • 'book ride to office tomorrow at 9am'")
    print("   • 'cancel my ride to home'") 
    print("   • 'change my office ride to 10am'")
    print("   • 'show me all my rides'")
    print("🌐 Running on http://localhost:3003")
    
    app.run(debug=True, port=3003)