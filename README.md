🚗 SmartRide - AI-Powered Ride Booking Assistant
An intelligent ride-sharing platform that uses natural language processing and AI to simplify multi-platform ride booking. Instead of manually comparing Uber, Lyft, and other services, simply tell SmartRide what you need in plain English.
🎯 The Problem
Booking the optimal ride today requires:
•	Checking multiple apps (Uber, Lyft, etc.)
•	Manually comparing prices and ETAs
•	Considering weather conditions
•	Factoring in surge pricing
•	Switching between apps repeatedly
Result: 5+ minutes of frustration for a single ride booking.
💡 The Solution
SmartRide transforms this into a simple conversation:
You: "Book a ride to the office tomorrow at 9am"
SmartRide: ✓ Checked weather (rain expected)
           ✓ Compared 4 ride options
           ✓ Best option: UberPool ($12.50, 15 min ETA)
           ✓ Ride booked!
Time taken: 10 seconds.
✨ Key Features
•	Natural Language Processing: Understand complex booking requests in plain English
•	Multi-Platform Integration: Fetch real-time data from Uber, Lyft APIs
•	Weather-Aware Booking: Automatically considers weather conditions
•	AI-Powered Recommendations: GPT-4 analyzes options and suggests the best ride
•	Smart Calendar Integration: Visual ride management with calendar interface
•	CRUD Operations: Create, read, update, and delete rides through chat commands
🏗️ Architecture
User Interface (Chat/Calendar)
         ↓
HTTP Bridge Server (Flask)
         ↓
MCP Server (JSON-RPC 2.0)
         ↓
┌────────┼────────┐
↓        ↓        ↓
NLP    AI Engine  APIs
    (Weather/Rides)
🛠️ Tech Stack
•	Backend: Python, Flask
•	AI/NLP: OpenAI GPT-4, Custom NLP Pipeline
•	APIs: OpenWeatherMap, Mock Uber/Lyft APIs
•	Frontend: HTML, CSS, JavaScript
•	Architecture: MCP (Model Context Protocol), JSON-RPC 2.0
📋 Prerequisites
•	Python 3.10+
•	OpenAI API Key
•	OpenWeatherMap API Key (optional)
🚀 Quick Start
1. Clone the Repository
bash
git clone https://github.com/yourusername/smartride.git
cd smartride
2. Create Virtual Environment
bash
python -m venv smartride-env
source smartride-env/bin/activate  # On Windows: smartride-env\Scripts\activate
3. Install Dependencies
bash
pip install flask flask-cors openai requests
4. Configure API Keys
Edit mcp_server.py and add your OpenAI API key:
python
openai_client = OpenAI(api_key="your-api-key-here")
5. Start the Services
Terminal 1 - Mock APIs:
bash
python mock_apis.py
Terminal 2 - HTTP Bridge Server:
bash
python http_bridge_server.py
Terminal 3 - Frontend (Optional):
bash
python -m http.server 8000
6. Access the Application
Open http://localhost:8000 in your browser or directly open index.html
💬 Example Commands
"Book a ride to downtown"
"Find rides to airport tomorrow at 3pm"
"Show me my upcoming rides"
"Cancel ride on Friday"
"Compare Uber and Lyft to Central Park"
"Book cheapest ride to office at 9am"
📁 Project Structure
smartride/
├── index.html              # Frontend UI
├── http_bridge_server.py   # Flask server handling HTTP requests
├── mcp_server.py          # MCP server with AI integration
├── mock_apis.py           # Mock Uber/Lyft API endpoints
├── README.md              # Documentation
└── requirements.txt       # Python dependencies
🔮 Future Enhancements
•	Real Uber/Lyft API integration
•	User authentication & profiles
•	Ride history analytics
•	Multi-language support
•	Mobile app (React Native)
•	Real-time price alerts
•	Group ride coordination
•	Favorite locations
🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.
👤 Author
Sai Gokul
•	LinkedIn: www.linkedin.com/in/sai-gokulyalamanchili
•	Email: ysaigokul09@gmail.com
 Acknowledgments
•	OpenAI for GPT-4 API
•	Anthropic for Claude and MCP concepts
•	OpenWeatherMap for weather data
 
⭐ If you find this project interesting, please give it a star!
<img width="468" height="635" alt="image" src="https://github.com/user-attachments/assets/d9eb0314-699a-4287-a195-7b8b6a4a2d8e" />
