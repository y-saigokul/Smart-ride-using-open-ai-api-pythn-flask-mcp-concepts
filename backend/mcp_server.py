#!/usr/bin/env python3
"""
Enhanced SmartRide MCP Server with Weather Integration and CRUD Operations
"""

import json
import sys
import requests
import random
from openai import OpenAI
from datetime import datetime, timedelta

# Initialize OpenAI client - replace with your API key
openai_client = OpenAI(api_key="open ai api key")

MOCK_API_BASE = "http://localhost:3001"

def get_mock_weather():
    """Simulate weather for demo purposes"""
    # Generate realistic weather scenarios
    scenarios = [
        {"will_rain": True, "rain_chance": 85, "condition": "Heavy Rain", "temp": 65},
        {"will_rain": True, "rain_chance": 70, "condition": "Light Rain", "temp": 68},
        {"will_rain": False, "rain_chance": 15, "condition": "Partly Cloudy", "temp": 75},
        {"will_rain": False, "rain_chance": 5, "condition": "Clear", "temp": 78},
        {"will_rain": True, "rain_chance": 90, "condition": "Thunderstorm", "temp": 62}
    ]

    # For demo consistency, you can make it deterministic based on time
    hour = datetime.now().hour
    scenario_index = hour % len(scenarios)

    return scenarios[scenario_index]

def should_book_immediately(weather_data, preferences):
    """Determine if ride should be booked immediately based on weather"""
    rain_threshold = 30  # Book immediately if rain chance > 30%

    if weather_data['will_rain'] and weather_data['rain_chance'] > rain_threshold:
        return True, f"Weather Alert: {weather_data['condition']} expected ({weather_data['rain_chance']}% rain chance). Booking immediately to avoid surge pricing."

    return False, f"Weather looks good: {weather_data['condition']} ({weather_data['rain_chance']}% rain chance). Will monitor prices until closer to ride time."

def handle_compare_rides(args):
    """Enhanced ride comparison with weather integration"""
    try:
        from_loc = args.get("from_location", "Home")
        to_loc = args.get("to_location", "Office")
        preferences = args.get("user_preferences", {})
        user_message = args.get("user_message", "")
        check_weather = args.get("check_weather", False)

        # Weather integration for tomorrow bookings
        weather_info = None
        immediate_booking = False
        weather_reason = ""

        if check_weather:
            weather_data = get_mock_weather()
            immediate_booking, weather_reason = should_book_immediately(weather_data, preferences)
            weather_info = weather_reason

        # Fetch data from mock APIs
        uber_response = requests.get(f"{MOCK_API_BASE}/api/uber/rides",
                                   params={'from': from_loc, 'to': to_loc})
        lyft_response = requests.get(f"{MOCK_API_BASE}/api/lyft/rides",
                                   params={'from': from_loc, 'to': to_loc})

        if uber_response.status_code != 200 or lyft_response.status_code != 200:
            return {"success": False, "error": "Failed to fetch ride data from APIs"}

        uber_data = uber_response.json()
        lyft_data = lyft_response.json()

        # Combine all options
        all_options = []
        for ride in uber_data['rides']:
            all_options.append({
                'service': 'Uber',
                'type': ride['type'],
                'price': ride['price'],
                'eta': ride['eta']
            })

        for ride in lyft_data['rides']:
            all_options.append({
                'service': 'Lyft',
                'type': ride['type'],
                'price': ride['price'],
                'eta': ride['eta']
            })

        # Apply user preferences
        filtered_options = all_options
        if preferences.get('no_shared_rides'):
            filtered_options = [opt for opt in all_options
                              if 'shared' not in opt['type'].lower() and 'pool' not in opt['type'].lower()]
            print(f"Filtered out shared rides. {len(filtered_options)} options remaining.")

        # Enhanced AI analysis with weather context
        ai_analysis = get_ai_recommendation(from_loc, to_loc, filtered_options, preferences, user_message, weather_info)

        # Calculate metrics
        prices = [opt['price'] for opt in all_options]
        metrics = {
            "total_options": len(all_options),
            "filtered_options": len(filtered_options),
            "potential_savings": max(prices) - min(prices) if prices else 0
        }

        result = {
            "success": True,
            "route": f"{from_loc} → {to_loc}",
            "ai_recommendation": ai_analysis,
            "all_options": all_options,
            "filtered_options": filtered_options,
            "preferences_applied": preferences,
            "metrics": metrics,
            "weather_info": weather_info,
            "immediate_booking": immediate_booking
        }

        return result

    except Exception as e:
        return {"success": False, "error": f"Ride comparison failed: {str(e)}"}

def handle_schedule_recurring(args):
    """Handle recurring ride scheduling"""
    try:
        schedule_desc = args.get("schedule_description", "")

        # Parse recurring schedule
        events = []
        if 'monday to friday' in schedule_desc.lower() or 'weekday' in schedule_desc.lower():
            weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
            days = [16, 17, 18, 19, 20]  # Sept 16-20 for example

            # Extract time from description
            time_part = '9:00 AM'  # Default
            if 'at' in schedule_desc:
                time_match = schedule_desc.split('at')[1].strip().split()[0]
                if any(char.isdigit() for char in time_match):
                    time_part = time_match + ' AM' if 'pm' not in time_match.lower() else time_match

            # Determine destination
            destination = 'Office' if 'office' in schedule_desc.lower() else 'Work'

            for i, day_name in enumerate(weekdays):
                events.append({
                    'date': days[i],
                    'day': day_name,
                    'time': time_part,
                    'destination': destination,
                    'type': 'recurring_ride'
                })

        result = {
            "success": True,
            "events_created": len(events),
            "schedule": events,
            "message": f"Scheduled {len(events)} recurring rides to {events[0]['destination'] if events else 'destination'} at {events[0]['time'] if events else 'time'}"
        }

        return result

    except Exception as e:
        return {"success": False, "error": f"Scheduling failed: {str(e)}"}

def handle_delete_ride(args):
    """Handle ride deletion/cancellation"""
    try:
        ride_id = args.get("ride_id")
        reason = args.get("reason", "User requested cancellation")

        # Mock deletion logic
        refund_amount = args.get("estimated_price", 15.00) * 0.9  # 90% refund

        result = {
            "success": True,
            "ride_cancelled": True,
            "ride_id": ride_id,
            "refund_amount": round(refund_amount, 2),
            "cancellation_reason": reason,
            "message": f"Ride {ride_id} cancelled successfully. Refund: ${refund_amount:.2f}"
        }

        return result

    except Exception as e:
        return {"success": False, "error": f"Cancellation failed: {str(e)}"}

def handle_update_ride(args):
    """Handle ride updates/modifications"""
    try:
        ride_id = args.get("ride_id")
        updates = args.get("updates", {})

        # Mock update logic
        updated_fields = []
        if "time" in updates:
            updated_fields.append(f"time changed to {updates['time']}")
        if "destination" in updates:
            updated_fields.append(f"destination changed to {updates['destination']}")

        result = {
            "success": True,
            "ride_updated": True,
            "ride_id": ride_id,
            "updates_applied": updates,
            "message": f"Ride {ride_id} updated: {', '.join(updated_fields)}" if updated_fields else "No changes made"
        }

        return result

    except Exception as e:
        return {"success": False, "error": f"Update failed: {str(e)}"}

def get_ai_recommendation(from_loc, to_loc, options, preferences, user_message, weather_info=None):
    """Get AI-powered ride recommendation with weather context"""

    weather_context = ""
    if weather_info:
        weather_context = f"\nWeather context: {weather_info}"

    prompt = f"""
    You are a ride optimization expert. Analyze these ride options for {from_loc} to {to_loc}:

    User request: "{user_message}"
    User preferences: {json.dumps(preferences)}
    {weather_context}

    Available options:
    {json.dumps(options, indent=2)}

    Instructions:
    1. If user preferences show no_shared_rides=true: Only consider UberX and Lyft (non-shared options)
    2. If user allows shared rides (no_shared_rides=false): Prioritize UberPool and Lyft Shared for savings
    3. Choose the best option considering: price (most important), ETA, weather impact
    4. Always respond in this EXACT format:

    RECOMMENDED_SERVICE: [Uber or Lyft]
    RECOMMENDED_TYPE: [UberX or UberPool or Lyft or Lyft Shared]
    REASON: [Brief explanation focusing on price savings and ETA]

    Example response:
    RECOMMENDED_SERVICE: Uber
    RECOMMENDED_TYPE: UberPool
    REASON: UberPool at $11.28 is $2.03 cheaper than Lyft Shared with same 18min ETA

    Choose the cheapest option that meets user preferences. Be specific with service and type names.
    """

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1  # Lower temperature for more consistent responses
        )

        ai_text = response.choices[0].message.content
        return {"ai_analysis": ai_text, "confidence": "high"}

    except Exception as e:
        return {"error": f"AI analysis failed: {str(e)}", "fallback": "cheapest_available"}

def main():
    """Simple request handler for MCP protocol"""
    try:
        # Read from stdin
        for line in sys.stdin:
            if not line.strip():
                continue

            try:
                request = json.loads(line.strip())

                # Handle different request types
                if request.get("method") == "tools/call":
                    tool_name = request["params"]["name"]
                    arguments = request["params"]["arguments"]

                    if tool_name == "compare_rides":
                        result = handle_compare_rides(arguments)
                    elif tool_name == "schedule_recurring_rides":
                        result = handle_schedule_recurring(arguments)
                    elif tool_name == "delete_ride":
                        result = handle_delete_ride(arguments)
                    elif tool_name == "update_ride":
                        result = handle_update_ride(arguments)
                    else:
                        result = {"success": False, "error": f"Unknown tool: {tool_name}"}

                    # Send response
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id", 1),
                        "result": [{"type": "text", "text": json.dumps(result)}]
                    }

                    print(json.dumps(response))
                    sys.stdout.flush()

                elif request.get("method") == "initialize":
                    # Send initialization response
                    init_response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id", 1),
                        "result": {
                            "protocolVersion": "1.0.0",
                            "capabilities": {"tools": {}},
                            "serverInfo": {
                                "name": "smartride-mcp-server",
                                "version": "2.0.0"
                            }
                        }
                    }
                    print(json.dumps(init_response))
                    sys.stdout.flush()

            except json.JSONDecodeError:
                continue

    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    print("Starting Enhanced SmartRide MCP Server...")
    print("Features: Weather Integration, CRUD Operations, AI Analysis")
    print("Available tools: compare_rides, schedule_recurring_rides, delete_ride, update_ride")
    main()
